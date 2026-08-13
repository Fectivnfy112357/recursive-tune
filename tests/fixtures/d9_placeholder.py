"""D9/Q5 fixture 形式化占位桩 — v0.5 OOS 占位机制首例。

引用:
  - docs/specs/v0.3-skeleton-spec.md §"OOS 占位机制(v0.5 首用)" 段
  - docs/specs/v0.3-skeleton-spec.md §"Out of Scope(v0.3 不做)" 段
    "C 类 D9/Q5 fixture 形式化" 条目
  - ADR-006 决策 1 "in production 状态 = ≥1 use case 真跑通" 判据

触发事件: v0.4+ 撞真实 C 类任务需要跨任务可比的 ground truth 时。
占位桩函数: 本文件 d9_fixture_formalize() — raise NotImplementedError。
关闭 owner: 待指定(v0.5+ ticket 同步;v0.5 本 PR 不开新 issue)。
"""


def d9_fixture_formalize() -> dict:
    """C 类 D9/Q5 fixture 形式化 — NotImplementedError 占位。

    真实落地内容(供未来实施者参考,非本占位职责):
      - 为 C 类产物构造 ≥10 positive + ≥10 negative ground truth
        (v0.2 D1 锁:数量门槛 ≥20,执行命中门槛 ≥80%)
      - v0.3 first cut 用 D4 命令型硬指标代替(见 v0.3 spec D4 段)
      - 跨任务可比 = 不同 recipe 跑同一 fixture 集可对比结果

    Returns:
        dict: 真实落地时返回 {"positive_hit": N, "negative_reject": N, "total": N}

    Raises:
        NotImplementedError: 占位机制首例,实施前永远 raise
    """
    raise NotImplementedError(
        "D9/Q5 fixture 形式化 — 见 v0.3 spec OOS 占位机制段 + Out of Scope 段 "
        "'C 类 D9/Q5 fixture 形式化' 触发条件;撞真实 C 类任务需要跨任务可比 "
        "ground truth 时实施(≥10 positive + ≥10 negative)。"
    )
