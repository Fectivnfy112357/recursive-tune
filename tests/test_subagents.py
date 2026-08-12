"""T1 · Sub-agents 派发骨架件 + D1.5 字段层测试（v0.3 spec T1 a/b/c）。

覆盖：
- recipe schema 校验（空 / 缺字段 / 重名 / agents 长度 ≠3）
- spawn envelope 五字段 + status 枚举 + error_code 状态对齐
- 三类错误码（E_AGENT_FAIL / E_RECIPE_INVALID / E_STATE_RACE）
- coordinator 聚合原子性（失败 → 不落 state、不动 ratchet HEAD）
- cacheable 二次复用（status=cached，duration_ms=0）
"""

from pathlib import Path
import sys

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import subagents as sa  # noqa: E402


# ---------- helpers ----------

def _recipe(*agents):
    """造一个 3-agent recipe（默认全合法），可被测试覆盖字段后传入 validate_recipe。"""
    return {
        "agents": list(agents),
    }


def _agent(name="t", profile="writer", prompt="echo hello",
           state_rw=("out.txt",), cacheable=True):
    return {
        "name": name,
        "profile": profile,
        "prompt_path": prompt,
        "state_rw": list(state_rw),
        "cacheable": cacheable,
    }


def _three_agents():
    """合法 3-agent recipe：state_rw 各异（spec D2 直觉：不同 section → 不同 state）。"""
    return _recipe(
        _agent("a", prompt="echo aaa", state_rw=("out-a.txt",)),
        _agent("b", prompt="echo bbb", state_rw=("out-b.txt",)),
        _agent("c", prompt="echo ccc", state_rw=("out-c.txt",)),
    )


# ---------- recipe validator（spec D1.5 / T1） ----------

def test_recipe_empty_fails():
    """空 recipe（无 agents 字段）→ E_RECIPE_INVALID。"""
    errs, warns = sa.validate_recipe({})
    assert any("E_RECIPE_INVALID" in e for e in errs)
    assert warns == []


def test_recipe_agents_not_list_fails():
    """agents 字段不是 list → E_RECIPE_INVALID。"""
    errs, _ = sa.validate_recipe({"agents": "not-a-list"})
    assert any("E_RECIPE_INVALID" in e for e in errs)


def test_recipe_wrong_agent_count_two_fails():
    """agents 长度 = 2 → E_RECIPE_INVALID（spec D2 恰好 3）。"""
    errs, _ = sa.validate_recipe(_recipe(_agent("a"), _agent("b")))
    assert any("E_RECIPE_INVALID" in e and "3" in e for e in errs)


def test_recipe_wrong_agent_count_five_fails():
    """agents 长度 = 5 → E_RECIPE_INVALID。"""
    errs, _ = sa.validate_recipe(_recipe(*[_agent(f"a{i}") for i in range(5)]))
    assert any("E_RECIPE_INVALID" in e and "3" in e for e in errs)


def test_recipe_duplicate_agent_names_fails():
    """重名 agent → E_RECIPE_INVALID。"""
    r = _recipe(_agent("dup"), _agent("dup"), _agent("c"))
    errs, _ = sa.validate_recipe(r)
    assert any("E_RECIPE_INVALID" in e for e in errs)


def test_recipe_missing_agent_field_fails():
    """agent 缺 name / profile / prompt_path / state_rw / cacheable 任一 → E_RECIPE_INVALID。"""
    for missing in ("name", "profile", "prompt_path", "state_rw", "cacheable"):
        a = _agent()
        del a[missing]
        r = _recipe(a, _agent("b"), _agent("c"))
        errs, _ = sa.validate_recipe(r)
        assert any("E_RECIPE_INVALID" in e for e in errs), f"缺 {missing} 应报错"


def test_recipe_valid_three_agents_passes():
    """合法 3-agent recipe → 无 error。"""
    errs, warns = sa.validate_recipe(_three_agents())
    assert errs == []
    assert warns == []


# ---------- envelope 字段层（spec D1.5 a） ----------

def test_envelope_five_fields_complete():
    """spawn 返回信封五字段齐备：agent/status/output_path/duration_ms/error_code。"""
    env = sa.make_envelope("a", sa.STATUS_OK, "/tmp/x", 100, None)
    assert set(env.keys()) == {"agent", "status", "output_path", "duration_ms", "error_code"}


def test_envelope_status_enum():
    """status ∈ {ok, failed, cached}。"""
    for st in (sa.STATUS_OK, sa.STATUS_FAILED, sa.STATUS_CACHED):
        env = sa.make_envelope("a", st, "/tmp/x", 100, None)
        assert env["status"] in {sa.STATUS_OK, sa.STATUS_FAILED, sa.STATUS_CACHED}


def test_envelope_error_code_null_on_ok():
    """status=ok|cached → error_code=None。"""
    env_ok = sa.make_envelope("a", sa.STATUS_OK, "/tmp/x", 100, None)
    env_cached = sa.make_envelope("a", sa.STATUS_CACHED, "/tmp/x", 0, None)
    assert env_ok["error_code"] is None
    assert env_cached["error_code"] is None


def test_envelope_error_code_required_on_failed():
    """status=failed → error_code 必须非空（E_AGENT_FAIL/E_STATE_RACE/E_RECIPE_INVALID 之一）。"""
    for code in (sa.E_AGENT_FAIL, sa.E_STATE_RACE, sa.E_RECIPE_INVALID):
        env = sa.make_envelope("a", sa.STATUS_FAILED, "/tmp/x", 100, code)
        assert env["error_code"] == code


