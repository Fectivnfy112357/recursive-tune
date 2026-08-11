# ADR-002 · Ratchet 替代覆盖式写入

**状态**：提议
**关联**：ADR-001（Loop Engineering 骨架）、ADR-004（meta 层契约——meta 与第一层共享 git ratchet）

---

## 背景

recursive-tune 的循环要「保留改进、回滚退化」。三种实现路径：

| 路径 | 实现机制 | 例子 |
|---|---|---|
| **覆盖式** | 直接写目标文件，新分数差就丢弃修改 | 临时 dir + diff |
| **Git ratchet** | 每次迭代前 `git commit`，分数上升保留 commit，下降就 `git revert` | AutoResearch、darwin-skill |
| **文件级 ratchet** | 多个版本文件共存（`config.v1.json` / `config.v2.json`），State 里指向当前 best | 传统版本管理 |

---

## 决策

**采用 git ratchet**（commit + revert）。理由：

1. **三方法都这么做**——AutoResearch 和 darwin-skill 都用 git ratchet，是被验证过的模式
2. **diff 可审计**——回滚时能精确看到改了什么，不只是"回到上一版"
3. **State 自动对齐**——git log 就是天然的 State，不需要单独维护一个"哪些版本被试过"的清单
4. **CI/CD 友好**——回滚等于 PR revert，工具链无缝

---

## 关键约束

1. **ratchet 不直接禁 git push**——recursive-tune v1 不引入「禁止 push」之类的强约束（那是 harness 层的事），但**默认行为是本地 commit，不自动 push**
2. **分数边界明确**——只有"分数严格上升"才保留 commit，"分数相等"也算退化（防止"看似没改但悄悄变复杂"）
3. **commit message 必须含 Score**——例如 `iter-12: 78→82, description: simplify whitelist`，便于后续审计
4. **results.tsv**（借鉴 autoresearch）作为 State 的辅助——记录每次迭代的 commit hash / score / 描述，便于回看

---

## 与"State 组件"的关系

按 ADR-001，State 是 Loop Engineering 6 件套之一。git ratchet 是 State 的**实现机制**，不是 State 的全部内容。State 还包含：
- `results.tsv`（迭代历史）
- `program.md`（当前任务的指令）
- `eval-prompts.json` 或 `tests/`（评测数据集）
- 当前 best score 的指针（通常由 git HEAD 隐式提供）

---

## 后果

- **Target 必须能用 git 管理**——这是 recursive-tune 的**前提条件**。如果 Target 不在 git repo 里，需要先用 `git init` 初始化
- **commit history 会爆炸式增长**——按 autoresearch 一晚 100 次迭代的规模，commit 数会很快。需要约定清理策略（v1 不实现自动压缩，但 ADR 化"何时清理"）
- **冲突解决靠 revert 而不是 merge**——多 writer 并行时各自独立 commit，不互相合并（revert 到基线再重写）

---

## 备选方案（被否决）

| 备选 | 否决理由 |
|---|---|
| 覆盖式（diff-based） | 缺审计能力，回滚粒度粗；State 单独维护成本高 |
| 文件级 ratchet（多版本共存） | 文件爆炸；State 文件指针不一致风险 |