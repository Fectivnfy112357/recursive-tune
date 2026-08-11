# recursive-tune · 项目语境

> 创建时间：2026-08-11
> 状态：v0 骨架（grilling 收口后第一稿，仅术语 + 范围）

---

## 是什么

**recursive-tune 是一个让"程序 / 配置 / Skill / 流水线"自己迭代变好的通用框架**。

它的核心思想是：与其手工打磨一个产物（配置、Skill、流水线），不如设计一个**循环**让 agent 在循环里反复生成、评估、保留改进。

两层递归：
- **第一层（use case）**：用框架去优化某个目标产物（如 deep-research kanban、hindsight config、某个 SKILL.md）
- **第二层（meta）**：框架本身的设计也按这套循环迭代——每次跑出一份改进经验，反过来沉淀到方法论文档

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
| **Loop（循环）** | 一轮「改 → 跑 → 评分 → 决定保留/回滚」 | autoresearch 的实验循环 |
| **Iteration（一轮迭代）** | 一次完整的 Loop 走完 | autoresearch 的一次 commit |
| **Ratchet（棘轮）** | 只升不降的版本控制：分数只能上不能下，下来就回滚 | autoresearch 的 git revert 机制 |
| **Score（评分）** | 可量化的改进指标。**硬指标为主**（测试通过率、recall 噪音率），LLM judge 为辅 | autoresearch 的 `val_bpb`、darwin-skill 的 9 维加权总分 |
| **Judge（评审员）** | 负责打分的 agent / 脚本。**与 writer 物理隔离**（不让自己评自己） | darwin-skill 的物理隔离 writer/judge |
| **Writer（写手）** | 负责改 Target 的 agent | autoresearch 里的那个 loop agent |
| **Checkpoint（人在回路节点）** | Loop 在某些关键决策点强制暂停，等人确认才继续 | darwin-skill 的阶段暂停 |
| **State（状态文件）** | 跨 iteration 持久化的产物：哪些已试、哪些失败、当前 best score | Loop Engineering 的 State（Linear / markdown） |
| **Worktree（工作树）** | 多个并行 loop 不冲突文件 | Loop Engineering 的 Worktrees |

---

## 三个源头方法论的权重

| 源头 | 权重 | 借什么 |
|---|---|---|
| **AutoResearch** (Karpathy, 2026-03) | 30% | Ratchet / 单文件可改 / 固定预算 / 无人值守哲学 |
| **Loop Engineering** (Addy Osmani, 2026-06) | 30% | 五大组件（Automations / Worktrees / Skills / Plugins / Sub-agents）+ State 持久化 |
| **darwin-skill** (alchaincyf, 2026-06) | 40% | 物理隔离 writer/judge / 人在回路 checkpoint / 9 维加权评分 / 阶段暂停 |

darwin-skill 权重最大，因为它的目标域（Skill / prompt / config）最贴近 recursive-tune 的实际 use case。

---

## 适用边界

**v1 收口**：
- **A 类（首要）**：单文件 + 有可量化指标——config 文件、prompt 模板、SKILL.md
- **B 类（次要）**：小脚本 / 小工具——Python 脚本 + 单测能跑通
- **C 类（探索性）**：multi-file / multi-agent 流水线——如 deep-research kanban，这是个 stretch goal，不保证 v1 完美支持

**明确不覆盖**：
- ML 训练（karpathy 自己的领地）
- 通用产品功能（不是脚本可验证的）
- UI/UX 类（没硬指标）

---

## 第一个真实目标

**deep-research kanban 团队**（在 `C:\Users\32115\AppData\Local\hermes\docs\deep-research\` 下有完整历史）。

已有的历史资料（不应丢失，新框架要兼容/复用）：
- `auto-optimization-plan.md` — v3 流水线 30min→≤10min 优化方案
- `auto-optimization-result-20260807.md` — omega-opt 静态验证 5/5 通过
- `auto-opt-validation-20260807.md` — v3.1 优化待办
- `known-issues-from-{mixue,multagent-research,omega-opt}.md` — 已知问题集

**新框架的工作方式**：把这套历史作为第一批 Score 候选维度（时间成本、产出质量、多 agent 协作），先写一份**诊断**：当前缺什么能跑通 recursive-tune 循环的基础设施。

---

## 后续 TODO（待 ADR 化）

1. ADR-001：Loop Engineering 作为骨架
2. ADR-002：Ratchet 替代覆盖式写入
3. ADR-003：Writer/Judge 物理隔离
4. ADR-004：人回路 checkpoint 在哪些节点强制
5. ADR-005：第一个真实目标——deep-research kanban 的具体 Score 维度
6. ADR-006：与已有 deep-research 优化历史的关系（保留 / 引用 / 整合）