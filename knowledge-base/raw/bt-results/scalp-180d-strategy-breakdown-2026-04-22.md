# Scalp 180d BT — Strategy × TF Breakdown (post htf_agreement fix)

**実施日**: 2026-04-22
**データ**: `bt-scalp-180d-2026-04-22.json` + `bt-scalp-180d-jpy-postfix-2026-04-22.json` (JPY 4 cells は post-fix 側で上書き)
**Friction**: BT 内で spread/slippage 適用済み
**目的**: Scalp 全体 EV=-0.289 (1m) / -0.121 (5m) が構造的負 EV である理由を戦略別に分解し、driver を特定する。

## 結論 Summary
1. **ema_trend_scalp** が単独で損失の **37.6%** を占める最大 driver (N=5726, PnL=-1384pip)。Live では既に FORCE_DEMOTED 済だが Scalp BT では依然稼働扱いで計上されている → BT/Live 定義乖離を wiki/analyses/bt-live-divergence.md に追記候補。
2. 上位 3 戦略 (ema_trend_scalp / bb_rsi_reversion / fib_reversal) だけで損失の **70.4%**。
3. **N ≥ 100 の全 10 戦略が負 EV**。Scalp 全体の負 EV は、個別 cell の外れ値ではなく **構造的** (spread/slippage > 小幅 edge)。
4. 唯一の正 EV は v_reversal (N=32 EV=+0.002)、実質ゼロ。Scalp scope で稼げる戦略は存在しないのが 180d 実測。
5. 修正後の vwap_mean_reversion は N=36 まで回復したが、EV=-0.113 で 5m 版 (N=5 EV=+0.429) にのみ兆候 — 365d 延長 BT で追試必須。

## Strategy Total (1m+5m combined)
| Strategy | N | WR% | EV | PnL (pip) | Loss share |
|---|--:|--:|--:|--:|--:|
| ema_trend_scalp | 5726 | 58.3 | -0.242 | -1383.8 | 37.6% |
| bb_rsi_reversion | 2627 | 46.3 | -0.332 | -873.3 | 23.7% |
| fib_reversal | 1060 | 48.2 | -0.316 | -335.2 | 9.1% |
| sr_channel_reversal | 1603 | 58.4 | -0.191 | -306.1 | 8.3% |
| engulfing_bb | 795 | 56.0 | -0.265 | -210.8 | 5.7% |
| vol_momentum_scalp | 769 | 59.6 | -0.236 | -181.7 | 4.9% |
| vol_surge_detector | 393 | 53.9 | -0.427 | -167.8 | 4.6% |
| macdh_reversal | 211 | 49.3 | -0.410 | -86.6 | 2.4% |
| stoch_trend_pullback | 500 | 60.6 | -0.145 | -72.5 | 2.0% |
| bb_squeeze_breakout | 379 | 65.4 | -0.090 | -34.2 | 0.9% |
| three_bar_reversal | 22 | 54.6 | -0.281 | -6.2 | 0.2% |
| mtf_reversal_confluence | 104 | 61.5 | -0.059 | -6.1 | 0.2% |
| trend_rebound | 80 | 65.0 | -0.069 | -5.6 | 0.1% |
| vwap_mean_reversion ✨ | 36 | 55.5 | -0.113 | -4.1 | 0.1% |
| confluence_scalp | 6 | 50.0 | -0.602 | -3.6 | <0.1% |
| ema_pullback | 6 | 50.0 | -0.425 | -2.5 | <0.1% |
| **v_reversal (唯一正)** | 32 | 62.5 | +0.002 | +0.1 | — |

✨ = post-fix 修正で発火復活した戦略

## TF Aggregate
| TF | N | WR | EV | PnL |
|---|--:|--:|--:|--:|
| 1m | 11,566 | 55.1% | **-0.289** | -3342.4 |
| 5m | 2,783 | 56.4% | **-0.121** | -337.5 |

- 1m vs 5m で EV 差 +0.168、PnL 差 -3005 pip。
- **5m は 1m の 41% に EV 損失が収まる** → 5m 側でノイズが希釈されて友好的。Scalp scope を 5m 中心に再設計する方向性は将来検討候補（データ駆動、lesson-reactive-changes 遵守のため 365d BT が前提）。

### Live-proxy Aggregate (FORCE_DEMOTED 7 strategies 除外後)
FORCE_DEMOTED: `ema_pullback`, `fib_reversal`, `macdh_reversal`, `engulfing_bb`, `sr_channel_reversal`, `stoch_trend_pullback`, `ema_trend_scalp`

