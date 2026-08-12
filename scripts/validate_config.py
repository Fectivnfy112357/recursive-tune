"""recursive-tune v0.1 · 配置校验。

校验 scoring.yaml / config.yaml（spec D3 + D8 hard rules），
任何违规直接报错退出——不静默通过。

CLI:  python scripts/validate_config.py [scoring.yaml] [config.yaml]
默认路径: ./scoring.yaml ./config.yaml
"""

from pathlib import Path
import ast
import copy
import json
import operator
import os
import subprocess
import sys

import yaml

DEFAULT_SCORING = "scoring.yaml"
DEFAULT_CONFIG = "config.yaml"
REQUIRED_CONFIG_KEYS = ("target_path", "writer", "judge", "program", "automations")
VALID_TYPES = ("hard", "soft")
ALLOWED_HARD_AGGREGATE = ("arithmetic_mean",)  # v0.1 只用均值（spec D3）
ALLOWED_SOFT_AGGREGATE = ("weighted_mean",)
JUDGE_PROMPT = "judge_prompt"

# D9（v0.2 spec D1）：社区共识 hard signal 首次使用免跑 fixture-set 验证。
# 豁免识别机制（O5）：first cut 用内建工具名白名单（不动 scoring.yaml schema）。
# 匹配语义：signal 命令的第一个词（工具名）命中即豁免——"pytest" 覆盖
# pytest / pytest -q / pytest -q -x 等全部社区共识变体（C-改1）。
# 维护纪律：扩白名单时必须同步在 tests/test_d9_gate.py 加 test_exempt_xxx_variants
# 验证新工具名豁免生效（spec D1 O5 锁定段）。
KNOWN_EXEMPT_COMMANDS = ("pytest",)
D9_MIN_SAMPLES = 20
D9_MIN_PER_SIDE = 10
D9_HIT_THRESHOLD = 0.8
D9_FIXTURE_ENV = "D9_FIXTURE_PATH"

_FORMULA_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod,
    ast.USub: operator.neg, ast.UAdd: operator.pos,
}


def eval_formula(formula, hard, soft):
    """安全求值 aggregate.final.formula（仅允许 hard/soft 变量 + 算术运算符）。

    不用 eval：__builtins__ 清空仍可经属性访问链逃逸。这里用 ast 白名单，
    只接受 Constant / Name(hard|soft) / 四则运算 + 幂 + 取模 + 一元正负。
    """
    node = ast.parse(formula, mode="eval").body

    def _eval(n):
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return n.value
        if isinstance(n, ast.Name) and n.id in ("hard", "soft"):
            return hard if n.id == "hard" else soft
        if isinstance(n, ast.BinOp) and type(n.op) in _FORMULA_OPS:
            return _FORMULA_OPS[type(n.op)](_eval(n.left), _eval(n.right))
        if isinstance(n, ast.UnaryOp) and type(n.op) in _FORMULA_OPS:
            return _FORMULA_OPS[type(n.op)](_eval(n.operand))
        raise ValueError(f"formula 只允许 hard/soft + 算术运算符: {formula!r}")

    return _eval(node)


