# Architecture Review · 2026-08-13 (Opus 4.8)

> 状态：v0.5 收尾后整体架构再判断——非 cleanup、只读评审。
> 用途：审阅结论可追溯，非 ADR，不构成新决策。
> 评审纪律：与 2026-08-11 两份 Opus 评审对齐——不挑零碎、不打分、只看文档状态；诚实说"基本成立 + N 条保留"。

---

## 任务来源

2026-08-13 v0.5 收尾（commit `5cb18fc`：v0.3 spec 漂移声明清理 + OOS 占位机制段；commit `ab727ff`：ADR-006 就绪轴 + OOS 占位机制首例（占位桩））后，重开一个 Opus 4.8 会话做"v0.5 落地后整体架构再判断"。

- 不看 commit 历史（除 5cb18fc / ab727ff 这两笔 v0.5 落定）
- 不挑零碎、不打分
- 只看当前文档状态
- 不重复 v0.4 cleanup notes 已存档的已知警告（A 类真实 Target 未上车 / 守护代码叠加边际信噪比下降 / Loop Engineering trigger 矩阵未在真实并行场景验证）

## 输入（审阅文件）

按用户给定顺序全部读完：

- docs/CONTEXT.md
- docs/adr/ADR-001~006（6 份，含 ADR-003.5）
- docs/specs/v0.1-skeleton-spec.md、v0.2-skeleton-spec.md、v0.3-skeleton-spec.md
- docs/handoff/v0.1-closure-note.md、v0.2-5week-plan.md、v0.3-final-summary.md、v0.3-real-e2e-evidence.md、v0.3-T2a-notes.md、v0.3-T2b-notes.md、v0.3-T3-notes.md、v0.4-cleanup-notes.md（8 份）
- docs/reviews/2026-08-11-opus-architecture-review.md、2026-08-11-opus-fresh-audit.md（2 份旧评审）

交叉验证（评审期需要的支持性事实点）：

- `tests/fixtures/d9_placeholder.py` 存在（commit `ab727ff` 标的占位桩首例）
- main HEAD = `5cb18fc`（v0.5 最新文档 commit）
- `git log main` 包含 `b1de151`（T1 / PR #12）、`9107fdc`（T2a / PR #13）、`60ab6e9`（T2b / PR #14）、`b5bae75`（T3 / PR #15）、`6239f00`（T1 债 / PR #16）、`2f52bd8`（T2 README / PR #17）—— 6 张 PR 全部 merge to main
- `14eefb2` 在 `git log --all` 存在但 **不在 main 上**（PR #10 的 source branch HEAD）

---

## 整体判断

**整体方向：基本成立。**

v0.5 落定的两件新东西（ADR-006 就绪轴 + OOS 占位机制）站得住，4+3 骨架 + 6 个 ADR 整体一致性良好。2026-08-11 两份 Opus 评审的 4 条保留吸收情况明确：3 条已闭合、1 条机制落地但触发未到（按设计）。

具体三块：

1. **v0.5 新东西（ADR-006 + OOS 占位机制）**：均站得住。ADR-006 用 2 态就绪轴（specd / in production）锁 v0.5 时点 7 件状态，决策 1「字段层是死态」+ 决策 3 跃迁纪律「3 件齐备」形成可机械检查的判定；OOS 占位机制（v0.3 spec line 88-99）以「触发事件 / 占位桩函数 / 关闭 owner」三件套约束延期项，示范桩 `tests/fixtures/d9_placeholder.py` 已落（commit `ab727ff` 显式标的占位机制首例）。
2. **4 条旧保留吸收情况**：v0.2/v0.3 落地物与旧保留逐条对齐——3 条已吸收（fresh 保留 1 / 旧保留 2 / fresh 保留 2 的两维 hard 部分）、1 条机制落地但触发未到（旧保留 1 + fresh 保留 2 的 Glossary 维度同根）。详细映射见下表。
3. **4+3 骨架 + 6 个 ADR 内部一致性**：v0.4 cleanup 后 §适用边界 v0.2 段已与 ADR-005 决策 1 + v0.2 spec D5/D8 对齐，spec 链 v0.1 → v0.2 → v0.3 各自职责清晰；v0.3 spec line 8 的 v0.2 漂移声明已闭合（commit `5cb18fc`）；handoff 链路（closure / 5week / final summary / T2a / T2b / T3 / v0.4 cleanup）承接关系清楚。

---

## 4 条旧保留 v0.5 状态映射

