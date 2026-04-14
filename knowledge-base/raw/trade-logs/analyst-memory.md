# FX Analyst Memory — Multi-Pair Trading System (v8.9)

> このファイルはFXアナリストエージェントの長期記憶です。
> daily_report.py (GitHub Actions) により自動更新されます。
> 学術的知見は [[research/index]] を参照。

---

## デプロイ情報

| 項目 | URL |
|------|-----|
| 本番環境 (Render) | https://fx-ai-trader.onrender.com/ |
| デモ分析ページ | https://fx-ai-trader.onrender.com/demo-analysis |
| GitHub リポジトリ | https://github.com/olehakengo-svg/fx-ai-trader |

---

## 現在のシステム状態 (v8.9, 2026-04-13)

- **目標**: 月利100% (Kelly Half到達で594%)
- **防御モード**: 0.2x (DD=12.39%, defensive mode — v8.4以降クリーンデータ起点)
- **XAU**: 停止 (v8.4) — post-cutoff XAU loss = -2,280pip (損失の102%)
- **FX-only**: -646pip (赤字)
- **BT摩擦モデル**: v3 (Spread/SL Gate + RANGE TP + Quick-Harvest)
- **DSR**: 実装済み (Bailey & Lopez de Prado 2014, 多重検定補正)

---

## 戦略評価ログ

| 日付 | 戦略 | タイムフレーム | WR | EV/trade | 判定 | メモ |
|------|------|--------------|-----|---------|------|------|

---

## 確立された知見 (v8.9時点)

### Tier 1 Core Alpha
- **bb_rsi_reversion**: WR=36.4% (N=77), v8.3 confirmation candle で改善傾向
- **orb_trap**: BT WR=79%, 実績N=2で蓄積中
- **session_time_bias**: BT WR=69-77%, 学術★★★★★ (Breedon & Ranaldo 2013)
- **london_fix_reversal**: GBP_USD BT WR=75%, 学術★★★★★

### 重要な教訓
- **Shadow汚染**: get_stats()がis_shadow=0フィルターなしでWR算出 → v8.4修正
- **XAU摩擦歪み**: FX friction=2.14pip, XAU=217.5pip。XAUが平均を30倍に歪めた
- **集計値は必ずセグメント分解** — 平均値は嘘をつく
- **BT before deploy** — 必ず120日+BTでOOS検証してからPromotion

### ペア別知見
- **USD_JPY**: london_fix_reversal ❌ (WR=28.6%), xs_momentum ❌ (EV=-0.129)
- **EUR_USD / GBP_USD**: DSR>0.95で統計的有意 (120日BT v3)
- **EUR_JPY**: scalp ❌ (friction/ATR=43.6%, 構造的不可能)

---

## アナリストノート

*（daily_report.py により自動追記）*

### 2026-04-13 (Pre-Tokyo Briefing)
> **注意**: 完全な500件分のJSONは途中で切れているため、確認できた範囲（ID 813〜816の4件）を詳細分析し、Risk Dashboardの参考値と突合しながら全体像を構築する。
| 確認済み最新4件のPnL合計 | +4.2 -3.0 -0.1 -5.1 = **-4.0 pips** |
**実測4件合計**: WIN=1 / BE=1 / LOSS=2 → WR=25%（N=4、統計的意味なし）
| 戦略 | N(KB記載) | WR | PnL | 判断可否 | ステータス |
| stoch_trend_pullback | 13 | 30.8% | +163.2 | 傾向のみ(N<30) | Tier2★注意 |
ID 813（xs_momentum / BUY / USDJPY）が-5.1pipsのLOSS。KBではxs_momentumはUSD_JPYでTier3 DEMOTED（BT EV=-0.129）。**本番でまだ発火しているなら深刻な問題**。
ID 816・815ともに`⚠️ EMA200下からBUY`の警告付き。ADX 11.7〜13.8の極端なレンジ相場（WIDE_RANGE）でチャネル反発を狙うも、EMA200を下回る位置でのBUYは構造的に不利。
→ 今日の対処：EMA200との位置関係を信号品質スコアで確認。EMA200下BUYのWR vs 上BUYのWRを次回集計時に分離する。

