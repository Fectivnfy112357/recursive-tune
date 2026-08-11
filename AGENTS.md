# recursive-tune · Agent Working Agreement

> Created 2026-08-11 via `/setup-matt-pocock-skills`.
> Updated 2026-08-11（arch-pivot 同步）：明确 v0.1 = A 类目标域、A 类下骨架仅实例化核心 4 件（详见 ADR-001）。

## Version anchor（agent 一进入先看这一段）

**v0.1 = A-class target domain**——单文件 config / SKILL.md / prompt，硬指标主导。详见 `docs/CONTEXT.md` §适用边界 + ADR-001（核心 4 件 + 扩展 3 件）+ `docs/specs/v0.1-skeleton-spec.md`。

| 关键决策 | 文件 |
|---|---|
| 骨架 = 核心 4 件 + 扩展 3 件（A 类不实例化扩展） | `docs/adr/ADR-001-loop-engineering-as-skeleton.md` |
| Ratchet 替代覆盖式写入 | `docs/adr/ADR-002-ratchet-over-mutation.md` |
| deep-research 首目标推迟到 v0.2 | `docs/adr/ADR-003-first-target-deep-research.md` |
| v0.1 锚定 A 类目标域 | `docs/adr/ADR-003-first-target-deep-research.md` 末尾 ADR-003.5 |
| Meta 层契约 v0.1 文档级 / v0.2 可执行 | `docs/adr/ADR-004-meta-layer-target.md` |
| v0.1 spec / 评分维度 / hard rules | `docs/specs/v0.1-skeleton-spec.md` |

实现 v0.1 ticket 时若发现需要 Worktrees / Plugins / Sub-agents 派发，**该 ticket 属于 v0.2 范围**，不应在 v0.1 实施。

## Agent skills

### Issue tracker
GitHub Issues at https://github.com/Fectivnfy112357/recursive-tune (default branch `main`). Use the `gh` CLI for all ops. See `docs/agents/issue-tracker.md`.

### Domain docs
Single-context layout: `docs/CONTEXT.md` (glossary + version anchor) + `docs/adr/` (ADRs) + `docs/use-cases/` (v0.2+ exploration). See `docs/agents/domain.md`.

### Triage labels
Not configured as a full taxonomy. The `triage` skill is installed but the repo currently has no inbound external-issue flow (only self-authored specs/tickets via `to-spec` → `to-tickets`). `triage` will use its built-in defaults if ever invoked. Add `docs/agents/triage-labels.md` only when external issues actually start arriving.

**Note on `ready-for-agent`**: the `/to-spec` skill applies this label directly on the issue it publishes — that one label is owned by `to-spec` and does not require triage-labels.md to be set up first. Anything beyond that label belongs to the triage taxonomy and follows the rule above.
