# Wave 1 R2-A Power Analysis (Pre-measurement Statistical Design)

**Session**: curried-ritchie (Wave 2 Day 2 Quant Rigor)
**Date**: 2026-04-27 JST early morning (= 2026-04-26 PM UTC)
**Status**: 計測前事前設計 (market re-open まで +5h)
**目的**: Wave 1 R2-A 効果の科学的検出可能性を**事前**に確定し、計測時に "N 不足を効果なしと誤判定" するリスクを排除する

---

## 0. Executive Summary (Quant TL;DR)

**4 cells のうち 2 cells のみ実用的 N で検出可能**:

| Cell | Δ 必要 (baseline-restore) | 必要 N/cell | 達成見込み |
|------|---------------------------|-------------|------------|
| **stoch_trend_pullback × Overlap × q2** | **16.7pp** | **N≥70** | **+5-7 days** ✅ |
| **sr_channel_reversal × London × q3** | **12.1pp** | **N≥125** | **+10-15 days** ✅ |
| ema_trend_scalp × London × q0 | 4.4pp | **N≥940** | **+6 ヶ月** ❌ 実質永久不検出 |
| vol_surge_detector × Tokyo × q3 | 不明 | 不明 | **baseline 計測必要** ⚠️ |

**🚨 Critical Caveat**: 本 implementation の spread quintile cuts (`compute_spread_quintile()` の **static cuts** [0.4, 0.6, 0.8, 1.2]) は Phase 4d-II の **dynamic per-(pair, session) quintile** とは異なる可能性が高い。Wave 1 R2-A は Phase 4d-II の **proxy** であり厳密な replication ではない。

---

## 1. Cell-Level Power Calculation

### 1.1 数学的根拠

Bonferroni-corrected detectable ΔWR (β=0.20, baseline avg=0.258):

```
Δ_detectable(N, K) = (z_{α/K} + z_β) × √(p(1-p)/N)
where α=0.05, K=4 (cells), p=0.258 (avg baseline)
```

scipy.stats で計算:

| N/cell | K=4 ΔWR detect | K=1 (single, no Bonferroni) |
|--------|----------------|------------------------------|
| 30 | 24.63pp | 19.86pp |
| 50 | 19.08 | 15.39 |
| 80 | 15.08 | 12.16 |
| 100 | 13.49 | 10.88 |
| 150 | 11.01 | 8.88 |
| 200 | 9.54 | 7.69 |

### 1.2 Cell 別必要 N

R2-A suppress (confidence ×0.5) で entry 数が半減すると仮定すると、**baseline restore (suppress 後 cell の WR が baseline cell の WR に近づく)** が期待効果。検出に必要な ΔWR と N:

```python
# Verification calculation (scipy.stats)
def required_n(target_delta, baseline=0.258, alpha=0.05, beta=0.20, K=4):
    a_corr = alpha / K
    z_a = stats.norm.ppf(1 - a_corr)
    z_b = stats.norm.ppf(1 - beta)
    # Iterate to find minimum N
    for n in range(20, 2000, 5):
        se = math.sqrt(baseline * (1 - baseline) / n)
        d = (z_a + z_b) * se
        if d <= target_delta:
            return n
    return None
```

| Cell | WR (R2-A 抑制対象) | baseline | Δ 目標 | 必要 N/cell (K=4) |
|------|--------------------|----------|--------|--------------------|
| stoch_trend_pullback × Overlap × q2 | 7.7% | 24.4% | **16.7pp** | **N≥70** |
| sr_channel_reversal × London × q3 | 15.0% | 27.1% | **12.1pp** | **N≥125** |
| ema_trend_scalp × London × q0 | 17.0% | 21.4% | **4.4pp** | **N≥940** ⚠️ |
| vol_surge_detector × Tokyo × q3 | 30.4% | 不明 | — | — ⚠️ |

### 1.3 Quant 重大 insight

1. **ema_trend_scalp × London × q0 は実質永久不検出**: Δ=4.4pp で N=940/cell 必要 = 約 **6 ヶ月** (Track ⑤ §5.6 の N 蓄積天井理論と整合)
2. **vol_surge_detector × Tokyo × q3** は Phase 4d-II で baseline 未明示 → baseline 計測しないと効果検証不可
3. **stoch×Overlap×q2 (Δ=16.7pp) と sr_ch×London×q3 (Δ=12.1pp) のみ**が 1-2 週間で検出可能
4. → Wave 1 R2-A 効果の科学的検出は **2 cells に限定**、残 2 cells は計測限界外と事前確定