| 旧保留 | 来源 | 落地物 | v0.5 状态 |
|---|---|---|---|
| meta 层契约「文档级承诺」边界偏软 | 旧 Opus 保留 1 | ADR-004 Open Issue（Glossary 静态化）+ v0.3 spec D3.2 量化触发条件（n ≥ 10 + ≥ 5 ADR + ≥ 3 模板） | **机制落地，触发未到**——T3 n=2 不构成首批数据（v0.3 spec line 50 / v0.3-T3-notes 显式） |
| 4+3 在 A 类成立但 C 类实例化产物无沉淀 | 旧 Opus 保留 2 | ADR-005 决策 1 trigger 矩阵 + v0.2 spec D5 接口规格四元组（输入 / 输出 / 状态 / 依赖）+ v0.3 spec D1.5 字段层 + T1/T2a/T2b 真 e2e | **基本吸收**——Sub-agents 派发已 in production（PR #14 merge）；Worktrees/Plugins 仍 specd（v0.3 first cut recipe 设计使 trigger 未命中，spec D1 显式说明） |
| A 类代码 vs 文本裂缝 | fresh Opus 保留 1 | v0.2 spec D1 D9 rule（fixture-set 验证 ≥ 20 条 + ≥ 80% 命中）+ 文本 hard signal 协议（commit `6d5981c`）+ `meta_check.sh` + T4 文本 e2e 跑通（commit `9a04a17`，v0.2 spec T4 P1→P0 升级） | **吸收**——D9 形式化 + T4 跑通 3 轮 |
| meta 文档级承诺被推到无验证能力位置 | fresh Opus 保留 2 | `scripts/meta_check.sh` 跑两维 hard（commit `a6d7742`）+ T3 n=2 数据（v0.3-T3-notes line 27-48 JSON 输出）+ D3.2 量化触发 | **部分吸收**——两维 hard 跑通；Glossary 维度触发未到（与旧 Opus 保留 1 同根，是设计内的延迟，不是新增债） |

> 4 条里 3 条已闭合、1 条按设计推迟——整体吸收情况符合 v0.1 收尾时的 Opus 4.8 收尾判预期。剩下未吸收的那条是「等真实数据触发」的延期项，不是「需要修」的问题。

---

## 保留（按重要性排序）

### 真问题 · 1 条

#### 真问题 1 · ADR-006 决策 2 注 commit hash 引用错

**位置**：`docs/adr/ADR-006-readiness-axis.md` line 47 决策 2 表第 7 行 Sub-agents 派发 in production 证据：

> v0.3 T1 派发骨架件 + D1.5 字段层（PR #12，commit `b1de151`）+ T2a 3-agent stub e2e（PR #13）+ T2b 真 e2e 50% 阈值断言 PASS（PR #14，commit `14eefb2`，2026-08-13 merge）

**事实**：

- `14eefb2` 是 PR #10（T2b）源分支的 HEAD commit，不在 main 上（`git log --all` 可见但 `git log main` 无）
- PR #14 merge to main 的 commit 是 `60ab6e9`（message `feat(v0.3): 真 hermes 派发 + T2b 真实 e2e + 50% 阈值断言（#10） (#14)`，parent = `9107fdc`）
- 当前 main HEAD = `5cb18fc`，`60ab6e9` 在 main 链上

**为什么是真问题**：

- ADR-006 是 v0.5 新立的就绪轴「当前时点状态」快照（决策 2「本表锁的是 v0.5 时点的瞬时状态」），读者拿 commit hash 回去查 git log 找不到会怀疑 in production 判定的真实性
- 同表第 1 行（Target in production）写「PR #14 evidence，详见 `docs/handoff/v0.3-real-e2e-evidence.md`」也没指 commit hash，但决策 2 字段层是带 commit hash 的——一旦带就要准
- 与 v0.3 final summary line 17 写「T2b ... commit `14eefb2`」的源分支 HEAD 用法对齐（summary 写时不带 merge commit 标识），但 ADR-006 同一处既带 commit hash 又写「2026-08-13 merge」，把源分支 commit 描述为 merge commit 是事实错

**修法建议（用户决定）**：

- 改 commit hash `14eefb2` → `60ab6e9`（保留 "2026-08-13 merge" 措辞 + 源分支 commit `14eefb2` 标注为 source）
- 或去掉 commit hash + 只标 PR #14 + handoff 文档路径
- 不影响 in production 判定本身（T2b 真 e2e 50% 阈值 PASS 事实不变）

**不是真问题的对照**：

- v0.3 final summary line 17 写 `14eefb2` 不带 merge 措辞——只标 T2b commit（源分支 HEAD 习惯），可读
- v0.4 cleanup notes line 80 写「PR #16（T1 债）:开 PR **不 merge**,等用户 ack」—— cleanup notes 写时是 merge 前的快照，merge 后 stale，但 cleanup notes 性质是「写时事实」，不是「当前快照」，不算错

