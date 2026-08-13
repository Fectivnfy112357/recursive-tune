"""v0.3 T3 · violation scanner —— 扫代码库守「v0.3 必入约束」。

禁词（spec v0.3 D1 必入约束）：
- 断点续跑路径：`checkpoint` / `pickle` / `save_state` / `load_state` / `resume_state`
- 独立 glossary 持久化件：`glossary_db` / `glossary_store` / `glossary.pkl` / `glossary.json`

扫描范围：scripts/ + tests/ + recipes/ 下所有 .py / .sh / .yaml 文件
（排除 __pycache__、.git、.pytest_cache）。

任何命中 → exit 1 + 报路径:行号:命中词。CI 守门交给
test_t3_guards::test_scan_violations_zero_hits。

注：hermes CLI 参数 `--resume` / `--restore-cwd` / `--no-restore-cwd` 不在
禁词表内（hermes 内部 session 概念，不是 v0.3 spec 锁的「断点续跑」语义）。
v0.3 锁的「断点续跑」= subagents 聚合失败后从中间状态续跑 = state pickle +
恢复执行；与 hermes session resume 正交。

用法：
    python scripts/scan_violations.py
"""

from pathlib import Path
import re
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
SCAN_DIRS = (REPO_ROOT / "scripts", REPO_ROOT / "tests", REPO_ROOT / "recipes")
SCAN_EXTS = (".py", ".sh", ".yaml", ".yml")

# 禁词：每个 token 独立匹配
_FORBIDDEN_TOKENS = (
    # 断点续跑路径
    "checkpoint",
    "pickle",
    "save_state",
    "load_state",
    "resume_state",
    # 独立 glossary 持久化件
    "glossary_db",
    "glossary_store",
    "glossary.pkl",
    "glossary.json",
)

# hermes CLI 参数行（不视为 v0.3 锁的「断点续跑」语义）
_HERMES_CLI_PATTERN = re.compile(
    r"--(resume|restore-cwd|no-restore-cwd)\b",
    re.IGNORECASE,
)

# 豁免规则：
# - scan_violations.py 自身（必须含禁词定义）+ scan_violations test
# - 注释行（# / """ / // 开头）
# - 测试断言行（assert 开头）
_EXEMPT_FILENAMES = {"scan_violations.py", "test_t3_guards.py"}


def _is_exempt(line, filename=None):
    """该行是否豁免禁词扫描。"""
    stripped = line.strip()
    if filename and Path(filename).name in _EXEMPT_FILENAMES:
        return True
    if stripped.startswith(("#", "//")):
        return True
    if stripped.startswith('"""') or stripped.startswith("'''"):
        return True
    if stripped.startswith("assert "):
        return True
    if _HERMES_CLI_PATTERN.search(line):
        return True
    return False


def scan_violations(scan_dirs=SCAN_DIRS, scan_exts=SCAN_EXTS):
    """扫禁词。返回 (files_scanned, hits)。

    hits = list of {"path", "line_no", "line", "token"}。
    """
    hits = []
    files_scanned = 0
    for scan_dir in scan_dirs:
        scan_dir = Path(scan_dir)
        if not scan_dir.exists():
            continue
        for path in sorted(scan_dir.rglob("*")):
            if not path.is_file() or path.suffix not in scan_exts:
                continue
            if "__pycache__" in path.parts or ".pytest_cache" in path.parts:
                continue
            files_scanned += 1
            for line_no, line in enumerate(
                path.read_text(encoding="utf-8", errors="replace").splitlines(),
                start=1,
            ):
                if _is_exempt(line, filename=str(path)):
                    continue
                for token in _FORBIDDEN_TOKENS:
                    if token in line.lower():
                        hits.append({
                            "path": str(path.relative_to(REPO_ROOT)),
                            "line_no": line_no,
                            "line": line.strip(),
                            "token": token,
                        })
    return files_scanned, hits


def main(argv=None):
    files_scanned, hits = scan_violations()
    if hits:
        print(f"FAIL: 禁词命中 {len(hits)} 处（扫描 {files_scanned} 文件）\n",
              file=sys.stderr)
        for h in hits:
            print(f"  {h['path']}:{h['line_no']}  [{h['token']}]  {h['line']}",
                  file=sys.stderr)
        return 1
    print(f"OK: 禁词 0 命中（扫描 {files_scanned} 文件）")
    return 0


if __name__ == "__main__":
    sys.exit(main())