---

## 2. Implementation vs Phase 4d-II の整合性検証 (Critical Caveat)

### 2.1 spread quintile 実装の差分

**Wave 1 R2-A 実装** (`modules/strategy_category.py:compute_spread_quintile`):
```python
_SPREAD_QUINTILE_CUTS = {
    "USD_JPY": [0.4, 0.6, 0.8, 1.2],   # static cuts
    "EUR_USD": [0.4, 0.6, 0.8, 1.2],
    "GBP_USD": [0.8, 1.2, 1.6, 2.4],
    "EUR_JPY": [0.6, 0.9, 1.2, 1.6],
}
```

**Phase 4d-II (推定)** (`tools/edge_lab.py:quintile_bin` 経由):
- `quintile_bin(value, cuts)` を使用、cuts は **dynamic per-(pair, session)** で計算
- 実 trade data の spread 分布を 5 等分する (Phase 4d 母集団 N=1804)

### 2.2 sqlite-fx 検証 (local DB N=373)

| 戦略 | Total N (local DB) | Phase 4d-II 主張 N (cell) | Spread 分布 |
|------|--------------------|----------------------------|-------------|
| stoch_trend_pullback | 14 | ≥40 (cell × Overlap × q2 で WR 7.7%) | 0.8-1.3 |
| sr_channel_reversal | 20 | ≥40 (cell × London × q3 で WR 15.0%) | 0.8-1.3 |
| ema_trend_scalp | 69 | ≥40 (cell × London × q0 で WR 17.0%) | 0.8-1.3 |
| vol_surge_detector | 7 | ≥24 (cell × Tokyo × q3 で WR 30.4%) | 0.8-1.3 |

**Pre-deploy 期間 (04-19〜04-25) で R2-A 4 cells に該当する trades**:
- stoch_trend_pullback × Overlap × q2: **N=1** (WR=100%)
- 他 3 cells: **N=0**

→ **本 implementation の static cuts では R2-A 対象 cell に該当する trade がほぼ存在しない**。Phase 4d-II の dynamic quintile では 40+ trades が該当するのに対し、static 換算では 1-数件のみ。

### 2.3 影響評価

3 つの可能性:

**仮説 A**: Wave 1 R2-A は事実上 **no-op** (該当 trades が稀)
- リスク: 計測しても "効果なし" となるが、それは R2-A が機能していないだけで Phase 4d-II の suppress 仮説自体は未検証
- 検証方法: Phase γ (+24h) で reasons log の "R2-A suppress" 出現件数を観察、0 ならこの仮説

**仮説 B**: Wave 1 R2-A は別 cells を suppress している (collateral suppress)
- リスク: 期待しない cell の entry が抑制され、baseline cell の WR を下げる可能性
- 検証方法: 非 R2-A cells の WR 分布を Pre-Post 比較

**仮説 C**: Phase 4d-II の cell 定義が実は静的 cuts ベースで、本 implementation と整合
- リスク: なし、計測通常進行
- 検証方法: Phase 4d-II 結果ファイルで `quintile_bin` の cuts 引数を確認

### 2.4 Quant 推奨 action

**現時点の判断**: 仮説 A が最有力 (local DB の証拠が支持)。

**Action**:
1. Phase γ (+24h) で reasons log の "R2-A suppress" 件数を観察
2. **0 件ならば**: Wave 1 R2-A は no-op として、別途 Phase 4d-II の dynamic quintile cuts で再実装する PR を準備 (Wave 2 Day 3+)
3. **数件以上発火しているならば**: 通常通り Phase α-η の計測 schedule で進行

→ **U18 として未解決問題に登録**: "Wave 1 R2-A の spread quintile cuts と Phase 4d-II の整合性検証"

---

## 3. Treatment / Control Design

### 3.1 Treatment cells (4)

R2-A suppress 対象。confidence ×0.5 が適用される。