def validate_scoring(data):
    """校验 scoring.yaml 结构。返回错误列表（空 = 通过）。"""
    errors = []
    if not isinstance(data, dict):
        return ["scoring.yaml 必须是 YAML 映射"]

    dims = data.get("dimensions")
    if not isinstance(dims, list) or not dims:
        errors.append("dimensions 必须是非空列表")
        dims = []

    has_hard = False
    for i, d in enumerate(dims):
        prefix = f"dimensions[{i}]"
        if not isinstance(d, dict):
            errors.append(f"{prefix} 必须是映射")
            continue
        for key in ("name", "type", "weight", "signal"):
            if key not in d:
                errors.append(f"{prefix} 缺 {key}")
        if not isinstance(d.get("name"), str) or not d.get("name"):
            errors.append(f"{prefix}.name 必须是非空字符串")
        if d.get("type") not in VALID_TYPES:
            errors.append(f"{prefix}.type 必须是 hard|soft")
        weight = d.get("weight")
        if not isinstance(weight, (int, float)) or not (0 <= weight <= 1):
            errors.append(f"{prefix}.weight 必须是 0..1 的数值")
        if not isinstance(d.get("signal"), str) or not d.get("signal"):
            errors.append(f"{prefix}.signal 必须是非空字符串")
        if d.get("type") == "hard":
            has_hard = True
            if d.get("signal") == JUDGE_PROMPT:
                errors.append(f"{prefix} hard 维度的 signal 必须是命令，不能是 {JUDGE_PROMPT}")
        elif d.get("type") == "soft" and d.get("signal") != JUDGE_PROMPT:
            errors.append(f"{prefix} soft 维度的 signal 必须是 {JUDGE_PROMPT}")

    if not has_hard:
        errors.append("至少 1 个 type: hard 维度（D8 rule 2）")

    agg = data.get("aggregate")
    if not isinstance(agg, dict):
        errors.append("aggregate 必须是映射")
    else:
        for key in ("hard", "soft", "final"):
            if key not in agg:
                errors.append(f"aggregate 缺 {key}")
        if agg.get("hard") not in ALLOWED_HARD_AGGREGATE:
            errors.append(f"aggregate.hard 必须是 {'|'.join(ALLOWED_HARD_AGGREGATE)}（v0.1 只用均值）")
        if agg.get("soft") not in ALLOWED_SOFT_AGGREGATE:
            errors.append(f"aggregate.soft 必须是 {'|'.join(ALLOWED_SOFT_AGGREGATE)}")
        final = agg.get("final")
        if not isinstance(final, dict):
            if "final" in agg:
                errors.append("aggregate.final 必须是映射")
        elif not isinstance(final.get("formula"), str) or not final.get("formula"):
            errors.append("aggregate.final.formula 必须是非空字符串")
        elif not _formula_syntax_ok(final.get("formula")):
            errors.append("aggregate.final.formula 不可求值（只允许 hard/soft + 算术运算符）")
    return errors


def parse_fixture(path):
    """解析 fixtures/<dimension-name>.yaml。返回 (positive_total, negative_total, errors)。

    结构错误（非法 YAML / 缺 expect / 非 pass|fail）→ errors（阻断，配置坏了要修）。
    """
    errors = []
    try:
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        return 0, 0, [f"{path.name} 非法 YAML: {exc}"]
    if not isinstance(raw, list):
        return 0, 0, [f"{path.name} 必须是 YAML 列表"]
    pos = neg = 0
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            errors.append(f"{path.name}[{i}] 必须是映射（input + expect）")
            continue
        if "input" not in item:
            errors.append(f"{path.name}[{i}] 缺 input 字段")
        expect = item.get("expect")
        if expect not in ("pass", "fail"):
            errors.append(f"{path.name}[{i}] expect 必须是 pass|fail")
            continue
        if expect == "pass":
            pos += 1
        else:
            neg += 1
    return pos, neg, errors


