"""M1 強定義 (M1_STRONG) + M3 二定義分離 readout の estimand・境界・配線 pin。

2026-09-10 meta-audit R4(a)/(b) 修復 (rule:R3)。pin は「性質」で書く
(lesson: project_freshness_ui_ssot_pin_property_2026_08_29):
- 判定境界 (N=29/30、EV 0.99/1.00、Wilson 下限の 0 跨ぎ) は跨いだ瞬間に
  カウントが動くことで pin する
- flip_attribution は「分解の和 = 全変化」の恒等式で pin する
- 読み手の配線は cron 定義 (render.yaml) と quant_gate_status の呼び出しまで pin する
  (読み手なしの計装は禁止 — write-only 教訓)
"""
from __future__ import annotations

import inspect
import re
from datetime import datetime, timedelta
from pathlib import Path

from tools import m1_clean_live_monitor as m1

ROOT = Path(__file__).resolve().parent.parent
ANCHOR = datetime(2026, 9, 10, 0, 0, 0)


def row(
    days_ago: float,
    pnl: float,
    *,
    trade_id: str,
    entry_type: str = "carry_dip",
    instrument: str = "USD_JPY",
    direction: str = "BUY",
    oanda_trade_id: str = "oanda-1",
    status: str = "CLOSED",
    dedup_violation: int = 0,
) -> dict:
    ts = ANCHOR - timedelta(days=days_ago)
    return {
        "trade_id": trade_id,
        "created_at": ts.strftime("%Y-%m-%d %H:%M:%S"),
        "pnl_pips": pnl,
        "oanda_trade_id": oanda_trade_id,
        "instrument": instrument,
        "status": status,
        "dedup_violation": dedup_violation,
        "is_shadow": 0,
        "entry_type": entry_type,
        "direction": direction,
    }


def cell_rows(n: int, pnl: float, *, prefix: str, start_days_ago: float = 2.0,
              spacing: float = 2.0, **kw) -> list[dict]:
    """1 セルに n 行 (cutoff 2026-04-08 以降・anchor 以前に収まる範囲で)。"""
    return [
        row(start_days_ago + i * spacing, pnl, trade_id=f"{prefix}{i}", **kw)
        for i in range(n)
    ]


# --------------------------------------------------------------------------
# Wilson 下限 — 0 跨ぎと単調性
# --------------------------------------------------------------------------

def test_wilson_lower_zero_crossing():
    """wins=0 で正確に 0.0 (「> 0」を満たさない)、wins=1 で正へ跨ぐ。"""
    assert m1.wilson_lower(0, 30) == 0.0
    assert m1.wilson_lower(1, 30) > 0.0
    assert m1.wilson_lower(0, 0) == 0.0  # N=0 は 0


def test_wilson_lower_monotonic_in_wins():
    assert m1.wilson_lower(10, 30) < m1.wilson_lower(20, 30) < m1.wilson_lower(30, 30)


def test_strong_cell_requires_wilson_lower_positive():
    """資格条件に wilson_lo > 0 が実際に配線されていること (条件の直接 pin)。

    win-rate 解釈では EV>0 が wilson_lo>0 を含意するため実データで単独に
    落とせない — 条件自体が外れると通る fake cell で拘束を pin する。
    """
    base = {"n": 30, "ev": 2.0, "wilson_lo": 0.0}
    assert m1._cell_is_strong(base) is False
    assert m1._cell_is_strong({**base, "wilson_lo": 0.001}) is True


# --------------------------------------------------------------------------
# M1_STRONG セル資格の判定境界
# --------------------------------------------------------------------------

def test_strong_cell_boundary_n29_vs_n30():
    """N=29 は不資格、30 本目で資格 (境界は ≥30 の含む側)。"""
    rows29 = cell_rows(29, 2.0, prefix="n")
    s29 = m1.strong_summary(rows29, ANCHOR)
    assert s29["n_cells_strong"] == 0
    assert s29["m1_strong_cell_met"] is False

    rows30 = rows29 + [row(90.0, 2.0, trade_id="n29")]
    s30 = m1.strong_summary(rows30, ANCHOR)
    assert s30["n_cells_strong"] == 1
    assert s30["m1_strong_cell_met"] is True
    assert s30["qualifying_cells"][0]["n"] == 30


