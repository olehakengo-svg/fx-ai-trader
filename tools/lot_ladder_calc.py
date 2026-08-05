"""Lot ladder R1 packet calculator.

SSOT: knowledge-base/wiki/analyses/lot-ladder-template-2026-08.md
ロット階段パケット (§8) の全数値を機械生成する。手計算での起案は禁止。

Kelly の式は本番実装 modules.risk_analytics.kelly_fraction を import して使う
(BT⇄本番の式同期原則 — 別式の再実装禁止)。MC 検証も同モジュールの
monte_carlo_ruin を JPY 建てで呼ぶ。

Usage (例 — placeholder 統計):
    python3 tools/lot_ladder_calc.py \
        --nav 326473 --pair USD_JPY --price 147.0 \
        --n 30 --mean 7.9 --sigma 35 --wr 0.55 --avg-win 30 --avg-loss 20 \
        --disaster-sl 150 --events-per-month 3.28 --current-rung 1000 \
        --max-concurrent 3
"""
from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import List, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.risk_analytics import kelly_fraction, monte_carlo_ruin  # noqa: E402

# ── テンプレ §1/§4 の凍結値 (変更は R1 — lot-ladder-template-2026-08.md §0) ──
RUNGS = [1000, 5000, 10000, 30000]
LEVERAGE = 25                        # OANDA Japan 個人 25x
MARGIN_CAP_PCT = 0.40                # §4.4 worst-case 同時証拠金 ≤ 40% NAV
CELL_EVENT_LOSS_CAP_PCT = 0.025      # §4.2 worst-case 1 イベント損失 ≤ 2.5% NAV
CELL_DD_BUDGET_PCT = 0.02            # §4.3 / §5 MC のセル DD 予算 (2% NAV)
MC_RUIN_PROB_MAX = 0.05              # §5 MC gate: P(DD>予算) ≤ 5%
MAX_CURRENCY_EXPOSURE = 20_000       # §4.5 modules/exposure_manager.py の実装値
MC_HORIZON_MONTHS = 12
Z95 = 1.959963984540054


def wilson_lower(p: float, n: int, z: float = Z95) -> float:
    """Wilson score interval lower bound for a proportion."""
    if n <= 0 or p < 0 or p > 1:
        return 0.0
    denom = 1 + z * z / n
    center = p + z * z / (2 * n)
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n)
    return max(0.0, (center - margin) / denom)


def bev_wr(avg_win: float, avg_loss: float) -> float:
    """Break-even win rate for frozen payoffs (§3.3)."""
    if avg_win + avg_loss <= 0:
        return 1.0
    return avg_loss / (avg_win + avg_loss)


def ev_wilson_lower(wr: float, n: int, avg_win: float, avg_loss: float) -> float:
    """EV lower bound: Wilson_lo(WR) applied to frozen payoffs (§3.3)."""
    lo = wilson_lower(wr, n)
    return lo * avg_win - (1 - lo) * avg_loss


def ev_normal_lower(mean: float, sigma: float, n: int, z: float = Z95) -> float:
    """Diagnostic-only normal lower bound on mean pips (§3.3 — not a gate)."""
    if n <= 0:
        return float("-inf")
    return mean - z * sigma / math.sqrt(n)


def n_required_for_gate(wr: float, avg_win: float, avg_loss: float,
                        n_max: int = 10_000) -> Optional[int]:
    """Smallest N where Wilson_lo(WR) > BEV_WR, assuming stats persist (§3.4).

    Returns None if the gate never opens by n_max (point WR <= BEV_WR).
    """
    target = bev_wr(avg_win, avg_loss)
    if wr <= target:
        return None
    for n in range(5, n_max + 1):
        if wilson_lower(wr, n) > target:
            return n
    return None


def jpy_per_pip_per_1000u(pair: str, usdjpy: Optional[float] = None,
                          explicit: Optional[float] = None) -> float:
    """JPY value of 1 pip on 1000 units (v in the template).

    JPY-quote pairs: pip=0.01 JPY/unit → 10 JPY. USD-quote pairs: pip=0.0001
    USD/unit → 0.1 USD → ×USD/JPY. Other quotes require --jpy-per-pip.
    """
    if explicit is not None:
        return float(explicit)
    quote = pair.split("_")[1]
    if quote == "JPY":
        return 10.0
    if quote == "USD":
        if not usdjpy:
            raise ValueError(f"{pair}: USD-quote pair needs --usdjpy for conversion")
        return 0.1 * usdjpy
    raise ValueError(f"{pair}: unsupported quote {quote} — pass --jpy-per-pip")


