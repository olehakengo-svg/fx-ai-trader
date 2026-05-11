from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _tier_master(
    *,
    generated_at: str = "2026-05-11T00:00:00+00:00",
    elite_live: list[str] | None = None,
    force_demoted: list[str] | None = None,
    pair_promoted: list[list[str]] | None = None,
    pair_demoted: list[list[str]] | None = None,
    strategy_lot_boost: list[str] | None = None,
) -> dict:
    return {
        "generated_at": generated_at,
        "elite_live": elite_live or [],
        "force_demoted": force_demoted or [],
        "scalp_sentinel": [],
        "universal_sentinel": [],
        "pair_promoted": pair_promoted or [],
        "pair_demoted": pair_demoted or [],
        "strategy_lot_boost": strategy_lot_boost or [],
    }


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _load_snapshot_script():
    path = ROOT / "scripts" / "save_tier_master_snapshot.py"
    spec = importlib.util.spec_from_file_location("save_tier_master_snapshot", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_save_snapshot_writes_dated_copy_with_taken_at(tmp_path, monkeypatch):
    script = _load_snapshot_script()
    src = tmp_path / "knowledge-base" / "wiki" / "tier-master.json"
    dst_dir = tmp_path / "knowledge-base" / "wiki" / "snapshots"
    _write_json(src, _tier_master(elite_live=["alpha"]))
    monkeypatch.setattr(script, "TIER_MASTER_PATH", src)
    monkeypatch.setattr(script, "SNAPSHOT_DIR", dst_dir)

    out = script.save_snapshot(snapshot_date="2026-05-11")

    assert out == dst_dir / "tier-master-2026-05-11.json"
    saved = json.loads(out.read_text(encoding="utf-8"))
    assert saved["elite_live"] == ["alpha"]
    assert saved["_snapshot_taken_at"].startswith("2026-")


def test_identical_generated_at_skips_diff_note():
    import app as app_mod

    base = _tier_master(generated_at="2026-05-10T00:00:00+00:00", elite_live=["alpha"])
    target = _tier_master(
        generated_at="2026-05-10T00:00:00+00:00",
        force_demoted=["alpha"],
    )

    result = app_mod._compute_strategies_diff(base, target)

    assert result["note"] == "snapshots have identical generated_at, no diff computed"
    assert result["changes_by_strategy"] == {}


def test_diff_detects_tier_pair_and_lot_boost_changes():
    import app as app_mod

    base = _tier_master(
        generated_at="2026-05-10T00:00:00+00:00",
        elite_live=["tier_only"],
        pair_promoted=[["pair_only", "USD_JPY"]],
        strategy_lot_boost=["boost_only"],
    )
    target = _tier_master(
        generated_at="2026-05-11T00:00:00+00:00",
        force_demoted=["tier_only"],
        pair_demoted=[["pair_only", "GBP_USD"]],
    )

    changes = app_mod._compute_strategies_diff(base, target)["changes_by_strategy"]

    assert changes["tier_only"]["tier_changed"] is True
    assert changes["tier_only"]["tier_from"] == "ELITE_LIVE"
    assert changes["tier_only"]["tier_to"] == "FORCE_DEMOTED"
    assert changes["pair_only"]["pair_cells_added"] == [
        {"pair": "GBP_USD", "tier": "PAIR_DEMOTED"}
    ]
    assert changes["pair_only"]["pair_cells_removed"] == [
        {"pair": "USD_JPY", "tier": "PAIR_PROMOTED"}
    ]
    assert changes["boost_only"]["lot_boost_toggled"] is True
    assert changes["boost_only"]["lot_boost_from"] is True
    assert changes["boost_only"]["lot_boost_to"] is False


def test_since_uses_nearest_past_snapshot_and_attaches_changes(
    tmp_path, monkeypatch, flask_client
):
    import app as app_mod

    class FakeDemoDB:
        def get_stats(self, **kwargs):
            return {"by_type": {}, "total": 0, "wins": 0, "total_pnl": 0}

        def get_closed_trades(self, **kwargs):
            return []

    current = tmp_path / "tier-master.json"
    snapshots = tmp_path / "snapshots"
    _write_json(
        current,
        _tier_master(
            generated_at="2026-05-11T00:00:00+00:00",
            force_demoted=["alpha"],
        ),
    )
    _write_json(
        snapshots / "tier-master-2026-05-01.json",
        _tier_master(generated_at="2026-05-01T00:00:00+00:00", elite_live=["old"]),
    )
    _write_json(
        snapshots / "tier-master-2026-05-04.json",
        _tier_master(generated_at="2026-05-04T00:00:00+00:00", elite_live=["alpha"]),
    )
    _write_json(
        snapshots / "tier-master-2026-05-08.json",
        _tier_master(generated_at="2026-05-08T00:00:00+00:00", elite_live=["ignored"]),
    )
    monkeypatch.setattr(app_mod, "TIER_MASTER_PATH", current)
    monkeypatch.setattr(app_mod, "TIER_MASTER_SNAPSHOT_DIR", snapshots)
    monkeypatch.setattr(app_mod, "_demo_db", FakeDemoDB())

    response = flask_client.get("/api/strategies/status?since=2026-05-05")

    assert response.status_code == 200
    body = response.get_json()
    assert body["diff_mode"] == "since"
    assert body["baseline_date"] == "2026-05-05"
    assert body["actual_baseline_date"] == "2026-05-04"
    alpha = next(s for s in body["strategies"] if s["name"] == "alpha")
    assert alpha["changes"]["tier_to"] == "FORCE_DEMOTED"
    assert body["changed_count"] >= 1


def test_compare_mode_takes_precedence_over_since(tmp_path, monkeypatch, flask_client):
    import app as app_mod

    class FakeDemoDB:
        def get_stats(self, **kwargs):
            return {"by_type": {}, "total": 0, "wins": 0, "total_pnl": 0}

        def get_closed_trades(self, **kwargs):
            return []

    current = tmp_path / "tier-master.json"
    snapshots = tmp_path / "snapshots"
    _write_json(current, _tier_master(generated_at="2026-05-11T00:00:00+00:00"))
    _write_json(
        snapshots / "tier-master-2026-05-01.json",
        _tier_master(generated_at="2026-05-01T00:00:00+00:00", elite_live=["alpha"]),
    )
    _write_json(
        snapshots / "tier-master-2026-05-08.json",
        _tier_master(generated_at="2026-05-08T00:00:00+00:00", force_demoted=["alpha"]),
    )
    monkeypatch.setattr(app_mod, "TIER_MASTER_PATH", current)
    monkeypatch.setattr(app_mod, "TIER_MASTER_SNAPSHOT_DIR", snapshots)
    monkeypatch.setattr(app_mod, "_demo_db", FakeDemoDB())

    response = flask_client.get(
        "/api/strategies/status?since=2026-05-04"
        "&compare_from=2026-05-01&compare_to=2026-05-08"
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["diff_mode"] == "compare"
    assert body["baseline_date"] == "2026-05-01"
    assert body["compare_target_date"] == "2026-05-08"
    assert body["changed_count"] == 1


def test_compare_from_without_compare_to_is_bad_request(flask_client):
    response = flask_client.get("/api/strategies/status?compare_from=2026-05-01")

    assert response.status_code == 400
    assert "compare_to" in response.get_json()["error"]


def test_since_without_any_snapshot_returns_current_with_warning(
    tmp_path, monkeypatch, flask_client
):
    import app as app_mod

    class FakeDemoDB:
        def get_stats(self, **kwargs):
            return {"by_type": {}, "total": 0, "wins": 0, "total_pnl": 0}

        def get_closed_trades(self, **kwargs):
            return []

    current = tmp_path / "tier-master.json"
    snapshots = tmp_path / "snapshots"
    _write_json(current, _tier_master(elite_live=["alpha"]))
    monkeypatch.setattr(app_mod, "TIER_MASTER_PATH", current)
    monkeypatch.setattr(app_mod, "TIER_MASTER_SNAPSHOT_DIR", snapshots)
    monkeypatch.setattr(app_mod, "_demo_db", FakeDemoDB())

    response = flask_client.get("/api/strategies/status?since=2026-05-01")

    assert response.status_code == 200
    body = response.get_json()
    assert body["warning"] == "no snapshot available"
    alpha = next(s for s in body["strategies"] if s["name"] == "alpha")
    assert "changes" not in alpha


def test_without_diff_params_preserves_strategy_shape(tmp_path, monkeypatch, flask_client):
    import app as app_mod

    class FakeDemoDB:
        def get_stats(self, **kwargs):
            return {"by_type": {}, "total": 0, "wins": 0, "total_pnl": 0}

        def get_closed_trades(self, **kwargs):
            return []

    current = tmp_path / "tier-master.json"
    _write_json(current, _tier_master(elite_live=["alpha"]))
    monkeypatch.setattr(app_mod, "TIER_MASTER_PATH", current)
    monkeypatch.setattr(app_mod, "_demo_db", FakeDemoDB())

    response = flask_client.get("/api/strategies/status")

    assert response.status_code == 200
    alpha = next(s for s in response.get_json()["strategies"] if s["name"] == "alpha")
    assert "changes" not in alpha