def test_strong_cell_boundary_ev_0p99_vs_1p00():
    """EV=+0.99 は強定義に落ち、rederivation literal (EV>0) には入る。

    文書間の閾値矛盾 (正EV vs ≥+1.0p/t) が出力上で区別できることの pin。
    """
    rows_low = cell_rows(30, 0.99, prefix="e")
    s = m1.strong_summary(rows_low, ANCHOR)
    assert s["n_cells_strong"] == 0
    assert s["n_cells_rederivation_literal"] == 1  # EV>0 では資格

    rows_hi = cell_rows(30, 1.0, prefix="f")
    s2 = m1.strong_summary(rows_hi, ANCHOR)
    assert s2["n_cells_strong"] == 1
    assert s2["n_cells_rederivation_literal"] == 1


def test_strong_cell_n_is_cumulative_post_cutoff_only():
    """cutoff (2026-04-08) より前の clean live 行はセル N に数えない。"""
    days_to_pre_cutoff = (ANCHOR - datetime(2026, 4, 7)).days  # cutoff 前日
    rows29 = cell_rows(29, 2.0, prefix="c")
    pre_cutoff = row(days_to_pre_cutoff, 2.0, trade_id="c-pre")
    s = m1.strong_summary(rows29 + [pre_cutoff], ANCHOR)
    assert s["n_cells_strong"] == 0, "cutoff 前の行が N に混入している"

    post_cutoff = row(days_to_pre_cutoff - 2, 2.0, trade_id="c-post")
    s2 = m1.strong_summary(rows29 + [post_cutoff], ANCHOR)
    assert s2["n_cells_strong"] == 1


def test_strong_book_and_full_definitions():
    """book 定義 (§8 案) = weak verdict MET のみ。FULL = セル ∧ book。"""
    # 分散が小さく一貫して勝つ窓 → weak MET / セルも N≥30 EV≥1 で資格
    rows = [row(1 + i * 0.5, 8.0 + (i % 3), trade_id=f"w{i}") for i in range(40)]
    weak = m1.summarize(rows, ANCHOR)
    assert weak["verdict"] == "MET"
    s = m1.strong_summary(rows, ANCHOR, weak=weak)
    assert s["m1_strong_book_met"] is True
    assert s["m1_strong_cell_met"] is True
    assert s["m1_strong_full_met"] is True

    # 窓の外 (31d 前より昔) に負けを足すと累積セル EV が崩れる →
    # book は据え置きのまま cell/full が落ちる = 2 定義が独立に動く
    rows_bad_history = rows + [
        row(40 + i, -50.0, trade_id=f"h{i}") for i in range(30)
    ]
    weak2 = m1.summarize(rows_bad_history, ANCHOR)
    assert weak2["verdict"] == "MET"  # 30d 窓は同じ
    s2 = m1.strong_summary(rows_bad_history, ANCHOR, weak=weak2)
    assert s2["m1_strong_book_met"] is True
    assert s2["m1_strong_cell_met"] is False
    assert s2["m1_strong_full_met"] is False


def test_definition_conflict_is_always_surfaced():
    """文書間矛盾 (§8 vs rederivation §4 / EV 閾値) は毎回明示される。"""
    s = m1.strong_summary(cell_rows(5, 1.0, prefix="d"), ANCHOR)
    assert s["definition_conflict"]["exists"] is True
    joined = " ".join(s["definition_conflict"]["notes"])
    assert "§8" in joined and "user" in joined
    md = m1.to_markdown_strong(s)
    assert "定義矛盾" in md
    assert "正EV literal" in md  # 両カウントの併記


# --------------------------------------------------------------------------
# 弱定義 readout の必須併記 (task (a)) — N / flip_attribution / P(sum<=0)
# --------------------------------------------------------------------------

def test_weak_markdown_always_carries_n_flip_and_bootstrap():
    rows = [row(1 + i, (-1) ** i * 5.0, trade_id=f"k{i}") for i in range(8)]
    rep = m1.summarize(rows, ANCHOR)
    md = m1.to_markdown(rep)
    assert re.search(r"N=\d+", md), "N が併記されていない"
    assert "P(sum<=0)" in md, "bootstrap P(sum<=0) が併記されていない"
    assert "窓外へ脱落" in md, "flip_attribution (新規 vs 窓外脱落) が併記されていない"