| # | strategy | session (canonical) | spread_q | baseline WR | 抑制中 WR |
|---|----------|----------------------|----------|--------------|-----------|
| 1 | stoch_trend_pullback | Overlap | q2 | 24.4% | 7.7% |
| 2 | sr_channel_reversal | London | q3 | 27.1% | 15.0% |
| 3 | ema_trend_scalp | London | q0 | 21.4% | 17.0% |
| 4 | vol_surge_detector | Tokyo | q3 | (不明) | 30.4% |

### 3.2 Control cells (per strategy, 同戦略 × 別 cell)

各戦略の non-suppressed cells を control とし、Wave 1 deploy で **WR が変化しない** ことを副作用検証として確認:

| strategy | Treatment cell | Control cells (非 R2-A) |
|----------|----------------|--------------------------|
| stoch_trend_pullback | Overlap × q2 | Tokyo / London / NewYork × q0/q1/q3/q4 (15 cells) |
| sr_channel_reversal | London × q3 | Overlap / Tokyo / NewYork × q0-q4 (15 cells) |
| ema_trend_scalp | London × q0 | Overlap / Tokyo / NewYork × q1-q4 (15 cells) |
| vol_surge_detector | Tokyo × q3 | London / Overlap / NewYork × q0-q4 (15 cells) |

### 3.3 Pre-Post baseline (Wave 1 deploy 前後比較)

- **Pre period**: 2026-04-19 〜 2026-04-25 (deploy 前 1 週間)
- **Post period**: 2026-04-27 21:00 UTC 〜 (Sydney 再オープン以降)
- **比較指標**:
  - Treatment cells の entry 数 (Post で減少期待: confidence ×0.5 で entry filter 通過減)
  - Treatment cells の WR (Post で baseline cell の WR に近づく期待)
  - Control cells の WR / entry 数 (Post で **変化なし** が副作用なしの証拠)

---

## 4. 計測 Schedule と Statistical Milestone

| Phase | timing (JST) | 目標 | 統計的 milestone | Action |
|-------|--------------|------|------------------|--------|
| α | +6h (04-27 06:00) | Sydney/Tokyo 開始 | qualitative: reasons log の "R2-A suppress" 出現確認 (0 件 → 仮説 A 確定 → U18 緊急対応) | 観察のみ |
| β | +12h (04-27 12:00) | Tokyo full session, ~10-30 trades | descriptive: confidence 分布シフト、Treatment cells の N | 観察のみ |
| γ | **+24h (04-27 24:00)** | 1 trading day, ~50 trades | **initial: stoch×Overlap×q2 N≥10 partial CI** + reasons log Treatment 件数の dispatch 確認 | **U18 仮説判定** |
| δ | +72h (04-30 02:00) | 3 days, ~150-200 trades | **stoch×Overlap×q2 N≥30 で K=4 Bonferroni p<0.0125 partial 検定** | initial assessment |
| ε | +7 days (05-04) | 1 週間, ~350-400 trades | **stoch×Overlap×q2 N≥70 で baseline-restore 検定** | **Phase 3 GO/NO-GO 1st 判断** |
| ζ | +14 days (05-11) | 2 週間, ~700-800 trades | **sr_ch×London×q3 N≥125 で baseline-restore 検定** | full effect assessment |
| η | +30 days (05-27) | 1 ヶ月 | 全 4 cells で initial assessment、ema_trend_scalp は不検出限界の確認 | long-term comprehensive |

### 4.1 各 Phase での具体的 SQL 雛形

**Phase α (+6h, qualitative)**:
```sql
-- Wave 1 deploy 後の trade 件数 + R2-A suppress reasons log 出現確認
SELECT
    COUNT(*) as n_trades,
    SUM(CASE WHEN reasons LIKE '%R2-A suppress%' THEN 1 ELSE 0 END) as n_r2a_suppressed,
    GROUP_CONCAT(DISTINCT entry_type) as strategies_fired
FROM demo_trades
WHERE entry_time >= '2026-04-26T14:18:00Z'
  AND status='CLOSED'
  AND instrument NOT LIKE '%XAU%';
```

