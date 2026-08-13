"""v0.3 T2b · wall-clock aggregator（读 per-run JSON 算 median + 写 evidence）。

用法：
    python scripts/t2b_aggregate.py \
        --json-in /path/to/t2b_runs.json \
        --recipe recipes/readme-multilang-3agent-real.yaml \
        --target /path/to/demo-readme-target
"""

from pathlib import Path
import argparse
import json
import statistics
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_recipe as rr  # noqa: E402

REPO_ROOT = rr.REPO_ROOT
EVIDENCE_PATH = REPO_ROOT / "docs" / "handoff" / "v0.3-real-e2e-evidence.md"


def _detect_pr_link(target):
    import subprocess
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
    parser = argparse.ArgumentParser(prog="t2b_aggregate")
    parser.add_argument("--json-in", required=True)
    parser.add_argument("--recipe", required=True)
    parser.add_argument("--target", required=True)
    args = parser.parse_args(argv)

    runs = json.loads(Path(args.json_in).read_text(encoding="utf-8"))
    if not isinstance(runs, list) or len(runs) < 2:
        sys.exit(f"runs JSON 不够：{len(runs) if isinstance(runs, list) else 0}")

    cold = [r for r in runs if r["phase"] == "cold"]
    cached = [r for r in runs if r["phase"] == "cached"]
    cold.sort(key=lambda r: r["index"])
    cached.sort(key=lambda r: r["index"])

    time_1 = [r["elapsed_s"] for r in cold]
    time_2 = [r["elapsed_s"] for r in cached]

    median_1 = statistics.median(time_1)
    median_2 = statistics.median(time_2)
    threshold = median_1 * 0.5
    passed = median_2 <= threshold
    speedup = median_1 / median_2 if median_2 > 0 else float("inf")

    print(f"cold runs:   {time_1}  median={median_1:.2f}s")
    print(f"cached runs: {time_2}  median={median_2:.2f}s")
    print(f"threshold (50% of median_1): {threshold:.2f}s")
    print(f"speedup: {speedup:.2f}x")
    print(f"ASSERTION: median(time_2) ≤ median(time_1) × 0.5 → {'PASS' if passed else 'FAIL'}")

    pr_link = _detect_pr_link(args.target)
    EVIDENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with EVIDENCE_PATH.open("a", encoding="utf-8") as f:
        f.write("\n---\n\n")
        f.write(f"## Run @ {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}\n\n")
        f.write(f"- recipe: `{args.recipe}`\n")
        f.write(f"- target: `{args.target}`\n")
        f.write(f"- remote_origin: `{pr_link}`\n")
        f.write(f"- n1={len(cold)} (cold cache), n2={len(cached)} (cache hit)\n\n")
        f.write("### time_1 (cold cache)\n\n")
        for i, r in enumerate(cold):
            f.write(f"- time_1[{r['index']}] = {r['elapsed_s']:.2f}s  "
                    f"committed={r['committed']}  statuses={','.join(e['status'] for e in r['envelopes'])}\n")
        f.write(f"\n**median(time_1*) = {median_1:.2f}s**\n\n")
        f.write("### time_2 (cache hit)\n\n")
        for i, r in enumerate(cached):
            f.write(f"- time_2[{r['index']}] = {r['elapsed_s']:.2f}s  "
                    f"committed={r['committed']}  statuses={','.join(e['status'] for e in r['envelopes'])}\n")
        f.write(f"\n**median(time_2*) = {median_2:.2f}s**\n\n")
        f.write("### 断言（spec D1 / D2 50% 判据）\n\n")
        f.write(f"- threshold = median(time_1*) × 0.5 = **{threshold:.2f}s**\n")
        f.write(f"- speedup = median(time_1*) / median(time_2*) = **{speedup:.2f}x**\n")
        f.write(f"- 断言: median(time_2*) ≤ median(time_1*) × 0.5 → **{'PASS' if passed else 'FAIL'}**\n\n")
        f.write("> 计时边界(spec D1):含 LLM call + agent IO,不含 clone / git commit。\n")
        f.write("> 二次执行全部 cacheable=true agent → status=cached 不 spawn(实证见 test_t2a_e2e::test_second_run_does_not_respawn)。\n")
        if not passed:
            f.write("\n> ⚠️ **断言 FAIL**：spec D1 50% 阈值未达。常见原因：\n")
            f.write("> - 二次执行仍触发了 LLM 调用(检查 recipe cacheable 字段)\n")
            f.write("> - 单次 LLM 调用波动大(median 仍可能落在阈值附近)\n")
            f.write("> - spawn_agent subprocess overhead 占大头(LLM 已 cache 但 Python 启动 ~30s/agent)\n")
    print(f"\nevidence 追加到 {EVIDENCE_PATH}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())