def margin_jpy_per_1000u(pair: str, price: float,
                         usdjpy: Optional[float] = None,
                         leverage: int = LEVERAGE) -> float:
    """Required margin (JPY) per 1000 units at `leverage`.

    Notional = 1000 units of base currency valued in JPY.
    JPY-quote: 1000×price. USD-quote (e.g. EUR_USD): 1000×price×USD/JPY.
    """
    quote = pair.split("_")[1]
    if quote == "JPY":
        notional = 1000.0 * price
    elif quote == "USD":
        if not usdjpy:
            raise ValueError(f"{pair}: USD-quote pair needs --usdjpy")
        notional = 1000.0 * price * usdjpy
    else:
        raise ValueError(f"{pair}: unsupported quote {quote}")
    return notional / leverage


def unit_ceilings(nav: float, wr: float, avg_win: float, avg_loss: float,
                  disaster_sl_pips: float, v1000: float,
                  margin_1000: float, max_concurrent: int = 1) -> dict:
    """All §4 unit ceilings + which one binds. Units rounded down to 1000."""
    k = kelly_fraction(wr, avg_win, avg_loss)
    f = k["half_kelly"]
    ceilings = {}
    ceilings["U_avg"] = (f * nav / (avg_loss * v1000) * 1000
                         if avg_loss > 0 and f > 0 else 0.0)
    ceilings["U_dis"] = (f * nav / (disaster_sl_pips * v1000) * 1000
                         if disaster_sl_pips > 0 and f > 0 else 0.0)
    ceilings["U_cellDD"] = (CELL_EVENT_LOSS_CAP_PCT * nav
                            / (disaster_sl_pips * v1000) * 1000
                            if disaster_sl_pips > 0 else float("inf"))
    ceilings["U_margin"] = (MARGIN_CAP_PCT * nav / (margin_1000 * max_concurrent)
                            * 1000 if margin_1000 > 0 else float("inf"))
    ceilings["U_exposure"] = MAX_CURRENCY_EXPOSURE / max(1, max_concurrent)
    floored = {name: (math.floor(u / 1000) * 1000 if math.isfinite(u) else u)
               for name, u in ceilings.items()}
    binding = min(floored, key=lambda name: floored[name])
    return {
        "kelly": k,
        "ceilings": floored,
        "binding": binding,
        "max_units": floored[binding],
    }


def next_rung(current_rung: int) -> Optional[int]:
    """One step up the standard ladder; None at the top (§1: 飛び級禁止)."""
    if current_rung not in RUNGS:
        raise ValueError(f"current_rung {current_rung} not in standard rungs {RUNGS}")
    idx = RUNGS.index(current_rung)
    return RUNGS[idx + 1] if idx + 1 < len(RUNGS) else None


def demote_rung(current_rung: int) -> int:
    """One step down (§6 — floor at base rung, never below)."""
    if current_rung not in RUNGS:
        raise ValueError(f"current_rung {current_rung} not in standard rungs {RUNGS}")
    idx = RUNGS.index(current_rung)
    return RUNGS[max(0, idx - 1)]


def mc_cell_dd_check(pnl_pips: List[float], units: int, nav: float,
                     v1000: float, events_per_month: float,
                     months: int = MC_HORIZON_MONTHS) -> dict:
    """§5 MC gate: P(cell DD > CELL_DD_BUDGET_PCT×NAV over `months`) via
    production monte_carlo_ruin on the JPY-converted live pnl series."""
    n_fwd = max(1, int(round(events_per_month * months)))
    pnl_jpy = [p * v1000 * units / 1000.0 for p in pnl_pips]
    res = monte_carlo_ruin(pnl_jpy, initial_capital=nav,
                           ruin_dd_pct=CELL_DD_BUDGET_PCT,
                           n_trades_forward=n_fwd)
    res["gate_pass"] = (not res.get("insufficient", True)
                        and res["ruin_probability"] <= MC_RUIN_PROB_MAX)
    return res


