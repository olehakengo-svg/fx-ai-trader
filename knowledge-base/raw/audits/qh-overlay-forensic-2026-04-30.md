# QH Overlay Forensic — 2026-04-30

## Method
- QH multiplier: **0.85** (matches demo_trader._QUICK_HARVEST_MULT)
- Data: Shadow CLOSED trades since `2026-04-16T08:00:00+00:00` (v9.1 FIDELITY_CUTOFF)
- Per trade: would_hit_qh = mafe_favorable_pips >= dist_qh_pips
- Cells with N ≥ 10: **8**
- Bonferroni α: 0.05 / 8 = 0.00625
- Total trades: **316**

## Venn Summary

| Group | Count | 解釈 |
|---|---|---|
| Both (raw ∧ qh promotable) | 0 | 真の Live 候補 (QH 適用後も edge 残存) |
| RAW only | 0 | **Live で QH に削られる楽観バイアス源** |
| QH only | 0 | EXEMPT 検討候補 (raw では届かないが QH なら通る) |
| Neither | 8 | promote 不可 (FORCE_DEMOTED 妥当性確認) |

### All cells (full table, sorted by raw EV) (8)

| entry_type | instrument | N | raw WR | raw Wlo | raw EV | raw PF | qh WR | qh Wlo | qh EV | qh PF | ΔWlo | ΔEV |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| dt_bb_rsi_mr | GBP_USD | 10 | 60.00% | 0.313 | +9.54 | 3.52 | 60.00% | 0.313 | +5.50 | 2.45 | +0.000 | -4.04 |
| fib_reversal | EUR_USD | 10 | 40.00% | 0.168 | -0.64 | 0.68 | 40.00% | 0.168 | -0.46 | 0.77 | +0.000 | +0.18 |
| ema_trend_scalp | EUR_USD | 25 | 20.00% | 0.089 | -1.25 | 0.50 | 20.00% | 0.089 | -1.27 | 0.49 | +0.000 | -0.02 |
| ema_trend_scalp | USD_JPY | 23 | 26.09% | 0.125 | -1.26 | 0.52 | 30.43% | 0.156 | -1.03 | 0.60 | +0.031 | +0.23 |
| ema_trend_scalp | GBP_USD | 23 | 26.09% | 0.125 | -1.40 | 0.62 | 26.09% | 0.125 | -1.69 | 0.54 | +0.000 | -0.29 |
| sr_channel_reversal | USD_JPY | 10 | 0.00% | 0.000 | -3.20 | 0.00 | 0.00% | 0.000 | -3.20 | 0.00 | +0.000 | +0.00 |
| sr_fib_confluence | GBP_USD | 11 | 27.27% | 0.097 | -11.90 | 0.27 | 36.36% | 0.152 | -9.91 | 0.35 | +0.054 | +1.99 |
| sr_break_retest | USD_JPY | 10 | 20.00% | 0.057 | -30.60 | 0.06 | 30.00% | 0.108 | -24.59 | 0.16 | +0.051 | +6.01 |

## 判定ロジック
- promotable := Wilson_lo > 0.5 AND Bonferroni p < 0.00625 AND EV > 0
- pnl_qh: would_hit_qh なら +dist_qh_pips、それ以外は min(pnl_raw, 0)

## 注意
- N が小さい (≥10) ため Wilson_lo は保守的。Phase 1 持続観測で N≥30 化を待つ
- raw WIN は構造的に qh WIN を含む (mafe ≥ dist_pips ≥ dist_qh_pips)
- QH only で WR_qh - WR_raw が大きいセルは TP 到達が遅延型のトレード分布
- pnl_qh の MISS 側に正の擬陽性が乗らない設計 (min(pnl_raw, 0))
- **dist_qh は entry_price 基準で計算 (spread 補正済み)** — qh_target_price は signal 基準だが MAFE は entry 基準で記録されるため

---

## Findings & Recommendation (analyst, v2 — entry-basis 補正後)

### 0. MAFE 擬陰性の真因 = forensic スクリプトのバグ（production 健全）

初版 forensic で raw WIN > qh WIN のセルが出現したため「MAFE 記録に race condition がある」と疑った。実態は:
- `qh_target_price = signal_price + 0.85 × (tp - signal_price)` (production と同じ)
- ただし MAFE / pnl は **entry_price 基準** で記録される (spread 約 1〜4 pips 込み)
- 初版は signal_price 基準で `dist_qh_pips` を計算していたため、平均 ~1.4 pip の擬距離超過が発生
- TP_HIT WIN trade のうち 14/69 (20%) が「signal 基準では mafe < dist_qh だが entry 基準なら ≥」のグレーゾーン

**production の MAFE 記録は健全**。post-v9.1 で WIN×mafe=0 の trade はゼロ (86/86 で mafe>0)。
別タスク化の必要なし。

### 1. ユーザー質問への直接回答 (補正後)
**「Shadow にも QH を入れた方が統計的優位ないか?」 → 現データでは引き続き NO**

- 8/8 セルが Bonferroni-adjusted promotion 基準を未達 (raw も qh も)
- Venn: both=0, raw_only=0, qh_only=0, neither=8
- 全戦略 FORCE_DEMOTED 状態 (2026-04-27 一括設定) によりサンプル N が薄い

### 2. EXEMPT 設計の妥当性（補正後はさらに強い）

唯一の +EV セル `dt_bb_rsi_mr GBP_USD` (raw EV=+9.54, WR=60%) で QH は EV を **-4.04 削る** (補正前 -2.88 → 補正後 -4.04)。spread 補正で QH の不利益がより明確化。

→ memory `feedback_ma_filter_breaks_mr` (MR 戦略保護) と整合: **dt_bb_rsi_mr GBP_USD は EXEMPT 候補として強く推奨**（現 EXEMPT 未登録）。N≥30 到達時に正式追加判定。

### 3. QH が EV を改善する非 EXEMPT セル
- `sr_break_retest USD_JPY`: ΔEV=+6.01 (raw -30.60 → qh -24.59)
- `sr_fib_confluence GBP_USD`: ΔEV=+1.99 (raw -11.90 → qh -9.91)

両方とも依然 **負 EV**。QH は損失緩和のみで promotion 候補化はしない。

### 4. Phase 1 進行可否判定
**Phase 1 (DB schema 追加 + double gate) は保留推奨**

理由:
- raw_only / qh_only が共にゼロ → double gate の分離力を発揮するシグナルなし
- ROI が低い: 現状の手動 EXEMPT で十分
- 代替: dt_bb_rsi_mr GBP_USD の EXEMPT 追加を Rule 2 で先行

再評価条件: アクティブセル復活 ＋ N≥30 を満たすセルが 5 以上揃った時点で再 Phase 0 → raw_only または qh_only が出現すれば Phase 1 着手

### 5. 補正履歴
- v1: signal_price 基準 → dt_bb_rsi_mr ΔEV=-2.88
- v2: entry_price 基準 (spread 補正) → dt_bb_rsi_mr ΔEV=-4.04 ← 採用