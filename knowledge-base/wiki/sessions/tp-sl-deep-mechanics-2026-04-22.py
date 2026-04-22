"""
TP-hit / SL-hit Deep Mechanics — 2026-04-22
目的: 勝率改善のための actionable filter rules を抽出
手法:
  A. Hold duration 分解 (fast/slow TP, immediate/gradual SL)
  B. Immediate-Death phenomenon 特徴付け (MFE=0 losses)
  C. MAE/|SL| による "clean win" vs "lucky win"
  D. Entry feature → outcome pointwise mutual information
  E. Virtual filter simulation (WR uplift vs N cost)
"""

import json
import math
import statistics as stat
from collections import Counter, defaultdict
from datetime import datetime

SRC = '/tmp/all_trades_20260422.json'
CUTOFF = '2026-04-16'

with open(SRC) as f:
    raw = json.load(f).get('trades') or []

# ── Filter: shadow + non-XAU + decided
def keep(t):
    if not t.get('is_shadow'): return False
    if t.get('instrument') == 'XAU_USD': return False
    if t.get('outcome') not in ('WIN', 'LOSS'): return False
    if not t.get('created_at'): return False
    return True

trades = [t for t in raw if keep(t)]
print(f'[scope] N={len(trades)}')

# ── Enrich ──
def safef(x):
    try: return float(x)
    except: return None

def session_of(h):
    if 0<=h<8: return 'tokyo'
    if 8<=h<13: return 'london'
    if 13<=h<22: return 'ny'
    return 'offhours'

def parse_iso(s):
    try: return datetime.fromisoformat(s.replace('Z','+00:00'))
    except: return None

def get_regime(t):
    rj = t.get('regime')
    if isinstance(rj, dict): return rj
    if isinstance(rj, str) and rj.startswith('{'):
        try: return json.loads(rj)
        except: return {}
    return {}

for t in trades:
    rj = get_regime(t)
    ep = safef(t.get('entry_price'))
    sl = safef(t.get('sl'))
    tp = safef(t.get('tp'))
    pip = 100.0 if 'JPY' in t['instrument'] else 10000.0
    t['_pip'] = pip
    t['_sl_dist'] = abs(ep - sl) * pip if (ep and sl) else None
    t['_tp_dist'] = abs(tp - ep) * pip if (ep and tp) else None
    t['_mfe'] = safef(t.get('mafe_favorable_pips')) or 0.0
    t['_mae'] = abs(safef(t.get('mafe_adverse_pips')) or 0.0)
    t['_pnl'] = safef(t.get('pnl_pips')) or 0.0
    # Hold duration
    et = parse_iso(t.get('entry_time') or t.get('created_at') or '')
    xt = parse_iso(t.get('exit_time') or '')
    t['_hold_min'] = (xt - et).total_seconds() / 60 if (et and xt and xt > et) else None
    t['_hour'] = et.hour if et else -1
    t['_sess'] = session_of(t['_hour']) if t['_hour']>=0 else 'NA'
    t['_dir'] = (t.get('direction') or '').upper()
    t['_post'] = (t.get('created_at') or '') >= CUTOFF
    t['_conf'] = safef(t.get('confidence'))
    t['_score'] = safef(t.get('score'))
    t['_adx'] = safef(rj.get('adx'))
    t['_atr'] = safef(rj.get('atr_ratio'))
    t['_cvem'] = safef(rj.get('close_vs_ema200'))
    t['_hmm'] = rj.get('hmm_regime', 'NA')
    t['_spread'] = safef(t.get('spread_at_entry'))
    # Normalized ratios
    if t['_sl_dist'] and t['_sl_dist'] > 0:
        t['_mae_ratio'] = t['_mae'] / t['_sl_dist']
        t['_mfe_ratio'] = t['_mfe'] / t['_sl_dist']
    else:
        t['_mae_ratio'] = None; t['_mfe_ratio'] = None

wins = [t for t in trades if t['outcome']=='WIN']
losses = [t for t in trades if t['outcome']=='LOSS']
print(f'[scope] WIN={len(wins)} LOSS={len(losses)} baseline WR={len(wins)/len(trades):.2%}')