def evaluate(*, nav: float, pair: str, price: float, n: int, mean: float,
             sigma: float, wr: float, avg_win: float, avg_loss: float,
             disaster_sl_pips: float, events_per_month: float,
             current_rung: int, max_concurrent: int = 1,
             usdjpy: Optional[float] = None,
             jpy_per_pip: Optional[float] = None,
             pnl_pips: Optional[List[float]] = None) -> dict:
    """Full §3-§5 evaluation for one cell. Returns packet-ready dict."""
    if pair.split("_")[1] == "JPY":
        usdjpy_eff = usdjpy
    else:
        usdjpy_eff = usdjpy if usdjpy else (price if pair == "USD_JPY" else None)
    v1000 = jpy_per_pip_per_1000u(pair, usdjpy=usdjpy_eff, explicit=jpy_per_pip)
    margin_1000 = margin_jpy_per_1000u(pair, price, usdjpy=usdjpy_eff)

    target = next_rung(current_rung)
    ceil = unit_ceilings(nav, wr, avg_win, avg_loss, disaster_sl_pips,
                         v1000, margin_1000, max_concurrent)

    bev = bev_wr(avg_win, avg_loss)
    w_lo = wilson_lower(wr, n)
    ev_lo = ev_wilson_lower(wr, n, avg_win, avg_loss)
    wilson_gate = w_lo > bev
    n_req = n_required_for_gate(wr, avg_win, avg_loss)

    mc = None
    if target is not None and pnl_pips:
        mc = mc_cell_dd_check(pnl_pips, target, nav, v1000, events_per_month)

    recommended = None
    verdict = "HOLD"
    reasons = []
    if target is None:
        reasons.append(f"already at top rung {current_rung}u")
    else:
        if not wilson_gate:
            reasons.append(
                f"Wilson gate FAIL: Wilson_lo(WR)={w_lo:.4f} <= BEV_WR={bev:.4f}"
                + (f" (N_required≈{n_req})" if n_req else " (point WR <= BEV)"))
        if target > ceil["max_units"]:
            reasons.append(
                f"target {target}u > binding ceiling {ceil['binding']}"
                f"={ceil['max_units']}u")
        if mc is not None and not mc["gate_pass"]:
            reasons.append(
                f"MC gate FAIL: P(DD>{CELL_DD_BUDGET_PCT:.0%} NAV)"
                f"={mc['ruin_probability']:.1%} > {MC_RUIN_PROB_MAX:.0%}")
        if not reasons:
            recommended = target
            verdict = "PROPOSE"

    # counterfactual (§8.4)
    counterfactual = None
    if target is not None:
        delta_u = target - current_rung
        opp_jpy = delta_u / 1000.0 * v1000 * mean * events_per_month
        wc_now = disaster_sl_pips * v1000 * current_rung / 1000.0
        wc_next = disaster_sl_pips * v1000 * target / 1000.0
        counterfactual = {
            "opportunity_jpy_per_month": round(opp_jpy, 1),
            "opportunity_pct_nav_per_month": round(opp_jpy / nav * 100, 3),
            "worst_case_event_jpy_current": round(wc_now, 0),
            "worst_case_event_jpy_target": round(wc_next, 0),
            "worst_case_event_pct_nav_target": round(wc_next / nav * 100, 2),
        }

    return {
        "pair": pair,
        "nav": nav,
        "v1000_jpy_per_pip": round(v1000, 3),
        "margin_jpy_per_1000u": round(margin_1000, 1),
        "current_rung": current_rung,
        "target_rung": target,
        "verdict": verdict,
        "hold_reasons": reasons,
        "recommended_units": recommended,
        "wilson": {
            "wilson_lo_wr": round(w_lo, 4),
            "bev_wr": round(bev, 4),
            "gate_pass": wilson_gate,
            "ev_wilson_lower_pips": round(ev_lo, 3),
            "ev_normal_lower_pips_diagnostic": round(
                ev_normal_lower(mean, sigma, n), 3),
            "n_required": n_req,
        },
        "kelly": ceil["kelly"],
        "ceilings": ceil["ceilings"],
        "binding_constraint": ceil["binding"],
        "max_units_all_constraints": ceil["max_units"],
        "mc": mc,
        "counterfactual": counterfactual,
    }


