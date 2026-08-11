# ADR-004 · Meta 层契约（v0.1 承诺，v0.2 执行）

**状态**：提议（2026-08-11 arch-pivot 引入）
**关联**：ADR-001（骨架 + 两集合机制）、CONTEXT.md（两层递归愿景）

---

## 背景

CONTEXT.md 把 recursive-tune 定位为带"两层递归"的通用框架：
- **第一层**：用框架优化某个目标产物（Target）
- **第二层（meta）**：框架本身也按这套循环迭代

但原版文档没说 meta 层**具体是什么**——是文档？是骨架代码？是 program 模板？meta 跑出来的经验怎么倒灌回第一层？这些都没回答。

2026-08-11 arch-pivot 决定**v0.1 不实现 meta 可执行骨架**，但**必须 v0.1 文档级承诺**——把 meta 的 Target / Score / 共享 ratchet 机制契约写清楚，避免"两层递归沦为口号"。

可执行骨架推到 v0.2。

---

## 决策

### Meta 层的 Target

**Meta 层的 Target 是框架自己的方法论产物**：

| Target | 用途 |
|---|---|
| `docs/adr/ADR-*.md` | 当 ADR 模板被破坏 / 字段缺失时需被修复 |
| `docs/adr/ADR-*.md` 的**模板**（未来的 `templates/adr.template.md`） | 字段完整度可作为 Score |
| `templates/*.md.template`（`program.md.template` / `judge-prompt.md.template` / `scoring.yaml.template`） | 模板占位符替换成功率可作为 Score |
| `docs/CONTEXT.md` 的 glossary | glossary 术语与文档实际用法的一致率可作为 Score |

不把骨架代码（未来的 `scripts/*.py`）作为 meta Target——v0.2 范围再评估。

### Meta 层的 Score（3 维，全部硬指标）

| 维度 | 信号 | 类型 |
|---|---|---|
| ADR 必填字段完整度 | 所有 `docs/adr/ADR-*.md` 文件的"状态/关联/决策/后果/备选"5 字段是否齐 | hard（脚本可扫描） |
| 模板占位符替换成功率 | 跑一遍 `templates/*.md.template` 替换流程，无未替换的 `{{...}}` 占位符 | hard（脚本可扫） |
| Glossary 术语一致率 | glossary 词条 vs 文档实际用法，全文 grep 比对 | **需静态化**——见下方 Open Issue |

> **Open Issue（需要 v0.2 决策）**：Glossary 术语一致率本质是语义判断，不是纯 hard signal。如何用静态工具实现（AST？正则 pattern？CI lint 规则？）留给 v0.2。本 ADR 在 v0.2 落地时**必须**给出方案，否则 meta Score 退化为不可执行。

### 第一层与 Meta 层共享 Ratchet 机制

两套 Loop 共享同一套 Ratchet + State 实现：
- **同一份 git ratchet**（commit + revert）——第一层的 Target commit 走 A 类产物路径；meta 的 Target commit 走 docs 路径
- **同一份 state/results.tsv**——按 Target 类型（first-layer / meta）在表里加一列
- **同一份硬规则**（v0.1 spec D8）——分数严格上升才保留，分数相等算退化

**不共享**的：分数维度本身——meta Score 维度是"文档质量"，第一层 Score 维度是"目标产物质量"。两套并行运行、各自 commit、不互相干扰。

---

## 后果

- **v0.1 文档级承诺已落地**——本 ADR 写明 meta Target / Score / 共享 ratchet 契约
- **v0.2 才有可执行骨架**——具体 runtime 工具（脚本 / CI / lint 规则）v0.2 决定
- **CONTEXT.md「两层递归」段加注**——"v0.1 仅承诺 meta 层契约，可执行骨架 v0.2"（commit 4a 完成）
- **Glossary 待补 2 词**（commit 4a 完成）：
  - **Iteration Boundary**：meta 跨版本回滚的粒度——一次 commit 是一次 iteration 还是一个 ADR 是一次？v0.2 决定。
  - **Meta Score Validity**：meta Score 不能仅靠 meta 自身产出验证——必须由第一层独立验证（否则 circular）。v0.2 决定具体机制。

---

## 备选方案（被否决）

| 备选 | 否决理由 |
|---|---|
| meta 进 v0.1 可执行骨架 | 拖慢 v0.1 工期；meta 自身需要"文档质量 Score 已经稳定"作前置，而文档质量 Score 是 meta 第一轮跑出来的产物——不能用 meta 产出去验证 meta |
| meta 不进任何版本，直接从 CONTEXT / 营销文案里删掉"两层递归" | 弱化框架愿景；v0.2+ 还要补回来 |
| meta 把骨架代码作 Target | 破坏"docs 是 source of truth"原则；scripts 是 docs 的可执行投影，归位关系反了 |
