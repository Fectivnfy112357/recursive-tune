# Architecture Review · 2026-08-11 (Fresh Opus 4.8)

> 状态：独立 Opus 4.8 session 审阅留痕——无旧 session 记忆、与 2026-08-11-ab96750e 那次审阅**完全独立**。
> 用途：v0.1 架构方向判断的存档（互补视角），供 v0.2 / v0.3 决策时回看。
> 性质：审阅结论可追溯，非 ADR，不构成新决策。

## 任务来源

2026-08-11 傍晚：ab96750e 那次会话已收尾（"基本成立 + 进 implementation"），新开会话拿到当前文档做"独立判断"——不查 commit、不带旧 session 记忆、不挑零碎、不打分。

## 输入（与 ab96750e 相同）

- docs/CONTEXT.md
- docs/adr/ADR-001-loop-engineering-as-skeleton.md
- docs/adr/ADR-002-ratchet-over-mutation.md
- docs/adr/ADR-003-first-target-deep-research.md
- docs/adr/ADR-003.5-A-class-target-domain.md
- docs/adr/ADR-004-meta-layer-target.md
- docs/specs/v0.1-skeleton-spec.md
- AGENTS.md
- docs/agents/domain.md

## Fresh Opus 4.8 给的整体判断

**整体方向：基本成立。**

明确肯定三件事：
1. **4+3 划分 + 接口/实现层分离**——把"骨架全集"与"本版实例化集"切开；接口不变、实现可换——"通用框架"宣称有了可检验防线。Out of Scope #2「不为扩展件预留任何 stub」成为有牙齿的纪律
2. **A 类锚点决策层面成立**——ADR-003 管"是否/何时上 deep-research"、ADR-003.5 管"v0.1 用什么"，两份文件拆开避免单锚点文档常见"推迟"与"替代"混谈
3. **v0.1/v0.2/v0.3 定位清楚**——A → A+C+meta → C 三段演进与 4+3 启用条件咬合，不是三段并列口号

## 两条全新保留（与 ab96750e 的旧判断**不重叠**）

### 保留 1 · A 类目标域内部还有一道没被区分的裂缝

**疑虑**：A 类被定义为"单文件 / 硬指标主导"，但它同时容纳两种性质不同的 Target：
- **代码型** Target——hard signal = `pytest` exit code，信号自带、零成本、可重复
- **文本型 config / SKILL.md / prompt** Target——hard signal 必须靠外部 eval 集构造（grep 命中数、recall 噪音率都要先有数据集才存在）

CONTEXT.md 宣称的 A 类真实战场是后者，但 D6 / T4 的验证物（内置会失败又能修好的 Python repo）是前者。

**如果不动它的后果**：v0.1 跑通证明的是"骨架能承载 autoresearch 原本就成立的场景"，**不是"骨架能承载 A 类"**。v0.2 试图接第一个真实 SKILL.md 类 Target 时，会发现 eval 集构造是一整块缺失的骨架件——那时归因会指向 C 类扩展，而**真实断裂点在 A 类内部**。

### 保留 2 · meta 层文档级承诺被推到一个当下还没有验证能力的位置

**疑虑**：ADR-004 把 Target / Score / 共享 ratchet 都写清楚了（"两层递归沦为口号"被挡一半）。但契约本身在 v0.1 既不执行、也不被检验——三件事叠起来：
- (1) D8 rule 12 明确豁免 docs 不必满足 meta Score
- (2) 三维 Score 里 Glossary 一致率自己承认不是 hard signal（Open Issue 留给 v0.2）
- (3) glossary Meta Score Validity 又规定 meta Score 必须由第一层独立验证——而第一层在 v0.1 只跑假 demo

**结论**：meta 不是"推迟实现"，是 **"推迟到一个还不具备验证条件的版本"**。若不动它，v0.2 很可能得出"meta Score 尚不可执行、再推一版"的结论——而每推一版的理由都会同样充分。

## D8 rule 12 对账（Fresh Opus 自己反思的）

用户给 fresh Opus 提了一个追问：D8 rule 12 是合理的"进度守护栏"，还是"再次确认 meta 不可执行现状"的证据？

**Fresh Opus 的回答（精炼）**：
> 两者都是，但不冲突。
>
> - 作为局部决策，rule 12 是合理的守护栏——它挡的是真实风险（implem agent 为凑文档分拖慢骨架）。
> - 作为全局证据，它同时说明 meta Score 在 v0.1 连"顺手跑一次"的成本都被判为不可承受——这恰恰是我说"推到无验证条件位置"的**表现**，而不是**原因**。
>
> 原因在更上游：Glossary 维度自认不是 hard signal、Meta Score Validity 又要求第一层验证、第一层只有假 demo。**就算删掉 rule 12，meta 也不会因此可执行**。
>
> 所以：**不建议改 rule 12**——它挡的风险是真的，改它治不了病根。真要动，动的是 ADR-004 里"三维是否有一维能在 v0.1 自证"这件事（属 v0.2 scope）。
>
> 握法上，rule 12 进 implem 时**按字面握即可**——它是豁免，不是禁止。

## 给后续 v0.2 接手的提示

启动 v0.2 时**先读**：

- 本文件（fresh Opus 视角）——A 类内部裂缝 + meta 不可执行的**症状**
- `2026-08-11-opus-architecture-review.md`（ab96750e 视角）——C 类实例化产物无沉淀 + meta 软边界偏软的**病根**

**两个保留指向同一方向**：

| 文件 | 视角 | 焦点 |
|---|---|---|
| ab96750e audit | 旧 Opus 4.8（收尾判） | v0.1 vs C 类**纵向**脱节、meta 软边界**病根** |
| fresh Opus audit | 新 Opus 4.8（独立判断） | v0.1 验证物 vs A 类**横向**脱节、meta 不可执行**症状** |

**v0.2 启动时的二阶决策点**（按重要性）：

1. **A 类代码 vs 文本裂缝**——v0.2 接 SKILL.md 类 Target 时，是否要为文本型 Target 单独准备 hard signal 工具（eval 集构造器、grep 召回基准等）？
2. **meta 不可执行**——ADR-004 meta Score 三维是否有一维能在 v0.1 自证？还是三件事都顺延到 v0.2 框架可执行骨架时一并解决？
3. **C 类实例化产物**——v0.2 启用扩展 3 件（Worktrees / Plugins / Sub-agents 派发）时，4+3 接口不变，但实现层能否直接复用 v0.1 的工作，还是要在 v0.1 末做一轮 use-case 沉淀（已落 `docs/use-cases/deep-research.md`）？

D8 rule 12 在 v0.1 implem 时按"豁免、非禁止"握；不要为凑 meta Score 拖慢 A 类骨架交付。
