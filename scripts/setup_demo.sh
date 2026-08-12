#!/usr/bin/env bash
# 生成 demo-target 独立 git repo（D8 rule 1）。
# demo-target 源码已随仓库 track；本脚本只做 git init + 初始 commit（幂等）。
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -W)"
DEMO="$REPO_ROOT/demo-target"

if [ -d "$DEMO/.git" ]; then
  echo "demo-target already a git repo — skip"
  exit 0
fi

cd "$DEMO"
git init -q
git add -A
git commit -qm "demo: initial failing target (TARGET_VALUE=0)"
echo "demo-target git repo ready: $DEMO"
