# FX AI Trader — 独立クオンツ監査プロンプト

あなたはヘッジファンドのリスク委員会に所属する独立クオンツアナリストです。
以下のアルゴトレードシステムについて、開発チームが行った2つの分析と改善施策を**第三者の視点で監査**してください。

## あなたの役割
- 開発チームの結論に同意する義務はありません。データが示すことだけに基づいてください
- 「攻撃は最大の防御」という開発チームの哲学を尊重しつつも、それがリスク管理として適切かを独立に判断してください
- 見落とされているリスク、過大評価されている機会、論理の飛躍があれば明確に指摘してください

---

## システム概要

- FX自動売買システム（USD/JPY, EUR/USD, GBP/USD, EUR/JPY, EUR/GBP, XAU/USD）
- アーキテクチャ: Flask + SQLite + OANDA v20 API (本番口座)
- 3層構造: LIVE（実弾）/ Sentinel（0.01lot観測）/ Shadow（デモ記録のみ）
- タイムフレーム: 1m scalp / 5m scalp / 15m daytrade / 1h breakout / 4h swing
- 戦略数: 約30（うちFORCE_DEMOTED=停止が約半数）
- 稼働期間: 約2ヶ月
- Fidelity Cutoff: 2026-04-08（SLTPバグ修正後のクリーンデータ起点）

## 4原則（開発チームの哲学）
1. マーケット開いてる間は攻める — トレード機会を逃すのが最大の敵
2. デスゾーン = スプレッド異常（動的検出）のみ — 静的時間ブロック禁止
3. 攻撃は最大の防御 — 防御フィルターの積み上げよりデータ蓄積を優先
4. カーブフィッティング禁止 — パラメータ調整は完了、本番データ蓄積フェーズ

---

## データA: 本番リスクダッシュボード（全718トレード）

```
システム全体:
  N = 718 trades
  WR = 39.42%
  Kelly = 0.0 (edge = -0.3799) → 数学的にはノーベット
  Monte Carlo ruin probability = 85.58% (5000 sim, 300 forward trades)
  VaR(95%) = 10.1pip, CVaR(95%) = 89.91pip → CVaR/VaR比 = 8.9x (極度Fat Tail)
  
DD状態:
  eq_peak = +51.5pip, eq_current = -1508.1pip
  DD = 1,559.6pip
  defensive_mode = true, lot_multiplier = 0.2x

PnL Attribution:
  gross_pnl = -2,849.1pip
  avg_friction = 7.04pip/trade
  total_friction = 5,058.2pip
```

### 戦略別Kelly（N≥10のみ有効）
| 戦略 | N | WR | edge | Kelly | 備考 |
|------|---|-----|------|-------|------|
| vol_momentum_scalp | 11 | 72.7% | +0.498 | 47.0% | 唯一の正Kelly |
| stoch_trend_pullback | 23 | 47.8% | +0.011 | 0.97% | 辛うじて正 |
| bb_rsi_reversion | 全N | 46.2% | -0.244 | 0% | 全ペア混合 |
| fib_reversal | 全N | 37.3% | -0.115 | 0% | バグ期間含む |
| ema_cross | 全N | 32.6% | -0.238 | 0% | |
| ema_pullback | 全N | 37.0% | -0.534 | 0% | XAU shadow含む |
| macdh_reversal | 全N | 36.4% | -0.512 | 0% | |
| sr_fib_confluence | 全N | 26.1% | -0.392 | 0% | |
| inducement_ob | 全N | 10.0% | -0.867 | 0% | |

### 相関行列（|r|>0.7のみ抜粋）
| ペア | r | 意味 |
|------|---|------|
| bb_rsi ↔ bb_squeeze | -0.842 | 極度の負相関（レジーム切替の鏡像） |
| sr_break_retest ↔ sr_channel_reversal | +0.916 | ほぼ同一（冗長） |
| h1_fib_reversal ↔ stoch_trend_pullback | +0.946 | ほぼ同一 |
| ema_trend_scalp ↔ orb_trap | +0.851 | 両方トレンドフォロー |
| inducement_ob ↔ orb_trap | +0.875 | inducement_obはorb_trapの劣化版 |
| ema_pullback ↔ engulfing_bb | -0.802 | |
| macdh_reversal ↔ vol_surge_detector | -0.777 | |
| pivot_breakout ↔ vol_surge_detector | +0.890 | |

---

## データB: Current Window Stats（155トレード）

