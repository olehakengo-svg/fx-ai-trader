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

## Current State (2026-04-14)

### Stage 6: PROMOTED (実弾運用中)
| Edge | Pairs | N(live) | WR | EV | Source |
|------|-------|---------|----|----|--------|
| orb_trap | JPY,EUR,GBP | 2 | 50% | insuff | BT WR=79% (v8.2) |
| session_time_bias | JPY,EUR,GBP | 0 | — | — | Breedon & Ranaldo 2013 |
| london_fix_reversal | GBP | 0 | — | — | Krohn 2024 |

### Stage 4: SENTINEL (Live shadow蓄積中)
| Edge | N(live) | WR | Notes |
|------|---------|----|-|
| vol_momentum_scalp | 12 | 66.7% | EV=+1.28, 最高WR |
| vol_surge_detector | 30 | 50.0% | WR低下傾向 (was 63.6%) |
| fib_reversal | 32 | 40.6% | Recovery path |
| liquidity_sweep | 0 | — | Osler 2003 stop-hunt |
| vol_spike_mr | 0 | — | BT JPY PF=1.92 |
| doji_breakout | 0 | — | BT JPY WR=75.9% |
| gotobi_fix | 0 | — | 発火窓=月6日 |
| vix_carry_unwind | 0 | — | 低頻度高インパクト |
| xs_momentum_dispersion | 0 (GBP/EUR promoted) | — | Eriksen 2019 |
| hmm_regime_overlay | 0 | — | 防御オーバーレイ |
| ema_pullback | 14 (JPY promoted) | 42.9% | EV=+1.09 |

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

### REJECTED (検証の結果棄却)
| Edge | Reason |
|------|--------|
| ヒゲ拒否シグナル | WR=26-44%, 摩擦負け (raw-alpha-mining A2) |
| 片側ヒゲ連続 | WR=42-46%, ランダム以下 (raw-alpha-mining B2) |
| 大足慣性フォロー | WR=52%, ほぼランダム (raw-alpha-mining A1) |
| Vol forecasting (options) | 機関投資家データ必須 (Bossens 2019) |
| NLP sentiment | 実装不可能 (Jia 2024) |

## Bottleneck Analysis (2026-04-14)

### 問題: Stage 4で停滞
- **10戦略がStage 4 (SENTINEL)** だが、N蓄積が進んでいない戦略が多い
- liquidity_sweep, vol_spike_mr, doji_breakout, gotobi_fix, vix_carry_unwind: 全てN=0
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
