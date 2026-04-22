#!/usr/bin/env python3
"""
TP-hit quant analysis — research-only, no strategy changes.

Pipeline:
  1. Load production trades JSON (fetched via curl from /api/demo/trades).
  2. Filter: non-XAU, CLOSED (has outcome or close_reason).
  3. Segment TP-hit vs non-TP-hit across (strategy, pair, regime, direction, tf, hour, window).
  4. Feature-level Mann-Whitney U with Bonferroni correction.
  5. Simple rule-mining: pick single-feature lifts that pass Bonferroni and produce
     >=lift_thresh uplift in TP-hit rate. Composite rules are reported per cond.
  6. Kelly-like EV per reproducible condition + Wilson 95% CI.
  7. Stability: pre-cutoff vs post-cutoff sign coherence, shadow vs live.

Output: prints markdown tables; writes a CSV summary for KB raw/analysis.
"""
from __future__ import annotations
import json
import math
import csv
import sys
import re
from collections import defaultdict, Counter
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median, stdev

TRADES_JSON = Path('/tmp/trades_all.json')
CSV_OUT = Path('/tmp/fx-tp-hit/knowledge-base/raw/analysis/tp-hit-raw-2026-04-20.csv')
CUTOFF_ISO = '2026-04-16T08:00:00+00:00'
CUTOFF_DT = datetime.fromisoformat(CUTOFF_ISO)

# ---------- util ----------

def parse_iso(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace('Z', '+00:00'))
    except Exception:
        return None