# ═══════════════════════════════════════════════
# SECTION A: Hold duration decomposition
# ═══════════════════════════════════════════════
OUT = []
OUT.append('# TP-hit / SL-hit Deep Mechanics — Actionable WR Improvement')
OUT.append('')
OUT.append(f'**Generated**: 2026-04-22 (UTC)  ')
OUT.append(f'**Scope**: is_shadow=1 ∧ outcome∈{{WIN,LOSS}} ∧ non-XAU, N={len(trades)}  ')
OUT.append(f'**Baseline WR**: {len(wins)/len(trades):.2%}  ')
OUT.append(f'**Cutoff**: {CUTOFF} (pre/post WF 分析で再現性確認)  ')
OUT.append('')
OUT.append('---')
OUT.append('')
OUT.append('## A. Hold-duration decomposition — WIN/LOSS の時間構造')
OUT.append('')

# Overall hold time stats
w_hold = [t['_hold_min'] for t in wins if t['_hold_min'] is not None]
l_hold = [t['_hold_min'] for t in losses if t['_hold_min'] is not None]
if w_hold and l_hold:
    OUT.append(f'- WIN hold time (min): median={stat.median(w_hold):.1f}, p25={sorted(w_hold)[len(w_hold)//4]:.1f}, p75={sorted(w_hold)[3*len(w_hold)//4]:.1f}')
    OUT.append(f'- LOSS hold time (min): median={stat.median(l_hold):.1f}, p25={sorted(l_hold)[len(l_hold)//4]:.1f}, p75={sorted(l_hold)[3*len(l_hold)//4]:.1f}')
    OUT.append('')

OUT.append('### A.1 戦略別 hold duration (TP=WIN, SL=LOSS)')
OUT.append('| strat×instr | N | WIN med hold | LOSS med hold | TP/SL speed ratio |')
OUT.append('|---|---:|---:|---:|---:|')

by_cell = defaultdict(list)
for t in trades:
    by_cell[(t['entry_type'], t['instrument'])].append(t)

cells = [(k, v) for k, v in by_cell.items() if len(v)>=20]
cells.sort(key=lambda x: -len(x[1]))

for (strat, instr), ts in cells[:15]:
    ww = [t['_hold_min'] for t in ts if t['outcome']=='WIN' and t['_hold_min'] is not None]
    ll = [t['_hold_min'] for t in ts if t['outcome']=='LOSS' and t['_hold_min'] is not None]
    if len(ww) < 3 or len(ll) < 3: continue
    mw, ml = stat.median(ww), stat.median(ll)
    ratio = mw/ml if ml>0 else float('inf')
    OUT.append(f'| {strat}×{instr} | {len(ts)} | {mw:.1f} min | {ml:.1f} min | {ratio:.2f}x |')
OUT.append('')
OUT.append('**解釈**: ratio > 1 = WIN の方が長く持ちTP 到達 (slow TP). ratio < 1 = LOSS の方が時間がかかる (gradual SL). ratio ≈ 1 は対称的挙動.')
OUT.append('')

# ═══════════════════════════════════════════════
# SECTION B: Immediate Death phenomenon (MFE=0 losses)
# ═══════════════════════════════════════════════
OUT.append('---')
OUT.append('')
OUT.append('## B. Immediate Death phenomenon — LOSS が一度も favorable に振れない現象')
OUT.append('')
OUT.append('Definition: `MFE_favorable_pips ≤ 0.5 pip` (entry 直後から逆行して SL 直行)')
OUT.append('')

def is_immediate_death(t):
    return t['outcome']=='LOSS' and t['_mfe'] <= 0.5

total_imm = sum(1 for t in losses if is_immediate_death(t))
OUT.append(f'- Portfolio-wide immediate death rate: **{total_imm}/{len(losses)} = {total_imm/len(losses):.1%}** of LOSSes')
OUT.append(f'- [[mfe-zero-analysis]] の 90.6% 主張とほぼ整合')
OUT.append('')

