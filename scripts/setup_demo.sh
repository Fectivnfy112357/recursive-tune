#!/usr/bin/env bash
# 生成 demo-target 独立 git repo（D8 rule 1）：从 demo-src/ 复制源码模板 + git init + 初始 commit。
# demo-target/ 整体被外层 .gitignore 忽略（避免嵌套 .git 触发 gitlink），幂等。
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -W)"
DEMO="$REPO_ROOT/demo-target"
DEMO_SRC="$REPO_ROOT/demo-src"

if [ -d "$DEMO/.git" ]; then
  echo "demo-target already a git repo — skip"
  exit 0
fi

mkdir -p "$DEMO"
cp "$DEMO_SRC"/config.py "$DEMO_SRC"/test_config.py "$DEMO_SRC"/.gitignore "$DEMO"/
cd "$DEMO"
git init -q
git add -A
git commit -qm "demo: initial failing target (TARGET_VALUE=0)"
echo "demo-target git repo ready: $DEMO"
