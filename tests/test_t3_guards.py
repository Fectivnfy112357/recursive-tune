"""v0.3 T3 · 必入约束回归守护测试（spec T3）。

CI 守门（spec T3 · 必入约束回归守护）：
- (a) recipe validator 单测：`len(agents) != 3` → fail + `error_code = E_RECIPE_INVALID`
- (b) 扫描 repo 内所有示例 recipe 文件，断言 `len(agents) == 3`（T1 subagents.validate_recipe 已落）
- (c) 断点续跑代码路径 / 独立 glossary 持久化件双扫描 = 0
"""

from pathlib import Path
import subprocess
import sys

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import scan_recipes as sr  # noqa: E402
import scan_violations as sv  # noqa: E402
import subagents as sa  # noqa: E402

REPO_ROOT = sr.REPO_ROOT
RECIPES_DIR = REPO_ROOT / "recipes"


# ---------- (a) recipe validator 单测：agents 长度 ≠ 3 → fail + E_RECIPE_INVALID ----------

@pytest.mark.parametrize("bad_count", [0, 1, 2, 4, 5])
def test_validate_recipe_rejects_wrong_agent_count(bad_count):
    """spec T3 (a)：agents 长度 ≠ 3 → fail + error_code 含 E_RECIPE_INVALID。"""
    recipe = {"agents": [{"name": f"a{i}", "profile": "writer",
                          "prompt_path": "echo x", "state_rw": [f"out-{i}.txt"],
                          "cacheable": True} for i in range(bad_count)]}
    errs, _ = sa.validate_recipe(recipe)
    assert any("E_RECIPE_INVALID" in e for e in errs), (
        f"agents={bad_count} 应报错，实际: {errs}"
    )


def test_validate_recipe_accepts_exactly_three():
    """边界：agents 长度 = 3 → 通过。"""
    recipe = {"agents": [
        {"name": "a", "profile": "writer", "prompt_path": "echo a",
         "state_rw": ["a.txt"], "cacheable": True},
        {"name": "b", "profile": "writer", "prompt_path": "echo b",
         "state_rw": ["b.txt"], "cacheable": True},
        {"name": "c", "profile": "writer", "prompt_path": "echo c",
         "state_rw": ["c.txt"], "cacheable": True},
    ]}
    errs, warns = sa.validate_recipe(recipe)
    assert errs == []
    assert warns == []


# ---------- (b) 扫描 repo 内所有示例 recipe 文件 → 全部 agents == 3 ----------

def test_scan_recipes_passes_current_set():
    """当前 recipes/*.yaml 全部应通过 scan_recipes.py（agents == 3 + 字段齐）。"""
    yaml_files, errors = sr.scan_recipes(RECIPES_DIR)
    assert yaml_files, "recipes/ 应至少有 1 个示例 recipe"
    assert errors == [], f"recipe 扫描失败：{errors}"


def test_scan_recipes_cli_exits_zero():
    """CLI：scan_recipes.py 主进程 exit 0。"""
    rc = sr.main([])
    assert rc == 0


def test_each_recipe_has_exactly_three_agents():
    """逐个 recipe 验：每个 recipe 都有 3 个 agent（不依赖 scan_recipes 的报错聚合）。"""
    yaml_files = sorted(RECIPES_DIR.glob("*.yaml"))
    assert yaml_files, "recipes/ 应至少有 1 个示例 recipe"
    for path in yaml_files:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        agents = data.get("agents", [])
        assert len(agents) == 3, (
            f"{path.name}: agents 长度 = {len(agents)}, spec D2 要求恰好 3"
        )


# ---------- (c) 断点续跑 / 独立 glossary 持久化件 双扫 = 0 ----------

def test_scan_violations_zero_hits():
    """spec T3 末条：断点续跑 / glossary 独立件 双扫 = 0 命中。"""
    files_scanned, hits = sv.scan_violations()
    assert hits == [], (
        f"禁词命中 {len(hits)} 处（扫描 {files_scanned} 文件）：\n"
        + "\n".join(f"  {h['path']}:{h['line_no']} [{h['token']}] {h['line']}"
                    for h in hits)
    )


def test_scan_violations_cli_exits_zero():
    """CLI：scan_violations.py 主进程 exit 0。"""
    rc = sv.main([])
    assert rc == 0


def test_forbidden_tokens_match_spec():
    """禁词列表与 spec D1 必入约束一致（防列表漂移）。"""
    expected = {
        # 断点续跑
        "checkpoint", "pickle", "save_state", "load_state", "resume_state",
        # 独立 glossary 持久化件
        "glossary_db", "glossary_store", "glossary.pkl", "glossary.json",
    }
    assert set(sv._FORBIDDEN_TOKENS) == expected


def test_hermes_cli_flags_are_exempt():
    """hermes CLI 参数行（--resume / --restore-cwd / --no-restore-cwd）应豁免。"""
    assert sv._is_exempt("hermes --resume session-123")
    assert sv._is_exempt("hermes --no-restore-cwd -p writer")
    assert sv._is_exempt("hermes --restore-cwd")
    # 普通生产代码不应被豁免（注释行除外）
    assert not sv._is_exempt("checkpoint = True")
    assert not sv._is_exempt("x = save_state(state)")