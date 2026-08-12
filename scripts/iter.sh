#!/usr/bin/env bash
# 单次迭代：writer → hard signal → judge → commit/revert（spec D8 hard rules）。
# 用法: iter.sh <iter_num> <config.yaml>
set -euo pipefail

ITER_NUM="${1:?usage: iter.sh <iter_num> <config.yaml>}"
CONFIG="${2:?usage: iter.sh <iter_num> <config.yaml>}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -W)"
cd "$REPO_ROOT"

SCORING="$REPO_ROOT/scoring.yaml"
STATE_DIR="$REPO_ROOT/state"
mkdir -p "$STATE_DIR"

# ---- 读配置（一次 python 调用，逐行输出；constraints 多行单独）----
{ read -r TARGET_PATH; read -r WRITER_PROFILE; read -r JUDGE_PROFILE; read -r TIMEOUT_MIN; read -r OBJECTIVE; } < <(python - "$CONFIG" <<'PYEOF'
import sys, yaml
sys.stdout.reconfigure(newline='\n')  # 禁 Windows \r\n 转换，防 bash read 带入 \r
d = yaml.safe_load(open(sys.argv[1], encoding='utf-8'))
if not isinstance(d, dict):
    d = {}
p = d.get('program') or {}
print(d.get('target_path', ''))
print(d.get('writer', ''))
print(d.get('judge', ''))
print((d.get('automations') or {}).get('iter_timeout_minutes', 5))
print(p.get('objective', '') if isinstance(p.get('objective'), str) else '')
PYEOF
)
CONSTRAINTS_TEXT="$(python - "$CONFIG" <<'PYEOF'
import sys, yaml
sys.stdout.reconfigure(newline='\n')
d = yaml.safe_load(open(sys.argv[1], encoding='utf-8'))
if not isinstance(d, dict):
    d = {}
p = d.get('program') or {}
print('\n'.join('- ' + str(x) for x in p.get('constraints') or [] if x))
PYEOF
)"

[ -n "$TARGET_PATH" ] || { echo "ERROR: config missing target_path" >&2; exit 1; }

# D8 rule 1：Target 必须是 git 仓库
[ -d "$TARGET_PATH/.git" ] || { echo "ERROR: target '$TARGET_PATH' is not a git repo (D8 rule 1)" >&2; exit 1; }

# 绝对路径（Windows 正斜杠）：agent（hermes oneshot）cwd 可能与 REPO_ROOT 不同
TARGET_ABS="$(cd "$TARGET_PATH" && pwd -W)"

# D8 rule 11：iteration 开始时 checkout 到 best commit（首次 = HEAD）
BEST_SCORE="0.0"
BEST_COMMIT="$(git -C "$TARGET_PATH" rev-parse HEAD)"
if [ -f "$STATE_DIR/best_score.txt" ]; then
  BEST_SCORE="$(sed -n '1p' "$STATE_DIR/best_score.txt")"
  BEST_COMMIT="$(sed -n '2p' "$STATE_DIR/best_score.txt")"
fi
if ! git -C "$TARGET_PATH" checkout -q "$BEST_COMMIT" 2>/dev/null; then
  echo "ERROR: 无法 checkout best commit '$BEST_COMMIT'（D8 rule 11 要求每轮从 best commit 开始）" >&2
  exit 1
fi

# ---- 生成 program.md（writer 指令）----
PROGRAM_FILE="$STATE_DIR/program.md"
python - "$REPO_ROOT/templates/program.md.template" "$PROGRAM_FILE" "$TARGET_ABS" "$OBJECTIVE" "$CONSTRAINTS_TEXT" <<'PYEOF'
import sys
from pathlib import Path
tpl_path, out_path, target, objective, constraints = sys.argv[1:6]
content = Path(tpl_path).read_text(encoding='utf-8')
content = content.replace('{{target_path}}', target)
content = content.replace('{{objective}}', objective)
content = content.replace('{{constraints}}', constraints)
Path(out_path).write_text(content, encoding='utf-8')
PYEOF

# ---- writer：修改 Target ----
echo "iter-$ITER_NUM: writer('$WRITER_PROFILE') → $TARGET_ABS"
hermes --no-restore-cwd -p "$WRITER_PROFILE" -z "$(cat "$PROGRAM_FILE")" > "$STATE_DIR/writer-$ITER_NUM.log" 2>&1 || echo "  (writer exit $?)"

