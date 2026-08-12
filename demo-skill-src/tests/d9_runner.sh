#!/usr/bin/env bash
# D9 模式 runner（v0.2 spec D9 A-min 约定）。
#
# 触发：validate_config.py / iter.sh 调用 signal 命令时注入 D9_FIXTURE_PATH
# 输出：{"total": N, "positive_hit": N, "negative_reject": N}（JSON 形式）
# 退出码：0 = 跑通；1 = fixture 路径未设或读不到
#
# 判定逻辑（demo 简化版）：fixture 文本同时含 事实 / 选项 / 决策建议 三个关键词 → 判 pass
# 验"信号"不验"Target"——读 fixture 文本本身判定，不读 SKILL.md
set -euo pipefail

if [ -z "${D9_FIXTURE_PATH:-}" ]; then
  echo "ERROR: D9_FIXTURE_PATH not set" >&2
  exit 1
fi

FIXTURE="$D9_FIXTURE_PATH"
[ -f "$FIXTURE" ] || { echo "ERROR: fixture not found: $FIXTURE" >&2; exit 1; }

total=0
pos_hit=0
neg_reject=0
current_input=""
current_expect=""

flush_sample() {
  # 调用时 current_input / current_expect 已设好
  [ -n "$current_expect" ] || return 0
  total=$((total + 1))
  if [ "$current_expect" = "pass" ]; then
    if echo "$current_input" | grep -q "事实" \
       && echo "$current_input" | grep -q "选项" \
       && echo "$current_input" | grep -q "决策建议"; then
      pos_hit=$((pos_hit + 1))
    fi
  else
    # fail 样本期望"缺任一段"——只要任一关键词缺失即正确判 fail
    if ! echo "$current_input" | grep -q "事实" \
       || ! echo "$current_input" | grep -q "选项" \
       || ! echo "$current_input" | grep -q "决策建议"; then
      neg_reject=$((neg_reject + 1))
    fi
  fi
  current_input=""
  current_expect=""
}

while IFS= read -r line; do
  # 跳过注释 / 空行
  case "$line" in
    "#"*|"") continue ;;
  esac
  # 样本起始
  if [[ "$line" =~ ^-\ input:\ (.*)$ ]]; then
    flush_sample
    current_input="${BASH_REMATCH[1]}"
  elif [[ "$line" =~ ^\ \ expect:\ (pass|fail)$ ]]; then
    current_expect="${BASH_REMATCH[1]}"
  fi
done < "$FIXTURE"

# 最后一条样本
flush_sample

# D9 模式输出（JSON）
echo "{\"total\": $total, \"positive_hit\": $pos_hit, \"negative_reject\": $neg_reject}"
