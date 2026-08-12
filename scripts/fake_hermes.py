"""v0.3 T2a stub LLM — 跨平台 deterministic 输出。

替代 v0.2 fake hermes（v0.2.1 commit 99653ab：bash heredoc 写
C:/Users/.../Temp/d9/hermes + PATH 注入 + cygpath 转换）。
v0.3 Python 版：跨平台一致（Windows / Linux / macOS 同构）、deterministic
输出（不依赖 hermes / LLM），满足 T2a e2e "stub 下 spawn 顺序 / 聚合写入 /
PR 结构" 断言。

profile 行为（D2 锁定 3 agent：translator / consistency / pr_drafter）：
- translator: 产 4 段翻译，每段含 1 glossary 关键词（coverage / glossary pass）
- consistency: 读 depends 列出的翻译文件，输出一致性 OK + 命中关键词报告
- pr_drafter: 产 PR diff 形态（```diff + --- a/README.md + +++ b/README.md）
  + PR body 含三 agent 段落（pr_lint pass）

输入：argv（profile / section-id / depends 文件路径列表）。
输出：stdout 文本（spawn_agent 把它写到 state_rw 路径）。
"""

from pathlib import Path
import argparse
import sys

GLOSSARY_TERMS = ("install", "configure", "usage", "contribute")


def _emit_translator(section_id):
    """4 段翻译 + section 标题 = 5 段，4 个 glossary 关键词各出现一次。"""
    lines = [f"# Section {section_id} (translated)", ""]
    for i, term in enumerate(GLOSSARY_TERMS, start=1):
        lines.append(f"paragraph {i} with term {term}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _emit_consistency(section_id, depends):
    """读 depends 中翻译文件，验证 glossary 关键词。"""
    found = []
    missing = []
    for dep in depends:
        path = Path(dep)
        if not path.exists():
            missing.append(f"{dep} (not found)")
            continue
        text = path.read_text(encoding="utf-8").lower()
        for term in GLOSSARY_TERMS:
            (found if term in text else missing).append(f"{term} in {dep}")
    lines = [f"# Consistency check for section {section_id}", ""]
    lines.append(f"OK: {len(found)}/{len(found) + len(missing)} glossary occurrences checked")
    for f in found:
        lines.append(f"- {f}")
    if missing:
        lines.append("")
        lines.append("WARN:")
        for m in missing:
            lines.append(f"- {m}")
    return "\n".join(lines).rstrip() + "\n"


def _emit_pr_drafter(section_id, depends):
    """产 PR diff 形态：```diff + --- a/README.md + +++ b/README.md +
    PR body 含三 agent 段落（translator / consistency / pr_drafter）。
    """
    diff_lines = [
        "```diff",
        "--- a/README.md",
        "+++ b/README.md",
        f"@@ -1,{len(GLOSSARY_TERMS)} +1,{len(GLOSSARY_TERMS)} @@",
    ]
    for i, term in enumerate(GLOSSARY_TERMS, start=1):
        diff_lines.append(f"-original paragraph {i}")
        diff_lines.append(f"+translated paragraph {i} with term {term}")
    diff_lines.append("```")
    diff_lines.append("")
    diff_lines.append("## PR body")
    diff_lines.append("")
    diff_lines.append("- translator: produced 4 translated paragraphs "
                      f"covering {' / '.join(GLOSSARY_TERMS)}")
    diff_lines.append(f"- consistency: all glossary terms verified for section {section_id}")
    diff_lines.append("- pr_drafter: assembled final diff for README.md")
    if depends:
        diff_lines.append("")
        diff_lines.append("### Sources")
        for dep in depends:
            diff_lines.append(f"- {dep}")
    return "\n".join(diff_lines) + "\n"


def main():
    p = argparse.ArgumentParser(prog="fake_hermes")
    p.add_argument("--profile", required=True,
                   choices=("translator", "consistency", "pr_drafter"))
    p.add_argument("--section-id", required=True)
    p.add_argument("--depends", action="append", default=[],
                   help="依赖的 state_rw 路径（可多次传）")
    p.add_argument("--cwd", default=".",
                   help="depends 路径的解析根（默认 cwd，spawn_agent 传 state_dir）")
    args = p.parse_args()

    if args.profile == "translator":
        out = _emit_translator(args.section_id)
    elif args.profile == "consistency":
        # depends 路径相对 cwd 解析
        cwd = Path(args.cwd)
        deps_abs = [str(cwd / d) for d in args.depends]
        out = _emit_consistency(args.section_id, deps_abs)
    elif args.profile == "pr_drafter":
        cwd = Path(args.cwd)
        deps_abs = [str(cwd / d) for d in args.depends]
        out = _emit_pr_drafter(args.section_id, deps_abs)
    else:
        sys.exit(f"unknown profile: {args.profile}")

    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())