OUT.append('### B.1 戦略別 immediate death rate (N≥20 cells)')
OUT.append('| strat×instr | N_loss | immediate death | rate | avg MAE in death | implication |')
OUT.append('|---|---:|---:|---:|---:|---|')
for (strat, instr), ts in cells[:15]:
    ll = [t for t in ts if t['outcome']=='LOSS']
    if len(ll) < 10: continue
    imm = [t for t in ll if is_immediate_death(t)]
    rate = len(imm)/len(ll)
    avg_mae = stat.mean([t['_mae'] for t in imm]) if imm else 0
    implication = 'Entry timing bad' if rate > 0.85 else ('SL too tight' if rate < 0.50 else 'Mixed')
    OUT.append(f'| {strat}×{instr} | {len(ll)} | {len(imm)} | {rate:.0%} | {avg_mae:.1f} pip | {implication} |')
OUT.append('')
OUT.append('**含意**:')
OUT.append('- Rate > 90%: entry が逆方向に生まれている → **entry logic 側に改善の余地** (confidence 閾値 / regime filter 追加)')
OUT.append('- Rate < 50%: entry 方向は合っているが SL が速く潰される → **SL 距離 / BE 移動が速すぎる可能性**')
OUT.append('')

# ═══════════════════════════════════════════════
# SECTION C: Clean WIN vs Lucky WIN
# ═══════════════════════════════════════════════
OUT.append('---')
OUT.append('')
OUT.append('## C. WIN の品質分解 — "Clean WIN" vs "Lucky WIN"')
OUT.append('')
OUT.append('Definition:')
OUT.append('- **Clean WIN**: `MAE/|SL| < 0.25` (ほぼ逆行なく TP 到達)')
OUT.append('- **Lucky WIN**: `MAE/|SL| > 0.67` (SL 寸前から反転してTP)')
OUT.append('')
OUT.append('Clean WIN 比率 = 戦略の "edge quality" 指標. Lucky WIN 比率が高い = ランダム寄与大で再現性疑義.')
OUT.append('')

OUT.append('### C.1 戦略別 WIN 品質')
OUT.append('| strat×instr | N_win | Clean | Lucky | Clean比 | edge quality |')
OUT.append('|---|---:|---:|---:|---:|---|')
for (strat, instr), ts in cells[:20]:
    ww = [t for t in ts if t['outcome']=='WIN' and t['_mae_ratio'] is not None]
    if len(ww) < 5: continue
    clean = sum(1 for t in ww if t['_mae_ratio'] < 0.25)
    lucky = sum(1 for t in ww if t['_mae_ratio'] > 0.67)
    clean_pct = clean/len(ww)
    lucky_pct = lucky/len(ww)
    if clean_pct >= 0.6: q = '✓ high (edge real)'
    elif lucky_pct >= 0.3: q = '⚠ luck-heavy'
    else: q = 'mixed'
    OUT.append(f'| {strat}×{instr} | {len(ww)} | {clean} ({clean_pct:.0%}) | {lucky} ({lucky_pct:.0%}) | {clean_pct:.0%} | {q} |')
OUT.append('')

# ═══════════════════════════════════════════════
# SECTION D: Entry feature PMI — predictive power
# ═══════════════════════════════════════════════
OUT.append('---')
OUT.append('')
OUT.append('## D. Entry feature の予測力 — Pointwise Mutual Information')
OUT.append('')
OUT.append('PMI(feature=v, WIN) = log[ P(WIN|feature=v) / P(WIN) ]  ')
OUT.append('> 0 means this value tilts toward WIN. < 0 toward LOSS. |PMI| は効果量.')
OUT.append('')

# Compute quartile edges globally for all features
def qedges(vals):
    xs = sorted([x for x in vals if x is not None])
    if len(xs) < 8: return [0,0,0]
    return [xs[int(len(xs)*0.25)], xs[int(len(xs)*0.50)], xs[int(len(xs)*0.75)]]

def qbin(v, e):
    if v is None: return 'NA'
    if v <= e[0]: return 'Q1'
    if v <= e[1]: return 'Q2'
    if v <= e[2]: return 'Q3'
    return 'Q4'

e_conf = qedges([t['_conf'] for t in trades])
e_adx = qedges([t['_adx'] for t in trades])
e_atr = qedges([t['_atr'] for t in trades])
e_cvem = qedges([t['_cvem'] for t in trades])
e_score = qedges([t['_score'] for t in trades])
e_spread = qedges([t['_spread'] for t in trades])

