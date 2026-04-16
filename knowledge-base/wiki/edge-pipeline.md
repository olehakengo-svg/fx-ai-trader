# Edge Pipeline — エッジ仮説の評価パイプライン

## 6-Stage Gate Process

| Stage | Name | Gate Criteria | Exit Action |
|-------|------|--------------|-------------|
| 1 | DISCOVERED | 学術文献 or データマイニングで仮説特定 | Hypothesis文書作成 |
| 2 | FORMULATED | エントリー/エグジット条件のコード化 | strategies/ にファイル作成 |
| 3 | BACKTESTED | BT N>=30, WR>BEV+5pp, Friction Model v3適用 | SENTINEL登録 |
| 4 | SENTINEL | Live shadow N蓄積（0.01lot相当） | N>=30 live到達 |
| 5 | VALIDATED | Live N>=30, Kelly>0, BT/Live乖離<15pp | PAIR_PROMOTED |
| 6 | PROMOTED | 実弾運用、Kelly Halfロット | 継続モニタリング |

## Current State (2026-04-16)

### Stage 6: ELITE_LIVE (実弾運用中、SHADOW免除)
| Edge | Pairs | N(live) | WR | EV | Source |
|------|-------|---------|----|----|--------|
| session_time_bias | JPY,EUR,GBP | 0 | — | — | Breedon & Ranaldo 2013 |
| trendline_sweep | EUR,GBP | — | — | — | BT 365d EUR EV=+0.93, GBP EV=+0.60 |
| gbp_deep_pullback | GBP | — | — | — | BT GBP EV=+1.06 |

### Stage 5: PAIR_PROMOTED (ペア限定実弾、Sentinel lot)
| Edge | Promoted Pairs | N(live) | WR | Notes |
|------|---------------|---------|----|-|
| orb_trap | JPY,EUR,GBP | 2 | 50% | BT WR=79% (v8.2), N<10 Sentinel免除 |
| london_fix_reversal | GBP | 0 | — | Krohn 2024, PAIR_PROMOTED×GBP_USD |
| vol_momentum_scalp | EUR_JPY | 12 | 66.7% | EV=+1.28, PAIR_PROMOTED (EUR_JPY 5m EV=+0.608) |
| xs_momentum | GBP,EUR | 0 | — | Eriksen 2019, PAIR_PROMOTED×GBP/EUR (JPY PAIR_DEMOTED) |
| ema_pullback | USD_JPY | 14 | 42.9% | EV=+1.09, FORCE_DEMOTED+PAIR_PROMOTED×JPY復活 |
| fib_reversal | EUR_USD | 32 | 40.6% | FORCE_DEMOTED+PAIR_PROMOTED×EUR (BT 1m EV=+0.426) |
| vix_carry_unwind | USD_JPY | 0 | — | PAIR_PROMOTED×JPY (BT EV=+0.212 N=49) |
| doji_breakout | GBP,JPY | 0 | — | PAIR_PROMOTED (BT GBP WR=78.3%, JPY WR=61.9%) |
| bb_squeeze_breakout | JPY,EUR,GBP_JPY | 0 | — | PAIR_PROMOTED (JPY 5m EV=+1.030最強) |
| post_news_vol | GBP,EUR | 0 | — | PAIR_PROMOTED (BT GBP EV=+1.762) |
| engulfing_bb | EUR_USD | 0 | — | PAIR_PROMOTED×EUR (FORCE_DEMOTED+EUR復活) |
| sr_channel_reversal | EUR_USD | 0 | — | FORCE_DEMOTED+PAIR_PROMOTED×EUR (5m EV=+0.231) |
| squeeze_release_momentum | EUR_USD | 0 | — | PAIR_PROMOTED×EUR (BT EV=+0.460) |
| vwap_mean_reversion | EUR_JPY,GBP_JPY,GBP,EUR | 0 | — | PAIR_PROMOTED, Bonferroni p<10^-7 |
| stoch_trend_pullback | GBP_JPY | 0 | — | FORCE_DEMOTED+PAIR_PROMOTED×GBP_JPY |
| macdh_reversal | EUR_JPY,GBP_JPY | 0 | — | FORCE_DEMOTED+PAIR_PROMOTED×JPYクロス |
| dt_fib_reversal | GBP_USD | 0 | — | PAIR_PROMOTED×GBP (BT WR=72.7% EV=+0.310) |

### Stage 4: SENTINEL (Live shadow蓄積中)
| Edge | N(live) | WR | Notes |
|------|---------|----|-|
| vol_surge_detector | 30 | 50.0% | WR低下傾向 (was 63.6%), SCALP_SENTINEL |
| bb_rsi_reversion | — | — | SCALP_SENTINEL (USD_JPY PAIR_DEMOTED) |
| liquidity_sweep | 0 | — | Osler 2003 stop-hunt, UNIVERSAL_SENTINEL |
| vol_spike_mr | 0 | — | BT JPY PF=1.92, UNIVERSAL_SENTINEL |
| gotobi_fix | 0 | — | 発火窓=月6日, UNIVERSAL_SENTINEL |
| eurgbp_daily_mr | 0 | — | EUR/GBP日足MR, UNIVERSAL_SENTINEL |
| v_reversal | 0 | — | 急落/急騰反転, UNIVERSAL_SENTINEL |
| trend_rebound | 0 | — | 強トレンド逆張り, UNIVERSAL_SENTINEL |
| london_close_reversal | 0 | — | ロンドンクローズ反転, UNIVERSAL_SENTINEL |
| dt_sr_channel_reversal | 0 | — | DT SR/チャネル反発, UNIVERSAL_SENTINEL |
| ema200_trend_reversal | 0 | — | EMA200ブレイクリテスト, UNIVERSAL_SENTINEL |
| post_news_vol | — | — | ニュース後ボラ, UNIVERSAL_SENTINEL (非promoted pairsのみ) |

