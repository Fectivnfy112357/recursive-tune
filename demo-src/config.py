"""recursive-tune 假 Target demo 源码模板（v0.1）。

setup_demo.sh 会把本目录复制到 demo-target/ 并 git init（D8 rule 1）。
A 类单文件 Target：把 TARGET_VALUE 从 0 改为 42，让 test_compute_returns_84 通过。
hard signal = `pytest -q`（exit 0 = 全绿）。
"""

TARGET_VALUE = 0  # 失败态基线；writer 的目标：改为 42 让 test 全绿


def compute():
    return TARGET_VALUE * 2
