# ADR-006 · 4+3 归位表就绪轴（2 态：specd / in production）

**状态**：确认（2026-08-13，v0.5 草稿；v0.3 真实 e2e 跑通后落笔）
**关联**：ADR-001（核心 4 件 + 扩展 3 件归位）、ADR-002（git ratchet）、ADR-003.5（A 类目标域）、ADR-004（meta 层契约）、ADR-005（扩展 3 件 trigger 矩阵）、CONTEXT.md §适用边界
**修订记录**：2026-08-13 v0.5 草稿；v0.3 真 e2e 跑通后，下游 reader 难分"已规格化"与"已在生产"，本 ADR 锁 2 态就绪轴

---

## 背景

ADR-001 的 4+3 归位表（核心 4 件 + 扩展 3 件）定义**接口全集**，但**没有"就绪"维度**。reader 拿到的 7 件里有 3 个状态混在一起：

| 件 | 现有状态混层 |
|---|---|
| Target | ADR-001 接口 / v0.1 spec D4 实现 / scripts/ 真生产 |
| Sub-agents 派发 | v0.2 D5 接口规格（v0.2 OOS 标"未实现"） / v0.3 T1 派发骨架件 + D1.5 字段层 / T2b 真 e2e evidence |
| Worktrees | ADR-005 trigger 矩阵 / v0.2 D5 接口规格 / v0.3 spec D1"本轮触发未命中" |

**问题是**：reader 拿不到 1 个简洁字段告诉他们"这 7 件，我现在能用哪些"。当前 reader 必须交叉查 ADR-001 + 各版本 spec + `scripts/` + `tests/` + `docs/handoff/` 5 处。

## 决策

### 决策 1 · 2 态就绪轴

| 态 | 含义 | 证据要求 |
|---|---|---|
| **specd** | 已写入 spec / ADR，但无对应实现代码，或实现代码未跑通 | spec 段落 / ADR 决策段；无 `scripts/` 落点或无真 e2e 落 `docs/handoff/` |
| **in production** | 有对应实现代码，且至少被 1 个 use case 真跑通（非 stub / 非 fake hermes） | `scripts/` 路径 + `tests/` 引用 + 真实 e2e evidence 文档落 `docs/handoff/` |

**字段层是死态**——"spec 已写字段层 + 代码层已写但未跑"不构成第 3 态；项目历史无件停留。任何 spec 字段层一旦落实为代码，要么跑通升 in production，要么回滚删代码回到 specd，不存在中间态。

理由：
1. **2 态够用**——reader 真正关心的是"我现在能用吗"；"spec'd + 字段层已写 + 未跑"对用户而言与"spec'd"无差
2. **避免状态膨胀**——3 态在边界 case 上反复横跳（跑 1 次失败算什么？revert 后回到哪个态？）；2 态下证据极简
3. **ratchet 自然背书**——按 ADR-002 的 git ratchet 思想，代码能跑通必然 commit 进 main；没 commit 就不算"生产"

### 决策 2 · 4+3 归位表（就绪轴列，v0.5 时点）

| # | 件 | 性质 | 就绪轴（v0.5） | 证据 |
|---|---|---|---|---|
| 1 | **Target** | 核心 4 件 | **in production** | v0.1 A 类 demo target + v0.3 C 类 README 多语种化 recipe 真 e2e（PR #14 evidence，详见 `docs/handoff/v0.3-real-e2e-evidence.md`） |
| 2 | **隔离约定（profile 级）** | 核心 4 件 | **in production** | `scripts/setup_profiles.sh` 创建 writer/judge 独立 hermes profile + T2a 3-agent stub e2e 跑通（PR #13）+ T2b 真 e2e 跑通（PR #14，2026-08-13 merge） |
| 3 | **Ratchet + State** | 核心 4 件 | **in production** | ADR-002 落 git ratchet + `state/results.tsv` 真实迭代历史 + `iter.sh` 落 commit 实证 |
| 4 | **Program 模板** | 核心 4 件 | **in production** | `templates/program.md.template` + `templates/judge-prompt.md.template` + v0.1 起的 A 类 program.md 实战 |
| 5 | **Worktrees** | 扩展 3 件 | **specd** | ADR-005 决策 1 trigger 矩阵 + v0.2 D5 接口规格；v0.3 spec D1 显式"本轮 recipe 设计使触发未命中"；无 `scripts/` 实现 |
| 6 | **Plugins** | 扩展 3 件 | **specd** | ADR-005 决策 1 trigger 矩阵 + v0.2 D5 接口规格；无 `scripts/` 实现 |
| 7 | **Sub-agents 派发** | 扩展 3 件 | **in production** | v0.3 T1 派发骨架件 + D1.5 字段层（PR #12，commit `b1de151`）+ T2a 3-agent stub e2e（PR #13）+ T2b 真 e2e 50% 阈值断言 PASS（PR #14，commit `14eefb2`，2026-08-13 merge） |

