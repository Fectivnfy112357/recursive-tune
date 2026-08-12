# v0.2 · Text-Target Hard Signal 评估协议

> 性质:v0.2 探索性设计文档(use-case 沉淀,非 ADR)
> 日期:2026-08-12
> 起草动机:v0.1 demo 跑的是 autoresearch 原生代码型 hard signal(`pytest -q`,社区共识),证明的是"骨架能承载 autoresearch 原生场景",**不是**"骨架能承载 A 类真实战场(SKILL.md / prompt)"——fresh audit §保留 1 的判定。本协议为 v0.2 接第一个文本型 Target 提供 hard signal 准入判据。
> 关系:本协议不是 spec 修改;`docs/specs/v0.2-skeleton-spec.md`(待写)将通过 D9 rule 引用本协议。Q5 是 hard/soft 的通用分界线,不仅限于文本型 Target。

---

## 协议要回答的问题（7 条）

### Q1 · 文本型 Target 的 hard signal 在 v0.1 骨架里塞在哪

**答案**:`scoring.yaml` 的 `dimensions[].signal`,**与代码型 Target 完全相同**——不新增字段、不改 schema。区别只在 signal 命令本身的构造方法。

骨架层(`iter.sh` / `validate_config.py` / `templates/*.template`)**零改动**;本协议不要求任何 v0.1 骨架件扩展。

### Q2 · 信号来源分几类

**答案(改写后)**:**两类**,不分 LLM 与命令:

| 来源类别 | 描述 | 是否能算 hard |
|---|---|---|
| **(a) 命令类** | exit code + stdout 模式(`pytest -q` / `grep -c` / 自定义 runner 脚本) | **看 Q5 fixture-set 验证** |
| **(b) LLM 判定类** | LLM 输出的二元或多元判定,被脚本包裹成命令(命令跑 LLM、解析 stdout) | **看 Q5 fixture-set 验证** |

**关键判断**:能否被标为 hard **不取决于来源**(LLM 还是命令),而是**能否通过 Q5 fixture-set 验证**——Q5 通过 = 有信号价值 = hard;Q5 不通过 = 噪声 = soft。

> **改写说明**:Q5 升格前,Q2 原列了"LLM judge 硬判定"作为 (c) 类,Q6 又说"文本 hard signal 必须可重复(非 LLM 输出)"——两条打架。Q5 升格后,(c) 类取消,Q6 删除,统一由 Q5 兜底。

### Q3 · 信号本身的 ground truth 从哪来

**答案**:**必须先有 eval 集**——固定文本输入 + 期望输出 / 期望模式。

无 eval 集 = 无 hard signal 准入门槛 = 退化为纯 soft 循环 = **违反 D8 rule 2 精神**(至少 1 个 hard 维度防 LLM 单一信号把循环带偏)。

**eval 集是用户的责任,不是框架的责任**——框架只规定"必须有",不规定"怎么造"。

### Q4 · 文本型 hard signal 命令模板长什么样

**答案**:三段式:`(eval-set-path) + (runner) + (parser)`,**全部封装在命令字符串内**——`iter.sh` / `validate_config.py` 不理解命令内部结构。

- `runner` 跑命令(如 `bash tests/run_skill_eval.sh`)
- `parser` 把 stdout 解析为 1.0 / 0.0
- `eval-set-path` 是 runner / parser 的固定输入

**退出契约**(继承 v0.1 D8 rule 6/7):

| runner 退出码 | stdout 非空 | 该 hard 维度分数 |
|---|---|---|
| 0 | 是 | 1.0 |
| 0 | 否 | 0.0(rule 6 缺失) |
| 124 / 137(timeout) | — | 0.0(rule 6 缺失) |
| ≠ 0 | — | **当次 iteration reject**(rule 7) |

**为何 parser 不提为骨架件**:parser 是 Target 特定的,封装在命令字符串内最简单;提到 `iter.sh` 内置解析 = 框架要理解每种 eval 集输出格式,违反薄骨架原则。