def test_flip_attribution_decomposition_is_complete():
    """分解の恒等式: sum_added − sum_aged_out = sum_now − sum_prev。

    「新規流入」と「窓外脱落」以外の経路で窓の合計が動かないことの性質 pin。
    """
    rows = (
        [row(0.5 + i, 7.0 - i, trade_id=f"new{i}") for i in range(4)]        # 新規
        + [row(10 + i, (-1) ** i * (3 + i), trade_id=f"mid{i}") for i in range(6)]  # 両窓
        + [row(30.5 + i * 1.7, -20.0 + i, trade_id=f"old{i}") for i in range(5)]    # 脱落
    )
    rep = m1.summarize(rows, ANCHOR, lookback=7)
    fa = rep["flip_attribution"]
    lhs = round(fa["sum_added"] - fa["sum_aged_out"], 2)
    rhs = round(rep["sum_pips"] - fa["sum_prev"], 2)
    assert lhs == rhs, f"分解が全変化と一致しない: {lhs} != {rhs}"
    assert fa["delta"] == lhs


# --------------------------------------------------------------------------
# M3a (throughput) — カウントと線形外挿 ETA
# --------------------------------------------------------------------------

def test_m3a_count_and_per_cell_eta_arithmetic():
    """N=20 のうち直近 30d に 10 → rate=10/30d → 残り 10 本は +30 日。"""
    done = cell_rows(35, 1.0, prefix="dn")  # 到達済セル
    grower = (
        cell_rows(10, 1.0, prefix="g-recent", start_days_ago=1.0, spacing=2.5,
                  entry_type="ps_eur_gbp", instrument="EUR_GBP")
        + cell_rows(10, 1.0, prefix="g-old", start_days_ago=40.0, spacing=3.0,
                    entry_type="ps_eur_gbp", instrument="EUR_GBP")
    )
    stalled = cell_rows(5, 1.0, prefix="s", start_days_ago=50.0,
                        entry_type="kalman_d7", instrument="AUD_JPY")
    m3 = m1.m3_summary(done + grower + stalled, ANCHOR)
    a = m3["m3a"]
    assert a["cells_done"] == 1
    assert a["met"] is False

    per = {e["cell"]: e for e in a["per_cell"]}
    g = per["ps_eur_gbp×EUR_GBP×BUY"]
    assert g["rate_per_30d"] == 10
    assert g["eta_days"] == 30.0
    assert g["eta_date"] == (ANCHOR + timedelta(days=30)).date().isoformat()
    assert per["kalman_d7×AUD_JPY×BUY"]["eta_days"] is None  # rate=0 は外挿不能

    # 蓄積中セルが 3 本未満 → 3 本目 ETA は None (捏造しない)
    assert a["eta_date"] is None


def test_m3a_eta_is_third_cell_completion():
    done = cell_rows(35, 1.0, prefix="dn")
    g1 = cell_rows(15, 1.0, prefix="g1", start_days_ago=1.0, spacing=1.9,
                   entry_type="ps_eur_gbp", instrument="EUR_GBP")  # 15/30d → 残15 → +30d
    g2 = cell_rows(6, 1.0, prefix="g2", start_days_ago=1.0, spacing=4.5,
                   entry_type="ps_aud_jpy", instrument="AUD_JPY")  # 6/30d → 残24 → +120d
    m3 = m1.m3_summary(done + g1 + g2, ANCHOR)
    a = m3["m3a"]
    assert a["cells_done"] == 1
    assert a["eta_days"] == 120.0  # 3 本目 = 最遅の g2
    assert a["eta_date"] == (ANCHOR + timedelta(days=120)).date().isoformat()


# --------------------------------------------------------------------------
# M3b (return) — 正EVセルの寄与・目標境界・ETA の意味論
# --------------------------------------------------------------------------

def test_m3b_only_positive_ev_cells_contribute():
    winner = cell_rows(10, 5.0, prefix="w", start_days_ago=1.0)  # 全部窓内 +50p
    loser = cell_rows(10, -9.0, prefix="l", start_days_ago=1.0,
                      entry_type="ps_eur_gbp", instrument="EUR_GBP")
    b = m1.m3_summary(winner + loser, ANCHOR, nav_jpy=100000.0)["m3b"]
    assert b["n_positive_ev_cells"] == 1
    assert b["pips_30d"] == 50.0
    # JPY quote は正確: 1000u × 0.01 = ¥10/pip → 50p = ¥500 → 0.5% of ¥100k
    assert b["jpy_30d_est"] == 500.0
    assert b["pct_nav_30d_est"] == 0.5
    assert b["met"] is True  # 境界は ≥ target (0.5 ちょうどで達成)
    assert b["eta"] == "達成中"


