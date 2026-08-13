"""v0.3 T2b · 真 hermes 派发脚本（替代 fake_hermes.py · v0.2 T4 模式沿用）。

把 recipe agent 的 prompt_path 接到真 hermes CLI：
- argparse 接收 --profile / --section-id / --depends（与 fake_hermes 同 schema）
- 按 profile 构造 prompt → 调 hermes --no-restore-cwd -p <profile> -z <prompt>
- 捕获 stdout → 写到 stdout（spawn_agent 再写到 state_rw）

与 fake_hermes.py 的区别：
- fake_hermes.py：deterministic stub 输出（CI 守门用，T2a）
- real_hermes_runner.py：调真 LLM（手跑 1 次 · T2b evidence 用；CI 不跑）

跨平台 hermes 路径：
- Windows：`C:/Users/32115/AppData/Local/hermes/hermes-agent/venv/Scripts/hermes.exe`
  （默认用户级安装；可在 HERMES_EXE 环境变量覆盖）
- 非 Windows：`hermes` 走 PATH（hermes-setup 装到 ~/.local/bin）
"""

from pathlib import Path
import argparse
import os
import shutil
import subprocess
import sys

# Windows 默认 hermes 路径（用户级 venv 安装）
_WINDOWS_HERMES = Path("C:/Users/32115/AppData/Local/hermes/hermes-agent/venv/Scripts/hermes.exe")


def _resolve_hermes():
    """跨平台定位 hermes 二进制。env HERMES_EXE 优先 → Windows 默认 → PATH 找。"""
    env = os.environ.get("HERMES_EXE")
    if env:
        return env
    if sys.platform == "win32" and _WINDOWS_HERMES.exists():
        return str(_WINDOWS_HERMES)
    found = shutil.which("hermes")
    if found:
        return found
    raise FileNotFoundError(
        "hermes 二进制找不到。设置 HERMES_EXE 环境变量，或把 hermes 加到 PATH。"
    )


GLOSSARY_TERMS = ("install", "configure", "usage", "contribute")


def _build_translator_prompt(section_id, depends):
    """翻译 prompt：把原文 + glossary 注入，让 hermes 输出翻译段落。"""
    parts = [
        f"You are translating README section {section_id!r} for a multilingual PR.",
        "",
        "Constraints:",
        f"- Use the following glossary terms verbatim (lowercase): {', '.join(GLOSSARY_TERMS)}",
        "- Output 4 translated paragraphs separated by blank lines",
        "- Do NOT add any commentary, headings, or meta-text. Just the paragraphs.",
        "",
    ]
    if depends:
        parts.append("Source content (from upstream translation files):")
        for dep in depends:
            p = Path(dep)
            if p.exists():
                parts.append(f"--- {dep} ---")
                parts.append(p.read_text(encoding="utf-8").strip())
                parts.append("")
    else:
        # 没有 depends：构造一个 4 段原文占位，让 hermes 翻译
        parts.append("Source content (translate each paragraph):")
        for i, term in enumerate(GLOSSARY_TERMS, start=1):
            parts.append(f"Paragraph {i}: this section discusses {term}.")
        parts.append("")
    return "\n".join(parts)


def _build_consistency_prompt(section_id, depends):
    """一致性自检 prompt：读依赖译文 + glossary,输出 OK / NOT-OK 报告。"""
    parts = [
        f"You are checking translation consistency for section {section_id!r}.",
        "",
        f"Glossary terms to verify: {', '.join(GLOSSARY_TERMS)}",
        "",
        "Output format (NO other text):",
        "consistency OK: <N>/<N> glossary occurrences",
        "- <term> in <file>: found",
        "- <term> in <file>: missing  (if any)",
        "",
    ]
    parts.append("Translated files to check:")
    for dep in depends:
        p = Path(dep)
        if p.exists():
            parts.append(f"--- {dep} ---")
            parts.append(p.read_text(encoding="utf-8").strip())
            parts.append("")
    return "\n".join(parts)


def _build_pr_drafter_prompt(section_id, depends):
    """PR 起草 prompt：聚翻译 + 一致性报告,产 PR diff + 三 agent 段落。"""
    parts = [
        f"You are drafting a PR description for the translation of section {section_id!r}.",
        "",
        "Output format (strict):",
        "```diff",
        "--- a/README.md",
        "+++ b/README.md",
        "@@ -1,N +1,N @@",
        "<diff lines>",
        "```",
        "",
        "## PR body",
        "",
        "- translator: <one-line summary>",
        f"- consistency: <one-line summary for section {section_id}>",
        "- pr_drafter: <one-line summary>",
        "",
        "Do NOT add any other text outside the diff and the three bullet points.",
        "",
    ]
    parts.append("Source artifacts:")
    for dep in depends:
        p = Path(dep)
        if p.exists():
            parts.append(f"--- {dep} ---")
            parts.append(p.read_text(encoding="utf-8").strip())
            parts.append("")
    return "\n".join(parts)


def main():
    p = argparse.ArgumentParser(prog="real_hermes_runner")
    p.add_argument("--profile", required=True,
                   choices=("translator", "consistency", "pr_drafter"))
    p.add_argument("--section-id", required=True)
    p.add_argument("--depends", action="append", default=[],
                   help="依赖的 state_rw 路径（可多次传）")
    p.add_argument("--cwd", default=".",
                   help="depends 路径的解析根（默认 cwd，spawn_agent 传 state_dir）")
    p.add_argument("--timeout", type=int, default=300,
                   help="hermes 调起超时秒数（默认 300）")
    args = p.parse_args()

    cwd = Path(args.cwd)
    deps_abs = [str(cwd / d) for d in args.depends]

    if args.profile == "translator":
        prompt = _build_translator_prompt(args.section_id, deps_abs)
        profile = "writer"
    elif args.profile == "consistency":
        prompt = _build_consistency_prompt(args.section_id, deps_abs)
        profile = "judge"
    elif args.profile == "pr_drafter":
        prompt = _build_pr_drafter_prompt(args.section_id, deps_abs)
        profile = "writer"
    else:
        sys.exit(f"unknown profile: {args.profile}")

    hermes_bin = _resolve_hermes()
    try:
        proc = subprocess.run(
            [hermes_bin, "--no-restore-cwd", "-p", profile, "-z", prompt, "--yolo"],
            capture_output=True,
            text=True,
            timeout=args.timeout,
        )
    except subprocess.TimeoutExpired:
        sys.exit("hermes timeout")
    except OSError as exc:
        sys.exit(f"hermes launch failed: {exc}")

    if proc.returncode != 0:
        sys.stderr.write(proc.stderr)
        sys.exit(f"hermes exit {proc.returncode}")

    sys.stdout.write(proc.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())