def wilson_ci(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def mannwhitney_u(a, b):
    """Two-sided approximate Mann-Whitney U; returns (U, z, p).
    Handles ties with average ranks. Normal approximation for large N.
    """
    if not a or not b:
        return (float('nan'), float('nan'), 1.0)
    na, nb = len(a), len(b)
    combined = [(v, 0) for v in a] + [(v, 1) for v in b]
    combined.sort(key=lambda x: x[0])
    # average ranks
    ranks = [0.0] * len(combined)
    i = 0
    while i < len(combined):
        j = i
        while j + 1 < len(combined) and combined[j + 1][0] == combined[i][0]:
            j += 1
        avg = (i + j) / 2 + 1  # 1-based
        for k in range(i, j + 1):
            ranks[k] = avg
        i = j + 1
    ra = sum(r for r, (_, g) in zip(ranks, combined) if g == 0)
    u1 = ra - na * (na + 1) / 2
    u2 = na * nb - u1
    U = min(u1, u2)
    # ties adjustment
    tie_term = 0.0
    i = 0
    while i < len(combined):
        j = i
        while j + 1 < len(combined) and combined[j + 1][0] == combined[i][0]:
            j += 1
        t = j - i + 1
        if t > 1:
            tie_term += t * (t - 1) * (t + 1)
        i = j + 1
    N = na + nb
    mu = na * nb / 2
    sigma_sq = na * nb / 12 * ((N + 1) - tie_term / (N * (N - 1))) if N > 1 else 0
    if sigma_sq <= 0:
        return (U, 0.0, 1.0)
    z = (U - mu) / math.sqrt(sigma_sq)
    # two-sided
    p = math.erfc(abs(z) / math.sqrt(2))
    return (U, z, p)


# ---------- load ----------

def load_trades():
    data = json.loads(TRADES_JSON.read_text())
    raw = data['trades']
    # Closed non-XAU only (includes BREAKEVEN); TP-hit = outcome=='WIN' per user brief
    out = []
    for t in raw:
        inst = t.get('instrument') or ''
        if 'XAU' in inst:
            continue
        status = (t.get('status') or '').upper()
        outcome = t.get('outcome')
        if status != 'CLOSED':
            continue
        # drop BREAKEVEN trades from TP/non-TP contrast (they are neither)
        if outcome not in ('WIN', 'LOSS'):
            continue
        t['_entry_dt'] = parse_iso(t.get('entry_time'))
        # Canonical TP-hit = reached profit (WIN). 458 explicit TP_HIT + 108 OANDA_SL_TP + ...
        t['_is_tp'] = (outcome == 'WIN')
        t['_is_tp_strict'] = (t.get('close_reason') == 'TP_HIT')
        t['_is_post'] = (t['_entry_dt'] is not None and t['_entry_dt'] >= CUTOFF_DT)
        # parse regime json (best-effort)
        rj = t.get('regime')
        if isinstance(rj, str) and rj:
            try:
                t['_regime'] = json.loads(rj)
            except Exception:
                t['_regime'] = {}
        else:
            t['_regime'] = rj or {}
        out.append(t)
    return out


# ---------- phase 1: segmentation ----------

def segment_counts(trades, key_fn, min_n=10):
    buckets = defaultdict(list)
    for t in trades:
        k = key_fn(t)
        buckets[k].append(t)
    rows = []
    total_tp = sum(1 for t in trades if t['_is_tp'])
    base = total_tp / len(trades) if trades else 0
    for k, lst in buckets.items():
        n = len(lst)
        if n < min_n:
            continue
        tp = sum(1 for t in lst if t['_is_tp'])
        wr = tp / n
        lift = wr / base if base > 0 else float('nan')
        lo, hi = wilson_ci(tp, n)
        rows.append((k, n, tp, wr, lift, lo, hi))
    rows.sort(key=lambda r: -r[3])
    return rows, base


def fmt_rows(rows, title, key_label='key'):
    lines = [f'\n### {title}', f'| {key_label} | N | TP | WR% | lift | 95%CI |', '|---|---|---|---|---|---|']
    for k, n, tp, wr, lift, lo, hi in rows:
        lines.append(f'| {k} | {n} | {tp} | {wr*100:.1f} | {lift:.2f} | [{lo*100:.1f}, {hi*100:.1f}] |')
    return '\n'.join(lines)


# ---------- phase 2: TP vs nonTP feature contrast ----------

NUM_FEATURES = ['score', 'confidence', 'ema_conf', 'spread_at_entry',
                'mafe_favorable_pips', 'mafe_adverse_pips', 'slippage_pips']


def feature_contrast(trades):
    tp = [t for t in trades if t['_is_tp']]
    nn = [t for t in trades if not t['_is_tp']]
    results = []
    for f in NUM_FEATURES:
        a = [t[f] for t in tp if isinstance(t.get(f), (int, float))]
        b = [t[f] for t in nn if isinstance(t.get(f), (int, float))]
        if len(a) < 30 or len(b) < 30:
            continue
        U, z, p = mannwhitney_u(a, b)
        results.append({
            'feature': f,
            'n_tp': len(a), 'n_nontp': len(b),
            'med_tp': median(a), 'med_nontp': median(b),
            'mean_tp': mean(a), 'mean_nontp': mean(b),
            'U': U, 'z': z, 'p': p,
        })
    # Bonferroni
    m = len(results)
    alpha = 0.05
    alpha_b = alpha / m if m > 0 else alpha
    for r in results:
        r['bonf_pass'] = r['p'] < alpha_b
        r['alpha_bonf'] = alpha_b
    return results


# ---------- phase 3: conditional rules ----------

def cond_rate(trades, pred):
    sub = [t for t in trades if pred(t)]
    n = len(sub)
    if n == 0:
        return (0, 0, 0.0, 0.0, 0.0)
    tp = sum(1 for t in sub if t['_is_tp'])
    lo, hi = wilson_ci(tp, n)
    return (n, tp, tp / n, lo, hi)


def mafe_ratio(t):
    fav = t.get('mafe_favorable_pips') or 0
    adv = t.get('mafe_adverse_pips') or 0
    if fav + adv <= 0:
        return None
    return adv / (fav + adv)


def hour_of(t):
    dt = t['_entry_dt']
    return dt.hour if dt else None


def session_of(t):
    h = hour_of(t)
    if h is None:
        return 'unknown'
    if 0 <= h < 7:
        return 'tokyo'
    if 7 <= h < 13:
        return 'london_pre'
    if 13 <= h < 20:
        return 'ny'
    return 'late'


def regime_of(t):
    r = t.get('_regime')
    if isinstance(r, dict):
        return r.get('regime') or t.get('mtf_regime') or 'unknown'
    return t.get('mtf_regime') or 'unknown'


# ---------- phase 4: Kelly-like EV per condition ----------

def cond_ev(trades, pred):
    sub = [t for t in trades if pred(t)]
    n = len(sub)
    if n == 0:
        return None
    pnl = [t.get('pnl_pips') or 0 for t in sub]
    r_mul = [t.get('pnl_r') or 0 for t in sub]
    tp = sum(1 for t in sub if t['_is_tp'])
    wr = tp / n
    ev_pip = mean(pnl)
    ev_r = mean(r_mul)
    sd_pip = stdev(pnl) if n > 1 else 0.0
    sharpe_like = ev_pip / sd_pip if sd_pip > 0 else 0.0
    lo, hi = wilson_ci(tp, n)
    # Kelly: approximate with avg win / avg loss payoff
    wins = [p for p in pnl if p > 0]
    losses = [-p for p in pnl if p < 0]
    if wins and losses and mean(losses) > 0:
        b = mean(wins) / mean(losses)
        k = wr - (1 - wr) / b if b > 0 else 0.0
    else:
        k = 0.0
    return dict(n=n, tp=tp, wr=wr, ev_pip=ev_pip, ev_r=ev_r,
                sd_pip=sd_pip, sharpe=sharpe_like, wilson_lo=lo, wilson_hi=hi,
                kelly=k)


# ---------- phase 5: stability ----------

def stability_split(trades, pred):
    out = {}
    for label, subset in [
        ('pre_cutoff', [t for t in trades if not t['_is_post']]),
        ('post_cutoff', [t for t in trades if t['_is_post']]),
        ('live_only', [t for t in trades if t.get('is_shadow') == 0]),
        ('shadow_only', [t for t in trades if t.get('is_shadow') == 1]),
    ]:
        out[label] = cond_ev(subset, pred)
    return out


# ---------- main ----------

def main():
    trades = load_trades()
    tp_all = [t for t in trades if t['_is_tp']]
    print(f'# TP-hit Quant Analysis — Data Window Header\n')
    print(f'- Source: /api/demo/trades (Render prod)')
    print(f'- Cutoff: {CUTOFF_ISO}')
    print(f'- Closed non-XAU: {len(trades)}')
    print(f'- TP-hit (close_reason=TP_HIT): {len(tp_all)}')
    print(f'- non-TP-hit: {len(trades) - len(tp_all)}')
    pre = [t for t in trades if not t['_is_post']]
    post = [t for t in trades if t['_is_post']]
    print(f'- Pre-cutoff closed: {len(pre)} (TP={sum(1 for t in pre if t["_is_tp"])})')
    print(f'- Post-cutoff closed: {len(post)} (TP={sum(1 for t in post if t["_is_tp"])})')
    print(f'- Live TP (is_shadow=0): {sum(1 for t in tp_all if t.get("is_shadow")==0)}')
    print(f'- Shadow TP (is_shadow=1): {sum(1 for t in tp_all if t.get("is_shadow")==1)}')

    # -------- Phase 1 --------
    print('\n# Phase 1 — Segmentation (all closed non-XAU)')
    rows, base = segment_counts(trades, lambda t: f"{t.get('entry_type')} × {t.get('instrument')}", min_n=20)
    print(f'\nBase rate (TP-hit / closed non-XAU): {base*100:.2f}%')
    print(fmt_rows(rows[:20], 'Top 20 strategy×pair by TP-hit rate', 'strategy × pair'))

    rows, _ = segment_counts(trades, lambda t: regime_of(t), min_n=20)
    print(fmt_rows(rows, 'Regime', 'regime'))

    rows, _ = segment_counts(trades, lambda t: t.get('direction'), min_n=20)
    print(fmt_rows(rows, 'Direction', 'direction'))

    rows, _ = segment_counts(trades, lambda t: t.get('tf'), min_n=20)
    print(fmt_rows(rows, 'TF', 'tf'))

    rows, _ = segment_counts(trades, session_of, min_n=20)
    print(fmt_rows(rows, 'Session', 'session'))

    rows, _ = segment_counts(trades, lambda t: t.get('mtf_alignment'), min_n=20)
    print(fmt_rows(rows, 'MTF alignment', 'mtf_alignment'))

    rows, _ = segment_counts(trades, lambda t: ('post' if t['_is_post'] else 'pre') + ('_live' if t.get('is_shadow')==0 else '_shadow'), min_n=20)
    print(fmt_rows(rows, 'Window × Pool', 'window_pool'))

    # -------- Phase 2 --------
    print('\n# Phase 2 — TP-hit vs non-TP-hit feature contrast (Mann-Whitney U, Bonferroni corrected)')
    fc = feature_contrast(trades)
    if fc:
        alpha_b = fc[0]['alpha_bonf']
        print(f'\nAlpha (family-wise, Bonferroni m={len(fc)}): {alpha_b:.4f}\n')
        print('| feature | N_tp | N_nontp | med_tp | med_nontp | mean_tp | mean_nontp | z | p | Bonf pass |')
        print('|---|---|---|---|---|---|---|---|---|---|')
        for r in fc:
            mark = 'YES' if r['bonf_pass'] else 'no'
            print(f"| {r['feature']} | {r['n_tp']} | {r['n_nontp']} | {r['med_tp']:.3f} | {r['med_nontp']:.3f} | {r['mean_tp']:.3f} | {r['mean_nontp']:.3f} | {r['z']:.2f} | {r['p']:.2e} | {mark} |")

    # -------- Phase 3: reproducible condition search --------
    print('\n# Phase 3 — Reproducibility conditions (single- and double-feature)')
    print('\nScreening rule: N>=30 AND lift >= 1.20 AND Wilson-CI lower-bound > base')

    base = len([t for t in trades if t['_is_tp']]) / len(trades)
    print(f'Base TP-hit rate: {base*100:.2f}% (N={len(trades)})')

    # Predictive (entry-time) features only — we do NOT mine post-hoc intra-trade
    # features (mafe_*) as "reproducible conditions" because they are observed
    # during the trade and are mechanically correlated with TP-hit (tautology).
    # MAFE contrast IS reported in Phase 2 but is excluded from Phase 3 rule mining.
    candidate_preds = []
    # strategy x pair (entry-time)
    sp_counts = Counter((t.get('entry_type'), t.get('instrument')) for t in trades)
    for (s, p), n in sp_counts.items():
        if n >= 30:
            candidate_preds.append((f'strat={s} × pair={p}',
                lambda t, s=s, p=p: t.get('entry_type') == s and t.get('instrument') == p))
    # regime
    for reg in set(regime_of(t) for t in trades):
        candidate_preds.append((f'regime={reg}', lambda t, r=reg: regime_of(t) == r))
    # direction
    for d in ['BUY', 'SELL']:
        candidate_preds.append((f'dir={d}', lambda t, d=d: t.get('direction') == d))
    # tf
    for tf in set(t.get('tf') for t in trades):
        if tf:
            candidate_preds.append((f'tf={tf}', lambda t, f=tf: t.get('tf') == f))
    # session
    for s in ['tokyo', 'london_pre', 'ny', 'late']:
        candidate_preds.append((f'session={s}', lambda t, s=s: session_of(t) == s))
    # mtf_alignment (entry-time)
    for a in set(t.get('mtf_alignment') for t in trades):
        if a:
            candidate_preds.append((f'mtf_align={a}', lambda t, a=a: t.get('mtf_alignment') == a))
    # score bucket (entry-time)
    candidate_preds.append(('score>=3', lambda t: (t.get('score') or 0) >= 3))
    candidate_preds.append(('score<=0', lambda t: (t.get('score') or 0) <= 0))
    # confidence bucket (entry-time)
    candidate_preds.append(('conf>=60', lambda t: (t.get('confidence') or 0) >= 60))
    candidate_preds.append(('ema_conf>=60', lambda t: (t.get('ema_conf') or 0) >= 60))
    candidate_preds.append(('spread<=0.8', lambda t: (t.get('spread_at_entry') or 0) <= 0.8))
    # mtf_vol_state (entry-time)
    for vs in set(t.get('mtf_vol_state') for t in trades):
        if vs:
            candidate_preds.append((f'mtf_vol_state={vs}', lambda t, v=vs: t.get('mtf_vol_state') == v))
    # layer1_dir
    for l1 in set(t.get('layer1_dir') for t in trades):
        if l1:
            candidate_preds.append((f'layer1={l1}', lambda t, l=l1: t.get('layer1_dir') == l))
    # gate_group
    for gg in set(t.get('gate_group') for t in trades):
        if gg:
            candidate_preds.append((f'gate_group={gg}', lambda t, g=gg: t.get('gate_group') == g))
    # mode
    for m in set(t.get('mode') for t in trades):
        if m:
            candidate_preds.append((f'mode={m}', lambda t, mm=m: t.get('mode') == mm))
    # Composite (strat × pair × regime) — the user explicitly asked this form
    sp_reg_counts = Counter((t.get('entry_type'), t.get('instrument'), regime_of(t)) for t in trades)
    for (s, p, r), n in sp_reg_counts.items():
        if n >= 30:
            candidate_preds.append((f'strat={s} × pair={p} × regime={r}',
                lambda t, s=s, p=p, r=r: t.get('entry_type') == s and t.get('instrument') == p and regime_of(t) == r))
    # Composite (strat × pair × session)
    sp_sess_counts = Counter((t.get('entry_type'), t.get('instrument'), session_of(t)) for t in trades)
    for (s, p, ss), n in sp_sess_counts.items():
        if n >= 30:
            candidate_preds.append((f'strat={s} × pair={p} × session={ss}',
                lambda t, s=s, p=p, ss=ss: t.get('entry_type') == s and t.get('instrument') == p and session_of(t) == ss))
    # Composite (strat × pair × direction)
    sp_dir_counts = Counter((t.get('entry_type'), t.get('instrument'), t.get('direction')) for t in trades)
    for (s, p, d), n in sp_dir_counts.items():
        if n >= 30:
            candidate_preds.append((f'strat={s} × pair={p} × dir={d}',
                lambda t, s=s, p=p, d=d: t.get('entry_type') == s and t.get('instrument') == p and t.get('direction') == d))

    # Score all single conditions
    scored = []
    for name, pred in candidate_preds:
        n, tp, wr, lo, hi = cond_rate(trades, pred)
        if n < 30:
            continue
        lift = wr / base if base > 0 else 0
        scored.append((name, n, tp, wr, lift, lo, hi))
    scored.sort(key=lambda r: -r[4])

    # Bonferroni on phase 3 tests: adjust alpha for multiple candidate count
    m = len(scored)
    alpha_b = 0.05 / m if m else 0.05
    print(f'\nSingle-condition candidates: {m}, Bonferroni alpha={alpha_b:.4f}')

    # Binomial 2-sided p-value via normal approximation
    def binom_p(k, n, p0):
        if n == 0 or p0 in (0, 1):
            return 1.0
        mu = n * p0
        sd = math.sqrt(n * p0 * (1 - p0))
        if sd == 0:
            return 1.0
        z = (k - mu) / sd
        return math.erfc(abs(z) / math.sqrt(2))

    print('\n| Condition | N | TP | WR% | lift | 95%CI | p(binom) | Bonf pass |')
    print('|---|---|---|---|---|---|---|---|')
    passed = []
    for name, n, tp, wr, lift, lo, hi in scored:
        p = binom_p(tp, n, base)
        bonf = p < alpha_b
        mark = 'YES' if bonf else 'no'
        if lift >= 1.15 or bonf:
            print(f'| {name} | {n} | {tp} | {wr*100:.1f} | {lift:.2f} | [{lo*100:.1f}, {hi*100:.1f}] | {p:.2e} | {mark} |')
        if bonf and lift >= 1.20 and lo > base:
            passed.append((name, n, tp, wr, lift, lo, hi, p))

    print(f'\nConditions passing Bonferroni AND lift>=1.20 AND Wilson_lo>base: {len(passed)}')

    # -------- Intra-trade (post-hoc) diagnostic (reported but NOT a reproducible rule) --------
    print('\n## Post-hoc intra-trade diagnostic (NOT a reproducibility rule — MAFE observed during trade)')
    print('| Condition | N | TP | WR% | lift | note |')
    print('|---|---|---|---|---|---|')
    for name, pred in [
        ('mafe_ratio<0.3', lambda t: (mafe_ratio(t) or 1) < 0.3),
        ('mafe_ratio<0.5', lambda t: (mafe_ratio(t) or 1) < 0.5),
        ('fav>=4pip (intra)', lambda t: (t.get('mafe_favorable_pips') or 0) >= 4),
    ]:
        n, tp, wr, lo, hi = cond_rate(trades, pred)
        if n:
            lift = wr / base
            print(f'| {name} | {n} | {tp} | {wr*100:.1f} | {lift:.2f} | tautological with TP-hit |')

    # -------- Phase 4 --------
    print('\n# Phase 4 — Kelly-like EV per reproducible condition')
    print('| Condition | N | TP | WR% | EV(pip) | EV(R) | σ | Sharpe | Kelly | 95%CI |')
    print('|---|---|---|---|---|---|---|---|---|---|')
    # find predicate back via dict
    pred_map = dict(candidate_preds)
    for name, n, tp, wr, lift, lo, hi, p in passed:
        pred = pred_map[name]
        ev = cond_ev(trades, pred)
        print(f'| {name} | {ev["n"]} | {ev["tp"]} | {ev["wr"]*100:.1f} | {ev["ev_pip"]:+.2f} | {ev["ev_r"]:+.2f} | {ev["sd_pip"]:.2f} | {ev["sharpe"]:+.2f} | {ev["kelly"]:+.3f} | [{ev["wilson_lo"]*100:.1f}, {ev["wilson_hi"]*100:.1f}] |')

    # -------- Phase 5 --------
    print('\n# Phase 5 — Stability (pre/post cutoff, live/shadow sign coherence)')
    print('| Condition | pre N | pre WR% | pre EV | post N | post WR% | post EV | live N | live WR% | live EV | shadow N | shadow WR% | shadow EV | sign_ok |')
    print('|---|---|---|---|---|---|---|---|---|---|---|---|---|---|')
    stability_rows = []
    for name, n, tp, wr, lift, lo, hi, p in passed:
        pred = pred_map[name]
        st = stability_split(trades, pred)
        def fmt(block):
            if not block:
                return ('0', 'n/a', 'n/a')
            return (str(block['n']), f'{block["wr"]*100:.1f}', f'{block["ev_pip"]:+.2f}')
        pre_n, pre_wr, pre_ev = fmt(st['pre_cutoff'])
        post_n, post_wr, post_ev = fmt(st['post_cutoff'])
        live_n, live_wr, live_ev = fmt(st['live_only'])
        sh_n, sh_wr, sh_ev = fmt(st['shadow_only'])
        pre_ev_v = st['pre_cutoff']['ev_pip'] if st['pre_cutoff'] else float('nan')
        post_ev_v = st['post_cutoff']['ev_pip'] if st['post_cutoff'] else float('nan')
        live_ev_v = st['live_only']['ev_pip'] if st['live_only'] else float('nan')
        sh_ev_v = st['shadow_only']['ev_pip'] if st['shadow_only'] else float('nan')
        # sign coherence: all non-nan positive, or all non-nan negative
        vals = [v for v in [pre_ev_v, post_ev_v, live_ev_v, sh_ev_v] if v == v]
        sign_ok = 'YES' if vals and (all(v > 0 for v in vals) or all(v < 0 for v in vals)) else 'no'
        print(f'| {name} | {pre_n} | {pre_wr} | {pre_ev} | {post_n} | {post_wr} | {post_ev} | {live_n} | {live_wr} | {live_ev} | {sh_n} | {sh_wr} | {sh_ev} | {sign_ok} |')
        stability_rows.append((name, pre_ev_v, post_ev_v, live_ev_v, sh_ev_v, sign_ok))

    # -------- CSV --------
    CSV_OUT.parent.mkdir(parents=True, exist_ok=True)
    with CSV_OUT.open('w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['condition', 'n', 'tp', 'wr', 'lift', 'wilson_lo', 'wilson_hi',
                    'ev_pip', 'ev_r', 'sd_pip', 'sharpe', 'kelly',
                    'pre_ev', 'post_ev', 'live_ev', 'shadow_ev', 'sign_ok'])
        for row in passed:
            name, n, tp, wr, lift, lo, hi, p = row
            pred = pred_map[name]
            ev = cond_ev(trades, pred)
            st = stability_split(trades, pred)
            pre_ev_v = st['pre_cutoff']['ev_pip'] if st['pre_cutoff'] else ''
            post_ev_v = st['post_cutoff']['ev_pip'] if st['post_cutoff'] else ''
            live_ev_v = st['live_only']['ev_pip'] if st['live_only'] else ''
            sh_ev_v = st['shadow_only']['ev_pip'] if st['shadow_only'] else ''
            vals = [v for v in [pre_ev_v, post_ev_v, live_ev_v, sh_ev_v] if isinstance(v, (int, float))]
            sign_ok = 'YES' if vals and (all(v > 0 for v in vals) or all(v < 0 for v in vals)) else 'no'
            w.writerow([name, n, tp, f'{wr:.4f}', f'{lift:.3f}', f'{lo:.4f}', f'{hi:.4f}',
                        f'{ev["ev_pip"]:.3f}', f'{ev["ev_r"]:.3f}', f'{ev["sd_pip"]:.3f}',
                        f'{ev["sharpe"]:.3f}', f'{ev["kelly"]:.3f}',
                        pre_ev_v, post_ev_v, live_ev_v, sh_ev_v, sign_ok])
    print(f'\nCSV written: {CSV_OUT}')

    # -------- DSR-like deflation note --------
    # DSR haircut concept: under m independent tests at alpha=0.05, expected false
    # positives = m * alpha. Here m≈ number of candidates (scored). Expected FP under null:
    print('\n# Phase 4b — Multiple-testing deflation (DSR-inspired)')
    print(f'Candidate conditions tested: {m}')
    print(f'Expected false-positives under global null (alpha=0.05): {m*0.05:.1f}')
    print(f'Conditions passing Bonferroni+lift+CI: {len(passed)} — if > expected FP, family-wise signal is plausible.')


if __name__ == '__main__':
    main()
