# ADR-001 · 用 Loop Engineering 作为骨架

**状态**：提议（2026-08-11 grilling 收口后）
**关联**：CONTEXT.md

---

## 背景

recursive-tune 要融合三个方法论（AutoResearch、Loop Engineering、darwin-skill），它们在「一个循环由哪些部分组成」这件事上给出了不同答案：

| 源头 | 一个 loop 由什么组成 |
|---|---|
| AutoResearch | prepare.py（不变）+ train.py（agent 改）+ program.md（人写 skill）+ git ratchet + 单文件 + 5 分钟固定预算 |
| Loop Engineering | Automations + Worktrees + Skills + Plugins + Sub-agents + State（6 件） |
| darwin-skill | Writer agent（物理隔离）+ Judge agent（独立打分）+ Checkpoint（阶段暂停）+ Ratchet + 实测数据集 |

**问题是**：以哪一套为骨架，其他两套的元素作为可选项叠加？

---

## 决策

**以 Loop Engineering 的 6 件套为骨架**（Automations / Worktrees / Skills / Plugins / Sub-agents / State）。

理由：
1. **覆盖度最广**——AutoResearch 的单文件、darwin-skill 的 writer/judge 都能落到"Sub-agents"组件里，不需要另外发明新概念
2. **明确支持 multi-file / multi-agent**——这是第一个真实目标（deep-research kanban）的要求，AutoResearch 和 darwin-skill 都偏单文件
3. **Addy Osmani 的产出最贴近产品级**——Codex / Claude Code 都把 6 件内置了，意味着这套定义已经被验证

---

## AutoResearch 元素的归宿

| AutoResearch 元素 | 在 Loop Engineering 骨架里落到哪 |
|---|---|
| `prepare.py`（read-only 基础） | 不在 6 件里。**作为 Target 的"环境基线"概念单独存在**——任何 Target 都依赖一个不可变环境 |
| `train.py`（agent 改的文件） | **Target 本身**——是 Sub-agent（writer）的操作对象 |
| `program.md`（人写 skill） | **Skills 组件的具体实现**——recursive-tune 必须自带一份 `program.md` 模板 |
| git ratchet（只升不降） | **不进 6 件核心，但作为 State 的版本控制机制**——ratchet 是 State 文件的演化规则 |
| 5 分钟固定预算 | **进 Automations 配置项**——不是核心架构，而是可调参数 |
| 单文件约束 | **不强制**——支持 multi-file 是 recursive-tune 的关键差异 |

---

## darwin-skill 元素的归宿

| darwin-skill 元素 | 在 Loop Engineering 骨架里落到哪 |
|---|---|
| Writer agent（物理隔离） | **Sub-agents 组件**，且是强制约定 |
| Judge agent（独立打分） | **Sub-agents 组件**，且物理隔离是 hard rule |
| Checkpoint（阶段暂停） | **不进 6 件核心，但作为 Sub-agent 的运行时约定**——某些 Score 维度需要人在回路 |
| 9 维加权评分 | **Score 的具体设计模式**——v1 沿用 darwin-skill 的 9 维结构，但允许 target-specific 自定义 |
| 实测数据集 | **State 组件的具体内容**——`tests.json` 或 `eval-prompts.json` 是 State 的一部分 |

---

## 后果

- **6 件套的最小实现**——recursive-tune v1 必须能跑通这 6 个组件（即使某些是 stub）
- **AutoResearch / darwin-skill 的元素**不被丢掉，而是归位到 6 件里——这样新框架不是"三选一"，而是"一个骨架 + 两套补强"
- **写 ADR-002 / ADR-003 时**要直接引用本 ADR 的元素归位表，不要重新发明术语

---

## 备选方案（被否决）

| 备选 | 否决理由 |
|---|---|
| 以 AutoResearch 为骨架 | 单文件约束不支持 multi-file / multi-agent，deep-research 用不上 |
| 以 darwin-skill 为骨架 | 偏 Skill 优化，没有 multi-file 概念，没有 State 概念 |
| 三件套并列，不分主次 | 落地时无法决定"先实现哪个"，陷入分析瘫痪 |