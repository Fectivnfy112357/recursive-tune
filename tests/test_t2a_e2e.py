"""v0.3 T2a · 机械结构 e2e（spec T2a · CI 跑 · stub LLM）。

覆盖：
- spawn 顺序符合 recipe 声明
- 各 agent 产物按 state_rw 写入正确路径
- coordinator 聚合读出 → envelopes 全 ok
- final_pr.md 结构（diff 头 / README 修改 / 三 agent 段落）— 由 fake_hermes
  deterministic 输出保证，测试直接验产物内容
- D4 三维命令（coverage / glossary / pr_lint）在产物上跑通返回 pass
- cacheable 复用：第二次 run_recipe 时 envelopes 全 cached（status=cached），
  二次不 spawn（fake_hermes 不被调）
- ratchet：首次 git log +1，二次无变更时无 commit（nothing to commit 跳过）

注意：T2a 不验 wall clock 中位 ≤50% 阈值断言（spec D1 留 T2b 真实 e2e）。
"""

from pathlib import Path
import json
import os
import subprocess
import sys
import time

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import d4_signals as d4  # noqa: E402
import run_recipe as rr  # noqa: E402

REPO_ROOT = rr.REPO_ROOT
RECIPE_PATH = REPO_ROOT / "recipes" / "readme-multilang-3agent.yaml"

ORIGINAL_README = (
    "intro paragraph 1.\n\n"
    "intro paragraph 2.\n\n"
    "intro paragraph 3.\n\n"
    "intro paragraph 4.\n"
)


@pytest.fixture
def git_target(tmp_path):
    """裸 git 仓库 + 原文 README（run_recipe 会自动 git init，但 README 需先写）。"""
    target = tmp_path / "target_repo"
    target.mkdir()
    (target / "README.md").write_text(ORIGINAL_README, encoding="utf-8")
    return target


# ---------- spawn 顺序 / 路径 / 聚合 ----------

def test_first_run_spawns_all_three_agents_in_recipe_order(git_target):
    """首次跑：3 agent 全 ok，按 recipe 顺序 spawn。"""
    result = rr.run_recipe(RECIPE_PATH, git_target)
    assert result["committed"] is True
    assert [e["agent"] for e in result["envelopes"]] == ["translator", "consistency", "pr_drafter"]
    for env in result["envelopes"]:
        assert env["status"] == "ok"
        assert env["error_code"] is None
        assert env["duration_ms"] >= 0


def test_first_run_writes_state_rw_paths(git_target):
    """首次跑：state_rw[0] 路径下有产物，且 final_pr.md 含 PR 结构。"""
    rr.run_recipe(RECIPE_PATH, git_target)
    state_dir = Path(git_target) / ".subagents_state"
    assert (state_dir / "state" / "sections" / "intro_translated.md").exists()
    assert (state_dir / "state" / "sections" / "intro_consistency.md").exists()
    assert (state_dir / "state" / "final_pr.md").exists()

    pr = (state_dir / "state" / "final_pr.md").read_text(encoding="utf-8")
    assert "```diff" in pr
    assert "--- a/README.md" in pr
    assert "+++ b/README.md" in pr
    # 三 agent 段落（spec D2 锁定）
    for label in ("translator", "consistency", "pr_drafter"):
        assert label in pr, f"PR body 缺 agent 段落: {label}"


def test_first_run_commits_to_git(git_target):
    """首次跑：ratchet 调一次 + git log +1。"""
    result = rr.run_recipe(RECIPE_PATH, git_target)
    assert result["ratchet_calls"] == 1
    assert result["commit_sha"] is not None
    log = subprocess.run(
        ["git", "-C", str(git_target), "log", "--oneline"],
        capture_output=True, text=True, check=True,
    ).stdout
    assert "subagents: recipe=readme-multilang-3agent" in log


# ---------- D4 三维在产物上跑通返回 pass ----------

def test_d4_three_dimensions_pass_on_real_artifacts(git_target):
    """D4 三维命令对 fake_hermes 产物跑通返回 pass：
    - coverage: 译文 5 段（含 section 标题）/ 原文 4 段 = 100%（cap 1.0）
    - glossary: 译文含 4/4 glossary 关键词 = 100%
    - pr_lint: final_pr.md 结构合规
    """
    rr.run_recipe(RECIPE_PATH, git_target)
    state_dir = Path(git_target) / ".subagents_state"

    original = (git_target / "README.md").read_text(encoding="utf-8")
    translated = (state_dir / "state" / "sections" / "intro_translated.md").read_text(encoding="utf-8")
    pr = (state_dir / "state" / "final_pr.md").read_text(encoding="utf-8")

    cov = d4.run_coverage(original, translated)
    assert cov["pass"] is True, f"coverage fail: {cov}"
    assert cov["ratio"] == 1.0

    glossary_path = tmp_glossary_file()  # 写到 tmp_path
    glos = d4.run_glossary(translated, ["install", "configure", "usage", "contribute"])
    assert glos["pass"] is True, f"glossary fail: {glos}"
    assert glos["ratio"] == 1.0

    lint = d4.run_pr_lint(pr)
    assert lint["pass"] is True, f"pr_lint fail: {lint['issues']}"
    assert lint["issues"] == []


