#!/usr/bin/env bash
# meta 两维 hard 验证脚本（v0.2 · ADR-004 落地第一步）。
# 用法: scripts/meta_check.sh [--json] [--strict] [--help]
#
# 退出码:  0  PASS（warning 不影响）  1  FAIL（维度 1 或维度 2 任一不通过）
# 选项:
#   --json    输出 JSON（便于 CI / 后续工具消费）
#   --strict  warning 也升级为 error（默认 warning 不阻断 workflow）
#   --help    打印本帮助
#
# 维度 1 · ADR 模板完整度
# 扫 docs/adr/ADR-*.md，结构契约（实际仓库 grep 校准）：
#   - 顶部 2 元数据：^**状态**： + ^**关联**：
#   - 核心 3 H2 段：^## 背景 / ^## 决策 / ^## 后果（容忍括号后缀，如"## 背景（沿用原版）"）
#   - 标准段：^## 备选方案（被否决）
# KNOWN_ADR_EXEMPT 表列出豁免"备选方案（被否决）"段的 ADR（key 用 basename）；
# 维护原则：豁免超过 2~3 条 = 重新审视 ADR 模板定义本身，不是膨胀豁免表。
#
# 维度 2 · 模板占位符替换成功率（零 hardcode 版）
#   (a) 每个 templates/*.template：grep -oE 提取占位符集合，非空 = OK
#   (b) 每个 state/*.md：扫 {{...}} 残留，空 = OK，非空 = error（真替换失败）
#   不维护"模板占位符 vs ground truth 对照表"——模板本身就是 ground truth；
#   iter.sh:68-70 / 152-154 只 replace 已知占位符,新增未替换占位符会以运行时
#   state/*.md 残留形式被 (b) 自动捕获。
#
# 复用 v0.1 已落件：
#   - tests/test_templates.py:8-9 的占位符集合 = pytest 侧权威（脚本不调它,只 grep）
#   - state/program.md / state/judge-prompt.md = iter.sh 的真实产物
#   - tests/test_templates.py:14-16 的 _placeholders 正则 = grep -oE 等价
#
# 不做的事（明确划出）：
#   - 不跑 Glossary 一致率（ADR-004 Open Issue 留给 v0.3+）
#   - 不写 Python 解析器（全部 shell + grep + awk）
#   - 不修任何文件（只报告）
#   - 不接 CI（本脚本独立可用,CI 接入留给后续）

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -W)"
cd "$REPO_ROOT"

# ---------- 选项解析 ----------
JSON_MODE=0
STRICT=0
for arg in "$@"; do
  case "$arg" in
    --json)  JSON_MODE=1 ;;
    --strict) STRICT=1 ;;
    --help|-h)
      sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *)
      echo "ERROR: unknown arg: $arg" >&2
      exit 2
      ;;
  esac
done

# ---------- 共享工具 ----------
# 提取文件中所有 {{小写字母_}} 形态占位符（去重,排序）
extract_placeholders() {
  grep -oE '\{\{[a-z_]+\}\}' "$1" 2>/dev/null | sort -u || true
}

# 占位符数量（用于人类可读输出）
count_placeholders() {
  extract_placeholders "$1" | wc -l | tr -d ' '
}

# ---------- ADR 维度 ----------
# 豁免清单：key=basename，value=被豁免的标准段（逗号分隔）。
# 当前 1 条（ADR-003.5 缺"备选方案（被否决）"段，因为它是元 ADR/从 ADR 拆出）。
# 维护原则：超过 2~3 条 = 重新审视 ADR 模板定义本身。
declare -A KNOWN_ADR_EXEMPT=(
  ["ADR-003.5-A-class-target-domain.md"]="备选方案（被否决）"
)

# 核心 H2 段（必查，前缀匹配容忍括号后缀，如"## 背景（沿用原版）"）
ADR_CORE_HEADERS=(
  "^## 背景"
  "^## 决策"
  "^## 后果"
)
# 标准段（必查，前缀匹配）——豁免清单可放宽
ADR_STANDARD_HEADERS=(
  "^## 备选方案（被否决）"
)

# 顶部元数据（必查，前缀匹配容忍同行后续内容）
ADR_TOP_METADATA=(
  "^\*\*状态\*\*"
  "^\*\*关联\*\*"
)