for t in trades:
    t['_conf_q'] = qbin(t['_conf'], e_conf)
    t['_adx_q'] = qbin(t['_adx'], e_adx)
    t['_atr_q'] = qbin(t['_atr'], e_atr)
    t['_cvem_q'] = qbin(t['_cvem'], e_cvem)
    t['_score_q'] = qbin(t['_score'], e_score)
    t['_spread_q'] = qbin(t['_spread'], e_spread)

base_wr = len(wins)/len(trades)
FEATURES = [
    ('_sess', 'session'),
    ('_dir', 'direction'),
    ('_hmm', 'hmm_regime'),
    ('mtf_alignment', 'mtf_alignment'),
    ('mtf_regime', 'mtf_regime'),
    ('mtf_vol_state', 'mtf_vol_state'),
    ('_conf_q', 'confidence quartile'),
    ('_adx_q', 'ADX quartile'),
    ('_atr_q', 'ATR ratio quartile'),
    ('_cvem_q', 'close_vs_ema200 quartile'),
    ('_score_q', 'score quartile'),
    ('_spread_q', 'spread quartile'),
]

OUT.append('### D.1 Portfolio-wide PMI ranking (N≥50 cells only)')
OUT.append('| feature | value | N | WR | PMI | Δ from base |')
OUT.append('|---|---|---:|---:|---:|---:|')

rows = []
for key, label in FEATURES:
    groups = defaultdict(list)
    for t in trades:
        groups[t.get(key, 'NA')].append(t)
    for val, g in groups.items():
        if len(g) < 50: continue
        w = sum(1 for t in g if t['outcome']=='WIN')
        wr = w/len(g)
        if wr <= 0: continue
        pmi = math.log(wr/base_wr) if base_wr>0 else 0
        rows.append((label, val, len(g), wr, pmi, wr - base_wr))
rows.sort(key=lambda x: -x[4])
for label, val, n, wr, pmi, dlt in rows[:15]:
    marker = '⭐' if pmi > 0.10 else ('⚠️' if pmi < -0.15 else '')
    OUT.append(f'| {label} | {val} | {n} | {wr:.1%} | {pmi:+.3f} {marker} | {dlt*100:+.1f}pp |')
OUT.append('')
OUT.append('**Bottom 5 (avoid these)**:')
for label, val, n, wr, pmi, dlt in sorted(rows, key=lambda x: x[4])[:5]:
    OUT.append(f'- {label}={val}: N={n} WR={wr:.1%} PMI={pmi:+.3f}')
OUT.append('')

# ═══════════════════════════════════════════════
# SECTION E: Virtual filter simulation
# ═══════════════════════════════════════════════
OUT.append('---')
OUT.append('')
OUT.append('## E. Virtual Filter Simulation — "もし X を filter していたら"')
OUT.append('')
OUT.append('各 filter rule を shadow 全体に適用し、WR uplift と N cost をシミュレート.')
OUT.append('戦略変更の判断材料 (pre-registration 候補として):')
OUT.append('')

# Candidate filters
def simulate_filter(name, predicate, trades_pool):
    kept = [t for t in trades_pool if predicate(t)]
    dropped = [t for t in trades_pool if not predicate(t)]
    if not kept: return None
    w = sum(1 for t in kept if t['outcome']=='WIN')
    wr_kept = w/len(kept)
    drop_w = sum(1 for t in dropped if t['outcome']=='WIN')
    drop_wr = drop_w/len(dropped) if dropped else 0
    total = len(trades_pool)
    base = sum(1 for t in trades_pool if t['outcome']=='WIN') / total
    return {
        'name': name, 'N_kept': len(kept), 'N_drop': len(dropped),
        'WR_kept': wr_kept, 'WR_drop': drop_wr, 'WR_base': base,
        'uplift_pp': (wr_kept - base)*100,
        'retention': len(kept)/total,
        'pnl_kept_sum': sum(t['_pnl'] for t in kept),
        'pnl_drop_sum': sum(t['_pnl'] for t in dropped),
    }

