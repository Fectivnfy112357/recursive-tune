#!/usr/bin/env bash
# T4 端到端：v0.2 假文本 Target demo 跑 3 轮 loop（spec T4 i/ii/iii）
#
# 断言：
#   (i)  state/results.tsv 行数 = accepted 轮数（仅记 accepted，D8 rule 8）
#   (ii) ≥1 轮 signal 命令 exit ≠ 0 → reject，该轮不入 results.tsv（D8 rule 7）
#   (iii) D9 门在 config-time 跑过（validate_config.py exit 0）
#
# 模式：1 坏 + 2 好（轮 2 临时改 signal = `bash -c 'exit 1'` 触发 reject；轮 1/3 正常）
# 测试隔离：备份/恢复根 scoring.yaml + 根 state/（iter.sh 硬编码读根，零骨架改动）
# hermes 不可用时 skip（与 v0.1 e2e 模式同构——v0.1 T4 是手跑 smoke test，未自动化的承诺）
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -W)"
cd "$REPO_ROOT"

# ---- hermes 不可用 → skip（CI 守门交给 test_d9_gate.py + test_meta_check.py）----
if ! command -v hermes >/dev/null 2>&1; then
  echo "SKIP: hermes CLI not installed (T4 需 LLM 调 profile，T4a 走 pytest 守门)"
  exit 0
fi

# 关键输出（iter.sh 的 ACCEPTED/REJECTED 屏幕标记）用同步 >> 写 e2e.log：
# 不能用 exec > >(tee ...) 异步进程替换——(a) 脚本 L70 rm -rf state 会删掉 tee 打开的文件，
# (b) tee 块缓冲在脚本内读文件断言时可能未 flush。同步重定向无这两个问题。
E2E_LOG="$REPO_ROOT/state/e2e.log"
mkdir -p "$(dirname "$E2E_LOG")"
echo "=== T4 启动 $(date) ===" >> "$E2E_LOG"

# ---- 一次性准备：profile + target repo + d9 runner staging（短路径，绕开 iter.sh:87 bash -c 拆空格）----
# d9_runner.sh 从 demo-skill-src 模板复制（setup_demo_skill.sh 生成 target 前就需要它）
D9_STAGE="C:/Users/32115/AppData/Local/Temp/d9"
mkdir -p "$D9_STAGE"
cp "$REPO_ROOT/demo-skill-src/tests/d9_runner.sh" "$D9_STAGE/d9_runner.sh"
bash scripts/setup_profiles.sh >/dev/null
bash scripts/setup_demo_skill.sh

# ---- 备份/恢复（关键：避免污染根 scoring + 根 state）----
BACKUP_DIR="$(mktemp -d)"
STATE_BACKUP="$(mktemp -d)"
restore_isolation() {
  # 保留 T4 e2e.log（断言依赖）——restore 前从根 state/ 拷出来，restore 后放回去
  local t4_e2e_backup="$BACKUP_DIR/t4-e2e.log"
  if [ -f "$REPO_ROOT/state/e2e.log" ]; then
    cp "$REPO_ROOT/state/e2e.log" "$t4_e2e_backup"
  fi
  # 恢复根 scoring.yaml
  if [ -f "$BACKUP_DIR/scoring.yaml.bak" ]; then
    cp "$BACKUP_DIR/scoring.yaml.bak" "$REPO_ROOT/scoring.yaml"
  fi
  # 恢复根 state/
  if [ -d "$STATE_BACKUP" ] && [ "$(ls -A "$STATE_BACKUP" 2>/dev/null)" ]; then
    rm -rf "$REPO_ROOT/state"
    mv "$STATE_BACKUP" "$REPO_ROOT/state"
  else
    rm -rf "$STATE_BACKUP"
  fi
  # 放回 e2e.log（断言已读完，可删）
  if [ -f "$t4_e2e_backup" ]; then
    mkdir -p "$REPO_ROOT/state"
    cp "$t4_e2e_backup" "$REPO_ROOT/state/e2e.log"
  fi
  # 清理 demo 临时 config
  rm -f "$CONFIG" 2>/dev/null || true
  rm -rf "$BACKUP_DIR"
}
trap restore_isolation EXIT
cp "$REPO_ROOT/scoring.yaml" "$BACKUP_DIR/scoring.yaml.bak"
if [ -d "$REPO_ROOT/state" ]; then
  cp -r "$REPO_ROOT/state/." "$STATE_BACKUP/" 2>/dev/null || true
fi
rm -rf "$REPO_ROOT/state"
mkdir -p "$REPO_ROOT/state"
# iter.sh 不初始化 results.tsv 表头（run_loop.sh 的职责）——T4 直接调 iter.sh，自己初始化
printf 'iter\tfinal\thard\tsoft\tcommit\tdescription\n' > "$REPO_ROOT/state/results.tsv"