def test_d4_cli_json_outputs_match_python_api(git_target, tmp_path, capsys):
    """CLI 协议：d4_signals.py 三个子命令都输出 JSON（v0.2 D9 A-min）。"""
    rr.run_recipe(RECIPE_PATH, git_target)
    state_dir = Path(git_target) / ".subagents_state"

    # coverage CLI
    original_path = git_target / "README.md"
    translated_path = state_dir / "state" / "sections" / "intro_translated.md"
    rc = d4.main_cli([
        "coverage", "--original", str(original_path), "--translated", str(translated_path),
    ])
    out = capsys.readouterr().out.strip()
    assert rc == 0
    data = json.loads(out)
    assert data["pass"] is True and data["ratio"] == 1.0

    # glossary CLI
    glossary_file = tmp_path / "glossary.txt"
    glossary_file.write_text("install\nconfigure\nusage\ncontribute\n", encoding="utf-8")
    rc = d4.main_cli([
        "glossary", "--translated", str(translated_path), "--glossary", str(glossary_file),
    ])
    out = capsys.readouterr().out.strip()
    assert rc == 0
    data = json.loads(out)
    assert data["pass"] is True and data["ratio"] == 1.0

    # pr_lint CLI
    pr_path = state_dir / "state" / "final_pr.md"
    rc = d4.main_cli(["pr_lint", "--pr", str(pr_path)])
    out = capsys.readouterr().out.strip()
    assert rc == 0
    data = json.loads(out)
    assert data["pass"] is True and data["issues"] == []


def tmp_glossary_file():  # 实际不创建文件——glossary 参数接受 list 也行
    return None  # noqa  占位


# ---------- cacheable 复用：二次执行命中产物即 status=cached ----------

def test_second_run_caches_all_three_agents(git_target):
    """第二次跑：3 agent 全 status=cached（cacheable=true + output 已存在）。"""
    rr.run_recipe(RECIPE_PATH, git_target)

    # 二次执行：所有 output 已存在 → 全 cached
    result2 = rr.run_recipe(RECIPE_PATH, git_target)
    assert result2["committed"] is True  # committed=True 因为 recipe validator 通过；ratchet 在 nothing-to-commit 时跳过 commit
    assert result2["ratchet_calls"] == 1  # ratchet_fn 仍被调一次（coordinate 全 ok/cached 时调）；但 git_commit 在无 staged 变更时跳过 commit
    for env in result2["envelopes"]:
        assert env["status"] == "cached", f"{env['agent']}: {env['status']}"
        assert env["error_code"] is None
        assert env["duration_ms"] == 0


def test_second_run_does_not_respawn(git_target, monkeypatch):
    """第二次跑：fake_hermes 不被调（monitor subprocess.run 调 python fake_hermes.py）。"""
    rr.run_recipe(RECIPE_PATH, git_target)

    # 拦截所有 subprocess.run，统计 fake_hermes 调用次数
    fake_hermes_calls = []
    import subagents
    original_run = subagents.subprocess.run

    def counting_run(*args, **kwargs):
        cmd = args[0] if args else kwargs.get("args", [])
        if cmd and isinstance(cmd, list) and len(cmd) >= 3 and cmd[0] == "bash":
            bash_arg = cmd[2] if len(cmd) > 2 else ""
            if "fake_hermes.py" in bash_arg:
                fake_hermes_calls.append(bash_arg)
        return original_run(*args, **kwargs)

    monkeypatch.setattr(subagents.subprocess, "run", counting_run)

    rr.run_recipe(RECIPE_PATH, git_target)
    assert fake_hermes_calls == [], (
        f"二次执行应全 cached 不 spawn，但 fake_hermes 仍被调: {fake_hermes_calls}"
    )


def test_second_run_no_new_git_commit(git_target):
    """第二次跑：无产物变更 → 无新 commit（ratchet nothing-to-commit 跳过）。"""
    rr.run_recipe(RECIPE_PATH, git_target)
    log_before = subprocess.run(
        ["git", "-C", str(git_target), "rev-list", "--count", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()

    rr.run_recipe(RECIPE_PATH, git_target)
    log_after = subprocess.run(
        ["git", "-C", str(git_target), "rev-list", "--count", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()

    assert log_before == log_after, "二次执行无变更应不产生新 commit"


# ---------- 端到端：recipe 校验 + ratchet + D4 ----------

def test_full_e2e_pipeline_runs_to_completion(git_target):
    """端到端（issue #9 AC 末条）：recipe 跑通 + D4 三维 pass + commit 落库。

    整合 spawn / 聚合 / PR 结构 / D4 / ratchet 五断言于一次完整跑。
    """
    result = rr.run_recipe(RECIPE_PATH, git_target)
    assert result["committed"] is True
    assert len(result["envelopes"]) == 3
    assert all(e["status"] == "ok" for e in result["envelopes"])
    assert result["commit_sha"] is not None

    state_dir = Path(git_target) / ".subagents_state"
    pr = (state_dir / "state" / "final_pr.md").read_text(encoding="utf-8")
    assert "```diff" in pr and "README.md" in pr and "translator" in pr

    # D4 三维在产物上跑通
    original = (git_target / "README.md").read_text(encoding="utf-8")
    translated = (state_dir / "state" / "sections" / "intro_translated.md").read_text(encoding="utf-8")
    assert d4.run_coverage(original, translated)["pass"] is True
    assert d4.run_glossary(translated, ["install", "configure", "usage", "contribute"])["pass"] is True
    assert d4.run_pr_lint(pr)["pass"] is True