---

### 次要债 · 4 条

#### 次要债 1 · v0.3 spec OOS 占位机制约束与已列 5 条延期项不齐

**位置**：`docs/specs/v0.3-skeleton-spec.md` line 88-99

**事实**：

- line 89-91「约束」段写「延期项必须配：触发事件（具名非类别词）/ 占位桩函数 / 关闭 owner; 不允许裸延期」
- line 92-99 列 5 条延期项（C 类 D9/Q5 fixture 形式化 / `scoring.yaml.template` / `iter.sh` signal array token 化 / O5 exempt 升级 / 加其他杂项），**每条都只有「触发 = ...」一句**，无占位桩函数、无关闭 owner

**为什么是次要债**：

- 是设计内的——OOS 占位机制是 v0.5 首用的纪律（v0.3 spec line 88 明确），对**未来**延期项必配
- 5 条已列延期项在 v0.3 first cut 收尾时（2026-08-13 之前）立的，没占位桩是历史产物
- v0.4 cleanup notes §3 把"下个 cleanup ticket 可顺手处理"的同源债（t2b_*.py ghost reference）已明示「已知留口」模式——本债与该模式同源
- 但 spec 没明示"旧项回填还是新项必配"——读者拿约束段对照 OOS 段会困惑

**修法建议（用户决定）**：

- v0.4+ 落 OOS 占位机制"新项必配"明示
- 5 条已列 OOS 项回填占位桩 + owner 由后续 ticket 按需补
- 不影响当前 v0.5 落地

#### 次要债 2 · v0.3 final summary §3 「⏳ 等 ack + 本地 main HEAD 不含 14eefb2」是 stale 快照

**位置**：`docs/handoff/v0.3-final-summary.md` line 14-17 + line 38-41 + line 49-54

**事实**：

- v0.3 final summary commit `cbe1d6b` 是在 T2b merge commit `60ab6e9`（= PR #14 merge to main）之后才落的（git log 时序：`60ab6e9` → `cbe1d6b`）
- 但 summary 文档内仍写「⏳ 等 ack」+「本地 main HEAD 不含 14eefb2」+「PR #14 ... 默认 merge, 加 wall clock evidence 到 main」+「PR #15 ... 默认 merge」
- 当前 main HEAD `5cb18fc` 链上 6 张 PR 全部 merge（PR #12-17 全在）
- §4「次日 ack 清单」整段已是 stale

**为什么是次要债**：

- v0.3 final summary 的文档性质是「v0.3 first cut 4 张票派完总览（2026-08-13,v0.3 spec v1 commit 81ada68 之后）」+「本会话维护，后续每次会话开场查」+「维护:不动 v0.3 spec / ADR / issue,仅 docs/handoff/」
- §4「次日 ack 清单」是用户决策清单，不是文档事实快照——但 git log 演进后，整段内容已无新信息
- 与 v0.4 cleanup notes line 79-80「PR #16 ... 不 merge,等用户 ack」+「PR #17 ... 不 merge,等用户 ack」同源 stale

**修法建议（用户决定）**：

- 下次 cleanup ticket 可顺手把 §4 改成「已合并记录」（标 merge commit hash）或注「写时快照，已 merge 状态以 git log main 为准」
- 与次要债 4（t2b_*.py ghost reference）同源

#### 次要债 3 · CONTEXT.md §后续 TODO 第 6 条措辞「v0.2 决策」与现实不一致

**位置**：`docs/CONTEXT.md` line 103

**事实**：

- §后续 TODO 第 6 条写「meta Score Glossary 静态化方案（**v0.2 决策**，详见 ADR-004 Open Issue）」
- v0.2 spec D4 末尾 + v0.3 spec D3.2 已把 Glossary 静态化触发条件量化为「n ≥ 10 + ≥ 5 ADR + ≥ 3 模板」+ D3.3 推迟到 v0.4 准备
- 当前 n=2，明确不构成首批数据
- §后续 TODO 第 1-5 条全标 ✅（v0.4 cleanup notes §34 明示「§后续 TODO 段未动 — 与漂移无关」+「ADR-005 第 5 条（启用条件）仍标 ✅」）

**为什么是次要债**：

- v0.4 cleanup notes §34 已明示「§后续 TODO 段未动」是 v0.4 cleanup 决策——不修
- §后续 TODO 是「索引位」性质（v0.4 cleanup notes §34 措辞），不是决策草案
- 但「v0.2 决策」措辞在 v0.2 + v0.3 收尾后明显 stale（v0.2 没做，v0.3 推迟到 v0.4）

