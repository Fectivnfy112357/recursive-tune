#!/usr/bin/env bash
# 创建 writer / judge 两个 Hermes profile（spec D1：隔离约定 profile 级——
# 不同 state.db / 不同 skills 可见集 / 不同 plugin 加载；共享文件系统与 API quota）。
# 幂等：profile 已存在则跳过。
set -euo pipefail

HERMES_HOME="${HOME}/AppData/Local/hermes"
DEFAULT_ENV="${HERMES_HOME}/.env"
DEFAULT_MODEL="$(hermes config get model.default 2>/dev/null || echo deepseek-v4-flash)"
DEFAULT_PROVIDER="$(hermes config get model.provider 2>/dev/null || echo opencode-go)"

create_profile() {
  local name="$1"
  if hermes profile list 2>/dev/null | grep -qE "^[[:space:]]+${name}[[:space:]]"; then
    echo "profile '${name}' already exists — skip"
  else
    hermes profile create "${name}" --no-skills >/dev/null
    # 继承 default 的 provider / 模型（spec D5：profile 在用户已有配置下正常工作）
    hermes -p "${name}" config set model.default "${DEFAULT_MODEL}" >/dev/null
    hermes -p "${name}" config set model.provider "${DEFAULT_PROVIDER}" >/dev/null
    # 继承 default 凭据（D1：共享 API quota）
    cp "${DEFAULT_ENV}" "${HERMES_HOME}/profiles/${name}/.env"
    echo "profile '${name}' created"
  fi
}

create_profile writer
create_profile judge

# 验证隔离（spec D1）：两个 profile 目录都存在且路径不同
# （state.db 首次使用会话时才生成；目录不同即 state.db 路径不同）
if [ ! -d "${HERMES_HOME}/profiles/writer" ] || [ ! -d "${HERMES_HOME}/profiles/judge" ]; then
  echo "ERROR: writer/judge profile 目录不存在——隔离验证失败" >&2
  exit 1
fi
if [ "${HERMES_HOME}/profiles/writer" = "${HERMES_HOME}/profiles/judge" ]; then
  echo "ERROR: writer/judge profile 目录相同 — isolation broken" >&2
  exit 1
fi
echo "isolation ok (profiles/writer ≠ profiles/judge → state.db 路径必然不同):"
echo "  writer: ${HERMES_HOME}/profiles/writer/state.db"
echo "  judge:  ${HERMES_HOME}/profiles/judge/state.db"