# ---- hard signal（D8 rule 6：缺失计 0 / rule 7：失败 reject）----
HARD_FILE="$STATE_DIR/hard-$ITER_NUM.tsv"
: > "$HARD_FILE"
REJECTED=0
# D9 约定（v0.2 spec D1+D9）：fixture 目录定位——target_path 的同级 fixtures/ 子目录
# 注入 D9_FIXTURE_PATH 给 runner，让硬信号能跑 fixture-set 命中验证
FIXTURES_DIR="$TARGET_PATH/../fixtures"
[ -d "$FIXTURES_DIR" ] || FIXTURES_DIR="$TARGET_PATH/fixtures"

while IFS=$'\t' read -r name signal; do
  [ -n "$name" ] || continue
  LOG="$STATE_DIR/hard-$ITER_NUM-${name}.log"
  set +e
  # D9 约定（v0.2 spec D9）：注入 D9_FIXTURE_PATH 给 runner（v0.1 兼容性保留——无 fixture 时不传）
  FIXTURE_PATH="$FIXTURES_DIR/${name}.yaml"
  if [ -f "$FIXTURE_PATH" ]; then
    (cd "$TARGET_PATH" && timeout "${TIMEOUT_MIN}m" env "D9_FIXTURE_PATH=$FIXTURE_PATH" bash -c "$signal" > "$LOG" 2>&1)
  else
    (cd "$TARGET_PATH" && timeout "${TIMEOUT_MIN}m" bash -c "$signal" > "$LOG" 2>&1)
  fi
  rc=$?
  set -e
  if [ $rc -eq 124 ] || [ $rc -eq 137 ]; then
    echo "  hard[$name]: TIMEOUT → 0 (rule 6 缺失)"
    echo -e "$name\t0.0" >> "$HARD_FILE"
  elif [ $rc -ne 0 ]; then
    echo "  hard[$name]: FAILED rc=$rc → REJECT (rule 7)"
    REJECTED=1
    break
  elif [ ! -s "$LOG" ]; then
    echo "  hard[$name]: 空输出 → 0 (rule 6 缺失)"
    echo -e "$name\t0.0" >> "$HARD_FILE"
  else
    echo "  hard[$name]: OK → 1.0"
    echo -e "$name\t1.0" >> "$HARD_FILE"
  fi
done < <(python - "$SCORING" <<'PYEOF'
import sys, yaml
sys.stdout.reconfigure(newline='\n')
d = yaml.safe_load(open(sys.argv[1], encoding='utf-8'))
for x in d.get('dimensions', []):
    if x.get('type') == 'hard':
        print(f"{x.get('name','')}\t{x.get('signal','')}")
PYEOF
)

if [ "$REJECTED" -eq 1 ]; then
  echo "iter-$ITER_NUM: REJECTED（hard 失败）— 不 commit、不写 results.tsv（rule 7/8）"
  git -C "$TARGET_PATH" checkout -q -- .
  exit 0
fi

if [ -s "$HARD_FILE" ]; then
  HARD_SCORE="$(python - "$HARD_FILE" <<'PYEOF'
import sys
vals = [float(line.split('\t')[1]) for line in open(sys.argv[1], encoding='utf-8') if line.strip()]
print(f"{sum(vals)/len(vals):.4f}" if vals else "0.0")
PYEOF
)"
else
  HARD_SCORE="0.0"
fi

# ---- judge：soft 打分 ----
DIMS_YAML="$(python - "$SCORING" <<'PYEOF'
import sys, yaml
sys.stdout.reconfigure(newline='\n')
d = yaml.safe_load(open(sys.argv[1], encoding='utf-8'))
for x in d.get('dimensions', []):
    if x.get('type') == 'soft':
        print(f"- name: {x.get('name','')}")
        print(f"  type: soft")
        print(f"  weight: {x.get('weight',1.0)}")
        print(f"  signal: {x.get('signal','judge_prompt')}")
PYEOF
)"
JUDGE_FILE="$STATE_DIR/judge-prompt.md"
# 注入本次改动的 git diff（judge 打分的依据）；上限 20KB 防 prompt 膨胀
DIFF_TEXT="$(git -C "$TARGET_PATH" diff | head -c 20000)"
python - "$REPO_ROOT/templates/judge-prompt.md.template" "$JUDGE_FILE" "$TARGET_ABS" "$DIMS_YAML" "$DIFF_TEXT" <<'PYEOF'
import sys
from pathlib import Path
tpl_path, out_path, target, dims, diff = sys.argv[1:6]
content = Path(tpl_path).read_text(encoding='utf-8')
content = content.replace('{{target_path}}', target)
content = content.replace('{{dimensions}}', dims)
content = content.replace('{{diff}}', diff)  # 最后替换：diff 内容不经后续 replace
Path(out_path).write_text(content, encoding='utf-8')
PYEOF

