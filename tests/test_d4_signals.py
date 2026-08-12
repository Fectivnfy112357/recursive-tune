"""v0.3 T2a · D4 三维 hard signal 命令测试（spec D4）。

三维命令（全部 hard，命令可量化）：
- coverage: 译文段落数 / 原文段落数 ≥95%
- glossary: 译文含 glossary 关键词率 ≥90%
- pr_lint: PR 结构合法（diff 头 / README 修改 / 三 agent 段落齐）

返回协议（v0.2 D9 A-min）：exit 0 + JSON {"total": N, "positive_hit": N, "negative_reject": N}。
本测试不直接验 JSON 协议（fixture 不适用 D9,spec D4 明确占位）—— T2a 只验
"命令可量化、出数值"。
"""

from pathlib import Path
import json
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import d4_signals as d4  # noqa: E402


# ---------- helpers ----------

GLOSSARY = ["install", "configure", "usage", "contribute"]

ORIGINAL_README = (
    "intro paragraph 1.\n\n"
    "intro paragraph 2.\n\n"
    "intro paragraph 3.\n\n"
    "intro paragraph 4.\n"
)

# 译文 = 4 段 + 每段 1 关键词（覆盖度 100% + glossary 100%）
TRANSLATED_OK = (
    "Section intro (translated)\n\n"
    "paragraph one with term install\n\n"
    "paragraph two with term configure\n\n"
    "paragraph three with term usage\n\n"
    "paragraph four with term contribute\n"
)

# 译文 = 3 段（覆盖度 75%，应返 fail）
TRANSLATED_LOW_COVERAGE = (
    "paragraph one\n\n"
    "paragraph two\n\n"
    "paragraph three\n"
)

# 译文 = 4 段但缺 2 个关键词（glossary 50%，应返 fail）
TRANSLATED_LOW_GLOSSARY = (
    "Section intro\n\n"
    "paragraph one with term install\n\n"
    "paragraph two with term configure\n\n"
    "paragraph three without keywords\n\n"
    "paragraph four without keywords\n"
)

PR_OK = (
    "```diff\n"
    "--- a/README.md\n"
    "+++ b/README.md\n"
    "@@ -1,4 +1,4 @@\n"
    "-old paragraph 1\n"
    "+new paragraph 1\n"
    "-old paragraph 2\n"
    "+new paragraph 2\n"
    "```\n"
    "\n"
    "## PR body\n"
    "\n"
    "translator: produced 4 paragraphs\n"
    "consistency: all terms verified\n"
    "pr_drafter: assembled diff\n"
)

PR_NO_DIFF_HEADER = (
    "Updated README.md\n\n"
    "translator: produced 4 paragraphs\n"
    "consistency: all terms verified\n"
    "pr_drafter: assembled diff\n"
)

PR_NOT_README = (
    "```diff\n"
    "--- a/CHANGELOG.md\n"
    "+++ b/CHANGELOG.md\n"
    "@@ -1,1 +1,1 @@\n"
    "-old\n"
    "+new\n"
    "```\n"
    "\n"
    "translator: produced\n"
    "consistency: verified\n"
    "pr_drafter: done\n"
)

PR_MISSING_AGENT_SECTION = (
    "```diff\n"
    "--- a/README.md\n"
    "+++ b/README.md\n"
    "@@ -1,1 +1,1 @@\n"
    "-old\n"
    "+new\n"
    "```\n"
    "\n"
    "## PR body\n"
    "\n"
    "translator: produced\n"
    "pr_drafter: done\n"
)


# ---------- coverage（覆盖度 ≥95% 段落） ----------

def test_coverage_passes_when_full():
    """4/4 段落 → 100% ≥95% → pass。"""
    result = d4.run_coverage(ORIGINAL_README, TRANSLATED_OK)
    assert result["pass"] is True
    assert result["ratio"] == 1.0


def test_coverage_fails_below_threshold():
    """3/4 段落 → 75% <95% → fail。"""
    result = d4.run_coverage(ORIGINAL_README, TRANSLATED_LOW_COVERAGE)
    assert result["pass"] is False
    assert result["ratio"] == 0.75