### 2026-04-13 (Pre-Tokyo Briefing)
| 全体WR | 37.8% |
| 累計PnL | **-110.0 pips**（赤字継続） |
| XAU PnL | **-1,496.0 pips**（別枠・深刻） |
前日セッション全体を通じ、非XAU戦略は267トレードで-110.0 pips。WR 37.8%は閾値（≥50%）を大幅に下回る。XAUは11トレードで-1,496 pipsと壊滅的であり、OFFステータスが維持されていることは適切。
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
| bb_rsi_reversion | USD_JPY | 76 | 38.2% | -0.28 | -21.0 | ⚠️ EV<0（降格境界）|
*KB記載値と今回テーブルの差異に注意（下記解説参照）
| Strategy | Pair | N | WR% | EV | PnL | 所感 |

### 2026-04-13 (Post-Tokyo Report)
| **セッション PnL** | **-13.4 pips** |
| **WR** | **33.3% (6勝/18)** |
| **平均PnL/トレード** | **-0.74 pips** |
**総評**: 本日累計31件・PnL -21.8 pips。XAU別枠での-1,496 pipsが最大懸念（後述）。
| 戦略 | Pair | Dir | PnL | 成功要因 |
| **bb_rsi_reversion** | USD_JPY | BUY×2 | +6.0 pips合計 | TP_HIT含む2勝でEV+0.83達成、RANGINGレジームで平均回帰が機能した |
| 戦略 | Pair | PnL | 失敗要因 |
| **sr_channel_reversal** | USD_JPY | -12.5 pips (N=8, WR=25%) | 8件中6件が損失/BEで、SL_HITが複数発生——RANGING環境でもレンジブレイクに巻き込まれておりSR水準の信頼度が低い |

### 2026-04-13 (Post-Tokyo Report)
| セッション内PnL | **-13.4 pips** |
| 勝率（WR） | **33.3%** |
本日累計（36件）: PnL **-35.2 pips** / WR **30.6%**
XAU別枠（11件）: PnL **-1,496 pips**（XAUスケール：要注意）
| 戦略 | ペア | PnL | 成功要因 |
| **bb_rsi_reversion** | USD_JPY | **+5.4 / +0.6 pips** | TP_HIT×1＋OANDA_SL_TP×1、平均回帰シグナルが東京RANGING環境に適合（セッション内EV+0.83は最良水準） |
| 戦略 | ペア | PnL | 失敗要因 |
| **sr_channel_reversal** | USD_JPY | **-12.5 pips（8件）** | WR25%・EV -1.56。SL_HIT×4、TIME_DECAY_EXIT×3が示す通り、レンジ内での逆張りエントリーがS/R水準を繰り返し割られ機能不全 |

### 2026-04-13 (Pre-Tokyo Briefing)
2026-04-12（前日）はトレード**ゼロ件**。全モードON状態にもかかわらず約定なし。XAU関連（daytrade_xau / scalp_xau / scalp_eurjpy）は引き続きOFF。Cutoff後累計はN=316、全体WR=34.8%、累計PnL=**-192.5 pips**（XAU別枠-1,496 pips含まず）。前日は市場参加なく、本日のポジション状態は直前データ依存（Open Trades=2件がOANDA上に残存）。
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
> **注**: fib_reversalはKBでN=32と記録されているが本テーブルではN=26。KB集計とのズレ（+6件）あり。**KBの数値を優先**し、N=32で判定する。EV=+0.78はまだ昇格基準EV≥+1.0に届かず。
| Strategy | Pair | N | WR% | EV | PnL | 所見 |
| vol_surge_detector | USD_JPY | 16 | 43.8% | -0.07 | -1.1 | ⚪ EVほぼゼロ |
| ema_pullback | USD_JPY | 14 | 42.9% | **+1.09** | +15.3 | 🟡 EV優秀・N不足 |
| bb_rsi_reversion | EUR_USD | 13 | 30.8% | -0.79 | -10.3 | 🔴 負EV継続 |
| vol_momentum_scalp | USD_JPY | 11 | **72.7%** | **+1.69** | +18.6 | 🟢 最高WR・N蓄積中 |

