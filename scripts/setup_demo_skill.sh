#!/usr/bin/env bash
# 生成 demo-skill-target 独立 git repo（D8 rule 1）：从 demo-skill-src/ 复制源码模板 + git init + 初始 commit。
# demo-skill-target/ 整体被外层 .gitignore 忽略（避免嵌套 .git 触发 gitlink），幂等。
# 与 v0.1 demo-src/ → demo-target/ 同构：模板入库，运行时 repo 忽略。
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -W)"
DEMO="$REPO_ROOT/demo-skill-target"
DEMO_SRC="$REPO_ROOT/demo-skill-src"

if [ -d "$DEMO/.git" ]; then
  echo "demo-skill-target already a git repo — skip"
  exit 0
fi

[ -f "$DEMO_SRC/SKILL.md" ] || { echo "ERROR: $DEMO_SRC/SKILL.md missing"; exit 1; }

mkdir -p "$DEMO"
cp "$DEMO_SRC"/SKILL.md "$DEMO"/
cp -r "$DEMO_SRC"/fixtures "$DEMO_SRC"/tests "$DEMO"/
cd "$DEMO"
git init -q
git add SKILL.md fixtures/ tests/
git commit -qm "demo: initial SKILL.md baseline (Triadic Reasoning)"
echo "demo-skill-target git repo ready: $DEMO"
