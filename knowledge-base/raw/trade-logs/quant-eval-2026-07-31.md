# Quant Evaluation: 2026-07-31 — shadow 含む全数監査 + 勝ちセル条件抽出

- **データ**: `/api/demo/trades?status=closed` 全ページング取得 (date_from=2026-04-08)。
  **closed 14,329 行** (2026-04-08〜07-31)、重複除去済み。API 実測値のみ (推測ゼロ)。
- **バケット 3 分割** (feedback_live_vs_shadow_strict_separation 準拠):
  live = `oanda_trade_id != ''` / shadow = `is_shadow=1` / other = 残余
- **依頼**: shadow 含む全実績抽出 → 勝ち戦略条件抽出 → 勝率改善

## 1. Bucket Totals (post-cutoff)

| bucket | N | WR | EV (p/t) | PnL | PF |
|---|---|---|---|---|---|
| live | 565 | 46.3% | −1.030 | −582.2p | 0.66 |
| shadow | 13,758 | 39.3% | −1.510 | −20,780.7p | 0.64 |
| other | 6 | 66.7% | −189.2 | −1,135.0p | 0.17 |

### Live 月次 (M1 指標: 月次符号転換)
| 月 | N | PnL | EV |
|---|---|---|---|
| 2026-04 | 360 | −230.7p | −0.64 |
| 2026-05 | 57 | **+14.8p** | +0.26 |
| 2026-06 | 121 | −281.9p | −2.33 |
| 2026-07 | 27 | −84.4p | −3.13 |

