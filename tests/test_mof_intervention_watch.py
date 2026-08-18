"""mof_intervention_watch のオフライン test pin (network 不要)。

凍結 rule (X,Y)=(2.0, 0.25%) のドリフト防止 + スコープ境界 (監視のみ、gating 不実装) を
構造的に固定する。rule の出典: mof-intervention-forward-prereg-2026-07-24.md §2.2/§5.2。
"""
import datetime as dt
import json
from pathlib import Path

import pandas as pd
import pytest

from tools import mof_intervention_watch as W


# ─── 凍結パラメータのドリフト防止 pin ────────────────────────────────────────
def test_frozen_params_pinned():
    # §5.2 凍結値。この test を変更する PR は pre-reg 違反 (再校正禁止)。
    assert W.FROZEN_X == 2.0
    assert W.FROZEN_Y == 0.25
    assert W.RANGE_MED_LOOKBACK == 20


def test_rule_boundary_inclusive():
    # candidate(d)=1 ⟺ co_ret ≤ −Y% ∧ ratio ≥ X (両端含む)
    assert W.rule_candidate(-0.25, 2.0) is True
    assert W.rule_candidate(-0.26, 2.1) is True
    assert W.rule_candidate(-0.24, 5.0) is False        # 下落不足
    assert W.rule_candidate(-1.99, 1.99) is False       # レンジ不足
    assert W.rule_candidate(0.30, 7.0) is False         # 上昇日 (2022-10-24 型は構造的補足不能)


# ─── UTC-day 集計 (verdict-grade 実装と同型) ─────────────────────────────────
def _hourly(day: str, opens, highs, lows, closes):
    idx = pd.DatetimeIndex([f"{day} {h:02d}:00" for h in range(len(opens))], tz="UTC")
    return pd.DataFrame({"Open": opens, "High": highs, "Low": lows, "Close": closes},
                        index=idx)


def test_build_daily_agg_and_weekend_filter():
    bars = pd.concat([
        _hourly("2026-08-14", [150.0, 149.5], [150.2, 149.6], [149.4, 148.8],
                [149.5, 149.0]),                        # 金曜
        _hourly("2026-08-15", [149.0], [149.1], [148.9], [149.0]),  # 土曜 → 除外
        _hourly("2026-08-17", [149.0, 149.2], [149.3, 149.4], [148.9, 149.1],
                [149.2, 149.3]),                        # 月曜
    ])
    daily = W.build_daily(bars)
    assert dt.date(2026, 8, 15) not in daily.index      # weekday<5 filter
    d = daily.loc[dt.date(2026, 8, 14)]
    assert d["open"] == 150.0 and d["close"] == 149.0
    assert d["range"] == pytest.approx(150.2 - 148.8)
    assert d["co_ret_pct"] == pytest.approx((149.0 / 150.0 - 1) * 100)
    assert d["n_bars"] == 2


def _synthetic_daily(n_quiet=25, drop_day=True):
    """静穏 n 日 + (任意で) 介入型 1 日の日次 frame を build_daily 経由で作る。"""
    days = [d.date() for d in pd.bdate_range("2026-06-01", periods=n_quiet)]
    frames = []
    for d in days:
        # 静穏日: range 0.5、微小陽線
        frames.append(_hourly(d.isoformat(), [150.0, 150.1], [150.3, 150.5],
                              [150.0, 150.0], [150.1, 150.2]))
    if drop_day:
        target = (pd.Timestamp(days[-1]) + pd.offsets.BDay(1)).date()
        # 介入型: open 150 → close 147 (−2%)、range 4.0 = med20(0.5)×8
        frames.append(_hourly(target.isoformat(), [150.0, 148.0], [150.5, 148.5],
                              [147.5, 146.5], [148.0, 147.0]))
    return W.build_daily(pd.concat(frames))


def test_evaluate_day_candidate_fires_on_intervention_signature():
    daily = _synthetic_daily()
    target = daily.index[-1]
    rec = W.evaluate_day(daily, target)
    assert rec["status"] == "evaluated"
    assert rec["candidate"] is True
    assert rec["co_ret_pct"] <= -W.FROZEN_Y
    assert rec["range_ratio"] >= W.FROZEN_X
    assert "thin" in rec.get("note", "")                # n_bars=2 < 12


def test_evaluate_day_quiet_day_no_fire():
    daily = _synthetic_daily(drop_day=False)
    rec = W.evaluate_day(daily, daily.index[-1])
    assert rec["status"] == "evaluated"
    assert rec["candidate"] is False


def test_evaluate_day_no_data_and_insufficient_history():
    daily = _synthetic_daily()
    rec = W.evaluate_day(daily, dt.date(2030, 1, 6))    # 不在日 (休場/欠損)
    assert rec["status"] == "no_data"
    with pytest.raises(RuntimeError):                   # med20 未成立は構造エラー
        W.evaluate_day(daily, daily.index[3])


def test_last_completed_utc_weekday():
    assert W.last_completed_utc_weekday(dt.date(2026, 8, 17)) == dt.date(2026, 8, 14)  # 月→金
    assert W.last_completed_utc_weekday(dt.date(2026, 8, 16)) == dt.date(2026, 8, 14)  # 日→金
    assert W.last_completed_utc_weekday(dt.date(2026, 8, 19)) == dt.date(2026, 8, 18)  # 水→火


# ─── KB 記録 = dedup 状態 ────────────────────────────────────────────────────
def test_record_dedup_roundtrip(tmp_path):
    out = str(tmp_path)
    day = dt.date(2026, 8, 14)
    assert W.already_recorded(day, out) is False
    W.append_record({"day": day.isoformat(), "status": "evaluated",
                     "candidate": False}, out)
    assert W.already_recorded(day, out) is True
    assert W.already_recorded(dt.date(2026, 8, 17), out) is False
    p = Path(W.record_path(day, out))
    assert p.name == "2026-08.jsonl"
    lines = [json.loads(x) for x in p.read_text().splitlines()]
    assert len(lines) == 1


# ─── スコープ境界の構造 pin ──────────────────────────────────────────────────
def test_no_gating_or_order_path_imported():
    """監視のみ — order/gating 系への参照が紛れ込んだら即 fail (Variant B 予防)。"""
    src = Path(W.__file__).read_text(encoding="utf-8")
    for banned in ("oanda_client", "OandaBridge", "demo_trader", "place_order",
                   "close_position"):
        assert banned not in src, f"gating/order 経路の参照が混入: {banned}"


def test_alert_text_carries_discipline():
    rec = {"day": "2026-08-14", "co_ret_pct": -1.99, "range": 5.79,
           "range_ratio": 7.7, "med20_range": 0.75}
    msg = W.format_alert(rec)
    assert "監視のみ" in msg
    assert "candidate ≠ 介入ラベル" in msg
    assert "自動 gating はしない" in msg


def test_post_discord_rejects_non_webhook_url():
    with pytest.raises(ValueError):
        W.post_discord("x", "https://evil.example.com/api/webhooks/1/2")
