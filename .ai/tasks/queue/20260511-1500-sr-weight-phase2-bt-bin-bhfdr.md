---
id: 20260511-1500-sr-weight-phase2-bt-bin-bhfdr
title: "[SR-Weight-Phase2] SR strength bin × forward PnL の BH FDR 検証 (BT-based, 6 戦略 × 5 bin)"
owner: codex
status: queued
priority: P1
created_at: 2026-05-11T15:00:00+0900
roadmap_gate: "W4-EDA「思想は正、設計は誤」91% の典型 SR 系 6 戦略を bin で discriminate。strength>=0.X cell が生きていれば re-promote 候補。Gate 1 (Aggregate Kelly > 0) 突破ルート"
rule: R1
related:
  - modules/indicators.py
  - strategies/daytrade/dual_sr_bounce.py
  - strategies/daytrade/sr_anti_hunt_bounce.py
  - strategies/daytrade/dt_sr_channel_reversal.py
  - strategies/daytrade/sr_channel_reversal.py
  - strategies/daytrade/sr_fib_confluence.py
  - strategies/daytrade/strong_sr_breakout.py
  - data/cache/massive/*.parquet
  - tools/r2_tier1_hour_bucket_extension.py (BT runner 参照)
  - .ai/decisions/2026-05-11-1430-sr-weight-phase1-postdeploy-accept.md
---

# 0. 背景

Phase 1 (commit 364027e) で `oanda_audit` に SR weight 5 列 (`sr_strength`, `sr_touches`, `sr_days_span`, `sr_is_strong`, `sr_distance_atr`) が追加・反映済 (decision 2026-05-11-1430)。

しかし `0208ba8 R2 Critical 12 cell shadow demote registry` で sr_channel_reversal × {EUR_USD,USD_JPY}, sr_fib_confluence × {EUR_JPY,GBP_JPY,USD_JPY} 等が **audit-only** mode (shadow_emit_signals skip + _tick_entry block) になり、demo_trades にも記録されないため **forward PnL が観測不能**。Live shadow による N 蓄積経路は閉塞。

司令塔判断 (2026-05-11): **BT-based bin analysis (案 B)** で先行検証。Phase 2 の目的は「strength bin の **構造的差異検証**」であり、Live edge magnitude 計測ではない。memory `feedback_shadow_first_quant_architecture` の「BT = sanity filter」位置付けで十分。

W4-EDA メモリ (`project_w4_eda_complete_2026_05_05`): SR 系 6 戦略は 91% 「思想は正、設計は誤」群の典型。bin で discriminate できれば `strength>=0.7` cell は re-promote 候補、`<0.7` は永続 demote 確定 → Tier 1/2 の re-balance で α 源確保。

# 1. 仕様

## 1.1 対象 6 戦略 × ペア (W4-EDA 既出 + tier-master 整合)

| 戦略 | pair scope (BT 対象) | 現 tier |
|---|---|---|
| `dual_sr_bounce` | EUR_USD, GBP_USD, USD_JPY | PHASE0_SHADOW (rolling EV=-2.486) |
| `sr_anti_hunt_bounce` | EUR_USD, GBP_USD, USD_JPY | PHASE0_SHADOW |
| `dt_sr_channel_reversal` | EUR_JPY (PAIR_PROMOTED), EUR_USD, USD_JPY | mixed |
| `strong_sr_breakout` | EUR_USD, GBP_USD, USD_JPY | inline legacy |
| `sr_channel_reversal` | EUR_USD, GBP_USD, USD_JPY | FORCE_DEMOTED + Shadow demoted |
| `sr_fib_confluence` | EUR_USD, GBP_USD, USD_JPY (+ JPY pairs) | mixed + Shadow demoted |

EUR_JPY / GBP_JPY 等の JPY クロスも、戦略が ALLOWED_PAIRS に含めていれば対象。

## 1.2 データソース必須 (memory `feedback_bt_must_use_massive`)

**MUST**: `data/cache/massive/{PAIR}_{TF}.parquet` を使用。Yahoo 禁止 (60d 制限で 365d BT 不可)。

`BT_MODE=1 BT_REQUIRE_MASSIVE_CACHE=1` を環境変数で設定 (既存 BT runner 規約)。

不在 parquet があれば task abort、必要 fetch を司令塔に上申。

## 1.3 BT 設定

- **期間**: 365d (rolling window: 直近 365 日)
- **TF**: 各戦略の native TF (`strategies/daytrade/*.py` の `interval` 属性に従う)
- **Friction**: `bt_friction_model_v3` (Spread/SL Gate + RANGE TP + Quick-Harvest) — production と整合
- **Gate chain**: spread_sl_gate / Q4 gate / Phase0 gate を本番と同じ順序で適用 (post-gate-chain EV を取得)

## 1.4 sr_strength 計算 (memory `feedback_codex_schema_hallucination` — schema 直貼)

`modules/indicators.py:330` `find_sr_levels_weighted()` (signature 想定、Codex は実装を **必ず読んで確認** すること):

```python
def find_sr_levels_weighted(
    df: pd.DataFrame,           # OHLCV with at least 'high', 'low', 'close'
    lookback_days: int = 60,    # SR detection window
    cluster_atr_pct: float = 0.3,  # cluster tolerance
    min_touches: int = 2,
) -> List[Dict]:
    """
    Returns list of SR levels with keys:
      - price (float)
      - strength (float, 0..1)
      - touches (int)
      - days_span (float)
      - is_strong (bool, strength >= 0.7)
      - distance_atr (float, distance from current price in ATR units)
    """
```

各 signal について **signal 直前の OHLCV** で `find_sr_levels_weighted()` を呼び、entry 価格に最も近い SR level の `strength`/`touches`/`days_span`/`is_strong`/`distance_atr` を記録。

戦略コードを **再現実装しない** — 戦略の `evaluate()` を呼んで Candidate 取得、その時点の bar index で `find_sr_levels_weighted()` を別途呼ぶ pattern。

## 1.5 Bin 定義 (pre-registration)

`sr_strength` を **5 bin** に分割 (pre-reg 厳守、post-hoc 調整禁止):

| Bin | strength 範囲 | 想定意味 |
|---|---|---|
| B1 | [0.0, 0.5) | 弱い (touches=2-3, recent only) |
| B2 | [0.5, 0.65) | 弱中 |
| B3 | [0.65, 0.75) | 中 |
| B4 | [0.75, 0.85) | 中強 |
| B5 | [0.85, 1.0] | 強 (touches>=5, 長期持続) |

## 1.6 統計仕様 (memory `feedback_partial_quant_trap` 完全準拠)

各 戦略 × pair × bin × direction (BUY/SELL) cell について:

| metric | 算出 |
|---|---|
| N | signal count |
| WR | win rate |
| EV (pip) | mean P&L (post-friction) |
| PF | profit factor = sum(wins) / abs(sum(losses)) |
| Kelly (full) | (WR×R - (1-WR)) / R, R=avg_win/avg_loss |
| Wilson 95% lower | scipy.stats.binom_conf_interval or 手計算 |
| Sharpe | mean / std × sqrt(252) |
| DSR | Bailey & Lopez de Prado (`dsr_overall` 既存実装参考) |
| WF folds 3+ pos_ratio | 3-fold walk-forward の positive-EV fold 比率 |

戦略レベル aggregate も同じ metric を出力。

## 1.7 BH FDR 検証 (pre-reg)

### Within-strategy bin discrimination (primary)

各戦略について 5 bin の P&L 分布が **strength 単調増加** か検証:

1. 各 bin の per-trade P&L 配列 (post-friction) を抽出
2. H0: 5 bin の P&L 分布は同一 (Kruskal-Wallis test)
3. H1: P&L は strength に対し単調増加 (Jonckheere-Terpstra trend test)
4. **BH FDR** (Benjamini-Hochberg, q=0.10) を 6 戦略 × 1 trend test = m=6 で適用

Trend test p < q_BH ⇒ そのstrategy の bin discrimination は **有意**。

### Across-strategy (secondary)

`is_strong=True` (strength>=0.7) vs `is_strong=False` の単純 2-bin で 6 戦略合算:
- H0: 2-bin の P&L は同一
- Mann-Whitney U test, Bonferroni m=6 (n_strategies)

## 1.8 Acceptance gate (Codex 規律)

ACCEPT 条件:
1. 6 戦略 × 5 bin で **N≥30/cell が最低 1 つ** (構造的に N が出ない設計なら CHANGES_REQUESTED で上申)
2. 全 metric (N/WR/EV/PF/Kelly/Wilson/Sharpe/WF) 出力済
3. trend test p-value × 6、Mann-Whitney p-value × 6 計算済
4. BH FDR / Bonferroni 補正後の survivor リスト出力
5. Final report に **per-strategy verdict** (BIN_DISCRIMINATION_VALID / NULL) を明記

不通過 → commit せず `final.md` に CHANGES_REQUESTED 報告。**push しない** (司令塔 review 待ち)。

## 1.9 Output artifacts

- `bt-results/sr-weight-phase2-bin-bhfdr-2026-05-11.json` (per-cell metric + p-values)
- `bt-results/sr-weight-phase2-bin-bhfdr-2026-05-11.md` (human-readable summary)
- `.ai/runs/<run-dir>/final.md` (Codex 規律 verdict)

## 1.10 NOT in scope (司令塔判断後の別タスク)

- 実装変更 (cell promote/demote) — bin discrimination 結果から司令塔が判断
- Live shadow 経路の再開 (案 A) — BT 結果次第で別 task
- Phase 3 (Live re-promotion) — BH FDR 通過 + 司令塔 R1 LOCK 後

# 2. クオンツ規律 (Codex 自己検証)

- **データ分離**: BT のみ。Live / Shadow / OANDA は触らない、混入禁止
- **memory `feedback_codex_mock_test_trap`**: mock-only test pass ではなく **MASSIVE 実データで BT 実行** が必須
- **memory `feedback_codex_stash_leak`**: 最終 step で **必ず git commit、stash しない**。「ACCEPT」report は repo persist してから報告すること
- **memory `feedback_partial_quant_trap`**: N/WR/EV/PF/Kelly/Wilson/Bonferroni/WF 全て出力必須
- **memory `feedback_label_empirical_audit`**: 「ロジック問題ないか?」 と code-deduction で結論しない、必ず BT 実測 metric で判定

# 3. 失敗 / 上申条件

- MASSIVE cache 不在 ペア × TF → fetch 必要、abort + 司令塔に上申
- 戦略 evaluate() が BT 環境で動かない (依存欠落等) → 個別 strategy を skip、final.md に明記
- 構造的に N=0 になる cell → null result として記録、棄却ではなく "INSUFFICIENT_BT_N" verdict