**Phase γ (+24h, R2-A target cells N + WR)**:
```sql
WITH classified AS (
    SELECT entry_type, instrument, spread_at_entry, outcome, pnl_pips, confidence,
        CASE
            WHEN CAST(strftime('%H', entry_time) AS INT) BETWEEN 13 AND 16 THEN 'Overlap'
            WHEN CAST(strftime('%H', entry_time) AS INT) BETWEEN 9 AND 12 THEN 'London'
            WHEN CAST(strftime('%H', entry_time) AS INT) BETWEEN 0 AND 6 THEN 'Tokyo'
            ELSE 'Other'
        END AS session,
        -- NOTE: Wave 1 implementation uses static cuts; Phase 4d-II may use dynamic
        CASE
            WHEN spread_at_entry <= 0.4 THEN 'q0'
            WHEN spread_at_entry <= 0.6 THEN 'q1'
            WHEN spread_at_entry <= 0.8 THEN 'q2'
            WHEN spread_at_entry <= 1.2 THEN 'q3'
            ELSE 'q4'
        END AS spread_q,
        CASE WHEN reasons LIKE '%R2-A suppress%' THEN 1 ELSE 0 END as r2a_applied
    FROM demo_trades
    WHERE entry_time >= '2026-04-26T14:18:00Z'
      AND status='CLOSED'
      AND instrument NOT LIKE '%XAU%'
)
SELECT entry_type, session, spread_q, r2a_applied,
       COUNT(*) as n,
       SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END) as wins,
       ROUND(100.0 * SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END) / COUNT(*), 1) as wr_pct,
       ROUND(AVG(confidence), 1) as avg_conf
FROM classified
WHERE (entry_type='stoch_trend_pullback' AND session='Overlap' AND spread_q='q2')
   OR (entry_type='sr_channel_reversal' AND session='London' AND spread_q='q3')
   OR (entry_type='ema_trend_scalp' AND session='London' AND spread_q='q0')
   OR (entry_type='vol_surge_detector' AND session='Tokyo' AND spread_q='q3')
GROUP BY entry_type, session, spread_q, r2a_applied
ORDER BY entry_type, session, spread_q;
```

### 4.2 副作用検証 (Phase γ, control cells)

```sql
-- 非 R2-A cells の WR が変化していないか
WITH classified AS (
    SELECT *, ... -- session/spread_q classification
    FROM demo_trades
    WHERE status='CLOSED'
      AND instrument NOT LIKE '%XAU%'
      AND entry_type IN ('stoch_trend_pullback','sr_channel_reversal','ema_trend_scalp','vol_surge_detector')
),
pre_period AS (
    SELECT entry_type, session, spread_q,
           COUNT(*) as n_pre, SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END) as wins_pre
    FROM classified
    WHERE entry_time BETWEEN '2026-04-19' AND '2026-04-26T14:18:00Z'
    GROUP BY entry_type, session, spread_q
),
post_period AS (
    SELECT entry_type, session, spread_q,
           COUNT(*) as n_post, SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END) as wins_post
    FROM classified
    WHERE entry_time >= '2026-04-26T14:18:00Z'
    GROUP BY entry_type, session, spread_q
)
SELECT pre.entry_type, pre.session, pre.spread_q,
       n_pre, wins_pre,
       n_post, wins_post,
       ROUND(100.0 * wins_pre / NULLIF(n_pre,0), 1) as wr_pre,
       ROUND(100.0 * wins_post / NULLIF(n_post,0), 1) as wr_post
FROM pre_period pre
LEFT JOIN post_period post USING (entry_type, session, spread_q)
ORDER BY pre.entry_type, pre.session, pre.spread_q;
```

---

## 5. Confounder 制御

### 5.1 Market Regime
- VIX / volatility regime: 同期間のマクロ環境を Pre-Post 対照
- 大きなマーケット event (FOMC, NFP) のタイミング確認
- BOJ 介入リスク (USD/JPY 158-160 帯では介入観測必要)

### 5.2 Session × Pair distribution shift
- 期間内の各 session の trade 件数比率が均一か検証
- pair 別の active mode が deploy 前後で変わっていないか (CLAUDE.md: scalp_eurjpy が Stopped 等の変更履歴確認)

### 5.3 Day-of-week effect
- Wave 1 deploy が weekend、計測初週は Mon-Fri
- 比較 Pre period (04-19 Sat 〜 04-25 Fri) も Mon-Fri trade のみで対照

### 5.4 ema_trend_scalp Live N=0 問題
- Wave 1 Day 1 deep dive で確認済: ema_trend_scalp は **Live N=0** (全 Shadow)
- → ema_trend_scalp × London × q0 の R2-A は **Shadow trades のみ** に適用される
- → 影響は Live PnL ではなく Shadow data quality のみ
- 計測時に `is_shadow=1` で filter する必要あり

