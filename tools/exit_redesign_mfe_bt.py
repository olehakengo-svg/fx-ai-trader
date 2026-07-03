#!/usr/bin/env python3
"""Exit-redesign MFE BT: trailing ON vs OFF for +EV candidates (vix_carry/mqe/wick/donchian/dt_bb_rsi).
Path-ordered (real bar replay) validation of the breakeven-trail counterfactual from
.ai/runs/20260608-cell-edge-deep-audit/final.md
Usage: BT_MODE=1 NO_AUTOSTART=1 python3 tools/exit_redesign_mfe_bt.py
"""
import os, sys, time, json
os.environ["BT_MODE"]="1"; os.environ["NO_AUTOSTART"]="1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import math
t0=time.time(); import app; print(f"import app {time.time()-t0:.0f}s", file=sys.stderr)

TARGETS = ["vix_carry_unwind","mqe_gbpusd_fix","wick_imbalance_reversion",
           "donchian_momentum_breakout","dt_bb_rsi_mr"]
PAIRS = sys.argv[1:] or ["USDJPY=X","GBPUSD=X","EURUSD=X"]
# config: name -> env overrides (besides BT_MODE/NO_AUTOSTART)
CONFIGS = {
    "trailOFF": {"BT_OPTIMISTIC":"1","BT_ABLATE_BE_TRAIL":"1"},  # optimistic, NO be/trail
    "trailON":  {"BT_OPTIMISTIC":"1","BT_ABLATE_BE_TRAIL":"0"},  # optimistic, WITH be/trail
}

def stats(trs):
    pnls=[t.get("pnl_pips",t.get("pnl",0)) for t in trs]
    pnls=[p for p in pnls if isinstance(p,(int,float))]
    n=len(pnls)
    if not n: return None
    nw=sum(1 for t in trs if t.get("outcome")=="WIN"); nl=sum(1 for t in trs if t.get("outcome")=="LOSS")
    dec=nw+nl; wr=nw/dec if dec else 0; ev=sum(pnls)/n
    gw=sum(p for p in pnls if p>0); gl=abs(sum(p for p in pnls if p<0))
    pf=gw/gl if gl>0 else float('inf')
    return dict(n=n,wr=wr,ev=ev,pnl=sum(pnls),pf=pf)

out={}
for cfg,env in CONFIGS.items():
    for k,v in env.items(): os.environ[k]=v
    for sym in PAIRS:
        app._dt_bt_cache.clear()
        t1=time.time()
        try:
            res=app.run_daytrade_backtest(sym, lookback_days=365, interval="15m")
        except Exception as e:
            print(f"  {cfg} {sym} FAIL {e}", file=sys.stderr); continue
        tl=res.get("trade_log",[]) or []
        print(f"  {cfg} {sym}: {len(tl)} trades {time.time()-t1:.0f}s", file=sys.stderr)
        for strat in TARGETS:
            sub=[t for t in tl if t.get("entry_type")==strat]
            s=stats(sub)
            if s: out[(cfg,sym,strat)]=s
    for k in env: os.environ.pop(k,None)

# print comparison
print("\n\n### EXIT-REDESIGN BT: trailing OFF vs ON (BT_OPTIMISTIC=1, 365d MASSIVE) ###\n")
print(f"{'strategy|pair':40}{'cfg':9}{'N':>5}{'WR%':>6}{'EV':>8}{'PnL':>9}{'PF':>6}")
seen=set()
for (cfg,sym,strat),s in sorted(out.items(), key=lambda x:(x[0][2],x[0][1],x[0][0])):
    pf="inf" if s["pf"]==float('inf') else f"{s['pf']:.2f}"
    print(f"{(strat+'|'+sym):40}{cfg:9}{s['n']:>5}{s['wr']*100:>6.1f}{s['ev']:>+8.2f}{s['pnl']:>+9.1f}{pf:>6}")
# delta
print("\n### EV delta (trailON - trailOFF) ###")
for strat in TARGETS:
    for sym in PAIRS:
        a=out.get(("trailOFF",sym,strat)); b=out.get(("trailON",sym,strat))
        if a and b and a["n"]>=20:
            print(f"  {strat+'|'+sym:40} EV {a['ev']:+.2f} -> {b['ev']:+.2f}  (Δ{b['ev']-a['ev']:+.2f}, N={a['n']}/{b['n']}, PnL {a['pnl']:+.0f}->{b['pnl']:+.0f})")
json.dump({f"{c}|{s}|{t}":v for (c,s,t),v in out.items()},
          open(".ai/runs/20260608-cell-edge-deep-audit/exit_redesign_bt.json","w"), indent=2)
print("\nWROTE exit_redesign_bt.json")