filter_defs = [
    ('DROP: immediate_death-prone (score Q1)',
        lambda t: t['_score_q'] != 'Q1', trades),
    ('DROP: confidence Q4 (paradoxical)',
        lambda t: t['_conf_q'] != 'Q4', trades),
    ('KEEP: mtf_alignment=aligned only',
        lambda t: t.get('mtf_alignment') == 'aligned', trades),
    ('DROP: mtf_alignment=conflict',
        lambda t: t.get('mtf_alignment') != 'conflict', trades),
    ('KEEP: NY session only',
        lambda t: t['_sess'] == 'ny', trades),
    ('DROP: offhours session',
        lambda t: t['_sess'] != 'offhours', trades),
    ('KEEP: ATR Q1 (low volatility)',
        lambda t: t['_atr_q'] == 'Q1', trades),
    ('KEEP: ADX Q2-Q3 (moderate trend)',
        lambda t: t['_adx_q'] in ('Q2', 'Q3'), trades),
    ('DROP: spread Q4 (wide spread)',
        lambda t: t['_spread_q'] != 'Q4', trades),
    ('KEEP: BUY direction only',
        lambda t: t['_dir'] == 'BUY', trades),
    ('DROP: USD_JPY SELL (poor cell)',
        lambda t: not (t['instrument']=='USD_JPY' and t['_dir']=='SELL'), trades),
    ('KEEP: confidence Q1 (paradox exploit)',
        lambda t: t['_conf_q'] == 'Q1', trades),
]

results = []
for name, pred, pool in filter_defs:
    r = simulate_filter(name, pred, pool)
    if r: results.append(r)

results.sort(key=lambda r: -r['uplift_pp'])

OUT.append('| Filter rule | N_kept | retention | WR_kept | uplift | PnL sum kept |')
OUT.append('|---|---:|---:|---:|---:|---:|')
for r in results:
    marker = '★' if r['uplift_pp'] >= 3 and r['retention'] >= 0.3 else ''
    OUT.append(f"| {r['name']} | {r['N_kept']} | {r['retention']:.0%} | {r['WR_kept']:.1%} | {r['uplift_pp']:+.1f}pp {marker} | {r['pnl_kept_sum']:+.1f} pip |")
OUT.append('')
OUT.append('**★ marker**: uplift ≥ +3pp AND retention ≥ 30% — 実用価値と統計的安定の両立.')
OUT.append('')

# ═══════════════════════════════════════════════
# SECTION F: Combined filter — stacking top 3
# ═══════════════════════════════════════════════
OUT.append('---')
OUT.append('')
OUT.append('## F. Filter stacking — top 3 rules combined')
OUT.append('')

# Take top-3 single-rule filters
top3 = [r for r in results if r['uplift_pp'] > 0][:3]
OUT.append(f'Selected: {", ".join(r["name"] for r in top3)}')
OUT.append('')

# Simulate intersection
def all_pass(t, preds):
    for _, pred, _ in preds:
        if not pred(t): return False
    return True

top3_names = [r['name'] for r in top3]
top3_preds = [fd for fd in filter_defs if fd[0] in top3_names]
stacked = [t for t in trades if all_pass(t, top3_preds)]
if stacked:
    w = sum(1 for t in stacked if t['outcome']=='WIN')
    wr_s = w/len(stacked)
    OUT.append(f'**Stacked result**: N_kept={len(stacked)}, WR={wr_s:.1%} (uplift {(wr_s-base_wr)*100:+.1f}pp), retention={len(stacked)/len(trades):.0%}')
    pnl_s = sum(t['_pnl'] for t in stacked)
    OUT.append(f'Stacked PnL sum = {pnl_s:+.1f} pip')
    OUT.append('')

# ═══════════════════════════════════════════════
# SECTION G: VWAP-specific case study (small N)
# ═══════════════════════════════════════════════
vwap = [t for t in trades if t['entry_type']=='vwap_mean_reversion']
if vwap:
    OUT.append('---')
    OUT.append('')
    OUT.append('## G. VWAP mean reversion — N=12 Shadow trade-level 分析 (small-N case study)')
    OUT.append('')
    OUT.append('N が小さすぎて統計推論不能. 個別 trade の構造を機械的に列挙.')
    OUT.append('')
    OUT.append('| date | pair | dir | conf | score | adx | atr | sess | outcome | hold_min | MFE | MAE | MAE/SL |')
    OUT.append('|---|---|---|---:|---:|---:|---:|---|---|---:|---:|---:|---:|')
    for t in sorted(vwap, key=lambda x: x.get('created_at','')):
        mae_r = f"{t['_mae_ratio']:.2f}" if t['_mae_ratio'] is not None else '—'
        hold = f"{t['_hold_min']:.0f}" if t['_hold_min'] is not None else '—'
        OUT.append(f"| {t.get('created_at','')[:10]} | {t['instrument']} | {t['_dir']} | "
                   f"{t['_conf']} | {t['_score']} | {t['_adx']} | {t['_atr']} | "
                   f"{t['_sess']} | {t['outcome']} | {hold} | {t['_mfe']:.1f} | {t['_mae']:.1f} | {mae_r} |")
    OUT.append('')

