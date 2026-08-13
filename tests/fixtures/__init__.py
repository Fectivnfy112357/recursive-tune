# tests/fixtures/__init__.py
# 让 tests.fixtures 成为 Python package,以便 v0.3 spec OOS 占位机制
# 段首例占位桩 `tests.fixtures.d9_placeholder` 可被 import。
# 未来新增占位桩时,放在此目录 + 无 test_ 前缀(不被 pytest 收集)。
