#!/usr/bin/env bash
# 入口：跑 N 次迭代。
# 用法: run_loop.sh --config <path> --iterations <N>
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -W)"
cd "$REPO_ROOT"

CONFIG=""
ITERATIONS=""
while [ $# -gt 0 ]; do
  case "$1" in
    --config) CONFIG="${2:-}"; shift 2 ;;
    --iterations) ITERATIONS="${2:-}"; shift 2 ;;
    *) echo "ERROR: unknown arg: $1" >&2; exit 1 ;;
  esac
done
[ -n "$CONFIG" ] && [ -n "$ITERATIONS" ] || { echo "usage: run_loop.sh --config <path> --iterations <N>" >&2; exit 1; }
[[ "$ITERATIONS" =~ ^[0-9]+$ ]] || { echo "ERROR: --iterations 必须是正整数" >&2; exit 1; }

# 配置校验（T2 validate_config.py：非法 schema / 缺必填段 → 报错退出）
python "$REPO_ROOT/scripts/validate_config.py" "$REPO_ROOT/scoring.yaml" "$CONFIG"

# D8 rule 1：Target 必须是 git 仓库
TARGET_PATH="$(python -c "import yaml,sys; d=yaml.safe_load(open(sys.argv[1],encoding='utf-8')); print(d.get('target_path','') if isinstance(d,dict) else '')" "$CONFIG")"
[ -d "$TARGET_PATH/.git" ] || { echo "ERROR: target '$TARGET_PATH' is not a git repo (D8 rule 1)" >&2; exit 1; }

# state 初始化（rule 8：results.tsv = accepted history 的镜像）
mkdir -p "$REPO_ROOT/state"
[ -f "$REPO_ROOT/state/results.tsv" ] || printf 'iter\tfinal\thard\tsoft\tcommit\tdescription\n' > "$REPO_ROOT/state/results.tsv"

# D8 rule 5：每轮迭代硬超时（默认 5 分钟，automations.iter_timeout_minutes 可改）
TIMEOUT_MIN="$(python -c "import yaml,sys; d=yaml.safe_load(open(sys.argv[1],encoding='utf-8')); a=d.get('automations') or {}; print(a.get('iter_timeout_minutes',5))" "$CONFIG")"

echo "recursive-tune v0.1 loop: $ITERATIONS iterations, config=$CONFIG, timeout=${TIMEOUT_MIN}m/iter"
for i in $(seq 1 "$ITERATIONS"); do
  if timeout "${TIMEOUT_MIN}m" bash "$REPO_ROOT/scripts/iter.sh" "$i" "$CONFIG"; then
    :
  else
    # 超时（124）或异常退出：这次 iteration 视为 reject——无 commit、无 tsv 写入（rule 7/8）
    echo "iter-$i: TIMEOUT/FAILED → reject（不 commit、不写 results.tsv）"
  fi
done
echo "done. results: $REPO_ROOT/state/results.tsv"
