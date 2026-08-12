"""recursive-tune v0.1 · 配置校验。

校验 scoring.yaml / config.yaml（spec D3 + D8 hard rules），
任何违规直接报错退出——不静默通过。

CLI:  python scripts/validate_config.py [scoring.yaml] [config.yaml]
默认路径: ./scoring.yaml ./config.yaml
"""

from pathlib import Path
import ast
import copy
import operator
import sys

import yaml

DEFAULT_SCORING = "scoring.yaml"
DEFAULT_CONFIG = "config.yaml"
REQUIRED_CONFIG_KEYS = ("target_path", "writer", "judge", "program", "automations")
VALID_TYPES = ("hard", "soft")
ALLOWED_HARD_AGGREGATE = ("arithmetic_mean",)  # v0.1 只用均值（spec D3）
ALLOWED_SOFT_AGGREGATE = ("weighted_mean",)
JUDGE_PROMPT = "judge_prompt"

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
    if errors:
        for err in errors:
            print(f"ERROR: {err}", file=sys.stderr)
        print(f"配置校验失败：{len(errors)} 个错误", file=sys.stderr)
        sys.exit(1)
    print("OK: scoring.yaml + config.yaml 校验通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
