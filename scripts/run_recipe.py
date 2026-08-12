"""v0.3 T2a · recipe runner —— recipe.yaml → 1 轮 multi-agent pipeline。

职责（薄 glue，T1 骨架件不变）：
- 读 recipe YAML
- 注入 SUBAGENTS_REPO_ROOT env（spawn_agent 子 bash 展开 $SUBAGENTS_REPO_ROOT）
- 调 subagents.coordinate(recipe, state_dir, ratchet_fn=git_commit_fn)
- ratchet_fn 实现 = git add -A + git commit -qm（v0.2 iter.sh:241-242 模式复用）
- target_repo 必须是 git repo（spec D8 rule 1 沿用：Target 是 git 仓库）
- state_dir = target_repo/.subagents_state/（recipe 内的 state_rw 相对此解析）

ratchet 复用策略（spec D1 落点）：v0.2 已用 git 作为 ratchet（ADR-002），
本模块不新写 ratchet 实现，直接复用 git commit 流程；调用方可通过
ratchet_fn 参数替换为 mock / 计数桩（test_t2a_e2e 用）。
"""

from pathlib import Path
import argparse
import os
import subprocess
import sys

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import subagents as sa  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent


def _ensure_git_repo(path):
    """target_repo 必须 init 过（spec D8 rule 1）。已 init 跳过；未 init 自动 init。"""
    path = Path(path)
    if not (path / ".git").exists():
        subprocess.run(["git", "-C", str(path), "init", "-q"], check=True)
        subprocess.run(["git", "-C", str(path), "config", "user.email",
                        "v0.3@recursive-tune"], check=True)
        subprocess.run(["git", "-C", str(path), "config", "user.name",
                        "v0.3 runner"], check=True)


def git_commit_ratchet(target_repo, msg="subagents: recipe run"):
    """ratchet_fn 默认实现：git add -A + git commit -qm（v0.2 iter.sh 模式复用）。

    若无变更（nothing to commit），跳过 commit 但不报错——T2a cache 命中场景
    下产物未变是预期，不应触发 set -e 退出。
    """
    target = Path(target_repo)
    subprocess.run(["git", "-C", str(target), "add", "-A"], check=True)
    # 检查是否有 staged 变更
    rc = subprocess.run(
        ["git", "-C", str(target), "diff", "--cached", "--quiet"],
        capture_output=True,
    ).returncode
    if rc == 0:
        # 无 staged 变更 → 跳过 commit
        return None
    subprocess.run(["git", "-C", str(target), "commit", "-qm", msg], check=True)
    return subprocess.run(
        ["git", "-C", str(target), "rev-parse", "--short", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()


def run_recipe(recipe_path, target_repo, *, ratchet_fn=None):
    """跑一次 recipe。

    返回 dict：{"envelopes": [...], "committed": bool, "commit_sha": str|None,
                "state_dir": str, "ratchet_calls": int}。
    """
    recipe_path = Path(recipe_path)
    target_repo = Path(target_repo).resolve()
    _ensure_git_repo(target_repo)

    recipe = yaml.safe_load(recipe_path.read_text(encoding="utf-8"))

    # env 注入：spawn_agent 子 bash 展开 $SUBAGENTS_REPO_ROOT
    os.environ["SUBAGENTS_REPO_ROOT"] = str(REPO_ROOT)

    state_dir = target_repo / ".subagents_state"
    state_dir.mkdir(parents=True, exist_ok=True)

    ratchet_calls = {"n": 0}

    def _ratchet_wrapper():
        ratchet_calls["n"] += 1
        if ratchet_fn is not None:
            return ratchet_fn(target_repo)
        return git_commit_ratchet(target_repo, msg=f"subagents: recipe={recipe_path.stem}")

    result = sa.coordinate(recipe, state_dir, ratchet_fn=_ratchet_wrapper)
    result["state_dir"] = str(state_dir)
    result["ratchet_calls"] = ratchet_calls["n"]
    result["commit_sha"] = _last_commit_sha(target_repo)
    return result


def _last_commit_sha(target_repo):
    try:
        return subprocess.run(
            ["git", "-C", str(target_repo), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except subprocess.CalledProcessError:
        return None


def main(argv=None):
    argv = list(argv if argv is not None else sys.argv[1:])
    parser = argparse.ArgumentParser(prog="run_recipe")
    parser.add_argument("recipe", help="recipe YAML 路径")
    parser.add_argument("target_repo", help="Target git 仓库路径（自动 init）")
    args = parser.parse_args(argv)

    result = run_recipe(args.recipe, args.target_repo)
    print(f"committed={result['committed']} ratchet_calls={result['ratchet_calls']} "
          f"commit_sha={result['commit_sha']}")
    for env in result["envelopes"]:
        print(f"  {env['agent']}: status={env['status']} "
              f"duration_ms={env['duration_ms']} error_code={env['error_code']}")
    return 0 if result["committed"] else 1


if __name__ == "__main__":
    sys.exit(main())