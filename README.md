# recursive-tune

## What it is

让"程序 / 配置 / Skill / 流水线"自己迭代变好的通用框架——一轮 Loop = 改 → 跑 → 评分 → 保留改进 / 回滚。

当前状态:v0.3 first cut。3-agent 多语种化 PR 流水线真 e2e 跑通,`median(time_2) ≤ median(time_1) × 0.5` 断言 PASS(1508.75x speedup)。总览见 [docs/handoff/v0.3-final-summary.md](docs/handoff/v0.3-final-summary.md)。

## Quick start

**A 类(SKILL.md / 单文件 config,硬指标主导)**:

```bash
bash scripts/setup_demo.sh              # 生成 demo-target(config.yaml 默认 target_path,幂等)
# 若目标是 SKILL.md 类,改用:bash scripts/setup_demo_skill.sh(生成 demo-skill-target)
bash scripts/setup_profiles.sh          # 创建 writer / judge hermes profile(需 hermes CLI)
bash scripts/run_loop.sh --config config.yaml --iterations 3
```

**C 类(3-agent README 多语种化 PR 流水线)**:

```bash
python scripts/run_recipe.py \
    --recipe recipes/readme-multilang-3agent.yaml \
    --target /path/to/your-readme-repo
```

`state/results.tsv` 是 accepted history(被 reject 的轮次不入)。

## Limits

- **不适用 ML 训练**(属 karpathy autoresearch 领地)
- **不适用 UI/UX / 通用产品功能**(无硬指标,无法脚本验证)
- **不做断点续跑**(v0.3 first cut 范围外;agent 失败 = from-scratch 重跑)
- **不做容器级隔离**(仅 profile 级——共享文件系统与 API quota)
- **必须含 ≥1 个 hard signal**(D8 rule 2;hard 命令需 fixture-set 验证,见 spec v0.2 D9 rule)
- **Worktrees / Plugins 触发未命中**(v0.3 recipe 设计避开并行分支共享 Target 路径冲突;v0.4+ 撞 trigger 再启用)
- **recipe agents 长度必须 = 3**(spec D2 锁;5 agent 等其它划分 v0.4+ 评估)

## Links

- **项目语境 + 术语 + 版本定位**:[docs/CONTEXT.md](docs/CONTEXT.md)
- **Agent 工作约定**:[AGENTS.md](AGENTS.md)
- **Spec 链**:`docs/specs/v0.1-skeleton-spec.md` → `v0.2-skeleton-spec.md` → `v0.3-skeleton-spec.md`
- **ADR 链**:`docs/adr/`(5 份:ADR-001 核心 4 件 / ADR-002 ratchet / ADR-003.5 A 类目标域 / ADR-004 meta 层契约 / ADR-005 v0.2 范围锚定)
- **v0.3 真 e2e evidence**:`docs/handoff/v0.3-real-e2e-evidence.md`
- **v0.4 cleanup 笔记**:`docs/handoff/v0.4-cleanup-notes.md`