def test_m3b_below_target_is_unreachable_by_linear_extrapolation():
    rows = cell_rows(10, 1.0, prefix="p", start_days_ago=1.0)  # +10p = ¥100
    b = m1.m3_summary(rows, ANCHOR, nav_jpy=1000000.0)["m3b"]
    assert b["met"] is False
    assert "到達不能" in b["eta"]


def test_m3a_splits_cumulative_vs_active_populations():
    """累積 N≥30 と「直近 30d 稼働」を混ぜない (ps capture 二母集団教訓)。

    休眠 legacy セル (R2 demote 済み等) は cells_done に入るが
    cells_done_active には入らない。
    """
    dormant = cell_rows(35, 1.0, prefix="dm", start_days_ago=40.0, spacing=2.0)
    active = (
        cell_rows(30, 1.0, prefix="ac-old", start_days_ago=35.0, spacing=2.0,
                  entry_type="ps_eur_gbp", instrument="EUR_GBP")
        + cell_rows(3, 1.0, prefix="ac-new", start_days_ago=1.0,
                    entry_type="ps_eur_gbp", instrument="EUR_GBP")
    )
    a = m1.m3_summary(dormant + active, ANCHOR)["m3a"]
    assert a["cells_done"] == 2
    assert a["cells_done_active"] == 1
    md = m1.to_markdown_m3(m1.m3_summary(dormant + active, ANCHOR))
    assert "直近30d 稼働 1" in md


def test_nav_parse_handles_flat_and_nested_payload():
    """/api/oanda/status の NAV は flat / 一段ネスト両方を受ける (実測 09-10)。"""
    nested = {"account": {"account": {"NAV": "275486.3010"}, "lastTransactionID": "1"}}
    assert m1._nav_from_status_payload(nested) == 275486.301
    flat = {"account": {"NAV": 100000}}
    assert m1._nav_from_status_payload(flat) == 100000.0
    assert m1._nav_from_status_payload({"account": {"error": "OANDA not active"}}) is None
    assert m1._nav_from_status_payload(None) is None


def test_m3b_without_nav_reports_unknown_not_fabricated():
    rows = cell_rows(10, 1.0, prefix="q", start_days_ago=1.0)
    b = m1.m3_summary(rows, ANCHOR, nav_jpy=None)["m3b"]
    assert b["pct_nav_30d_est"] is None
    assert b["met"] is False
    assert "UNKNOWN" in b["eta"]
    assert b["pips_30d"] == 10.0  # 一次単位 (pips) は NAV 無しでも成立


# --------------------------------------------------------------------------
# 後方互換 — 弱定義 readout は --strong なしで不変
# --------------------------------------------------------------------------

def test_weak_report_shape_unchanged_without_strong():
    rows = cell_rows(5, 1.0, prefix="b")
    rep = m1.summarize(rows, ANCHOR)
    assert "strong" not in rep and "m3" not in rep
    md = m1.to_markdown(rep)
    assert "M1_STRONG" not in md and "## M3" not in md

    sig = inspect.signature(m1.build_report)
    assert sig.parameters["strong"].default is False, (
        "--strong はオプトイン (既存呼び出しの出力を変えない)"
    )


def test_strong_sections_render_after_weak_in_markdown():
    rows = cell_rows(35, 2.0, prefix="r", start_days_ago=1.0, spacing=0.5)
    rep = m1.summarize(rows, ANCHOR)
    rep["strong"] = m1.strong_summary(rows, ANCHOR, weak=rep)
    rep["m3"] = m1.m3_summary(rows, ANCHOR, nav_jpy=278905.0)
    md = m1.to_markdown(rep)
    assert md.index("## M1 KPI") < md.index("## M1_STRONG") < md.index("## M3")


# --------------------------------------------------------------------------
# 読み手の配線 — cron (render.yaml) と quant_gate_status (同一コミット必須)
# --------------------------------------------------------------------------

def _tier_a_cron_block() -> str:
    text = (ROOT / "render.yaml").read_text()
    idx = text.index("name: fx-ai-tier-a-gate-status")
    return text[idx: idx + 600]


