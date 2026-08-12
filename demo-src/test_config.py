"""demo-target 测试：1 个会失败（直到 TARGET_VALUE=42）+ 1 个永远通过。"""

from config import compute


def test_compute_returns_84():
    """初始失败（TARGET_VALUE=0 → 0 ≠ 84）；writer 把 TARGET_VALUE 改为 42 后通过。"""
    assert compute() == 84


def test_smoke_always_passes():
    assert True