def test_coverage_handles_empty_translation():
    """译文空 → 0/4 → fail（不退化）。"""
    result = d4.run_coverage(ORIGINAL_README, "")
    assert result["pass"] is False
    assert result["ratio"] == 0.0


# ---------- glossary（术语一致性 ≥90%） ----------

def test_glossary_passes_when_all_terms_found():
    """4/4 关键词 → 100% ≥90% → pass。"""
    result = d4.run_glossary(TRANSLATED_OK, GLOSSARY)
    assert result["pass"] is True
    assert result["ratio"] == 1.0


def test_glossary_fails_below_threshold():
    """2/4 关键词 → 50% <90% → fail。"""
    result = d4.run_glossary(TRANSLATED_LOW_GLOSSARY, GLOSSARY)
    assert result["pass"] is False
    assert result["ratio"] == 0.5


def test_glossary_is_case_insensitive():
    """关键词匹配大小写不敏感（PR body / 译文常见大小写混用）。"""
    text = "Paragraph with INSTALL and Configure."
    result = d4.run_glossary(text, ["install", "configure"])
    assert result["pass"] is True
    assert result["ratio"] == 1.0


# ---------- pr_lint（PR 结构合法） ----------

def test_pr_lint_passes_valid_pr():
    """合法 PR 结构（diff 头 + README 修改 + 三 agent 段落） → pass。"""
    result = d4.run_pr_lint(PR_OK)
    assert result["pass"] is True
    assert result["issues"] == []


def test_pr_lint_fails_without_diff_header():
    """缺 ```diff 头 → fail。"""
    result = d4.run_pr_lint(PR_NO_DIFF_HEADER)
    assert result["pass"] is False
    assert any("diff" in i.lower() for i in result["issues"])


def test_pr_lint_fails_when_not_readme():
    """diff 改的不是 README.md → fail（spec D2 锁定 README 多语种化）。"""
    result = d4.run_pr_lint(PR_NOT_README)
    assert result["pass"] is False
    assert any("README" in i for i in result["issues"])


def test_pr_lint_fails_when_missing_agent_section():
    """PR body 缺 agent 段落(translator / consistency / pr_drafter)→ fail。"""
    result = d4.run_pr_lint(PR_MISSING_AGENT_SECTION)
    assert result["pass"] is False
    assert any("consistency" in i for i in result["issues"])


# ---------- CLI 协议（v0.2 D9 A-min：JSON 输出 + exit 0） ----------

def test_cli_coverage_writes_json(tmp_path, capsys):
    """CLI 模式：覆盖度信号 → exit 0 + JSON stdout（A-min 协议）。"""
    original = tmp_path / "original.md"
    translated = tmp_path / "translated.md"
    original.write_text(ORIGINAL_README, encoding="utf-8")
    translated.write_text(TRANSLATED_OK, encoding="utf-8")

    rc = d4.main_cli([
        "coverage",
        "--original", str(original),
        "--translated", str(translated),
    ])
    out = capsys.readouterr().out.strip()
    assert rc == 0
    data = json.loads(out)
    assert "ratio" in data
    assert data["ratio"] == 1.0


def test_cli_glossary_writes_json(tmp_path, capsys):
    """CLI 模式：术语信号 → exit 0 + JSON stdout。"""
    translated = tmp_path / "translated.md"
    translated.write_text(TRANSLATED_OK, encoding="utf-8")
    glossary = tmp_path / "glossary.txt"
    glossary.write_text("\n".join(GLOSSARY), encoding="utf-8")

    rc = d4.main_cli([
        "glossary",
        "--translated", str(translated),
        "--glossary", str(glossary),
    ])
    out = capsys.readouterr().out.strip()
    assert rc == 0
    data = json.loads(out)
    assert data["ratio"] == 1.0


def test_cli_pr_lint_writes_json(tmp_path, capsys):
    """CLI 模式：PR 结构信号 → exit 0 + JSON stdout。"""
    pr = tmp_path / "final_pr.md"
    pr.write_text(PR_OK, encoding="utf-8")

    rc = d4.main_cli([
        "pr_lint",
        "--pr", str(pr),
    ])
    out = capsys.readouterr().out.strip()
    assert rc == 0
    data = json.loads(out)
    assert data["pass"] is True
    assert data["issues"] == []