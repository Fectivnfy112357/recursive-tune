"""v0.3 spec D1 + D1.5 · Sub-agents 派发骨架件。

骨架件职责（薄）：
- recipe schema 校验（落 D1.5 字段层：agents 长度 = 3、五字段齐备、name 唯一、state_rw 不互冲）
- spawn envelope 构造（5 字段 + status 枚举 + error_code 状态对齐）
- 子 agent 执行（bash -c prompt_path；rc != 0 → E_AGENT_FAIL 且不落产物）
- coordinator 聚合原子性（任一失败 → 全 agent 产物清理 + 不调 ratchet_fn）

设计纪律（v0.3 spec D1 落点）：
- 不规定协作模式（recipe 文件决定 spawn 顺序）
- ratchet 复用 v0.2 git commit 流程（coordinate 的 ratchet_fn 由调用方注入；
  spec 不在本模块写"git 提交"细节，保持薄骨架）
- 不引入断点续跑（spec D1 "必入约束"），失败 = 从头跑
- cacheable=true + output 已存在 → status=cached，duration_ms=0，不 spawn
"""

from pathlib import Path
import subprocess
import sys
import time

# --- 错误码（D1.5：错误码 ≥3 起步） ---
E_AGENT_FAIL = "E_AGENT_FAIL"
E_RECIPE_INVALID = "E_RECIPE_INVALID"
E_STATE_RACE = "E_STATE_RACE"

# --- spawn envelope 状态（D1.5 a：status 枚举） ---
STATUS_OK = "ok"
STATUS_FAILED = "failed"
STATUS_CACHED = "cached"
_STATUS_ENUM = {STATUS_OK, STATUS_FAILED, STATUS_CACHED}

# --- recipe agent 必填字段（D1.5 字段层） ---
REQUIRED_AGENT_KEYS = ("name", "profile", "prompt_path", "state_rw", "cacheable")
EXPECTED_AGENT_COUNT = 3  # spec D2：恰好 3 agent

# 子 agent 执行超时（spec 不锁秒数，给个上界防 hang）
_SPAWN_TIMEOUT_SEC = 300


def validate_recipe(recipe):
    """校验 recipe。返回 (errors, warnings)。

    errors 含错误码 token（E_RECIPE_INVALID / E_STATE_RACE），便于测试断言
    与上层日志聚合（v0.3 spec D1.5 b）。
    """
    errors = []
    warnings = []

    if not isinstance(recipe, dict):
        return [f"{E_RECIPE_INVALID} recipe 必须是 YAML 映射"], warnings

    agents = recipe.get("agents")
    if not isinstance(agents, list):
        return [f"{E_RECIPE_INVALID} recipe.agents 必须是列表"], warnings
    if not agents:
        return [f"{E_RECIPE_INVALID} recipe.agents 不能为空"], warnings

    if len(agents) != EXPECTED_AGENT_COUNT:
        errors.append(
            f"{E_RECIPE_INVALID} agents 长度 = {len(agents)}，spec D2 要求恰好 {EXPECTED_AGENT_COUNT}"
        )
        # 长度错时后续字段检查仍继续（errors 累加），但聚合步骤必拒

    seen_names = set()
    seen_state_paths = {}  # state_rw[0] → agent name（用于 race 检测）
    for i, agent in enumerate(agents):
        prefix = f"agents[{i}]"
        if not isinstance(agent, dict):
            errors.append(f"{E_RECIPE_INVALID} {prefix} 必须是映射")
            continue
        for key in REQUIRED_AGENT_KEYS:
            if key not in agent:
                errors.append(f"{E_RECIPE_INVALID} {prefix} 缺 {key}")

        name = agent.get("name")
        if isinstance(name, str) and name:
            if name in seen_names:
                errors.append(f"{E_RECIPE_INVALID} agents 重名: {name!r}")
            seen_names.add(name)
        elif "name" in agent:
            errors.append(f"{E_RECIPE_INVALID} {prefix}.name 必须是非空字符串")

        state_rw = agent.get("state_rw")
        if isinstance(state_rw, list) and state_rw:
            first_path = state_rw[0]
            if isinstance(first_path, str) and first_path:
                if first_path in seen_state_paths:
                    errors.append(
                        f"{E_STATE_RACE} agents {seen_state_paths[first_path]!r} 与 {name!r} "
                        f"共享 state_rw[0] = {first_path!r}"
                    )
                else:
                    seen_state_paths[first_path] = name

    return errors, warnings


def make_envelope(agent, status, output_path, duration_ms, error_code):
    """构造 spawn 返回信封（D1.5 a：5 字段齐备）。

    仅校验 status 在合法枚举内；status=failed 时 error_code 应非空，但
    不在本构造器强制（薄骨架：调用方 spawn_agent 负责语义不变式，构造器
    只负责字段形状）。
    """
    if status not in _STATUS_ENUM:
        raise ValueError(f"status 必须是 {sorted(_STATUS_ENUM)} 之一，收到 {status!r}")
    return {
        "agent": agent,
        "status": status,
        "output_path": str(output_path),
        "duration_ms": int(duration_ms),
        "error_code": error_code,
    }