def test_tier_a_cron_calls_strong_readout():
    """Tier A cron (render.yaml) が --strong 込みで読み手を呼ぶこと。

    読み手なしの計装は禁止 — 強定義を実装しても cron が弱定義のままなら
    write-only の再来になる。
    """
    block = _tier_a_cron_block()
    start_cmd = next(
        line for line in block.splitlines() if "startCommand" in line
    )
    assert "quant_gate_status.py" in start_cmd
    assert "--to-discord" in start_cmd
    assert "--strong" in start_cmd, "Tier A cron が強定義 readout を呼んでいない"


def test_quant_gate_status_passes_strong_through():
    from tools import quant_gate_status as qgs

    assert qgs.m1 is m1
    sig = inspect.signature(qgs.build_report)
    assert "strong" in sig.parameters

    src = inspect.getsource(qgs.run_m1_readout)
    assert "m1.build_report(strong=strong)" in src, (
        "run_m1_readout が strong を m1 に渡していない"
    )
    main_src = inspect.getsource(qgs.main)
    assert '"--strong"' in main_src
    assert "build_report(strong=args.strong)" in main_src, (
        "CLI の --strong が build_report に配線されていない"
    )


def test_quant_gate_markdown_carries_strong_sections_when_present():
    """強定義セクションが Tier A Markdown に実際に載ること (値でなく構造)。

    Discord は 1900 字切り詰めなので M1 系は Readiness より前に出る。
    """
    from tools import quant_gate_status as qgs
    from tools.alpha_budget_tracker import _empty_state

    rows = cell_rows(35, 2.0, prefix="z", start_days_ago=1.0, spacing=0.5)
    m1_rep = m1.summarize(rows, ANCHOR)
    m1_rep["strong"] = m1.strong_summary(rows, ANCHOR, weak=m1_rep)
    m1_rep["m3"] = m1.m3_summary(rows, ANCHOR, nav_jpy=278905.0)
    md = qgs.to_markdown({
        "generated_at": "2026-09-10T00:00:00+00:00",
        "m1_readout": m1_rep,
        "quant_readiness": "readiness-body",
        "alpha_budget": _empty_state("2026-09"),
        "candidate_queue_7d": {"total": 0, "pass": 0, "shadow_only": 0, "recent_names": []},
        "prereg_trigger_watch": "watch-body",
    })
    assert "## M1_STRONG" in md
    assert "## M3 (二定義分離)" in md
    assert md.index("## M1_STRONG") < md.index("## Readiness")
    assert md.index("## M3 (二定義分離)") < md.index("## Readiness")


# --------------------------------------------------------------------------
# Discord 配信 — 新読み手 (strong) を足しても既存読み手を切り落とさない
# --------------------------------------------------------------------------

def test_discord_chunking_preserves_all_sections():
    """--strong で先頭ブロックが肥大しても Readiness / prereg watch が
    切り落とされないこと (旧 text[:1900] 単発送信では毎日必ず消えていた)。
    """
    from tools import quant_gate_status as qgs

    body = (
        "# Quant Gate Status\nhead\n"
        + "## M1 KPI\n" + "a" * 1200 + "\n"
        + "## M1_STRONG\n" + "b" * 800 + "\n"
        + "## M3 (二定義分離)\n" + "c" * 500 + "\n"
        + "## Readiness\nreadiness-body\n"
        + "## prereg\nwatch-body"
    )
    chunks = qgs._discord_chunks(body)
    assert all(len(c) <= qgs.DISCORD_CHAR_LIMIT for c in chunks)
    assert len(chunks) <= qgs.DISCORD_MAX_MESSAGES
    joined = "\n".join(chunks)
    assert "readiness-body" in joined, "Readiness が切り落とされた"
    assert "watch-body" in joined, "prereg watch が切り落とされた"
    # M1 は必ず先頭チャンクの先頭側 (Discord 通知の最初に見える)
    assert "## M1 KPI" in chunks[0]


def test_discord_chunking_short_text_is_single_message():
    from tools import quant_gate_status as qgs

    assert qgs._discord_chunks("## M1 KPI\nshort") == ["## M1 KPI\nshort"]


def test_send_discord_uses_chunking():
    """send_discord が chunking を実際に通すこと (配線 pin)。"""
    from tools import quant_gate_status as qgs

    src = inspect.getsource(qgs.send_discord)
    assert "_discord_chunks" in src, "send_discord が分割送信を通していない"
    assert "[:1900]" not in src, "旧 hard-cut 単発送信が残っている"