echo "iter-$ITER_NUM: judge('$JUDGE_PROFILE') 打分"
hermes --no-restore-cwd -p "$JUDGE_PROFILE" -z "$(cat "$JUDGE_FILE")" > "$STATE_DIR/judge-$ITER_NUM.log" 2>&1 || echo "  (judge exit $?)"

SOFT_SCORE="$(python - "$SCORING" "$STATE_DIR/judge-$ITER_NUM.log" <<'PYEOF'
import sys, re, yaml
sys.stdout.reconfigure(newline='\n')
scoring = yaml.safe_load(open(sys.argv[1], encoding='utf-8'))
judge_text = open(sys.argv[2], encoding='utf-8').read()
dims = [x for x in scoring.get('dimensions', []) if x.get('type') == 'soft']

def parse_judge_scores(text):
    """宽容解析 judge 输出：逐行提取 name/score。

    rationale 是自由文本（可能含 'key: value' 样式），整体 yaml.safe_load
    会 ScannerError——这里只认行首 '- name:' / 'score:' 结构，rationale 不影响。
    """
    scores = {}
    m = re.search(r'```(?:yaml)?\s*(scores:.*?)```', text, re.S)
    if not m:
        m = re.search(r'(scores:.*)', text, re.S)
    if not m:
        return scores
    cur = None
    for line in m.group(1).splitlines():
        s = line.strip()
        nm = re.match(r'^-?\s*name:\s*(.+)$', s)
        sc = re.match(r'^score:\s*([0-9]+(?:\.[0-9]+)?)$', s)
        if nm:
            cur = nm.group(1).strip().strip('"\'')
        elif sc and cur:
            scores[cur] = float(sc.group(1))
    return scores

judge_scores = parse_judge_scores(judge_text)
if not dims:
    print("0.0")
else:
    total_w = sum(float(x.get('weight', 1.0)) for x in dims) or 1.0
    val = sum(float(judge_scores.get(x.get('name'), 0.0)) * float(x.get('weight', 1.0)) for x in dims)
    # soft 归一化到 0-1：judge 打分 0-10（judge-prompt 模板），formula 按 0-1 语义
    print(f"{val / total_w / 10:.4f}")
PYEOF
)"

# ---- final score（effective_aggregate formula，安全求值）----
FINAL_SCORE="$(python - "$SCORING" "$CONFIG" "$HARD_SCORE" "$SOFT_SCORE" <<'PYEOF'
import sys, yaml, importlib.util
sys.stdout.reconfigure(newline='\n')
spec = importlib.util.spec_from_file_location('vc', 'scripts/validate_config.py')
vc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vc)
scoring = yaml.safe_load(open(sys.argv[1], encoding='utf-8'))
config = yaml.safe_load(open(sys.argv[2], encoding='utf-8'))
agg = vc.effective_aggregate(scoring, config)
formula = agg.get('final', {}).get('formula', '0.6*hard + 0.4*soft')
hard, soft = float(sys.argv[3]), float(sys.argv[4])
print(f"{vc.eval_formula(formula, hard, soft):.4f}")
PYEOF
)"

echo "iter-$ITER_NUM: hard=$HARD_SCORE soft=$SOFT_SCORE final=$FINAL_SCORE (best=$BEST_SCORE)"

# ---- ratchet（D8 rule 4：分数相等 = 退化 = revert）----
if python -c "import sys; sys.exit(0 if float(sys.argv[1]) <= float(sys.argv[2]) else 1)" "$FINAL_SCORE" "$BEST_SCORE"; then
  echo "iter-$ITER_NUM: $FINAL_SCORE <= $BEST_SCORE → REVERT（不 commit）"
  git -C "$TARGET_PATH" checkout -q -- .
  exit 0
fi

# ---- accept（rule 3 commit 格式 / rule 8 只记 accepted / rule 9 不 push）----
DESC="hard=$HARD_SCORE soft=$SOFT_SCORE"
git -C "$TARGET_PATH" add -A
git -C "$TARGET_PATH" commit -qm "iter-$ITER_NUM: ${BEST_SCORE}→${FINAL_SCORE}, ${DESC}"
COMMIT_SHA="$(git -C "$TARGET_PATH" rev-parse --short HEAD)"
printf '%s\n%s\n' "$FINAL_SCORE" "$COMMIT_SHA" > "$STATE_DIR/best_score.txt"
printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$ITER_NUM" "$FINAL_SCORE" "$HARD_SCORE" "$SOFT_SCORE" "$COMMIT_SHA" "$DESC" >> "$STATE_DIR/results.tsv"
echo "iter-$ITER_NUM: ACCEPTED ${BEST_SCORE}→${FINAL_SCORE} commit=$COMMIT_SHA"