def spawn_agent(agent, state_dir, *, force=False):
    """执行单个子 agent；返回 envelope。

    行为契约（D1.5 + D1）：
    - cacheable=True 且 output_path 已存在且 force=False → status=cached（不 spawn）
    - rc != 0 / 超时 → status=failed / error_code=E_AGENT_FAIL（产物不落 state）
    - rc == 0 → 把 stdout 写入 state_rw[0]

    设计取舍：直接 write_text(rc=0 才写)，不做 tmp+atomic move（薄骨架，
    失败 = 没产物，原子性天然成立）。
    """
    state_dir = Path(state_dir)
    state_rw = agent.get("state_rw") or []
    output_rel = state_rw[0] if state_rw else f"{agent.get('name', 'out')}.txt"
    output_abs = state_dir / output_rel
    output_abs.parent.mkdir(parents=True, exist_ok=True)

    # cache hit（D1 50% 判据的来源：cacheable + output 已存在 → 直接复用）
    if agent.get("cacheable") and not force and output_abs.exists():
        return make_envelope(
            agent.get("name", "?"), STATUS_CACHED, str(output_abs), 0, None
        )

    prompt = agent.get("prompt_path") or ""
    start = time.monotonic()
    try:
        proc = subprocess.run(
            ["bash", "-c", prompt],
            cwd=str(state_dir),
            capture_output=True,
            text=True,
            timeout=_SPAWN_TIMEOUT_SEC,
        )
        rc = proc.returncode
        stdout = proc.stdout or ""
    except subprocess.TimeoutExpired:
        rc = -1
        stdout = ""
    except OSError:
        rc = -1
        stdout = ""
    duration_ms = int((time.monotonic() - start) * 1000)

    if rc != 0:
        # 失败：产物不落 state（spec D1.5 原子性）
        return make_envelope(
            agent.get("name", "?"), STATUS_FAILED, str(output_abs),
            duration_ms, E_AGENT_FAIL,
        )

    output_abs.write_text(stdout, encoding="utf-8")
    return make_envelope(
        agent.get("name", "?"), STATUS_OK, str(output_abs), duration_ms, None
    )


def coordinate(recipe, state_dir, ratchet_fn=None):
    """按 recipe 顺序 spawn 所有 agent，聚合产出。

    入口先 validate_recipe（gate）：recipe 不合法（长度错 / race / 缺字段）
    → 直接 committed=False，不动 state、不调 ratchet_fn（HEAD 未动）。

    返回 {"envelopes": [...], "committed": bool}。
    - 任一 envelope.status == failed → committed=False
      - 清理所有 agent 已写的产物（保守：spec D1.5 原子性要求"聚合失败不落 state"）
      - 不调 ratchet_fn（HEAD 未动）
    - 全 ok/cached → committed=True，调 ratchet_fn()（ratchet 提交由调用方决定；
      v0.3 不在本模块写 git commit 细节，调用方注入即可复用 v0.2 iter.sh 流程）
    """
    state_dir = Path(state_dir)
    errs, _ = validate_recipe(recipe)
    if errs:
        return {"envelopes": [], "committed": False, "errors": errs}

    envelopes = []
    for agent in recipe.get("agents", []):
        env = spawn_agent(agent, state_dir)
        envelopes.append(env)
        if env["status"] == STATUS_FAILED:
            # 聚合失败 → 清理所有 agent 已写产物 + 不调 ratchet_fn
            for e in envelopes:
                p = Path(e["output_path"])
                if p.exists():
                    p.unlink()
            return {"envelopes": envelopes, "committed": False}

    # 全成功（含 cached）→ 提交 ratchet
    if ratchet_fn is not None:
        ratchet_fn()
    return {"envelopes": envelopes, "committed": True}


def main(argv=None):
    """最小 CLI：打印一个合法 recipe 的 validator 结果（便于手工 smoke test）。

    用法: python scripts/subagents.py <recipe.yaml>
    """
    argv = list(argv if argv is not None else sys.argv[1:])
    if not argv:
        print("usage: python scripts/subagents.py <recipe.yaml>", file=sys.stderr)
        return 2
    import yaml  # 局部依赖，validator 本身只接 dict
    try:
        recipe = yaml.safe_load(Path(argv[0]).read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        print(f"ERROR: 读 recipe 失败: {exc}", file=sys.stderr)
        return 1
    errs, warns = validate_recipe(recipe)
    if errs:
        for e in errs:
            print(f"ERROR: {e}", file=sys.stderr)
        return 1
    for w in warns:
        print(f"WARNING: {w}")
    print(f"OK: recipe 校验通过（{len(recipe.get('agents', []))} agents）")
    return 0


if __name__ == "__main__":
    sys.exit(main())