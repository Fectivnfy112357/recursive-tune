# ADR-001 · 用 Loop Engineering 作为骨架（核心 4 件 + 扩展 3 件）

**状态**：提议（2026-08-11 grilling 收口后；2026-08-11 arch-pivot 修订）
**关联**：CONTEXT.md
**修订记录**：2026-08-11 改为"核心集合 4 件 + 扩展集合 3 件"——6 件套不变，归位表也不变；新增"按目标域类别实例化"机制，避免下游误读成 6 件全装。

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

**采用 Loop Engineering 的 6 件套作为骨架集合**，但分两个**子集合**：

### 核心集合（4 件，必装）

任何版本、任何目标域都必须实例化的 4 件：

1. **Target**——被优化的对象
2. **物理隔离**（writer / judge 互不可见）
3. **Ratchet + State**——ratchet 是"只升不降"的版本控制机制；State 是 ratchet 演化的辅助（results.tsv / best score 指针 / eval 集）
4. **Program 模板**——agent 的任务指令模板（基于 autoresearch 的 `program.md` 思路）

### 扩展集合（3 件，按目标域类别启用）

不同目标域类别按下表选择性实例化——**A 类目标不装**（v0.1 的实际战场），**C 类目标必装**：

| 扩展件 | A 类（单文件 config / SKILL.md / prompt） | C 类（multi-file / multi-agent 流水线） |
|---|---|---|
| Worktrees | 不实例化（git ratchet 隐式承担） | 实例化 |
| Plugins | 不实例化 | 实例化（hook / adapter） |
| Sub-agents 派发 | 不实例化（仅 writer / judge 两个 profile） | 实例化（coordinator 派生子 agent） |

理由：
1. **覆盖度最广**——AutoResearch 的单文件、darwin-skill 的 writer/judge 都能落到"Sub-agents"组件里，但 Sub-agents 在 A 类是"profile 级隔离"、在 C 类才是"派发"
2. **版本纪律清晰**——6 件套是**全集**，v0.1 spec 只宣告 A 类下实例化 4 件；v0.2+ 按目标域类别扩展
3. **避免下游误读**——之前的版本直接说"6 件套为骨架"，导致下游 spec 把 6 件全写进 v0.1 文件树，Worktrees / Plugins 沦为"空壳结构"。本次修订把"全集 vs 实例化集"切开

### A 类目标域（一句话定义，供后续 ADR 引用）

**A 类目标域**指：单文件 / 硬指标主导 / 无需多 agent 协作的目标产物。典型场景：配置调优、prompt 模板迭代、SKILL.md 改写。

---

## AutoResearch 元素的归宿

| AutoResearch 元素 | 在 Loop Engineering 骨架里落到哪 |
|---|---|
| `prepare.py`（read-only 基础） | 不在 6 件里。**作为 Target 的"环境基线"概念单独存在**——任何 Target 都依赖一个不可变环境 |
| `train.py`（agent 改的文件） | **Target 本身**——是 Sub-agent（writer）的操作对象 |
| `program.md`（人写 skill） | **Program 模板（核心）**——recursive-tune 必须自带一份 `program.md` 模板 |
| git ratchet（只升不降） | **核心（Ratchet + State 组件的一部分）**——ratchet 是 State 文件的演化规则 |
| 5 分钟固定预算 | **进 Automations 配置项**（核心）——不是核心架构，而是可调参数 |
| 单文件约束 | **不强制**——支持 multi-file 是 recursive-tune 的关键差异 |

---

## darwin-skill 元素的归宿

| darwin-skill 元素 | 在 Loop Engineering 骨架里落到哪 |
|---|---|
| Writer agent（物理隔离） | **核心（物理隔离组件）**；A 类下用独立 Hermes profile 实现 |
| Judge agent（独立打分） | **核心（物理隔离组件）**；A 类下用独立 Hermes profile 实现 |
| Checkpoint（阶段暂停） | **不进核心**，是物理隔离组件在 A 类下的运行时约定 |
| 9 维加权评分 | **Score 的具体设计模式**——v1 沿用 darwin-skill 的 9 维结构，但允许 target-specific 自定义（详见 `specs/v0.1-skeleton-spec.md` D3） |
| 实测数据集 | **核心（Ratchet + State 组件的一部分）**——`tests.json` 或 `eval-prompts.json` 是 State 的内容 |

---

## 后果

- **核心 4 件必须 v0.1 实现**——任何版本、任何目标域都必须实例化
- **扩展 3 件按目标域类别启用**——具体启用关系写进各版本 spec 的 D4 文件树 / 组件表
- **AutoResearch / darwin-skill 的元素**不被丢掉，而是归位到全集里——A 类目标下"6 件"折叠为"4 件实例化 + 2 件空缺"；C 类目标下保持全 6 件
- **写 ADR-002 / ADR-003 时**要直接引用本 ADR 的"核心集合 + 扩展集合"措辞，不要重新发明术语
- **"A 类目标域"** 是 ADR-003.5 末尾追加时引用的父术语，定义见上文

---

## 备选方案（被否决）

| 备选 | 否决理由 |
|---|---|
| 以 AutoResearch 为骨架 | 单文件约束不支持 multi-file / multi-agent，deep-research 用不上 |
| 以 darwin-skill 为骨架 | 偏 Skill 优化，没有 multi-file 概念，没有 State 概念 |
| 6 件套全集必装 | v0.1 写成"1 yaml + 3 shell + 6 件全装" → Worktrees/Plugins/Sub-agents 沦为空壳；2026-08-11 arch-pivot 已否决 |
| 三件套并列，不分主次 | 落地时无法决定"先实现哪个"，陷入分析瘫痪 |
