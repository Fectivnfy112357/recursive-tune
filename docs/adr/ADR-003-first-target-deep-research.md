# ADR-003 · 第一个真实目标：deep-research kanban（推迟到 v0.2）

**状态**：推迟（2026-08-11 arch-pivot 修订）
**原版**：2026-08-11 grilling 收口后"提议"状态
**关联**：ADR-001（骨架）、CONTEXT.md（目标范围）、ADR-003.5（A 类目标域）

---

## 背景（沿用原版）

recursive-tune 要避免"框架脱离实际需求"。原版第一个真实目标是 `C:\Users\32115\AppData\Local\hermes\docs\deep-research\` 下已存在的 kanban 团队，但**之前用户已经做过两轮优化尝试**：

- v3 流水线设计 → `team-v3-design.md` / `team-v3-spec.md`
- omega-opt 优化 → `auto-optimization-plan.md` + `auto-optimization-result-20260807.md` + `auto-opt-validation-20260807.md`
- 复盘问题 → `known-issues-from-{mixue,multagent-research,omega-opt}.md` 3 份

deep-research 历史文件清单已迁移至 `docs/use-cases/deep-research.md`，本 ADR 不再列举。

---

## 决策（2026-08-11 修订）

**v0.1 锚点 = 假 Target demo 跑通（A 类下）；不绑真实 first target，deep-research 推迟到 v0.2 重新评估是否上车。**

理由：
1. **v0.1 锚点改 A 类**——A 类（单文件 config / SKILL.md / prompt）有现成的硬指标、能用假 Target demo 跑通；deep-research 是 C 类（multi-file / multi-agent 流水线），其验证锚点与 v0.1 扩展集合（核心 4 件实例化）不相容
2. **避免 v0.1 spec 与 ADR-001 决策锚点脱节**——原版"首目标是 deep-research（C 类）" + v0.1 spec 的 A 类骨架会形成"骨架不验证首目标"的悬空决策
3. **deep-research 现状不应被破坏**——之前两轮优化尝试是手工的（omega-opt），本框架是循环的；v0.1 不动 deep-research，v0.2 评估"是否上车"再决定

诊断范围（在 v0.2 阶段）：current deep-research 有什么可量化 Score、Writer / Judge 如何隔离、State 怎么持久化。

---

## 评估已有产物（保留供参考，本节非本 ADR 决策）

| 已有产物 | 对 recursive-tune 的可复用性 |
|---|---|
| `auto-optimization-plan.md` (v3, P0/P1/P2) | **可作为 Score 维度的输入**——P0 级别的"流超时 600→120s"是具体可量化的硬指标 |
| `auto-optimization-result-20260807.md` (5/5 静态验证) | **可作为基线 score**——5/5 通过是初始状态 |
| `auto-opt-validation-20260807.md` (v3.1 待办) | **可作为下一轮 Loop 的候选 action 列表**——但要意识到这些待办是"人手优化"思路，不一定能在 Loop 里自动做到 |
| `known-issues-from-*.md` (3 份) | **可作为 Score 维度的反向参考**——"已知问题消失"是改进信号 |
| `provider-benchmark-20260807.json` | **Score 体系的有用输入**——provider 选择已是量化决策 |

文件清单见 `docs/use-cases/deep-research.md`。

---

## v0.2 阶段交付物（占位，不在本 ADR 决策）

> 以下是"如果 v0.2 评估说'能做'，下一步要交付什么"——**不在本 ADR 范围**，留作占位；占位路径，实际目录 / 文件名以 v0.2 评估时为准

- `deep-research/program.md`（基于现有 v3 spec 写一份给 agent 的指令）
- `deep-research/scoring.yaml`（C 类 Score 维度定义）
- `deep-research/results.tsv`（初始 baseline）
- `deep-research/judge-prompt.md`（Judge agent 的 prompt 模板）

---

## 后果

- **v0.1 不挂任何与 deep-research 相关的 ticket**——具体见 `specs/v0.1-skeleton-spec.md` 修订后的 D6 / User Stories
- **deep-research 本体文件不被动**——本 ADR 修订前的"诊断清单"也仅是参考
- **v0.2 决策依据**：v0.1 跑通的 A 类骨架能否扩展到 C 类（启用扩展 3 件）；deep-research 团队是否还有"待优化"空间（之前已两轮手工优化）

---

## 备选方案（被否决）

| 备选 | 否决理由 |
|---|---|
| 直接用 recursive-tune 框架改造 deep-research | v0.1 锚点 A 类；强行动 C 类破坏 v0.1 验证锚点 |
| 选另一个更简单的目标（如 hindsight config） | hindsight 已做过完整调优，没有"待优化"空间 |
| 不指定第一个目标 | 框架会变成空架子，没有验证锚点 |
| **v0.1 同时绑 A 类 + deep-research**（原版倾向） | 双锚点验证混乱，spec 含糊 |

---

# ADR-003.5 · A 类作为 v0.1 唯一目标域（追加于 2026-08-11）

**状态**：确认
**关联**：ADR-001（核心集合 4 件 + 扩展集合 3 件）

---

## 决策

**v0.1 的"目标产物"严格圈定为 A 类目标域——单文件 / 硬指标主导 / 无需多 agent 协作。**

定义见 ADR-001「A 类目标域（一句话定义）」：
> **A 类目标域**指：单文件 / 硬指标主导 / 无需多 agent 协作的目标产物。典型场景：配置调优、prompt 模板迭代、SKILL.md 改写。

按 ADR-001 的实例化机制，**A 类下骨架只实例化核心 4 件**：
- Target
- 隔离约定（profile 级，writer / judge 两个独立 Hermes profile）
- Ratchet + State
- Program 模板

**A 类下不实例化扩展 3 件**（Worktrees / Plugins / Sub-agents 派发）。

---

## 后果

- v0.1 spec 的 D4 文件树只列核心 4 件对应的 artifacts；Worktrees / Plugins / Sub-agents 三件标"A 类：不启用"
- v0.1 验证用假 Target demo（一个能跑通 happy path / ratchet / commit-revert 流程的最小 Python repo），不指向 deep-research
- deep-research 真上车是 v0.2 范围——届时启用扩展 3 件、改 C 类下骨架
