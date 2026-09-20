# 純算数 (価格/DB 非接触)。Wilson は tools/lot_ladder_calc.py と同式を転記。
import math
from statistics import NormalDist
N01=NormalDist()
Z=1.959963984540054
def wilson_lower(p,n,z=Z):
    d=1+z*z/n; c=p+z*z/(2*n); m=z*math.sqrt((p*(1-p)+z*z/(4*n))/n); return max(0,(c-m)/d)
def n_req(wr,aw,al):
    t=al/(aw+al)
    if wr<=t: return None
    for n in range(5,10001):
        if wilson_lower(wr,n)>t: return n
def payoff_from_drift(k):  # normal drift mu=k*sigma, time-exit → WR, avgW/σ, avgL/σ
    wr=N01.cdf(k); phi=N01.pdf(k)
    aw=k+phi/wr; al=-k+phi/(1-wr); return wr,aw,al
NAV=275517; KEEPER=2080; M2=0.005*NAV
print(f"M2 net ¥{M2:.0f}; gross incl keeper ¥{M2+KEEPER:.0f} = {(M2+KEEPER)/NAV*100:.3f}%/月")
# σ_5d from Gate A median|fwd5| (pips): median = 0.6745σ
sig={'EUR_USD':71.45/0.6745,'GBP_USD':95.0/0.6745,'USD_JPY':81.85/0.6745}
print("σ_5d pips:",{k:round(v) for k,v in sig.items()})
# MDE check: 2.485*σ/sqrt(N)*1.2 with σ in bp
for s in (90,110,130):
    print(f"MDE bp @N=300 σ={s}bp: {2.485*s/math.sqrt(300)*1.2:.1f}")
print("\nμ/σ → WR, payoff, N_required(Wilson gate), USD_JPY pips/event")
for k in (0.10,0.124,0.15,0.17,0.20,0.235,0.30):
    wr,aw,al=payoff_from_drift(k)
    nr=n_req(wr,aw,al)
    print(f"k={k:.3f} WR={wr:.3f} payoff={aw/al:.3f} BEV={al/(aw+al):.3f} N_req={nr} | USDJPY mean={k*sig['USD_JPY']:.1f}p")
# proposal's template: WR55/payoff1.5
print("template WR55/payoff1.5 N_req=",n_req(0.55,1.5,1.0))
# events per month
print("\nevents/月: G4=",32/12, " 7CB(8+8+8+8+8+8+7)=",55/12)
# months to N
import datetime as dt
start=dt.date(2026,12,15)
def add_m(d,m):
    y=d.year+int((d.month-1+m)//12); mo=int((d.month-1+m)%12)+1; return dt.date(y,mo,1)
for N in (30,41,76,93,110):
    for epm in (2.67,3.7,4.58,5.0):
        print(f"N={N} @{epm}/月 → {N/epm:.1f} 月 → {add_m(start,math.ceil(N/epm))}")
# constraint 4.2 at L1
cap=0.025*NAV
print(f"\n4.2 cap = ¥{cap:.0f}; L1 5000u JPY pair max SL={cap/50:.0f}p; USD-quote (¥75/pip) max SL={cap/75:.0f}p; wg 150p×¥50=¥7500 →", "違反" if 7500>cap else "OK")
for sl,v in ((150,10),(200,10),(150,15),(200,15)):
    print(f"  SL={sl}p v={v} → L1 需要 NAV ≥ ¥{5*sl*v/0.025:,.0f}")
# floor clock
margin=NAV-262000
for burn,label in ((2080,'keeper only'),(2080+200,'keeper+edge drift −0.075%'),(2080-690,'keeper − #29 L0 optimistic ¥690'),(2080+200-690,'all three')):
    print(f"floor: {label}: {margin/burn:.1f} 月 → {add_m(dt.date(2026,9,20),math.ceil(margin/burn))}")
# #29 contributions
for units,v_jpy in ((1000,10),(5000,50)):
    for pips in (10,15,25):
        for epm in (2.67,4.58):
            jpy=pips*v_jpy*epm
            print(f"{units}u {pips}p×{epm}/月 → ¥{jpy:,.0f}/月 = {jpy/NAV*100:.2f}% (net of keeper {(jpy-KEEPER)/NAV*100:+.2f}%)")
# required pips/event for M2 gross incl keeper
for units,v in ((1000,10),(5000,50)):
    for epm in (2.67,4.58):
        print(f"M2 gross incl keeper @ {units}u, {epm}/月 → {(M2+KEEPER)/v/epm:.1f} p/event")
# P(M2≤2027) increment
for ppass in (0.04,0.08,0.12):
    for pcond in (0.10,0.2,0.5):
        print(f"P(PASS)={ppass} P(M2≤2027|PASS)={pcond} → +{ppass*pcond*100:.1f}pp")