### Stage 3: BACKTESTED (BT完了、結果待ち/判断待ち)
| Edge | BT Result | Next Action |
|------|-----------|-------------|
| (なし — BT完了分は全てStage 4に移行済み) | | |

### Stage 2: FORMULATED (コード実装済み、BT未完了)
| Edge | Code File | BT Status | Next Action |
|------|-----------|-----------|-------------|
| (なし — 実装済み分は全てBT済み) | | | |

### Stage 1: DISCOVERED (仮説のみ、未実装)
| Edge | Source | Priority | Est. EV | Next Action |
|------|--------|----------|---------|-------------|
| Month-end Fix flow | Melvin & Prins 2015 | MED | 不明 | 仮説定式化 |
| Month-end rebalancing | Harvey et al 2025 | LOW | 不明 | 仮説定式化 |
| Stock→FX cross-momentum | Iwanaga & Sakemoto 2024 | MED | 不明 | データ取得方法調査 |
| NY session USD sell bias | raw-alpha-mining C1 | LOW | +1.09pip | session_time_biasのNY版検討 |
| Open>Close vol asymmetry | Barardehi & Bernhardt 2025 | LOW | 不明 | orb_trap強化に使用可能 |

### FORCE_DEMOTED (OANDA停止、Demo Sentinel継続)
| Edge | Reason | PAIR_PROMOTED復活 |
|------|--------|------------------|
| sr_fib_confluence | v6.8: N=40 WR=28.9% -92.8pip, BT乖離確定 | なし |
| ema_cross | Phase1 降格 | なし |
| inducement_ob | Phase1 降格 | なし |
| ema_ribbon_ride | Phase2: EV=-2.75 | なし |
| h1_fib_reversal | Phase2: EV=-4.18 | なし |
| pivot_breakout | Phase2: EV=-8.56 | なし |
| lin_reg_channel | 負EV確定 | なし |
| dual_sr_bounce | 負EV確定 | なし |
| sr_break_retest | v7.0: N=2 EV=-21.4 | なし |
| ema_pullback | Phase3: WR=19%, EV=-0.77 | USD_JPY (Stage 5) |
| fib_reversal | v6.8: N=117 WR=39.6% PF<1 | EUR_USD (Stage 5) |
| macdh_reversal | v6.8: N=86 WR=34.7% PF<1 | EUR_JPY,GBP_JPY (Stage 5) |
| engulfing_bb | v8.0: N=7 WR=14.3% | EUR_USD (Stage 5) |
| bb_squeeze_breakout | v8.2: BT EV=-0.799 | JPY,EUR,GBP_JPY (Stage 5) |
| sr_channel_reversal | v8.9: N=17 WR=11.8% 即死率87.5% | EUR_USD (Stage 5) |
| stoch_trend_pullback | v8.9: N=19 WR=31.6% EV=-0.97 | GBP_JPY (Stage 5) |
| dt_bb_rsi_mr | v8.9: N=7 WR=14.3% EV=-4.09 | なし |

### REMOVED (戦略ではないもの)
| Edge | Reason |
|------|--------|
| hmm_regime_filter | ユーティリティモジュール（evaluate()常にNone）、戦略ではない |

### REJECTED (検証の結果棄却)
| Edge | Reason |
|------|--------|
| ヒゲ拒否シグナル | WR=26-44%, 摩擦負け (raw-alpha-mining A2) |
| 片側ヒゲ連続 | WR=42-46%, ランダム以下 (raw-alpha-mining B2) |
| 大足慣性フォロー | WR=52%, ほぼランダム (raw-alpha-mining A1) |
| Vol forecasting (options) | 機関投資家データ必須 (Bossens 2019) |
| NLP sentiment | 実装不可能 (Jia 2024) |

## Bottleneck Analysis (2026-04-16)

### 問題: Stage 4 (SENTINEL)で停滞
- 多くのUNIVERSAL_SENTINEL戦略がN=0のまま蓄積が進んでいない
- liquidity_sweep, vol_spike_mr, gotobi_fix, eurgbp_daily_mr, v_reversal, trend_rebound: 全てN=0
- **原因**: 発火条件が厳しい or 発火窓が狭い（gotobi_fix=月6日）

### 問題: Stage 1に5件が放置
- 仮説はあるがコード化されていない
- Month-end Fix flow は学術根拠が強い（Melvin & Prins 2015）が未着手

### Next Actions (優先順)
1. **N=0のSENTINEL戦略の発火頻度を確認** — コードは存在するが実際に信号が出ているか？出ていなければパラメータ調整 or デバッグ
2. **Month-end Fix flow の定式化** — 月末3営業日のFix前USDフロー。gotobi_fixと類似構造
3. **Stock→FX cross-momentum のデータ取得可能性調査** — 日経先物/S&P先物→通貨シグナル

## Related
- [[raw-alpha-mining-2026-04-12|Alpha Mining Results]]
- [[research-sweep-2026-04-12|Research Sweep]]
- [[changelog]] — 各戦略の実装バージョン