### 2026-04-13 (Post-NY Report)
| 勝率 (WR) | 23.1% |
| PnL | **-53.7 pips** |
| 戦略 | ペア | PnL | 成功要因 |
| 戦略 | ペア | PnL | 失敗要因 |
| `dt_bb_rsi_mr` | USD_JPY | -8.2, -1.8 (合計-10.0) | BUY方向に逆行（SL_HIT + SIGNAL_REVERSE）、方向バイアスの誤認 |
### セッションPnL比較
| Session | N | WR% | PnL (pips) | 評価 |
| NY (16–22 UTC) | 26 | 23.1% | -53.7 | ❌ 最低WR |

### 2026-04-13 (Pre-Tokyo Briefing)
- **前日（2026-04-12）トレード数: 0件**（全セッション無発火）
- Cutoff後累積: N=399、全体WR=34.3%、累積PnL=**-259.8 pips**（XAU除く）
- XAU別枠: N=11、PnL=**-1,496.0 pips**（JPYスケール換算）。XAU戦略は現在OFF。
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
| bb_rsi_reversion | USD_JPY | 83 | 37.3% | -0.31 | -25.5 | ⚠️ Tier3降格済（EV負継続）|
| vol_surge_detector | USD_JPY | 24 | 50.0% | +0.05 | +1.2 | 🟡 EV微正・経過観察 |
| engulfing_bb | USD_JPY | 14 | 28.6% | -0.63 | -8.8 | 🔴 N傾向・EV負 |
| vol_momentum_scalp | USD_JPY | 13 | 61.5% | +0.92 | +12.0 | 🟢 KB Tier2・最高WR |

### 2026-04-14 (Pre-Tokyo Briefing)
前日（2026-04-13）は **N=166、WR=28.3%、PnL=−180.4pips** と全セッションを通じて大幅赤字。Cutoff後累計（N=406、WR=33.7%、PnL=−285.2pips）に対し、前日1日だけで累積損失の **63%** を消化した。特にsr_channel_reversal（USD_JPY）が単独で−40.4pipsを叩き出し、前日損失の主犯となった。
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
| bb_rsi_reversion | USD_JPY | 83 | 37.3% | −0.31 | −25.5 | ⚠️ 負EV確定（KB: PAIR_DEMOTED済） |
| sr_channel_reversal | USD_JPY | 29 | 17.2% | −1.67 | −48.3 | 🔴 N≈30到達・EV深刻、降格判断域 |
> **sr_channel_reversal/USD_JPY**：N=29でEV=−1.67、WR17.2%。本日N=30突破が見込まれ、降格基準（N≥30 & EV<−0.5）を大幅超過。正式降格判断の閾値に到達。
| Strategy | Pair | N | WR% | EV | PnL | 状態 |
| fib_reversal | USD_JPY | 26 | 34.6% | +0.78 | +20.4 | 🟡 唯一の正EV大サンプル・昇格ウォッチ |
| vol_surge_detector | USD_JPY | 25 | 48.0% | −0.10 | −2.4 | 🟡 WR良好だがEVフラット、前日悪化 |

## Related
- [[index]] — 戦略Tier分類
- [[bb-rsi-reversion]] — 主要分析対象
- [[research/index]] — 学術的裏付け
- [[lessons/index]] — 過去の教訓
- [[friction-analysis]] — 摩擦モデル
