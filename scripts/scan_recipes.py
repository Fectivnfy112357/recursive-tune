"""v0.3 T3 · recipe scanner —— 扫 recipes/*.yaml 守 agents 长度 = 3。

复用 T1 scripts/subagents.py 的 validate_recipe（已有 E_RECIPE_INVALID / E_STATE_RACE
错误码路径）。任一 recipe 失败 → exit 1 + 报 recipes/<name>:agents=4 形式错误。

CI 守门交给 test_t3_guards::test_scan_recipes_passes_current_set。

用法：
    python scripts/scan_recipes.py
"""

from pathlib import Path
import sys

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import subagents as sa  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
RECIPES_DIR = REPO_ROOT / "recipes"


def scan_recipes(recipes_dir=RECIPES_DIR):
    """扫 recipes_dir/*.yaml。返回 (yaml_files, errors)。"""
    recipes_dir = Path(recipes_dir)
    errors = []
    yaml_files = sorted(recipes_dir.glob("*.yaml"))
    if not yaml_files:
        return yaml_files, errors  # 空目录不算错（v0.3 first cut 允许无 recipe）
    for path in yaml_files:
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            errors.append(f"{path.name}: YAML 解析失败: {exc}")
            continue
        if not isinstance(data, dict):
            errors.append(f"{path.name}: 顶层必须是 YAML 映射")
            continue
        errs, _ = sa.validate_recipe(data)
        for e in errs:
            errors.append(f"{path.name}: {e}")
    return yaml_files, errors


def main(argv=None):
    errors = scan_recipes()[1]
    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        print(f"\nFAIL: recipe 扫描未通过（{len(errors)} 错）", file=sys.stderr)
        return 1
    files, _ = scan_recipes()
    print(f"OK: {len(files)} recipes 全部通过（agents 长度 = 3 + 字段齐备 + 无 race）")
    return 0


if __name__ == "__main__":
    sys.exit(main())