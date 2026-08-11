# recursive-tune · 项目语境

> 创建时间：2026-08-11
> 状态：v1 骨架（arch-pivot 后第二稿，含术语 + 版本定位 + 三方法权重）

---

## 是什么

**recursive-tune 是一个让"程序 / 配置 / Skill / 流水线"自己迭代变好的通用框架**。

它的核心思想是：与其手工打磨一个产物（配置、Skill、流水线），不如设计一个**循环**让 agent 在循环里反复生成、评估、保留改进。

两层递归：
- **第一层（use case）**：用框架去优化某个目标产物（如 hindsight config、某个 SKILL.md）—— **v0.1 的实际战场是 A 类目标域（单文件 config / SKILL.md / prompt），不是 multi-agent 流水线**
- **第二层（meta）**：框架本身的设计也按这套循环迭代——**v0.1 仅承诺 meta 层契约（ADR-004），可执行骨架 v0.2 落地**

---

## 不是什么

- **不是 ML 训练**——属于 karpathy autoresearch 的范畴，方法论上有借鉴但不实现
- **不是 Agent harness 框架**——那是 Claude Code / Codex 应用层的事，本框架是应用层之上的"使用说明书"
- **不是单一脚本**——v1 起点是 docs/ 方法论文档 + 一个最小可执行骨架
- **不是 Hermes 内部 skill**——是独立 repo，被任何 agent（包括 Hermes）clone 后使用

---

## 核心术语（glossary）

| 术语 | 含义 | 类比 |
|---|---|---|
| **Target（目标产物）** | 被优化的对象。一个文件、或一组协同的文件/流水线 | autoresearch 的 `train.py`、darwin-skill 的某个 SKILL.md |
| **A 类目标域** | 单文件 / 硬指标主导 / 无需多 agent 协作的目标产物 | 配置调优、prompt 模板迭代、SKILL.md 改写 |
| **C 类目标域** | multi-file / multi-agent 流水线（如 deep-research kanban） | v0.2 才上车 |
| **Loop（循环）** | 一轮「改 → 跑 → 评分 → 决定保留/回滚」 | autoresearch 的实验循环 |
| **Iteration（一轮迭代）** | 一次完整的 Loop 走完 | autoresearch 的一次 commit |
| **Ratchet（棘轮）** | 只升不降的版本控制机制——分数只能上不能下，下来就回滚。**v0.1 实现 = git ratchet**（见 ADR-002） | autoresearch 的 git revert 机制 |
| **Score（评分）** | 可量化的改进指标。**硬指标为主**（测试通过率、recall 噪音率），LLM judge 为辅 | autoresearch 的 `val_bpb`、darwin-skill 的 9 维加权总分 |
| **Hard Signal（硬信号）** | 可由命令直接量化的 signal（如 `pytest` exit code、`grep` 命中数）——必须有，否则 Score 不稳 | darwin-skill 的硬指标主导 |
| **Soft Signal（软信号）** | LLM judge 输出的 signal——可解释但有噪声，必须配 hard signal 才稳定 | darwin-skill 的 9 维加权里的 soft 维度 |
| **Judge（评审员）** | 负责打分的 agent / 脚本。见「隔离约定（profile 级）」 | darwin-skill 的独立 judge |
| **Writer（写手）** | 负责改 Target 的 agent。见「隔离约定（profile 级）」 | autoresearch 里的那个 loop agent |
| **隔离约定（profile 级）** | Writer 和 Judge 之间互不可见；v0.1 用两个独立 Hermes profile 实现（不同 state.db / 不同 skills 可见集 / 不同 plugin 加载），**共享文件系统与 API quota**。**不是字面意义的物理隔离**——darwin-skill 字面意义的"物理隔离"在 v0.1 不强制 | darwin-skill 的物理隔离 writer/judge |
| **Program 模板** | agent 任务指令模板（基于 autoresearch 的 `program.md` 思路）；v0.1 实例化为 A 类目标无感知占位版（详见 `specs/v0.1-skeleton-spec.md` D2） | autoresearch 的 `program.md` |
| **Checkpoint（人在回路节点）** | Loop 在某些关键决策点强制暂停，等人确认才继续 | darwin-skill 的阶段暂停 |
| **State（状态文件）** | 跨 iteration 持久化的产物：哪些已试、哪些失败、当前 best score。**State 是 Ratchet 的状态载体；Ratchet 是 State 的演化规则** | Loop Engineering 的 State（Linear / markdown） |
| **Worktree（工作树）** | 多个并行 loop 不冲突文件。A 类目标下不实例化 | Loop Engineering 的 Worktrees |
| **Iteration Boundary**（meta） | meta 跨版本回滚的粒度——一次 commit 是一次 iteration 还是一个 ADR 是一次？v0.2 决定 | — |
| **Meta Score Validity**（meta） | meta Score 不能仅靠 meta 自身产出验证——必须由第一层独立验证（否则 circular） | — |

---

## 三个源头方法论的权重

| 源头 | 权重 | 借什么 |
|---|---|---|
| **AutoResearch** (Karpathy, 2026-03) | 30% | Ratchet / 单文件可改 / 固定预算 / 无人值守哲学 |
| **Loop Engineering** (Addy Osmani, 2026-06) | 30% | 核心 4 件 + 扩展 3 件（详见 ADR-001）。**注**：Loop Engineering 原版 6 件是平铺并列、不分核心/扩展；4+3 是 recursive-tune 在其基础上的归位与子集划分。详见 ADR-001「核心 4 件的层次定义」段。 |
| **darwin-skill** (alchaincyf, 2026-06) | 40% | 隔离约定 writer/judge / 人在回路 checkpoint / 9 维加权评分 / 阶段暂停 |

darwin-skill 权重最大，因为它的目标域（Skill / prompt / config）最贴近 recursive-tune 实际 use case（A 类目标域）。

---

## 适用边界（按版本定位）

### v0.1（A 类锚点）
- **A 类目标域**（单文件 config / SKILL.md / prompt，硬指标主导）
- 验证用假 Target demo，不指向 deep-research
- skeleton = 核心 4 件（Target / 物理隔离 / Ratchet-State / Program 模板）
- meta 层 v0.1 文档级承诺（ADR-004），可执行骨架不在 v0.1 范围

### v0.2（A + C 探索 + meta 落地）
- 启用扩展 3 件（Worktrees / Plugins / Sub-agents 派发）
- 上车 deep-research（评估后决定）
- meta 层落地可执行骨架

### v0.3（C 类深耕）
- C 类目标域为主战场
- meta 层稳定迭代

### 不覆盖
- ML 训练（karpathy 自己的领地）
- 通用产品功能（不是脚本可验证的）
- UI/UX 类（没硬指标）

---

## 第一个真实目标

参见 `docs/use-cases/deep-research.md`。

原"v0.1 第一阶段只诊断 deep-research"决策已推迟到 v0.2 重新评估（ADR-003）。

---

## 后续 TODO（待 ADR 化）

1. ADR-001：Loop Engineering 核心 4 件 + 扩展 3 件 ✅（commit 1）
2. ADR-002：Ratchet 替代覆盖式写入 ✅
3. ADR-003：deep-research 首目标 — 状态推迟 ✅（commit 2）
4. ADR-003.5：A 类作为 v0.1 唯一目标域 ✅（commit 2 末尾追加）
5. ADR-004：meta 层契约（v0.1 承诺，v0.2 执行）✅（commit 3）
6. ADR-005：v0.2 扩展 3 件启用条件（待 v0.1 验证后写）
7. meta Score Glossary 静态化方案（v0.2 决策，详见 ADR-004 Open Issue）