> **关于 Sub-agents 派发 in production 的判定**：T1 + T2a 已确立"派发骨架件 + 字段层 + 机械结构 e2e"齐备；T2b 真 e2e 是同一件 in production 的"强化证据"（决策 1 要求的"非 stub"判据），不构成状态跃迁必要条件。T2b merge 后状态不变（in production），但 e2e evidence 升完整。

### 决策 3 · 状态跃迁纪律

- **specd → in production**：3 件齐备——(a) `scripts/` 实现已 commit 进 main（git ratchet 实证，非 working tree 草稿）；(b) `tests/` 单元/集成测试 PASS；(c) ≥1 个 use case 真跑通（非 stub、非 fake hermes）且 e2e evidence 落 `docs/handoff/`
- **in production → specd**：不允许（只升不降，与 ADR-002 思想一致；代码回滚 = 回到 specd，但 git 历史保留 in production 的事实）；reader 看 git blame 即可知历史
- **就地读 / 跨时点读**：本表锁的是 v0.5 时点的瞬时状态；后续 spec 起草时若发现某件 in production 但 v0.x 已把它删了，应在该 spec 注明"原 in production，v0.x 后回退 specd"——不回写本表

### 决策 4 · v0.5 起术语统一

之前各 spec / handoff 中"启用 / 未启用 / 接口规格 / 字段层待补"等多种说法，**v0.5 起统一替换为 2 态**：specd / in production。具体替换表：

| 旧说法 | 新说法 |
|---|---|
| "v0.2 仅定义扩展 3 件接口，未启用" | "Worktrees / Plugins / Sub-agents 派发：v0.2 specd" |
| "T1 派发骨架件 + D1.5 字段层已落" | "Sub-agents 派发：T1+T2a 落 in production" |
| "本轮 recipe 设计使触发未命中" | "Worktrees v0.5 仍 specd，触发未命中见 ADR-005 决策 1" |

## 明确划出（就绪轴不答的）

| 项 | 划出理由 |
|---|---|
| **健康度评估**（代码覆盖率 / 测试强度 / 维护活跃度） | 就绪轴只问"能不能用"，不问"好不好用"；健康度另起 ADR（若需要） |
| **"字段层已写"独立态** | 决策 1 明确"字段层是死态"，无独立态；若有 reader 误读，见决策 1 理由 2 |
| **多版本就绪轴（每个 version 一行）** | 单 ADR 单时点；版本维度已在 spec 链（v0.1/v0.2/v0.3 spec）中，不重复 |
| **v0.5 时点之外的状态变化史** | 本表快照；状态变化史由 git log + 各 version handoff（`docs/handoff/v0.x-*.md`）承担，本 ADR 不维护变更日志 |

## 后果

- **新 spec 起草时**必须先看本 ADR 决策 2 表，新引入的件**默认 specd**；只有证据齐备（决策 3 三件齐）才升 in production
- **`docs/CONTEXT.md` §适用边界 段后续改写**时，按决策 4 表替换"启用 / 未启用"等旧说法
- **本表时点**：2026-08-13 v0.5；后续版本若改某件状态，在新 spec 注明即可，不回写本 ADR 决策 2
- **`scripts/meta_check.sh` 不扫本表**——本表是叙事性总结，非机器可扫的结构化产物；meta 维护者手工维护
- **本 ADR 与 ADR-001 职责分开**：ADR-001 答"全集 vs 实例化机制"（结构），本 ADR 答"当前时点状态"（快照）；版本一变就绪轴就要更新，混进 ADR-001 会污染其通用接口定义

## 备选方案（被否决）

| 备选 | 否决理由 |
|---|---|
| **3 态（specd / spec'd-with-fields / in production）** | 字段层是过渡态，无件停留；3 态在 ratchet 视角下冗余（决策 1 理由 2） |
| **4 态（+ planned 计划态）** | ADR-005 已用 trigger 矩阵表达"何时该上"，planned 态与 trigger 矩阵职责重叠 |
| **5 态（+ deprecated 废弃态）** | v0.5 时点无件废弃；过早引入会让 reader 计数分心；废弃态留 v0.6+ 真正出现废弃件时再加 |
| **不写就绪轴，reader 自己看 `scripts/` 目录** | reader 要交叉查 ADR + spec + scripts + tests + handoff 5 个目录，体验差；就绪轴 1 字段汇总 |
| **就绪轴写进 ADR-001** | ADR-001 是"全集 vs 实例化机制"，就绪轴是"当前时点状态"；两者职责分开避免 ADR-001 频繁回写（版本一变就绪轴就要更新） |
| **就绪轴写进 ADR-005** | ADR-005 是"扩展 3 件 trigger 矩阵"（只管 Worktrees/Plugins/Sub-agents 3 件）；核心 4 件的状态不在 ADR-005 范围；本 ADR 必须覆盖 4+3 全 7 件 |