### Q5 · **hard signal 准入判据(fixture-set 验证)**——**本协议最硬的一条**

**核心**:任何 dimension 在被标为 `type: hard` 之前,**必须**配 `fixture-set`(已知 baseline + 反例集),并在 fixture-set 上跑过验证。

#### fixture-set 最小规格

- **positive examples ≥ 10 条**:信号命令应该命中 / 通过的样本
- **negative examples ≥ 10 条**:信号命令应该排除 / 不命中的样本
- **阈值**:**positive ≥ 80% 命中、negative ≥ 80% 正确排除**——两者都过 = 信号可用 = 可标 hard
- **位置**:由用户随 `scoring.yaml` 提交,文件名约定为 `fixtures/<dimension-name>.yaml`(占位,O1 待定)
- **格式**:YAML 列表,每条 `{input: <text>, expect: <pass|fail>}`(占位,O1 待定)

#### 准入流程

1. 用户在 `scoring.yaml` 写 `type: hard` 的 dimension,附带 signal 命令
2. **准入检查**:同一目录或 `fixtures/` 子目录下必须有 `<dimension-name>.yaml`,且 ≥ 20 条样本
3. **验证**:命令在 fixture-set 上跑一遍,断言 positive ≥ 80%、negative ≥ 80%
4. **不通过** = dimension 标 hard 被拒 = **强制降级为 soft**(`validate_config.py` 在 v0.2 验证 CLI 中报错并提示降级,而不是 exit 1 阻断)——这是为了让"信号在长尾上还不够稳"的现实情况有退路,而非直接拒绝用户
5. **不通过时用户可选**:(i) 修 signal 命令 / 扩 fixture-set 重跑;(ii) 接受降级为 soft

#### 关键边界

- **Q5 是 hard/soft 的通用分界线**,**不仅限于文本型 Target**——任何 dimension(代码型 / 文本型 / 未来类型)在 `type: hard` 之前都过 Q5
- **代码型 Target 的现有维度豁免**:`pytest -q` 等社区共识 hard signal(v0.1 demo 用过)享受"已知 baseline"待遇,**首次使用不需要重跑 fixture-set**;但**用户自行构造的代码型命令**仍需 Q5
- **fixture-set 不是测试集**——它是信号的 ground truth,不是 Target 的 ground truth

### Q6 · ~~命令输出不稳定怎么办~~ — **删除,被 Q5 取代**

Q5 升格前,Q6 讨论"LLM 抖动必须留给 soft";升格后,**Q5 不通过的 LLM 判定被自动降级为 soft**——LLM 抖动问题在 hard 信号层面不存在,因为不稳定的 LLM 判定在 fixture-set 上必然达不到 80% 阈值,被识别为噪声。

### Q7 · 协议与 spec D3/D8 hard rules 的关系

| 已有契约 | 关系 | 本协议动作 |
|---|---|---|
| `scoring.yaml` schema(`dimensions[].signal`) | **不动** | Q1:信号命令塞在 signal 字段,无 schema 变更 |
| D3 hard 二进制化(1.0 / 0.0) | **继承** | Q4:三段式命令退码契约直接对齐 |
| D8 rule 6(缺失计 0) | **继承** | Q4:超时 / 空输出走 rule 6 |
| D8 rule 7(hard 失败 reject) | **继承** | Q4:exit ≠ 0 走 rule 7 |
| D8 rule 2(至少 1 个 hard 维度) | **不变** | Q3:无 eval 集 = 退化为纯 soft = 违反 rule 2 精神 |

**v0.2 spec 需要新增的契约**:**D9 rule**(一句话级)——

> **D9**:任何 `type: hard` 的 dimension 必须有 fixture-set 验证(Q5),通过方可标 hard;不通过时 `validate_config.py` 提示降级为 soft(由用户决定)。

D9 的完整设计依据在本文档 Q5。

### Q8 · 协议是否给 v0.1 加工作量

