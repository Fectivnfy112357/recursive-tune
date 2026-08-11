# ADR-003 · 第一个真实目标：deep-research kanban

**状态**：提议
**关联**：ADR-001（骨架）、CONTEXT.md（目标范围）

---

## 背景

recursive-tune 要避免"框架脱离实际需求"。第一个真实目标是 `C:\Users\32115\AppData\Local\hermes\docs\deep-research\` 下已存在的 kanban 团队，但**之前用户已经做过两轮优化尝试**：

- v3 流水线设计 → `team-v3-design.md` / `team-v3-spec.md`
- omega-opt 优化 → `auto-optimization-plan.md` + `auto-optimization-result-20260807.md` + `auto-opt-validation-20260807.md`
- 复盘问题 → `known-issues-from-{mixue,multagent-research,omega-opt}.md` 3 份

新框架不是替代这些工作，而是**让未来第三轮优化（如果有）能用 recursive-tune 的循环来做**。

---

## 决策

**第一阶段只做诊断**——用 recursive-tune 框架的视角审一遍现有 deep-research 历史，输出**缺什么基础设施才能跑通循环**的清单。不动 deep-research 本身。

诊断要回答三个问题：
1. **当前 deep-research 有什么可量化 Score？**（沿用之前 30min→≤10min 的时间成本？还是要新增"产出质量"、"协作效率"等维度？）
2. **Writer / Judge 如何隔离？** 当前 14 个 md + 7 个 scripts 里有现成的吗？还是都要新建？
3. **State 怎么持久化？** 已有 `results.tsv` 类的东西吗？

---

## 评估已有产物

| 已有产物 | 对 recursive-tune 的可复用性 |
|---|---|
| `auto-optimization-plan.md` (v3, P0/P1/P2) | **可作为 Score 维度的输入**——P0 级别的"流超时 600→120s"是具体可量化的硬指标 |
| `auto-optimization-result-20260807.md` (5/5 静态验证) | **可作为基线 score**——5/5 通过是初始状态 |
| `auto-opt-validation-20260807.md` (v3.1 待办) | **可作为下一轮 Loop 的候选 action 列表**——但要意识到这些待办是"人手优化"思路，不一定能在 Loop 里自动做到 |
| `known-issues-from-*.md` (3 份) | **可作为 Score 维度的反向参考**——"已知问题消失"是改进信号 |
| `provider-benchmark-20260807.json` | **Score 体系的有用输入**——provider 选择已是量化决策 |

---

## 第一阶段交付物（不属于本次任务，留作 TODO）

> 以下是"如果第一阶段诊断说'能做'，下一步要交付什么"——**不在本次范围**，只是占位

- `deep-research/program.md`（基于现有 v3 spec 写一份给 agent 的指令）
- `deep-research/scoring.yaml`（9 维评分定义）
- `deep-research/results.tsv`（初始 baseline）
- `deep-research/judge-prompt.md`（Judge agent 的 prompt 模板）

---

## 后果

- **本 ADR 不动 deep-research 任何文件**——grilling 收口时用户明确说"我现在不想动 deep-research 现状"
- **本 ADR 的价值是把"第一目标"明确化**——后续任何 v0.1 脚本设计都要回头看这 ADR，确认是否在为 deep-research 服务
- **避免和"omega-opt"重复**——之前的优化尝试是手工的，本框架是循环的；两者是替代关系，不是补充关系

---

## 备选方案（被否决）

| 备选 | 否决理由 |
|---|---|
| 直接用 recursive-tune 框架改造 deep-research | 用户没要求动 deep-research；强行做容易破坏现有工作 |
| 选另一个更简单的目标（如 hindsight config） | hindsight 已做过完整调优，没有"待优化"空间；deep-research 才有真正的 use case |
| 不指定第一个目标 | 框架会变成空架子，没有验证锚点 |