"""v0.3 T2a · D4 三维 hard signal 命令（spec D4）。

三维命令（全部 hard，命令可量化）：
- coverage: 译文段落数 / 原文段落数 ≥95%
- glossary: glossary 关键词在译文中的命中率 ≥90%（大小写不敏感）
- pr_lint: PR 结构合法（diff 头 / README 修改 / 三 agent 段落齐）

D4 fixture 不适用（spec D4 明确占位：C 类产物非固定答案），T2a 不构造
ground truth，只验"命令可量化、出数值"。CLI 输出 JSON {key: value}
（v0.2 D9 A-min 协议的精简版，T2a 不强制 fixture 门槛；T2b 撞真实 e2e
才补 ground truth——触发见 v0.3 OOS）。
"""

from pathlib import Path
import argparse
import json
import re
import sys

# 阈值（spec D4：覆盖度 ≥95%、术语 ≥90%）
COVERAGE_THRESHOLD = 0.95
GLOSSARY_THRESHOLD = 0.90

# 段落分隔：连续空行
_PARAGRAPH_SPLIT = re.compile(r"\n\s*\n+")
# diff 头
_DIFF_FENCE = "```diff"
# 期望的 PR body agent 段落（D2 锁定 3 agent：translator / consistency / pr_drafter）
_REQUIRED_AGENT_LABELS = ("translator", "consistency", "pr_drafter")


def _split_paragraphs(text):
    """按空行分段；过滤空段。"""
    if not text or not text.strip():
        return []
    return [p.strip() for p in _PARAGRAPH_SPLIT.split(text) if p.strip()]


def run_coverage(original_text, translated_text):
    """返回 {pass, ratio, original_n, translated_n}。

    覆盖度 = min(译文/原文, 1.0)：译文多写也算 100% 覆盖，只有译文段落
    数 < 原文时才计入缺口（D4 直觉：原文段落是否被译文"覆盖"，不是译文
    是否"等于"原文）。
    """
    orig = _split_paragraphs(original_text)
    trans = _split_paragraphs(translated_text)
    if not orig:
        return {"pass": False, "ratio": 0.0, "original_n": 0, "translated_n": len(trans)}
    raw = len(trans) / len(orig) if orig else 0.0
    ratio = min(raw, 1.0)
    return {
        "pass": ratio >= COVERAGE_THRESHOLD,
        "ratio": round(ratio, 4),
        "original_n": len(orig),
        "translated_n": len(trans),
    }


def run_glossary(translated_text, glossary):
    """返回 {pass, ratio, hit, total}。关键词命中（大小写不敏感）。"""
    if not glossary:
        return {"pass": False, "ratio": 0.0, "hit": 0, "total": 0}
    text_lower = translated_text.lower()
    hit = sum(1 for term in glossary if term.lower() in text_lower)
    ratio = hit / len(glossary)
    return {
        "pass": ratio >= GLOSSARY_THRESHOLD,
        "ratio": round(ratio, 4),
        "hit": hit,
        "total": len(glossary),
    }


def run_pr_lint(pr_text):
    """检查 PR 结构。返回 {pass, issues}。"""
    issues = []

    if _DIFF_FENCE not in pr_text:
        issues.append(f"缺 diff 头 {_DIFF_FENCE!r}")

    if "--- a/README.md" not in pr_text or "+++ b/README.md" not in pr_text:
        issues.append("diff 修改的不是 README.md（spec D2 锁定 README 多语种化）")

    for label in _REQUIRED_AGENT_LABELS:
        # 容忍 "- translator:" / "translator:" / "**translator**:" 多种格式
        if not re.search(rf"(^|\s|-){re.escape(label)}\s*[:：]", pr_text, re.IGNORECASE):
            issues.append(f"PR body 缺 agent 段落: {label!r}")

    return {"pass": len(issues) == 0, "issues": issues}


def main_cli(argv=None):
    """CLI 入口：coverage | glossary | pr_lint + 对应 args。

    exit 0 = 信号已计算（pass/fail 由 stdout JSON 字段标识，不阻塞；
    与 spec D4「命令型硬指标」一致——硬不硬看语义，不看 exit 码）。
    """
    argv = list(argv if argv is not None else sys.argv[1:])

    parser = argparse.ArgumentParser(prog="d4_signals")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_cov = sub.add_parser("coverage")
    p_cov.add_argument("--original", required=True)
    p_cov.add_argument("--translated", required=True)

    p_gloss = sub.add_parser("glossary")
    p_gloss.add_argument("--translated", required=True)
    p_gloss.add_argument("--glossary", required=True,
                         help="glossary 文件路径，每行一个关键词")

    p_lint = sub.add_parser("pr_lint")
    p_lint.add_argument("--pr", required=True)

    args = parser.parse_args(argv)

    if args.cmd == "coverage":
        orig = Path(args.original).read_text(encoding="utf-8")
        trans = Path(args.translated).read_text(encoding="utf-8")
        result = run_coverage(orig, trans)
    elif args.cmd == "glossary":
        trans = Path(args.translated).read_text(encoding="utf-8")
        glossary = [
            line.strip() for line in Path(args.glossary).read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        result = run_glossary(trans, glossary)
    elif args.cmd == "pr_lint":
        pr = Path(args.pr).read_text(encoding="utf-8")
        result = run_pr_lint(pr)
    else:
        parser.error(f"未知子命令: {args.cmd}")

    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main_cli())