### 7 月 live 反実仮想 (出血源の分解)
| 系列 | WR | PnL | N |
|---|---|---|---|
| 実績 | 53.8% | −84.4p | 27 |
| − 修正済みバグ経路 (07-01/02 watchdog 再武装: bb_rsi×11, xs_momentum_rsi, trendline_sweep) | 40.0% | −52.1p | 11 |
| − さらに ny_close (Grail #19) + vix pilot | 50.0% | **−7.6p** | 4 |

→ **既知修正済みバグ + ny_close + vix を除けば 7 月 live は −7.6p** = M1 まで残り一歩。
残余 −7.6p の内訳: dt_bb_rsi_mr×GBP_USD −6.8 (N=1) / orb_trap −3.6 (N=1) / ps AUD_JPY +0.6 / vsg EUR_JPY +2.2。

## 2. 現役 live 経路の診断 (06-01 以降に発火した経路)

| 経路 | 最終発火 | N (06-01〜) | PnL | 判定 |
|---|---|---|---|---|
| vix_carry_unwind×USD_JPY (Overlap pilot) | 07-30 | 14 | −53.3p | ⚠️ **user 決裁事項** (下記 §5) |
| ny_close_reversal×USD_JPY (Grail #19) | 07-15 | 3 | −10.2p | ❌ **R2 撤去執行** ([[grail19-ny-close-removal-2026-07-31]]) |
| price_shock_rev ×5 (carve-out) | 07-29 | 1 | +0.6p | ✅ 意図された 8 セル体制 |
| weekend_gap_fade ×3 | (イベント待ち) | 0 | — | ✅ 次回 08-02 |
| ema200_trend_reversal (Grail #1) | 06-12 | 2 | −11.2p | ⚠️ 監視 (live 累計 N=4 WR25% −17.5p、shadow は Bonf PASS) |
| vol_surge_detector (Grail #4) | — | — | live 累計 N=26 −9.4p | ⚠️ N≥30 で再判定 |
| その他 (bb_rsi/trendline/xs_momentum_rsi 等) | 07-02 以前 | — | — | 停止済み/バグ修正済みの残骸 |

## 3. Shadow 勝ちセル (N≥30, 102 セル中)

### EV>0 の片側 t 検定 + WR vs BEV 二項検定 (いずれも Bonferroni m=102, α=4.9e-4)

| セル | N | WR (Wilson lo) | EV | PnL | PF | EV t-test p | WR vs BEV p | 月次符号 |
|---|---|---|---|---|---|---|---|---|
| sr_anti_hunt_bounce×EUR_JPY | 65 | 73.4% (61.5) | +4.47 | +290.5 | 2.66 | 2.9e-3 | **2.2e-11 ✅** | 2/4 (04:−65 05:+326 06:−24 07:+54) |
| donchian_momentum_breakout×NZD_USD | 37 | 77.8% (61.9) | +7.65 | +283.0 | 3.48 | 1.5e-3 | **4.2e-6 ✅** | 3/3 |
| ema200_trend_reversal×USD_JPY | 79 | 59.7% (48.6) | +1.04 | +82.4 | 1.43 | 0.115 | **2.6e-6 ✅** | 3/4 |
| orb_trap×GBP_USD | 33 | 70.0% (52.1) | +6.88 | +226.9 | 5.19 | **8e-5 ✅** | **3.0e-4 ✅** | 2/4 (07 月 −18) |
| dt_bb_rsi_mr×EUR_USD | 98 | 54.0% (43.6) | +1.68 | +164.3 | 1.73 | 0.012 | 4.4e-3 | **4/4 (唯一の全月正)** |
| wick_imbalance_reversion×EUR_USD | 92 | 56.4% (45.4) | +2.22 | +204.5 | 2.07 | 8.1e-3 | 1.9e-3 | 2/4 |
| ob_retest×USD_JPY | 75 | 50.0% (38.6) | +1.25 | +93.8 | 1.34 | 0.176 | 4.4e-3 | 3/3 |
| vix_carry_unwind×USD_JPY | 179 | 44.4% (37.2) | +1.79 | +320.0 | 1.20 | 0.226 | — | **2/4 減衰型** (04:+537 → 05:−98 06:+5 07:−123) |
| mqe_gbpusd_fix×GBP_USD | 87 | 47.1% | +1.81 | +157.3 | 1.30 | 0.113 | — | ⚠️ **04 月のみ、以後 emit ゼロ (死線)** |

### 勝ちセルの条件分解 (エッジの所在)
- **sr_anti_hunt_bounce×EUR_JPY**: **BUY 片側** (BUY N=57 WR80% +329p / SELL N=8 WR25% −39p)。
  Tokyo 集中 (N=35 WR71% +300p)。mtf `trend_up_weak` が弱点 (N=9 WR22% −98p)
- **donchian×NZD_USD**: **BUY 100%** (全 37 件 BUY)。`range_wide` +268p。全セッション正
- **ob_retest×USD_JPY**: **BUY +130p vs SELL −36p**。overlap WR75% +94p / **london WR25% −67p が毒**。`range_wide` WR83%
- **orb_trap×GBP_USD**: SELL 主体 (N=27 WR71% +207p)。**overlap (12-16) N=23 WR80% +196p にエッジ集中**
- **wick_imbalance×EUR_USD**: **BUY 単独** (SELL N=2)。london+overlap +202p / ny WR23% −20p
- **ema200_trend_rev×USD_JPY**: overlap WR82% +121p / `range_tight` +103p。tokyo −40p
- **dt_bb_rsi_mr×EUR_USD**: ny WR100% +70p、overlap WR61% +76p。方向両対応 (SELL 57%/BUY 48%)

**横断パターン**: ①勝ちセルはほぼ全て**方向片側性** (エッジは direction-conditional)。
②**Overlap (12-16 UTC) が横断的勝ち時間帯** (7 セル中 6 で正)。③ mtf `range_wide`/`range_tight`
の適合はセル依存 — 集約 regime でなくセル×regime 粒度が必須 (既存 lesson と整合)。

## 4. 母集団レベル条件マイニング (shadow, 06-01 以降, N_decided=6,429, m=24, Bonf α=2.1e-3)

| 条件 | N | ΔWR | p | 判定 |
|---|---|---|---|---|
| confidence≥70 | 2,528 | **+5.0pp** | 5e-7 | ✅ Bonf PASS — ただし PnL は依然負 (WR≠EV) |
| confidence<55 | 1,382 | **−5.5pp** | 4e-5 | ✅ Bonf PASS |
| spread>1.5 | 1,192 | +5.9pp | 4e-5 | ✅ PASS だが **PnL 大幅負 → フィルタ化禁止** (高スプレッド≠高EV) |
| session=tokyo | 1,317 | −3.8pp | 6e-3 | nominal |
| mtf=range_tight | 1,824 | +3.1pp | 8e-3 | nominal |
| session=late (21-24) | 126 | −11.7pp | 9e-3 | nominal |

**注**: 2026-04-22 TP-hit 分析では confidence は WIN と**負相関**だった。現データでは**正に反転**
(Bonferroni PASS) — 06-12 以降の bb_rsi 系停止で低品質 emit が除かれた影響と推定。KB 矛盾として記録。

## 5. ⚠️ Warnings / user 決裁事項

1. **vix_carry_unwind×USD_JPY pilot**: live 累計 N=26 PnL −46.9p PF0.66、月次 3/4 負
   (04:−21.3 / 05:+27.7 / 06:−19.0 / 07:−34.3)。shadow エッジは 04 月 +537p をピークに
   3 ヶ月連続で減衰 (05〜07 累計 −216p / n=139)。**07-07 user 裁定で「demote は user 決裁」
   + checkpoint (live SELL N≥20 or 08-31)**。checkpoint 未達 (N≈14) だが証拠悪化が顕著 —
   **早期 demote を推奨、user 判断待ち**。demote 時は pilot 撤去 + PAIR_DEMOTED 復帰。
2. **mqe_gbpusd_fix×GBP_USD (PAIR_PROMOTED #8)**: shadow emit が 2026-04 で完全停止
   (n=87 全て 4 月)。発火経路の死線調査が必要。
3. **donchian_momentum_breakout×NZD_USD/NZD_JPY**: D-c-2 (07-28 user 決裁) で shadow 維持
   (365d BT FAIL CI 全負) だが、**forward shadow は N=37 WR77.8% BEV 対比 Bonf PASS + 3/3 月正**。
   BT と forward の矛盾 — 「TV Pine > Python BT」の既存教訓と同型の可能性。
   **shadow N≥50 到達時に D-c-2 再審 (R1) を提案**。
4. **other バケット 6 行で −1,135p** (1 行平均 −189p) — weekend_gap 无タグ shadow artifact
   (07-26 バグ時代) 等。集計時は必ず除外すること。

## 6. Next Actions

| # | Action | Rule | Status |
|---|---|---|---|
| 1 | Grail #19 ny_close live 経路撤去 | R2 | ✅ 本 PR で執行 |
| 2 | vix pilot 早期 demote 提案 | user 決裁 | 📋 §5-1 提示 |
| 3 | sr_anti_hunt_bounce×EUR_JPY BUY×Tokyo の R1 pre-reg 起案 (365d cell-conditional BT + LOCK) | R1 | 提案 (最有力: BEV 対比 p=2e-11) |
| 4 | ema200×USD_JPY / orb_trap×GBP_USD×Overlap×SELL R1 パケット候補 (orb は lesson-orb-trap-bt-divergence 留意) | R1 | 候補 |
| 5 | dt_bb_rsi_mr×EUR_USD: 4/4 月正だが Bonf 未達 → shadow N 蓄積継続 (N≥130 目安で再検定) | — | 蓄積 |
| 6 | mqe_gbpusd_fix emit 死線調査 | R3 候補 | 未着手 |
| 7 | Grail #1 ema200 live セル監視 (live N=4 WR25% — N=10 で R2 再判定) | R2 監視 | 登録 |