**修法建议（用户决定）**：

- 把「v0.2 决策」改成「v0.3 spec D3.2 量化触发（n ≥ 10），D3.3 推迟到 v0.4 准备」
- 或加注「索引位，历史措辞保留；详见 v0.3 spec D3.2」
- 与 v0.4 cleanup notes §34 决策一致（「TODO 段不修」），但措辞可同步——属同源

#### 次要债 4 · t2b_*.py ghost reference 已知留口

**位置**：`tests/test_t2b_real_e2e.py:7-8` + `:108` 注释 + `docs/handoff/v0.3-T2b-notes.md:11-13` 引入清单

**事实**：

- v0.4 cleanup notes §3 明示「Ghost reference（已知留口,本 ticket 不修）」+ 列出 2 处
- §5 写「下个 cleanup ticket 可顺手处理:test docstring 改成'那是 wall clock evidence 文档的责任',T2b-notes 加一句'脚本 v0.4 cleanup 已删,git 历史 commit `14eefb2` 可查'」
- 当前两处 ghost reference 仍存在

**为什么是次要债**：

- 已明示「已知留口」+ 给出修法——不算隐藏债
- v0.4 cleanup notes §5 写「下个 cleanup ticket」——用户决定的执行节奏
- 与 v0.4 cleanup 范围决策一致（cleanup 只动 T1 债，不动 T2b-notes 历史记述）

**修法建议（用户决定）**：

- v0.5+ cleanup ticket 顺手处理，与次要债 2 合并做一次 stale 文档 sweep
- 不影响当前架构

---

## 给后续提示

按重要性排序：

1. **真问题 1 优先处理**：ADR-006 是 v0.5 新立的「就绪轴」快照文档，commit hash 引用错会被 reader 怀疑 in production 判定的真实性。修法小（改 commit hash 或去掉 commit hash + 标 PR），建议下次动 ADR-006 时一并修。
2. **次要债 1（OOS 占位机制 vs 已列 5 条 OOS 项）**：v0.5 落定后 OOS 占位机制是新增纪律，「新项必配」与「旧项不强制」边界需明示。下次动 v0.3 spec 时加注一句即可。
3. **次要债 2 + 4（stale 文档 sweep）**：v0.3 final summary §4「次日 ack 清单」+ v0.4 cleanup notes §5「PR #16/#17 等 ack」+ t2b_*.py ghost reference 三处同源，建议合并成一次 cleanup ticket（不属 v0.5 范围，属 v0.5+ cleanup）。
4. **次要债 3（CONTEXT §后续 TODO 措辞）**：与次要债 1 同源（措辞同步），优先级最低——动 v0.5 收尾相关文档时顺手改。
5. **评审纪律提醒**：本评审不复用 4 条旧保留原文措辞——保留的「形式」（4 条）与 v0.5 落地的「实质」（3 条已吸收 + 1 条按设计推迟）已分离。下次评审可继续沿用此分离。
6. **架构方向（v0.5 落定后展望）**：v0.5 落定后整体方向 = ON TRACK（与 v0.4 cleanup 评审判定一致）。下个 milestone 是 v0.4 first cut 启动工程节奏（按 v0.3 final summary §6 + v0.3 spec OOS 6 条延期项的触发条件），不是 v0.5+ 新增。架构层无需新 ADR；meta n=2 → n ≥ 10 的数据累积是 v0.4 工程节奏自然产物。

---

## 与 2026-08-11 两份评审的关系

- 旧 Opus 评审（ab96750e 视角）：C 类实例化产物无沉淀 + meta 软边界 → v0.5 落定后，**保留 2 已基本吸收 / 保留 1 机制落地触发未到**。
- fresh Opus 评审（独立 session 视角）：A 类代码 vs 文本裂缝 + meta 不可执行 → v0.5 落定后，**保留 1 已吸收 / 保留 2 部分吸收（与旧 Opus 保留 1 同根）**。
- 两份评审共同指向的「v0.2 启动二阶决策点」（A 类裂缝 / meta 不可执行 / C 类实例化）→ 全部在 v0.2 + v0.3 落地过程中闭合或按设计推迟。

v0.5 评审判定：**2026-08-11 两份评审的 4 条保留已形成可追溯的吸收链，v0.5 收尾不留新债。**

---

## 修订记录

- 2026-08-13 v1：v0.5 收尾后首版评审（commit `5cb18fc` / `ab727ff` 之后），不动 v0.5 已落文档
