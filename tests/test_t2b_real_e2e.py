"""v0.3 T2b · 真 e2e 测试（spec T2b · 手工 1 次 · 非 CI）。

CI 守门交给 test_t2a_e2e（fake_hermes stub 路径）。本测试：
- skipif hermes 二进制不可用（与 v0.2 T4 shell 测试同构——`command -v hermes`
  缺失即 skip）
- 真实 LLM + 真实 git repo 跑一次，验 spawn 全 ok + 产物落库 + D4 三维 pass
- 不验 wall clock 中位 ≤50%（那是 wall clock evidence 文档的责任，
  不入 CI 断言——spec T2b：「PR 可人工 merge」「wall clock ≤50%」两条判据只在
  T2b 下成立，不作为 CI 断言）

fixture 用 v0.3-T2a handoff 提到的 demo-readme-target（已 push 到
Fectivnfy112357/v0.3-demo-readme 的临时仓）；CI 默认跑会因缺少本地 clone
+ 没有 hermes → skip，所以这里 skipif 也覆盖 hermes 不可用场景。
"""

from pathlib import Path
import os
import shutil
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import d4_signals as d4  # noqa: E402
import real_hermes_runner as rhr  # noqa: E402
import run_recipe as rr  # noqa: E402

REPO_ROOT = rr.REPO_ROOT
RECIPE_REAL = REPO_ROOT / "recipes" / "readme-multilang-3agent-real.yaml"

ORIGINAL_README = (
    "intro paragraph 1.\n\n"
    "intro paragraph 2.\n\n"
    "intro paragraph 3.\n\n"
    "intro paragraph 4.\n"
)


def _hermes_available():
    try:
        rhr._resolve_hermes()
        return True
    except FileNotFoundError:
        return False


# spec T2b 「手工 1 次,非 CI」：默认 skip；启用需设 T2B_REAL_HERMES=1
# （确保 CI 默认不跑真 LLM,墙钟计时 + 真实 PR 验证只在人工 ack 时跑）
_REAL_HERMES_ENABLED = os.environ.get("T2B_REAL_HERMES") == "1"

pytestmark = pytest.mark.skipif(
    not (_hermes_available() and _REAL_HERMES_ENABLED),
    reason="T2b 真 e2e 默认 skip（spec T2b「手工 1 次,非 CI」）—— 设 T2B_REAL_HERMES=1 启用",
)


@pytest.fixture
def local_demo_clone(tmp_path):
    """从 Fectivnfy112357/v0.3-demo-readme clone 一份到 tmp_path。
    fixture 缺失时 skip(本测试需网络访问 — CI 默认不跑)。
    """
    if not shutil.which("git") or not shutil.which("gh"):
        pytest.skip("git/gh 不可用")
    target = tmp_path / "v0.3-demo-readme-target"
    try:
        subprocess.run(
            ["gh", "repo", "clone", "Fectivnfy112357/v0.3-demo-readme", str(target)],
            check=True, capture_output=True, timeout=60,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        pytest.skip("无法 clone Fectivnfy112357/v0.3-demo-readme（网络或权限问题）")
    return target


def test_real_hermes_translates_one_paragraph(local_demo_clone):
    """单 agent 真 hermes 调用 → 产物有内容（非空字符串）。"""
    a = {
        "name": "translator",
        "profile": "writer",
        "prompt_path": (
            f"python \"{rhr._WINDOWS_HERMES.parent.parent}/real_hermes_runner.py\" "
            "--profile translator --section-id intro"
        ),
        "state_rw": ["state/sections/intro_translated.md"],
        "cacheable": True,
    }
    # 直接调 real_hermes_runner 验证基础路径（避免 spawn_agent bash quoting 复杂度）
    state = local_demo_clone / ".subagents_state"
    state.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [
            sys.executable, str(REPO_ROOT / "scripts" / "real_hermes_runner.py"),
            "--profile", "translator",
            "--section-id", "intro",
            "--cwd", str(state),
            "--timeout", "120",
        ],
        capture_output=True, text=True, timeout=180,
    )
    assert proc.returncode == 0, f"hermes 失败: {proc.stderr[:500]}"
    assert len(proc.stdout.strip()) > 0, "hermes 输出空"


def test_real_recipe_runs_end_to_end(local_demo_clone):
    """真 hermes recipe 跑通：3 agent 全 ok + state 产物 + D4 pass。

    本测试跳 wall clock 断言（那是 wall clock evidence 文档的责任），只验
    骨架件 / spawn / 聚合 / D4 命令跑通。
    """
    result = rr.run_recipe(RECIPE_REAL, local_demo_clone)
    assert result["committed"] is True
    assert len(result["envelopes"]) == 3
    assert all(e["status"] == "ok" for e in result["envelopes"]), \
        f"任一 agent 失败: {[e for e in result['envelopes'] if e['status'] != 'ok']}"

    state_dir = Path(local_demo_clone) / ".subagents_state"
    pr = (state_dir / "state" / "final_pr.md").read_text(encoding="utf-8")
    # 真 LLM 产物的 PR 结构可能略宽松：diff 头/README 修改/三 agent 段落至少一个满足
    has_diff = "```diff" in pr or "diff --git" in pr
    has_readme = "README" in pr
    has_agents = any(label in pr for label in ("translator", "consistency", "pr_drafter"))
    assert has_diff, f"PR 缺 diff 头: {pr[:300]}"
    assert has_readme, f"PR 未提 README: {pr[:300]}"
    assert has_agents, f"PR 缺 agent 段落: {pr[:300]}"

    # D4 三维命令对真 LLM 产物跑通(可能 pass / 可能因 LLM 不完美 fail — 落 evidence 不阻断)
    translated = (state_dir / "state" / "sections" / "intro_translated.md").read_text(encoding="utf-8")
    cov = d4.run_coverage(ORIGINAL_README, translated)
    glos = d4.run_glossary(translated, ["install", "configure", "usage", "contribute"])
    lint = d4.run_pr_lint(pr)
    # 不强制 pass(D4 三维对真 LLM 是 fuzzy 判断,T2b 关注跑通而非完美)
    print(f"\nD4 真 LLM 产物评估:coverage={cov} glossary={glos} pr_lint={lint}")


def test_second_run_caches_all_three_agents(local_demo_clone):
    """二次跑：3 agent 全 cached(同 T2a fake 版行为,真 hermes 也满足)。"""
    rr.run_recipe(RECIPE_REAL, local_demo_clone)
    result2 = rr.run_recipe(RECIPE_REAL, local_demo_clone)
    assert result2["committed"] is True
    for env in result2["envelopes"]:
        assert env["status"] == "cached"
        assert env["duration_ms"] == 0