# Use Case · deep-research kanban

> 状态：v0.2 探索性目标（2026-08-11 arch-pivot 修订）
> 关联：ADR-003（推迟到 v0.2 重新评估）

本文件承接原 `docs/CONTEXT.md` 末尾「第一个真实目标」段搬出的 deep-research 历史清单。**仅作占位与历史资料索引**，不对应 v0.1 工作。

## 历史文件清单

源路径：`C:\Users\32115\AppData\Local\hermes\docs\deep-research\`

| 文件 | 内容摘要 |
|---|---|
| `team-v3-design.md` | v3 流水线设计方案 |
| `team-v3-spec.md` | v3 流水线 spec |
| `auto-optimization-plan.md` | v3 流水线 30min → ≤10min 优化方案（P0/P1/P2 分级） |
| `auto-optimization-result-20260807.md` | omega-opt 静态验证 5/5 通过 |
| `auto-opt-validation-20260807.md` | v3.1 优化待办 |
| `known-issues-from-mixue.md` | 从 mixue 项目复盘的已知问题 |
| `known-issues-from-multagent-research.md` | 从 multagent-research 复盘的已知问题 |
| `known-issues-from-omega-opt.md` | 从 omega-opt 复盘的已知问题 |
| `provider-benchmark-20260807.json` | provider 选择基准数据 |

## v0.1 不动 deep-research

v0.1 范围严格圈定为 A 类目标域（单文件 config / SKILL.md / prompt），详见 ADR-001 / ADR-003.5。

**v0.1 不挂任何与 deep-research 相关的 ticket**——具体见 `specs/v0.1-skeleton-spec.md` 修订后的 D6 / User Stories。

deep-research 真上车时（v0.2 评估）：启用 ADR-001 的扩展 3 件（Worktrees / Plugins / Sub-agents 派发），改 C 类下骨架。