def run_signal_for_d9(signal, fixture_path, cwd):
    """执行 signal 命令做 D9 命中验证（A-min 约定）。

    注入 D9_FIXTURE_PATH 环境变量，cwd = fixture 所在目录；
    返回解析后的 dict；任何失败（非零 / 超时 / 输出不可解析）→ None。
    """
    env = dict(os.environ)
    env[D9_FIXTURE_ENV] = str(fixture_path)
    try:
        proc = subprocess.run(
            signal, shell=True, cwd=str(cwd), env=env,
            capture_output=True, text=True, timeout=30,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None
    if proc.returncode != 0:
        return None
    try:
        data = json.loads(proc.stdout.strip())
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    for key in ("total", "positive_hit", "negative_reject"):
        if not isinstance(data.get(key), (int, float)):
            return None
    return data


def validate_d9(scoring, base_dir):
    """D9 门禁（v0.2 spec D1 + T1/T2）。

    返回 (errors, warnings)：errors = 结构错误（fixture 配错，阻断）；
    warnings = 降级提示（缺 fixture / 样本不足 / 命中不足 / 命令未实现 D9 模式，
    不阻断——用户可降级 soft 继续）。
    """
    errors = []
    warnings = []
    dims = scoring.get("dimensions") if isinstance(scoring, dict) else None
    if not isinstance(dims, list):
        return errors, warnings
    fixtures_dir = Path(base_dir) / "fixtures"
    for d in dims:
        if not isinstance(d, dict) or d.get("type") != "hard":
            continue
        name = d.get("name")
        signal = d.get("signal")
        if not isinstance(name, str) or not isinstance(signal, str):
            continue
        if signal.strip().split()[0] in KNOWN_EXEMPT_COMMANDS:
            continue  # 社区共识工具名豁免（O5 first cut：内建白名单）
        fixture_path = fixtures_dir / f"{name}.yaml"
        if not fixture_path.exists():
            warnings.append(
                f"dimension[{name}] 缺 fixture-set（fixtures/{name}.yaml），"
                f"D9 不通过 → 建议降级 soft（spec D1）"
            )
            continue
        pos_total, neg_total, parse_errors = parse_fixture(fixture_path)
        errors.extend(parse_errors)
        if parse_errors:
            continue
        if pos_total + neg_total < D9_MIN_SAMPLES or pos_total < D9_MIN_PER_SIDE or neg_total < D9_MIN_PER_SIDE:
            warnings.append(
                f"dimension[{name}] fixture-set 样本不足 "
                f"（{pos_total} positive / {neg_total} negative，需 ≥{D9_MIN_SAMPLES} 且单侧 ≥{D9_MIN_PER_SIDE}），"
                f"D9 不通过 → 建议降级 soft"
            )
            continue
        result = run_signal_for_d9(signal, fixture_path, Path(base_dir))
        if result is None:
            warnings.append(
                f"dimension[{name}] signal 命令未实现 D9 模式或执行失败"
                f"（无法解析 JSON 输出）→ 建议降级 soft"
            )
            continue
        if result["total"] != pos_total + neg_total:
            warnings.append(
                f"dimension[{name}] D9 命令 total={result['total']} "
                f"与 fixture 样本数 {pos_total + neg_total} 不一致"
                f"（命令未跑全样本）→ 建议降级 soft"
            )
            continue
        pos_hit_rate = result["positive_hit"] / pos_total
        neg_reject_rate = result["negative_reject"] / neg_total
        if pos_hit_rate < D9_HIT_THRESHOLD or neg_reject_rate < D9_HIT_THRESHOLD:
            warnings.append(
                f"dimension[{name}] fixture-set 命中不足"
                f"（positive {pos_hit_rate:.0%} / negative {neg_reject_rate:.0%}，"
                f"需 ≥{D9_HIT_THRESHOLD:.0%}）→ 建议降级 soft"
            )
    return errors, warnings


def _formula_syntax_ok(formula):
    try:
        eval_formula(formula, 0.0, 0.0)
        return True
    except Exception:
        return False


def validate_config(data):
    """校验 config.yaml 结构。返回错误列表（空 = 通过）。"""
    errors = []
    if not isinstance(data, dict):
        return ["config.yaml 必须是 YAML 映射"]

    for key in REQUIRED_CONFIG_KEYS:
        if key not in data:
            errors.append(f"config.yaml 缺必填段 {key}")
    for key in ("target_path", "writer", "judge"):
        value = data.get(key)
        if key in data and (not isinstance(value, str) or not value):
            errors.append(f"config.yaml.{key} 必须是非空字符串")

    automations = data.get("automations")
    if isinstance(automations, dict):
        timeout = automations.get("iter_timeout_minutes")
        if timeout is not None and (not isinstance(timeout, (int, float)) or timeout <= 0):
            errors.append("automations.iter_timeout_minutes 必须是正数")
    elif "automations" in data:
        errors.append("automations 必须是映射")

    program = data.get("program")
    if not isinstance(program, dict):
        errors.append("program 必须是映射（objective + constraints）")
    else:
        objective = program.get("objective")
        if not isinstance(objective, str) or not objective:
            errors.append("program.objective 必须是非空字符串")
        constraints = program.get("constraints")
        if not isinstance(constraints, list) or not constraints:
            errors.append("program.constraints 必须是非空列表")
        else:
            for i, c in enumerate(constraints):
                if not isinstance(c, str) or not c:
                    errors.append(f"program.constraints[{i}] 必须是非空字符串")

    aggregate = data.get("aggregate")
    if aggregate is not None:
        if not isinstance(aggregate, dict):
            errors.append("aggregate 必须是映射（若出现）")
        elif aggregate.get("final") is not None and not isinstance(aggregate.get("final"), dict):
            errors.append("config.yaml.aggregate.final 必须是映射（若出现）")
    return errors


def effective_aggregate(scoring, config):
    """config.yaml 的 aggregate 段覆盖 scoring.yaml 的 aggregate。

    覆盖语义（spec D3「formula 可被 config.yaml 覆盖」）：只有 final 段
    （典型 final.formula）可被覆盖；hard / soft 归约方法继承 scoring.yaml。
    """
    agg = copy.deepcopy(scoring.get("aggregate")) if isinstance(scoring, dict) else None
    override = config.get("aggregate") if isinstance(config, dict) else None
    if not isinstance(agg, dict):
        agg = {}
    if isinstance(override, dict):
        final = agg.get("final")
        if not isinstance(final, dict):
            final = {}
        override_final = override.get("final")
        if isinstance(override_final, dict):
            final.update(override_final)
        agg["final"] = final
    return agg


def load_and_validate(scoring_path=DEFAULT_SCORING, config_path=DEFAULT_CONFIG):
    """读文件 + 解析 + 校验。返回错误列表（空 = 通过）。"""
    errors = []
    scoring = config = None
    for path, label in ((scoring_path, "scoring.yaml"), (config_path, "config.yaml")):
        try:
            parsed = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        except FileNotFoundError:
            errors.append(f"文件不存在: {path}")
            continue
        except yaml.YAMLError as exc:
            errors.append(f"{label} 非法 YAML: {exc}")
            continue
        if label == "scoring.yaml":
            scoring = parsed
        else:
            config = parsed

    if scoring is not None:
        errors.extend(validate_scoring(scoring))
    if config is not None:
        errors.extend(validate_config(config))
    return errors


def main(argv=None):
    argv = list(argv if argv is not None else sys.argv[1:])
    scoring_path = argv[0] if len(argv) > 0 else DEFAULT_SCORING
    config_path = argv[1] if len(argv) > 1 else DEFAULT_CONFIG
    errors = load_and_validate(scoring_path, config_path)
    d9_warnings = []
    # D9 门禁（v0.2 spec D1）：load_and_validate 保持纯校验签名，
    # 这里单独读 scoring 跑 validate_d9（结构错误已由 load_and_validate 报告）。
    try:
        scoring = yaml.safe_load(Path(scoring_path).read_text(encoding="utf-8"))
        if isinstance(scoring, dict):
            d9_errors, d9_warnings = validate_d9(
                scoring, Path(scoring_path).resolve().parent
            )
            errors.extend(d9_errors)
    except (yaml.YAMLError, OSError):
        pass  # 已在 load_and_validate 中报告
    if errors:
        for err in errors:
            print(f"ERROR: {err}", file=sys.stderr)
        print(f"配置校验失败：{len(errors)} 个错误", file=sys.stderr)
        sys.exit(1)
    for warn in d9_warnings:
        print(f"WARNING: {warn}")
    print("OK: scoring.yaml + config.yaml 校验通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