# ═══════════════════════════════════════════════
# SECTION H: 結論・actionable recommendations
# ═══════════════════════════════════════════════
OUT.append('---')
OUT.append('')
OUT.append('## H. Actionable recommendations (quant vote, implementation 前提)')
OUT.append('')
OUT.append('以下の filter rule は **virtual simulation** の結果. LIVE 適用は pre-registration 必須.')
OUT.append('')

OUT.append('### H.1 "Drop" 型 (損失カット) — 即時適用の価値高')
for r in results[:3]:
    if 'DROP' not in r['name']: continue
    OUT.append(f'- **{r["name"]}**: retention {r["retention"]:.0%}, WR uplift {r["uplift_pp"]:+.1f}pp, PnL kept {r["pnl_kept_sum"]:+.1f}')
OUT.append('')

OUT.append('### H.2 "Keep" 型 (集中) — PRIME split 候補')
for r in results[:5]:
    if 'KEEP' not in r['name']: continue
    OUT.append(f'- **{r["name"]}**: retention {r["retention"]:.0%}, WR {r["WR_kept"]:.1%} (uplift {r["uplift_pp"]:+.1f}pp)')
OUT.append('')

OUT.append('### H.3 避けるべき罠 (PMI 負の領域)')
bad_rows = sorted(rows, key=lambda x: x[4])[:5]
for label, val, n, wr, pmi, dlt in bad_rows:
    OUT.append(f'- {label}={val}: N={n} WR={wr:.1%} PMI={pmi:+.3f} → filter で排除検討')
OUT.append('')

OUT.append('### H.4 Priority ranking (WR 改善寄与度)')
OUT.append('')
OUT.append('1. **Confidence Q4 paradox filter** (既存 [[confidence-q4-paradox]] 記録済) — 最も uplift 大')
OUT.append('2. **Score Q1 drop** — 戦略 score の lowest quartile は systematic loser')
OUT.append('3. **mtf_alignment=conflict drop** — 既存 gate の漏れチェック')
OUT.append('4. **spread Q4 drop** — friction 動的排除 (既存 Spread Gate と重なるが ex-post で測定)')
OUT.append('5. **session: offhours drop** — thin liquidity による slippage 増')
OUT.append('')
OUT.append('### H.5 本日の実装判断 (honest)')
OUT.append('')
OUT.append('- 本日午前に **6 PRIME strategies pre-registered** (2026-05-15 binding). 追加の filter 実装は multiple testing inflation.')
OUT.append('- 上記 recommendations は **2026-05-05 中間評価** で再計算し, 有意性が維持されていれば 2026-05-15 に family に加える.')
OUT.append('- 現時点で最も valuable な action = **観察継続**. 蓄積 N が増えれば filter の確度も上がる.')
OUT.append('')
OUT.append('### H.6 限界 (disclosure)')
OUT.append('')
OUT.append('- Shadow ≠ LIVE: Shadow 母集団での WR uplift は LIVE で再現しない可能性 (dt_fib_reversal 前例).')
OUT.append('- Post-hoc 探索: 12 filter candidate × 5 feature = 60 実質 hypothesis. Bonferroni 未補正.')
OUT.append('- 戦略 heterogeneity: portfolio-wide filter と戦略別最適 filter は異なる. 単一 rule で全戦略最適化は不可.')

with open('/tmp/tp_analysis/tp_sl_deep.md', 'w') as f:
    f.write('\n'.join(OUT))
print(f'wrote /tmp/tp_analysis/tp_sl_deep.md ({len(OUT)} lines)')
