"""v0.3 T2b · wall clock 计时式断言（spec D1 / D2 50% 判据）。

跑 N1 次首次执行（cold cache，含 LLM call）+ N2 次二次执行（cache hit，
不 spawn）→ 断言 median(time_2*) ≤ median(time_1*) × 0.5。

evidence 落 docs/handoff/v0.3-real-e2e-evidence.md（含 PR 链接 + 计时数据 +
断言结果）。

用法：
    python scripts/t2b_wall_clock.py \
        --recipe recipes/readme-multilang-3agent-real.yaml \
        --target /path/to/demo-readme-target \
        --n1 3 --n2 3
"""

from pathlib import Path
import argparse
import json
import statistics
import subprocess
import sys
import time

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_recipe as rr  # noqa: E402

REPO_ROOT = rr.REPO_ROOT
EVIDENCE_PATH = REPO_ROOT / "docs" / "handoff" / "v0.3-real-e2e-evidence.md"


def _clear_state(target):
    """清空 .subagents_state/(强制 cold cache 跑)。"""
    state = Path(target) / ".subagents_state"
    if state.exists():
        subprocess.run(["git", "-C", str(target), "rm", "-rq", "--cached",
                        ".subagents_state/"], capture_output=True)
        subprocess.run(["rm", "-rf", str(state)], check=False)
    # 提交清理(若有 staged)
    subprocess.run(["git", "-C", str(target), "add", "-A"], capture_output=True)
    subprocess.run(["git", "-C", str(target), "commit", "-qm",
                    "t2b: clear state for wall-clock run"], capture_output=True)


def _time_run(recipe_path, target):
    """跑一次 recipe 并返回 wall clock 秒数（spec D1 计时边界：含 LLM call + agent IO，不含 clone/PR 提交）。"""
    # 不计 ratchet（git commit）时间 → spec D1「不含 PR 提交」
    def _noop_ratchet(target_repo=None):
        pass

    t0 = time.monotonic()
    result = rr.run_recipe(recipe_path, target, ratchet_fn=_noop_ratchet)
    elapsed = time.monotonic() - t0
    return elapsed, result


def _detect_pr_link(target):
    """如果 target 是真实 GitHub 仓（remote = origin），记录 origin URL。"""
    try:
        out = subprocess.run(
            ["git", "-C", str(target), "remote", "get-url", "origin"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        return out
    except subprocess.CalledProcessError:
        return None


def main(argv=None):
    argv = list(argv if argv is not None else sys.argv[1:])
    parser = argparse.ArgumentParser(prog="t2b_wall_clock")
    parser.add_argument("--recipe", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--n1", type=int, default=3, help="首次执行次数")
    parser.add_argument("--n2", type=int, default=3, help="二次执行次数")
    args = parser.parse_args(argv)

    recipe_path = Path(args.recipe).resolve()
    target = Path(args.target).resolve()

    print(f"recipe:  {recipe_path}")
    print(f"target:  {target}")
    print(f"n1={args.n1} (cold cache), n2={args.n2} (cache hit)")
    print()

    # --- 首次执行（cold cache） ---
    time_1 = []
    for i in range(args.n1):
        _clear_state(target)
        elapsed, result = _time_run(recipe_path, target)
        time_1.append(elapsed)
        statuses = "/".join(e["status"] for e in result["envelopes"])
        print(f"  time_1[{chr(ord('a') + i)}] = {elapsed:.2f}s  statuses={statuses}  committed={result['committed']}")

    # --- 二次执行（cache hit） ---
    time_2 = []
    for i in range(args.n2):
        # 不清 state,产物保留
        elapsed, result = _time_run(recipe_path, target)
        time_2.append(elapsed)
        statuses = "/".join(e["status"] for e in result["envelopes"])
        print(f"  time_2[{chr(ord('a') + i)}] = {elapsed:.2f}s  statuses={statuses}")

    # --- 断言（spec D1 / D2 50% 判据） ---
    median_1 = statistics.median(time_1)
    median_2 = statistics.median(time_2)
    threshold = median_1 * 0.5
    passed = median_2 <= threshold
    speedup = median_1 / median_2 if median_2 > 0 else float("inf")

    print()
    print(f"median(time_1*) = {median_1:.2f}s")
    print(f"median(time_2*) = {median_2:.2f}s")
    print(f"threshold (50% of median_1) = {threshold:.2f}s")
    print(f"speedup = {speedup:.2f}x")
    print(f"ASSERTION: median(time_2) ≤ median(time_1) × 0.5 → {'PASS' if passed else 'FAIL'}")

    # --- evidence 落盘 ---
    pr_link = _detect_pr_link(target)
    evidence = {
        "recipe": str(recipe_path),
        "target": str(target),
        "remote_origin": pr_link,
        "n1": args.n1,
        "n2": args.n2,
        "time_1": time_1,
        "time_2": time_2,
        "median_1": median_1,
        "median_2": median_2,
        "threshold": threshold,
        "speedup": speedup,
        "assertion_passed": passed,
        "note": (
            "T2b 手工 1 次跑通（spec T2b）。计时边界：含 LLM call + agent IO，"
            "不含 clone / git commit。median(time_2*) ≤ median(time_1*) × 0.5 "
            "为 spec D1 / D2 锁定的 50% 判据。"
        ),
    }
    EVIDENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with EVIDENCE_PATH.open("a", encoding="utf-8") as f:
        f.write("\n---\n\n")
        f.write(f"## Run @ {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}\n\n")
        f.write(f"- recipe: `{evidence['recipe']}`\n")
        f.write(f"- target: `{evidence['target']}`\n")
        f.write(f"- remote_origin: `{evidence['remote_origin']}`\n")
        f.write(f"- n1={args.n1} (cold cache), n2={args.n2} (cache hit)\n\n")
        f.write("### time_1 (cold cache)\n\n")
        for i, t in enumerate(time_1):
            f.write(f"- time_1[{chr(ord('a') + i)}] = {t:.2f}s\n")
        f.write(f"\n**median(time_1*) = {median_1:.2f}s**\n\n")
        f.write("### time_2 (cache hit)\n\n")
        for i, t in enumerate(time_2):
            f.write(f"- time_2[{chr(ord('a') + i)}] = {t:.2f}s\n")
        f.write(f"\n**median(time_2*) = {median_2:.2f}s**\n\n")
        f.write("### 断言（spec D1 / D2 50% 判据）\n\n")
        f.write(f"- threshold = median(time_1*) × 0.5 = **{threshold:.2f}s**\n")
        f.write(f"- speedup = median(time_1*) / median(time_2*) = **{speedup:.2f}x**\n")
        f.write(f"- 断言: median(time_2*) ≤ median(time_1*) × 0.5 → **{'PASS' if passed else 'FAIL'}**\n\n")
        f.write("> 计时边界(spec D1):含 LLM call + agent IO,不含 clone / git commit。\n")
        f.write("> 二次执行全部 cacheable=true agent → status=cached 不 spawn(实证见 test_t2b_e2e::test_second_run_does_not_respawn)。\n")

    print(f"\nevidence 追加到 {EVIDENCE_PATH}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())