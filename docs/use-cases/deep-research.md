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

## v0.2 启动决策的已知材料索引

> 性质:非 ADR,不固化决策。use-case 沉淀(对照 `docs/reviews/2026-08-11-opus-architecture-review.md` §保留 2 的判断:写成 ADR 会把待定问题提前固化为决策草案,违反 ADR 只记已决事项的纪律)。

### 0. 段说明

本段沉淀 v0.2 接手 deep-research 评估时**该带着哪些材料 + 该先回答哪些问题**——非 ADR,不固化决策。段内只列候选 / trigger / 待回答问题,不写"决定用 X"。

### 1. 候选 Score 维度

| 候选维度 | 来源材料 | 类型 | 备注 |
|---|---|---|---|
| 流超时时间(目标 30min → ≤10min) | `auto-optimization-plan.md` P0 段 | hard(候选)— 需先有测量命令 + fixture-set(Q5) | 原 omega-opt 已做到 5/5 静态验证,**该硬指标的命令形态在 v0.2 第一次实跑时定** |
| 静态验证通过率(基线 5/5) | `auto-optimization-result-20260807.md` | hard(候选)— 命令形态待定 | 是初始 baseline,被超过算改进 |
| v3.1 待办覆盖率(已知优化点关闭率) | `auto-opt-validation-20260807.md` | soft — 待办是"人手优化"思路,Loop 里能自动做到的占比待评估 | **不能直接当 hard**:v3.1 待办是描述性,不全是可机械判定的 |
| 已知问题消失率 | `known-issues-from-{mixue,multagent-research,omega-opt}.md` 三份 | soft — 反向信号 | "已知问题消失"是改进信号,但"消失"难自动检测 |
| Provider 选择一致性 | `provider-benchmark-20260807.json` | soft — 数据驱动的决策 | 适合做候选 baseline,不当 hard |
| 多 agent 协作效率 | (待 v0.2 评估时定义) | 维度名占位 | 多 agent 协作指标难量化,**先不锁** |

> **路径注意**:`provider-benchmark-20260807.json` 不在 recursive-tune 仓库(在 hermes 用户目录),引用时只指路径,不复制内容。

### 2. 候选硬信号命令

| 候选命令 | 测什么 | 触发频率 | fixture-set 来源 |
|---|---|---|---|
| 流超时测量命令(待定) | P0 端到端时间 | 每轮 iter | 需构造(deep-research 当前没有"已知 baseline 命令") |
| 静态验证套件命令(待定) | `auto-optimization-result-20260807.md` 提到的 5/5 通过项 | 每轮 iter | 需把 5 项翻译成可重复命令 |
| Provider 调用统计(可脚本化) | 调用次数 / 平均耗时 / 失败率 | 每轮 iter | `provider-benchmark-20260807.json` 是 baseline |

> **Q5 适用**:`docs/use-cases/text-target-hard-signal.md` §Q5 的 fixture-set 验证同样适用于 deep-research 的 hard signal——任何 deep-research hard signal 命令必须先过 fixture-set 才能进 `scoring.yaml`。

### 3. 扩展 3 件候选 trigger(ADR-005 写入依据)

| 扩展件 | 何时该上车 | 在 deep-research 下的具体触发场景(候选) |
|---|---|---|
| **Worktrees** | 单 writer 串行不够,需要并行分支探索 | deep-research 流水线有多版本候选(plan 的 P0/P1/P2 可能是并行分支)— **v0.2 评估时判断 deep-research 实际场景是否需要并行** |
| **Plugins** | 需要外部 hook / adapter 接入 | deep-research 用了多 provider(从 `provider-benchmark-20260807.json` 看)— **provider 切换是否需要 plugin 抽象?还是直接换配置?** |
| **Sub-agents 派发** | coordinator 派生子 agent 协同工作 | deep-research 本身是 multi-agent 流水线(从 `team-v3-design.md` / `team-v3-spec.md` 推断)— **这是 C 类最可能必装的扩展件**;但 Sub-agents 派发的具体 coordinator 接口规格 ADR-005 必须先写 |