**答案:不加**。v0.1 demo 的 `pytest -q` 是社区共识 hard signal(见 Q5 §关键边界 §代码型 Target 豁免),不需要 fixture-set 验证;本协议只对**v0.2 新增的** hard signal 命令生效。

---

## 开放项(下次协议迭代再锁)

| # | 项 | 当前默认值 | 锁定时机 |
|---|---|---|---|
| **O1** | fixture-set 文件格式与目录约定 | 占位:`fixtures/<dimension-name>.yaml`,YAML 列表 `{input, expect: pass|fail}` | v0.2 第一次接文本 Target 时定 |
| **O2** | 80% 阈值是否过严 | **先写 80%** 作为占位 | v0.2 第一次跑出真实数后回看 |
| **O3** | parser 错误处理(malformed stdout / 部分输出) | **默认行为走 D8 rule 6**:parser 无法解析 stdout → 命令退出 0 但 stdout 非空 → 1.0(parser 把 malformed 当 pass);parser 自身崩溃 → 命令非 0 → **当次 reject(D8 rule 7)**。**不要发明"计 0 不 reject"中间态**——Q5 已通过 = 信号足够稳;Q5 没通过 = 不该是 hard。 | 本协议定稿即生效,不留 v0.2 实跑兜底 |
| **O4** | 协议是否带 `scripts/check_signal_fixture.sh` 的参考实现 | **不带** | 留给 implem 层 |

> **O3 改写说明**(评审意见 4):原 O3 建议"parser 无法解析 → 计 0 不 reject",经评审否决,理由是 Q5 升格后该默认值被 Q5 架空——Q5 不通过 = 信号进不了 hard 维度,谈不上"计 0"。改写后:**parser 错误要么走 rule 6(命令退出 0 + stdout 非空 → 1.0)、要么走 rule 7(parser 崩溃 → reject)**,不做第三态。

---

## 协议不回答的问题(明确划出去)

- ❌ 不规定文本型 Target 改什么(那是 `program.md` 的事)
- ❌ 不规定 judge 软维度怎么打分(那是 `judge-prompt.md` 的事)
- ❌ 不规定 eval 集本身怎么造(那是用户的责任,协议只规定"必须有 eval 集")
- ❌ 不规定 soft / hard 权重怎么分(那是 `scoring.yaml` aggregate 的事)
- ❌ 不规定 fixture-set 验证脚本形态(O4)

---

## v0.2 spec 接入指引

`docs/specs/v0.2-skeleton-spec.md`(待写)接入本协议的最薄形态:

1. spec D4 文件树新增 `fixtures/` 目录(A 类下实例化,C 类下不强制)
2. spec D9 rule 段引用本协议 Q5,文案见本文档 Q7
3. spec User Story 增加一条:"As a v0.2 framework user, I want a fixture-set validation step in `validate_config.py`, so that my `type: hard` dimensions are guaranteed to have signal value before entering the loop"
4. spec Testing Decisions 增加 T-层测试:`validate_config.py` 在 hard dimension 缺 fixture-set / fixture-set 不达阈值时降级为 soft 而非 exit 1

具体 to-spec 工作留给 v0.2 启动后做,本协议不锁 spec 形态。

---

## 与已有材料的交叉引用

- v0.1 spec D3 / D8:`docs/specs/v0.1-skeleton-spec.md` line 99-122 / line 180-193
- 隔离约定(D1 profile 级):本协议不涉及隔离;Q5 fixture-set 验证在 writer 之前跑,**不引入新 profile**
- meta 层(ADR-004):本协议是**第一层**的 hard signal 准入;meta 层 Glossary 维度是另一回事,见 `docs/adr/ADR-004-meta-layer-target.md` Open Issue
- deep-research 上车:`docs/use-cases/deep-research.md` 的 C 类 hard signal 也走 Q5——v0.2 第一次实跑 deep-research 时,deep-research 自身的 hard signal 命令必须先过 fixture-set

---

## 修订记录

- 2026-08-12 v1:首版(Hermes + Claude Code 协作起草)