# ---- 写入 demo scoring（python 写文件，避免 heredoc 变量展开陷阱）----
DEMO_SCORING="$REPO_ROOT/scoring.yaml"
python -c "
import sys
content = '''dimensions:
  - name: triadic_structure
    type: hard
    weight: 1.0
    signal: "C:/Users/32115/AppData/Local/Temp/d9/d9_runner.sh"
  - name: clarity
    type: soft
    weight: 1.0
    signal: judge_prompt
aggregate:
  hard: arithmetic_mean
  soft: weighted_mean
  final:
    formula: \"0.6*hard + 0.4*soft\"
    default: true
'''
print(content.replace('REPO_ROOT_PLACEHOLDER', sys.argv[1]))
" "$REPO_ROOT" > "$DEMO_SCORING"

# ---- demo config（target_path = target 仓库根，约束层管 SKILL.md）----
# 注：放 REPO_ROOT 下（不在 /tmp/）—— git-bash Windows /tmp/ 路径对原生 python 不可见
CONFIG="$REPO_ROOT/.demo-text-config.yaml"
cat > "$CONFIG" <<EOF
target_path: $REPO_ROOT/demo-skill-target
writer: writer
judge: judge
program:
  objective: "优化 SKILL.md 的三段式结构完整度"
  constraints:
    - "仅修改 SKILL.md，不动其他文件"
automations:
  iter_timeout_minutes: 5
EOF

# ---- (iii) D9 门 config-time ----
echo "=== (iii) D9 门 config-time 验证 ==="
if ! python "$REPO_ROOT/scripts/validate_config.py" "$REPO_ROOT/scoring.yaml" "$CONFIG" >/dev/null 2>&1; then
  echo "FAIL: D9 门 exit 非 0"
  exit 1
fi
echo "  (iii) PASS: D9 门 exit 0"

# ---- 3 轮 loop ----（iter.sh 输出同步进 e2e.log，断言 grep 用）
echo "=== 跑 3 轮 loop（1 坏 + 2 好）===" >> "$E2E_LOG"
# 轮 1：正常 signal
{ echo "--- 轮 1（正常 signal）---"; bash scripts/iter.sh 1 "$CONFIG" || true; } >> "$E2E_LOG" 2>&1
# 轮 2：人为坏 signal（sed 替换 d9_runner.sh → exit 1）
sed -i "s|d9_runner.sh|-c 'exit 1' ;|" "$REPO_ROOT/scoring.yaml"
{ echo "--- 轮 2（坏 signal）---"; bash scripts/iter.sh 2 "$CONFIG" || true; } >> "$E2E_LOG" 2>&1
# 轮 3：恢复 signal
python -c "
import sys
content = open(sys.argv[1], encoding='utf-8').read()
# 撤掉轮 2 的 sed：把 '-c \\'exit 1\\' ;' 换回 'd9_runner.sh'
content = content.replace(\"-c 'exit 1' ;\", 'd9_runner.sh')
open(sys.argv[1], 'w', encoding='utf-8').write(content)
" "$REPO_ROOT/scoring.yaml"
{ echo "--- 轮 3（恢复 signal）---"; bash scripts/iter.sh 3 "$CONFIG" || true; } >> "$E2E_LOG" 2>&1

# ---- (i)(ii) 断言（读 e2e.log，含 iter.sh 屏幕输出）----
echo "=== (i)(ii) 断言 ==="
E2E_LOG="$REPO_ROOT/state/e2e.log"
if [ ! -f "$E2E_LOG" ]; then
  echo "FAIL: state/e2e.log 不存在"
  exit 1
fi
TSV="$REPO_ROOT/state/results.tsv"
ACCEPTED=$(grep -c "ACCEPTED" "$E2E_LOG")
REJECTED=$(grep -c "REJECTED" "$E2E_LOG")
DATA_LINES=$(($(wc -l < "$TSV") - 1))  # 减 1 减表头
echo "  e2e.log: ACCEPTED=$ACCEPTED, REJECTED=$REJECTED"
echo "  results.tsv 数据行: $DATA_LINES"

# 关键断言 (ii)：轮 2 REJECTED 真触发（rc=127 = command not found）
if [ "$REJECTED" -lt 1 ]; then
  echo "FAIL: e2e.log 无 REJECTED 标记（轮 2 人为 reject 未真触发）"
  exit 1
fi
# 关键断言 (i)：results.tsv 数据行 = 1（只记轮 1 accepted；轮 2 reject + 轮 3 revert 都不入表）
if [ "$DATA_LINES" -ne 1 ]; then
  echo "FAIL: results.tsv 数据行 = $DATA_LINES，期望 1（轮 1 accepted）"
  exit 1
fi
# 关键断言：results.tsv 没有 iter 2（reject 不入表）
if grep -q "^2	" "$TSV"; then
  echo "FAIL: results.tsv 含 iter 2 行（reject 不该入表）"
  exit 1
fi

echo "  (i)  PASS: results.tsv 数据行 = 1 = accepted 轮数（轮 2 reject + 轮 3 revert 都不入表）"
echo "  (ii) PASS: 轮 2 hard signal exit ≠ 0 → reject 不入 results.tsv"
echo "OVERALL: PASS"
exit 0