| TF | N | WR | EV | PnL |
|---|--:|--:|--:|--:|
| 1m | 3,429 | 51.0% | **-0.338** | -1159.6 |
| 5m | 1,019 | 54.5% | **-0.121** | -122.9 |

**反直感的な発見**: FORCE_DEMOTED を除外すると Scalp 1m EV は **-0.289 → -0.338 と悪化**、WR も 55.1% → 51.0% に低下。

#### 解釈
- FORCE_DEMOTED 戦略 (特に ema_trend_scalp 58.3% WR) は「損は出すが WR は比較的高い群」 — 除外すると残存戦略側の WR 50% 付近のノイズが支配的になる
- Live の FORCE_DEMOTED フィルタは "損失の流出を止める" 施策として機能するが、残存戦略だけで Scalp が勝てるわけではない
- **5m (-0.121) は FORCE_DEMOTED 除外で値変化なし** → 5m scope は既に非デモート戦略中心で構成されている → 5m Scalp 再設計の方向性は依然有望
- 1m Scalp は FORCE_DEMOTED で何を除外しても構造的負 EV、signal 自体の問題ではなく **friction > edge per trade** の時間軸問題

## Top 10 負 cell (pair × tf × strategy, N ≥ 10)
| Pair | TF | Strategy | N | WR% | EV | PnL |
|---|---|---|--:|--:|--:|--:|
| GBPUSD | 1m | ema_trend_scalp | 846 | 46.3 | -0.795 | -672.7 |
| USDJPY | 1m | ema_trend_scalp | 993 | 56.9 | -0.308 | -306.2 |
| GBPUSD | 1m | bb_rsi_reversion | 327 | 37.3 | -0.837 | -273.7 |
| EURUSD | 1m | ema_trend_scalp | 661 | 57.5 | -0.288 | -190.7 |
| USDJPY | 1m | bb_rsi_reversion | 466 | 47.2 | -0.381 | -177.6 |
| EURJPY | 1m | ema_trend_scalp | 1085 | 60.9 | -0.140 | -151.9 |
| GBPUSD | 1m | vol_momentum_scalp | 200 | 51.0 | -0.659 | -131.8 |
| EURJPY | 1m | bb_rsi_reversion | 397 | 43.8 | -0.314 | -124.6 |
| GBPUSD | 1m | sr_channel_reversal | 180 | 50.6 | -0.619 | -111.4 |
| GBPUSD | 1m | fib_reversal | 132 | 40.9 | -0.740 | -97.7 |

**GBPUSD 1m が 4/10 を占める** — friction 4.53pip (最大) × 1m 高ノイズ環境で edge が消失している構造。

## 解釈 (Analysis → Judgement)
- **構造的問題**: Scalp 1m は friction (0.7-1.3pip spread + 0.5-1pip slip) が edge と同オーダーで、個別戦略の WR 45-60% 程度では recover 不能。
- **ema_trend_scalp は再確認**: Live で既に FORCE_DEMOTED、BT でも -0.242 EV で最大 driver — 既存 demotion 判断は fresh BT で追確証された。
- **5m scope の可能性**: 1m の -0.289 から 5m -0.121 への改善は friction per trade 一定で edge (movement) が時間軸拡大で増える構造と整合。ただし結論を出すには cell 数不足 (5m の N 合計 2,783 は 1m 11,566 の 24%)。
- **今すぐ打てる手**: 存在しない。lesson-reactive-changes により、この 180d 結果だけでは Scalp FORCE_DEMOTED / scope 再定義は保留。365d BT を次セッションで実行後に判断。

## Next Actions
- [ ] 365d × Scalp BT で本分解を再確認（実行時間見積もり 1.5-2h）
- [ ] 5m scope だけの walk-forward で正 EV 戦略が自然発生するか検証
- [x] ema_trend_scalp は Live FORCE_DEMOTED 済だが、Scalp BT の `_compute_scalp_signal_v2` が FORCE_DEMOTED を respect しているか確認 → **respect していない** (app.py grep 済み、L5266-L5297 の QUALIFIED_TYPES にはあるが FORCE_DEMOTED check なし)。BT/Live 乖離 #7 候補として記録済み
- [x] Scalp vwap_mr 5m (N=5 EV+0.429) を 365d 延長で真偽判定 → **N=9 EV=+0.427 で signal 維持**（下記 Addendum 参照）

## Addendum: 365d × 5m × JPY 延長 BT 結果 (2026-04-22 17:55 JST)

`raw/bt-results/bt-scalp-5m-365d-jpy-2026-04-22.json` (1180s 総時間)