is_exempt() {
  local basename="$1"
  local segment="$2"
  local exempt_segments="${KNOWN_ADR_EXEMPT[$basename]:-}"
  if [ -z "$exempt_segments" ]; then
    return 1
  fi
  # 逗号分隔列表中是否包含该段
  local IFS=','
  for s in $exempt_segments; do
    if [ "$s" = "$segment" ]; then
      return 0
    fi
  done
  return 1
}

check_adr_file() {
  local f="$1"
  local basename
  basename="$(basename "$f")"
  local missing=()

  # 核心 3 H2（任何 ADR 都必须有）
  for h in "${ADR_CORE_HEADERS[@]}"; do
    if ! grep -qE "$h" "$f"; then
      missing+=("$h")
    fi
  done
  # 标准段（豁免清单可豁免）
  for h in "${ADR_STANDARD_HEADERS[@]}"; do
    # h 形如 "^## 备选方案（被否决）"，取段名部分比对豁免
    local seg="${h#^\#\# }"
    if is_exempt "$basename" "$seg"; then
      continue
    fi
    if ! grep -qE "$h" "$f"; then
      missing+=("$h")
    fi
  done
  # 顶部 2 元数据（任何 ADR 都必须有）
  for m in "${ADR_TOP_METADATA[@]}"; do
    if ! grep -qE "$m" "$f"; then
      missing+=("$m")
    fi
  done

  if [ ${#missing[@]} -ne 0 ]; then
    echo "FAIL|$basename|missing: ${missing[*]}"
    return 1
  fi
  local total=$(( ${#ADR_CORE_HEADERS[@]} + ${#ADR_STANDARD_HEADERS[@]} + ${#ADR_TOP_METADATA[@]} ))
  # 计算实际豁免数
  local exempt_count=0
  for h in "${ADR_STANDARD_HEADERS[@]}"; do
    local seg="${h#^\#\# }"
    if is_exempt "$basename" "$seg"; then
      exempt_count=$((exempt_count + 1))
    fi
  done
  local expected=$((total - exempt_count))
  echo "OK|$basename|($expected/$total 字段)"
  return 0
}

run_dimension_1() {
  local results=()
  local status="PASS"
  local fail_count=0
  local files_json=()

  # glob ADR 文件；KNOWN_ADR_EXEMPT 在表里的全检（含 .5 独立文件）
  local adr_files=(docs/adr/ADR-*.md)
  for f in "${adr_files[@]}"; do
    [ -f "$f" ] || continue
    local line
    if line="$(check_adr_file "$f")"; then
      results+=("$line")
    else
      results+=("$line")
      fail_count=$((fail_count + 1))
      status="FAIL"
    fi
  done

  # 输出
  echo "[meta_check] 维度 1: ADR 模板完整度"
  for r in "${results[@]}"; do
    IFS='|' read -r st path detail <<< "$r"
    if [ "$st" = "OK" ]; then
      printf '  %-50s %s\n' "$path" "$detail"
    else
      printf '  %-50s FAIL  %s\n' "$path" "$detail"
    fi
  done
  echo "  维度 1 总评: $status"

  # JSON 累加
  D1_JSON='"status":"'"$status"'"'
  local files_arr=()
  for r in "${results[@]}"; do
    IFS='|' read -r st path detail <<< "$r"
    if [ "$st" = "OK" ]; then
      files_arr+=("{\"path\":\"$path\",\"ok\":true,\"detail\":\"$detail\"}")
    else
      files_arr+=("{\"path\":\"$path\",\"ok\":false,\"detail\":\"$detail\"}")
    fi
  done
  D1_JSON+=",\"files\":[$(IFS=,; echo "${files_arr[*]}")]"

  DIM1_STATUS="$status"
}

# ---------- 模板维度 ----------
check_template_file() {
  local f="$1"
  local rel="${f#$REPO_ROOT/}"
  local n
  n="$(count_placeholders "$f")"
  if [ "$n" -eq 0 ]; then
    echo "WARN|$rel|模板无占位符（可能错配或空模板）"
    return 0  # warning,不阻断
  fi
  echo "OK|$rel|($n 占位符)"
  return 0
}

check_state_file() {
  local f="$1"
  local rel="${f#$REPO_ROOT/}"
  local residuals
  residuals="$(extract_placeholders "$f")"
  if [ -n "$residuals" ]; then
    local n
    n="$(echo "$residuals" | wc -l | tr -d ' ')"
    echo "FAIL|$rel|运行时残留 $n 个占位符: $(echo "$residuals" | tr '\n' ' ')"
    return 1
  fi
  echo "OK|$rel|(无残留占位符)"
  return 0
}

run_dimension_2() {
  local results=()
  local status="PASS"
  local warn_count=0
  local fail_count=0

  echo "[meta_check] 维度 2: 模板占位符替换成功率"
  # (a) 模板侧
  local tpl_files=(templates/*.template)
  for f in "${tpl_files[@]}"; do
    [ -f "$f" ] || continue
    local line
    line="$(check_template_file "$f")"
    results+=("template|$line")
    case "$line" in
      WARN\|*) warn_count=$((warn_count + 1)) ;;
    esac
  done

  # (b) 运行时侧（state 缺失 → warning/skip，不阻断）
  local state_files=(state/program.md state/judge-prompt.md)
  local state_present=0
  for f in "${state_files[@]}"; do
    if [ -f "$f" ]; then
      state_present=1
      local line
      if line="$(check_state_file "$f")"; then
        results+=("state|$line")
      else
        results+=("state|$line")
        fail_count=$((fail_count + 1))
        status="FAIL"
      fi
    else
      results+=("state|SKIP|$f|运行时产物未生成（state 缺失,运行时残留检查跳过）")
      warn_count=$((warn_count + 1))
    fi
  done

  # 输出
  for r in "${results[@]}"; do
    IFS='|' read -r kind st path detail <<< "$r"
    case "$kind" in
      template)
        case "$st" in
          OK)   printf '  %-50s OK    %s\n' "$path" "$detail" ;;
          WARN) printf '  %-50s WARN  %s\n' "$path" "$detail" ;;
        esac
        ;;
      state)
        case "$st" in
          OK)   printf '  %-50s OK    %s\n' "$path" "$detail" ;;
          SKIP) printf '  %-50s SKIP  %s\n' "$path" "$detail" ;;
          FAIL) printf '  %-50s FAIL  %s\n' "$path" "$detail" ;;
        esac
        ;;
    esac
  done
  echo "  维度 2 总评: $status"

  # JSON 累加
  D2_JSON='"status":"'"$status"'"'
  local files_arr=()
  for r in "${results[@]}"; do
    IFS='|' read -r kind st path detail <<< "$r"
    case "$kind" in
      template)
        if [ "$st" = "OK" ]; then
          files_arr+=("{\"path\":\"$path\",\"kind\":\"template\",\"ok\":true,\"detail\":\"$detail\"}")
        else
          files_arr+=("{\"path\":\"$path\",\"kind\":\"template\",\"ok\":null,\"detail\":\"$detail\"}")
        fi
        ;;
      state)
        case "$st" in
          OK)   files_arr+=("{\"path\":\"$path\",\"kind\":\"state\",\"ok\":true,\"detail\":\"$detail\"}") ;;
          SKIP) files_arr+=("{\"path\":\"$path\",\"kind\":\"state\",\"ok\":null,\"detail\":\"$detail\"}") ;;
          FAIL) files_arr+=("{\"path\":\"$path\",\"kind\":\"state\",\"ok\":false,\"detail\":\"$detail\"}") ;;
        esac
        ;;
    esac
  done
  D2_JSON+=",\"files\":[$(IFS=,; echo "${files_arr[*]}")]"

  DIM2_STATUS="$status"
  DIM2_WARN="$warn_count"
}

# ---------- 主流程 ----------
DIM1_STATUS=""
DIM2_STATUS=""
DIM2_WARN="0"

run_dimension_1
run_dimension_2

OVERALL="PASS"
if [ "$DIM1_STATUS" != "PASS" ] || [ "$DIM2_STATUS" != "PASS" ]; then
  OVERALL="FAIL"
fi
if [ "$STRICT" = "1" ] && [ "$DIM2_WARN" != "0" ]; then
  OVERALL="FAIL"
fi

echo "[meta_check] 总评: $OVERALL ($DIM1_STATUS / $DIM2_STATUS)"

if [ "$JSON_MODE" = "1" ]; then
  cat <<EOF
{
  "dimension_1_adr": {$D1_JSON},
  "dimension_2_templates": {$D2_JSON},
  "overall": "$OVERALL"
}
EOF
fi

if [ "$OVERALL" = "FAIL" ]; then
  exit 1
fi
exit 0