> **ADR-005 写入时机**:v0.2 第 5 周草稿(参见 handoff 进度);本表是 ADR-005 的输入材料,**不是 ADR-005 本身**。

### 4. 待 v0.2 评估回答的问题

> 本节合并原"v0.2 评估时复核"段的 3 条问题(避免重复),扩展到 6 条:

1. **deep-research 还能优化吗 / 第三轮 ROI 如何** — 之前已两轮手工优化(omega-opt),第三轮上 Loop 是否还有空间?判断依据:本段 §1 Score 维度的当前值 vs omega-opt 后的值
2. **v3.1 待办里哪些是 Loop 友好 / 哪些必须人手** — `auto-opt-validation-20260807.md` 列出 v3.1 待办,逐条判定是否可脚本化进 Loop;**人手才能做的事不进 hard signal**
3. **profile 级隔离在 C 类下够不够,什么时候升级 Docker** — C 类下 writer / judge / coordinator 三方隔离需求,A 类的 profile 级隔离(v0.1 spec D1)是否够,什么时候必须加容器级
4. **meta 第一层在 deep-research 上如何避免 circular** — Meta Score Validity(ADR-004 Open Issue)要求 meta Score 必须由第一层独立验证;**C 类 deep-research 的第一层跑出来能否充当 meta 的独立验证集**?
5. **Q5 fixture-set 验证在 C 类 hard signal 上是否同样适用** — 协议当前以 A 类文本 Target 为驱动写的(deep-research 是 C 类 multi-agent);**Q5 在 C 类下需要哪些调整**(multi-agent 协同产出的 ground truth 怎么造)?
6. **deep-research 上车时 spec D4 文件树的具体形态** — v0.1 spec D4 是 A 类下的 4 件实例化;C 类下扩展 3 件 + 可能的 Sub-agents 接口,文件树会长什么样

### 5. 与 v0.1 已落骨架的关系

| v0.1 已落件 | C 类下复用 | 必须改 | 必须新增 |
|---|---|---|---|
| **Target**(v0.1 spec D4) | ✓ 直接复用——deep-research 整个仓库就是一个 Target | 无 | 无 |
| **隔离约定 (profile 级)**(D1) | ⚠ 部分复用——v0.1 是 writer/judge 两 profile,C 类下需 coordinator profile | profile 数量从 2 → 3+(writer / judge / coordinator) | coordinator profile 的 setup 脚本 |
| **Ratchet + State**(D8) | ✓ 直接复用——git ratchet + `state/results.tsv` 在 C 类下仍成立 | 无 | C 类下需要"多 Target 并行"的 State 切分(每个并行分支一份 results.tsv?还是合并?) |
| **Program 模板**(D2) | ✓ 复用 templates/program.md.template | 无 | C 类下需 coordinator 的 program 模板 |
| **Worktrees**(扩展 3 件,A 类不装) | — | — | C 类必装,需 v0.2 评估具体形态(per-branch worktree? per-iteration worktree?) |
| **Plugins**(扩展 3 件) | — | — | C 类必装,需 ADR-005 写明 trigger |
| **Sub-agents 派发**(扩展 3 件) | — | — | C 类必装,coordinator 接口是 deep-research 上车的关键 |

### 6. 已知悬而未决(显式占位,防止下游误以为已锁)

| # | 悬而未决 | 触发解决时机 |
|---|---|---|
| H1 | ADR-005 扩展 3 件启用条件的具体 trigger 矩阵 | v0.2 第 5 周草稿 ADR-005 时 |
| H2 | meta 两维 hard 跑通后的首批数据(看真实数据是否需要调整 Score 维度) | v0.2 meta_check.sh 跑过 1~2 轮后 |
| H3 | Q5 fixture-set 验证在 C 类下的边界(multi-agent ground truth 怎么造) | v0.2 接 deep-research 第一次实跑时 |
| H4 | profile 级 vs 容器级隔离的临界点 | deep-research 上车评估时 |
| H5 | 已知问题消失率作为 soft 维度的可自动化程度 | v0.2 第一次实跑时 |