**注意: is_shadowフィルターが未適用。Shadow/Demo-onlyトレードが混入している。**

| 戦略 | N | WR | PnL(pip) | 状態 |
|------|---|-----|----------|------|
| bb_rsi_reversion | 50 | 34.0% | -304.3 | LIVE (PAIR_PROMOTED×USD_JPY) |
| ema_pullback | 25 | 48.0% | -496.0 | FORCE_DEMOTED (XAU shadow) |
| vol_momentum_scalp | 9 | 77.8% | +17.4 | Sentinel |
| ema_trend_scalp | 9 | 44.4% | +179.6 | Shadow (XAU) |
| dt_bb_rsi_mr | 9 | 33.3% | -7.9 | Sentinel |
| fib_reversal | 8 | 25.0% | -12.5 | FORCE_DEMOTED |
| engulfing_bb | 7 | 14.3% | -353.5 | DISABLED (Shadow混入) |
| vol_surge_detector | 7 | 57.1% | +2.7 | Sentinel |
| bb_squeeze_breakout | 6 | 66.7% | +18.7 | LIVE |
| sr_fib_confluence | 6 | 16.7% | -41.9 | FORCE_DEMOTED |
| sr_channel_reversal | 5 | 0.0% | -10.9 | Shadow |
| gold_trend_momentum | 3 | 66.7% | -1136.0 | Sentinel (XAU) |
| dt_sr_channel_reversal | 2 | 100% | +17.0 | Shadow |
| stoch_trend_pullback | 2 | 0.0% | -8.9 | Sentinel |
| trend_rebound | 2 | 50.0% | +1.3 | DISABLED |
| macdh_reversal | 1 | 0.0% | -292.0 | FORCE_DEMOTED |
| orb_trap | 1 | 100% | +18.2 | SHIELD Whitelist |
| sr_break_retest | 1 | 0.0% | -8.6 | Shadow |
| trendline_sweep | 1 | 100% | +23.4 | FORCE_DEMOTED |
| lin_reg_channel | 1 | 100% | +8.8 | FORCE_DEMOTED |
| **合計** | **155** | **40.6%** | **-2385.4** | EV = -15.39pip/trade |

---

## データC: CLAUDE.md記録のペア×戦略粒度データ

### 本番556tクオンツ監査（pre-Fidelity Cutoff）
- 25戦略中 PF > 1 は **bb_rsi_reversion × USD_JPY のみ**（N=123, WR=54.7%, +54.8pip, PF=1.13）
- DT全体 WR=29%（損益分岐WR=44%）
- sr_fib_confluence: N=40, WR=28.9%, -92.8pip（BT WR=64%との36pp乖離）
- LOSS 90.6%のMFE=0（一度も順行せずSL）

### Post-Fidelity Cutoff（2026-04-08以降、クリーンデータ）
| 戦略 | N(post) | WR | PnL | 変化 |
|------|---------|-----|-----|------|
| bb_rsi_reversion | 23 | 52.2% | +36.6p | pre 54.7%と整合 |
| fib_reversal | 20 | 55.0% | +35.6p | pre 25.6%→劇的改善 |
| stoch_trend_pullback | 4 | 25.0% | -9.3p | |
| dt_bb_rsi_mr | 3 | 0.0% | -10.2p | |
| macdh_reversal | 3 | 33.3% | +0.3p | |
| scalp 1m (全体) | 37 | 54.1% | +68.7p | |

### BT統合データ（v5.95, 摩擦モデルv2）
- Scalp bb_rsi: 181t WR=61.3% EV=+0.173 ATR
- DT orb_trap: USD/JPY 29t WR=79.3% EV=+0.617, EUR/USD 42t WR=71.4% EV=+0.482
- DT htf_false_breakout: GBP/USD 40t WR=72.5% EV=+1.011
- DT gbp_deep_pullback: 38t WR=73.7% EV=+0.543
- DT adx_trend_continuation: EUR/USD 14t WR=85.7% EV=+2.045

### 摩擦耐性（BEV_WR計算済み）
| ペア | TF | Spread | ATR | BEV_WR | bb_rsi実績WR | マージン |
|------|-----|--------|-----|--------|-------------|---------|
| USD/JPY | 1m | 0.7pip | 5pip | 34.4% | 52-55% | +18pp |
| EUR/USD | 1m | 0.7pip | 3pip | 39.7% | 20% (DEMOTED) | -19.7pp |
| GBP/USD | 1m | 1.3pip | 5pip | 37.9% | ~40% | +2.1pp |
| EUR/GBP | 15m | 1.5pip | 3.5pip | 57.1% | 12.5% | -44.6pp |