---

## 6. Phase 3 GO/NO-GO 判断基準

### 6.1 GO 基準 (ε = +7 days で評価)

以下すべてを満たす:
- ✅ stoch×Overlap×q2 で **baseline-restore 検出** (Δ ≥ +16.7pp で K=4 Bonferroni p < 0.0125)
- ✅ Wave 1 副作用なし (control cells の WR 顕著変化なし、|ΔWR| < 5pp)
- ✅ reasons log に "R2-A suppress" 出現確認 (≥10 件)
- ✅ Pre-Post period で confounder (regime, session distribution) の差が小さい

### 6.2 HOLD 基準 (ε で N 不足ならば ζ まで継続)

- N が必要 N に達していないが、trend は positive direction
- Bonferroni 通過しないが Wilson 95% lower が baseline 方向にシフト
- Action: Phase ζ (+14 days) まで継続観測

### 6.3 NO-GO 基準

以下のいずれか:
- ❌ Phase γ (+24h) で R2-A suppress 出現 0 件 (= 仮説 A: implementation no-op、U18 必須)
- ❌ Phase γ で control cells の WR 顕著低下 (副作用)、|ΔWR| ≥ 10pp
- ❌ Phase ε で stoch×Overlap×q2 が baseline-restore 反対方向 (WR が 7.7% よりさらに低下)

### 6.4 Phase 3 BT 着手判断との接続

- ε (+7 days) で GO ならば Phase 3 BT GO/NO-GO 判断材料の一つ
- Phase 3 BT は他にも gating あり: U13/U14 friction calibration final (60+ days passive)、pre-reg LOCK 文書 (Wave 2 Day 2 A)
- Wave 1 monitor は Phase 3 BT 着手の **必要条件** だが **十分条件ではない**

---

## 7. Limitations & Caveats

### 7.1 Statistical limitations

1. **多重検定 K=4 cells のみ**: pair × session × strategy の cross product まで含めると K は爆発的に増加。本 analysis は cell-level に限定
2. **Pre-Post quasi-experimental design**: RCT ではなく、market regime の自然実験。confounders 完全排除は不可
3. **N=940 限界 (ema_trend_scalp)**: Δ=4.4pp は constructive な期待値だが、検出する物理的時間が長すぎる
4. **vol_surge_detector baseline 不明**: Phase 4d-II で baseline 未明示、独立検定不能

### 7.2 Implementation limitations

1. **Spread quintile cuts mismatch (U18)**: Phase 4d-II の dynamic per-pair quintile と Wave 1 implementation の static cuts が異なる可能性
2. **ema_trend_scalp Live N=0**: Live 効果は実質計測不能、Shadow only
3. **Friction model (U13/U14) との交絡**: friction multiplier 変更がない状態で R2-A 効果のみ計測する想定だが、Wave 1 deploy 期間中に他のシステム変更が起きると分離困難

### 7.3 Action items

| Item | Trigger | Responsible Phase |
|------|---------|---------------------|
| U18 (spread quintile mismatch) | Phase γ で R2-A suppress 0 件 | Wave 2 Day 3+ で別 PR |
| ema_trend_scalp 永久不検出 (本 analysis) | 既知の制約として受容 | Phase 3 BT 設計から除外検討 |
| vol_surge_detector baseline 計測 | Phase 4d-II 再分析 | 別セッション |

---

## 8. References

- 本 Plan: `/Users/jg-n-012/.claude/plans/fx-edge-reset-curried-ritchie.md`
- Wave 1 deploy 状況: `wiki/learning/wave1-monitoring-status.md`
- R2-A 実装: `modules/strategy_category.py:apply_r2a_suppress_gate, compute_spread_quintile`
- R2-A 4 cells 出所: `knowledge-base/wiki/analyses/phase4d-II-nature-pooling-result-2026-04-26.md`
- Phase 4d session×spread routing: `knowledge-base/wiki/analyses/phase4d-session-spread-routing-result-2026-04-26.md`
- 数学根拠: Track ⑤ §5.4-5.6 (Bonferroni / Power calc)、`fx-fundamentals.md`
- demo_trades.db (sqlite-fx): N=373 closed FX-only post-cutoff