### vwap_mean_reversion 5m の追跡
| TF Window | Pair | N | WR | EV | PnL |
|---|---|--:|--:|--:|--:|
| 180d | EUR_JPY | 2 | 100.0% | +0.874 | +1.7 |
| **365d** | **EUR_JPY** | **4** | **100.0%** | **+0.839** | **+3.4** |
| 180d | GBP_JPY | 3 | 66.7% | +0.132 | +0.4 |
| **365d** | **GBP_JPY** | **5** | **60.0%** | **+0.098** | **+0.5** |
| **365d 合計** | JPY 2pair | **9** | 77.8% | **+0.427** | +3.9 |

**判定**: 2ヶ月延長で N 5→9 (+4)、signal は消えず方向一致。ただし **N ≥ 20 未達で Live 実装判断は引き続き保留** (lesson-reactive-changes)。
EURJPY 100% WR は "signal 発火稀 × 2σ mean reversion が効く日を選ぶ" 性質と整合。

### 365d × 5m Overall 結果
| Pair | N | WR | EV | PnL |
|---|--:|--:|--:|--:|
| EUR_JPY | 1,206 | 56.6% | -0.075 | — |
| **GBP_JPY** | **1,300** | **60.2%** | **+0.026** | **+33.8** |

**重要**: GBP_JPY 5m Overall EV = **+0.026** — Scalp scope で 365d ベースの「正 EV cell」を確認（180d postfix +0.019 → 365d +0.026、persistence あり）。この cell を driver 分解すると:

### GBPJPY 5m driver rank (365d, N≥15 のみ)
| Strategy | N | WR | EV | PnL | Tier |
|---|--:|--:|--:|--:|---|
| ema_trend_scalp | 464 | 64.7% | +0.087 | +40.1 | ⚠️ Live FORCE_DEMOTED（global）だが JPY 5m で正 EV |
| mtf_reversal_confluence | 17 | 82.4% | +0.609 | +10.3 | LOT_BOOST 1.3x |
| vol_surge_detector | 39 | 69.2% | +0.219 | +8.5 | PAIR_PROMOTED 候補 |
| stoch_trend_pullback | 45 | 64.4% | +0.144 | +6.5 | Live FORCE_DEMOTED だが JPY 5m 正 EV |
| sr_channel_reversal | 147 | 61.2% | +0.010 | +1.4 | Live FORCE_DEMOTED |
| fib_reversal | 123 | 56.1% | +0.005 | +0.6 | Live FORCE_DEMOTED |
| bb_rsi_reversion | 308 | 52.3% | -0.065 | -19.9 | 唯一の大 N 負 driver |

### EURJPY 5m driver rank (365d, N≥15 のみ)
| Strategy | N | WR | EV | PnL | Tier |
|---|--:|--:|--:|--:|---|
| vol_momentum_scalp | 83 | 72.3% | +0.287 | +23.8 | LOT_BOOST 1.0x |
| vol_surge_detector | 31 | 71.0% | +0.276 | +8.6 | |
| mtf_reversal_confluence | 14 | 71.4% | +0.271 | +3.8 | |
| bb_squeeze_breakout | 29 | 65.5% | +0.068 | +2.0 | PAIR_PROMOTED×USD_JPY |
| ema_trend_scalp | 419 | 59.4% | -0.071 | -29.6 | Live FORCE_DEMOTED |
| bb_rsi_reversion | 274 | 49.3% | -0.130 | -35.6 | |

### 365d 延長 BT の含意
1. **5m scope JPY は構造的正 EV に近い**: GBPJPY +0.026 / EURJPY -0.075 → 平均 -0.02、180d の -0.04 から改善。「1m Scalp は死 / 5m Scalp は境界的」の仮説を 365d で確認
2. **ema_trend_scalp の矛盾**: Live FORCE_DEMOTED だが GBPJPY 5m で +0.087 の正 EV driver — 全ペア集計での負 EV が JPY 5m に押し付けた injustice か、カーブフィッティングか要検証
3. **vwap_mr 5m は single-cell に pass 可能**: GBPJPY + EURJPY 合計 N=9 EV=+0.427 で 180d と方向一致。Live N 累積を継続観察（現実の Gate は N≥20 or 30）
4. **vol_momentum_scalp × EUR_JPY** (N=83 EV+0.287 WR=72.3%) は PAIR_PROMOTED 候補として注目 — 既存 LOT_BOOST 1.0x で Scalp Sentinel 該当確認要

## Source Script
`/tmp/scalp_ev_breakdown.py` (実行結果を本ファイルに転記)

## Related
- [[vwap-mean-reversion]]
- [[force-demoted-strategies]]
- [[bt-live-divergence]]
- [[lesson-reactive-changes]]