def render_packet(result: dict, cell_id: str = "{cell_id}",
                  strategy: str = "{strategy}", date: str = "{date}") -> str:
    """Render the §8 one-page R1 packet skeleton with computed numbers."""
    r = result
    cur, tgt = r["current_rung"], r["target_rung"]
    w = r["wilson"]
    lines = [
        f"# ロット階段 R1 パケット — {cell_id} {cur}u→{tgt}u ({date})",
        "",
        "## 1. 遷移",
        f"{strategy}×{r['pair']} : {cur}u → {tgt}u "
        "(rule:R1、テンプレ [[lot-ladder-template-2026-08]] 準拠)",
        "",
        "## 2. 凍結根拠数値 (live 実績 — oanda_trade_id != '' のみ)",
        "(N累積 / N at-rung / mean / σ / WR / avg_win / avg_loss / disaster / "
        "slippage を DB から転記)",
        "",
        "## 3. ゲート判定 (tools/lot_ladder_calc.py 出力)",
        f"- Wilson_lo(WR) = {w['wilson_lo_wr']} vs BEV_WR = {w['bev_wr']} → "
        + ("PASS" if w["gate_pass"]
           else "FAIL (N_required≈{})".format(w["n_required"])),
        f"- EV 下限 (Wilson): {w['ev_wilson_lower_pips']}p / "
        f"diagnostic normal 下限: {w['ev_normal_lower_pips_diagnostic']}p",
        f"- Kelly: half={r['kelly']['half_kelly']} → ceilings {r['ceilings']}",
        f"- **binding constraint = {r['binding_constraint']} "
        f"({r['max_units_all_constraints']}u)**",
        f"- verdict: **{r['verdict']}**"
        + (f" — {'; '.join(r['hold_reasons'])}" if r["hold_reasons"] else ""),
    ]
    if r.get("mc"):
        lines.append(
            f"- MC: P(セル DD>{CELL_DD_BUDGET_PCT:.0%} NAV, "
            f"{MC_HORIZON_MONTHS}mo) = {r['mc']['ruin_probability']:.1%} → "
            f"{'PASS' if r['mc']['gate_pass'] else 'FAIL'}")
    cf = r.get("counterfactual")
    if cf:
        lines += [
            "",
            "## 4. counterfactual",
            f"- 機会費用: +{cf['opportunity_jpy_per_month']} JPY/月 "
            f"(+{cf['opportunity_pct_nav_per_month']}% NAV)",
            f"- 追加 tail: worst-case イベント損失 "
            f"{cf['worst_case_event_jpy_current']:.0f} → "
            f"{cf['worst_case_event_jpy_target']:.0f} JPY "
            f"({cf['worst_case_event_pct_nav_target']}% NAV)",
        ]
    lines += [
        "",
        "## 5. 停止条件 (R2 自動 — テンプレ §6 instantiated)",
        f"D1 slippage>+2.0p→{cur}u / D2 at-rung N12<−60p→{cur}u / "
        f"D3 disaster 1発→{cur}u・2発→{RUNGS[0]}u / D4 合成DD 4/6/8% NAV / "
        "D5 Wilson gate 割れ→凍結",
        f"latch kv: `LOT_LADDER_{cell_id}_DEMOTED` (再武装経路なし、解除は R1)",
        "",
        "## 6. rollback",
        f"kv 削除 1 操作で {cur}u へ復帰。shadow 蓄積は不変",
        "",
        "## 7. 動機記録",
        "データ駆動 (ゲート全通過) / 感情起因でないことの確認:",
        "",
        "## 8. 参照",
        "戦略カード / OOS verdict / [[lot-ladder-template-2026-08]] / JPY 台帳感応度更新",
        "",
        "## 9. user 承認 (SLA 48h)",
        "[ ] 承認 / [ ] 却下 / [ ] 保留 — 日付・条件:",
    ]
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    import argparse
    import json

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--nav", type=float, required=True, help="実 NAV (JPY)")
    ap.add_argument("--pair", required=True)
    ap.add_argument("--price", type=float, required=True)
    ap.add_argument("--usdjpy", type=float, default=None,
                    help="USD-quote ペアの JPY 換算レート")
    ap.add_argument("--jpy-per-pip", type=float, default=None,
                    help="1000u あたり JPY/pip の明示指定 (特殊 quote 用)")
    ap.add_argument("--n", type=int, required=True, help="live 累積 N")
    ap.add_argument("--mean", type=float, required=True, help="stressed-net pips")
    ap.add_argument("--sigma", type=float, required=True)
    ap.add_argument("--wr", type=float, required=True)
    ap.add_argument("--avg-win", type=float, required=True)
    ap.add_argument("--avg-loss", type=float, required=True)
    ap.add_argument("--disaster-sl", type=float, required=True)
    ap.add_argument("--events-per-month", type=float, required=True)
    ap.add_argument("--current-rung", type=int, default=1000)
    ap.add_argument("--max-concurrent", type=int, default=1)
    ap.add_argument("--pnl-file", default=None,
                    help="live pnl pips 系列 (1 行 1 値) — MC gate 用")
    ap.add_argument("--packet", action="store_true",
                    help="§8 パケット markdown を出力")
    ap.add_argument("--cell-id", default="{cell_id}")
    ap.add_argument("--strategy", default="{strategy}")
    ap.add_argument("--date", default="{date}")
    args = ap.parse_args(argv)

    pnl = None
    if args.pnl_file:
        pnl = [float(line) for line in Path(args.pnl_file).read_text().split()
               if line.strip()]

    result = evaluate(
        nav=args.nav, pair=args.pair, price=args.price, n=args.n,
        mean=args.mean, sigma=args.sigma, wr=args.wr, avg_win=args.avg_win,
        avg_loss=args.avg_loss, disaster_sl_pips=args.disaster_sl,
        events_per_month=args.events_per_month,
        current_rung=args.current_rung, max_concurrent=args.max_concurrent,
        usdjpy=args.usdjpy, jpy_per_pip=args.jpy_per_pip, pnl_pips=pnl,
    )
    if args.packet:
        print(render_packet(result, cell_id=args.cell_id,
                            strategy=args.strategy, date=args.date))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
