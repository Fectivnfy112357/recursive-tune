"""v0.3 T2b · 单次 wall-clock run helper（atomic per-run 模式）。

替代 t2b_wall_clock.py 的「一次性跑 6 次」模式——拆成 atomic 单元：
- 每次 Bash 调用只跑 1 次 run（cold 或 cached），落 JSON
- 多次 Bash 串接 → 6 runs → 调 t2b_aggregate.py 算 median + 写 evidence

避免单 Bash timeout (120s/600s) 截断整 6 runs 链。

用法：
    python scripts/t2b_one_run.py \
        --recipe recipes/readme-multilang-3agent-real.yaml \
        --target /path/to/demo-readme-target \
        --phase cold --index a \
        --json-out /path/to/t2b_runs.json
"""

from pathlib import Path
import argparse
import json
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_recipe as rr  # noqa: E402

REPO_ROOT = rr.REPO_ROOT


def _clear_state(target):
    state = Path(target) / ".subagents_state"
    if state.exists():
        _subprocess_rm(state)


def _subprocess_rm(path):
    import shutil
    shutil.rmtree(path, ignore_errors=True)


def _time_run(recipe_path, target):
    """跑一次 recipe（不调 ratchet，spec D1 不计 PR 提交）。"""

    def _noop_ratchet(target_repo=None):
        pass

    t0 = time.monotonic()
    result = rr.run_recipe(recipe_path, target, ratchet_fn=_noop_ratchet)
    elapsed = time.monotonic() - t0
    return elapsed, result


def main(argv=None):
    argv = list(argv if argv is not None else sys.argv[1:])
    parser = argparse.ArgumentParser(prog="t2b_one_run")
    parser.add_argument("--recipe", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--phase", required=True, choices=("cold", "cached"))
    parser.add_argument("--index", required=True, help="a/b/c")
    parser.add_argument("--json-out", required=True,
                        help="runs JSON 文件路径（追加本 run）")
    args = parser.parse_args(argv)

    recipe_path = Path(args.recipe).resolve()
    target = Path(args.target).resolve()
    json_out = Path(args.json_out)

    if args.phase == "cold":
        _clear_state(target)

    elapsed, result = _time_run(recipe_path, target)
    record = {
        "phase": args.phase,
        "index": args.index,
        "elapsed_s": round(elapsed, 2),
        "committed": result["committed"],
        "envelopes": [
            {"agent": e["agent"], "status": e["status"],
             "duration_ms": e["duration_ms"], "error_code": e["error_code"]}
            for e in result["envelopes"]
        ],
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
    }

    runs = []
    if json_out.exists():
        try:
            runs = json.loads(json_out.read_text(encoding="utf-8"))
            if not isinstance(runs, list):
                runs = []
        except json.JSONDecodeError:
            runs = []
    runs.append(record)
    json_out.write_text(json.dumps(runs, ensure_ascii=False, indent=2), encoding="utf-8")

    statuses = "/".join(e["status"] for e in result["envelopes"])
    print(f"  [{args.phase}/{args.index}] elapsed={elapsed:.2f}s  committed={result['committed']}  "
          f"statuses={statuses}", flush=True)
    return 0 if result["committed"] else 1


if __name__ == "__main__":
    sys.exit(main())