---

## 開発チームの分析結論（あなたが監査すべき対象）

### Tier分類
| Tier | 戦略 | 根拠 |
|------|------|------|
| **Tier 1 (Core Alpha)** | bb_rsi×USD_JPY | 556t中唯一PF>1, post-cut WR=52.2% |
| **Tier 1 (最高優先昇格)** | orb_trap | BT WR=79.3%, 摩擦マージン+50pp |
| **Tier 1** | htf_false_breakout | BT GBP WR=72.5% EV=+1.011 |
| Tier 2 (復活) | fib_reversal | post-cut WR=55% (pre: 25.6% → パラメータ改善効果) |
| Tier 2 | gbp_deep_pullback | BT WR=73.7% |
| Tier 2 | adx_trend_continuation | BT WR=85.7% (N=14のみ) |
| Tier 3 | macdh_reversal | BT WR=63%だが本番34.7%。rehab条件付き |
| Tier 4 (廃棄) | inducement_ob, ema_ribbon_ride, sr_fib_confluence, engulfing_bb 等 | |

### 即時アクション（合意済み）
1. orb_trap: N≥10到達で PAIR_PROMOTED 昇格
2. fib_reversal: N≥30, WR≥50%で SENTINEL 昇格
3. vol_momentum_scalp: lot boost 2.0x→1.0x（N=11で信頼区間が広すぎる）
4. TP再設定: MFE 75%タイルベース（現在TP到達率8%）
5. bb_squeeze_breakout: 停止確認（BT EV=-0.799 ATR）
6. UTC 7-8 DT: ADX≥25追加フィルター（z=0.88で非有意）

### v8.3で実施した即死率改善
| 戦略 | 修正内容 | 期待効果 |
|------|---------|---------|
| bb_rsi | 確認足(陽陰線)+TREND逆張りブロック+ADX<15排除 | 即死率77.6%→20-25%, WR→58-62% |
| fib_reversal | Fib階層化+MACD-H必須+body0.60 | 即死率75.9%→25-35%, WR→60-65% |
| ema_pullback | バウンスATR×0.2+三重確認+body0.35 | 即死率72.2%→30-35%, WR→45-50% |

### FORCE_DEMOTED 7戦略の再審査結果
開発チームの結論: **「7戦略中、今すぐ復活させるべき戦略はゼロ。macdh_reversalのみ条件付きrehab候補。」**

---

## 監査で回答してほしい項目

### A. データの信頼性
1. 全718t中のShadow/Demo混入が分析をどの程度歪めているか
2. Post-cutoff N=23のbb_rsi WR=52.2%と、Current window N=50のWR=34%の矛盾をどう解釈するか
3. vol_momentum_scalp Kelly=47%はN=11で信頼できるか（CIの幅を定量的に）

### B. Tier分類の妥当性
4. bb_rsi×USD_JPYを「Tier 1」とすることは、post-cut N=23のデータで十分な根拠か
5. orb_trapをBTデータのみで「Tier 1最高優先昇格」とすることのリスクは何か
6. fib_reversalの「復活」判断（pre: WR=25.6%→post: WR=55%）は、パラメータ改善の効果か偶然の揺らぎか

### C. 見落とされているリスク
7. Monte Carlo破産確率85.58%の状態で「攻撃は最大の防御」哲学を維持することは合理的か
8. CVaR/VaR比=8.9x（正規分布なら1.6x）のテールリスクの真の原因は何か
9. eq_peak=51.5pip（システムがほぼ一度も利益圏に出ていない）が示すシステム設計上の根本問題は何か

### D. アクションプランの評価
10. 提案された6つの即時アクションの優先順位は適切か
11. v8.3の即死率改善（確認足フィルター等）は「カーブフィッティング禁止」原則と矛盾しないか
12. 破産確率85%からの現実的な脱出パスとして、提案されたロードマップ（bb_rsi維持+orb_trap昇格+fib復活）は十分か、それとも根本的な再設計が必要か

### E. 開発チームへの独立勧告
13. あなたがリスク委員会の立場なら、このシステムに対して何を勧告するか（継続/縮小/停止/条件付き継続）
14. 最も価値のある改善に1つだけ工数を使えるとしたら、何に使うべきか