# ---------- spawn 错误码映射（spec D1.5 b） ----------

def test_spawn_nonzero_exit_returns_agent_fail(tmp_path):
    """子 agent 非零退出（prompt 故意 false）→ status=failed / error_code=E_AGENT_FAIL。"""
    a = _agent("a", prompt="bash -c 'exit 7'", state_rw=("out.txt",))
    env = sa.spawn_agent(a, tmp_path)
    assert env["status"] == sa.STATUS_FAILED
    assert env["error_code"] == sa.E_AGENT_FAIL
    assert env["duration_ms"] >= 0


def test_spawn_success_writes_output(tmp_path):
    """子 agent 成功 → 产物写到 state_rw[0]，status=ok。"""
    a = _agent("a", prompt="echo hello", state_rw=("out.txt",))
    env = sa.spawn_agent(a, tmp_path)
    assert env["status"] == sa.STATUS_OK
    assert env["error_code"] is None
    out = Path(env["output_path"])
    assert out.exists()
    assert "hello" in out.read_text(encoding="utf-8")


# ---------- coordinator 聚合 + 原子性（spec D1.5 c） ----------

def test_state_race_two_agents_share_state_path_fails(tmp_path):
    """两 agent 写同一 state_rw 路径 → E_STATE_RACE（validate 时直接拒）。"""
    r = _recipe(
        _agent("a", state_rw=("shared.txt",)),
        _agent("b", state_rw=("shared.txt",)),
        _agent("c", state_rw=("c.txt",)),
    )
    errs, _ = sa.validate_recipe(r)
    assert any("E_STATE_RACE" in e for e in errs)


def test_coordinate_failure_leaves_state_clean_and_ratchet_untouched(tmp_path):
    """聚合失败 → state 目录无 agent 产物 + ratchet_fn 未被调用（HEAD 未动）。

    ratchet_fn 用一个 list 容器当 monkey patch：append 即视为"HEAD 移动"。
    """
    r = _recipe(
        _agent("a", prompt="echo aaa"),
        _agent("b", prompt="bash -c 'exit 1'"),  # 必失败
        _agent("c", prompt="echo ccc"),
    )
    ratchet_calls = []
    result = sa.coordinate(r, tmp_path, ratchet_fn=lambda: ratchet_calls.append(1))
    assert result["committed"] is False
    # 任一产物落 state？聚合失败 → 全无（agent b 失败、a/c 不落）
    leftovers = [p for p in tmp_path.iterdir() if p.is_file()]
    assert leftovers == [], f"聚合失败应无 state 产物，发现: {leftovers}"
    assert ratchet_calls == [], "聚合失败不应动 ratchet"


def test_coordinate_success_writes_state_and_calls_ratchet(tmp_path):
    """聚合成功 → 3 个 agent 产物落 state + ratchet_fn 调用一次。"""
    ratchet_calls = []
    result = sa.coordinate(
        _three_agents(), tmp_path,
        ratchet_fn=lambda: ratchet_calls.append(1),
    )
    assert result["committed"] is True
    assert len(result["envelopes"]) == 3
    assert all(e["status"] == sa.STATUS_OK for e in result["envelopes"])
    assert ratchet_calls == [1]
    files = sorted(p.name for p in tmp_path.iterdir() if p.is_file())
    assert files == ["out-a.txt", "out-b.txt", "out-c.txt"]


# ---------- cacheable 复用（spec D1 50% 判据的来源） ----------

def test_cacheable_hit_reuses_output(tmp_path):
    """cacheable=true + output 已存在 + 上游输入未变 → status=cached（不 spawn）。

    本测试只覆盖"output 已存在"这一条件（上游输入未变留 v0.4+ 评估，
    v0.3 first cut 用产物存在性作判据即可）。
    """
    a = _agent("a", prompt="echo never-called", state_rw=("out.txt",), cacheable=True)
    # 先把产物写好
    (tmp_path / "out.txt").write_text("cached-content", encoding="utf-8")
    env = sa.spawn_agent(a, tmp_path)
    assert env["status"] == sa.STATUS_CACHED
    assert env["error_code"] is None
    assert env["duration_ms"] == 0
    assert Path(env["output_path"]).read_text(encoding="utf-8") == "cached-content"


def test_non_cacheable_reruns_even_if_output_exists(tmp_path):
    """cacheable=false + output 已存在 → 仍 spawn（status=ok，覆盖产物）。"""
    a = _agent("a", prompt="echo fresh", state_rw=("out.txt",), cacheable=False)
    (tmp_path / "out.txt").write_text("stale", encoding="utf-8")
    env = sa.spawn_agent(a, tmp_path)
    assert env["status"] == sa.STATUS_OK
    assert "fresh" in Path(env["output_path"]).read_text(encoding="utf-8")


# ---------- 端到端：单 agent spawn → 落 state（issue #8 AC 末条） ----------

def test_e2e_single_agent_spawn_drops_to_state(tmp_path):
    """独立 demo：单 agent 跑通 → 产物落 state。

    这是 issue #8 的最后一条 AC（"T1 单元测全绿，可独立 demo 单 agent spawn"）。
    """
    a = _agent("demo", prompt="echo demo-output", state_rw=("state/demo.txt",))
    env = sa.spawn_agent(a, tmp_path)
    assert env["status"] == sa.STATUS_OK
    assert env["error_code"] is None
    assert Path(env["output_path"]).exists()
    assert "demo-output" in Path(env["output_path"]).read_text(encoding="utf-8")