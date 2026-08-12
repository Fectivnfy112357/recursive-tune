# Architecture Review · 2026-08-11 (Opus 4.8)

> 状态：审阅留痕——作为 v0.1 架构方向判断的存档，供 v0.2 / v0.3 决策时回看。
> 用途：审阅结论可追溯，非 ADR，不构成新决策。

## 任务来源

2026-08-11 下午 arch-pivot 5 commit + 5 patch commit 落锤后，重开一个 Opus 4.8 会话做"架构方向再判断"——不看 commit 历史、不挑零碎问题、只看当前文档状态。

## 输入（审阅文件）

- docs/CONTEXT.md
- docs/adr/ADR-001-loop-engineering-as-skeleton.md
- docs/adr/ADR-002-ratchet-over-mutation.md
- docs/adr/ADR-003-first-target-deep-research.md
- docs/adr/ADR-003.5-A-class-target-domain.md
- docs/adr/ADR-004-meta-layer-target.md
- docs/specs/v0.1-skeleton-spec.md
- AGENTS.md
- docs/agents/domain.md
- docs/use-cases/deep-research.md

## OpUs 4.8 给的整体判断

**整体方向：基本成立。**

- v0.1 = A 类锚点、4+3 骨架、meta 层 v0.1 文档级承诺——三条骨干站得住
- 三者各自能独立回答 "v0.1 验证什么、骨架装什么、meta 怎么过承诺关"，且互相之间没有隐形冲突
- A 类目标域与 4+3 天然咬合（A 类只实例化核心 4 件，扩展 3 件不为 A 类空转）
- meta 层契约虽 v0.1 不执行骨架，但 "target / score / 共享 ratchet" 三件套已经讲了清楚的接口而不是口号
- 三版本定位（v0.1 A 锚 / v0.2 A+C+meta 落地 / v0.3 C 深耕）收敛——每个版本的扩展点都对应前一版尚未验证的边界

## 两条保留（架构层面疑虑）

### 保留 1 · meta 层契约的 "文档级承诺" 边界偏软

**疑虑**：ADR-004 给了 Target 候选、Score 候选 3 维、共享 ratchet 机制，但 Glossary 术语一致率那一维明示 "v0.2 决定静态化方案"——这是 meta Score 三维里唯一非 hard 的维度，且承认 "退化为不可执行" 的风险。

**如果不动它的后果**：v0.1 看起来自洽；v0.2 接手时这一维要么被迫降级、要么被迫现场发明静态化机制，间接把 v0.2 的设计负载推高。这是 "哪一维是真硬、哪一维是软目标" 的二阶问题。

**倾向**：本轮**不动**。明确留到 v0.2 决策。Opus 4.8 在上一轮审阅已拒掉 "提前抽象成 Meta Validator" 倾向，与本保留的处理一致。

### 保留 2 · 4+3 在 A 类下成立，但 C 类下 "实例化产物长什么样" 无沉淀

**疑虑**：deep-research（v0.2 C 类）是已知扩展触发器，但现有产物（plan / result / validation / 三份 known-issues / benchmark）目前只是 use-case 文件里的历史索引，没有作为 v0.2 启用扩展 3 件时的 "已知形状" 沉淀。

**如果不动它的后果**：v0.2 上车时 4+3 接口虽然不变，但 C 类下 "实例化产物长什么样"（worktrees 怎么切 / plugins 怎么挂 / sub-agents 怎么派发）在 v0.1 范围内没锚点，全部要 v0.2 重新发明。

**倾向**：**在 docs/use-cases/deep-research.md 加 "v0.2 启动决策的已知材料索引" 段**。Opus 给的关键理由——**写成 ADR 会把 "待定问题" 提前固化成 "决策草案"，违反 ADR 只记已决事项的纪律**。use-case 文件夹本就是 v0.2+ 探索域，沉淀物归位正确。

## Hermes 倾向 C 评估结果（Opus 对账）

| 项 | 结果 |
|---|---|
| 倾向 C 整体合理性 | **合理**——下手位置和抽象等级匹配 |
| 保留 1 | 确认不动 |
| 保留 2 形态选择 | **倾向 C**（use-case 沉淀，非 ADR 化） |
| 颗粒度 | "列 v0.2 需回答的问题 + 可参考材料" 已压在 "不构成新决策但不丢上下文" 的分界上 |

## 给后续 v0.2 接手的提示

- 启动 v0.2 时**先读本文件 + docs/use-cases/deep-research.md "v0.2 启动决策的已知材料索引" 段**——那是 Hermes v0.1 收尾时保留给 v0.2 的上下文
- 保留 1（meta Glossary 一致率静态化）是 v0.2 启动时**第一个**二阶决策点
- 保留 2（4+3 C 类实例化产物）是 v0.2 启动时**第二个**二阶决策点
