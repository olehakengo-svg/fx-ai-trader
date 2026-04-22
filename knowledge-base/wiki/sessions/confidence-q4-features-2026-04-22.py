"""What features distinguish Q4 trades from Q2+Q3 in the 4 inverted strategies?

For each inverted strategy, compute LR = P(feature | Q4) / P(feature | Q2+Q3)
for key features (ADX q, ATR q, CVEMA q, session, direction). High LR means
that feature is over-represented in Q4 vs mid-conf — i.e., it's what's
pushing confidence to Q4. If the same feature also has low WIN rate in that
strategy, we have the smoking gun.
"""
import json
from collections import defaultdict

with open("/tmp/shadow_trades.json") as f:
    data = json.load(f)
trades = [t for t in data.get("trades", [])
          if t.get("is_shadow") == 1
          and t.get("outcome") in ("WIN", "LOSS")
          and t.get("instrument") != "XAU_USD"]

CONF_EDGES = [53.0, 61.0, 69.0]
ADX_EDGES = [20.3, 25.3, 31.7]
ATR_EDGES = [0.95, 1.01, 1.09]
CVEMA_EDGES = [-0.019, 0.001, 0.034]

def q(v, edges):
    if v is None: return None
    try: v = float(v)
    except: return None
    if v <= edges[0]: return "Q1"
    if v <= edges[1]: return "Q2"
    if v <= edges[2]: return "Q3"
    return "Q4"

def parse_regime(s):
    if isinstance(s, dict): return s
    if isinstance(s, str) and s.startswith("{"):
        try: return json.loads(s)
        except: return {}
    return {}

def session_of(hour):
    if hour is None: return None
    if 0 <= hour < 8: return "tokyo"
    if 8 <= hour < 13: return "london"
    if 13 <= hour < 22: return "ny"
    return "offhours"

from datetime import datetime, timezone
def parse_dt(s):
    if not s: return None
    try: return datetime.fromisoformat(s.replace("Z","+00:00")).astimezone(timezone.utc)
    except: return None

# Enrich & bucket
enriched = []
for t in trades:
    rd = parse_regime(t.get("regime",""))
    cq = q(t.get("confidence"), CONF_EDGES)
    if cq is None: continue
    dt = parse_dt(t.get("entry_time",""))
    enr = {
        "et": t.get("entry_type",""),
        "outcome": t.get("outcome"),
        "direction": str(t.get("direction","")).upper(),
        "regime": rd.get("regime","UNK"),
        "_conf_q": cq,
        "_adx_q": q(rd.get("adx"), ADX_EDGES),
        "_atr_q": q(rd.get("atr_ratio"), ATR_EDGES),
        "_cvema_q": q(rd.get("close_vs_ema200"), CVEMA_EDGES),
        "session": session_of(dt.hour if dt else None),
        "hour": dt.hour if dt else None,
        "ema_bull": rd.get("ema_stack_bull", False),
        "ema_bear": rd.get("ema_stack_bear", False),
    }
    enriched.append(enr)

TARGET = ["ema_trend_scalp", "fib_reversal", "ema_cross", "bb_rsi_reversion"]

for strat in TARGET:
    rows = [e for e in enriched if e["et"] == strat]
    q4 = [e for e in rows if e["_conf_q"] == "Q4"]
    q23 = [e for e in rows if e["_conf_q"] in ("Q2","Q3")]
    if len(q4) < 15 or len(q23) < 15: continue
    n4, n23 = len(q4), len(q23)
    wr4 = sum(1 for e in q4 if e["outcome"]=="WIN")/n4*100
    wr23 = sum(1 for e in q23 if e["outcome"]=="WIN")/n23*100
    print("="*90)
    print(f"### {strat}   Q4 N={n4} WR={wr4:.1f}%   vs Q2+Q3 N={n23} WR={wr23:.1f}%   Δ={wr4-wr23:+.1f}pp")
    print("="*90)

    # Check each feature: LR = P(value|Q4) / P(value|Q23)
    features = {
        "direction":  ["BUY","SELL"],
        "regime":     ["TREND_BULL","TREND_BEAR","RANGE","HIGH_VOL"],
        "session":    ["tokyo","london","ny","offhours"],
        "_adx_q":     ["Q1","Q2","Q3","Q4"],
        "_atr_q":     ["Q1","Q2","Q3","Q4"],
        "_cvema_q":   ["Q1","Q2","Q3","Q4"],
    }
    print(f"{'feat':<12} {'value':<12} {'Q4 P':>7} {'Q23 P':>7} {'LR(Q4/Q23)':>12}  {'Q4 WR':>7}")
    print("-"*90)
    for feat, values in features.items():
        for v in values:
            c4 = sum(1 for e in q4 if e.get(feat)==v)
            c23 = sum(1 for e in q23 if e.get(feat)==v)
            p4 = c4/n4
            p23 = c23/n23
            lr = p4/p23 if p23 > 0 else (float("inf") if p4 > 0 else 0)
            # WR in this Q4 × feat-value cell
            sub4 = [e for e in q4 if e.get(feat)==v]
            wr_cell = (sum(1 for e in sub4 if e["outcome"]=="WIN")/len(sub4)*100) if sub4 else 0
            if p4 < 0.05 and p23 < 0.05: continue  # skip rare
            mark = ""
            if lr >= 1.5 and wr_cell + 8 < wr23: mark = "★ Q4-enriched + WR-drop"
            elif lr >= 1.5: mark = "Q4-enriched"
            if mark or abs(lr-1) > 0.3:
                lr_str = f"{lr:.2f}" if lr != float("inf") else "inf"
                print(f"{feat:<12} {v:<12} {p4:>6.1%} {p23:>6.1%} {lr_str:>12}  {wr_cell:>6.1f}%  {mark}")
    print()
