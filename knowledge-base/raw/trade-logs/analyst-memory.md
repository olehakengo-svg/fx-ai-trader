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

### 2026-04-14 (Post-Tokyo Report)
| 勝率 (WR) | 37.5%（6勝/10敗） |
| PnL | **−12.8 pips** |
**注意**: 本日累計N=20・PnL=−23.7pipsとの差分（N+4, PnL−10.9pips）は東京セッション外（UTC −06:00以前）の4件に帰属。
| 戦略 | Pair | PnL | 成功要因 |
| **stoch_trend_pullback** | USD_JPY | +8.0 | TP_HIT達成（WR=100%、N=1）。ただし単発のためv8.9のFORCE_DEMOTED処分と矛盾する点は後述。 |
| 戦略 | Pair | PnL | 失敗要因 |
| **vol_surge_detector** | USD_JPY | −16.2（N=5, WR=20%） | 最大ドローダウン源。ボラリティスパイク後の方向性を誤読し4連続SL_HIT。本セッションのネガティブ主因。 |
| **bb_rsi_reversion** | USD_JPY | −3.9（N=3） | v8.9でPAIR_DEMOTED確定（EV=−0.28）済みにもかかわらず3件発火。KB判断との整合性を要確認。 |

### 2026-04-14 (Pre-Tokyo Briefing)
前日（2026-04-13）はN=166トレード、WR=28.3%、PnL=**-180.4** という深刻な結果。全セッション（東京・ロンドン・NY）を通じてほぼ全戦略が赤字で、単日損失としてはCutoff後最大規模。Cutoff後累計はN=343、WR=32.9%、PnL=**-209.1**（XAU除く）に達しており、前日だけで累計損失の約86%が発生した異常事態。
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
| vol_surge_detector | USD_JPY | 30 | 50.0% | **+0.11** | +3.4 | ✅ N=30到達・EV微正 |
| sr_channel_reversal | USD_JPY | 29 | 17.2% | **-1.80** | -52.3 | 🔴 N=30目前・EV崩壊 |
| fib_reversal | USD_JPY | 17 | 11.8% | **-1.93** | -32.8 | 🔴 WR壊滅 |
| ema_pullback | USD_JPY | 10 | **60.0%** | **+3.55** | +35.5 | ✅ 最高EV（N=10、要追跡） |
| N | PnL(pips) | 単位換算 |
XAUはN=11、PnL=-1,496pips（JPYスケール）。停止中（OFF）のため新規発火なし。リスク遮断は適切に機能している。

### 2026-04-14 (Pre-Tokyo Briefing)
| PnL合計（前日） | **-180.4 pips** |
| 全体WR | **28.3%** |
前日は166件のトレードで28.3%のWR、-180.4pipsという大幅な損失セッションとなった。XAUの+181.0は別枠集計であり本体P&Lには非加算。Cutoff後累計は N=289、WR=29.8%、PnL=-273.6pips で損失基調が継続。
| Strategy | Pair | N | WR% | EV | 判定 |
| **bb_rsi_reversion** | USD_JPY | 34 | 32.4% | **-0.47** | ⚠️ Tier3相当（EVマイナス継続） |
| **sr_channel_reversal** | USD_JPY | 29 | 17.2% | **-1.87** | 🔴 降格基準抵触（EV<-0.5、N=29で実質確定圏） |
| Strategy | Pair | N | WR% | EV | 状態 |
| vol_surge_detector | USD_JPY | 27 | 44.4% | -0.17 | EVほぼゼロ、WR拮抗 |

### 2026-04-15 (Pre-Tokyo Briefing)
| 前日PnL | **取得不可** |
| 全体WR | **取得不可** |
| Strategy | Pair | N (post-cut) | WR | EV | Kelly | ステータス |
### 📊 Tier 2 — Sentinel（判断基準: N≥30 & EV≥1.0）
| Strategy | N (post-cut) | WR | PnL | 昇格まで | 所見 |
| **vol-momentum-scalp** | 10 | **80.0%** | +21.6 | **残20件** | N<10→データ不足ゾーン脱出直後。高WRだが10件での過信厳禁 |
| vol-surge-detector | 15 | 46.7% | +1.9 | 残15件 | WR下降トレンド（63.6%→46.7%）。EVが辛うじて正 |
| **fib-reversal** | 32 | 40.6% | +21.9 | **N≥30達成** | WR<50%で昇格基準未達。EV確認要 |

### 2026-04-15 (Post-Tokyo Report)
| WR | 38.5% |
| PnL | **−1.5 pips** |
| 戦略 | ペア | 結果 | PnL | 成功要因 |
**bb_rsi_reversion が唯一EV正（+3.53）かつ高WR（100%）を記録**。ただし N=4 のため過信禁物。
| 戦略 | ペア | 結果 | PnL | 失敗要因 |
| BT vs Live 乖離 | session_time_bias/GBP_USD が N_Live=3, WR=0%（🔴アラート）— ただしN=3で確定判断不可 |
### 推奨戦略配分
| 🟢 高 | **bb_rsi_reversion** | USD_JPY | 本日東京でEV+3.53、RANGINGで機能実証（N=4 / 参考値だが整合） |

### 2026-04-15 (Pre-Tokyo Briefing)
| PnL合計 | **-95.0 pips** |
| 全体WR | **27.5%** |
| 平均EV/トレード | **-1.38** |
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
> **唯一N≥30達成**。EV=-1.65は降格基準（EV<-0.5）を大幅に下回る。WR 19.4%は統計的に有意な機能不全。
| Strategy | Pair | N | WR% | EV | PnL | 傾向評価 |
| vol_surge_detector | USD_JPY | 24 | 41.7% | -0.50 | -12.0 | 🟠 境界線（EV=-0.5） |
| Strategy | Pair | N | WR% | EV | コメント |

### 2026-04-15 (Pre-Tokyo Briefing)
| PnL合計（前日） | **-95.0 pip** |
| 全体WR | **27.5%**（期待値ライン30%を下回り） |
前日は69件中53件が損失。SL_HIT主導の広範な負けセッション。Cutoff後累計（N=216）も WR=28.7%、PnL=-257.5 pip と一貫した低調が続いている。
| Strategy | Pair | N | WR% | EV | 判定 |
| vol_surge_detector | USD_JPY | 17 | 47.1% | **-0.30** | 🟡 WR良好だがEV負・要観察 |
| ema_trend_scalp | USD_JPY | 12 | 33.3% | **-0.40** | 🟡 低WR・EV負 |
| engulfing_bb | USD_JPY | 11 | 18.2% | **-0.99** | 🔴 EV<-0.5、N=11 |
| ema_trend_scalp | EUR_USD | 10 | 20.0% | **-1.84** | ⛔ N=10達成・EV深刻 |

### 2026-04-16 (Pre-Tokyo Briefing)
前日（2026-04-15）は38トレード、WR=31.6%、PnL=**-40.1 pips**。全体損失の主因は`sr_fib_confluence/USD_JPY`（-20.6）と`dual_sr_bounce/GBP_USD`（-28.2）の2戦略で計-48.8pipという致命的損失。`bb_rsi_reversion/USD_JPY`（+19.5）と`dt_sr_channel_reversal`クロス円2件（+25.1）が部分的に救ったが、ネットは大幅マイナス。
| Strategy | Pair | N | WR% | EV | 判定 |
| bb_rsi_reversion | EUR_USD | 11 | 45.5% | +0.10 | 🟡 EV薄い |
| ema_trend_scalp | EUR_USD | 10 | 20.0% | **-1.84** | 🔴 強い負EV |
> **N<30の全戦略は「判断可能」領域未到達。** ただしEV≤-2.0かつN≥10は「傾向として有意な負」として扱う。
SL_HIT、スプレッド0.8pip（正常）。損失規模がシステム全体PnLの約半分。この戦略はKB記載なし＝SENTINELリスト外の「散発シグナル」。N=1（全期間）であり統計的判断不可だが、**単一トレードでこの損失額はポジションサイズの問題**。
### 課題②：`dual_sr_bounce/GBP_USD` — 4連敗、EV=-7.05
WR=0%、全てSL_HIT。GBP_USDは現在RANGING（ATR%ile=53%、SMA slope=+0.00385）。レンジ相場でのバウンス戦略は方向性定まらず逆張りが機能しないレジーム。**戦略・レジームのミスマッチ**が主因。

### 2026-04-16 (Post-Tokyo Report)
| 勝率 (WR) | 20.0% (4W / 16L+BE) |
| PnL | **−62.0 pips** |
| 平均EV/トレード | −3.10 |
| 戦略 | ペア | N | WR | PnL | 成功要因 |
| **bb_rsi_reversion** | USD_JPY | 4 | 75.0% | +6.1 pips | RANGING相場(ATR%ile 34%)でのBBタッチ逆張りが機能、TP_HIT×3でEV+1.52 |
**唯一の構造的ポジティブシグナル: bb_rsi_reversionのEV+1.52（N=4, 参考値水準）**
| 戦略 | ペア | N | WR | PnL | 失敗要因 |
| **stoch_trend_pullback の一時停止を検討** | N=3, WR=0%, EV=−4.33。USD_JPYがRANGINGである限り、トレンドフォロー系の期待値は構造的にマイナス |

### 2026-04-16 (Pre-Tokyo Briefing)
前日（2026-04-15）は **N=21、WR=47.6%、PnL=+35.1** と直近では最良の結果。
`bb_rsi_reversion / USD_JPY` が5戦5勝（EV=+3.90）、`dt_sr_channel_reversal / GBP_JPY・EUR_JPY` が大型TP取得（+12.7、+12.4）と、高EV戦略が機能した日。一方、`ema_trend_scalp / EUR_USD` は3戦1勝（EV=-0.53）、`bb_squeeze_breakout / USD_JPY` は2戦全敗（EV=-3.30）と明暗が分かれた。
> Shadow除外済み / XAU別枠（現在XAU OFF） / N=87 全体 WR=29.9%、PnL=−105.7
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
| vol_surge_detector | USD_JPY | 11 | 27.3% | −0.87 | −9.6 | ⚠️ 要監視（EV負） |
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
| ema_trend_scalp | USD_JPY | 6 | 33.3% | +0.12 | +0.7 | △ EV微正だが不安定 |
`vix_carry_unwind`（N=2, EV=−15.45）、`session_time_bias / GBP_USD`（N=2, EV=−7.70）、`xs_momentum`（N=1, EV=−10.50）等は統計的有意性なし。ただし単発での損失幅が大きいものは引き続き記録要。

### 2026-04-16 (Pre-Tokyo Briefing)
前日（2026-04-15）: **PnL = +35.1 | N = 21 | WR = 47.6%**
bb_rsi_reversionのUSD_JPY 5連勝（100% WR, EV +3.90）が牽引し、dt_sr_channel_reversalのGBP_JPY/EUR_JPYが各+12点超の大型獲得。
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
| session_time_bias | GBP_USD | 2 | 0.0% | -7.70 | -15.4 | データ不足（EV懸念大） |
**全体（Cutoff後）: N=56 / WR=30.4% / PnL=-64.3**
※PnLマイナスは初期の大型損失（vix_carry_unwind -22.7、session_time_bias GBP_USD -15.4等）が重荷。
前日4件のSL_HIT（EUR_USD ×3、USD_JPY ×1）。EUR_USDはTRENDING_UPレジームにも関わらずエントリー方向が機能せず、EUR_USD全体EV=-1.50（N=8）は「傾向」として有意に負。
**→ 今日の対処**: ema_trend_scalp（特にEUR_USD）はエントリーシグナルが出ても、システムが自動実行する以上、人的介入は不可。ただし**N=8→N=30到達後に降格判定**が必要であることを認識しておく。本日も同パターンが続く可能性を前提に全体PnL管理。

### 2026-04-17 (Pre-Tokyo Briefing)
前日（2026-04-16）は **12件のトレード、WR 25.0%、PnL -33.6 pips** と大幅な赤字セッション。`vix_carry_unwind` 単体で **-22.7 pips**（1件）という致命的損失が全体を押し下げた。`bb_rsi_reversion` は4件中3勝と健闘したが、他戦略の損失を補填できていない。
| Strategy | Pair | N | WR% | EV | 判定 |
> **昇格基準チェック（N≥30 & EV≥1.0）**: 現時点で基準到達ゼロ。最有望の `bb_rsi_reversion/USD_JPY` がN=10。あと**20件**必要。
> **降格基準チェック（N≥30 & EV<-0.5）**: N≥30の戦略ペアが存在しないため、降格判定の統計的根拠なし。
- 単件で全体PnLの67%を毀損。USD_JPY SELLが N=1 にもかかわらず稼働していた。
- KB上での当該戦略の分類・BT履歴が提示データ内に確認できない（KB記載がカット）。
- **今日の対処**：`vix_carry_unwind` は N=1、EV=-22.70。市場が急変（円急騰局面）していたと推察されるが、1件のSL_HITで判断する段階ではない。ただし**異常損失として記録し、シグナルが再発する場合は優先的に観測**する。
- ボラ急増を検知してエントリーしているが、USD_JPYがRANGINGレジーム下では方向性が出ず、TIME_DECAYで損切りされる構造的弱点が示唆される。

### 2026-04-17 (Post-Tokyo Report)
| PnL | ±0 |
| WR | N/A |
- トレードゼロはシステム異常ではなく、スプレッドガードと時間帯フィルタが機能した結果
- spread_guard閾値（Scalp30%）は東京セッションの流動性低下に対し適切に機能している
- N=0では統計的判断の根拠なし。Fidelity Cutoff（2026-04-08）以降の累積データで判断すべき
### 推奨戦略配分
| `trendline-sweep` (ELITE) | EUR_USD | TRENDING_UP + ATR57%。BT EV=+0.927/WR=80.8%。ロンドン開始のブレイクアウトに適合 |
| `session-time-bias` (ELITE) | EUR_USD, GBP_USD | ロンドンセッションはこの戦略のコアタイム。USD_JPY EV=+0.580も有効 |

### 2026-04-17 (Pre-Tokyo Briefing)
前日（2026-04-16）の全セッション合計：**N=12、PnL=−33.6、WR=25.0%**。
> **N=38、全体WR=36.8%、累積PnL=−16.6**
| Strategy | Pair | N | WR% | EV | 評価 |
| bb_rsi_reversion | USD_JPY | **9** | 88.9% | **+2.84** | ⚠️ N不足だが最高EV戦略 |
- N≥30到達戦略: **ゼロ**（全戦略が「データなし〜傾向」段階）
- 昇格基準（N≥30 & EV≥1.0）到達: 未達
- 降格基準（N≥30 & EV<−0.5）到達: 未達（N不足のため判定保留）
### 課題①：vix_carry_unwind USD_JPY — 単発EV=−22.70（SL_HIT）

### 2026-04-17 (Post-London Report)
| PnL | **0 pips / 0円** |
| WR | **N/A** |
| PnL | 0 | 0 |
| WR | N/A | N/A |
### 推奨戦略配分
| その他 | — | RANGINGペアでのDT系はNO ACTION推奨 |
> **USD_JPY/GBP_JPY/EUR_JPY についてはNO ACTION推奨。**
| 東京 + ロンドン累計PnL | **0 pips / 0円** |

### 2026-04-17 (Pre-Tokyo Briefing)
前日（2026-04-16）トレード数は **2件**、合計PnL = **-0.8pips**、全体WR = **0.0%**。
両トレードとも `TIME_DECAY_EXIT` によるBREAKEVEN決済であり、実質的に「エントリー→時間切れ撤退」のパターン。
| Strategy | Pair | N | WR% | EV | PnL | 評価 |
| ③ | **スプレッド負担** | USD_JPY spread=0.8pip。EV=-0.40はほぼスプレッドコストそのものに相当し、エッジゼロを示唆 |
- **TIME_DECAY_EXIT多発** → USD_JPYが現在RANGINGかつATR%ile=42%（中程度）。DT系戦略はトレンドフォロー前提のものが多く、レンジ相場での不発は構造的。本日もUSD_JPY DTモードでの大量発火は期待しないこと。
- **シグナル枯渇** → EUR/GBP系（TRENDING_UP）の稼働モードに注目。`daytrade_eur`・`daytrade_eurjpy`・`daytrade_gbpusd` がONであることは正しい方向性。引き続き稼働継続を維持。
- **USD_JPY**: SMAスロープ≈0。米国指標次第でTRENDING_UPまたはTRENDING_DOWNへ急転換リスク。ATR%ile上昇（現42%）に注目。
- **GBP_USD**: RANGING継続中だが、SMAスロープ+0.00364は弱いながら上向き。ロンドン時間に抜ければTRENDING_UP転換の可能性。

### 2026-04-20 (Post-Tokyo Report)
| セッション内PnL | 0 pips |
| WR | N/A |
| 本日累計 | N=1 / WR 0.0% / -7.3 pips |
UTC 00:00–06:00（JST 09:00–15:00）該当トレードはゼロ。本日の唯一のトレードはセッション外で発生した-7.3pips（WR 0%）の1件のみ。
- 東京セッションのN=0はデータ不足であり、判断基準（N≥10）を満たさない
- Block Countsを見ると、シグナルそのものは発生している（下記参照）が、フィルタが機能してエントリーを抑制している状態
- 本日稼働中モード（16モード中11モードON）の構成は正常範囲内
| GBP_USD | RANGING (ATR 55%ile) | ロンドン主戦場。オープンでのブレイクアウト試行に注意。RANGING脱却可能性中程度 |

### 2026-04-20 (Pre-Tokyo Briefing)
- **2026-04-19**: トレードゼロ（全セッション不発）
- **当日（Cutoff後累計）**: N=2、WR=50.0%、PnL=+36.9（vwap_mean_reversion のみ）
- Cutoff後のクリーンデータ蓄積はほぼ白紙に近い状態。統計判断に耐えるサンプルはまだ存在しない。
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
- `rnb_usdjpy`の方向フィルターが91件ブロックという異常値。USD/JPYがRANGINGレジームである現状と整合しており、フィルターは正常動作している可能性が高い。無理に突破させるべきではない。
- `score_gate`連発はマーケット側の問題（低ボラ・方向性不明確）であり、戦略側の異常ではない可能性が高い。引き続きモニタリング。
- `same_price`系のブロックはスプレッド拡大・流動性枯渇の兆候。東京時間前後（特に板の薄い時間帯）に集中していると推定される。
- EUR系はTRENDING_UPで最もトレーダブル。ただしATR%ile=36-57%と中低水準のため、大きな値幅は期待しにくい。

### 2026-04-20 (Pre-Tokyo Briefing)
| 前日 PnL | **0** |
| 前日 WR | **N/A** |
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
> **現状**: 全戦略でN=1。Cutoff後の有効サンプルが極端に少なく、EVの数値（特にvwap GBP_JPY: +44.20）は単発の外れ値として扱う。
- EUR系2ペア（EUR_JPY, EUR_USD）が`TRENDING_UP`。ただしATR%ileは中位（36-57%）で極端な高ボラではない。
- GBP系・USD_JPYは`RANGING`。vwap_mean_reversion・gbp_deep_pullbackなどリバーサル系に理論的優位がある環境。
- **レジームとアクティブ戦略のアライメント**: vwap_mean_reversionがGBP_JPY（RANGING）に1件約定し+44.2pipsを記録したことは、レジーム一致の機会を捉えた事例として整合的。
**レジーム遷移リスク**: USD_JPYのSMA20 Slope=+0.00004（ほぼフラット）。RANGINGからTRENDING_UPへの遷移があれば doji_breakout, session_time_biasに追い風。EUR_USDのATR57%ileがさらに上昇するとscalp系のspread_guardブロックが増加するリスクに注意。

### 2026-04-21 (Pre-Tokyo Briefing)
> PnL合計・トレード数・全体WR：**算出不可**（APIレスポンスなし）
定量的な前日集計は行えないが、KBの Portfolio状態・BT EV・Tier分類を基に、構造的分析を以下に示す。
**⚠️ 本日は実トレードデータ取得不可のため、KBのBTベースEVを参照値として掲載**
| Tier | Strategy | Pair | BT EV | BT WR | 昇格基準充足 |
| PAIR_PROMOTED | london-fix-reversal | EUR_JPY | -0.199 | 54.3% | ⚠️ 要注意(BT) |
> **実ライブN値は取得不可のため、昇格基準（N≥30 & EV≥1.0）の充足判定は本日行えない**
- **API復旧確認が最優先**: STATUS → TRADES → OANDA の順に再取得を試みる
- Render環境のスリープ・タイムアウトの可能性あり（コールドスタート後に再クエリ）

### 2026-04-21 (Post-Tokyo Report)
| PnL | 0 pips / 0円 |
| WR | N/A |
- Fidelity Cutoff後のクリーンN=0（本日東京）であり、統計的判断材料が存在しない
- ブロック理由は全てレジーム・セッション・スプレッドに起因しており、パラメータ誤設定の証拠なし
- `direction_filter`（188件）は USD_JPY RANGING環境での正常動作
- `score_gate`系の多発は、複数RANGINGペアに対する適切な保守動作と解釈できる
- DD=25.9%でDD防御0.2x発動中 → 現状でのパラメータ緩和は禁忌
| GBP_USD | RANGING / ATR 57%ile | 高ATRにも関わらずRANGING → ブレイクアウト注意。方向感出れば急騰 |

### 2026-04-21 (Pre-Tokyo Briefing)
- **PnL合計**: +38.2 pips | **トレード数**: 3件 | **全体WR**: 66.7%（2勝1敗）
- Cutoff後累計も同数（3件）— データ蓄積は依然初期段階。統計的判断には程遠い水準。
- 稼働モード数は多数（ON: 13モード）だが、信号発生は極めて低頻度。ブロックが実トレードを大幅に上回る構造が継続中。
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
- 稼働13モード・丸一日で3件のみ。Block Countの上位が **direction_filter（48件）・score_gate（81件合計）** に集中しており、シグナル自体は多数発生しているが、品質フィルタで大半が遮断されている。
- **今日の対処**: フィルタは触れない（コード変更禁止）。観察を継続し、block比率のトレンドを注視する。
- GBP_JPY +44.2pipsは単発の大陽線であり、「実力」ではなく「幸運」の可能性が高い（N=1）。BT未実施のまま本番稼働中。
- **今日の対処**: N蓄積を待つ。この1件でポジティブな評価をしない。

### 2026-04-21 (Post-London Report)
| PnL (pips) | **0.0** |
| PnL | +1.5 pips（WR 100%） | 0.0 pips |
| EUR_USD | TRENDING_UP（ATR%ile 52%） | ドル関連指標・Fed系ニュースで変動リスク高。トレンド継続か反転か要注意 |
### 推奨戦略配分
| ◎ | `post-news-vol` (SENTINEL) | EUR_USD, GBP_USD | NYオープン直後のボラ拡大環境に適合。BT EV: GBP_USD +1.762が最高水準 |
| ◎ | `trendline-sweep` (ELITE) | EUR_USD | TRENDING_UP継続ならEV +0.927が発揮されやすい |
| ○ | `gbp-deep-pullback` (ELITE) | GBP_USD | RANGING高ATR環境でのプルバック狙い。EV +1.064 |
| ✕ | `rnb_usdjpy` | USD_JPY | `direction_filter`が連続発動中。NYでも方向感なければ**NO ACTION推奨** |

### 2026-04-21 (Post-NY Report)
| PnL | **+3.6 pips** |
| 戦略 | ペア | 方向 | PnL | 成功要因 |
| 戦略 | ペア | PnL | 失敗要因 |
### セッション別PnL比較
| Session | 時間帯(UTC) | N | WR% | PnL |
| 本日合計PnL | **+3.6 pips** |
| 本日WR | **100.0%** |
### **NO ACTION推奨**

### 2026-04-22 (Pre-Tokyo Briefing)
前日（2026-04-21）は **vwap_mean_reversion / EUR_JPY** のみが稼働。2トレード、WR 100%、PnL **+3.6 pips**。スプレッド平均1.95pip（2.0 + 1.9）と、Cutoff基準（DT=20%ガード）の範囲内で正常執行。累積（Cutoff後）はN=4、WR=100%、PnL=**+49.1 pips**（うちGBP_JPY 1件が+44.2と突出）。
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
> **統計的地位**: 全戦略がN<10。現時点では「データなし」扱い。昇格基準（N≥30 & EV≥1.0）まで遠い。
> GBP_JPY の EV=+44.20は単一大勝トレードによるアーチファクト。平均として扱うべきではない。
- **score_gateブロックが消えない限り**、DT系戦略からの新規シグナルは期待薄。レジームがRANGINGである以上、スコア閾値超えは構造的に困難。状況観察を継続。
- **daytrade:same_price_5pip=10** は価格クラスタリングによる自己抑制。同ペア同方向の重複エントリー排除として正常動作と解釈。
- **scalp:spread_guard=9** はスプレッド拡大局面への防御。現状維持を確認。
- ✅ **vwap_mean_reversion**（平均回帰）— 最も環境適合

### 2026-04-22 (Post-Tokyo Report)
| PnL | ¥0 |
- 全ブロックは設計済みフィルタの正常動作（spread_guard/score_gate/sl_cluster）
- 全通貨ペアが **RANGING × ATR%ile 34–52%**（中程度ボラティリティ） — トレンド系戦略がスコアを取りにくい環境として整合
- Fidelity Cutoff後の累積Nが事実上ゼロ（本日セッション）であり、統計的根拠なしにパラメータ変更を行うリスクが調整メリットを上回る
### 推奨戦略配分
| **高** | `post-news-vol` | EUR_USD, GBP_USD | BT EV+0.817/+1.762と突出。ロンドンオープン直後のVol拡大局面に直結 |
| **高** | `gbp-deep-pullback` | GBP_USD | ELITE_LIVE EV+1.064。GBP_USD ATR50%でプルバック深度が出やすい |
| **中** | `trendline-sweep` | EUR_USD, GBP_USD | EV+0.927/+0.599。ただしRANGINGでは偽ブレイクリスクあり。score_gate通過依存 |

### 2026-04-22 (Post-London Report)
| **PnL** | **-59.2 pips** |
| **WR** | **0.0%（0勝3敗）** |
| **EV（平均）** | **-19.7 pips/trade** |
| # | 戦略 | ペア | PnL | 敗因 |
| 1 | vwap_mean_reversion | GBP_USD | **-14.1** | シグナル反転（SIGNAL_REVERSE）— エントリー直後に方向性が否定された |
| PnL | 0 pips（0件） | -59.2 pips（3件） | ✗ 悪化 |
| WR | N/A | 0.0% | ✗ |
### 推奨戦略配分

### 2026-04-22 (Post-NY Report)
| **PnL** | **+9.2 pips** |
| **WR** | **100.0%** |
NYセッションは極めて薄商い。1件のみの執行だが、スプレッド0.8pipsに対し+9.2pipsの獲得で摩擦調整後EV=+8.4pips。質的には問題なし。
| 戦略 | ペア | 方向 | PnL | 成功要因 |
| 戦略 | ペア | PnL | 失敗要因 |
### セッション別PnL比較
| Session | N | WR% | PnL (pips) | 評価 |
**ロンドン** — N=3, WR=0%, PnL=-59.2pips

### 2026-04-23 (Pre-Tokyo Briefing)
| PnL合計 | **-50.0 pips** |
| 全体WR | **25.0%** (1勝3敗) |
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
| vwap_mean_reversion | EUR_JPY | 3 | 66.7% | **-6.33** | -19.0 | 🔴 EV深刻 |
| vwap_mean_reversion | GBP_USD | 2 | 0.0% | **-18.30** | -36.6 | 🔴 EV深刻 |
**全期間合算（N=6）**: WR=50.0%、総PnL=**-46.4 pip**
- vwap_mean_reversion の EV が両ペアで著しく負。特に GBP_USD（EV=-18.30）は損失幅が大きく、SL_HIT + SIGNAL_REVERSE の2パターンで消耗
- doji_breakout は N=1のため判断保留（BT EV=+0.338〜+0.724は参考値に留める）

### 2026-04-23 (Post-Tokyo Report)
| PnL (pips) | — |
| WR | — |
| 本日累計 (参考) | N=2, WR=50.0%, PnL=-3.1 pips |
・USD_JPY: slope+0.00061はほぼフラット → 方向性確立まで待機推奨
### 推奨戦略配分
| 🔴 高 | `trendline-sweep` (ELITE_LIVE) | EUR_USD, GBP_USD | BT EV=+0.927/+0.599。ロンドン初動のブレイクアウトと相性最良 |
| 🔴 高 | `post-news-vol` (PAIR_PROMOTED) | GBP_USD | BT EV=+1.762 WR=88.5%。ロンドン時間の報道後ボラ拡張に直結 |
| 🟡 中 | `doji-breakout` (PAIR_PROMOTED) | GBP_USD | BT EV=+0.724。レンジ→ブレイク移行局面で発火条件が整いやすい |

### 2026-04-23 (Post-London Report)
| PnL | **−26.2 pips** |
| 平均EV/トレード | −3.73 |
| 戦略 | ペア | PnL | 成功要因 |
| 戦略 | ペア | PnL | 失敗要因 |
| **trendline_sweep** | GBP_USD | **−2.4 / −4.3 pips** | SIGNAL_REVERSE×2件、ロンドン後半の方向感喪失局面でのシグナル品質低下 |
**構造的問題**: vwap_mean_reversionのJPY通貨ペア（EUR_JPY, GBP_JPY）はspreaddが高く、かつATR%ile 33-36%の低ボラ環境では摩擦調整EVが著しく悪化する。
本日の東京セッション単体データは提供されていないため、**本日累計 N=8 / WR=37.5% / PnL=−33.0**からロンドン分を逆算：
| セッション | N | WR% | PnL |

### 2026-04-23 (Post-NY Report)
| 勝率 (WR) | 0.0% |
| PnL | **-6.8 pips** |
| 戦略 | ペア | 方向 | PnL | 失敗要因 |
### セッション別PnL比較
| Session | N | WR% | PnL (pips) | 評価 |
- **最悪セッション**: London — 7トレード中4敗、-26.2pips。全損失の79%をロンドンが占める
- **最良セッション**: Tokyo — 0トレードにより損失回避（ただし機会損失の観点は別議論）
- **本日合計**: N=8、WR=37.5%、PnL=-33.0pips。全ペアがRANGINGレジームの中で、方向性バイアス戦略が苦戦した可能性が高い

### 2026-04-24 (Pre-Tokyo Briefing)
| 前日PnL合計 | **-33.0 pips** |
| 全体WR | 37.5%（3勝5敗） |
| Cutoff後累計PnL | -83.0 pips（N=12） |
前日は5連敗を含む低調なセッション。vwap_mean_reversionが3件でドラッグ（-50.9 pips）、trendline_sweepも2件がSIGNAL_REVERSE終了と不安定。gbp_deep_pullback (+8.1) のみ健全なTPヒット。
| Strategy | Pair | N | WR% | EV | 判定 |
- GBP_JPY: -20.1 / EUR_JPY: -10.1 / GBP_USD: SL連発
- **GBP_JPYのEV=-20.10はKBにBTデータなし**（"no BT data"）。根拠なしで本番稼働している状態
- spread 2.8pip（GBP_JPY）はvwap系に対して過大な摩擦

### 2026-04-24 (Post-Tokyo Report)
| PnL | ¥0 / 0 pips |
| 勝率 (WR) | N/A |
- Fidelity Cutoff後の有効トレード蓄積が継続中（N→30進行中）。このフェーズでパラメータを変更すればデータが再汚染される
- 本日のゼロ約定は「戦略の失敗」ではなく「適切なフィルタリングの結果」として解釈すべき。RANGING相場でスコアゲートが機能している
- `daytrade_gbpusd:unknown_type:ihs_neckbreak`（30件）は既知の未定義パターン問題だが、コード変更禁止方針に従い判断のみ記録する
### 推奨戦略配分
**ロンドン開始直後（UTC 08:00-10:00）: NO ACTION推奨**
- 現時点でATR%ile全ペア35-52%。ロンドン初動のボラ確認を待つべき段階

### 2026-04-24 (Post-London Report)
| WR | 0.0% |
| PnL | **-6.1 pips** |
| 戦略 | ペア | 方向 | PnL | 失敗要因 |
| WR | 0.0% | 0.0% | 変化なし |
| PnL | -0.3 pips | -6.1 pips | **悪化** |
> 本日累計N=2・WR=0%・PnL=-6.4pipsより、東京セッションでも1トレード(-0.3pips)が確認できる。両セッションともエントリー機会自体が極端に少ない。全通貨ペアがRANGING・ATR%ile 33-52%という「動かない相場」が継続しており、block_countも`same_price_5pip`・`regime_trend_bull_dt_tf`の2件のみ。システムが正常に機会を絞っている。
### 推奨戦略配分
| 🟢 継続可 | session-time-bias (ELITE_LIVE) | USD_JPY | BT EV=+0.580と高く、NY時間バイアスに適合 |

### 2026-04-24 (Post-NY Report)
| 勝率 (WR) | 0.0% |
| PnL | **-0.3 pips** |
| 戦略 | ペア | 方向 | PnL | 失敗要因 |
### セッション別PnL比較
| Session | N | WR% | PnL (pips) | 評価 |
| 本日合計PnL | **-6.4 pips** |
| WR | **0.0%** (0/2) |
| 🔴 高 | **本日WR 0.0%** | N=2でサンプル小さいが、2連敗はKBのELITE_LIVE戦略が稼働していない可能性を示唆 |

### 2026-04-27 (Pre-Tokyo Briefing)
| 前日PnL | **±0** |
| 全体WR | **N/A** |
前日は全モードで約定ゼロ。システムは稼働中だが、ブロックフィルターが全シグナルを遮断した形。Cutoff後累積はN=11、PnL=-42.4の状況が継続している。
> **注意**: 全戦略でN<10（最大N=3）。統計的判断可能水準（N≥30）には程遠く、以下はすべて「データなし〜傾向」の扱い。
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
- **トレンドフォロー系**（trendline_sweep、ema200-trend-reversal等）：**不利**
- **平均回帰系**（vwap_mean_reversion、bb_rsi_reversion）：**理論上有利だが損失記録あり**（精度問題の可能性）
- **ブレイクアウト系**（doji-breakout、squeeze-release-momentum）：レンジ相場ではダマシが増加、**注意要**

### 2026-04-27 (Post-Tokyo Report)
| WR | **0.0%** (0/3) |
| PnL | **-9.4 pips** |
| 本日累計 (N=7) | WR 0.0% / -25.1 pips |
| 戦略 | ペア | Dir | PnL | 失敗要因 |
- `bb_rsi_reversion / USD_JPY`: 本日N=7, WR=0%, EV未確定（Cutoff後累計N未公開だがN<30確実）
- **Fidelity Cutoff後のN蓄積が最優先**。現時点でN<30のため降格基準（N≥30 & EV<-0.5）には未達
- パラメータ変更判断は**N≥30到達後**に持ち越し
### 推奨戦略配分

### 2026-04-27 (Post-London Report)
| 勝率 (WR) | 55.6% (5W / 2L / 1BE / 1LOSS相当) |
| セッション内 PnL | **+15.0 pips** |
| 戦略 | ペア | 寄与PnL | 詳細 |
| bb_rsi_reversion | USD_JPY | **+17.7 pips** | 5戦4勝（WR 80%）、全件スプレッド0.8pips一定でTP_HIT主体の高効率決済 |
| 戦略 | ペア | 寄与PnL | 詳細 |
| bb_rsi_reversion | EUR_USD | **-2.7 pips** | 4戦1勝（WR 25%）、TIME_DECAY_EXIT × 2・SL_HIT × 1が主因 |
| 本日累計 vs セッション単体 | 累計16件・WR 31.2%・-5.0 pips | 9件・WR 55.6%・+15.0 pips |
| 推定PnL差 | — | ロンドン単独で**+15.0 pips**（東京推定 ≈ -20.0 pips） |

### 2026-04-27 (Post-NY Report)
| 勝率 (WR) | 0.0% |
| PnL | -0.1 pips |
| 戦略 | ペア | 結果 | PnL | 失敗要因 |
| bb_rsi_reversion | EUR_USD | BREAKEVEN | -0.1 pips | TIME_DECAY_EXITで時間切れ終了。スプレッド0.8bpの摩擦が収益を僅かに削り、方向性なきRANGING相場でエントリーが機能しなかった。 |
**補足**: BREAKEVEN判定だが-0.1pipsの摩擦コストが残っており、実質微損。EUR_USDはATR%ile=50%・RANGING レジームで、bb_rsi_reversionのような平均回帰系にとって方向転換タイミングの見極めが困難な状態。
### セッション別PnL比較
| セッション | 時間 (UTC) | N | WR% | PnL (pips) | 評価 |
> **注記**: 本日累計テーブル（N=16, PnL=-5.0）とセッション合算（N=13, PnL=+5.5）に乖離あり。Cutoffフィルタ外のトレード3件（PnL合計-10.5pips相当）が累計側に含まれている可能性が高い。以降はFidelity Cutoff準拠のセッション合算（N=13, +5.5pips）を正とする。

### 2026-04-28 (Pre-Tokyo Briefing)
| PnL合計（2026-04-27） | **-5.0 pips** |
| 全体WR | **31.2%** (5勝11敗) |
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
| bb_rsi_reversion | GBP_USD | 3 | 0.0% | **-4.40** | -13.2 | 🔴 要注意 |
> **全戦略・全ペアでEV負。** N≥30の昇格基準に達しているペアはゼロ。GBP_USDはN=3で判断不可だが、EV=-4.40は構造的懸念材料。
- EUR/USD SMA20 Slope=+0.00386（緩やかな上昇）だが、前日EUR_USD WR=20%（1勝4敗）
- 上昇トレンド環境でリバーサル戦略（bb_rsi_reversion）を連打 → 順張りと逆張りのミスマッチ
- **対策**: RANGING相場での方向フィルタの有効性を注視。score_gate/conf<30のブロックが機能しているか確認。

### 2026-04-28 (Post-Tokyo Report)
| WR | 28.6% (2/7) |
| PnL | **-3.0 pips** |
> 本日累計（N=9, WR=22.2%, PnL=-9.6）と合算すると、セッション外でさらに2件の損失が発生している。
| 戦略 | ペア | Dir | PnL | 成功要因 |
| 戦略 | ペア | N損失 | 合計PnL | 失敗要因 |
**特記事項**: bb_rsi_reversion は本日 N=6 でEV=-2.10。Cutoff 後の累積 N が不明だが、本セッション単独でも EV が深刻に負。
| bb_rsi_reversion | **降格検討ライン入り（要 N 蓄積確認）** | 本日 N=6 は統計的に「傾向」止まり。Cutoff 後累積 N≥30 に達した時点で改めて EV を評価する。現時点でのパラメータ変更は早計。 |
| vix_carry_unwind | **継続監視** | N=1 は「データなし」水準。KB上 BT EV=+0.212 / WR=67.3% であり、本日の +9.6 は方向性と整合する一例に過ぎない。 |

### 2026-04-28 (Post-London Report)
| 勝率（WR） | 100.0%（1/1） |
| PnL | +1.3 pips |
結果はWIN（SL_HIT経由）でPnL +1.3 pips。スプレッドも1.3 pipsと記録されており、
**実質的な摩擦調整EVはほぼゼロ**（gross pips = spread と等しい）。
| 戦略 | ペア | 方向 | PnL | 成功要因 |
| 本日累計N | WR | PnL |
→ ロンドン前（東京セッション）で**9件 / WR約22% / PnL −9.6 pips**相当が発生していた計算。
| WR | ≈22% | 100%（N=1、参考値） |

### 2026-04-28 (Post-NY Report)
| WR | — |
| PnL | **+0.0 pips** |
| Session | N | WR% | PnL (pips) | 評価 |
> ※合計N=8（セッション合計）、公式集計テーブルのN=10・WR=30%との差はセッション外時間帯（UTC 06–07等）のトレードが含まれる可能性あり。PnLは−1.7pipsを正値として採用。
| 総PnL | **−1.7 〜 −8.3 pips** |
| 最悪セッション | **Tokyo（7件、WR28.6%、−3.0pips）** |
**特記事項:** 本日合計PnLテーブルの「−8.3 pips / N=10」と、セッション別合計の「−1.7 pips / N=8」の乖離は、pip計算基準（スプレッド込み/抜き、通貨スケール差異）または深夜帯トレードの集計範囲差に起因する可能性がある。**どちらの数値を正とするにせよ、本日は明確な負け日。**
これは意図的な設計動作 — シャドウフェーズにある戦略のシグナルはOANDA本番に転送せずデモ蓄積のみ。Fidelity Cutoff後データが N<30 に留まる限り、この状態は継続する。現時点でOANDA本番稼働率は **0%** であり、全損益はデモPnLのみ。

### 2026-04-29 (Pre-Tokyo Briefing)
| 前日PnL合計 | **-8.3 pips** |
| 全体WR | **30.0%** (3勝7敗) |
前日はbb_rsi_reversionのUSD_JPYが8戦1勝（WR 12.5%）と壊滅的なパフォーマンス。vix_carry_unwindの+9.6が唯一の救いだったが、構造的には損益がbb_rsi_reversionの連続SL_HITに引っ張られた1日。
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
- bb_rsi_reversion/USD_JPY: N=20 → **あと10件でN=30到達**（降格判定確定ライン）
- その他全戦略: N≦5、判断不可
前日8トレード中7件がSL_HIT（1件はTIME_DECAY_EXIT）。WR=12.5%はBT期待値（想定50-60%台）を大幅に下回る。
- USD_JPYは現在レジーム=RANGING（ATR%ile 31%）、低ボラ環境でSMAスロープほぼゼロ（-0.00013）

### 2026-04-29 (Post-Tokyo Report)
| WR | 0.0% (0/1) |
| PnL | **-3.4 pips** |
| 本日累計 PnL | -9.6 pips（N=3, WR=0.0%） |
| 戦略 | ペア | 方向 | PnL | 失敗要因 |
- スプレッド 0.8 pips は正常範囲（spread_guard 引っかかりなし）
- **bb_rsi_reversion** はKBに PAIR_PROMOTED / ELITE_LIVE のいずれにも未登録であることに留意
- N=1（本日累計N=3）では判断材料として不十分
- bb_rsi_reversion の累積クリーンデータ（Fidelity Cutoff後）が蓄積途上であり、EV算出不可

### 2026-04-29 (Post-London Report)
| WR | **0.0%** |
| PnL | **-8.9 pips** |
| 戦略 | ペア | PnL | 失敗要因 |
GBP_USDは本日レジームRANGING（ATR%ile=31%）であり、session_time_biasのBTデータ（GBP_USD EV=+0.113、WR=67.1%）が想定するトレンド性が現実化しなかった典型ケース。
| セッションWR | — | 0.0% |
| セッションPnL | 約-9.6pips（残差） | -8.9pips |
- 本日累計N=4、WR=0.0%、PnL=-18.5pipsであり、東京・ロンドン双方で勝ちゼロ
- 全ペアがRANGING状態（ATR%ile 31-43%）で推移しており、東京引き続きロンドンでもトレンド系戦略の成立条件が欠如

### 2026-04-29 (Pre-Tokyo Briefing)
| PnL合計 | **+1.3 pips** |
| 全体WR | **100%** (N=1, 統計的意味なし) |
前日（2026-04-28）は全稼働モード（17系統中10ON）にもかかわらず、約定は1件のみ。session_time_bias/GBP_USDのSELL→WIN（PnL+1.3）のみ。活動水準は極めて低調。
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
> 📌 N=5は「統計的にデータなし」レベル。いかなる昇格・降格判定も不可。EV・WRの数値は参考値として保持するが意思決定に使わない。
- 全17モード中10モードがONにもかかわらず、前日約定は1件。
- Cutoff後累計でもN=5にとどまる。これはシステム稼働から**3週間超**が経過している水準としては深刻な低頻度。
- 月利100%目標に対し、1日1件ペースでは統計蓄積もPnL蓄積も成立しない。

### 2026-04-30 (Post-Tokyo Report)
| セッション内PnL | — |
| セッション内WR | — |
本日累計（参考）: N=5, WR=40.0%, PnL=−3.8 pips（東京前の累積）
- ブロック内容は全て設計通りの品質フィルター（`recent_emit`、`score_gate`、`direction_filter`）
- `same_price_0pip`の多発は市場側の問題（低ボラ）であり、システム側の誤動作ではない
- `scalp_5m_eur:sl_cluster`(2件) は正常なリスク管理作動
- 本日累計N=5はFidelity Cutoff後の統計として無意味（判断閾値N≥30に遠く及ばない）
- **コード変更禁止原則に加え、データ的根拠も存在しない**

### 2026-04-30 (Post-London Report)
| 勝率 (WR) | **71.4%** (5勝2敗) |
| セッション PnL | **+6.4 pips** |
| Payoff比 | **0.49** (非対称リスクに注意) |
| 戦略 | ペア | PnL | 成功要因 |
**本セッションの最大貢献:** xs_momentum GBP_USD (+22.2p) がセッションPnLの347%分を単独で稼ぎ、他の損失を相殺した構造。
| 戦略 | ペア | PnL | 失敗要因 |
> ⚠️ **streak_reversalの-23.4pipsは本セッション最大損失**。xs_momentumの+22.2pipsとほぼ相殺される規模であり、1トレードでセッションPnLを破壊しうるリスクが顕在化。
| 本日累計 PnL | **-4.3 pips** | ロンドン単体 +6.4 pips | 東京: -10.7 pips（逆算） |

### 2026-04-30 (Post-NY Report)
| WR | — |
| PnL | **±0.0 pips** |
### セッション別PnL比較
| Session | N | WR% | PnL (pips) | 評価 |
> ※ 本日累計（system集計）は N=11 / WR=54.5% / PnL=−4.3 と乖離あり。ロンドン外のトレードがシステム内部で計上されている可能性（クリーンデータ外のshadow分含む）。本レポートではFidelity Cutoff後の有効データであるロンドンセッション値（N=7）を正とする。
**ロンドン** — N=7 / WR=71.4% / +6.4 pips。唯一のアクティブ帯域。
| 2 | **BT vs Live乖離：session_time_bias / GBP_USD** ΔWR=+26.7pp（Live WR=33.3%、N=3） | 中（N不足） |
| 4 | **本日累計PnL乖離**（system=−4.3 pips vs London単独=+6.4 pips）の出所確認 | 中 |

### 2026-05-01 (Pre-Tokyo Briefing)
- **PnL合計**: -4.3 pips（11トレード、WR 54.5%）
- **勝ちトレードの頭打ち**: xs_momentum +22.2、bb_rsi_reversion +6.9が牽引したが、streak_reversal -23.4の単発損失が全体を沈める
- **実態**: 勝率は5割超だが、**最大損失(-23.4)が最大利益(+22.2)を上回るリスク非対称**が今日も継続
| Strategy | Pair | N | WR% | EV | 判定 |
- N=1での評価は統計的に無意味だが、USD_JPYが現在VOLATILE（ATR%ile 64%）レジームにある点と-23.4という損失規模は注目に値する
- BT実績なし（KB: "no BT data"）の戦略がPAIR_PROMOTEDで稼働中
- **本日の対処**: BT根拠のない戦略については、Nが積み上がるまで損失1件の重みが過大になる点を認識して監視継続
### 課題②：session_time_bias（GBP_USD）— WR 33.3% / EV -3.33

### 2026-05-01 (Post-Tokyo Report)
| WR | 50.0% |
| PnL | **+1.6 pips** |
| 本日累計N | 10 / WR 50.0% / +10.8 pips |
| # | Strategy | Pair | Dir | PnL | Reason |
| ✅ | bb_rsi_reversion | USD_JPY | BUY | +3.6 | 同上、3連続TP_HIT局面でEV貢献 |
| # | Strategy | Pair | Dir | PnL | Reason |
- SELL側の-9.1pipが全体PnLを圧迫。USD_JPYはSMA20 Slope=-0.00054（ほぼフラット）だが、VOLATILE環境ではモメンタム継続リスクが高い。方向バイアスなしの逆張りでSELLエントリーが下降加速に捕まった可能性。
- TIME_DECAY_EXIT（-1.0）は戦略上許容範囲だが、ボラ高環境でのTP設定が狭い可能性も示唆。

### 2026-05-01 (Post-London Report)
| 勝率（WR） | **40.0%** |
| 純PnL | **-10.6 pips** |
セッション全体は赤字。gbp_deep_pullbackの1件がセッションPnLを大きく毀損。
| 戦略 | ペア | PnL | 成功要因 |
| 戦略 | ペア | PnL | 失敗要因 |
| **vix_carry_unwind** | USD_JPY | -0.1 pips | BREAKEVENでSL_HIT — BT WR=67.3%に対し直近ライブWR=33.3%（🔴乖離アラート）。 |
GBP_USDは現在TRENDING_UP（SMA20 Slope=+0.00540）。ディープ・プルバック戦略はトレンドの強い環境では構造的に不利。ELITEステータス（BT EV=+1.064）であっても現レジームとの適合性に疑問符。
| 累計PnL貢献 | -7.1 pips（推定） | -10.6 pips |

### 2026-05-01 (Post-NY Report)
| PnL | **-7.8 pips** |
| 戦略 | ペア | 方向 | PnL | 失敗要因 |
### セッション別PnL比較
| セッション | N | WR% | PnL (pips) | 評価 |
> ※本日累計テーブルにN=14, WR=42.9%, PnL=-17.7との記載があるが、セッション合計N=12, PnL=-16.8との乖離は集計タイミング差と思われる。セッション別テーブルを採用。
**東京セッション** — N=6, WR=50.0%, +1.6pips。ただし規模が小さく有意とは言えない。
**ロンドンセッション** — N=5, WR=40.0%, -10.6pips。PnL単独では最大損失。EUR_USD RANGING環境下で方向性戦略が機能しなかった可能性。
- `bb_rsi_reversion` (EUR_USD) がNY唯一のトレードでTIME_DECAY_EXIT → 反平均回帰的な値動き

### 2026-05-04 (Pre-Tokyo Briefing)
前日（2026-05-03）は**トレード執行なし**。PnL = ¥0、N = 0、WR = N/A。
Cutoff後累計はN=22、WR=45.5%、PnL=−12.1pips相当。システムは稼働中（OANDA NAV: 435,495.96）だが実質的に無執行日が継続している。
| Strategy | Pair | N | WR% | EV | 判定 |
| bb_rsi_reversion | USD_JPY | 9 | 44.4% | −0.03 | ⚪ N不足（EV≈0） |
| vix_carry_unwind | USD_JPY | 4 | 25.0% | −5.25 | 🔴 N不足・EV深刻 |
- `direction_filter`の遮断集中（92件）が本当にレジーム由来の正常動作なのか、または過剰収縮なのかを**rnb_usdjpyのシグナル品質**で判断する必要がある
- `recent_emit`のクールダウン時間が実質的にセッション全体をカバーしている可能性を注視
| USD_JPY | VOLATILE | 67% | −0.001 | 方向性不明確。bb_rsi_reversionには不利。fib_reversalは機能する可能性あり。vix_carry_unwindはVOLATILEで本来有利なはずだがWR=25%は構造問題の示唆 |

### 2026-05-04 (Post-Tokyo Report)
| 純PnL | **+1.1 pips** |
| 戦略 | ペア | 方向 | PnL | 成功要因 |
| **bb_rsi_reversion** | USD_JPY | SELL | **+6.4 pips** | TP_HIT、USD/JPY VOLATILE レジーム下でバンド端からの回帰が高EV条件を満たした |
| 戦略 | ペア | 方向 | PnL | 失敗要因 |
> 注目点：bb_rsi_reversion の2トレードを合算すると EV=+0.20（N=2）。個別の損益振れ幅（±6 pips）に対しネット収益が微小であり、1トレードあたりのリスクリワード効率が低い状態。
| EV方向 | bb_rsi_reversion EV=+0.20、streak_reversal EV=+0.70、どちらも正値 |
| vix_carry_unwind 乖離 | BT WR=67.3% vs Live WR=25.0%（N=4）は要継続観察だが、N=4で降格判断には早い |
| EUR_JPY | VOLATILE (66%ile) | 継続VOLATILE | ボラ系戦略有利、ただし hedge_block 多発注意 |

### 2026-05-04 (Post-London Report)
| PnL | **-13.6 pips** |
| 戦略 | ペア | 結果 | PnL | 成功要因 |
| 戦略 | ペア | 結果 | PnL | 失敗要因 |
| sr_fib_confluence | GBP_USD | LOSS | **-12.6 pips** | SIGNAL_REVERSE終了—サポート/フィボ水準での反転期待がGBP_USD上昇トレンドに逆らう形となり、シグナルそのものが反転（TRENDING_UPに逆張りした構造的ミスマッチ） |
**注目点**: sr_fib_confluenceの-12.6 pipsは本日の全損失の**約89%**を占める。SIGNAL_REVERSEという終了理由は「エントリー後に市場が逆行しシグナル消失」を意味し、GBP_USDのTRENDING_UPレジームで逆張り的なSR/Fib戦略を取ったことのレジームミスマッチが根本原因と見られる。
> 本日累計 N=7, WR=57.1%, PnL=-12.5 pips
> ロンドン分 N=4, PnL=-13.6 pips
> ∴ **東京セッション推計**: N=3, PnL≈+1.1 pips（東京は小幅プラス）

### 2026-05-04 (Post-NY Report)
| 勝率 (WR) | 0.0% |
| PnL | **-2.5 pips** |
| 戦略 | ペア | 方向 | PnL | 失敗要因 |
### セッション別PnL比較
| Session | N | WR% | PnL (pips) | 評価 |
| 本日合計WR | 50.0% |
| 本日合計PnL | **-15.0 pips** |
| 最良セッション | **東京** (+1.1 pips, WR 66.7%) |

### 2026-05-05 (Pre-Tokyo Briefing)
前日（2026-05-04）は **8トレード、WR 50.0%、PnL -15.0** と赤字セッション。
`sr_fib_confluence` の -12.6（SIGNAL_REVERSE）と `gbp_deep_pullback` による累積損が全体を押し下げ、勝率では均衡しているにもかかわらず損益が非対称に傾いている典型的なペイオフ逆転構造が出現した。
| Strategy | Pair | N | WR% | EV | 判定 |
> **全体**: N=16、WR 43.8%、PnL -46.2
### 課題①：`sr_fib_confluence` — SIGNAL_REVERSE による大損
- PnL -12.6（EV -12.60、N=1）
- エグジット理由が `SIGNAL_REVERSE` ＝ エントリー後に逆方向シグナルが発生し損切り。GBP_USDはTRENDING_UPレジームであり、逆張り系フィブ戦略がトレンドに逆行した可能性が高い。
- **本日の対処方針**: GBP_USDがTRENDING_UP継続中の間、`sr_fib_confluence`のGBP_USD向けシグナルは統計的根拠が薄い。N蓄積を優先し、昇格判断は保留。

### 2026-05-05 (Post-Tokyo Report)
| PnL | — |
| WR | — |
本日累計ではN=1、WR=0%、PnL=**-7.4 pips**（セッション外の1件、詳細不明）。
- Cutoff後のトレードがN=1（本日のみ）のため、いかなる戦略も統計的判断基準（N≥10「傾向」、N≥30「判断可能」）に達していない
- 東京セッション0件は「戦略の問題」ではなく、後述のブロック構造と流動性起因と判断
| USD_JPY | VOLATILE | 71% | ヘッジブロック多発中、注意 |
### 推奨戦略配分
| 🔴 最優先 | `gbp-deep-pullback` | GBP_USD | ELITE_LIVE・BT EV=+1.064・TRENDING_UP整合 |

### 2026-05-05 (Post-London Report)
| 勝率（WR） | 50.0% |
| 合計PnL | **-1.1 pips** |
| EV | -0.55 pips/trade |
ロンドンセッション（UTC 07:00–16:00）は2トレードのみで実質的な不活性セッション。PnLは僅かにマイナスで着地。
| 戦略 | ペア | 方向 | PnL | 成功要因 |
**成功要因1文**: SL/TPによる規律ある利確が機能したが、+0.8pipsに対してスプレッドが0.8pipsであり、実質的な純益はゼロ水準（摩擦調整後EV≈0）。
| 戦略 | ペア | 方向 | PnL | 失敗要因 |
| 累計PnL | -7.4 pips（残差推定） | -1.1 pips | 損失拡大継続 |

### 2026-05-05 (Post-NY Report)
| WR | — |
| PnL | **+0.0 pips** |
### セッション別PnL比較
| Session | N | WR% | PnL (pips) | 評価 |
> ※ Fidelity Cutoff後の「本日累計」は N=3 / WR=33.3% / PnL=−8.5 pipsと乖離あり。セッション集計と時刻の整合性から、本日の確定値は **N=2 / WR=50% / PnL=−1.1 pips** を採用。残差1トレード（−7.4pips相当）は前セッション境界の可能性あり。
- OANDA接続は `Active: True` だが NAV/Balance が **None** のまま
- `Latency: None ms` — APIは接続しているが資金情報の取得が失敗している
- これにより全シグナルが安全サイドでSKIP継続

### 2026-05-06 (Pre-Tokyo Briefing)
| 前日PnL | **-8.5 pip** |
| 全体WR | **33.3%** |
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
> **全体**: N=12, WR=41.7%, PnL=-31.3pip（Cutoff後累計）
| USD_JPY TIME_DECAY | 2件(N=2)はノイズ。N=5まで追跡継続。ただしEV=-0.78は要監視 |
- **最も危険な組み合わせ**: GBP_USD TRENDING_UP × bb_rsi_reversion SELL → 継続リスク高
- **最も環境適合**: EUR_USD RANGING × 平均回帰系（ただし約定量が少ない）
- **機会領域**: USD_JPY/EUR_JPY VOLATILE × モメンタム系（streak_reversal等）

### 2026-05-06 (Post-Tokyo Report)
| WR | **0.0%** (1敗) |
| PnL | **−5.6 pips** |
| 本日累計（参考） | N=2 / WR=50% / +6.2 pips |
| 戦略 | ペア | 方向 | PnL | 失敗要因 |
- streak_reversal / USD_JPY はKB上「no BT data / PAIR_PROMOTED」。センチネル段階でありN蓄積中。
- N=1（本日）の単一損失からシグナルは引き出せない。
- VOLATILE環境下でのSL_HIT 1件は通常レンジ内事象。
- 現在DD=28.01% → DD防御モード（0.2x）稼働中であり、パラメータ干渉のコストが高い。

### 2026-05-06 (Post-London Report)
| WR | 100.0%（参考値・N=1） |
| PnL | **+11.8 pips** |
| 戦略 | ペア | 方向 | PnL | 成功要因 |
| WR | 0%（1件LOSS） | 100%（1件WIN） | +100pt |
| PnL | **▲5.6 pips** | **+11.8 pips** | +17.4 pips 改善 |
本日累計がN=2・WR50%・+6.2 pipsであることから、東京セッションでの1件は推定▲5.6 pipsのLOSSとなる。
### 推奨戦略配分
| ○ | post-news-vol（SENTINEL） | GBP/USD | TRENDING_UP環境下・NY米指標後のVolスパイクに親和性（BT EV=+1.762） |

### 2026-05-06 (Post-NY Report)
| PnL | **+0.0 pips** |
| WR | **—** |
### セッション別PnL比較
| Session | N | WR% | PnL (pips) | 評価 |
| 合計PnL | **+6.2 pips** |
| WR | **50.0%** |
| 最良セッション | **London** (+11.8 pips, WR 100%) |
| 最悪セッション | **Tokyo** (-5.6 pips, WR 0%) |

### 2026-05-07 (Pre-Tokyo Briefing)
- **PnL**: +6.2 pips（2トレード）
- **WR**: 50.0%（1勝1敗）
- **特記**: 1勝（bb_rsi_reversion USD_JPY +11.8p）が1敗（streak_reversal USD_JPY -5.6p）を相殺し辛うじてプラス着地。日次トレード数は極めて少なく、システムが過剰フィルタリング状態にある可能性あり。
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
| **合計** | | **8** | **37.5%** | — | **-16.0** | ❌ N不足・EV不明 |
> **統計的注意**: 全戦略でN<10。判断可能水準（N≥30）に到達しているものはゼロ。EVの正負はすべて「傾向」以下の信頼度。PnL合計-16.0は前日の+6.2を差し引いた累積であり、構造的赤字が継続中。
- **現象**: 前日2件のみ。Block counts上位を見ると`recent_emit`系が系統的にシグナルを抑制している（daytrade_eur:99、daytrade_gbpusd:93、daytrade:75など）。
- **主因分析**:

### 2026-05-07 (Post-Tokyo Report)
- UTC 00:00–06:00 対象トレード: **0件**
- 本日累計: N=6, WR=66.7%, PnL=**-9.9 pips**（セッション外の取引を含む）
- OANDA NAV: **435,752.48** / Open Trades: **0**
- N=6, PnL=**-9.9 pips**（WR 66.7%でもネガティブPnL）
- 「3勝4敗相当のpip収支」は**勝ちpipsより負けpipsが大きい非対称構造**を示唆
- 具体的には平均勝ち<平均負けの逆リスクリワード状態が疑われる
- 東京セッションの実行機会ゼロは「戦略の失敗」ではなく、**ブロック機構が正常動作している証拠**
- Block Countsのトップが `scalp_eur:max_open(262)` `scalp:max_open(260)` と `max_open` 系に集中

### 2026-05-07 (Post-London Report)
| PnL | **-10.0 pips** |
**サマリー**: WR63.6%にもかかわらずPnLはマイナス。ペイオフ比（勝ち平均/負け平均）= 0.30という深刻な非対称性が支配している。「多く勝って大きく負ける」典型的なリバーション系の病理。
| 戦略 | ペア | PnL | 成功要因 |
| 戦略 | ペア | PnL | 失敗要因 |
| **bb_rsi_reversion** | GBP_USD | **-0.6 pips**（4戦2勝2敗） | TRENDING_UPに逆らうリバーション。勝ち負けが相殺されるがEV=-0.15と微妙にマイナス。 |
| 本日累計PnL | -46.0 pips | ロンドン分: -10.0 pips |
| 東京分PnL推定 | **-36.0 pips** | — |
| 累計WR | 53.3% | ロンドン: 63.6% |

### 2026-05-07 (Pre-Tokyo Briefing)
前日（2026-05-06）は **2トレード、PnL +6.2pip、WR 50.0%** で小幅プラス着地。
| Strategy | Pair | N | WR% | EV | PnL | ステータス |
| trendline_sweep | GBP_USD | 5 | 80.0% | -0.22 | -1.1 | ⚠️ EV負 |
| bb_rsi_reversion | GBP_USD | 4 | 50.0% | -0.15 | -0.6 | ⚠️ EV負 |
> **N注記**: 全戦略 N<10。統計的に「データなし〜傾向」の域を出ず。EVの絶対値より方向性とLoss規模に注目すべき段階。
- Cutoff後 N=2、WR=0%、EV=**-12.90**。前日も -5.6pip（SL_HIT）。
- この戦略はKBで「no BT data」のまま PAIR_PROMOTED。実データで裏付けなし。
- **対策**: 本日も稼働するが、N=10到達まで EV推移を注視。N=10時点でEV≦-3.0であれば降格判断の根拠となる。

### 2026-05-08 (Pre-Tokyo Briefing)
前日（2026-05-07）は **17トレード、WR 47.1%、PnL -75.4pip** と大幅損失セッション。Cutoff後累計も N=19、WR 47.4%、PnL -69.2pip に留まり、単日で累計損益を押し上げた格好。勝ちはあるが、数件の大型SL_HIT（-20pip前後）が全体を押し下げる典型的な非対称損失構造。
| Strategy | Pair | N | WR% | EV | 判定 |
| trendline_sweep | GBP_USD | 5 | 80.0% | **-0.22** | ⚠️ WR高いがEV負（摩擦大） |
> **統計的判断ライン**: 全戦略 N<10。現時点で「判断可能」水準（N≥30）に達しているものはゼロ。EVの正負は「傾向」として読む。
wick_imbalance_reversion  GBP_USD  -9.2pip (SIGNAL_REVERSE) + -9.3pip (SL_HIT)
### 主要問題② — trendline_sweep のEV逆転
WR 80%でも EV = -0.22。前日詳細を見ると、勝ちトレードは +1.1〜+1.4pip（小）、負けは -6.3pip（大）。典型的な **RR比の歪み**（Win小・Loss大）。ELITE_LIVEステータスを持つが、**本番GBP_USDでのリターン実績は現時点でBT想定（EV=+0.599）を大幅に下回っている**。
**本日の対処**: 昇格ステータスは維持しつつも、N=30到達後に本番EVを改めてBT値と比較することを予約。

### 2026-05-08 (Post-Tokyo Report)
| セッション (UTC 00:00–06:00) | **N=2, WR=100.0%, PnL=+9.0 pips** |
⚠️ **統計的扱い**: N=2 は「データなし」扱い。WR 100%・PnL+9.0 は参考値に留める。
| 戦略 | ペア | 方向 | PnL | 成功要因 |
- N=2 は判断に必要な統計量を満たしていない（判断閾値 N≥30）
- 現在 DD=28.01%（DD防御 0.2x モード）。この局面での戦略変更は追加リスクを招く
- ブロック多発はシステムが意図通りリスクを制限している証拠であり、異常ではない
- Fidelity Cutoff 後の蓄積データが極めて少量（本日 N=2）。クリーンデータの蓄積優先
### 推奨戦略配分

### 2026-05-08 (Post-London Report)
| PnL | **−4.1 pips** |
| トレード | 方向 | PnL | クローズ理由 |
- **成功要因**: USD_JPYが`VOLATILE`レジーム（ATR%ile 76%）かつSMA20スロープが−0.00345（下方向）で、JPY高方向へのモメンタムとアンワインド方向が完全に一致。全3件がSL/TP正常作動（OANDA_SL_TP）でスリッページなく決済。
- **Spread 0.8 pips**は許容範囲内。EV +5.93は本日最高。
| トレード | 方向 | PnL | クローズ理由 |
- **失敗要因**: GBP_USDは`RANGING`（ATR%ile 40%）で、モメンタム戦略が本来機能しにくいレジームにも関わらず全3件がBUY方向に集中。SL_HITが2件と損切り多発。
- BT乖離アラート🔴: WR_BT 63.5% vs WR_Live 33.3%（ΔWR −30.2pp）— **構造的乖離の可能性あり**。
- **失敗要因**: EUR_USDは`RANGING`（ATR%ile 40%）でSMA20スロープが僅かに上向き（+0.00236）。N=1のため判断材料として不十分だが、レジーム適合性に疑問。

### 2026-05-08 (Post-NY Report)
| WR | — |
| PnL (pips) | **0.0** |
### セッション別PnL比較
| Session | N | WR% | PnL (pips) | 評価 |
- **合計PnL**: +4.9 pips（N=9）
- **最良セッション**: Tokyo — N=2, 100.0% WR, +9.0 pips。小サンプルながら全勝。
- **最悪セッション**: London — N=7, WR57.1%, -4.1 pips。エントリー数は最多だが負のPnL。
- **NYは完全沈黙** — 本日9トレードのうちロンドン終了後はゼロ。

### 2026-05-11 (Pre-Tokyo Briefing)
**2026-05-10（前日）はトレードゼロ。** 全モード合計でエントリーなし。PnL = ±0。
Cutoff後（2026-04-08〜）の累積データ：N=29, WR=51.7%, PnL=**−72.3**（累積赤字）。母数が小さく統計的判断はまだ困難だが、損失額のドラッグは無視できない水準。
| Strategy | Pair | N | WR% | EV | 判定 |
| trendline_sweep | GBP_USD | 5 | 80.0% | −0.22 | ⚠️ WRとEVが乖離（損小なのでUW非該当） |
> **全N=29。昇格基準（N≥30 & EV≥1.0）到達者ゼロ。降格基準（N≥30 & EV<−0.5）も未達（母数不足）。**
- 全モードでエントリーなし。block_countsを見ると **hedge_block** と **r2_shadow_demoted_cell** が支配的。
- hedge_blockの主因：daytrade系の複数モードが同一ポジション方向をブロックし合っている。
- r2_shadow_demoted_cellの主因：scalp系セルがシャドウステージで降格判定を受けている。

### 2026-05-11 (Pre-Tokyo Briefing)
**2026-05-10（前日）: トレードゼロ**。全セッション（東京・ロンドン・NY）を通じて一件も発火せず。直近週次累計はCutoff後N=17、WR=64.7%、PnL=**-9.1pips**（収益赤字継続）。信号発火の絶対量不足が最大の課題。
| Strategy | Pair | N | WR% | EV | 判定 |
| trendline_sweep | GBP_USD | 5 | 80.0% | **-0.22** | ⚠️ EV負（ELITE_LIVEだが乖離）|
> `vix_carry_unwind` はN=4ながら最高EV——平均回帰リスクを留意しつつ最注目。
- 前日（5/10）は全モード合計でトレードゼロ。エントリー条件未充足 or レジーム非適合の可能性。
- GBP_USD・EUR_USDはRANGING（ATR%ile 38-41%）、JPYペアはVOLATILE（74-78%）——両極が混在し、トレンドフォロー系とレンジ系どちらも条件が曖昧な中間状態にある可能性。
- BT: WR=63.5%（N=0とされているが基準値として記録済み）→ Live: WR=33.3%（N=3）
- ΔWR = **-30.2pp**。サンプルN=3で断定は不可だが、方向性は明確にネガティブ。GBP_USDのRANGINGレジームがモメンタム系に不利に作用している可能性が高い。

### 2026-05-11 (Post-London Report)
| 勝率 (WR) | **100.0%** |
| PnL | **+0.8 pips** |
> **統計的位置づけ**: N=1 は「データなし」水準。単一トレードのWR100%はノイズと同義。数値的事実として記録するに留め、戦略評価は行わない。
| 戦略 | ペア | 方向 | PnL | 成功要因 |
| streak_reversal | USD_JPY | BUY | **+0.8 pips** | OANDA_SL_TP決済が正常動作、スプレッド0.8pips以内に収まりネット正EV確保 |
| 本日累計 N=2, WR=50%, PnL | **-7.2 pips** |
| WR | 0% | 100% | ↑ 改善（N小により無意味） |
| PnL | **▲8.0 pips** | **+0.8 pips** | ↑ 回復基調 |

### 2026-05-11 (Post-NY Report)
| WR | — |
| PnL | 0.0 pips |
### セッション別PnL比較
| Session | N | WR% | PnL(pips) | 評価 |
| 合計PnL | **−7.2 pips** |
| WR | 50.0% |
| 最良セッション | London（+0.8 pips、WR 100%） |
| 最悪セッション | Tokyo（−8.0 pips、WR 0%） |

### 2026-05-12 (Pre-Tokyo Briefing)
前日（2026-05-11）は **2件のトレード、PnL合計 −7.2、WR 50.0%**。
| Strategy | Pair | N | WR% | EV | 判定 |
| trendline_sweep | GBP_USD | 5 | 80.0% | **−0.22** | EV負（N不足） |
| xs_momentum | GBP_USD | 3 | 33.3% | **−5.63** | 🔴 EV大幅負 |
> **全体集計（Cutoff後）**: N=16、WR=62.5%、PnL=**−20.9**
> WR62.5%にもかかわらずPnLがマイナスという典型的な **Payoff非対称問題**（負け時の損失が勝ち時の利益を大幅に上回る）。
### 課題①：`dt_sr_channel_reversal/EUR_JPY` — −8.0 (EV=−8.00)
- EUR_JPYは現在 **VOLATILE（ATR%ile 81%）**、SMAスロープ −0.00217 で下降トレンド中

### 2026-05-12 (Post-Tokyo Report)
| PnL | ¥0 |
| 勝率 (WR) | N/A |
- Fidelity Cutoff後のクリーンN蓄積中。全戦略で本日N=0であり、統計的判断の根拠がない
- OANDA転送率0%（SENT=0/50、全SKIP）はshadow_tracking=20件が示す通り、意図的シャドウ監視期間の継続であり、異常ではない
- BT vs Live乖離の`xs_momentum GBP_USD`（ΔWR=−30.2pp、N_Live=3）はN<10のため「データなし」扱い — 過剰反応禁止
- レジーム判断（EUR/JPY・GBP/JPYがVOLATILE、USD/JPYがRANGING高ATR）でパラメータ変更の必要性を示す構造的証拠は現時点で不十分
### 推奨戦略配分
- trendline-sweep (ELITE_LIVE): EUR_USD / GBP_USD

### 2026-05-12 (Post-London Report)
| PnL | **0.0 pips / $0.00** |
| 勝率 (WR) | **N/A** |
| PnL | $0 | $0 |
| WR | N/A | N/A |
### 推奨戦略配分
**⚠️ NO ACTION推奨（ただし条件付き）**
- **EUR_USD × session-time-bias** (EV=+0.215, RANGING適合)
- **USD_JPY × doji-breakout** (EV=+0.338, RANGING適合)

### 2026-05-12 (Pre-Tokyo Briefing)
| 前日PnL合計 | **-7.2 pips** |
| 全体WR | **50.0%** |
前日は2件のみ約定。streak_reversalがUSD_JPYで小幅勝利（+0.8）した一方、dt_sr_channel_reversalがEUR_JPYで大幅損失（-8.0）を記録。1勝1敗だが損失側のロスが大きく、PnL合計はマイナス。
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
| trendline_sweep | GBP_USD | 5 | 80.0% | **-0.22** | -1.1 | 🟡 EV要注意（N不足） |
| dt_sr_channel_reversal | EUR_JPY | 1+1=**2** | 0.0% | **-8.00** | -8.0 | 🔴 EV深刻（N不足） |
> **補足**: 全戦略でN<10。統計的判断ラインには到達していないが、EV方向の傾向として記録。全体EV = -20.9 / 16 ≒ **-1.31**（負）。
| BT期待値 | EV=+0.178（BT上は正だが極めて小さい）|

### 2026-05-13 (Pre-Tokyo Briefing)
- PnL: **+0.5pip** | トレード数: **1件** | WR: **0.0%**（1件・BEのみ）
- ny_close_reversal / USD_JPY がSELL→BREAKEVEN（+0.5）。実質利益ゼロ水準。
- 前日はシステム全体として**トレード機会の極端な枯渇**が続いており、ほぼ無活動の一日。
> N=17, 全体WR=58.8%, 累計PnL=**−20.4pip**
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
| trendline_sweep | GBP_USD | 5 | 80.0% | **−0.22** | −1.1 | 🟡 WR良好・EV要注意 |
| xs_momentum | GBP_USD | 3 | 33.3% | **−5.63** | −16.9 | 🔴 EV深刻・BT乖離警報 |
- 全戦略でN≥30未達。「判断可能」域に達した戦略はゼロ。

### 2026-05-13 (Post-Tokyo Report)
| PnL | 0.0 pips |
- Fidelity Cutoff（2026-04-08）以降のCleanデータN=0（本日セッション）であり、統計的判断の基礎がない
- ブロックは設計通りの防御動作であり、`VOLATILE`レジーム下では正常挙動
- `xs_momentum GBP_USD` はLive N=3、`vix_carry_unwind USD_JPY` はLive N=4 — いずれもN<10のため「データなし」扱い（判断不可）
- DD=28.01%のDD防御0.2xモード継続中 → リスクパラメータ触媒は禁止水域
| ペア | 現在レジーム | ロンドン移行予測 | 注意点 |
### 推奨戦略配分
→ `doji-breakout GBP_USD` — BT EV=+0.724は参考値として有望

### 2026-05-13 (Post-London Report)
| セッションPnL | **+14.9 pips** |
| 平均PnL/トレード | +4.97 pips |
| 戦略 | ペア | PnL | 件数 |
- **成功要因**: GBP_USDがRANGINGレジーム（ATR%ile=53%、SMA傾斜+0.208と緩やかな上昇）にあり、S/R+Fib水準がレジスタンスとして機能したSELL2発が共にOANDA_SL_TP決済で完遂。
- 特に1件目（+27.7 pips）はRR比が良好で、spread（1.3）対比でも十分なリターン。
| 戦略 | ペア | PnL | 件数 |
- **失敗要因**: RANGING環境（ATR%ile=53%）でモメンタム戦略を発動したが、方向性が持続せずSL_HIT。RANGINGレジームはモメンタム系にとって構造的不利環境であり、今回のSELL方向に対しGBP_USDのSMAは上向き（+0.208）—逆方向への偏りが原因。
### 推奨戦略配分

### 2026-05-13 (Pre-Tokyo Briefing)
前日（2026-05-12）はトレード**1件**のみ。`ny_close_reversal / USD_JPY` がBREAKEVEN着地（PnL +0.5pip相当）。全体WR 0%（勝ちなし）、PnL +0.5。実質的に**ほぼノートレード日**であり、システムはシグナル抑制状態で稼働中。
| Strategy | Pair | N | WR% | EV | 判定 |
> **全戦略でN<10**。統計的判断は一切不可。累積N=14は「観測開始直後」の水準。昇格基準（N≥30, EV≥1.0）到達まで最低16件以上追加が必要（最速戦略でも数週間単位）。
| ③ | **xs_momentum の連敗**: N=4でEV=-7.75は警戒水準。BTとのWR乖離が▲38.5ppと最大値 |
- `xs_momentum/GBP_USD`：N≥30まで積極的な信頼付与を保留。現状の-7.75 EVトレンドを継続監視
- hedge_block 発動回数は正常なリスク管理の証拠として評価可。対処不要
- shadow_tracking(18件)がOANDA転送の主要抑制因：設計通り動作
| 09:00〜11:00 | **東京セッション開幕**: USD/JPY・EUR/JPYのボラティリティスパイクに注意。ATR%ile高水準（78-83%）で既に拡張状態 |

### 2026-05-14 (Pre-Tokyo Briefing)
| PnL合計 | **+11.8 pips** |
| 全体WR | **50.0%** |
4件中2件の大勝（sr_fib_confluence GBP/USD、計+29.0）が全体を黒字に押し上げた。xs_momentumの-14.1損失が重しだが、sr_fib_confluenceが相殺を超えた日。実質的に**1戦略依存のPnL構造**。
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
| xs_momentum | GBP_USD | 4 | 25.0% | -7.75 | -31.0 | 🔴 BT乖離+EV負 |
**ポートフォリオ合計: N=14, WR=50.0%, 累積PnL=+1.0**
### 課題①：xs_momentum の負EV継続（最重要）
| WR_Live | 25.0% |

### 2026-05-14 (Post-Tokyo Report)
| WR | 100.0%（参考値：N<5） |
| PnL | **+1.9 pips** |
| 戦略 | ペア | 方向 | PnL | 成功要因 |
- **シグナル発生が極めて低調**：17モード稼働中（ONは12モード）で東京セッション成立トレードは1件のみ
- **ブロック主因**（参考）：
- `scalp_eur` / `scalp` / `scalp_5m`: `r2_shadow_demoted_cell`による大量ブロック（合計21件）
- `hedge_block` 多発（daytrade系4戦略で31件合計）
- `rnb_usdjpy`: `direction_filter`で7件全止め

### 2026-05-14 (Post-London Report)
| PnL (pips) | **0** |
| WR | **N/A** |
- **hedge_block**が合計1,059件（266+265+176+175+107）を超えており、**ロンドン全体を通じてヘッジポジション判定が継続していた**と推定。open tradesが0であることと合わせると、ヘッジ判定が「残存しているが実ポジションがない」状態の可能性がある。
- **max_open**系はscalp系で399件。仮にshadowトレードが内部で開いていればmax_openトリガーは説明可能。
- **r2_shadow_demoted_cell**が合計295件。複数戦略でdemotionが進行中であり、シグナル生成セルの品質劣化が顕在化している。
| PnL | +1.9 pips | 0 pips |
| WR | 100% (N=1) | N/A |
### 推奨戦略配分

### 2026-05-14 (Pre-Tokyo Briefing)
| PnL合計 | **+11.8 pips** |
| 全体WR | **50.0%** (2勝2敗) |
| Strategy | Pair | N | WR% | EV | PnL | 評価ステータス |
- **Reason: SL_HIT**。スプレッド1.3pipsで入場し、モメンタムが機能しなかった。
- GBP_USDのATR%ile=59%（中程度）で、RANGING環境下においてモメンタム戦略は不利なレジームにある。
- **対処**：現時点では判断を留保（N=1）。RANGINGレジーム継続中は同戦略のシグナルを慎重に観察。
### 課題②：dt_sr_channel_reversal（EUR_JPY）— SIGNAL_REVERSE -3.1 pips
- **Reason: SIGNAL_REVERSE**（エントリー後にシグナルが逆転）。EUR_JPY ATR%ile=83%（高ボラ）かつRANGING分類という矛盾した環境。

### 2026-05-15 (Pre-Tokyo Briefing)
| PnL合計 (2026-05-14) | **+1.9 pips** |
| 全体WR | **100%** (N=1, 統計的意味なし) |
> N=6, 全体WR=50.0%, 累計PnL=+14.2pips ※N<10は「データなし」として解釈
| Strategy | Pair | N | WR% | EV | PnL | 評価 |
| xs_momentum | GBP_USD | 1 | 0.0% | -14.10 | -14.1 | 📊 データなし（大損注意） |
- `direction_filter`（91件）と `r2_shadow_demoted_cell`（計129件）の2本柱がシステム全体の機会を圧迫。
- GBPペア系の `gbp_asia_flash_crash` ガード（計74件）が本日アジア時間にも継続する可能性大。ATR%ile: GBP/JPY=84%, EUR/JPY=83% と高ボラティリティ環境が継続しており、フラッシュクラッシュ保護が引き続き発動しやすい地合い。
- `r2_shadow_demoted_cell` ブロックが累積129件に達している。シャドウ降格セルの内容を確認し、過剰に広くなっていないか監視を続ける（コード変更なし）。

### 2026-05-15 (Post-Tokyo Report)
| PnL | **0** |
| WR | **N/A** |
- 本日東京セッションの N=0 はパラメータ問題ではなく、**レジーム・フィルター群が正常に機能した結果**として解釈可能
- Block Counts の主因は hedge_block（3件）・direction_filter（9件）・r2_shadow_demoted_cell（4件）であり、いずれも設計通りの防御ロジック
- データ不足（Cutoff後 累積N未充足）の状態でパラメータを触ることはサンプルバイアスを拡大させるリスクがある
- OANDA転送率 0%（全50件 SKIP）は shadow_tracking による正常なデモ運用継続状態であり、異常ではない
| GBP_JPY | RANGING | **84%** | 同上。JPYクロスは高ATR%ile帯にあり、ブレイクアウト方向次第でスラッページ拡大に注意 |
| GBP_USD | RANGING | **59%** | 中程度のボラティリティ。SMA20 Slope +0.00033（微弱上向き）でレンジ上限テスト注意 |

### 2026-05-15 (Post-London Report)
| PnL | **0 pips / ¥0** |
| 勝率 (WR) | **N/A** |
| PnL | ¥0 | ¥0 |
| WR | N/A | N/A |
### 推奨戦略配分
> **⚠️ NO ACTION推奨 — 17:22–19:00 UTC**
| ○ | `session-time-bias` | EUR_USD | NY時間帯はBT EV+0.215、条件合致なら有効 |
| 累計PnL | **¥0 / 0 pips** |

### 2026-05-15 (Post-NY Report)
| PnL | +0.0 |
| WR | — |
### セッション別PnL比較
| Session | N | WR% | PnL | 評価 |
- **本日合計PnL**: ±0
- **本日合計トレード数**: 0
- **本日WR**: 定義不能
- **最も成績が良かったセッション**: 該当なし（全セッション同一）

### 2026-05-18 (Pre-Tokyo Briefing)
- PnL合計: **¥0** | トレード数: **0** | WR: **N/A**
- 前日は全セッション（東京・ロンドン・NY）を通じて一切のシグナル発火なし。Block機構とシャドウ管理が完全に機能しており、静的な日となった。
> N=6合計、全体WR=50.0%、累計PnL=+14.2 pips
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
- **現状維持が正解**。前日ゼロトレードはシステムが「発火すべきでない環境と判断した」証拠。無理にトレードを求めない。
- Block件数の高さは「システムが機能している証拠」として肯定的に解釈する。
- `sr_fib_confluence (GBP_USD)` — レンジATR60%はSR反発環境として適切。現在唯一のEV+傾向戦略。
- `dt_sr_channel_reversal (EUR_JPY)` — RANGING+ATR84%はチャネル反転に構造的に合致。

### 2026-05-18 (Pre-Tokyo Briefing)
- **2026-05-17（前日）**: トレード **0件**、PnL **¥0**、WR **N/A**
- Cutoff後（2026-04-08以降）累計: **N=6、WR=50.0%、PnL=+14.2 pips**
- モード全25戦略中、稼働ON=23、OFF=2（daytrade_xau / scalp_xau / scalp_eurjpy）
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
- recent_emit 過多は「シグナル品質の問題」ではなく「抑制ロジックの感度設定の問題」として切り分けて観察継続
- hedge_blockはEUR_JPY集中ポジションリスクを示唆→ EUR_JPY系の方向確認を朝一で実施
- spread_gate作動（scalp系）は昨日のスプレッド環境を反映→ 本日のスプレッド状況を東京時間開始時に確認
- dt_sr_channel_reversal (EUR_JPY) : レンジ→チャネル反転に理論上適合

### 2026-05-18 (Post-London Report)
| 勝率 (WR) | 100.0% |
| 総PnL | **+13.3 pips** |
| 平均EV/トレード | +13.30 |
| 戦略 | ペア | PnL | Dir | 成功要因 |
- スプレッド1.3pips（scalp閾値30%基準では許容範囲内）
- GBP_USDはATR%ile 60%・RANGING レジームながら、momentumシグナルが単発で有効に機能
| WR | — | 100% |
| PnL | 0 | +13.3 |

### 2026-05-18 (Pre-Tokyo Briefing)
- **前日（2026-05-17）**: トレードゼロ。完全な非活性日。
- **Cutoff後累計（全期間）**: N=8、WR=62.5%、PnL=+28.8 pips
- 前日・当日早朝を通じてシステムはトレードを一切執行していない。サンプル蓄積が依然として深刻に不足している状態が継続中。
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
> 全戦略がN<10の「データなし」ゾーン。EVの優劣は現時点で統計的意味を持たない。
- トレードゼロの原因がレジームフィルター（全ペアRANGING＋高ATR）によるものか、シグナル閾値によるものか、を本日のログから確認する
- OANDA転送の主因「shadow_tracking（17件）」の実態——どの戦略がシャドウ期間中なのかを把握する
- OFFモードの3戦略について、意図的な停止かシステム異常かを確認する

### 2026-05-19 (Pre-Tokyo Briefing)
| 前日PnL合計 | **+14.6 pip** |
| 全体WR | **100.0%** |
| Strategy | Pair | N | WR% | EV | PnL |
> **全体（Cutoff後）**: N=8、WR=62.5%、PnL=+28.8 pips
⚠️ **統計的注意**: 全戦略でN<10。現時点では「傾向」すら読めない段階。EVの正負は参考値に留める。
| **09:00-11:00** | 東京セッション開始。USD_JPY・EUR_JPYでのATR急変に注意（現在81-86%ile＝既に高水準） |
`sr_fib_confluence` GBP_USDのEV=+14.50は表面上驚異的だが、N=2の数値は統計的にゼロ情報。`dt_sr_channel_reversal` EUR_JPYのEV=-3.10も同様にN=1で意味をなさない。現時点で昇格・降格を議論できる戦略

### 2026-05-19 (Pre-Tokyo Briefing)
前日（2026-05-18）は **2件のトレード、WR 100%、PnL +14.6 pips** で着地。
> **総計: N=8, WR=62.5%, PnL=+26.1**
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
**注目点：** `sr_fib_confluence` の EV=+27.70 は1件のみ。大勝ち1件として記録するが、統計的意味はゼロ。KBでのBT EV(EUR_USD=+0.103)と大きく乖離しており、アウトライヤーとして扱う。
| **xs_momentum の累積EV負** | N=2 で EV=-0.40 だが、前日単体では +13.3 と大勝ち → サンプルの非一貫性 | N=30 到達まで判断保留。昨日の大勝ちがサンプルを歪める可能性あり |
| EUR_JPY | RANGING | 86% | -0.00314 | **高ボラ×レンジ**: `dt_sr_channel_reversal`(BT EV=+0.178)は理論上有利だが、実績EV=-3.10(N=1)は警戒。hedge_blockで実質停止中 |
| GBP_USD | RANGING | 62% | -0.00178 | 中程度ボラ×レンジ: `doji_breakout`(BT EV=+0.724)・`trendline_sweep`(ELITE_LIVE BT EV=+0.599)は動作しやすい環境 |
| USD_JPY | RANGING | 81% | -0.00089 | 高ボラ×レンジ: `doji_breakout`(USD_JPY, BT EV=+0.338)は機能するが、hedge_blockの影響次第 |

### 2026-05-19 (Post-London Report)
| 勝率（WR） | 100.0%（1/1） |
| PnL | **+1.3 pips** |
| 戦略 | ペア | 方向 | PnL | 成功要因 |
> **注記**: `Reason: SL_HIT`はシステム上「相手のSLに到達 → WIN」を意味するWIN判定。スプレッド1.3pipに対してネットPnL+1.3pipはギリギリ正の摩擦調整EVを確保。
ただし本日累計（N=2, WR=50%, PnL=**-0.9 pips**）との差分から、**東京セッションに1件のLOSSトレード（推定 -2.2 pips）が存在**。ロンドン+1.3で部分挽回した形。
| WR | 0%（推定） | 100% |
| PnL | 約 -2.2 pips（推定） | +1.3 pips |
- **レジーム変化なし**: 全ペアRANGINGが維持された。EUR_JPY・GBP_JPYはATR86%ile（高ボラ気味）だが、SMA Slopeが全ペアマイナスでドリフトなし → レンジ内上下動が支配的。

### 2026-05-19 (Pre-Tokyo Briefing)
前日（2026-05-18）は **2トレード、PnL = +14.6 pips、WR = 100%**。
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
**総計: N=5, WR=80.0%, PnL=+15.6**
> ⚠️ **全戦略 N<10**。統計的判断基準に照らすと「データなし」フェーズ。EV値・WR値は参考値に留める。
- Cutoff後5件という蓄積は、昇格基準（N≥30）に対して **17%未満**。
- 稼働モードは25種（OFF除く23種）あるにもかかわらず、前日発火したのは **GBP_USD 1ペアのみ**。
- 多数のモードが「ON だが取引0」という状態が継続している。
- 前日の全収益は GBP_USD BUY 2件に依存。方向性（BUY）と通貨の集中が顕在化。

### 2026-05-20 (Pre-Tokyo Briefing)
| PnL合計（前日） | **-0.9 pips** |
| 全体WR | **50.0%** |
| Strategy | Pair | N | WR% | EV | 判定 |
**統計判断**: 全戦略がN<10。**「データなし」区分**。いかなるEV値も意思決定に使用不可。Cutoff後累計N=5は深刻なサンプル不足。
### 課題②: trendline_sweep の SIGNAL_REVERSE LOSS
前日LOSS (-2.2) の理由が `SIGNAL_REVERSE`。これはポジション保有中にシグナルが反転したケースで、RANGING相場での典型的なフェイク。BT想定EV +0.599（GBP_USD）との乖離は現状N=2では判断不能。
- リスクフィルター（hedge_block, spread_guard, r2_shadow_demoted_cell）が正常機能しており、

### 2026-05-20 (Pre-Tokyo Briefing)
- **PnL**: −0.9 pips（WIN +1.3 / LOSS −2.2）
- **トレード数**: 2件（前日 2026-05-19）
- **全体WR**: 50.0%（1勝1敗）— 極小サンプルにつき統計的意味なし
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
> ⚠️ **全戦略 N<10**。Fidelity Cutoff後の有効サンプルが著しく少なく、EV・WRは参考値に過ぎない。統計的判断可能水準（N≥30）まで遠い。
### 課題①: trendline_sweep GBP_USD — SIGNAL_REVERSE Loss
| 負けトレード | BUY → SIGNAL_REVERSE → −2.2 pips |
| 構造的問題 | Spread 1.3pip / EV −0.45 → 摩擦調整後EVが既に負域に近い |

### 2026-05-20 (Post-London Report)
| **セッションPnL** | **+38.8 pips** |
| 戦略 | ペア | 方向 | PnL | 成功要因 |
**本日のPnL牽引役は`vix_carry_unwind`の単発+30.1pipsが全体の77.6%を占める。**
| 戦略 | ペア | 方向 | PnL | 失敗要因 |
| **xs_momentum** | GBP_USD | BUY | **-0.6 pips** | SIGNAL_REVERSEで決済 — GBP_USDがRANGING（SMA20スロープ-0.00211、下向き）の中でBUYモメンタムが失速し、シグナルが短期で反転。損失は軽微（-0.6pips）でリスク管理は機能 |
> **注記**: GBP_USDはスプレッド1.3pips環境。EV=-0.60はスプレッドコストほぼイコールで、実質シグナル価値ゼロに近い。
| **WR** | データなし | 75.0% |
| **PnL牽引** | 不明 | vix_carry_unwind単発が全体を牽引 |

### 2026-05-20 (Pre-Tokyo Briefing)
PnL合計 **−0.9 pips**、WR **50%**、EV **−0.45**。
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
> 昇格基準（N≥30 & EV≥1.0）まで最大残り **29件**。
| # | Dir | Outcome | PnL | Reason | Spread |
| 2 | BUY | LOSS | −2.2 | SIGNAL_REVERSE | 1.3 |
- `SIGNAL_REVERSE`による−2.2は典型的なRANGINGレジームでの「だまし」パターン。GBP_USDはATR%ile=59%・SMA20 Slope=−0.00223（緩やかな下落傾向）でトレンドの方向性が曖昧。
- スプレッド1.3に対してWINが+1.3（RR比≈1:1未満）は摩擦調整後のEVがほぼゼロ。Scalp閾値30%との対比ではspread_guardが機能しているか要確認。
- RANGING継続中はtrendline_sweepのシグナル精度が低下しやすい。N蓄積を優先しつつ、EV推移を注視する。

### 2026-05-21 (Pre-Tokyo Briefing)
| PnL合計 | **+38.8 pips** |
| 全体WR | **75.0%** |
前日はトレード数が極めて少ないながらも、`vix_carry_unwind` の+30.1という大型勝ちトレードに牽引されてPnLはプラス。実質的には3勝1敗で、全体EVは1件あたり+9.7pip。ただし本数が4件という水準ではノイズと信号を区別できない。
| Strategy | Pair | N | WR% | EV | PnL |
- `trendline_sweep`（ELITE_LIVE）: Cutoff後N=2、EV=-0.45。BT実績（EUR_USD EV=+0.927）と比較して懸念があるが、N不足で断言不可
- `vix_carry_unwind` の+30.1は単発の大勝利。平均回帰を考慮するとこの水準の期待値維持は過信禁物
- 累計N=8件。**昇格基準（N≥30）まで残り22件以上**が必要な状態が全戦略で継続
| EUR_JPY | RANGING | 74% | -0.00303（下落傾向） | `vsg_jpy_reversal`・`dt-sr-channel-reversal`は逆張り適性あり。ただしSlope負でトレンドのバイアスに注意 |

### 2026-05-21 (Pre-Tokyo Briefing)
| PnL合計 | **+38.8 pips** |
| 全体WR | **75.0% (3/4)** |
前日は少数精鋭ながら高品質なエントリー。`vix_carry_unwind` の+30.1が全体PnLを牽引。唯一の損失は`xs_momentum`のSIGNAL_REVERSE（−0.6、軽微）。
> **N=8, WR=75.0%, 累計PnL=+52.5**（Shadow除外、XAU別枠）
| Strategy | Pair | N | WR% | EV | 判定 |
### 課題①：xs_momentum の損失（SIGNAL_REVERSE）
- BUYエントリー直後にシグナル反転 → −0.6 pips（損失は軽微）
- **GBP_USDはRANGING / SMA20下向き(-0.00223)**：トレンドフォロー系には逆風レジーム

### 2026-05-21 (Post-London Report)
| PnL | **0 pips / 0円** |
| 勝率 (WR) | **N/A** |
- 全ペアの **SMA20 Slope が負（下降傾向）** → トレンドフォロー系フィルターがブロック
- EUR_JPY / GBP_JPY の **ATR%ile=74%** → スプレッド乖離によりspread_guard発動の可能性
- **RANGING判定が全5ペアで共通** → モメンタム系戦略の入口条件を満たせず
- daytrade_xau / scalp_xau / scalp_eurjpy が **OFF状態** → カバレッジ縮小
| PnL | 0 | 0 |
| WR | N/A | N/A |

### 2026-05-21 (Pre-Tokyo Briefing)
データ取得失敗により、前日PnL・トレード数・WRの確定値は算出不可。
> ⚠️ 以下はバックテスト値またはKB記録値。Cutoff後のライブN/WR/EVは今回取得不可。
| Strategy | Pair | BT EV | BT WR | Live Status |
| Strategy | Pair | BT EV | BT WR | Live N | 判定 |
- **API障害の確認が最優先**: Renderサービスの再起動・ヘルスチェックログを直接確認する
- **DD防御継続**: APIが復旧してもDD=65%超は異常水準。サイズ0.2x維持を確認
- **BT陰転戦略**: Live N≥30データが取得可能になり次第、降格判断を即時実施
- DD防御0.2xモード中: 多数のシグナルがsize=0でSKIPされている可能性

### 2026-05-22 (Pre-Tokyo Briefing)
- PnL合計: ±0.0 | トレード数: 0 | WR: N/A
- Cutoff後累計（全期間）: N=5 / WR=80.0% / PnL=+40.1
- 前日はBlock機構とShadow Trackingが全トレードを抑制。実質的なブランクデイ。
| Strategy | Pair | N | WR% | EV | PnL | 統計判定 |
> **全戦略 N=1。統計的有意性ゼロ。** 昇格基準（N≥30 & EV≥1.0）まで最短でも29件の追加蓄積が必要。
- **hedge_block（計234件）が最大抑制要因。** daytrade_eur / daytrade_gbpusd / daytrade の3系統で集中発生。全通貨ペアが同方向（USD弱・円高傾向）に傾いており、ヘッジ判定が連鎖トリガーされている可能性が高い。
- **r2_shadow_demoted_cell（計149件）が第2要因。** scalp系全般でシャドウセルが降格済みのため、シグナル生成自体が止まっている。
- **direction_filter（102件）：** rnb_usdjpyはトレンドに逆らうレンジ戦略のため、USD_JPYの現在のレジームでフィルター多発は合理的。ただしカウント規模が異常に大きく、連続拒否状態。

### 2026-05-22 (Pre-Tokyo Briefing)
**2026-05-21（前日）: トレードゼロ。** PnL = 0、N = 0、WR = N/A。
Cutoff後の累積実績は **N=5、WR=60.0%、PnL=+38.3pip相当** にとどまる。
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
> ⚠️ **全戦略 N=1** — 統計的判断は一切不可。傾向値としても無意味。昇格基準（N≥30 & EV≥1.0）まで残り **29件以上**。
- **hedge_block頻発**: GBP_USD・GBP_JPY・EUR系で逆ポジション競合が継続中。今日も同様の市場構造が続く可能性が高い。**ブロックは正常動作**として受容し、強制突破を試みない。
- **shadow降格セル**: scalp/scalp_eurのr2_shadow_demoted_cellが20件。これらセルは意図的に抑制されており、**現状維持が正解**。
- **前日ゼロ発火**: 市場条件の問題（レンジ継続）であり、システム障害ではないと判断。
- **shadow_tracking 100%** がスキップ原因 → システム設計通りの動作

### 2026-05-22 (Post-London Report)
| 勝率 (WR) | 0.0% |
| 総PnL | **-0.5 pips** |
| EV（単純） | -0.50 |
唯一のトレードが BREAKEVEN (-0.5 pips) であり、「成功」に分類できるエントリーはゼロ。
| 戦略 | ペア | PnL | 失敗要因 |
| `trendline_sweep` | GBP_USD | **-0.5 pips** | `SIGNAL_REVERSE`（エントリー直後に方向転換）＋ spread 1.3 pips で実質コスト超過 |
- Outcome = `BREAKEVEN` だが、PnL = -0.5 は **spread摩擦の直接コスト**を示す。エントリーした優位性が即座に否定されたケース。
- GBP_USD のレジームは `RANGING`（ATR%ile=57%、SMA20 Slope=-0.00190）。`trendline_sweep` はトレンド追随系であり、**RANGINGレジームでの構造的不利**が顕在化。

### 2026-05-22 (Pre-Tokyo Briefing)
前日（2026-05-21）はトレード**ゼロ**。エントリー条件を満たしたシグナルは発生しなかった。Cutoff後累計はN=5、PnL=+38.3（WR 60.0%）と極めて少数。前日を含めた直近の無発火は、全ペアがRANGINGレジームに収束していることと整合的であり、戦略ロジックが機能停止しているわけではない。
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
> **統計的判断**: 全戦略N=1。「データなし」扱い。いかなる戦略評価も統計的根拠ゼロ。`vix_carry_unwind`のEV=+30.10は外れ値の可能性を排除できない。
- **トレードゼロ継続**: 5月21日は全セッションで無発火。エントリー条件（レジーム・モメンタム・spread_guard等）を突破するシグナルが存在しなかった。
- **N蓄積が停滞**: Cutoff後累計N=5。昇格基準N=30に対し残り25件。このペースでは統計的判断可能な閾値到達に数週間を要する。
- **OANDA転送率0%**: 50件全件がSKIPされており、本番資金でのトレードは一件も実行されていない。
- 現時点ではシステムの動作を信頼し、**レジームがトレンドへ移行する兆候を監視**することが最優先。
- トレードゼロ自体は「誤作動」ではなくRANGING環境への適応として解釈する。ただし無発火が長期化する場合はエントリー閾値の緩み・タイトさの構造的問題として改めて確認が必要（コード変更は別途判断者へ委ねる）。

### 2026-05-25 (Pre-Tokyo Briefing)
**2026-05-24（前日）: トレードゼロ。PnL = ¥0、N = 0、WR = N/A。**
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
> **全体**: N=5、WR=60.0%、PnL=+38.3
- `r2_shadow_demoted_cell`が71件ブロック → Scalp系のShadow降格セルが実効的な取引機会を大幅に制限している。降格基準の妥当性を確認し、一定期間経過後の再昇格プロセスが機能しているかを点検すべき。
- N蓄積が進まない最大の原因は「フィルタ層の多段重複」。今日も同様の低約定環境が続く可能性が高い。
- **MR（平均回帰）系戦略に相対的に有利**な環境。ただし全ペアの下落バイアスは、Longエントリー偏重の戦略にとってはコスト要因。
- **トレンドフォロー系（trendline_sweep・xs_momentum）には不利なレジーム**。GBP_USDの trendline_sweep EV=-0.50はレジームと整合的。
- EUR_USDのATR%ile=31%は特に低い。Scalp系のスプレッド対EV比が悪化しており、`scalp_eur`が`r2_shadow_demoted_cell`で多数ブロックされているのと符合する。

### 2026-05-25 (Pre-Tokyo Briefing)
| PnL | **±0** |
| WR | **N/A** |
> **注意**: 全戦略N<10 — 統計的には「データなし」フェーズ。EVは参考値として記載。
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
- **Sentinel N蓄積進捗**: 全戦略N=1。昇格基準（N≥30）まで残り**29件以上**。現時点で昇格・降格判断は不可。
- **累計50トレード中、Cutoff後有効分はわずか5件（10%）** — クリーンデータの蓄積が極めて限定的。
- **hedge_block多発**は「既存ポジションがある」ことを示唆するが、現在Open Trades=0。**昨日以前に蓄積されたブロック履歴**がカウントに残っている可能性が高い。本日はポジションゼロから再スタートのため、hedge_blockは解消方向へ。
- **direction_filter × 7**（rnb_usdjpy）はUSD/JPYのレンジ相場（ATR%ile=45%、SMA20 Slope≒-0.0006）との整合性あり。強い方向性なし → フィルターが機能している正常動作と判断。

### 2026-05-25 (Post-London Report)
| セッション内PnL | **±0** |
| WR | **N/A** |
| PnL | ±0 | ±0 |
| WR | N/A | N/A |
- **全5ペアがRANGING**（ATR%ile: EUR_USD=31% ← 最低水準、GBP_JPY=64% ← 相対的に動意あり）
- **全SMA20 Slopeがマイナス**（-0.00055〜-0.00283）→ トレンドフォロー系は構造的逆風
- ロンドンフィックス（UTC 16:00）前後でGBP/JPY系が若干揺れた可能性はあるが、ブロックにより捕捉されず
- ロンドンクローズ後、EUR/GBP系の流動性は低下

### 2026-05-25 (Pre-Tokyo Briefing)
| PnL合計 | **¥0** |
| 全体WR | **N/A** |
前日（2026-05-24）はシステム全体でトレード実行ゼロ。前々日以降もCutoff後の累計トレードは **trendline_sweep / GBP_USD の1件のみ**（PnL=-0.5）という極めて薄いデータ環境が継続している。
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
> **統計的判断**: 全戦略でN<10。「傾向」すら語れる段階ではない。EV=-0.50 は1件の結果に過ぎず、戦略評価として無意味。
| **session-time-bias（SENTINEL）** | 🟡 中立 | 時間帯バイアスはレジームに相対的に非依存。ただしボラが低いためPnL絶対値が縮小 |
| **dt-bb-rsi-mr（USD_JPY）** | 🟢 有利 | Mean Reversion系はRANGINGで最も機能する。ただしBTデータのEVが低い（-0.023〜-0.135）点に注意 |
| 時間帯（JST） | 内容 | 注意点 |

### 2026-05-26 (Pre-Tokyo Briefing)
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
**全戦略合計**: N=1、WR=0.0%、累積PnL=-0.5
> ⚠️ **Cutoff後の有効データが極端に少ない。** N=1は統計的に「データなし」と同義。昇格基準（N≥30 & EV≥1.0）・降格基準（N≥30 & EV<-0.5）いずれにも到達していない。
**全ペア共通観察:** SMAスロープが全ペアでマイナス（下向きドリフト）。レンジング環境下でのトレンドフォロー系戦略は構造的に不利。`ELITE_LIVE`の`trendline_sweep`でさえN=1/EV=-0.50という現状。
| 時間帯（JST） | 内容 | 注意点 |
**レジーム遷移リスク:** GBP/JPY（ATR64%）とEUR/JPY（ATR57%）はレンジからブレイクアウトへ移行する潜在エネルギーを持つ。本日の欧州～NYセッションでのボラティリティ拡大には注意。ただし**方向判断は現時点で不可**（全ペアSMAスロープがマイナス基調）。
- 現在N=1（Cutoff後）→ **残り29件**
- 前日トレードゼロが連続する場合、到達時期は不定

### 2026-05-26 (Pre-Tokyo Briefing)
| 前日 PnL | ±0 |
| 全体 WR | — |
**Cutoff後（2026-04-08〜）の累積実績もN=2、PnL=−7.6pips と事実上トレードゼロ状態が継続。** システムは稼働中（24モード ON）だが、実取引はほぼ発生していない。
| Strategy | Pair | N | WR% | EV | PnL |
> **統計的判断**: N=2は「データなし」扱い。いずれの戦略も判断基準（N≥30）に遠く届かず、WR・EVの数値は統計的に無意味。EV=−7.10（ema200, USD_JPY）は単発の外れ値として保留。
- シグナル発生有無をログで確認し、「シグナルは出たがフィルターで弾かれたのか」vs「そもそもシグナル条件が未成立なのか」を区別する（ログ分析限定、コード変更なし）
- OANDA接続の NAV=None を監視継続
| 16:00〜18:00 | ロンドンオープン。EUR_USD・GBP_USDのレンジブレイク試行に注意 |

### 2026-05-26 (Post-London Report)
| セッション内PnL | **0 pips** |
| セッション内WR | **N/A** |
| WR | 0.0% (1件・損失) | N/A |
| PnL | -7.1 pips | 0 pips |
- **レジーム変化なし**：全5通貨ペアが揃って`RANGING`を維持。SMAスロープは全ペアでマイナス（弱下降バイアス）。ATR%ileはGBP_JPY 64%・GBP_USD 57%・EUR_JPY 57%と中程度。レンジの「深さ」は浅くなく、ブレイクアウト戦略には依然として厳しい地合い。
- 東京→ロンドンで**WRが改善する材料なし**。本日は東京の1件損失のみで、ロンドンは完全沈黙。
- `rnb_usdjpy:direction_filter`の94件は、USD/JPY（ATR%ile 45%・RANGING）がRNB戦略の発火条件を一切満たせない状態を端的に示す。
### 推奨戦略配分

### 2026-05-26 (Pre-Tokyo Briefing)
- **前日（2026-05-25/26）トレード数**: 0件（全モード）
- **PnL合計**: ±0
- **全体WR**: N/A（データなし）
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
**統計的判定**: N=2は「データなし」として扱う（N<10）。EVの正負に関わらず、いかなる判断も下せない水準。
- **OANDA接続の実態確認**: NAV=None, Balance=Noneは口座情報取得の失敗を示す。APIキー有効性・環境変数をオペレーショナルに確認すべき
- **SKIP=100%の原因特定**: block_reasonが `shadow_tracking` のみ — これは全トレードがシャドーモード判定されていることを意味する。本番フラグの設定を確認すべき
- **エントリーゼロ**: レジーム・フィルター状況から自然抑制の可能性があるが、ゼロが2日以上継続している場合、パラメータが過剰に保守的になっている可能性を疑うべき

### 2026-05-27 (Pre-Tokyo Briefing)
| PnL合計（前日） | **-7.1 pips** |
| 全体WR | **0.0%** (1/1 LOSS) |
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
`ema200_trend_reversal`はBTデータでもUSD_JPY EV=-0.183と元々マイナスEV。KB上でPAIR_PROMOTED扱いだが、本番では唯一の発火がロスで終了。本番N=1のため判断不能だが、BT数値自体が悪い点は要警戒。
| 時間（JST） | セッション | 注意点 |
- **全ペアRANGING継続中**。ATR%ile が GBP_JPY 60%を除いて24〜47%と低位。EUR_USD 24%は特に注意——スプレッドに対するペイオフが薄く、scalp系の誤発火時のダメージが相対的に大きい。
- **daytrade_eurgbp:regime_squeeze_mr が40件**。EUR_GBPがスクイーズ状態にあることを示す。ブレイクアウトが来れば方向が出やすいが、それまでは誤シグナル多発帯。

### 2026-05-27 (Pre-Tokyo Briefing)
前日（2026-05-26）のトレードは**1件のみ**。`ema200_trend_reversal / USD_JPY / SELL` が `TIME_DECAY_EXIT` で決済され、**PnL = -7.1pip**（損失）。WR = 0%。システム全体はほぼ停止状態に近く、実質的にトレードが機能していない日であった。NAV = **¥301,073** は前回比ほぼ横ばい。
| Strategy | Pair | N | WR% | EV | PnL |
**⚠️ 統計的判断不能**: 全戦略 N=1。バックテスト上の ELITE_LIVE（trendline_sweep）も本番では N=1、EV=-0.50 と振るわないが、これは**完全にサンプル不足**であり評価不能。
- 25モードが稼働中にもかかわらず、実際のトレードは1件。
- Block Countsが高水準（TOP1: `daytrade_eur:hedge_block=35`、`rnb_usdjpy:direction_filter=33`、`daytrade_eurjpy:recent_emit=32`）であり、エントリー候補はあるが**内部フィルターで全て遮断**されている。
- `recent_emit` ブロックが複数戦略で発生（eurjpy=32, eurgbp=22, nzdusd=14, gbpusd=14）→ **同一方向シグナルの短期集中による連続発火抑制**が主因と見られる。
- 前日唯一のトレードが `TIME_DECAY_EXIT`（時間切れ決済）で終了。
- ポジション方向（SELL）はRANGING レジーム下のUSD_JPY。SMA20 Slope = -0.00071（ほぼフラット）であり、トレンドフォロー系戦略が不利な局面。

### 2026-05-27 (Post-London Report)
| セッション内PnL | **0.0 pips** |
| セッション内WR | **N/A** |
- 全25モード中、稼働中23モード（daytrade_xau・scalp_xau・scalp_eurjpyはOFF）がフル稼働したにもかかわらず、いずれも発火せず
- 本日唯一のトレード（N=1、PnL=-6.8pips、WR=0%）はセッション**外**（UTC 07:00以前）の発生と推定される
| PnL | -6.8pips | 0.0pips |
| WR | 0% | N/A |
- **EUR/USD（ATR%ile 24%）**: ロンドン不発後のNYは値幅圧縮が継続しやすい。ブレイクアウト系の誤発火リスクが高い状態
- **GBP/JPY（ATR%ile 60%）**: 相対的に動きやすい唯一のペア。ただしSMAスロープがマイナス（-0.00184）で方向性は下向き弱い

### 2026-05-27 (Pre-Tokyo Briefing)
- **PnL合計**: -7.1 pips | **トレード数**: 1件 | **全体WR**: 0.0%
- 唯一のトレードは `ema200_trend_reversal / USD_JPY SELL` が `TIME_DECAY_EXIT` で損切り（-7.1 pips）
- 活動はほぼ停止状態。Cutoff後累積N=2、累積PnL=-13.9 pips
| Strategy | Pair | N | WR% | EV | PnL |
> ⚠️ **統計的判断不能域**: N=2はデータとして扱わない。EVは参考値に留める。
- **全5ペアがRANGING**。Slope全マイナスでトレンドなし。
- **ATR%ile最大=GBP_JPY 60%**——唯一の相対高ボラペア。Scalp系の機会軸。
- **EUR_USD 22%ile**は要注意。スプレッドコストが相対的に大きくなる水準。

### 2026-05-28 (Pre-Tokyo Briefing)
| 前日（2026-05-27）PnL合計 | **-6.8 pips** |
| 全体WR（前日） | **0.0%**（1/1 LOSS） |
Cutoff後累計でも **N=2, WR=0%, PnL=-13.9 pips**。実質的に統計的判断可能な蓄積データは存在しない段階。
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
> **注意**: いずれも N=1。統計的に「データなし」の扱い。EV・WRに意味はない。
- 全戦略で N=2 / 30 → **昇格基準まで残り28件**
- 現在の蓄積ペース（直近観察）: 1〜2件/日 → **最短15〜28日以上**でN=30到達見込み
- ブロック状況はシステム設定の問題であり、コード変更なしには変化しない。**本日も低約定数を前提として運営**

### 2026-05-28 (Pre-Tokyo Briefing)
- **PnL**: -6.8 pips（1トレード）
- **トレード数**: 1件（全期間累計: 3件）
- **全体WR**: 0.0%（前日）/ 33.3%（Cutoff後累計）
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
- EUR_JPY RANGING環境での`sr_anti_hunt_bounce`のBUYシグナル品質を注視する（次のエントリーで再検証）
- トレード頻度が低い根本原因（フィルタ過剰かシグナル非生成か）を確認する価値がある
| NY Session（JST 21:00〜） | GBP_USD, GBP_JPYのボラ変動に注意。RANGINGからのブレイクアウトフェイク多発帯 |
- **Live転送率4%は実質ゼロ運用**。50件中48件がデモ止まり。

### 2026-05-28 (Post-London Report)
| **セッション PnL** | **+0.8 pips** |
| **WR** | **50.0%** |
| PnL貢献 | +13.2 pips（累計+14.0 - ロンドン+0.8） | +0.8 pips |
| WR推定 | 100%（1勝0敗） | 50%（1勝1敗） |
- **現在**: 全5ペアがRANGING、SMA20 Slopeは全ペア負（緩やかな下落トレンド）
- **NY移行時の変化予測**: NY Open（UTC 13:00）前後はロンドンFixingとNY参入でボラ一時拡大の可能性があるが、ATR%ile 22〜47%という現環境は構造的にボラ抑制。USD/JPY=159.518、EUR/USD=1.16258ともにキーレベルから離れており、大幅なレジーム変化は期待薄。
- **GBP_JPY（ATR%ile=60%）** が唯一相対的に高ボラ水準。NYでのリスクオフ/オン転換に最も敏感な通貨として要注意。
### 推奨戦略配分

### 2026-05-28 (Pre-Tokyo Briefing)
- **PnL合計**: -6.8 pips | **トレード数**: 1件 | **全体WR**: 0.0%
- 前日（2026-05-27）はEUR/JPY `sr_anti_hunt_bounce` の単発トレードのみ。SL_HITで終了。
- Spread 1.8は閾値（DT=20%ルール）に対し許容範囲内だが、シグナル自体の精度が問題。
| Strategy | Pair | N | WR% | EV | PnL |
> ⚠️ **全戦略N=1。統計的判断は一切不可能。** 全て「データなし」カテゴリ（N<10）。EV・WR数値の解釈は行わない。
- EUR/JPYは引き続きRANGING（ATR%ile=41%）かつSMA20下向き。BUY系逆張り戦略の発動には慎重な見方が必要。
- `sr_anti_hunt_bounce`はCutoff後N=1（全期間でも判断不可）。昇格基準（N≥30）まで実績蓄積が最優先。
| 時間帯 (JST) | セッション | 注意点 |

### 2026-05-29 (Pre-Tokyo Briefing)
- **前日（2026-05-28）**: 3トレード、PnL **+14.0**、WR **66.7%**
- 内訳：bb_rsi_reversion (EUR/USD WIN +3.8, USD/JPY LOSS -3.0)、dt_sr_channel_reversal (EUR/JPY WIN +13.2)
- Cutoff後累計: **N=5、WR=40.0%、PnL=+0.1**（有意判断不可レベル）
| Strategy | Pair | N | WR% | EV | 判断 |
| EUR_USD | RANGING | 22% | -0.00174（下向き） | ATR%ile低水準＝**スプレッド負荷が相対的に大きい**。bb_rsi_reversionのEV棄損リスク |
**全5ペアがRANGING**。トレンドフォロー系戦略（ema200_trend_reversal、session_time_bias等）には**構造的不利**な環境。リバーサル系（bb_rsi_reversion、dt_sr_channel_reversal）が相対的に適合するが、ATR%ile低水準ペアではR/Rが圧縮されている点に注意。
| 時間帯（JST） | 注意点 |
| **レジーム遷移リスク** | ATR%ile 22%（EUR_USD）は底値圏。経済指標等でブレイクアウト発生時、scalp系のspread_guard発動に注意（閾値30%） |

### 2026-05-29 (Pre-Tokyo Briefing)
- **2026-05-28 成績**: トレード数 N=3、PnL **+14.0 pips**、WR **66.7%**
- 勝ちトレード: bb_rsi_reversion/EUR_USD (+3.8)、dt_sr_channel_reversal/EUR_JPY (+13.2)
- 負けトレード: bb_rsi_reversion/USD_JPY (-3.0)
- 全体として小幅プラスで着地。EUR_JPYの大勝ちが全体牽引。
> **注意: 全期間 N=4、前日 N=3。統計的判断には到底不足（全戦略「データなし」水準）。数値は参考値のみ。**
| Strategy | Pair | N | WR% | EV | PnL | 判断水準 |
**集計サマリー（Cutoff後）**: N=4 / WR=50.0% / PnL=+7.2
> N=1 per cell。WR・EVは完全にノイズ。昇格・降格判断はいずれも不可。

### 2026-05-29 (Post-London Report)
| PnL | **データなし** |
| WR | **データなし** |
**所見:** Renderのスリープ復帰失敗、またはOANDA接続断の可能性が高い。DD=65.07%による **0.2x防御モード**が継続中であれば、ポジションサイズが大幅抑制されており、仮にトレードが発生していてもPnLインパクトは軽微。
| 有利戦略（BT根拠） | session-time-bias(USD_JPY EV+0.580)、doji-breakout | trendline-sweep(EUR_USD EV+0.927)、squeeze-release |
> ロンドン時間はATR拡大により **trendline-sweep / squeeze-release-momentum** がBT上最も高EVを示す帯域。ただし現在DD防御モード下では恩恵が0.2xに圧縮される。
- ロンドン・クローズ（UTC 16:00）通過後は **ATR縮小フェーズ**へ移行が通常パターン
- NY Mid（18:00-21:00 UTC）は経済指標次第で急騰・急落リスク。2026-05-29時点のイベントカレンダーは確認不能だが、月末フロー（5月末）による **USD需給変動** に注意
### 推奨戦略配分

### 2026-05-29 (Pre-Tokyo Briefing)
| PnL合計 | **+14.0 pips** |
| 全体WR | **66.7% (2W/1L)** |
3件という極小サンプルだが、**dt_sr_channel_reversal** の+13.2がPnLの大半（94%）を牽引。実質的に1トレードの勝敗でセッション全体が決まる構造が続いている。
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
- Cutoff後4件で WR=25%、EV=-1.75
- USD_JPY は **RANGING（ATR%ile=30%、SMA Slope=+0.00097 でほぼフラット）** — Mean-Reversionロジックには条件が整っているはずだが、実績は逆
- **考えられる構造問題**：スプレッド摩擦（都度0.8）、レンジでもSL幅がボラに対して狭すぎる可能性
- 24時間で3件はシステムが「動いている証拠を出していない」レベル

### 2026-06-01 (Pre-Tokyo Briefing)
前日（2026-05-31）は**トレードゼロ**。システムは稼働中だが、全モードでシグナル未発生のまま終了。累積Cutoff後データはN=7、PnL=+3.2pip（WR=42.9%）と依然として極薄サンプル状態が継続している。
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
**全体: N=7 / WR=42.9% / EV=+0.46（平均） / PnL=+3.2**
> ⚠️ **統計的判断基準との対照**: N<10は「データなし」扱い。現時点で「判断可能」な戦略は存在しない。EV数値は参考値にとどめる。
**本日の対処（観察上の注意点）:**
- hedge_blockの集中は**ヘッジポジションとの方向衝突**を示す。OANDA Open Trades=0なので、デモ側の内部ヘッジロジックが連鎖している可能性を注視
- `r2_shadow_demoted_cell`ブロック多数 → Scalp系はSentinel N蓄積がほぼ止まっている状態
- **全ペアRANGING**。ATR%ile が26〜52%という狭いレンジ内に集中しており、**ボラティリティ圧縮局面**が継続。

### 2026-06-01 (Pre-Tokyo Briefing)
| 本日累積PnL（Cutoff後全期間） | **+10.8 pips** |
| 全体WR | **57.1%** |
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
**全戦略合計N=7**。昇格基準（N≥30 & EV≥1.0）・降格基準（N≥30 & EV<-0.5）に達する戦略は現時点でゼロ。統計的判断は不可能な段階。
- **Trend-following系戦略に不利**: Scalp系のブレイクアウト戦略が機能しにくい
- **Reversion系に理論上有利だが**: EUR_USD・GBP_USDの下落slope（-0.0015前後）は「緩やかなトレンド内レンジ」を示唆。純粋なRANGINGではなく方向感が薄い下落ドリフト
- **rnb_usdjpy**: USD_JPYのみ微上Slopeでdirection_filterがやや緩和される可能性。ただしATR31%は低水準でScalp利幅も限定的
- Live Rate 32%は低いが、主因は **shadow_tracking（6件）** — Sentinel審査中の戦略がデモ止まりになっている正常動作

### 2026-06-01 (Post-NY Report)
| 勝率 WR | 33.3% |
| PnL | **−8.3 pips** |
| 戦略 | ペア | 方向 | PnL | 成功要因 |
- EUR/JPYはSMA20 Slope = −0.00051と下落バイアスが弱く、レンジ内での反発余地があった点が奏功。
| 戦略 | ペア | 方向 | PnL | 失敗要因 |
- Spread 0.8pipsは許容範囲内（Scalp閾値30%に対し問題なし）だが、EV = −5.10/トレードは構造的に深刻。
- 2連続同一ペア・同一方向（SELL）は通貨リスク集中の典型パターン。
### セッション別 PnL 比較

### 2026-06-01 (Pre-Tokyo Briefing)
Cutoff後累計: N=19, WR=57.9%, PnL=+26.5pip（累計黒字維持）
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
> **全戦略でN<30。判断可能領域に到達した戦略はゼロ。現時点でのEV値は参考値に過ぎない。**
- モード別ステータス表でRunning=ON のモードが多数稼働中にもかかわらず執行ゼロ
- Block Countsに `rnb_usdjpy:direction_filter` が12件 → フィルタが厳格に機能し、シグナル自体はあったが全てブロック
- レジーム：全ペアRANGING（ATR%ile: USD_JPY=21%, EUR_USD=26%）→ トレンド系戦略がシグナルを生成しにくい環境
- レンジ環境での執行能力を持つ戦略（session_time_bias, bb_rsi_reversion）のシグナル頻度を注視する
- direction_filterの12件blockはシステムが正常に機能している証拠でもあるが、過剰フィルタリングの可能性も排除できない

### 2026-06-02 (Pre-Tokyo Briefing)
前日（2026-06-01）は **13トレード、WR 61.5%、PnL +16.5**。session_time_biasのEUR/USDが5トレードで+23.8を叩き出し、全体を牽引。bb_rsi_reversionとwick_imbalance_reversionが足を引っ張る展開。OANDA転送率は全期間通算で8%（50件中4件SENT）と依然低水準。
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
**Cutoff後全体**: N=19 / WR=57.9% / PnL=+26.5
- 前日4トレード中3件がSL_HITまたはBREAKEVEN。方向バイアスはSELL一辺倒。
- EUR/USDはRANGING（ATR%ile 26%、SMA20 slope -0.00142）。低ボラティリティ環境でのBB平均回帰は機能しやすいはずだが、SELLのみの偏りが示唆するのは**シグナル生成ロジックが現在のレンジ上限でなく下限付近でエントリーしている可能性**。
- **対処**: 本日はbb_rsi_reversionのエントリー方向と、RANGINGレジーム内の価格位置（上半・下半）の整合性を目視確認する。N=5では降格判断保留、ただし要警戒。
- N=1、Spread=1.3。EV=-6.80は最悪ケース1件が直撃している状態。
- GBP/USDはRANGING（ATR%ile 43%、SMA20 slope -0.00176 ↓）。下降バイアスある中でBUYエントリーはレジーム逆張り。

### 2026-06-02 (Pre-Tokyo Briefing)
| PnL合計 | **+16.5 pips** |
| 全体WR | **61.5%** (8/13) |
収益の大部分は `session_time_bias / EUR_USD` の2本の大型勝ちトレード（+15.9, +15.3）が牽引。これを除くと残り11件のPnLは **-14.7 pips** となり、実態は `session_time_bias` 依存の構造が鮮明。
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
> **昇格基準**: N≥30 & EV≥+1.0 → 未達戦略なし（全戦略N<10）
### 課題①：`bb_rsi_reversion` のEV劣化
- EUR_USD: 4件中WIN1件、連続SL_HIT 2件（-5.2, -5.0）が重症
- USD_JPY: 前日1件WIN（+2.4）だが、全期間EV=-0.92は深刻

### 2026-06-02 (Pre-Tokyo Briefing)
- PnL: **+16.5** / トレード数: **13件** / WR: **61.5%**
- session_time_biasのEUR/USD SELL集中（5件）が収益の大部分を牽引。+15.9と+15.3の大型勝ちトレードが全体を支えた。
- wick_imbalance_reversion（-6.8）とbb_rsi_reversion（合計-6.0相当）が足を引っ張るも、session_time_biasの超過収益でカバー。
| Strategy | Pair | N | WR% | EV | 判定 |
**N=28合計（Cutoff後）**: WR 42.9%, PnL +16.1
> ⚠️ 全戦略において **N<30**。昇格基準（N≥30 & EV≥1.0）到達まで、最先着のsession_time_biasで **残り21件**。現時点でいかなる戦略も「判断可能」水準に達していない。
| # | Pair | Dir | PnL | Exit |
EUR_USDはATR%ile=26%（RANGINGの低ボラ帯）+ SMA20 Slope=-0.00142（微下向き）。逆張り系のbb_rsi_reversionが2連続SLを食らったのは、このレジームでシグナルが十分なブレイクアウト幅を持てないためと解釈できる。EVは累計-1.52（N=4）。

### 2026-06-02 (Pre-Tokyo Briefing)
**2026-06-01（全セッション）**：PnL **+16.5pip**、トレード数 **13件**、WR **61.5%**
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
- EUR_USDでSL_HIT×2（-5.2, -5.0）→ RANGING相場（ATR%ile=28%）でbounce戦略がノイズに食われている構図
- USD_CHFはCutoff後N=8でWR=25%、EV=-1.38が最悪値。RANGING環境下でのfalse signal頻発と推定
- **今日の対処**：bb_rsi_reversionの新規エントリーは積極視しない。特にEUR_USD・USD_CHFのエントリーはspread_guardが機能しているか確認を優先
- N=1でEV=-6.80は一件あたりの損失としては最大級。SL設定とポジションサイズの妥当性要確認
- RANGING相場（GBP_USD ATR%ile=38%）ではwick playは方向感なく刈られやすい
- **今日の対処**：RANGING継続中は同戦略の新規エントリーに慎重姿勢

### 2026-06-03 (Pre-Tokyo Briefing)
前日（2026-06-02）は **16トレード、WR 31.2%、PnL -12.0** と明確なマイナスセッション。bb_rsi_reversion/USD_CHFの連敗（8件中6敗）がドローダウンの主因。sr_anti_hunt_bounce/EUR_JPYの+25.7が損失を一部相殺したが焼け石に水。全体的に方向性のないRANGINGレジーム下でのトレンドフォロー系戦略の失敗が顕著。
| Strategy | Pair | N | WR% | EV | PnL | 評価 |
**重要注記**: 全戦略N<30。現時点では**全戦略「傾向把握」段階**であり、昇格基準（N≥30 & EV≥1.0）を満たす戦略はゼロ。降格基準（N≥30 & EV<-0.5）も形式上は未到達だが、bb_rsi_reversionの軌道は警戒に値する。
前日8件のうちWIN=2、LOSS=5、BREAKEVEN=1
### 課題②：session_time_bias/EUR_USD のBT乖離（WR_BT=87.5% → WR_Live=55.6%、ΔWR=▲31.9pp）🔴
前日は4件中WIN=1（WR=25%）と更に低下。SIGNAL_REVERSEによるEXITが3件で、シグナルそのものが不安定。BT期間（ウォークフォワード）のレジームと現在のRANGINGレジームが乖離している可能性が高い。
**今日の対処**: N=9という段階では判断できないが、WR乖離は拡大傾向。N=15通過時点で再評価が必要。
1件目BUY → LOSS(-18.4) → 2件目BUY → WIN(+25.7) と同日同方向で結果が真逆。EUR_JPYはRANGINGながらATRパーセンタイル36%と相対的に高め。大振れ戦略のため1勝1敗でもPnLはプラスになる構造。N=2では評価不能。

### 2026-06-03 (Pre-Tokyo Briefing)
| PnL合計 (2026-06-02) | **-12.0 pip** |
| 全体WR | **31.2%** (5勝11敗) |
前日はbb_rsi_reversion/USD_CHFの連続LOSS（TIME_DECAY_EXIT 6件）が主因となりPnL悪化。sr_anti_hunt_bounce/EUR_JPYが+25.7pip（MAX_HOLD_TIME）で一時的に損失を緩和したが、全体として赤字で終了した。
**⚠ 全N=42、全体WR=42.9%、PnL=-33.3pip**
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
| 件数 | 8件中6件がTIME_DECAY_EXIT（LOSS/BREAKEVEN） |
| WR | 25.0%（期待最低水準を大幅下回る） |
| EV | -1.38（摩擦込みで明確なマイナス） |

### 2026-06-03 (Pre-Tokyo Briefing)
定量分析（N/WR/EV更新、OANDA転送率、block_counts）は実施不可能。
> **PnL / トレード数 / WR: データ取得不可（API全エンドポイント失敗）**
ライブN/WR/EVは取得不可のため、**KBに格納されたBTベースライン**を参照。
| 戦略 | ペア | BT EV | BT WR | ライブN | ライブEV | ステータス |
| 戦略 | ペア | BT EV | BT WR | 昇格判断基準 | 備考 |
| dt-bb-rsi-mr | USD/JPY | -0.023 | 54.2% | 降格検討圏 | EV≈0 |
> ⚠️ **N/WR/EV（ライブCutoff後）は本日取得不可。上記はBT参照値であり実績ではない。**
- STATUS / TRADES / OANDA の3エンドポイントが同時に取得不可

### 2026-06-03 (Pre-Tokyo Briefing)
| 総PnL | **−12.0** |
| 全体WR | **31.2%** |
前日は全3セッション通じてネガティブ。`bb_rsi_reversion/USD_CHF` の連続SL（8戦2勝）と `session_time_bias/EUR_USD` の低WRが主因。唯一の救いは `sr_anti_hunt_bounce/EUR_JPY` の +25.7pips（逆に−18.4の損失も同戦略から発生）。
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
**全体合計: N=32, WR=37.5%, PnL=−47.6**
| WR=25%、EV=−1.38はN=8ながら一貫してネガティブ |
### 課題②：`session_time_bias/EUR_USD` — BT乖離 ΔWR=+54.2pp（最大級アラート）
| BT WR | Live WR | ΔWR |

### 2026-06-04 (Pre-Tokyo Briefing)
前日（2026-06-03）は**10トレード、WR 40.0%、PnL -33.8pips**。全トレードが `session_time_bias` に集中（EUR_USD 8件 + GBP_USD 2件）、方向はすべて**SELL**で一方向偏重。勝利3件はいずれも小幅利益（+0.8〜+2.1）、敗北7件はSL到達で平均 -6.6pip と非対称な損益構造を示した。
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
| session_time_bias | EUR_USD | 12 | 33.3% | -3.05 | -36.6 | 🔴 要注意 |
**全体（N=32）: WR 37.5%、PnL -47.6pip、EV マイナス優勢**
> 昇格基準（N≥30 & EV≥1.0）到達戦略：**なし**
> 降格基準（N≥30 & EV<-0.5）該当：`session_time_bias / EUR_USD`（N=12、基準のN=30未達だが傾向として強く警戒ゾーン）
### 課題①：`session_time_bias` の構造的負EV
- **前日EV = -3.39（EUR_USD）、-3.35（GBP_USD）**。勝ち時の平均 +1.56pip に対し、負け時の平均 -6.76pip。RR比は 1:4.3 の逆転状態

### 2026-06-04 (Pre-Tokyo Briefing)
| PnL合計 | **-33.8** |
| 全体WR | **40.0%** |
前日（2026-06-03）は `session_time_bias` が EUR_USD × 8件・GBP_USD × 2件を独占。10件中4件勝利（WR 40%）で大幅なマイナス。**リスクリワード比の非対称性（損失6-9 pip vs 利益1-3 pip）**が直接的な損失原因。
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
> **全体**: N=28、WR=39.3%、PnL=-44.1
- **N=30達成戦略**: なし（最大N=13、不足17件）
- `session_time_bias / EUR_USD`: **N=13 → あと17件**で降格判定閾値到達
| 方向 | 勝利時PnL | 敗北時PnL |

### 2026-06-04 (Post-London Report)
| 勝率 (WR) | 20.0% |
| 合計PnL | **−25.4 pips** |
| 平均EV/トレード | −5.07 pips |
| 戦略 | ペア | PnL | 成功要因 |
> **実質的な「成功」は存在しない。** 唯一の勝ちトレードもEV寄与は+0.7 pipsに過ぎず、方向性バイアス（全SELL）の中で偶然生き残った1件。
| 戦略 | ペア | PnL | 失敗要因 |
| WR | — | 20.0% | 低 |
| PnL | ~+1.0（本日累計6件でN=6, WR=33.3%, −24.4pipsから逆算） | −25.4 | 大幅悪化 |

### 2026-06-04 (Pre-Tokyo Briefing)
前日（2026-06-03）は **10トレード、PnL = -33.8 pips、WR = 40.0%**。
| Strategy | Pair | N | WR% | EV | 判定 |
> **全体**: N=17、WR=35.3%、PnL=-76.6 pips
> 昇格基準（N≥30 & EV≥1.0）到達戦略：**ゼロ**
> 降格検討水準（N≥30 & EV<-0.5）：`session_time_bias/EUR_USD` は EV=-3.57 で既に深刻水準、ただし N=11 で正式降格判定には N≥30 が必要
WIN 平均 PnL: +1.6 pips（+1.8, +1.8, +2.1, +0.8）
LOSS 平均 PnL: -6.7 pips（-8.8, -6.7, -6.5, -6.6, -6.4, -5.3）
WR 40% で損益均衡するためには最低 RR ≥ 1:1.5 が必要。現状 RR=1:4.2 では **WR 80%超** でなければ EV が正にならない計算。BT WR=87.5% との乖離（ΔWR=51.1pp 🔴）が直接的な破綻要因。

### 2026-06-05 (Pre-Tokyo Briefing)
前日（2026-06-04）は **6トレード、WR 33.3%、PnL -24.4pips**。5連続SL_HITで始まり、終盤に vsg_jpy_reversal がWINを拾ったが焼け石に水。全戦略をまとめた累積（Cutoff後）も **N=16、WR 37.5%、PnL -58.2pips** であり、赤字基調は変わらない。
| Strategy | Pair | N | WR% | EV | 判定 |
> **凡例**: EV≥+1.0かつN≥30 → 昇格候補 / EV<-0.5かつN≥30 → 降格検討 / N<10 → 「データなし」扱い
- session_time_bias / EUR_USD: **11/30（あと19件）**
- 残り全戦略ペア: **事実上データなし**
前日トレード詳細を見ると、session_time_bias は EUR_USD・GBP_USD 両ペアで **全エントリーがSELL方向**。レジーム確認（後述）ではEUR_USD の SMA20 Slope が **-0.00190**（わずかに下落バイアス）であり、方向性は間違っていない。しかしEV=-3.57〜-4.93 という深いマイナスは「スプレッド負け・SL幅設定の問題」ではなく、**シグナル品質そのもの**に問題がある可能性が高い。
KBでは dt_bb_rsi_mr の昇格ペアは **USD_JPY** であり、EUR_USD はBT EV=-0.077。前日のエントリーはペア設定の整合性を要確認。（コード変更はしない — 判断として記録）
| 時刻(UTC) | イベント | 影響ペア | 注意点 |

### 2026-06-05 (Pre-Tokyo Briefing)
前日（2026-06-04）はトレード6件、PnL **-24.4**、WR **33.3%**（2勝4敗）。session_time_bias が主損失源（5件中4件がSL_HIT）、唯一のプラスは vsg_jpy_reversal の+1.0のみ。全体として損失超過の1日。
| Strategy | Pair | N | WR% | EV | 判定 |
| **全体計** | | **14** | **35.7%** | — | **PnL: -53.7** |
> **統計的注意**: 全戦略N<30。「判断可能」閾値未達。EVの数値は傾向値として扱う。
前日6件中5件がSELLサイド。EUR_USD・GBP_USDともにSELL方向で連続SL_HIT。BT乖離テーブルの通り、BT WR=87.5% vs Live WR=33.3%（ΔWR **+54.2pp**、🔴アラート）が示す通り、ライブ環境での戦略適合度に深刻な疑問。
session_time_bias EUR_USDのΔWRは54.2pp。これはバックテストで想定された市場環境と現在のレジームが乖離していることを示唆。RANGINGかつATR%ile 28%（低ボラ）の環境でトレンドフォロー的なバイアス戦略が機能しない可能性。
- session_time_bias の N≥30 到達まで、EVの推移を毎日トラッキング継続
- BT乖離がΔWR>50ppを維持するようであれば降格検討を本格化

### 2026-06-05 (Post-London Report)
| 勝率（WR） | **0.0%** |
| セッション内PnL | **-5.2 pips** |
| 戦略 | ペア | 方向 | PnL | 失敗要因 |
| zz_pivot_v60_sr | EUR_USD | SELL | **-5.2 pips** | SIGNAL_REVERSE（シグナル反転による損切り）、スプレッド0.8pipは許容範囲内だが、EUR_USDのRANGING＋ATR低水準（20日%ile=28%）でPivotベースのブレイクシグナルが偽陽性を生成したと推定 |
- **本日累計N=1、PnL=-5.2pips**——東京セッションでも成立トレードがゼロであったことを示唆（累計=セッション内と一致）
- 全通貨ペアが**RANGING（低ATR）**レジームで固定されており、東京・ロンドン両セッションを通じてボラティリティ不足が続いている
- USD_JPYのATR%ile=16%は特に低水準で、ロンドンフィックス前後でも方向性が出なかった
- レジーム面の変化：東京→ロンドンで**改善なし**——全5ペアがRANGINGを継続

### 2026-06-05 (Pre-Tokyo Briefing)
| PnL合計 | **-24.4 pips** |
| 全体WR | **33.3%** (2/6) |
前日は全6件中4件がSL_HIT。唯一の戦略内正収益はvsg_jpy_reversal (+1.0pip)のみ。session_time_biasがPnLの大半を毀損した。
| Strategy | Pair | N | WR% | EV | 判定 |
| session_time_bias | EUR_USD | 3 | 33.3% | -4.07 | ⚠️ N不足・EV負 |
> Cutoff後合計: N=8, WR=25.0%, PnL=-43.7pips
| WR (EUR_USD) | **87.5%** | **33.3%** |
| ΔWR | | **▼54.2pp 🔴** |

### 2026-06-08 (Pre-Tokyo Briefing)
- **2026-06-07（前日）**: **トレードゼロ** — 全セッション（東京・ロンドン・NY）を通じて約定なし
- **Cutoff後累計（全期間）**: N=8、WR=25.0%、PnL=**-43.7 pips**
- 前日の非活動は単発事象ではなく、後述するブロック構造の集積によるもの
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
- `r2_shadow_demoted_cell`ブロックが常態化しているscalpセルの格付けを確認すること
- `same_price_0pip`が69件発生しているdaytrade_eurのデータフィードを確認すること
- BreakoutおよびMomentum系戦略（donchian、doji-breakout等）は**構造的に不利**なレジーム
- Reversal・SR系戦略（dt_sr_channel_reversal、vsg_jpy_reversal）は**相対的に有利**だが、現状ブロックで機能していない

### 2026-06-08 (Pre-Tokyo Briefing)
- 前日（06-07）のトレード実行数：**0件**
- 全セッション（東京・ロンドン・NY）を通じて実質的なエントリーなし
- Cutoff後累計（全期間）：N=9、WR=22.2%、PnL=**-51.2**
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
> **注記**: 全戦略でN<10。「データなし」水準。統計的判断はいずれも不可。EVの絶対値の大きさは小ロットでの損失幅を反映。
- 前日0件。本日も現時点で全モードのTrades=0。
- 稼働モードは25個あるが、実質エントリーを生成できていない。
- Shadow降格セルの累積ブロックが減少に転じるか（降格→昇格待ち）

### 2026-06-08 (Post-London Report)
| 勝率 (WR) | 0.0% |
| PnL | **-38.1 pips** |
| 戦略 | ペア | PnL | 失敗要因 |
| WR | — | 0.0% |
| PnL | 0 | -38.1 pips |
- **EUR_USD / GBP_USD**: ロンドン勢の手仕舞いで一時的スパイク後、再びRANGING収束の可能性が高い
- **USD_JPY**: ATR%ile 19%（最低）、本日の動意は極めて限定的と判断
- EUR_JPY / GBP_JPYはRANGINGだがATR%ile 40-45%とやや高め、NY初動で動く可能性はある

### 2026-06-08 (Pre-Tokyo Briefing)
**2026-06-07（前日）: トレードゼロ。** セッション全体（東京・ロンドン・NY）を通じて約定なし。Cutoff後累計はN=6、PnL=**−57.4**、全体WR=**0.0%**という極めて低調な状態が継続中。
| Strategy | Pair | N | WR% | EV | PnL |
> **統計的注意**: 全戦略 N<10。現時点では「データなし」水準。EVの数値は参照値に過ぎず、優劣判断には用いない。
- 全対象ペアがRANGING × ATR%ile低位（USD_JPY=17%、GBP_USD=31%）→ トレンド系・ブレイクアウト系戦略のシグナル発生頻度が構造的に低い
- EUR_JPY（40%）・GBP_JPY（43%）は相対的に高いが、それでもRANGING分類
- エントリー枯渇は現在のレジームに対する正常反応の可能性あり。無理なポジション追加よりも**N蓄積待ち**を優先する姿勢を維持。
- 低頻度自体を問題視する前に、「不要なトレードをしない」ことの方が重要。ただしN=30到達まで昇格・降格判断は一切保留。
| EUR_JPY | RANGING | 40% | +0.00128（微弱上昇） | `dt_sr_channel_reversal`・`sr_anti_hunt_bounce`：レンジ環境は逆張り系に一見有利だが、ATR低位でpip幅が取れずEV圧迫リスク |

### 2026-06-09 (Pre-Tokyo Briefing)
- **前日（2026-06-08）PnL: -38.1 pips | トレード数: 4件 | WR: 0.0%**
- 全4トレードがSL_HIT。方向は3 SELL / 1 BUY、ペアはEUR_JPY×2・EUR_USD・GBP_USD。
- スプレッドは0.8〜1.8pipsと許容範囲内であり、ブロック問題ではなくシグナル品質の問題。
| Strategy | Pair | N | WR% | EV | PnL |
> **全体**: N=6, WR=0.0%, 累積PnL=-57.4 pips
- **trendline_sweep / zz_pivot_v60_sr**: RANGINGフェーズでのシグナル頻度と損失集中を注視。N≥10到達後にEV傾向を再評価する。
- **dt_sr_channel_reversal（EUR_JPY）**: KBではBT EV=+0.178 / WR=63.8%と記録があるが、実トレード2件いずれも損失。これはN=2のノイズとして許容範囲内だが、次のEUR_JPYトレードは特に記録を要する。
- **sr_anti_hunt_bounce**: N=1のため判断留保。

### 2026-06-09 (Pre-Tokyo Briefing)
| PnL合計（前日） | **−38.1 pips** |
| 全体WR | **0.0%（4戦0勝）** |
全トレードがSL_HITで終了。単日として見れば壊滅的だが、N=4は統計的に「ノイズ」の範囲。Cutoff後累計N=7・WR=0%・PnL=−64.9も同様に判断不能な水準。
| Strategy | Pair | N | WR% | EV | PnL |
### 課題①：全4トレードがSL_HIT（WR=0%）
- EUR_JPY・EUR_USD・GBP_USD全てがRANGINGレジーム（ATR%ile: 17〜43%）
- Trendline_sweep・dt_sr_channel_reversal・sr_anti_hunt_bounceはいずれも**ブレイクアウト系またはモメンタム依存型**
- RANGINGレジームではファルスブレイクが多発し、これらの戦略はレジーム的逆風を受けていた可能性が高い

### 2026-06-09 (Post-London Report)
| PnL | **+10.6 pips** |
| PnL | **+18.1 pips** |
| PnL | **-7.5 pips** |
| WR | — | 50.0% | — |
| PnL | — | +10.6 | — |
| USD_JPY | RANGING | **17%** | 極低ボラ。NY時間の米系指標でスパイク注意 |
### 推奨戦略配分
⚠️ NO ACTION推奨: scalp系全般

### 2026-06-09 (Pre-Tokyo Briefing)
Cutoff後トレードデータが取得できないため、前日PnL・トレード数・WRの実測値を提示できません。APIの連続失敗は、Renderのスリープ復帰遅延またはOANDA接続障害のいずれかが疑われます。
リアルタイムN/WR/EVは取得不可のため、**KBに記録されたBTデータ**をベースラインとして参照します。
| Strategy | Pair | BT EV | BT WR | ライブ判定可否 |
| Strategy | Pair | BT EV | BT WR | 備考 |
| dt-sr-channel-reversal | EUR_JPY | +0.178 | 63.8% | EV低め・N蓄積優先 |
| dt-bb-rsi-mr | EUR_USD | -0.077 | 52.0% | **BT EV負** |
| dt-bb-rsi-mr | GBP_USD | -0.135 | 51.3% | **BT EV負（最悪）** |
| ema200-trend-reversal | USD_JPY | -0.183 | 56.2% | **BT EV負** |

### 2026-06-10 (Pre-Tokyo Briefing)
| 前日PnL合計 | **+10.6 pips** |
| 前日WR | **50.0%** (1勝1敗) |
| Strategy | Pair | N | WR% | EV | PnL | 評価 |
**全体**: N=8 / WR=12.5% / PnL=**-46.8 pips**
- direction_filterのブロック傾向を注視（USD_JPY TRENDING_UP環境での機会損失 vs. リスク管理のトレードオフを把握）
- GBP関連戦略の活動時間帯を意識してモニタリング
| EUR_JPY | **VOLATILE** | 43% | +0.00092 | 唯一のVOLATILE。dt_sr_channel_reversalの主戦場。スプレッド拡大注意 |
- **EUR_JPY**：VOLATILE継続なら dt_sr_channel_reversal にシグナル増加期待。ただしATR43%は中程度で、急落すればRANGING移行も

### 2026-06-10 (Pre-Tokyo Briefing)
| 前日PnL | **+10.6 pips** |
| 全体WR | **50.0%** (1W/1L) |
| Strategy | Pair | N | WR% | EV | PnL | 評価 |
> ※前日分（dt_sr_channel_reversal EUR_JPY +18.1）を全期間に統合すると、dt_sr_channel_reversal EUR_JPY N=4、PnL=+14.5推定。全戦略合計N=8。
- 全モード25個が稼働中にもかかわらず、前日実行トレードは**わずか2件**
- Block Countsを見ると、hedge_block（scalp_5m_gbp:22、daytrade_eurgbp:21、daytrade_eur:14）とdirection_filter（rnb_usdjpy:21）が主要阻害要因
- **hedge_blockの集中**: GBP系・EUR系で相互ヘッジブロックが連鎖しており、同方向シグナル発生時に機会損失が構造的に発生
- scalp_eur:18件、scalp_5m:2件がシャドウデモート済みセルにブロック

### 2026-06-10 (Post-London Report)
| PnL | **N/A**（データ取得不可） |
| WR | **N/A** |
- `trendline-sweep (EUR_USD)` — EV=+0.927、ロンドン高流動性帯でブレイク確度が上がる傾向
- `doji-breakout (GBP_USD)` — EV=+0.724、GBP方向性がロンドン開始後に確定しやすい
- `dt-bb-rsi-mr` 系は全ペアでBT EV<0 — ロンドンの高ATR環境ではMR戦略は逆風
- `ema200-trend-reversal (USD_JPY)` EV=-0.183 — ロンドン後半の方向転換期に誤シグナルリスク大
- ロンドン→NY移行（UTC 16:00-17:00）はしばしば**偽ブレイク・リバーサル**が多発
- 現在UTC 18:24は**NY序盤**に該当。EUR/USD方向性がロンドン引け水準に対してリトレースするか判断が必要

### 2026-06-11 (Pre-Tokyo Briefing)
| PnL合計（前日） | **+3.0 pips** |
| 全体WR | **60.0%** (3W/1L/1BE) |
前日は小幅プラスで着地。dt_sr_channel_reversal が +10.3 pips の大幅勝ちでPnLを牽引。一方 wick_imbalance_reversion が -10.9 pips の大幅ロスを出し、全体利益の大部分を相殺した。
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
> **全体（Cutoff後）**: N=10, WR=40.0%, EV=−1.7, PnL=−17.0
> ⚠️ **統計的注記**: 最大N=3。全戦略が「データ不足（N<10）」ゾーン。EV・WRの解釈は傾向参照にとどめる。
LOSS: -10.9 pips（SIGNAL_REVERSE）
同一セッションで同一方向（GBP_USD BUY ×2）でエントリー。SIGNAL_REVERSE で大幅ロス後、即座に同方向再エントリーして小幅勝ちというパターン。**相関リスクが顕在化**しており、同一ペア・同一方向の連続エントリー管理が重要。

### 2026-06-11 (Pre-Tokyo Briefing)
- **前日（2026-06-10）**: PnL **+3.0** / トレード **5件** / WR **60.0%**
- `dt_sr_channel_reversal / EUR_JPY` の大勝（+10.3）が全体を牽引。`wick_imbalance_reversion` の1件大敗（-10.9）で相殺される構造。
- OANDA転送率 **8%**（4 SENT / 46 SKIP）— 本番資金への貢献は依然限定的。
| Strategy | Pair | N | WR% | EV | 判定 |
> **全体**: N=11 / WR=45.5% / PnL=-10.3
> ⚠️ **全戦略でN<10**（統計的判断不可）。EVの符号は傾向として参照するにとどめる。
| 件 | Dir | Outcome | PnL |
| 1 | BUY | LOSS | **-10.9** (SIGNAL_REVERSE) |

### 2026-06-11 (Post-London Report)
| PnL | **-3.6 pips** |
> ⚠️ **WR66.7%でもPnLがマイナス**: GBPUSD SL_HIT (-7.7) の損失が2勝の合計利益 (+4.1) を上回るペイオフ非対称。
| 戦略 | ペア | PnL | 成功要因 |
| 戦略 | ペア | PnL | 失敗要因 |
| 本日累計WR | 75.0% | セッション単体66.7% |
| 本日累計PnL | -2.2 pips | セッション単体 -3.6 pips |
> 東京セッション推定: 1件 WIN +1.4 pips（累計4件-3件=1件、PnL: -2.2-(-3.6)=+1.4pips）
### 推奨戦略配分

### 2026-06-11 (Pre-Tokyo Briefing)
**2026-06-10（前日）**: PnL **+3.0** / トレード数 **5件** / 全体WR **60.0%**
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
> **注**: 全戦略N<10。「判断可能」な戦略はゼロ。EVの正負はすべて「傾向」レベル。
> 全体合計: N=10 / WR=70.0% / PnL=**+18.9**（dt_sr_channel_reversalの高EVが全体を引き上げ）
BUY/LOSS: -10.9  (SIGNAL_REVERSE — エントリー後に方向反転)
EV前日: -4.80（Cutoff後累計も-3.75）
**観察**: GBP_USDはRANGINGレジーム(ATR%ile 40%)。Spreadは1.3pipsで許容範囲だが、SIGNAL_REVERSEでの-10.9は「エントリー後に逆走→TP未到達でSL拡大」を示唆。WR50%かつEV<0という組み合わせはレンジ環境でのシグナル品質劣化を示す。
**本日対処**: GBP_USDのwick_imbalance_reversionシグナルは「N=4・EV=-3.75」で降格基準（N≥30 & EV<-0.5）には未到達だが、**現在のレンジ環境では信頼度が特に低い**。この戦略からのシグナルは要注視。

### 2026-06-12 (Pre-Tokyo Briefing)
| PnL合計 | **-2.2 pips** |
| 全体WR | **75.0%** (3勝1敗) |
WR75%にもかかわらずPnL赤字。`wick_imbalance_reversion` の1敗（-7.7pips）が3勝分の利益（+5.5pips）を上回るペイオフ非対称が原因。件数は依然として低水準（N=4/日）。
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
| `wick_imbalance_reversion` | GBP_USD | 4 | 50.0% | **-3.75** | -15.0 | 🔴 EV負・要監視 |
- 全戦略 N<10 → 現時点では「データなし」扱いが厳密
- `dt_sr_channel_reversal` のEV+14.20はN=2のため信頼区間が極めて広大（外れ値リスク大）
- `wick_imbalance_reversion` はN=4でEV-3.75。全期間で最も懸念材料

### 2026-06-12 (Pre-Tokyo Briefing)
前日（2026-06-11）は **4トレード、WR=75.0%、PnL=−2.2pips** で終了。勝率は良好だが、`wick_imbalance_reversion / GBP_USD` の1件（−7.7pips）が全体を赤字に引き込んだ。勝ち3件の合計（+5.5pips）をSL-HIT1件が単独で上回る非対称な損益構造が露呈。
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
| vix_carry_unwind | USD_JPY | 6 | 66.7% | −0.35 | −2.1 | ⚠️ EV負・継続監視 |
| wick_imbalance_reversion | GBP_USD | 5 | 60.0% | −2.54 | −12.7 | 🔴 **EV大幅マイナス** |
| dt_sr_channel_reversal | EUR_JPY | 1 | 100.0% | +10.30 | +10.3 | データ不足（外れ値注意） |
| ema200_trend_reversal | USD_JPY | 2 | 0.0% | −5.60 | −11.2 | 🔴 **EV極端マイナス（N=2）** |
> **全体（N=21）**: WR=66.7%、PnL=−5.3pips
### 🔴 課題①：`wick_imbalance_reversion / GBP_USD` のEV=−2.54

### 2026-06-12 (Post-London Report)
| **PnL** | **-9.6 pips** |
**概評**: 勝率75%にもかかわらずPnLがマイナスという典型的な「非対称損失」セッション。少数の大損失（-15.4, -7.4, -5.6）が多数の小勝利を食い潰している。
| 戦略 | ペア | PnL | 成功要因 |
| **wick_imbalance_reversion** | GBP_USD | +2.3 pips (1件) | RANGING環境下での価格行動パターンが機能、スプレッド1.3pipsを吸収しEV+2.30。|
| 戦略 | ペア | PnL | 失敗要因 |
| **trendline_sweep / GBP_USD** | GBP_USD | **-11.7 pips（4件合計）** | 1件の-15.4pips SL_HITが致命的。GBP_USDがRANGING（ATR40%ile）にもかかわらずトレンドライン突破を狙う戦略を展開→レジームミスマッチ。EV=-2.35。|
| **ema200_trend_reversal / USD_JPY** | USD_JPY | **-5.6 pips（1件）** | USD_JPY ATR29%ile（低ボラ）でのSELL→SL_HIT。EV=-5.60は単発でも構造的に危険な水準。BTデータでUSD_JPY EV=-0.183と既に負のシグナルあり。|
> ※本日累計17件・PnL -15.2pipsに対してロンドン16件・-9.6pipsであることから、**東京セッションは約1件・-5.6pips**と推定される。

### 2026-06-12 (Pre-Tokyo Briefing)
前日（2026-06-11）: **N=4、WR=75.0%、PnL=−2.2**
Cutoff後累計: **N=26、WR=69.2%、PnL=−14.4**（全体EV赤字継続）。
| Strategy | Pair | N | WR% | EV | 判定 |
| ema200_trend_reversal | USD_JPY | 2 | 0.0% | **−5.60** | ⚠️ データ不足・EV極端な負 |
| trendline_sweep | GBP_USD | 7 | 71.4% | **−0.81** | ⚠️ WRは高いが損大/勝小 |
| vix_carry_unwind | USD_JPY | 7 | 71.4% | **−0.19** | ⚠️ ほぼゼロEV、摩擦で実質赤字 |
- **損失が7.7pip規模**に拡大しているのに対し、勝ち時は2.3pipと小さい。
- SL配置がwidすぎるか、エントリー精度が低くRRが機能していない。

### 2026-06-15 (Pre-Tokyo Briefing)
全セッション（東京・ロンドン・NY）を通じてエグゼキューションなし。PnL=0、N=0、WR=N/A。
前日サマリーとしての数値評価対象なし。Cutoff後累積（N=23、WR=69.6%、PnL=**-27.0**）が現在の参照基準。
| Strategy | Pair | N | WR% | EV | 判定 |
| vix_carry_unwind | USD_JPY | 7 | 71.4% | **-0.19** | 傾向（EV負・要監視） |
| trendline_sweep | GBP_USD | 5 | 80.0% | **-1.60** | データ不足・EV深刻 |
| wick_imbalance_reversion | GBP_USD | 5 | 60.0% | **-2.54** | データ不足・EV最悪 |
| ema200_trend_reversal | USD_JPY | 2 | 0.0% | **-5.60** | データなし・EV崩壊 |
**全体: N=23（判断基準N≥30未達）、WR=69.6%は表面上良好だが、EV計算ではPnL=-27.0と損失。WR≠EVの乖離が最大の構造問題。**

### 2026-06-15 (Pre-Tokyo Briefing)
**2026-06-14（前日）はトレードゼロ。** システムは全モード稼働中だが、シグナル発火なし。Cutoff後の累計実績はN=24、WR=70.8%、PnL=**-25.8**（EV=**-1.075**）と、高WRにもかかわらず負のEVが継続している。
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
| trendline_sweep | GBP_USD | 6 | 83.3% | **-1.13** | -6.8 | 🔴 高WR・負EV（N<10） |
**全体**: N=24 / WR=70.8% / EV=-1.075 / PnL=-25.8
### 課題①：高WRでも負EVが続く「スプレッド/スリッページ負け」構造
`trendline_sweep GBP_USD`はWR=83.3%で6勝1敗なのにEV=-1.13。**勝ちトレードの利益が小さく、負けトレードが大きい非対称損益**が示唆される。`wick_imbalance_reversion GBP_USD`（WR=60%でEV=-2.54）も同様で、スプレッド拡大局面でのエントリーが疑われる。
### 課題②：`ema200_trend_reversal USD_JPY`のEV=-5.60
N=2で0勝2敗。1トレード平均-5.6pips相当の損失は数値として深刻。ただしN=2のため確率的ノイズの可能性が高い。**BT上はEV=-0.183（USD_JPY）であり、ライブ実績との乖離が既に顕在化している。**

### 2026-06-15 (Pre-Tokyo Briefing)
> **全エンドポイントが応答不可。以下の分析はKB蓄積知見のみに基づく。定量値（N/WR/EV）は本日分として算出不可。**
**データ取得不可のため、前日PnL・トレード数・WRの定量報告は不可能。**
- DD=80.03%（2026-06-10時点）でDefensive Mode（ポジションサイズ 0.2x）が発動中
- システムは稼働しているが、本日時点でAPIが全断しており、リアルタイム状態が確認できない
| 戦略 | ペア | BT_EV | BT_WR | LIVE_N | ステータス |
> N値はAPI不通のため取得不可。EV<0の戦略（dt-bb-rsi-mr全ペア、ema200 USD_JPY）はBT段階で既に閾値割れ。
- APIが回復した場合、**Fidelity Cutoff以降の累積N値を最優先で確認**
- DD=80.03%の水準が改善していない場合、0.2xポジションサイズを維持継続

### 2026-06-15 (Pre-Tokyo Briefing)
**2026-06-14（日曜日）はトレードゼロ。** 全モードON状態にもかかわらずエントリーなし。週明け月曜Tokyo開場前の静寂として正常範囲内。Cutoff後累積はN=25、WR=72.0%、PnL=**-20.7pip**。高勝率にもかかわらずPnLがマイナスという「勝率/EV乖離」が引き続き最重要課題。
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
| vix_carry_unwind | USD_JPY | 7 | 71.4% | **-0.19** | -1.3 | N不足・EV警戒 |
| trendline_sweep | GBP_USD | 6 | 83.3% | **-1.13** | -6.8 | 🔴 高WR/負EV乖離 |
| wick_imbalance_reversion | GBP_USD | 3 | 66.7% | **-1.03** | -3.1 | N不足・EV警戒 |
| ema200_trend_reversal | USD_JPY | 2 | 0.0% | **-5.60** | -11.2 | 🔴 最悪EV |
**全体: N=25 / WR=72.0% / PnL=-20.7**
### 課題①：ema200_trend_reversal（USD_JPY）— EV=-5.60が全体PnLを破壊

### 2026-06-16 (Pre-Tokyo Briefing)
前日（2026-06-15）は **4件のトレード、WR=75.0%、PnL=-3.3pip** で着地。勝率は良好だが、`doji_breakout / GBP_USD` の単発LOSS（-8.1pip）がPnLを大きく削り、3勝1敗でもネット赤字という典型的な「非対称損益」を記録。Cutoff後累計は **N=23、WR=73.9%、PnL=-15.3pip** と、高勝率に反してEVがマイナス圏のセルが支配的な構造的問題が継続している。
| Strategy | Pair | N | WR% | EV | 判定 |
| vix_carry_unwind | USD_JPY | 7 | 71.4% | -0.19 | ⚠️ N蓄積中・EV微負 |
| trendline_sweep | GBP_USD | 6 | 83.3% | -1.13 | 🚨 高WRなのにEV負（損益非対称）|
| ema200_trend_reversal | USD_JPY | 2 | 0.0% | -5.60 | ⛔ N=2で壊滅的EV |
- `vix_carry_unwind / USD_JPY`: 残り23件
- `trendline_sweep / GBP_USD`: 残り24件
- `zz_pivot_v60_sr / EUR_USD`: 残り27件

### 2026-06-16 (Pre-Tokyo Briefing)
前日（2026-06-15）は **4トレード、WR=75.0%、PnL=▲3.3**。
全期間累計（N=26、WR=73.1%）でもPnL=▲15.4と赤字継続中。勝率は高いが**損益非対称（負けが大きすぎる）**構造が鮮明。
| Strategy | Pair | N | WR% | EV | 判定 |
| vix_carry_unwind | USD_JPY | 7 | 71.4% | **▲0.19** | 🟡 EV微負（N蓄積中） |
| trendline_sweep | GBP_USD | 7 | 85.7% | **▲0.77** | 🔴 高WRだが損益逆転 |
**N≥30達成戦略：ゼロ。**全戦略がまだSentinel蓄積フェーズ。最高でN=7（`trendline_sweep` / `vix_carry_unwind`）。昇格基準（N≥30 & EV≥1.0）到達まで、最速の戦略でも残り**23件**。
### 課題①：`doji_breakout/GBP_USD` の異常損失（▲8.1、EV=▲8.10）
- SL_HIT により単発▲8.1。BT上のEV=+0.724（WR=78.3%）と実績の乖離が顕著。

### 2026-06-16 (Pre-Tokyo Briefing)
| 前日 PnL | **-3.3 pip** |
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
| trendline_sweep | GBP_USD | 6 | 83.3% | -1.13 | -6.8 | 🟠 高WR・負EV（要精査） |
> **重要注記**: 全戦略でN<30。統計的判断可能な戦略は現時点で0。EVの符号は「傾向の方向」として参照するに留める。
差:                    -3.3 pip（最終PnL）
`doji_breakout`のSL幅が他戦略比で著しく大きい。BT上のEV=+0.724（GBP_USD）に対し、ライブ初弾が-8.1 pipというのは**SL設計またはエントリータイミングの問題**を示唆。
### 課題②：trendline_sweep の高WR・負EV構造
| WR | 83.3%（6件中5勝） |

### 2026-06-16 (Pre-Tokyo Briefing)
## ⚠️ データ可用性警告
以下のブリーフィングは「KBベースの構造分析」として位置づけます。定量的なN/WR/EVテーブルはリアルタイムデータ欠損のため生成不可。
| PnL合計 | **取得不可** |
| 全体WR | **取得不可** |
## 2. 戦略別パフォーマンス（KBベース — リアルタイムN/WR/EV欠損）
| 戦略 | ペア | BT EV | BT WR | ライブN | ライブEV | 状態 |
| 戦略 | ペア | BT EV | BT WR | ライブN | 昇格基準達成 |
> **注意**: 上記はBTデータ。Fidelity Cutoff後のライブNが揃わない限り、昇格/降格判断は保留が原則。

### 2026-06-17 (Pre-Tokyo Briefing)
前日（2026-06-16）は **5トレード、WR 40.0%、PnL -26.0 pip** と明確な損失セッション。全5件中GBP_USD集中が4件で、sr_fib_confluenceとwick_imbalance_reversionの2戦略が損失の大半を牽引。日次損失が-26.0pipに達し、**daily_loss_limit（-20pip閾値）をオーバー**してOANDA Bridgeがブロック発動した。
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
| vix_carry_unwind | USD_JPY | 7 | 71.4% | **-0.19** | -1.3 | N不足・EV負 |
| trendline_sweep | GBP_USD | 6 | 83.3% | **-1.13** | -6.8 | ⚠️ WR高・EV負の逆説 |
**全期間合計**: N=26, WR=65.4%, PnL=**-44.5 pip**
> ⚠️ **全戦略がN<30**。現時点では「判断可能」な戦略はゼロ。ただしEVの方向性は参照可能。
→ **今日の対処**: 本日はリセット後の1日目。序盤の損失管理が最重要。累積が-15pipに近づいた時点で手動での状況確認を推奨。
### 課題③：trendline_sweep の WR-EV 逆説

### 2026-06-17 (Pre-Tokyo Briefing)
- **2026-06-16 PnL: -26.0 pips / 5トレード / WR 40.0%**
- GBP_USD集中（4/5件）で大型損失が連続。sr_fib_confluenceが-13.1、wick_imbalance_reversionが-10.5と、2戦略だけで-23.6を叩き出した。
- 唯一のプラスはtrendline_sweep GBP_USD +1.4のみ。損小利大の逆パターン（損失平均 -8.1、利益平均 +1.85）が前日の構造問題。
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
| trendline_sweep | GBP_USD | 6 | 83.3% | **-1.13** | -6.8 | 🟡 **WR高いがEV負** |
| vix_carry_unwind | USD_JPY | 9 | 55.6% | **-0.72** | -6.5 | 🟡 EV要注意 |
| wick_imbalance_reversion | GBP_USD | 2 | 50.0% | -4.10 | -8.2 | 🔴 N不足+EV深刻 |
| sr_fib_confluence | GBP_USD | 2 | 50.0% | -6.55 | -13.1 | 🔴 N不足+EV深刻 |

### 2026-06-17 (Post-London Report)
| **WR（勝率）** | 0.0%（0勝4敗） |
| **PnL（pips）** | **-25.0** |
| **平均PnL/トレード** | -6.25 pips |
`vix_carry_unwind / USD_JPY / +0.5pip` のBREAKEVENが唯一のプラス着地だが、「成功」とは分類しない。1件のBreakevenはスプレッド（0.8pip）を考慮すると実質コスト負担。
| 戦略 | ペア | 方向 | PnL | 失敗要因 |
- `vix_carry_unwind / USD_JPY` は本日N=3でWR=0%、BT WR=100%（N_BT=0、ゼロサンプルのBT）との乖離アラート🔴が出ている。BTのN=0はバックテストとして実質「無効」であり、このアラート自体が「根拠なき昇格」を示唆。
- 全4件すべてSELL方向。USD_JPYのSMAスロープ+0.00269・GBP_USDの横ばいという環境で売り戦略に集中したことが損失を構造化。
データ上、東京セッション（UTC 00:00–07:00）の独立カウントは提供されていないため直接比較は不可。ただし**本日累計N=4（WR=0%、-25.0pip）**がそのままロンドン分に相当していることから、**東京セッションはトレードゼロ**だった可能性が高い。

### 2026-06-17 (Pre-Tokyo Briefing)
- PnL合計: **-26.0 pips**（5トレード）
- 全体WR: **40.0%**（2勝3敗）
- 勝利トレードは小幅（+1.4, +2.3）、敗北トレードが大幅（-10.5, -15.4, -3.8）と **ペイオフ比が著しく非対称（損大・益小）**。勝っても取り返せない構造が前日も継続。
| Strategy | Pair | N | WR% | EV | 判定 |
| trendline_sweep | GBP_USD | 5 | 80.0% | -1.82 | ⚠️ 高WRだがEV負 |
> **全体N=16、全体WR=43.8%、PnL=-66.0 pips**
> ただしEVの方向性（特に`sr_fib_confluence`, `vix_carry_unwind`のEV<-5.0）は統計的閾値以前に構造問題を示唆。
| 前日平均勝ちPnL | +1.85 pips |

### 2026-06-18 (Pre-Tokyo Briefing)
| PnL合計 | **-25.0 pips** |
| 全体WR | **0.0%** (4戦0勝) |
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
| trendline_sweep | GBP_USD | 4 | 75.0% | **-2.85** | -11.4 | ⚠️ EV要注意 |
| sr_fib_confluence | GBP_USD | 3 | 33.3% | -6.80 | -20.4 | 🔴 EV深刻 |
| vix_carry_unwind | USD_JPY | 3 | 0.0% | -5.90 | -17.7 | 🔴 EV深刻 |
> **注記**: 全戦略 N<10。統計的判断には不十分だが、EV方向性として `sr_fib_confluence`・`vix_carry_unwind`・`wick_imbalance_reversion` の3戦略で深刻なマイナスEVが観測されている。
- **問題の構造**: BT vs Live 乖離が最大。BT WR=100%（N=0）に対し Live WR=0.0%（N=3）、ΔWR=**+100pp** の完全乖離 🔴

### 2026-06-18 (Pre-Tokyo Briefing)
| 前日PnL合計 | **-25.0** |
| 前日WR | **0.0%** (0勝4負) |
昨日（2026-06-17）は4トレード全敗。`vix_carry_unwind`がUSD/JPYで3連続SELL失敗（-17.7）、`sr_fib_confluence`がGBP/USDで損切り（-7.3）。BREAKEVENが1件（+0.5）あるが実質的損益は圧倒的マイナス。
**全体: N=14, WR=35.7%, PnL=-64.6**
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
> **N≥30達成: 0戦略。** 全戦略が統計的判断不能域（N<10）または傾向域（N<30）にある。EVがマイナスの戦略でも降格基準（N≥30 & EV<-0.5）に達していない点に注意。
| WR | 100.0%（想定） | 0.0% |
| ΔWR | **+100pp** 🔴 |

### 2026-06-18 (Post-London Report)
| 勝率 (WR) | 0.0% |
| PnL | **-14.1 pips** |
| 戦略 | ペア | 方向 | PnL | 失敗要因 |
| WR | 0.0%（累計WR 0.0%から逆算） | 0.0% | 変化なし |
| PnL | 約 -10.3 pips | -14.1 pips | ロンドンでさらに悪化 |
- 全ペアATR%ile 40–64%のRANGING継続が基本シナリオ。NY市場開幕（UTC 13:00以降）のモメンタムインジェクションは既にロンドンフィックス（UTC 16:00）で一段落している
- USD_JPYのATR%ile=40%はやや低め → Scalp系には不利、DT系のブレイクアウト待ち
- EUR_JPYのSMA20 slope=+0.00095という微小上向きは、NY引き継ぎで円安バイアスがわずかに継続する可能性あり → SELL系リバーサル（vsg_jpy_reversalのSELL方向）は引き続き地合い逆行リスク

### 2026-06-18 (Pre-Tokyo Briefing)
| PnL合計 | **-25.0 pip** |
| 全体WR | **0.0%** (0勝4敗、BEは除外換算) |
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
| vix_carry_unwind | USD_JPY | 3 | 0.0% | -5.90 | -17.7 | 🔴 要注意 |
| vsg_jpy_reversal | EUR_JPY | 2 | 0.0% | -12.20 | -24.4 | 🔴 最悪EV |
| trendline_sweep | GBP_USD | 1 | 100.0% | +1.40 | +1.4 | ✅ 唯一正EV |
**全体: N=11, WR=18.2%, PnL=-75.4 pip**
> **注記:** 全戦略N<10。統計的に「データなし」フェーズ。trendline_sweepの+1.40EVは1件のみで判断不可。

### 2026-06-19 (Post-Tokyo Report)
| PnL | 0 |
| WR | N/A |
- 東京セッションN=0は「失敗」ではなく「フィルタ正常稼働」として解釈が妥当
- block_countsを見ると最大要因は `rnb_usdjpy:direction_filter(137)` および各ペアの `hedge_block`（合計330件超）であり、これはリスク管理機能の正常動作
- `r2_shadow_demoted_cell` によるscalpブロック（計116件）も適正。シャドウトラッキング段階の戦略がライブエントリーを控えているのは仕様通り
- **DDが80.03%のDD防御0.2x発動中** — この状況でのパラメータ緩和は禁忌
| EUR_JPY | RANGING | 64% | ボラティリティ拡大余地あり、ブレイク試行に注意 |
### 推奨戦略配分

### 2026-06-19 (Pre-Tokyo Briefing)
- **前日（2026-06-18）PnL: -24.4 pip、トレード数: 2件、WR: 0.0%**
- 全発動トレードは `vsg_jpy_reversal / EUR_JPY` の連続SELL → 2本ともSL_HIT
- Cutoff後累計: N=13、WR=15.4%、PnL=-95.4 pip。本番環境は依然として構造的赤字継続中
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
> **統計的判断**: 全戦略 N<10。「データなし」扱い。傾向値としてEVが全戦略で大幅マイナス推移中。N=30到達前に構造的判断を下すことは統計的に不適切だが、EV水準（-5〜-12）は許容できる「外れ値」の範囲を大きく超えている点を記録する。
- EUR_JPY SELL × 2本、両者ともSL_HIT
- EV=-12.20は**異常値水準**（正常なSL構造なら-2〜-3が上限）
- スプレッド1.6は基準内（DT閾値20%以内と思われる）だが、**方向判定そのものが誤っている可能性**が高い

### 2026-06-19 (Post-London Report)
| PnL (pips) | **0.0** |
| WR | **N/A** |
**なし** — ただし「何も起きなかった」は無害ではない。本日累計 N=2、WR=0%、PnL=**-20.0 pips** という状態でロンドンセッション全体が無活動で終了した。損失はロンドン以前（東京セッション相当）に既に確定済み。
| WR | 0% (0/2) | N/A |
| PnL | -20.0 pips | 0.0 pips |
- 現在全ペアRANGING（EUR/JPY 64%、GBP/JPY 67%、GBP/USD 53%）
- NYオープン（UTC 13:00過ぎ）の時間帯は既に経過しているが、**daily_loss_limitリセット後（翌UTC 00:00）まで本日のOANDA本番発注は制限継続**と推察される
- レジーム変化の触媒（米経済指標発表等）がない限り、RANGING継続の可能性が高い

### 2026-06-19 (Pre-Tokyo Briefing)
前日（2026-06-18）は **vsg_jpy_reversal / EUR_JPY** の2トレードのみが実行された。PnL合計 **-24.4pip**、WR **0%**（2/2敗北）。両トレードとも SL_HIT による損切りで、当日のシステムは日次損失リミット（-20.0pip）到達後にブロックされた。全体的にトレード機会は極めて少なく、システムは実質的に休止状態に近かった。
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
> ⚠️ **全戦略 N<10**。統計的判断材料としては「データなし」扱い。EV・WRの数値は参考値に留める。
- **SELL方向2連敗**（EUR/JPY）。EUR/JPY のレジームは **VOLATILE（ATR%ile 64%）** であり、リバーサル系戦略にとって逆風の環境。
- EV = **-12.20**（N=2）は統計的意味を持たないが、VOLATILEレジームでのリバーサル戦略の相性の悪さとは一致している。
- `daily_loss_limit(-20.0pip<=-20.0pip)` が1件発動。前日後半のトレード機会はゼロとなった。
- これはリスク管理として正常動作だが、1日2件のトレードで上限到達という事実は、1件あたりのロスサイズが大きいことを示す。
- VOLATILEレジームでのリバーサル系戦略（vsg_jpy_reversal 等）のシグナルは警戒を要する。

### 2026-06-22 (Pre-Tokyo Briefing)
前日（2026-06-21）はトレード**ゼロ**。PnL = ¥0、WR = N/A。
Cutoff後累積でN=9、PnL=-79.9pip相当と、実質的に稼働不能に近い低稼働状態が継続している。
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
> **補足**: 全戦略でWR=0%、EV<-5.9。ただしN<10のため統計的判断は不可。「傾向として極めて悪い」止まり。
- **原因**: hedge_block（eurjpy:128、gbpusd:114、daytrade:49、scalp_5m_eur:44）が支配的
- hedge_blockの累積数がトップ3を占めており、ヘッジ検知ロジックが事実上の「発火ストッパー」として機能している
- rnb_usdjpy:direction_filterが126件と第2位——rnb戦略はほぼ方向性フィルターで全滅
- 累積50件中、SENT=3、SKIP=47

### 2026-06-22 (Pre-Tokyo Briefing)
**2026-06-21（前日）はトレードゼロ**。シグナル自体は複数のブロック理由が記録されているため、エンジンは稼働していたが、約定に至るシグナルが一切生成されなかった。累計（Cutoff後全期間）のPnLは **-68.1 pips / N=9 / WR=11.1%** と依然として深刻な赤字水準。
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
| vsg_jpy_reversal | EUR_JPY | 2 | 0.0% | -12.20 | -24.4 | データ不足（傾向：最悪EV） |
> **注記**: 全戦略がN<10（うち4戦略N≤2）。統計的有意性なし。ただし **EV水準は構造的懸念を示唆**。vsg_jpy_reversalのEV=-12.20は単純な損失深さを示しており、SL設定の妥当性を要確認。
| Strategy | WR_BT | WR_Live | ΔWR | 評価 |
> N_BT=0のウォークフォワードファイル（walkforward-w90-2026-04-22.md）がWR=100%と記録されている点が矛盾。**BT自体のデータ品質に疑義あり**。Live N=3でWR=0%は統計的判断に足りないが、方向性の乖離として要監視。
- 前日は全モードでトレード数=0。hedge_block・direction_filterが上位を占めるブロック理由から、**相場環境がシグナル発火条件を満たさなかった**と推定。
- 対処（本日）：レジーム確認（下記§5）を踏まえ、VOLATILEペアでの発火可能性を注視。

### 2026-06-22 (Pre-Tokyo Briefing)
前日（2026-06-21）トレードゼロ。当日（06-22 19:18 UTC時点）も実質的な新規約定なし。Cutoff後の有効トレードはN=7、合計PnL=**-62.9pip**、全体WR=**14.3%**。システムは稼働中だが、約定に繋がるシグナルをほぼ全量ブロックしている状態が継続している。
| Strategy | Pair | N | WR% | EV | PnL |
> **統計的判断**: 全戦略 N<10。現時点では「データなし」扱い。EV・WRは傾向参考値にすぎず、昇格・降格判断の根拠にはならない。
- **hedge_block祭り**は複数モードが同一通貨エクスポージャーを監視し合っている可能性が高い。EUR/GBP/JPY方向の合意が取れるまでは構造的ブロックが継続する見込み。本日も約定は期待薄と認識してモニタリングに徹する。
- **scalp系demoted_cell**はセルのWR/EV改善を待つしかない。人為的介入は不可。
- rnb_usdjpyはUSD/JPYがRANGINGを脱するレジーム遷移待ち。
| 時間帯 | 注意点 |
| **東京セッション（09:00-12:00 JST）** | JPY系ペアのRANGING継続の可能性高い。USD/JPYが161.3付近の高値圏。BOJ関連ニュースフローに注意 |

### 2026-06-22 (Pre-Tokyo Briefing)
2026-06-21（前日）：**トレードゼロ**。エントリー条件を満たしたシグナルなし、またはすべてシャドウ追跡段階で吸収。PnL = ¥0、WR = N/A。週次累計も含め、実運用に寄与するトレードは発生していない。
| Strategy | Pair | N | WR% | EV | PnL |
**統計的判定**：全戦略でN<10。「データなし」ステータス。EVの数値（特に`vsg_jpy_reversal`の−12.20、`wick_imbalance_reversion`の−10.00）は警戒値だが、N=2では統計的結論不可。`dt_bb_rsi_mr`のEV+1.30はN=1のノイズ。
- Cutoff後の累計N=6（全戦略合計）。本番稼働中モードが22本あるにもかかわらず、エントリー数が著しく少ない。
- **シグナル発火率の低下**：spread_guard・regime filter・shadow追跡の複合フィルタが過剰に機能している可能性が高い。
- 対処の方向性（判断）：どの段階でシグナルが消滅しているか（生成→spread_guard→regime filter→shadow→OANDA）のロス率確認が必要。**今日のログ監視でblock_countの内訳に注目**。
- 50件中50件がSKIP（Live Rate = 0%）。全件がデモ専用として処理されている。
- Bridge StatusのSKIP理由はすべて`shadow_tracking`（20件）。

### 2026-06-23 (Pre-Tokyo Briefing)
| PnL合計 | **+1.3 pips** |
| 全体WR | **100%（1/1）** |
| Strategy | Pair | N | WR% | EV | PnL | 判定ステータス |
**全体合計: N=5, WR=20.0%, EV=−8.62平均, PnL=−43.1**
> **重要**: N<10のため全戦略が「データなし」扱い。EVの正負は傾向に過ぎず、統計的判断は保留。ただし`wick_imbalance_reversion`と`vsg_jpy_reversal`のEV=−10〜−12台は、たとえN=2でも損失規模として看過できない。
- `hedge_block`が**242件**で最大要因。ヘッジポジションが長時間解消されず、新規エントリーをほぼ全面封鎖している状態。これは相場のレンジ化・方向感のなさとも整合。
- `r2_shadow_demoted_cell`の**132件**は、ShadowセルがR2評価で降格済みのシグナルを大量に弾いていることを意味する。Signal品質のフィルタリングが機能しているが、同時にトレード機会を大幅に削減している。
- `direction_filter(rnb_usdjpy: 95件)`はレンジ相場でのRNBエントリー抑制が機能している正常な挙動。

### 2026-06-23 (Pre-Tokyo Briefing)
前日（2026-06-22）は **1トレード、WR 100%、PnL +1.3pips** と極めて低活動。
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
**総計: N=6、WR=33.3%、PnL=-40.8**
| GBP_JPY | **VOLATILE** | 69% | +0.028(↑) | ウィック系戦略には有利環境だが、wick_imbalance_reversalのEVは現状マイナス |
| 時間帯 | イベント | 注意点 |
- EUR_USD、GBP_USDのSMA20がともに**下向き**（USD高トレンド継続の示唆）。VOLATILEからTRENDINGへの遷移が起きると、MR系戦略（dt_bb_rsi_mr等）のパフォーマンスが更に低下する懸念あり。
- USD_JPYのRANGINGは比較的安定。SMA20が若干上向きのため、上方ブレイクアウト発生時にRANGING→VOLATILEへの転換に注意。

### 2026-06-23 (Post-London Report)
| PnL (pips) | **0.0** |
| WR | **N/A** |
| WR | 100% (N=1) | N/A |
| PnL | +2.3 pips | 0 pips |
| EUR/JPY | VOLATILE | 69% | 継続 VOLATILE、リスクオフ波及に注意 |
### 推奨戦略配合
- `daytrade_eur:hedge_block` **224件**
- `daytrade_gbpusd:hedge_block` **184件**

### 2026-06-23 (Pre-Tokyo Briefing)
| PnL合計 | **+1.3 pips** |
| 全体WR | **100%** (N=1) |
- 前日は `dt_bb_rsi_mr / GBP_USD / SELL` の1件のみが約定・勝利（OANDA_SL_TP決済）。
- 実質「トレードなし」に等しい稼働水準。N=1のWR=100%はノイズとして扱う。
| Strategy | Pair | N | WR% | EV | PnL | 評価 |
**全戦略合算（Cutoff後）:** N=5、WR=40.0%、PnL=**-30.5**
> ⚠️ **全戦略でN<10**。統計的判断は不可能。EVの正負はノイズの範囲内だが、`wick_imbalance_reversion`のEV=-5.90と`vsg_jpy_reversal`のEV=-14.10は**1件あたりの損失規模**として要注視。
- Cutoff後N=5（期間不明だが複数週にわたると推察）で合計5件は、事実上のシステム停止水準。

### 2026-06-24 (Pre-Tokyo Briefing)
前日（2026-06-23）は**1トレードのみ**が成立。`wick_imbalance_reversion / GBP_USD` のBUYが +2.3 pips（OANDA_SL_TP決済）で勝利。WR=100%、PnL=+2.3 pip。システムは稼働中だが**事実上の不稼働日**に近い超低頻度。
| Strategy | Pair | N | WR% | EV | PnL | 評価 |
| wick_imbalance_reversion | GBP_USD | 3 | 33.3% | -5.90 | -17.7 | ⚠️ EV深刻 |
**全体合計（Cutoff後）: N=5, WR=40.0%, EV=-6.7（平均）, PnL=-30.5**
> ⚠️ **統計的注記**: N=5は「データなし」水準。昇格・降格判断の対象外。ただし `wick_imbalance_reversion` のEV=-5.90は数値として懸念要因として記録。
- `r2_shadow_demoted_cell` のブロックが**169件**（全体の最大勢力）。これはShadow期間中に降格されたセルが本番稼働を全面封鎖している構造的問題。Shadow解除 or セル再評価の判断が必要かを注視。
- `direction_filter` 99件は相場がレンジ/方向不明瞭な状況を正しく認識している可能性もあり、USD_JPY = **RANGING** レジームと整合的。現時点では正常機能と判断。
- `gbp_asia_flash_crash` 29件は東京時間のGBP系に対する保護。本日東京時間も継続する可能性が高い。

### 2026-06-24 (Pre-Tokyo Briefing)
| PnL合計（前日） | **+2.3 pips** |
| 全体WR | **100.0%**（N=1、統計的意味なし） |
| Strategy | Pair | N | WR% | EV | PnL | 統計ステータス |
**Cutoff後 合計**: N=5、WR=60.0%、PnL=**-14.0 pips**
注目点: `wick_imbalance_reversion / GBP_USD` はEV=-5.90と極めて低調だが、N=3のため降格判断の閾値（N≥30）には遠く、データ蓄積段階。
- 25モードが稼働中にもかかわらず前日の執行は**1件のみ**
- Block Counts上位が示す通り、複数のフィルターが連続作動している
- `shadow_tracking`ブロック18件が主因

### 2026-06-24 (Post-London Report)
| 勝率 (WR) | **100.0%** |
| セッションPnL | **+2.4 pips** |
| 戦略 | ペア | 方向 | Outcome | PnL | Spread |
**成功要因**: EUR/JPYがVOLATILE（ATR%ile 67%、SMA20 Slope −0.00032の緩やかな下方傾斜）の環境下でSELLシグナルが機能し、スプレッド1.5pipsを差し引いても正EV実現。OANDA_SL_TPによる規律ある決済が奏功。
| WR | — | 100% |
| PnL | +0.0 | +2.4 pips |
- **EUR系・GBP系（VOLATILE継続）**: ATR%ile 62–72%圏でロンドン終値を引き継ぐため、NYオープン（UTC 13:00–）でボラティリティ縮小局面に入るリスクあり。ただし米指標（週次ベース）次第でスパイクあり。
- **USD_JPY（RANGING）**: SMA20 Slope +0.00350と上向きバイアスあり。RANGING継続ならブレイクアウト系は不利。

### 2026-06-24 (Pre-Tokyo Briefing)
- **前日（2026-06-23）**: トレード数 **N=1**、PnL **+2.3 pips**、WR **100%**
- 唯一のトレードは `wick_imbalance_reversion / GBP_USD / BUY / WIN`（OANDA_SL_TP決済、スプレッド1.3）
- Cutoff後累計: **N=6、WR=66.7%、PnL=-12.0 pips**（wick_imbalance_reversionがN=3で-17.7pipと足を引っ張っている）
| Strategy | Pair | N | WR% | EV | 判定 |
| `wick_imbalance_reversion` の累積損失 | N=3でEV=-5.90、PnL=-17.7。1勝2敗パターン |
- `wick_imbalance_reversion` はEV=-5.90と深刻だが**N=3のため統計的根拠なし**。ただし損失方向への集中を警戒しつつN蓄積を継続監視する
- トレード数が1日1件ペースでは**N=30到達に約1ヶ月**を要する計算。シグナル発生の構造的問題の有無を確認する必要がある
- OANDA NAV/Balanceが`None`のままなので接続状態の検証を優先する

### 2026-06-25 (Pre-Tokyo Briefing)
前日（2026-06-24）は **2トレード、PnL +4.4pip、WR 100%** で完結。trendline_sweep（GBP_USD SELL +2.0）および vsg_jpy_reversal（EUR_JPY SELL +2.4）が共にOANDA_SL_TP / SL_HIT決済で勝利。スプレッドは1.3〜1.5pip圏で正常範囲内。ただしトレード数は極端に少なく、戦略の稼働ポテンシャルと比較して著しく未稼働の状態が続いている。
> ⚠️ **統計的注意**: 全戦略N=1。「傾向」「判断可能」水準（N≥10）に全く達していない。数値は参考記録に過ぎない。
| Strategy | Pair | N | WR% | EV | 統計ステータス |
**全体合計（Cutoff後）**: N=4、WR=100%、PnL=+8.0pip
- Sentinel昇格基準（N≥30）まで全戦略で **残り29件以上** 必要
- OANDA昇格基準（N≥30 & EV≥1.0）の判断は現時点で不可能
- rnb_usdjpy:direction_filterの69件は断然トップ。USD_JPYがRANGINGでSMAスロープ+0.00366と弱いながら上向きの中、方向フィルタが機能していることは**むしろ正常なシステム動作**と見なす
- rr_floor 30件はRANGINGレジームでの構造的問題。ATR%ile 59〜72%はそれほど低くないが、SMAスロープが全ペアで小さく、方向性プレミアムが薄い

### 2026-06-25 (Pre-Tokyo Briefing)
前日（2026-06-24）は**2トレード、全勝（WR=100%）、PnL=+4.4pips**。`trendline_sweep/GBP_USD`と`vsg_jpy_reversal/EUR_JPY`がそれぞれSELL方向でWIN。件数は少ないが質は高い結果。システム全体の発火頻度の低さが依然として最大の制約。
**⚠️ 警告: 全戦略N<10。統計的判断不可能。以下は「記録」であり「評価」ではない。**
| Strategy | Pair | N | WR% | EV | 統計ステータス |
**全体合計: N=6、WR=83.3%、PnL=+3.2pips**
唯一懸念すべきは`dt_sr_channel_reversal/EUR_JPY`のEV=-2.40だが、N=2では統計的ノイズの域を出ない。ただしBT期待値（EV=+0.178）との乖離は記録しておく価値あり。
- 全モード25のうち、前日発火は実質**2戦略・2件のみ**
- Block Counts TOP15を見ると、**hedge_block・same_price_0pip・recent_emit・r2_shadow_demoted_cell**の4類型が支配的
- **hedge_block（53件）**: レンジ相場でのヘッジポジション衝突。全ペアがRANGINGのため構造的に発生しやすい状態

### 2026-06-25 (Post-London Report)
| セッション PnL | **-12.6 pips** |
| EV（/trade） | **-6.30 pips** |
| 戦略 | ペア | 方向 | PnL | Spread | Reason |
- **成功要因（1文）**: SELL方向がEUR_JPYの短期下押しレジームに適合し、1.5pipsの小利確を実現したが、spread 1.8pipsに対して純利益は実質微益（摩擦後EV≈0）。
| 戦略 | ペア | 方向 | PnL | Spread | Reason |
- **失敗要因（1文）**: EUR_JPYはRANGING（ATR%ile=67%、SMA20 Slope=-0.00078）でありながら瞬間的な方向性バイアスが強く、SRチャネルの反発想定が外れてSLヒット（-14.1pipsは標準的なSL幅に相当）。
| セッション PnL | 本日累計-26.4 / N=4より差分: **-13.8 pips** | **-12.6 pips** |
**総評**: 東京セッションはWR=0%（推定）と完敗、ロンドンセッションは50%に改善したが依然として負のEV。1日を通じてdt_sr_channel_reversalのEUR_JPYが唯一のシグナル源であり、戦略集中度が極端に高い。ロンドン時間帯でRANGINGが継続しており、レジーム変化は確認されなかった。

### 2026-06-25 (Pre-Tokyo Briefing)
前日（2026-06-24）は **2トレード、WR 100%、PnL +4.4pip** と小規模ながらクリーンな結果。`trendline_sweep / GBP_USD (+2.0)` および `vsg_jpy_reversal / EUR_JPY (+2.4)` の2件がいずれもWINで完結。両トレードともスプレッド1.3-1.5pipと正常範囲内。
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
> ⚠️ **全戦略 N<10**。統計的判断は不可能な段階。EVの絶対値より「傾向の方向」として読む。
- **昇格基準 N=30** に対し、最大 N=3（dt_sr_channel_reversal）
- 最速到達候補でも残り **27件**。現在の約定ペース（2件/日）で換算すると **約13-14営業日後**
- 全戦略が実質「観察前期」。本日以降の積み上げが最優先課題
- **稼働モード25種** に対し前日約定2件は著しく低い
- daytrade_1h系（9モード稼働）・scalp_5m系（3モード稼働）の全てでゼロ約定

### 2026-06-26 (Pre-Tokyo Briefing)
前日（2026-06-25）は**4トレード、WR=25.0%、PnL=−26.4pip**。3連敗（内2件はOANDA_SL_TP、1件はSL_HIT）が収益を圧迫。Cutoff後の全期間累計でも**N=7、WR=57.1%、PnL=−19.7pip**と損失圏にある。本番稼働ながら生成される実トレードは極めて限定的。
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
> **注記**: 全戦略ともN<10。判断基準上は「データなし」扱い。EV・WRの数値は傾向の参考に留める。昇格/降格判断は時期尚早。
前日3トレード中2敗（WR33.3%、EV=−6.30）。特に1件の−14.1pip（OANDA_SL_TP）が致命傷。EUR/JPYはRANGINGレジーム（ATR%ile=62%）かつSMA20 Slope=−0.00126（緩やかな下向き）。チャネルリバーサル系は方向感が出にくいRANGING中でも機能し得るが、**SL幅に対してリターンが小さい非対称な損益構造**が顕在化している。
| EUR_USD | RANGING | 66% | −0.00496 | ボラ高め。trendline_sweep/bb_squeeze系はブレイク方向への追従が必要。下向きSlopeに注意 |
- **東京セッション（09:00〜15:00 JST）**: USD/JPYはSMA上向き（+0.00370）で東京時間の円安方向の動きに注目。rnb_usdjpy の方向フィルターが緩む条件が揃うか監視。
- **ロンドンオープン（16:00〜17:00 JST）**: GBP/USDのSMA Slope=−0.00454。ロンドン勢の売り持続なら wick_imbalance_reversion のBUYシグナルは逆張りリスクが高い。
- **NYセッション（22:00〜 JST）**: EUR/USD 66%ile ATRで荒い値動きの可能性。

### 2026-06-26 (Pre-Tokyo Briefing)
前日（2026-06-25）は **4件執行、WR 25.0%、PnL -26.4pips**。
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
> **全戦略N<10のため統計的判断不可。** `dt_sr_channel_reversal / EUR_JPY` のみN=4で「傾向値」として観察可能だが、EVの著しい悪化（BT時EV=+0.178 vs LIVE EV=-7.48）は要追跡。
- BT想定EV=+0.178はWR≈63.8%を前提とするが、直近LIVE WR=25%（3戦1勝）と大きく乖離
- EUR_JPYレジームが **RANGING（SMA20 Slope=-0.00126、ATR%ile 62%）** であり、チャネル・SR反転系は「方向が定まらない中での逆張り」が刺さりにくい局面と整合
- N=1のため断定不可。ただしGBP_USDも **RANGING（ATR%ile 59%、Slope=-0.00454下落基調）** で、GBP全体がソフト地合い
- 上記2戦略の新規シグナルに対しては「N蓄積期間中の観察継続」として現行ブロック設定の効果を確認する
- 大負けの主因となっている **SL設定とR:R比の非対称性** については、パラメータ検討の材料として記録

### 2026-06-26 (Post-London Report)
| 勝率 (WR) | 25.0% |
| 総PnL | **-29.2 pips** |
| 平均PnL/trade | -7.3 pips |
ロンドンセッションは全4件中3件がSL_HIT。EV水準はマイナスで終了。
| 戦略 | ペア | 方向 | PnL | 成功要因 |
| **vsg_jpy_reversal** | EUR_JPY | SELL | **+2.1 pips** | 逆張りシグナルが短期下押しをキャプチャ、スプレッド(1.6)対比で辛うじてポジティブEVを確保 |
| 戦略 | ペア | 方向 | PnL | 失敗要因 |
| **zz_pivot_v60_sr** | EUR_USD | SELL | **-10.5 pips** | RANGING環境でピボット反転期待が外れSL直行、スプレッド0.8pipsと低水準ながらEV=-10.5 |

### 2026-06-26 (Pre-Tokyo Briefing)
| PnL合計 | **-26.4 pip** |
| 全体WR | **25.0%** (1勝3敗) |
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
| dt_sr_channel_reversal | EUR_JPY | **5** | 20.0% | **-7.94** | -39.7 | ⚠️ N不足・EV深刻 |
> **凡例**: N≥30 & EV≥1.0 → 昇格候補 ｜ N≥30 & EV<-0.5 → 降格検討 ｜ N<10 → データなし扱い
**Cutoff後全期間合計**: N=10, WR=40.0%, PnL=-51.2pip
| トレード | 方向 | PnL | 終了理由 |
3件全てSELL。EUR/JPYのレジームは**RANGING（SMA20 Slope=-0.00177）**であり、下落トレンドを前提としたSELLポジションが機能しにくい地合い。SR-Channelリバーサル系はレンジ相場では誤シグナルが増加しやすい。BT上のEV=+0.178（EUR_JPY）は「弱い正」であり、スプレッド・スリッページ込みの実運用では容易にマイナス転化する水準。

### 2026-06-29 (Pre-Tokyo Briefing)
| PnL合計 | 0.0 |
| 全体WR | N/A |
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
| N合計 | WR | PnL合計 |
- 前日（06-28）は全セッション無発火。
- Block Count上位を見ると、**rnb_usdjpy:direction_filter（135件）**、**daytrade:hedge_block（127件）**、**daytrade_eur:hedge_block（113件）** が支配的。
- これは「市場の方向性とシステムのフィルター条件が一致しない」状態が継続していることを示す。
- 全50シグナルのうちLIVE送信はわずか3件（6%）。

### 2026-06-29 (Pre-Tokyo Briefing)
**2026-06-28: トレードゼロ日**。前日は全セッション（東京・ロンドン・NY）を通じてシステムがシグナルを発生させず、PnL=0、N=0、WR=N/A。直近の執行実績はCutoff後累積N=12に留まる。
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
**累計: N=12、WR=50.0%、PnL=-46.9**
> ⚠️ **全戦略がN<10水準**。統計的判断基準上、現時点では全て「データなし」扱い。EVの正負は傾向として参照するに留める。
- `recent_emit`ブロックが優勢（GBP_JPY:15件、daytrade:14件、GBP_USD:14件）— シグナルは発生しているが連続発火を抑制中
- `rnb_usdjpy:direction_filter`が15件 — レンジ環境下でのRnB戦略の方向性フィルタが強く機能
- `eurgbp:same_price_0pip`が10件 — エントリー条件の価格判定で弾かれ続けている
- `recent_emit`連発はシステムが意図的に自己抑制している状態。過去シグナルの消化待ちであり、東京時間オープン後にフレッシュなシグナルが発生するか注視

### 2026-06-29 (Post-London Report)
| 勝率（WR） | 87.5% (7W/1L) |
| 総PnL | **+3.3 pips** |
| 平均EV/トレード | +0.41 pips |
> ⚠️ WRは優秀（87.5%）だが、**単一LOSS（-8.5 pips）が7勝の+11.8 pipsを食いつぶし**、セッション利益を圧縮。リスク非対称性に注意。
| 戦略 | ペア | PnL | 成功要因 |
| 戦略 | ペア | PnL | 失敗要因 |
**EVの矛盾**: セッション内のzz_pivot_v60_srはN=4でEV=-1.07だが、同戦略が3勝しながら単一の-8.5 pips LOSSで全体EVを引き下げる「逆サイズ問題」が見える。TP/SL非対称がセッション単位で顕在化。
> ※東京セッションデータが本データセットに明示されていないため、本日累計（N=9, WR=88.9%, PnL=+5.4）とセッション内（N=8, WR=87.5%, PnL=+3.3）の差分から推定。

### 2026-06-29 (Pre-Tokyo Briefing)
前日（2026-06-28）は**トレードゼロ**。本日06:29 UTCまでの累積でもCutoff後N=19、PnL=**-48.7**（WR 57.9%だがEVは全体的に低調）。前日はエントリー条件を満たすシグナルが生成されなかった、または全シグナルがブロックされた可能性が高い。
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
- **トレードゼロ（前日）**: エントリー条件未充足またはブロック。RANGING相場が支配的な中、DT系シグナルの閾値をクリアできなかった可能性。
- **EV構造の悪化**: 最大Nを持つ`dt_sr_channel_reversal/EUR_JPY`（N=6）がEV=-6.27と深刻。WRが33.3%であり、勝ちトレードが損失をカバーできていない（損小利大の逆構造）。
- **PnL集中リスク**: 全損失の77%が`dt_sr_channel_reversal/EUR_JPY`の単一戦略ペアから発生。
- `dt_sr_channel_reversal/EUR_JPY` はN=6で既に危険シグナル。KB記載のBTデータ（EV=+0.178）との乖離が拡大中。**N=10到達時に改めてEV確認し、乖離継続なら降格検討**を優先議題に乗せる。
- `zz_pivot_v60_sr/EUR_USD` はKB未記載戦略と思われる（PAIR_PROMOTEDリストにない）。N=5でEV=-2.96は要注意。
| GBP_USD | **RANGING** | 62% | -0.00455 (緩やかな下落) | trendline_sweep（実績WR100%）は引き続き注視 |

### 2026-06-30 (Pre-Tokyo Briefing)
前日（2026-06-29）は **N=10、WR=80.0%、PnL=+4.9pip** と表面上は強い勝率を記録。ただしzz_pivot_v60_srの1発の大負け（-8.5pip）が足を引っ張り、**EV加重での収益性は抑制的**。オープンポジションなし、OANDA残高は**283,543 JPY相当、Latency=87.6ms**で接続は安定。
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
| zz_pivot_v60_sr | EUR_USD | 5 | 60.0% | **-2.96** | -14.8 | 🔴 EV懸念 |
| dt_sr_channel_reversal | EUR_JPY | 6 | 33.3% | **-6.27** | -37.6 | 🔴 最悪EV |
**全体（Cutoff後）: N=19、WR=57.9%、PnL=-48.7pip**
| WR | 75.0%（3勝1負） |
| 日次PnL | **-4.3pip** |
- **3勝しても1敗で赤字**という損益比の非対称性が明確。WR75%でもEV=-1.07は、リスクリワード比が構造的に不利（≒1:0.5前後）である可能性を示唆。

### 2026-06-30 (Pre-Tokyo Briefing)
前日（2026-06-29）は **N=10、WR=80.0%、PnL=+4.9pips** と表面上好調。ただし `zz_pivot_v60_sr` が1件の大損（-8.5）を出しており、8勝1敗1BEの結果としては期待値が歪んでいる点に注意。ポジションはすべてクローズ済み（Open Trades=0）。
### 全期間サマリー（N=19, WR=52.6%, PnL=−56.6）
| Strategy | Pair | N | WR% | EV | 評価 |
> **全戦略N<30のため「判断可能」水準未達。ただし傾向として全5戦略がEV負値、唯一の例外はvsg_jpy_reversalのみ（N=2）。**
| Strategy | Pair | N | WR% | EV | コメント |
- 前日4件中3勝1敗だが、敗1件が **−8.5pip**（他3勝の合計 +4.2pip を吸収し日次EV=−1.07）
- 全期間EV=**−2.96**（N=5）は「傾向」として悪い。SL幅対TP幅の非対称（RR<1:1疑い）が構造的問題と考えられる
- **対策判断**：N=30到達を待ちつつ、追加のサンプル蓄積を最優先。現時点では降格の根拠として扱えないが、EV悪化が続けばN=15前後で要再評価

### 2026-06-30 (Post-London Report)
| 勝率 (WR) | **0.0%** (0勝2敗) |
| 総PnL | **-18.7 pips** |
| 平均PnL/Trade | -9.35 pips |
| 戦略 | ペア | PnL | 失敗要因 |
| `trendline_sweep` | GBP/USD | **-5.9 pips** | BUY後にSIGNAL_REVERSE — GBP/USDはRANGINGレジーム（ATR%ile 62%）でレンジ内の偽ブレイク。スプレッド1.3pipsも摩擦コストとして寄与。 |
| WR | — | 0.0% |
| PnL | — | -18.7 pips |
本日累計N=2・PnL=-18.7pipsは全てロンドンセッション分。東京セッション（UTC 00:00-07:00）に記録されたトレードは**0件**であり、ロンドンが唯一の執行ウィンドウだった。ロンドン特有の流動性向上局面でもエントリー確保は困難で、フィルター強度が機会を過度に制限した可能性がある。

### 2026-06-30 (Pre-Tokyo Briefing)
前日（2026-06-29）は **N=10 / WR=80.0% / PnL=+4.9pip** と勝率面では良好。ただし大型損失（zz_pivot: -8.5pip SL_HIT）が1件あり、勝利の積み上げを相殺。全体PnLは軽微なプラスにとどまった。Cutoff後の全期間累計では **N=18 / WR=50.0% / PnL=-57.4pip** と構造的損失が継続している点に注意が必要。
| Strategy | Pair | N | WR% | EV | 判定 |
| dt_sr_channel_reversal | EUR_JPY | 3 | 33.3% | **-6.23** | 🔴 最悪EV |
> **統計的留保**: 最大N=5。全戦略が「データ不足（N<10）」フェーズ。EVの正負は傾向としてのみ解釈。判断可能水準（N≥30）まで最低25件以上の蓄積が必要。
前日4件中、WIN×3（+1.7/+1.7/+0.8）に対し LOSS×1（**-8.5**）。ペイオフ比が非対称で、1回の大損が3勝を吹き飛ばす構造。全期間EV=-2.96はこの非対称性を反映している。
**対処方針**: SL設定の適切性を確認。勝ちPnLの分布（+0.8〜+1.7）に対しSLが-8.5まで許容されている場合、RR比が根本的に歪んでいる可能性を認識しておく。
### 課題②：dt_sr_channel_reversal の EV最悪値
N=3でEV=-6.23。前日は+2.1で勝利したものの、全期間では3戦1勝（-18.7pip累計）。直近1勝で回復した印象があるが、構造的に劣位な可能性がある。

### 2026-07-01 (Pre-Tokyo Briefing)
**2026-06-30**: トレード数 **N=3**、PnL **−25.6**、WR **0.0%**
全3件がSL_HIT/SIGNAL_REVERSEによる損切り。trendline_sweep (GBP_USD) が2連敗、xs_momentum_rsi (USD_JPY) が単発大幅損失（−12.8）。直近の損失集中が顕著。
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
| zz_pivot_v60_sr | EUR_USD | 5 | 60.0% | −2.96 | −14.8 | ⚠️ N不足・EV負 |
| trendline_sweep | GBP_USD | 4 | 50.0% | −2.35 | −9.4 | ⚠️ N不足・EV負 |
| dt_sr_channel_reversal | EUR_JPY | 3 | 33.3% | −6.23 | −18.7 | ⚠️ N不足・EV大幅負 |
> **全体**: N=17、WR=52.9%、PnL=**−49.9**
> ⚠️ 昇格基準（N≥30 & EV≥1.0）を満たす戦略は**ゼロ**。降格基準（N≥30 & EV<−0.5）も判定不能（N不足）。全戦略がSentinel段階。

### 2026-07-01 (Pre-Tokyo Briefing)
前日（2026-06-30）は **3トレード、WR 0.0%、PnL -25.6** と完全にゼロ勝の日。trendline_sweep（GBP_USD）が2連続SL_HIT+SIGNAL_REVERSEで-12.8、xs_momentum_rsi（USD_JPY）が-12.8。全セッションを通じて単一方向（BUY）のみで損失が集中した。
| Strategy | Pair | N | WR% | EV | 判定 |
| trendline_sweep | GBP_USD | 7 | 57.1% | **-1.81** | 負EV（N不足）|
| zz_pivot_v60_sr | EUR_USD | 5 | 60.0% | **-2.96** | 負EV（N不足）|
| dt_sr_channel_reversal | EUR_JPY | 3 | 33.3% | **-6.23** | 負EV（N不足）|
**全体**: N=20、WR=55.0%、PnL=-53.2
- GBP_USDは現在**RANGING（ATR%ile 62%）**、SMA20スロープ -0.00440と下向き。BUYバイアスが構造的に不利なレジームに当たった。
- SIGNAL_REVERSEでの損失（-5.9）は、エントリー後すぐに方向が反転していることを示す。RANGING相場でのトレンドフォロー型エントリーが機能していない典型。

### 2026-07-01 (Post-London Report)
PnL       : N/A
WR        : N/A
レジーム・WR・PnL比較は実施不可
- ロンドン→NY移行は通常、**USD主導のボラティリティ再拡張フェーズ**
- 本日が月初（2026-07-01）であることから、**月初ISM/PMIリリース**の影響を想定すべき
- 月初1日目のNYは統計的に**方向性が出やすい**がフェイクブレイクも多い
### 推奨戦略配分
| **NO ACTION推奨（暫定）** | リアルタイムデータが一切取得できない状態での新規判断は禁忌。ポジション管理の根拠がない |

### 2026-07-01 (Pre-Tokyo Briefing)
| 総PnL | **-25.6 pip** |
| Strategy | Pair | N | WR% | EV | 判定 |
| 2 | BUY | LOSS -5.9pip | SIGNAL_REVERSE | 1.3 |
- 両件ともBUY方向。GBP_USDは現在RANGING（ATR%ile 60%、SMAスロープ-0.00396で微弱下向き）
- SIGNAL_REVERSEによるロスは、シグナル自体がエントリー後すぐに反転を示していることを意味する。Ranging相場でのトレンドライン系戦略は構造的に不利
- spread 1.3はDT閾値20%に対して問題ないが、EV=-4.09はスプレッドだけでは説明できない。損益構造（SLサイズ vs TPサイズ）に本質的な問題がある可能性
- N=1のため統計的判断不能
- ただし-12.8pipという損失幅は突出して大きい。SLサイズが他戦略比で過大の可能性

### 2026-07-02 (Pre-Tokyo Briefing)
| 前日PnL | **-23.3 pip** |
| 全体WR | **50.0%** |
前日は trendline_sweep (GBP_USD) が4件エントリー。勝ち2件合計 +4.0pip に対し、負け2件合計 -27.3pip という**非対称な損益構造**が確認された。EV -5.83はサンプル数が少なく統計的ノイズだが、1件目の-20.0pip大損が全体を支配している点は注視。
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
| trendline_sweep | GBP_USD | 8 | 50.0% | -4.09 | -32.7 | ⚠️ N不足・EV負 |
**昇格基準（N≥30 & EV≥1.0）達成戦略：なし**
**降格基準（N≥30 & EV<-0.5）該当戦略：なし（全戦略N<30）**
- WIN 2件: +2.0pip × 2 = +4.0pip（RR極めて小）

### 2026-07-02 (Pre-Tokyo Briefing)
- **2026-07-01**: N=4、WR=50.0%、**PnL = -23.3 pips**
- 全4件が `trendline_sweep / GBP_USD` に集中。勝ちトレード2件の利益合計+4.0に対し、負けトレード2件の損失合計-27.3と **ペイオフ比が著しく歪**
- 現在オープンポジション0件。OANDA転送は全50件スキップ（Live Rate 0%）
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
> **全体集計**: N=15, WR=53.3%, PnL=-48.3
> ※ N≥30の戦略なし。全戦略が「判断前」ステータス。降格基準（N≥30 & EV<-0.5）には未到達だが `trendline_sweep/GBP_USD` は傾向として警戒域。
| 件 | 結果 | PnL | 備考 |
- 勝ちPnL平均: **+2.0**、負けPnL平均: **-13.65**

### 2026-07-02 (Post-London Report)
| PnL | **−0.6 pips** |
勝率62.5%に対してPnLが−0.6という結果は、**損益の非対称性（ペイオフ比の悪化）** を端的に示している。
| 戦略 | ペア | 代表PnL | 成功要因 |
| bb_rsi_reversion | USD_JPY | −3.9 pips | 同上：短期上昇圧力下でのSHORT積み重ねがEV=−0.40の主因 |
- 7件すべてが**SELL方向**に集中 → 方向バイアスの固着
- 勝ちトレード平均: +3.2 pips、負けトレード平均: **−5.2 pips** → ペイオフ比=0.62（1.0を大きく下回る）
- Spread=0.8で安定しているためspread_guardの問題ではなく、**方向選択とSL/TP非対称が主因**
本日累計N=11に対しセッション内N=8であることから、**東京セッションはN=3、PnL=−14.4 pips**と推計される。

### 2026-07-02 (Pre-Tokyo Briefing)
前日（2026-07-01）は**4トレード、WR 50.0%、PnL -23.3**という結果。全件が`trendline_sweep / GBP_USD`に集中。2勝はいずれも+2.0止まりだが、1敗は-20.0と非対称なペイオフが全体を引きずり、EV -5.83という深刻な水準。損益構造は「小さく勝って大きく負ける」典型パターン。
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
> **全体**: N=19, WR=57.9%, PnL **-49.8**
| Dir | Outcome | PnL |
- WIN時のペイオフ上限が+2.0に張り付いている一方、LOSS時は-20.0まで伸びる。
- 全件`Reason: SL_HIT`であり、TPが近すぎる / SLが遠すぎるRR設定が疑われる。
- Spread 1.3pipsはGBP/USDとして許容範囲内（Scalp閾値30%以下）であり、スプレッドは主因ではない。
### 課題②：xs_momentum_rsi の壊滅的EV

### 2026-07-03 (Pre-Tokyo Briefing)
**前日（2026-07-02）**: 13トレード、WR 69.2%、PnL **-6.8 pips**
| Strategy | Pair | N | WR% | EV | PnL | 判定ステータス |
| trendline_sweep | GBP_USD | 5 | 40.0% | **-6.04** | -30.2 | 🔴 要注視（N不足+EV負） |
| xs_momentum_rsi | USD_JPY | 2 | 0.0% | **-15.40** | -30.8 | 🔴 危険水域（N不足+EV深負） |
- **昇格基準（N≥30 & EV≥1.0）到達戦略: ゼロ** — 全戦略がN<30の「判断不可」段階
- bb_rsi_reversionはN=11で最も蓄積が進んでいるが、EV=+0.82は昇格閾値（EV≥1.0）未到達
- xs_momentum_rsi・trendline_sweepはN<10につきデータなし扱いが妥当だが、方向性は極めて悪い
- **SL_HITで-18.0pips**は前日bb_rsi_reversionの全利益（+9.0pips）の2倍を吹き飛ばす規模

### 2026-07-03 (Pre-Tokyo Briefing)
**2026-07-02 前日実績**: トレード数 **N=13**、勝率 **69.2%**、PnL **-6.8 pips**
bb_rsi_reversionが9/11で勝利しPnL+9.0を稼いだが、xs_momentum_rsiの単発大敗（-18.0）が全体を押し下げた。Cutoff後累計はN=18、WR=61.1%、PnL=-37.0と引き続き赤字圏。
| Strategy | Pair | N | WR% | EV | 判定 |
- N=1、SL_HITで全額消失。EV=-18.00は統計的には無意味だが、リスク管理の観点では**一撃でbb_rsi_reversionの累積利益（+9.0）の2倍を消す構造**は看過できない
- 前日の全体赤字（-6.8）の主因が100%このトレード1件に起因
- **今日の対処**: xs_momentum_rsiのポジションサイジングが適正かを本番Kellyログで確認。`agg_kelly=-0.326<0`ブロックが発動していたことは確認済みだが、それ以前のエントリー制御を注視
### 課題②：trendline_sweepの累積ドローダウン（N=5, EV=-6.04, PnL=-30.2）
- Cutoff後N=5で最大の損失源。勝率40%・EV-6.04は**小サンプルながら構造的に悪い数字**

### 2026-07-03 (Post-London Report)
| セッション内PnL | **0 pips / 0円** |
| 勝率（WR） | **N/A（取引なし）** |
| PnL | 0 | 0 |
| WR | N/A | N/A |
### 推奨戦略配分
**🔴 NO ACTION推奨**
- 米国独立記念日（7/4）により、NYセッションは流動性枯渇・スプレッド異常拡大の高リスク環境
- spread_guard閾値（DT=20%、Scalp=30%）が機能する前提は通常流動性。本日はその前提が崩れる可能性大

### 2026-07-03 (Pre-Tokyo Briefing)
前日（2026-07-02）トレード数 **N=13**、全体WR **69.2%**、PnL **-6.8**。
`bb_rsi_reversion` 単独では +9.0（WR 72.7%）と堅調。
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
> **全体集計（Cutoff後）**: N=18, WR=61.1%, PnL=-33.7
- N=1、EV=-18.0。統計的には「事故」でなく「損失確定の1件」として記録。
- **SL_HIT** で終了しているため、リスク管理機構自体は機能している。
- ただし損益比率が著しく非対称（`bb_rsi_reversion` の平均TP +1.8〜+7.4 に対し、SL -18.0）。ロットサイジングかSL設定の問題が示唆される。
- **今日の対処**: N=1のため判断保留。ただし本日も発動した場合は **損失構造が戦略設計に起因する可能性**を認識しながら監視。

### 2026-07-06 (Pre-Tokyo Briefing)
**2026-07-05: トレードゼロ日**。前日（7/5）は全セッションを通じてエントリーなし。PnL = ¥0、N = 0、WR = N/A。システムは稼働中だが、フィルター群（hedge_block、r2_shadow_demoted_cell、direction_filter）が全シグナルを遮断した形となった。
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
**全体集計**: N=18、WR=61.1%、PnL=−33.7
- `direction_filter`の93件はrnb_usdjpyが方向を確立できていない状態の継続を示す → **USD/JPY のトレンド方向が固まるまでrnb戦略のシグナルは出ない**と認識して待機
- `hedge_block`はポジションゼロ状態でも発動しているか確認が必要だが、介入不可のため観察継続
- `r2_shadow_demoted_cell`の累積186件：shadow降格済みセルがシグナルを出し続けているのは正常動作。問題はその戦略が本番トレードに貢献できない点 → **Sentinel N蓄積の機会損失が継続中**
| GBP_USD | **RANGING** | 64% | −0.00227 | レンジ内下落。trendline_sweepには逆風（N=4でEV=−5.83と一致） |
**レジーム総評**: USD/JPYのVOLATILE+上昇バイアスは`bb_rsi_reversion`にとって理想的な地合い。一方、GBP/USDのRANGING環境が`trendline_sweep`のEV悪化（−5.83）と整合しており、現環境でのGBP/USD戦略は構造的に不利。EUR/USDも高ATRレンジで偽ブレイクリスク高。

### 2026-07-06 (Pre-Tokyo Briefing)
**2026-07-05（前日）: トレードゼロ。PnL = 0.0、N = 0、WR = N/A。**
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
> **全体: N=15, WR=60.0%, PnL=-30.4（EV加重では負）**
> trendline_sweepはKBでELITE_LIVE指定（GBP_USD: BT EV=+0.599）だが、ライブ1件で-20.0。サンプル数1のため統計的判断不能だが要注視。
- `r2_shadow_demoted_cell`が98件と支配的 → Scalp系セルのデモーション状態が慢性化。これはコード変更ではなく、**当該セルのパフォーマンス回復を待つしかない構造的停滞**。本日も同条件継続を前提に計画する。
- `daytrade_1h_audjpy:order_bar_dedup` 20件 → AUDJPYで1時間足単位のシグナル連打が発生中。実際の約定には至っておらず問題なし。
- `daytrade_eurgbp:hedge_block` 9件 → EURGBPで相反ポジション検知。本日もEUR/GBP通貨交差に注意。
**総評:** USD_JPYのみが方向性×ボラティリティの組み合わせで戦略適合域。EUR/GBP系はRANGING支配で摩擦コストに対しEVが薄い。

### 2026-07-06 (Post-London Report)
| PnL | **0 pips** |
| PnL | 0 | 0 |
| WR | N/A | N/A |
### 推奨戦略配分
> **⚠️ NO ACTION 推奨 — NY序盤（UTC 16:00–17:00）は様子見**
| 累計PnL | **0 pips** |
**推奨判断（実装方法ではなく方向性）**: OANDA Live転送がゼロのまま23モードが稼働し続ける現状は「データ生産コスト（サーバー稼働）に見合う情報を産出していない」状態。NYセッション終了後、Live転送が依然0%のままであれば、shadow_tracking解除の優先度を経営判断レベルで再検討すべき局面に入っている。

### 2026-07-06 (Pre-Tokyo Briefing)
**2026-07-05（前日）はトレードゼロ**。Cutoff後累計はN=15、全体WR=60.0%、累計PnL=**-12.8p**。
勝率は表面上60%だが、EVが+0.82の`bb_rsi_reversion`以外は全て負EVという構造。総PnLはシステム全体がまだ損失域。
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
- **`bb_rsi_reversion` USD_JPY**: 現状最も信頼できるシグナル。N=30到達（残19件）を最優先モニタリング
- **`xs_momentum_rsi`**: N=1・EV=-18.0は「データなし」扱いが統計的に正しいが、損失規模に注意継続
- トレードゼロ日が続くなら、モード設定とエントリー条件の感度確認が必要（実装判断は別途）
- **全ペアがRANGING/VOLATILEでトレンドなし** — トレンドフォロー系（`xs_momentum_rsi`等）には構造的逆風
- **USD_JPY VOLATILEはbb_rsi_reversionに両刃** — 平均回帰は機能しやすいが、オーバーシュート時の損失も大きくなる

### 2026-07-07 (Pre-Tokyo Briefing)
- **前日（2026-07-06）PnL: −2.4p　トレード数: 1件　WR: 0.0%**
- `ny_close_reversal / USD_JPY / SELL` が `SIGNAL_REVERSE` で損切り（スプレッド0.8）
- 実質的に「ほぼ無活動」の一日。累積Cutoff後全体でもN=15に留まる
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
> **全体合計**: N=15 / WR=60.0% / PnL=−12.8p
### 課題①: ny_close_reversal の SIGNAL_REVERSE 損切り
- NYクローズ付近でSELLエントリーしたが、シグナルが反転して損切り
- USD_JPY はCurrentレジーム「VOLATILE」＋ATR%ile 66%。反転系には不向きなレジーム

### 2026-07-07 (Pre-Tokyo Briefing)
前日（2026-07-06）は **N=1、WR=0%、PnL=−2.4p**。`ny_close_reversal / USD_JPY` の1件のみが約定し、SIGNAL_REVERSEで損切り終了。実質的に不活動日。Cutoff後累計はN=16、WR=56.2%、PnL=−19.6p（摩擦考慮後）。
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
- `ny_close_reversal`はSIGNAL_REVERSEで損切り。これはエントリー直後にシグナルが反転したことを意味し、NYクローズ付近のUSD_JPY方向感の不安定さを示す。
- Fidelity Cutoff後のN蓄積が依然として極めて低速（累計N=16、約3ヶ月稼働換算で非常に少ない）。
- Block Count合計99件に対してCutoff後N=16。**ブロック率が圧倒的に高く、シグナル生成自体は機能しているが出口（フィルター）で止まっている**。
- `hedge_block`（daytrade: 18件、daytrade_gbpjpy: 17件）と`direction_filter`（rnb_usdjpy: 17件）が上位を占め、リスク管理フィルターが過剰に機能している可能性。
- `r2_shadow_demoted_cell`（scalp_5m_gbp: 7件、scalp_5m_eur: 4件等）= デモ評価中のセルがシャドウに降格され本番未送信。
- hedge_blockの主因ペア（daytrade, daytrade_gbpjpy）は両建て検出が連続発動中。ヘッジポジション解消まで当該ペアの約定数は回復しない。現状維持で観察。

### 2026-07-07 (Post-London Report)
| WR | **0.0%** (0/1) |
| PnL | **−6.8 pips** |
| 戦略 | ペア | 方向 | PnL | 失敗要因 |
| `dt_bb_rsi_mr` | GBP_USD | BUY | **−6.8p** | SL_HIT — BT上EV陰性（GBP_USD: EV=−0.135）の戦略が逆張りエントリーし、スプレッド1.3pipsの摩擦下でSLまで押し切られた |
**構造的問題**: `dt_bb_rsi_mr` はKBで **GBP_USDのBT EV=−0.135**（USD_JPYもEV=−0.023）と記録されており、今セッションの失敗はノイズではなく **BT期待値の現実化**と解釈すべき。
| PnL | — | −6.8p |
- 現在UTC 17:52 — NYオープン（UTC 13:00）は既に4時間50分経過
- 現時点のレジーム: EUR/JPY・EUR/USD・GBP/JPY・GBP/USD → **RANGING**、USD/JPY → **VOLATILE**（ATR%ile 66%）

### 2026-07-07 (Pre-Tokyo Briefing)
| PnL合計（前日） | **-2.4p** |
| 全体WR | **0.0%** (N=1) |
前日は `ny_close_reversal / USD_JPY` のSELL1件のみ。SIGNAL_REVERSEで決済、-2.4pの損失。活動量は極小。
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
※前日分のN=1のEV=-2.40。全期間集計ではN=2として扱う
| ① | `ny_close_reversal` がSIGNAL_REVERSEで強制決済 → exit執行の崩壊パターン（KB v2.3確認済みの構造的問題と一致） |
- `ny_close_reversal` はN=2・WR=0%。本日も同戦略がファイアした場合、**統計的にノイズ域**であることを念頭に置く
- シグナル頻度の低さはモード数（24）に対してトレード数が極端に少ないことを示す → **ルール通り蓄積継続、介入不要**

### 2026-07-08 (Pre-Tokyo Briefing)
前日（2026-07-07）は **N=1、PnL=-6.8p、WR=0.0%** という最小活動日。`dt_bb_rsi_mr / GBP_USD` の1件のみがSL_HIT（損失-6.8p、スプレッド1.3）。全モードが稼働中にもかかわらず実質トレードゼロに近い状態であり、hedge_blockやr2_shadow_demoted_cellによるフィルタリングが支配的。システムは防御姿勢を維持している。
| Strategy | Pair | N | WR% | EV | PnL | 評価 |
**全体**: N=16合計、WR=56.2%、PnL=-19.6p
- BT EV: -0.135（GBP_USD）と既にマイナス設計
- 昨日SL_HIT -6.8pを追加。累計でもEVはマイナス圏維持
- **今日の対処**: このセルは現在PAIR_PROMOTED（シャドー追跡中）。N蓄積を見守る以外の介入はしない。ただし本番資金露出ゼロ（SKIP=100%）なので被害なし
- 単発で-18pは異常値。STD相当のスリッページかレジームミスマッチの可能性
- N=1のため統計判断不可。ただし警戒フラグとして記録

### 2026-07-08 (Post-Tokyo Report)
| PnL | 0.0 pips |
| WR | N/A |
- 東京セッションN=0 — 統計的判断の基盤が存在しない
- KBにて「exit-repair pre-reg LOCK済み」（BT verdict期日: 07-21）— ロック期間中に調整を加えることは汚染データを生む
- DD=99.33%（$24未満）の防御モード中 — 戦略調整より**DD防御継続**が最優先
- ブロック動作は全て設計仕様内（異常なブロックロジック誤動作ではない）
### 推奨戦略配分
**NO ACTION推奨（実質）**

### 2026-07-08 (Post-London Report)
| PnL | **0.0 pips** |
| 勝率 (WR) | **N/A** |
| `daytrade:hedge_block` | 46 | 反対方向ポジション干渉。オープントレード0件なのにブロック継続は要注意 |
| PnL | 0.0p | 0.0p |
### 推奨戦略配分
| **NO ACTION推奨** | DD=100%超の防御モード下では新規エントリーのリスク/リワードが著しく悪化。NYセッションのVOLATILEレジーム拡大は、ドローダウン深化リスクと隣合わせ |

### 2026-07-08 (Pre-Tokyo Briefing)
**2026-07-07（前日）**: トレード数 N=1、PnL = **−6.8p**、WR = **0.0%**
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
> **注**: 全戦略 N<10。統計的判断は不可能。EVは参考値として記録のみ。
- **状況**: GBP_USD BUYエントリー後にSL直撃。EV=−6.80は1件分の損失そのもので統計的意味なし。
- **本日の対処**: 追加シグナルを待つ。N=1での戦略判断は不可能。KB上では `dt_bb_rsi_mr` の BT EV（GBP_USD: −0.135）が元々微負であり、このペアへのエントリー自体の適切性は引き続き監視対象。
- **状況**: 25モードが稼働中（2モードOFF）にもかかわらず、Cutoff後の累計が N=4 にとどまる。これはシグナルフィルタ（spread_guard、shadow_tracking）が機能している裏返しでもあるが、N蓄積の観点では深刻な低速度。
- **本日の対処**: レジーム変化（VOLATILE移行）によるシグナル増加を期待しつつ、今日の東京セッションでの発火件数を注視する。
- **状況**: KBによればDD=100.01%でバリア突破済み、現在 **0.2x 防御モード**。新高値なし。

### 2026-07-09 (Pre-Tokyo Briefing)
**2026-07-08 実績**: トレード数 N=1、PnL=**-7.9p**、WR=**0.0%**
| Strategy | Pair | N | WR% | EV | PnL |
> ⚠️ 全戦略N<10 → 統計的には「データなし」水準。EVの数値は参考値に留め、昇格/降格の判断材料にはならない。
- USD_JPYは**VOLATILE**レジーム（ATR%ile=66%）で正のSMAスロープ（+0.00245）という**上昇トレンド局面**。
- そこへのSELLエントリーはレジームと逆行しており、SL_HIT必然の状況だった可能性が高い。
- ただしN=2であり、この2件のみでnc_reversalの適合性を断定するのは不適切。
- 25モード中24モードONだが、有効シグナルは前日1件のみ。
- Block countsを見るとhedge_block・direction_filter・r2_shadow_demoted_cellが圧倒的多数を占め、シグナルが存在しても多段フィルターで消滅している構図。

### 2026-07-09 (Pre-Tokyo Briefing)
前日（2026-07-08）のトレード数は**1件**、戦略は`ny_close_reversal / USD_JPY`のSELL。結果はSL_HIT、PnL = **-7.9p**、WR = **0.0%**。Cutoff後累計でもN=4、PnL=-20.7p、WR=0.0%と、有効サンプルは著しく少なく、現時点では統計的判断に耐えない水準。
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
昇格基準（N≥30 & EV≥1.0）に到達している戦略：**ゼロ**
降格基準（N≥30 & EV<-0.5）に到達している戦略：**ゼロ**（N不足）
- **USD_JPYのレジームはVOLATILE（ATR%ile 66%、SMA20 slope +0.00245で上昇バイアス）**
- SELLエントリーに対し、レジームが逆風だった可能性が高い
- ただしN=2のため「戦略の問題」と断定する根拠なし。レジームとの相性として記録にとどめる
- **USD_JPYのVOLATILEレジームが継続中** → ny_close_reversalの逆張り系シグナルが出た場合、レジームとの整合性を意識した観察を続ける（判断はN蓄積後）

### 2026-07-09 (Post-London Report)
| PnL | **0.0p** |
| 勝率(WR) | **N/A** |
- **hedge_block集中** — EUR/GBP系の複数戦略で同時にヘッジ判定。ロンドン時間帯の方向感なき値動き（全ペアRANGING）がポジション相殺を誘発
- **r2_shadow_demoted_cell** — scalp系は既に降格判定済みセルが大量存在し、シグナルが出ても実行に至らない
- **OANDA転送率0%** — 全50件がSKIPで、Live実行ゼロを追認。shadow_trackingブロックが全案件を吸収
| PnL | 0.0p | 0.0p |
| WR | N/A | N/A |
### 推奨戦略配分

### 2026-07-09 (Pre-Tokyo Briefing)
| PnL合計（前日） | **−7.9p** |
| 全体WR（前日） | **0.0%** |
| Strategy | Pair | N | WR% | EV | PnL |
- N=2、WR=0.0%、EV=−5.15
- 前日もSL_HIT（Spread=0.8p）
- ただしN<10のため**「損失傾向」すら統計的に確定不能**。平均回帰の範囲内として扱う
- 25モードが稼働中であるにもかかわらず、Cutoff後の有効トレード総数はわずか**N=4**
- これはエントリー条件の厳格化（spread_guard、レジームフィルター等）が原因と推定される

### 2026-07-10 (Pre-Tokyo Briefing)
前日（2026-07-09）：**トレードゼロ**。PnL = 0、N = 0、WR = N/A。
| Strategy | Pair | N | WR% | EV | PnL |
> ⚠️ **全戦略 N<10 → 「データなし」扱い。** WR・EVの数値は参考値以下。統計的判断不可。
**レジーム遷移リスク：** USD_JPY ATR%ile 66%はレンジ上限付近。ロンドン時間（15:00 JST〜）でブレイクアウトへの遷移に注意。
Kelly値がマイナスということは、現在のポートフォリオEVが実質的にマイナス（または不確定）と判定されている。これは防御モード継続の根拠として整合的であり、システムが自己防衛機能を正しく発動している。逆に言えば、この状態でLive率が上昇した場合は要アラート。
- `agg_kelly<0`による安全遮断が正常作動 → 損失拡大を防いでいる
- GBP系の`gbp_asia_flash_crash`フィルターが東京時間の不良エントリーを防止している
- シャドウ監視体制（Sentinel）は継続稼働しており、N蓄積のインフラは維持されている

### 2026-07-10 (Pre-Tokyo Briefing)
**2026-07-09（前日）: トレードゼロ。PnL = 0。WR = N/A。**
東京・ロンドン・NYの全セッションを通じてエントリーなし。現時点のCutoff後累計はN=3、PnL=−17.1p、WR=0%という極めて薄いサンプル状態が継続している。
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
> ⚠️ **全戦略N<10 → 統計的判断の域外。EV値は参照値として記録するが、昇格・降格判定はいずれも保留。**
- **事実**: 前日（07-09）全セッションでトレードゼロ。本日09:44時点でも当日トレードゼロ。
- **主因候補**:
- レジーム条件（全ペアRANGING）がエントリーフィルターをほぼ通過させていない可能性
- spread_guard が厳格に機能しており、市場条件が閾値外にある可能性

### 2026-07-10 (Post-London Report)
| WR | — |
| PnL (pips) | **0.0** |
- 全ペアRANGING継続が基本シナリオ。USD_JPY ATR66%pileはやや高め → NY序盤（米指標前後）で一時的なブレイクアウト可能性は排除できないが、SMA20 Slope水準（最大+0.00309）はトレンド転換の証拠なし
- **USD_JPY（162.396）とGBP_JPY（217.75）のSlope上昇**はJPY売り継続示唆 → 円安方向のバイアス微弱あり
### 推奨戦略配分
| rnb_usdjpy | USD_JPY | **NO ACTION** | direction_filter 292件は方向性不確定を意味する |
### **→ NY全体: NO ACTION推奨**
| 累計PnL | **-7.8 pips** |

### 2026-07-10 (Pre-Tokyo Briefing)
前日（2026-07-09）はトレードゼロ。Cutoff後の累積実績はN=3、PnL=**−22.5p**、WR=**0.0%**（全3本損切）。実質的にシステムはシグナル生成が止まっており、稼働中モード26本のうちトレードを生んでいるのはわずか3戦略×1件のみという極度の低頻度状態が継続している。
| Strategy | Pair | N | WR% | EV(p/t) | PnL |
> **判断上の注意**: N=3は統計的判断不能（「データなし」扱い）。EVの数値はノイズであり、個別戦略の優劣を論じる意味はない。唯一確認できる事実は「3本全て損切」という点のみ。
- shadow_trackingによるSKIPは設計通りの動作であり問題ではない。本日も同様の構造が継続することを前提に置く。
- agg-Kellyがマイナスである限り、本番OANDA転送は抑制される。WS3 stage-2の結果が出るまでこの状態は続くと想定すべき。
- USD_JPY ATR%ile=64%はRANGING上限に近い。米指標（今週CPI・PPI等）でBreakoutに転じる可能性。その場合、DT系の方向性バイアスが有効化し得る。
- EUR_USDはATR%ile=44%（低め）。london_fix_reversalのリバーサルエッジが発揮されやすい環境。ただしstage-2待ちにつき観察のみ。
- 50件のうち2件のみSENT。残り48件のSKIPのうち19件はshadow_tracking（これは本番転送対象外の設計）、残りはKelly・spread等でフィルター済と推定。

### 2026-07-13 (Pre-Tokyo Briefing)
- PnL合計: **¥0** | トレード数: **0** | WR: **N/A**
- 全モードはON状態にもかかわらず約定ゼロ。シグナル枯渇またはブロック率100%の状態が継続。
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
> ⚠️ **N=3は統計的に「データなし」扱い**。WR・EVは参考値としても信頼性ゼロ。
- 東京・ロンドン・NYの3セッション全てでトレードが発生しなかった
- 26モードがONにもかかわらず、Block Countsが総計約540件超に達している
- **主因の構造**:
- 50件中48件がSKIP（デモ止まり）

### 2026-07-13 (Pre-Tokyo Briefing)
| PnL合計 | **0.0** |
| 全体WR | **N/A** |
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
- **合計 N=2、全体WR=0%、合計PnL=−15.7**
- N<10のため「データなし」扱い。いずれの戦略も昇格・降格の判断材料にならない
- **Sentinel N蓄積進捗**: 最上位戦略でもN=1/30。昇格基準（N≥30）まで**29件以上**必要
- `r2_shadow_demoted_cell`が最大ブロック要因（40件）→ shadow tier評価でdemoteされたセルへのエントリーを全て排除している。シャドウ判定ロジックが現在のレジームで非常に厳しく機能している
- `hedge_block`（21件）→ 逆方向ポジションとの干渉ブロック。ポジションなし（Open Trades=0）にもかかわらず発生しているのは、**前回エントリー方向の記憶が残存している可能性**

### 2026-07-13 (Post-London Report)
| セッション内PnL | **0 pips / 0円** |
| 勝率（WR） | **N/A** |
| PnL | 0 | 0 |
| WR | N/A | N/A |
### 推奨戦略配分
> **⚠️ NO ACTION推奨（条件付き）**
- USD_JPYに米指標（CPI・FOMCネタ等）が重なりATR急上昇した場合のみ、rnb_usdjpyのdirection_filter解除を確認してから評価
- それ以外は静観が合理的

### 2026-07-13 (Post-NY Report)
| PnL | **データなし** |
| WR | **データなし** |
| WS3 stage-2 barrier/EV設計 | 2026-07-10 | ❌ FAIL（PR #75） |
### セッション別PnL比較テーブル
| セッション | PnL | トレード数 | WR |
- **摩擦調整EV負のセルが全戦略に存在**（v2.3診断確定）
- **勝ち側exit執行の崩壊**：設計TP実走MFEの5倍乖離、trail返上142.5p/30d
- **M1目標（月次符号転換）すら達成できていない可能性**：DD=100.01%での防御モード継続中

### 2026-07-14 (Pre-Tokyo Briefing)
| PnL合計 | 0.0 |
| 全体WR | N/A |
| Strategy | Pair | N | WR% | EV | PnL |
> ⚠️ **N=2（統計的判断不能）**: 両戦略とも「データなし」扱い。EV・WRは参考値に過ぎず、現時点で昇格・降格判断の素材にならない。
**対処の方向性（判断のみ）**: 今日も同様のレジーム（RANGING）が続く限り、hedge_blockが継続する蓋然性が高い。本日は同通貨群の相関シグナル集中に注意。
GBP系のフラッシュクラッシュガード発動。GBP_USDのATR%ile=34%（低位）にもかかわらずガードが作動しており、ボラ検知ロジックとATRの乖離に注意。
- **DaytradeとRNB**: RANGINGはtrendフォロー型には不利。hedge_blockとdirection_filterが継続して発動する環境。
- **Scalp系**: レンジ環境はScalpに理論上有利だが、r2_shadow_demoted_cellによる自己ブロックが有効エントリーを消している。構造的な阻害要因がレジーム優位を打ち消している状態。

### 2026-07-14 (Post-Tokyo Report)
| PnL | — |
| 勝率(WR) | — |
- エントリーゼロの原因が「シグナル未発生（レジーム由来）」なのか「gate条件による抑制（agg-Kelly / spread_guard）」なのかは現データのみでは切り分け不可
- 全ペアが **RANGING / ATR%ile 34–67%** という中程度ボラティリティ帯にあり、シグナル発生しにくい条件は説明可能
- DD=100.01%（100%バリア突破後 held）の **DD防御0.2x モード発動中** — この状態でのパラメータ緩和は禁忌
### 推奨戦略配分
**→ NO ACTION 推奨（ただし条件付きで監視継続）**
- UTC 07:00–08:00（ロンドン本格参入）以降、USD_JPY(ATR%ile=67%)でブレイクアウトが発生した場合、daytrade_eurjpy / rnb_usdjpy のシグナルが復活する可能性。ただし本番約定にはagg-Kelly解消が必要。

### 2026-07-14 (Post-London Report)
| 勝率 (WR) | 100.0% |
| PnL | +3.6 pips |
| EV/trade | +1.80 pips |
| 戦略 | ペア | 方向 | PnL | 成功要因 |
ただし「失敗がない」＝「良好」と即断するには N=2 は不十分。稼働中の全26モード（daytrade系・scalp系・rnb_usdjpy）でトレード発生がゼロであることは、シグナル枯渇・フィルター超過締め出しの観点で要注意（後述クオンツ見解参照）。
本日レポートには東京セッション（UTC 00:00–07:00）の独立集計が含まれていないため、**日中累計として本日合計 N=2 / WR=100% / +3.6p がそのままベースライン**となる。
| WR | — | 100% |
| PnL | — | +3.6p |

### 2026-07-14 (Post-NY Report)
| PnL (pips) | **0.0** |
| WR | **—** |
### セッション別PnL比較
| Session | N | WR% | PnL (pips) | 評価 |
| 本日合計PnL | **+3.6 pips** |
| 本日WR | **100.0%** (N=2、統計的判断不可) |
> **N=2は統計的に「データなし」扱い。** WR 100%は構造的優位を示すものでなく、サンプルノイズと区別不能。
| 🔴 高 | **vix_carry_unwind 乖離アラート** | BT WR 100%（N=0、意味不明）vs Live WR 66.7%（N=3）— N=3は判断不能域だが🔴アラートが発報されている。N≥10に到達するまで追跡継続 |

### 2026-07-15 (Pre-Tokyo Briefing)
前日（2026-07-14）は **vix_carry_unwind / USD_JPY** が2件執行、**PnL = +3.6p、WR = 100%（2/2）**。全セッションを通じてシステムが生成したシグナルは極めて限定的で、稼働中モード26個に対してトレード数はわずか2件。量的にはほぼ沈黙に近い一日だった。
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
| vix_carry_unwind | USD_JPY | 3 | 66.7% | -1.40 | -4.2 | ⚠️ N不足／EV負 |
### 課題①：EV構造の矛盾
前日2件はWR=100%・PnL=+3.6pで良好に見えるが、**Cutoff後累計EVは-1.40**。これは勝ち3件／負け1件（N=3）で全体が-4.2pであることを示す。1件の負けトレードが+5.4p以上を消した計算になる。**ペイオフ非対称（勝ち小／負け大）の構造的問題が継続中**であることをKBが示す通り、前日の好結果はサンプルノイズと解釈すべき。
| WR | 100% | 66.7% |
| ΔWR | — | -33.3pp 🔴 |
BT側N=0（ファイル記録なし）に対してLive WR=66.7%というアラートは、**比較基準そのものが不安定**であることを意味する。BTファイル（ws3_stage2_barrier_sim_oos2.md）のWR=100%は参照上の問題を含む可能性があり、乖離アラートを字義通りに受け取るのは危険。

### 2026-07-15 (Post-Tokyo Report)
| PnL | 0p |
| WR | N/A |
- 本日のシグナルゼロは「フィルター過剰」か「市場条件の不成立」か現時点では判別不能
- OANDA転送率0%（50件全SKIP）はコード問題ではなくshadow_tracking=18件 + agg_kelly負値=2件によるもので、設計通りの動作
- DD=100.01%（100%バリア突破後 held）でDD防御0.2x発動中 — この状態でのパラメータ緩和は禁忌
- vix_carry_unwind / USD_JPY の乖離（N=3, WR=66.7% vs BT 100%）はN<10のため「データなし」として扱う
### 推奨戦略配分
**NO ACTION推奨**

### 2026-07-15 (Post-London Report)
| PnL | **0.0 pips** |
| WR | N/A | N/A |
| PnL | 0 | 0 |
### 推奨戦略配分
> **NO ACTION推奨**
| 累計PnL | **0.0 pips** |
KB記録にある「勝ち側exit崩壊・摩擦調整EV全負」という v2.3診断と照合すると、**「発火しない」こと自体が悪いわけではなく、むしろ品質フィルターが機能している証拠**と解釈するのが合理的。WS3外部仮説移行という正しい方向性のもと、**今夜のNYセッションについて既存モードへの追加的な期待・介入は不要**。Sentinel N蓄積（N=0/30）の進行を静観し、外部仮説スクリーニング（KB: `external-hypothesis-scan-2026-07-13`ライン）の進捗を優先せよ。

### 2026-07-15 (Pre-Tokyo Briefing)
前日（2026-07-14）は **N=2、WR=100%、PnL=+3.6p** と良好な結果。
ただし当日（2026-07-15）累計は **N=4、WR=50%、PnL=−4.1p** と反落しており、前日の利益を全損に近い形で削っている。
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
| vix_carry_unwind | USD_JPY | 3 | 66.7% | **−1.40** | −4.2 | ⚠️ EV負（N不足） |
**全体**: N=4 / WR=50.0% / PnL=−4.1p
> ⚠️ **N=4 は統計的に「データなし」水準**。EV・WRはいずれも判断材料として不十分。
| Strategy | Pair | N | WR% | EV | PnL |
| Strategy | N_BT | WR_BT | N_Live | WR_Live | ΔWR | Alert |

### 2026-07-16 (Pre-Tokyo Briefing)
前日（2026-07-15）トレード数 **N=1**、PnL **+0.1p**、WR **0%（BREAKEVENのため）**。
唯一のトレードは `ny_close_reversal / USD_JPY / SELL` がシグナルリバーサルにより BREAKEVEN 決済。実質的にほぼノーアクションの一日。
| Strategy | Pair | N | WR% | EV | 判定 |
| vix_carry_unwind | USD_JPY | 3 | 66.7% | −1.40 | ⚠️ N不足・EV負 |
> **統計的注記**: 全戦略 N<10。本基準では「データなし」扱い。WR・EVは参考値に過ぎず、判断の根拠として使用不可。
- 26モードが起動中であるにもかかわらず、昨日のシグナル発火は **1件のみ**。
- ほぼすべてのモードで `Trades=0` の状態が継続。システムは動いているが、エントリー機会を捕捉できていない。
- **今日の注視点**: シグナル発火数のモニタリング。特に東京時間オープン（USD/JPY）でのスキャン稼働確認。

### 2026-07-16 (Post-Tokyo Report)
| PnL | 0.0p |
| WR | N/A |
- セッション内N=0のため統計的判断材料が皆無
- block機能は設計通り作動（異常ではない）
- DD防御モード（0.2x）が継続稼働中 — 積極的な調整は禁忌
- 現在のRANGINGレジーム（EUR_JPY 60%ile / USD_JPY 67%ile）はシステムの保守的フィルターが働きやすい環境
| GBP_USD | VOLATILE / 59%ile | **最注意** — VOLATILE分類唯一のペア、ロンドン勢の建玉でトレンド発生の可能性 |
### 推奨戦略配分

### 2026-07-16 (Post-London Report)
| PnL | **0 pips / 0円** |
| WR | **N/A** |
- **OANDA転送率 0%**（50件SKIP、SENT=0）— ライブ到達がゼロ
- **OANDA Blockの全件が `shadow_tracking`（20件）** — デモシャドウ追跡のみで実執行ゼロ
- **`daytrade_xau`・`scalp_xau`・`scalp_eurjpy` がOFF継続** — XAU系は本日も非稼働
| PnL | 0 | 0 |
| WR | N/A | N/A |
### 推奨戦略配分

### 2026-07-16 (Pre-Tokyo Briefing)
前日（2026-07-15）は **トレード1件、WR 0.0%、PnL +0.1p** という極めて低活動な1日。ny_close_reversal / USD_JPY が BREAKEVEN（SIGNAL_REVERSE 決済）のみで、実質的なアルファは生成されなかった。
| Strategy | Pair | N | WR% | EV | PnL |
> **統計的地位**: 全戦略 N<10。「データなし」ゾーン。数値は参考値であり、判断の根拠にならない。vix_carry_unwind の WR 100% は N=2 によるノイズ。
| ① | トレード数 = 1件（BREAKEVEN） | エントリーシグナル発火が極端に低頻度。レジーム全ペアがRANGING/VOLATILEで戦略条件を満たしにくい状態 |
| ② | SIGNAL_REVERSE による早期決済 | エントリー直後に逆シグナルが発生 → NY クローズ付近のノイズ帯での誤発火の可能性 |
| ③ | spread = 0.8（USD/JPY） | spread_guard 閾値（DT=20%）以内だが、BREAKEVENは摩擦費用を回収できていないことを示す |
- SIGNAL_REVERSE BREAKEVENの頻度を蓄積観察する。単発では判断不可だが、繰り返し発生する場合は ny_close_reversal のエントリータイミング適合性を疑う根拠となる
- N蓄積最優先。現状N=3では全ての戦略が評価不能帯にある

### 2026-07-17 (Pre-Tokyo Briefing)
前日は東京・ロンドン・NY全セッションを通じてシグナル成立ゼロ。PnL=±0、WR=N/A。
Cutoff後累計は vix_carry_unwind(USDJPY) 2件 + ny_close_reversal(USDJPY) 1件の計**N=3、PnL=+3.7p**のみ。
| Strategy | Pair | N | WR% | EV | PnL | 判定ステータス |
> ⚠️ **XAUモード（daytrade_xau / scalp_xau）はOFF**のため計上なし。昇格基準（N≥30 & EV≥1.0）・降格基準（N≥30 & EV<−0.5）ともに、現時点では対象戦略なし。
- 前日は24時間で約定ゼロ。Block Countsを見ると**direction_filter（90件）**と**gbp_asia_flash_crash（71件）**が最大要因。
- **direction_filter**（rnb_usdjpy）：USD_JPYはRANGING（ATR%ile 67%、SMA slope +0.00243）で方向感は存在するが、rnb系のフィルターが現レジームで過剰抑制している可能性。
- **gbp_asia_flash_crash（71件）**：daytrade_eurgbpのGBP特有ガードが繰り返し発火。GBP_JPYはVOLATILE+RANGING移行帯（ATR%ile 62%）にあり、フラッシュクラッシュ判定閾値に頻繁に触れている。
- daytrade_eur、daytrade、daytrade_1h_audjpyでhedge_blockが多発。複数モードが同一方向に競合エントリーしようとし、内部ヘッジ判定でキャンセルされている構造。

### 2026-07-17 (Post-Tokyo Report)
| PnL | 0.0p |
| 勝率（WR） | N/A |
- 今日の非執行はすべてシステムの正常なリスク管理動作（`hedge_block`・`dedup`）
- 本日Cutoff後有効トレードN=0につき、統計的判断材料なし
- OANDA Live Rate 0%（50/50件がSKIP）は`shadow_tracking`が18件を占めるデモ追跡フェーズとして整合的
- daytrade_xau・scalp_xau・scalp_eurjpyはOFF継続 → 変更不要
### 推奨戦略配分

### 2026-07-17 (Post-London Report)
| PnL | **0.0 pips** |
| 勝率（WR） | **N/A** |
| PnL | 0.0p | 0.0p |
### 推奨戦略配分
### **重要警告**
- `r2_shadow_demoted_cell`によるブロックはNYでも継続する見込み（セル状態はリアルタイム価格には依存しない構造的抑制）
- GBP_USD VOLATILE状態ではspread_gate発動継続の可能性が高く、scalp_5m_gbpは**NO ACTION推奨**
- XAU系（daytrade_xau / scalp_xau / scalp_eurjpy）は**OFF状態**のためNYも対象外

### 2026-07-17 (Post-NY Report)
| PnL | **+0.0 pips** |
| Session | N | WR% | PnL |
| 本日合計PnL | +0.0 pips |
- `shadow_tracking`とは、シャドウモード（`is_shadow=1`）として記録されたトレードが本番転送をスキップされている状態。
- 本番転送率0%は「OANDAとの接続障害」ではなく、**システム設計上の意図的スキップ**（シャドウ検証フェーズ継続中）と判断。
- ただしNAV/Balance=Noneはデータ取得の軽微な異常を示す。接続はActiveだが残高情報の取得に問題がある可能性。
> **NO ACTION推奨**
- **仮説A（良性）**: フィルタ群が市場のノイズ期間を正確に識別し、リスクを回避している

### 2026-07-20 (Pre-Tokyo Briefing)
**2026-07-19（前日）: トレード数 = 0、PnL = 0、WR = N/A**
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
> **注記**: Cutoff後有効トレード総数 N=3。統計的有意性の閾値（N=10）に遠く及ばず、WR・EVはいずれも「参考値」にすぎない。昇格基準（N≥30 & EV≥1.0）・降格基準（N≥30 & EV<-0.5）ともに適用不能。
- **`hedge_block`が合計237件**（全ブロックの約56%）: 現在オープンポジションがない（Open Trades=0）にもかかわらずhedge_blockが大量発生。これは同一方向への同時シグナルが複数戦略で連続発生し、内部ヘッジ判定が片側に集中する構造を示す。レジームがRANGINGに偏る中、方向性シグナルが均一に出ない状況がブロックを誘発している可能性。
- **`r2_shadow_demoted_cell`が合計114件**（約27%）: USD/CHF、EUR Scalp、GBP 5m Scalp等の複数戦略で降格セルが多数存在。Shadow期間中のパフォーマンス悪化によりライブ実行経路が広範に閉塞されている。
- **`direction_filter`が123件（最大）**: RNB USD/JPYはシグナルは出るが方向フィルターに全件遮断。USD/JPYのRANGING（ATR%ile 71%）かつSMA上昇傾向（+0.00231）のレジームが、RNBの逆張りロジックと構造的に相性不良の可能性。
- **`gbp_asia_flash_crash`が26件**: GBP/JPY（RANGING、ATR%ile 60%）で防衛フィルターが稼働。GBP/JPYのSMAスロープ急傾斜（+0.00470）がフラッシュクラッシュ判定を誘発か。
- `hedge_block`の多発は現レジーム下での構造的現象として**観察継続**。コード変更なし。

### 2026-07-20 (Pre-Tokyo Briefing)
前日（2026-07-19）は全モードで約定ゼロ。Cutoff後累計はN=3、WR=66.7%、PnL=+3.7pと極めて小規模。本日時点でシステムは「信号を出せていない」状態が続いている。
| Strategy | Pair | N | WR% | EV | PnL | 判定ステータス |
- `hedge_block`（計113件：daytrade系合計）が最大勢力。これはエントリーシグナルが出ているにもかかわらず、反対方向のオープンポジション（またはその記録）が存在するために遮断されていることを示す
- `r2_shadow_demoted_cell`（計63件：scalp系合計）は、Shadow検証で低評価となったセルへのシグナルが多数発生していることを示す。シグナル源そのものの品質問題を示唆
- `direction_filter`（41件：rnb_usdjpy）はUSDJPYの方向性判定が頻繁にシグナルと乖離している
- **Daytrade系（DT）**: 大半のペアがRANGING。DT戦略はトレンド/ブレイクアウトを前提とするケースが多く、現状レジームは**中立〜やや不利**。GBPJPYのATR60%・slope+0.47が唯一の好機候補だが、`daytrade_gbpjpy`のblock状況は不明（blockリストに出ていないため非活性か）
- **Scalp系**: RANGING環境はスキャルプに**理論上は有利**（tight rangeでの反転狙い）。しかし`r2_shadow_demoted_cell`が63件と多く、稼働可能なセルが少ない状態
- **RnB_USDJPY**: ATR71%pileは高めで値動きあり。しかし`direction_filter`41件が示すとおり、方向性判定がシグナルと噛み合っていない

### 2026-07-20 (Post-London Report)
| PnL | **0.0 pips / $0.00** |
| 勝率 (WR) | **N/A** |
| PnL | 0 | 0 |
| WR | N/A | N/A |
### 推奨戦略配分
| 累計PnL | **0.0 pips / $0.00** |
**推奨アクション（判断のみ）:**
- NYセッションについては「NO ACTIONが最適」と位置付け、強制エントリー圧力をかけない

### 2026-07-20 (Pre-Tokyo Briefing)
前日（2026-07-19）はトレードゼロ。Cutoff後累積でN=2、PnL=+1.9p、WR=50.0%。システムは稼働中だが、実質的なシグナル生成が極めて限定的な状態が続いている。統計的判断に足るデータ蓄積は現時点で皆無に等しい（N=2）。
| Strategy | Pair | N | WR% | EV | PnL | 判断ステータス |
| 3 | N蓄積が進まずEV/WR評価が不能状態 | 🔴 高 |
- **トレードゼロ**の原因がシグナル未発火なのか、フィルタで全弾ブロックされているのかを区別して監視する。ログ上の`block_counts`とシグナル候補数の比較が鍵。
- **OANDA接続の`None`値**はデータ取得不全を示す可能性がある。本日のNY→東京引継ぎ時点でNAV/Balanceが依然`None`であれば、接続の実効性を疑うべき。
- **shadow_tracking（20件）が全block原因**：これはシステム設計上の動作であり異常ではないが、デモ→本番昇格経路が完全に閉塞している現状の象徴でもある。
- **現在の環境でシグナルが出やすい**: GBP_JPY（TRENDING_UP）> GBP_USD（VOLATILE）
- **シグナルが出にくい/出ても勝ちにくい**: EUR_JPY/EUR_USD（RANGING、ATR低位）

### 2026-07-21 (Pre-Tokyo Briefing)
| 総PnL | ±0.0p |
| 全体WR | N/A |
| Strategy | Pair | N | WR% | EV | PnL | ステータス |
- **hedge_block（96+53+28=177件）が最大ブロック群**。相対ポジションが既にヘッジ構成と判定され、新規エントリーを全面封鎖。月曜日の方向感の不在がヘッジ判定を多発させた可能性が高い。
- **r2_shadow_demoted_cell（30+25+20+5=80件）**がスキャルプ系を壊滅。Shadowセルの降格状態が継続しており、スキャルプ戦略全体のシグナル供給が構造的に枯渇。
- **rnb_usdjpy: direction_filter（92件）** はレンジ相場（USD_JPY RANGING 71%ile）での方向フィルターが意図通りに機能している正常動作。ただし結果としてエントリーゼロ。
- hedge_blockの集中は「今日も継続リスク」として認識。EUR系・AUD_JPY系での新規エントリーは引き続き制限される見込み。
- r2_shadow_demoted_cellの状況が改善しない限り、scalp系は本日もエントリー困難。この状態が何営業日継続しているか追跡要。

### 2026-07-21 (Post-Tokyo Report)
| PnL | 0.0p |
| WR | N/A |
- 東京セッションN=0は「フィルターが機能した結果」であり、「見逃し損失」の証拠がない
- hedge_blockはポジション方向集中リスク回避の正常動作
- order_bar_dedupはエントリー重複防止の正常動作
- r2_shadow_demoted_cellはシグナル品質管理の正常動作
- **DD=100.01%のDD防御0.2x発動中** — この水準でのパラメータ緩和は禁止
| USD_JPY | RANGING | 71% | ATR高水準なのにRANGING — レジーム分類とATRの乖離に注意 |

### 2026-07-21 (Post-London Report)
| PnL | **0.0 pips** |
- GBP/JPYは`TRENDING_UP`（ATR%ile 60%）、GBP/USDは`VOLATILE`（ATR%ile 59%）と、ロンドン時間に適合するレジームが存在していた。
- それにもかかわらず稼働中の全26モードでエントリーゼロという結果は、シグナル生成側かフィルタリング側での**構造的抑制**が機能していたことを示唆する。
| PnL | 0.0p | 0.0p |
| WR | N/A | N/A |
| USD/JPY | RANGING (ATR 71%) | ATR%ile高いがSMAスロープ+0.00194と弱い上昇バイアス。レンジ内でのノイズ増大に注意。 |
### 推奨戦略配分
| 戦略 | ペア候補 | 推奨度 | 理由 |

### 2026-07-21 (Pre-Tokyo Briefing)
| PnL合計 | ±0.0 |
| 全体WR | N/A |
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
> **注意**: N=1は統計的に「データなし」として扱う。EV・WR・PnLのいずれも参考値にすらならない。現時点でCutoff後に判断可能な戦略×ペアの組み合わせは**ゼロ**である。
**レジームサマリー**: 5ペア中3ペアがRANGING。現在の市場構造はDT系（トレンド追随）に対して構造的不利。RANGINGペアでのスプレッドコスト比率が上昇しており、EV圧迫要因となりうる。
| 時間帯（JST） | 内容 | 注意点 |
**レジーム遷移リスク**: USD/JPY（ATR%ile=71%×RANGING）は最も不安定な組み合わせ。高ATRがRANGING内で消費されている状態であり、方向ブレイクアウト時の瞬間的ボラ上昇に注意。
shadow_trackingによる100% SKIPは、「本番に上げられるシグナルが1件も存在しない」ことを意味する。v2.3 roadmapで指摘されている「正の摩擦調整EV

### 2026-07-22 (Pre-Tokyo Briefing)
- PnL合計: **±0** | トレード数: **0** | 全体WR: **N/A**
- 前日は全セッション（東京・ロンドン・NY）を通じて約定ゼロ。システムは稼働しているが、シグナル生成→執行に至るパスが完全に枯渇した状態。
- Cutoff後の累計では `ny_close_reversal × USD_JPY` のN=1（EV=+0.10、PnL=+0.1）のみ記録。**実質的にデータなし**の状態が継続中。
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
> **補足**: N=1は「データなし」扱い（統計的有意性ゼロ）。全戦略において昇格基準（N≥30 & EV≥1.0）・降格基準（N≥30 & EV<-0.5）を判断できる戦略は現在皆無。Sentinel N蓄積進捗は **N=1/30**（29件不足）。
- `r2_shadow_demoted_cell`: Shadow降格セルが多数存在＝シグナル品質の構造的問題。Scalp系は現状のセル構成では執行経路が事実上閉鎖されている。**N蓄積は待機継続で良いが、現状は蓄積すら不可能なことを認識すべき**。
- `hedge_block`: オープンポジションがゼロ（OANDA Open Trades=0）にもかかわらずhedge_blockが発動している点は要注視。ポジション管理ロジックに何らかの残存フラグが疑われる。
- `direction_filter`（87件）: RNB_USDJPYの方向フィルターが機能しすぎており、現状RANGINGレジームのUSDJPYでは事実上シグナルが出ない設計になっている可能性が高い。

### 2026-07-22 (Post-Tokyo Report)
| PnL | 0.0 pips |
- 本日東京のN=0は「戦略の劣化」ではなく「設計通りのブロック作動」と解釈できる
- `r2_shadow_demoted_cell`はshadow評価による自律降格メカニズムであり、正常機能
- `hedge_block`はEUR系リスク集中防御として意図的設計
- Fidelity Cutoff後の累積Nが十分に蓄積していない現状では、ブロック解除の根拠データが存在しない
- **コード変更禁止原則に基づき、判断のみ**: 現時点でパラメータ介入は統計的根拠ゼロ
### 推奨戦略配分
| `daytrade_gbpusd` | GBP/USD | 🟡 要監視 | VOLATILEレジームでspread_guard発動リスク。GBP/JPYと同方向リスク集中に注意 |

### 2026-07-22 (Post-London Report)
| PnL | 0.0 pips |
- **OANDA転送率 0%**（50件中50件がSKIP）
- **Block主因**: `shadow_tracking`（20件100%） — デモシャドー追跡状態が継続中であり、全シグナルがデモ専用として処理されている
- **NAV/Balance = None** — OANDA口座情報が取得不能状態。接続はActive=Trueだが実質的な口座参照が機能していない
| PnL | 0 | 0 |
| WR | N/A | N/A |
### 推奨戦略配分
> **⚠️ NO ACTION推奨**

### 2026-07-22 (Pre-Tokyo Briefing)
**PnL合計: N/A｜トレード数: 0｜全体WR: N/A**
| 戦略 | N | WR | EV | 判定 |
> **注**: 集計テーブルにトレード実績なし。N=0のため統計的評価は不可能。昇格基準（N≥30 & EV≥1.0）・降格基準（N≥30 & EV<-0.5）いずれも適用外。
- **観察継続**: 1日のゼロは異常値ではなく、レジーム起因の自然な不発の可能性が高い。システム介入は不要
- **GBP_JPYに注目**: 唯一のTRENDING_UP（ATR%ile 59%）。本日DT系のシグナル候補が出るとすれば最有力ペア
- **OFFモードの状況確認**: daytrade_xau・scalp_xauが継続的にOFFである理由を要確認（意図的停止か障害か）
| EUR_JPY | RANGING | 33% | +0.00187 | ❌ DT不向き／Scalp狭レンジ注意 |
| 時間（JST） | イベント | 対象ペア | 注意点 |

### 2026-07-23 (Pre-Tokyo Briefing)
**PnL合計: N/A | トレード数: 0 | 全体WR: N/A**
| 戦略 | N | WR | EV | 判定 |
> **備考**: Cutoff後の有効トレードが皆無のため、統計的評価は不可能。N=0は「傾向なし」ではなく「システムが機能していない」ことを示す。昇格基準（N≥30 & EV≥1.0）・降格基準（N≥30 & EV<-0.5）いずれも適用対象外。
- `hedge_block`がTOP4のうち3席を占める（合計253件）。これは単一通貨リスク（EUR/GBP系）への偏ったエクスポージャーに対するシステム自己規制が過剰に機能している状態
- `rnb_usdjpy: direction_filter`の99件は上限カウント（実際はそれ以上の可能性）。RNBモードはUSD/JPY=163.2水準のRANGINGレジームでフィルターが恒常的にOFFになっている可能性が高い
- `r2_shadow_demoted_cell`（scalp系 79件）は過去のシャドウ評価での降格が執行経路を塞いでいる。Shadow降格セルが累積すると、現行レジームでは回復しない構造的詰まりとなる
- **hedge_block多発ペア**（EURGBP, EUR, GBPUSD）の現在ポジション状況を確認→ネットポジションがゼロ（実際Open=0）にもかかわらずhedge_blockが発動しているなら、ポジション追跡ロジックの状態が問題
- **scalp r2_shadow_demoted_cell**：現在のランクで降格セルが何件存在するかを把握し、自然回復を待つか構造的介入が必要かを判断する

### 2026-07-23 (Post-Tokyo Report)
| PnL | 0.0 pips |
| WR | N/A |
- Fidelity Cutoff後のOANDA転送実績 N=50、SENT=0（Live Rate 0%）の状況は継続中。これは `shadow_tracking` による意図的スキップであり、異常ではない
- 東京セッションのゼロトレードは低ATRパーセンタイル（EUR/JPY・EUR/USD・GBP/USD いずれも33–55%台）によるシグナル品質不足と整合的
- `r2_shadow_demoted_cell`（daytrade_1h_usdchf・scalp）によるブロックはShadow Tierの降格判定が正常に機能している証拠であり、介入不要
- DD防御モード（0.2x）が継続中 — この制約下でのパラメータ変更は禁忌
### 推奨戦略配分
**NO ACTION推奨（本番エントリー見送り）**

### 2026-07-23 (Post-London Report)
| セッション内PnL | **0.0 pips** |
| 勝率（WR） | **N/A** |
| PnL | 0.0p | 0.0p |
| WR | N/A | N/A |
- **EUR/GBP主導ペアのボラティリティ低下**：ロンドンフィックス（UTC 16:00）通過済み。EUR_JPY・EUR_USDのATR%ile=33%は既にフラットを示唆。
- **USD関連ペアの注目**：NY時間はUSD_JPY（ATR%ile=67%）が最も動きやすい環境だが、RANGING分類でありトレンド戦略の優位性は限定的。
- **GBP_JPY唯一のTRENDING_UP**：NY序盤の継続性には懐疑的（ロンドン主導トレンドの惰性）。
### 推奨戦略配分

### 2026-07-23 (Pre-Tokyo Briefing)
| PnL合計 | **0.0p** |
| 全体WR | **N/A** |
| 戦略 | N | WR | EV | 判定 |
**Cutoff後の有効トレードはゼロ件**。昇格基準（N≥30 & EV≥1.0）・降格基準（N≥30 & EV<-0.5）いずれの評価も不可能。Sentinel N蓄積進捗：**0/30**（全戦略）。
- トレードゼロが継続する場合、**spread_guardの閾値抵触頻度**を確認すること（コード変更ではなく、現在のスプレッド実測値とガード閾値の乖離幅の把握）
- NAV/Balance=Noneは**OANDA API認証またはアカウント接続の問題**の可能性があり、監視継続
| USD_JPY | RANGING | 67%ile | +0.00217 | ATRは高水準だがRANGING。レンジ内ボラが高く、Scalp誤発シグナルに注意。 |
- 唯一のTRENDING_UPはGBP_JPY（60%ile）。本日最も注目すべきペア。

### 2026-07-24 (Pre-Tokyo Briefing)
| PnL合計 | 0.0p（トレードなし） |
| 全体WR | N/A |
| 戦略 | N | WR | EV | ステータス |
- **トレンド環境**: GBP/JPYのみ（かつブロック中）
- **Scalp有利環境**: なし（全ペアRANGING or ボラ不安定）
- **R&B有利環境**: なし（USD/JPYのレンジが深すぎてdirection_filterに捕捉）
- **結論**: 現在のマーケット環境はシステムの全戦略に対して不利。空振りは「失敗」ではなく「正常なフィルター機能」の可能性が高い。
| 時間（JST） | 内容 | 注意点 |

### 2026-07-24 (Post-Tokyo Report)
| PnL | — |
| WR | — |
### 推奨戦略配分
| `scalp_eur` / `scalp_5m_eur` | EUR/USD, EUR/JPY | **待機推奨** | r2_shadow_demoted_cellブロック多発中。レジームも低ATR。エッジ薄 |
| `rnb_usdjpy` | USD/JPY | **待機推奨** | direction_filterが3件遮断。RANGINGでRnBエッジも不明確 |
- **Live Rate: 0%（50件全件SKIP）**
- Block理由: 全件 `shadow_tracking`（= Sentinel追跡中のデモ専用状態）
- **→ 本番口座への影響ゼロ。DD防御態勢維持中（設計通り）**

### 2026-07-24 (Post-London Report)
| PnL | **0.0 pips** |
| 勝率（WR） | **N/A** |
| PnL | — | — |
| GBP/JPY | TRENDING_UP | 60% | ボラティリティ維持。NY初動でトレンド継続 or 巻き戻しに注意 |
| GBP/USD | RANGING | 60% | 同上。レンジ上限・下限での反転注意 |
### 推奨戦略配分
**⚠️ NO ACTION推奨**
| 累計PnL | **0.0 pips** |

### 2026-07-24 (Pre-Tokyo Briefing)
| PnL合計 | N/A |
| 全体WR | N/A |
| 戦略 | N | WR | EV | 判定 |
- **現時点でできる対処はない**（コード変更禁止、判断のみ）
- 監視継続：shadow_trackingのSKIP数が増加しているか横ばいかを次回ブリーフィングで確認
- OANDA NAV/Balanceの取得失敗が接続品質問題か仕様かを状況観察
| GBP_JPY | TRENDING_UP | 54% | +0.00549 | 218.322 | DT:有利 / Scalp:spread_guard注意 |
- **GBP_JPY のみ TRENDING_UP（ATR%ile 54%）**：5ペア中唯一のトレンド環境。daytradeモードにとって最も適合的だが、現状エントリーがゼロのため恩恵なし。

### 2026-07-27 (Pre-Tokyo Briefing)
前日（2026-07-26）のトレード実績：**ゼロ**。Cutoff後の累積実績も同様に**ゼロトレード**。PnL・WR・EVともに計算対象なし。システムは全モードON（XAU/scalp_eurjpy除く）で稼働中であるが、シグナル→執行のパイプラインが完全に空の状態。
| 戦略 | N | WR | EV | 判定 |
> **注意**：統計的判断の最低ラインN=10すら未達。現時点では戦略優劣の評価は不可能。
- `hedge_block`（計200件超）：ヘッジポジションが長期間オープン保持されているか、もしくはフラグが誤保持されている可能性。ただし現在OANDA Open Trades=0であり、**実ポジションなきhegde_blockの大量発生は異常シグナル**。
- `order_bar_dedup`（計169件）：同一バーでの重複シグナル発生自体は正常なフィルタリングだが、これが支配的ブロック理由になっているのは、エントリー条件の粒度が粗い（同バー内で連続発火）ことを示唆。
- `r2_shadow_demoted_cell`（計122件）：ScalpセルがShadow評価で降格判定を受け、本番への通路が閉じられている。Shadowステージでの累積EV不足が原因と推定。
- `hedge_block`大量発生の原因究明：Open Trades=0とhegde_blockの矛盾を確認すること
- Shadowセルが降格判定されている戦略（scalp系3戦略）の蓄積N数を確認し、昇格見込みを再評価すること

### 2026-07-27 (Pre-Tokyo Briefing)
| PnL合計 | **0.0p** |
| 全体WR | **N/A** |
| 戦略 | N | WR | EV | 判定 |
**Fidelity Cutoff（2026-04-08）以降、有効トレードの蓄積なし。** 昇格基準（N≥30, EV≥1.0）・降格基準（N≥30, EV<-0.5）いずれも評価不可。Sentinel N蓄積進捗：**0/30（全戦略）**。
- **コード変更は行わない**
- Shadow Trackingによるブロックが支配的である事実を記録・注視する。これがシステムの設計通りの動作か、過剰抑制かを蓄積データで判断する素材として位置付ける
- GBP_JPY（TRENDING_UP、ATR55%）のみがトレンド環境にあり、DTモードにとって唯一の潜在的エントリー候補通貨であることを本日注視する
- **USD_JPY**：ATR%ile 66%でRANGINGという不安定状態。ニュース等のトリガーでTRENDING転換の可能性。転換時はDTがエントリー開始するが、初動の偽シグナルリスクに注意

### 2026-07-27 (Post-London Report)
| PnL | **0.0 pips / 0円** |
| 勝率（WR） | **N/A** |
| PnL | 0 | 0 |
| WR | N/A | N/A |
### 推奨戦略配分
**⚠️ NO ACTION推奨**
**NYセッションで注視すべき点（アクション不要だが観察推奨）：**
- GBP/JPYのhedge_block解除タイミング（TRENDING_UP継続なら最初の執行候補）

### 2026-07-27 (Pre-Tokyo Briefing)
- PnL合計: **±0** / トレード数: **0** / WR: **N/A**
- Cutoff後全期間（2026-04-08以降）においてもトレード実績はゼロ
- システムは27モード中25モードが"ON"状態にもかかわらず、一切のシグナル発火なし
| 戦略 | N | WR | EV | 判定 |
- shadow_trackingによるSKIPは**設計通りの動作**（is_shadow=1トレードの本番非転送）であり、異常ではない
- ただし「OFFモードかつ50件転送試行」という事実は要注視 — `scalp_eurjpy`と`scalp_xau`、`daytrade_xau`はOFF状態にもかかわらずshadow試行が発生している可能性
- **本日最優先確認事項**: なぜシグナルが一切発火しないのか（レジーム条件・フィルター閾値の問題か、エントリー条件の厳格化によるものか）
- 5ペア中4ペアがRANGING、かつATR%ileが低〜中位（33〜67%）

### 2026-07-28 (Pre-Tokyo Briefing)
| 前日（2026-07-27）PnL | **データなし（トレード0件）** |
| 全体WR | **N/A** |
| 戦略 | N | WR | EV | 判定 |
- `order_bar_dedup`（計62+38+13=113件）：シグナルは生成されているが「同一バーの重複」として排除されている。エントリー機会は存在した可能性がある
- `r2_shadow_demoted_cell`（計74件）：Shadow降格済みセルへのブロックは正常機能。ただしこれがscalp系の全面的不発の主因
- `direction_filter`（70件）：RnB_USDJPYはUSD/JPY=163.746でRANGING相場中。方向性確信度が低い状態が継続
- 上記はすべてシステム設計通りの正常動作であり、修正不要と判断
- `r2_shadow_demoted_cell`の蓄積は、シャドーN蓄積が不十分なセルが多数残存していることを示す。昇格を待つ段階

### 2026-07-28 (Post-Tokyo Report)
| PnL | — |
| WR | — |
| `scalp_5m_eur:r2_shadow_demoted_cell` | 12 | EUR系スキャルプでシャドウ降格セルに該当。セルEVが閾値未満 |
- **hedge_block（計23件）**: GBP/JPY・AUD/JPY中心。TRENDING系ペアで逆張り/ヘッジシグナルが衝突しやすい市況
- **r2_shadow_demoted_cell（計24件）**: EUR系スキャルプのセルEVが構造的に閾値未満。WS3/外部仮説転進と整合する「EVゼロ問題」の現れ
- **order_bar_dedup（計26件）**: 信号は発生しているが同一バー重複として排除。実質的に信号強度よりサンプリング頻度が問題
- 東京セッションN=0は「システム異常」ではなく「フィルター正常作動」
- `shadow_tracking`による本番完全ブロックはDD防御方針の反映

### 2026-07-28 (Post-London Report)
| PnL | **0.0 pips** |
| 勝率（WR） | **N/A** |
- `direction_filter`（340件）が最大ブロック源。`rnb_usdjpy`はUSD_JPY=RANGING（ATR%ile 67%）にもかかわらず方向性フィルターが全シグナルを棄却 — **レンジ環境でトレンドフォロー系フィルターが機能不全に陥っている可能性**。
- `hedge_block`（daytrade系合計 432件超）は同時間帯のオープンポジション保護として作動。ただし本日はOpen Trades=0のため、**ポジション解消後の再エントリー機会も逸している**可能性がある。
- `r2_shadow_demoted_cell`（scalp系合計 230件）はシャドウ降格セルが依然として大量のシグナルをフィルター中。
| PnL | 0 | 0 |
| WR | N/A | N/A |
### 推奨戦略配分

### 2026-07-28 (Pre-Tokyo Briefing)
**前日（2026-07-27）：トレード 0件 / PnL N/A / WR N/A**
| 戦略 | N | WR | EV | ステータス |
- **主因（Block Counts 上位）**
- `daytrade_eur:hedge_block` … 6件 ← 最大因子
- `rnb_usdjpy:direction_filter` … 4件
- `hedge_block`はヘッジポジション検出による保護的ブロック。EUR系の保有ポジション（またはその認識）がエントリーを阻止している。現在オープン0件との乖離は、**ヘッジ判定ロジックが外部ポジションまたは残留状態を参照している可能性**を示唆。
- `direction_filter`はrnb_usdjpyのトレンド方向フィルターが非該当と判断。USD/JPYはATR%ile=66%（最高位）だが、SMA20 slope=+0.00265のレンジ圏でシグナルが方向感を掴めていない状態。
- `hedge_block`の発生源（何のポジションを参照しているか）を本番ログで確認する優先度が高い

### 2026-07-29 (Pre-Tokyo Briefing)
前日（2026-07-28）および Cutoff後全期間を通じて、**記録上のトレード数はゼロ**。PnL合計・WR・EV の算出対象データが存在しない。システムは全モード稼働中（XAU・scalp_eurjpy を除く）だが、エントリー執行には至っていない状態が継続している。
| 戦略 | N | WR | EV | 判定 |
> Fidelity Cutoff（2026-04-08）以降、執行トレードが存在しないため、統計的評価は不可能。昇格基準（N≥30 & EV≥1.0）・降格基準（N≥30 & EV<-0.5）のいずれも判定対象外。
- `direction_filter`の多発は**レンジ深化のシグナル**として観察を継続。強制的に通過させる性質のものではない
- `r2_shadow_demoted_cell`のブロックが127件に達していることは、**シャドーモードのセルが依然として本番昇格基準を満たしていない**ことを示す。N蓄積を待つしかない段階
- `hedge_block`の集中は複数戦略が同方向バイアスを持とうとしていることの裏返し。通貨リスク集中の潜在リスクとして把握しておく
- **東京セッション（JST 08:00〜15:00）**: USD/JPY・GBP/JPYのATR%ileが高め。アジア時間は`gbp_asia_flash_crash`ブロックが活性化しやすい。GBP系への注視が必要
- **ロンドンフィックス前後（JST 23:00〜00:00）**: WS3 OOS検証で`london_fix_reversal×EUR_USD`がBH-FDR通過済み（ratio 1.43, p=0.0115）。ただし現在はlive実装禁止フェーズであり、観察のみ

### 2026-07-29 (Post-Tokyo Report)
| PnL | — |
| WR | — |
- 東京セッションN=0。統計的根拠皆無。調整トリガーを満たさない
- ブロック理由はいずれも設計通りのフィルター動作であり、誤作動の証拠なし
- `hedge_block`が複数戦略で発動 → 既存ポジション（OANDA Open Trades: 1件）との方向性衝突による正常防御
- DD防御モード継続中（KB記録: DD=100.01%バリア圏、defensiveモード）— 追加リスクテイクの根拠なし
| GBP_JPY | RANGING | 45% | EUR系同様、ロンドン初動でのブレイク試行に注意 |
### 推奨戦略配分

### 2026-07-29 (Post-London Report)
| PnL (pips) | **0.0** |
| PnL | +0.6 pips | 0.0 pips |
| WR | 100%（N=1） | N/A |
### 推奨戦略配分
【NO ACTION推奨】
**全体として**: 現在オープントレード0・hedge_block多発状態ではNYセッションも同様のブロック継続が想定される。**特定のブロック解除シグナルが観測されない限り、NY前半はNO ACTION維持が合理的。**
| 本日累計PnL | **+0.6 pips** |

### 2026-07-29 (Pre-Tokyo Briefing)
前日（2026-07-29）のPnL・トレード数・WRは本APIからは取得不能。ただし、KBの直近文脈（DD=100.01%、defensive mode継続中）と照合すると、**システムは引き続き「ドローダウン防御0.2x縮退モード」下にある**と推定される。新高値更新なし。
| 戦略 | N（Cutoff後） | WR | EV | 判定 |
| 摩擦調整EV | **全セル負**（T2 exit-repair FAIL確定） |
→ N=93は「判断可能」水準だが、EV構造は依然として負。**昇格候補ゼロの状態が継続している可能性が高い。**
| 3 | **DD=100.01%バリア突破後の防御継続** | 新高値なし。defensive mode（0.2x）が続いており、EV回収の機会が構造的に制限されている |
- **新規ポジションに対する積極的判断は保留** — データが見えない状態での追加リスクテイクは禁忌
- **外部仮説スクリーン（KB: external-hypothesis-scan-2026-07-13の後続フェーズ）の進捗確認を優先**
- APIが復旧次第、Cutoff後のN・EV・block_countsを即時確認する

### 2026-07-30 (Pre-Tokyo Briefing)
前日（2026-07-29）の約定は **1件のみ**。`price_shock_rev_aud_jpy_h1_long` / AUD_JPY BUY → WIN / PnL **+0.6pip**。
システム全体WR = 100%（N=1）、PnL合計 = **+0.6pip**。
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
- hedge_blockの多発は相場構造（後述のRANGING環境）に起因する可能性が高く、今日も継続する蓋然性が高い。同条件での約定は引き続き困難と見込む
- r2_shadow_demoted_cellブロックについては、対象セルが「本当に死んでいるか」の定期レビューが必要だが、N蓄積がないため現時点では静観が妥当
- **デイトレード戦略**：トレンドフォロー型の要素を持つため、RANGING環境では誤シグナルが増加しhedge_blockが多発する正のフィードバックループが形成されている
- **スキャルプ戦略**：spread_guardが機能しやすい環境だが、r2_shadow_demoted_cellブロックにより供給自体が枯渇
- **rnb_usdjpy**：direction_filterで85件ブロック。USD_JPYのATR%ile=67%は高いが、SMAスロープが明確なトレンドを示さず、方向判定が定まらない状態

### 2026-07-30 (Post-Tokyo Report)
| PnL | 0 pips |
| WR | N/A |
- **hedge_block が東京セッション最大の約定阻止要因（42件/TOP15合計=89件の47%）**。GBP_USD（17件）・EUR_JPY（13件）・GBP_JPY（12件）の3ペアに集中しており、これらペアでヘッジ方向のシグナルが逆張り的に連発したことを示す。
- **direction_filter（rnb_usdjpy 16件）** は、USD_JPY ATR%ile=67%・SMA Slope+0.00248 というRANGING-Upper Bandの環境下でRnBロジックが方向を絞り込めていない状態を反映。
- **r2_shadow_demoted_cell（16件）** はshadow tracking中のセルが本番昇格未完のまま信号を出し続けていることを示す。
- 本日セッションN=0 のため統計的判断の基礎なし。
- block_countsはすべてシステム設計内の保護ロジック（hedge_block、direction_filter、shadow demote）が正常作動した結果であり、誤作動ではない。
- OANDA転送率0%は「約定ゼロ」の結果であって、Bridge自体の異常ではない（shadow_tracking 19件 + agg_kelly=-0.343<0 の1件のみ）。

### 2026-07-30 (Post-London Report)
| WR | 0.0% |
| PnL | **-30.1 pips** |
本日累計データ（N=1, WR=0.0%, PnL=-30.1）がそのままロンドンセッション値と一致していることから、**東京セッションはゼロトレード**だったと判断される。
| WR | — | 0.0% |
| PnL | 0 | -30.1 |
### 推奨戦略配分
**NO ACTION推奨（条件付き）**
| 累計WR | 0.0% |

### 2026-07-30 (Pre-Tokyo Briefing)
前日（2026-07-29）は**トレード1件、PnL +0.6pip、WR 100%**。
`price_shock_rev_aud_jpy_h1_long / AUD_JPY / BUY / WIN`。Cutoff後累計はN=2、PnL=-29.5pip（前日の`vix_carry_unwind`による-30.1pipの損失が残存）。実質的にはほぼ無活動日。
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
- 前々日（または当日初動）の`vix_carry_unwind / USD_JPY`が-30.1pipを記録。
- これが`daily_loss_limit(-30.1pip <= -20.0pip)`トリガーとなり、**3件のBridgeブロックが連鎖発生**。
- 本日の注視点：daily_loss_limitはリセットされたか（UTC 00:00リセット想定）。**本日は新日付での制限下でトレード可能なはず**。
- Cutoff後N=2は28日以上経過していると仮定すると、**1日あたり平均0.07件**。
- 全27モードが稼働しているにもかかわらずシグナルがほぼ発火していない。

### 2026-07-31 (Pre-Tokyo Briefing)
- PnL: **−30.1 pip** | トレード数: **1件** | 全体WR: **0.0%**
- 唯一の執行 `vix_carry_unwind / USD_JPY SELL` がSL_HIT（−30.1 pip）。前日を通じてシステムは実質的に「休眠状態」であり、活発な戦略稼働は確認されない。
| Strategy | Pair | N | WR% | EV | PnL |
> **統計的判断**: N=2はデータなし（N<10は「データなし」扱い）。個別EVは参考値に過ぎず、昇格・降格の判断材料にはならない。
- USD_JPY SELL方向でSL_HIT（−30.1pip）
- USD_JPYのATR%ile=83%（VOLATILE上位）の環境での逆張り系エントリーと推定
- VIX急変に反応したキャリー巻き戻し戦略が、その後の相場反転に飲まれた可能性
- この単発損失がデイリーロスリミット（−20.0pip）を超過 → OANDAブロック理由 `daily_loss_limit(-30.1pip<=-20.0pip)` が2件計上

### 2026-07-31 (Post-Tokyo Report)
| PnL | 0.0 pips |
| WR | — |
- **VOLATILE レジーム（USD/JPY ATR%ile 83%、GBP/JPY 74%）** 下でスキャルプ系がフィルターを通過しなかった可能性が高い
- spread_guard が高ボラティリティ時間帯に多く発動していた可能性（block_reasons に spread 系は今回未計上だが、Scalp閾値30%・DT閾値20%との競合が推定される）
### 推奨戦略配分
| 戦略 | ペア | 推奨 | 根拠 |
**NO ACTION推奨（積極エントリー不推奨）**
- OANDA Live Rate = **0%**（50件中0件送信）。agg_kelly = −0.367 < 0 でKellyゲートが閉まっており、システム自体が現在のリスク環境を否定的に評価している

### 2026-07-31 (Post-London Report)
| PnL | **0.0 pips** |
| 勝率（WR） | **N/A** |
- EUR/JPY ATR%ile **71%**・GBP/JPY **74%**・USD/JPY **83%** —— いずれも VOLATILE レジームで、DTおよびScalp戦略が動作すべき環境水準にあったにもかかわらず、一件も約定しなかった。
- **シグナル生成の不発** がフィルター手前で起きているか、スプレッドガード等で全件 SKIP された可能性が高い。
| PnL | 0.0 pips | 0.0 pips |
| WR | N/A | N/A |
### 推奨戦略配分
| **GBP_USD系** | — | RANGING判定のためDT系は見送り推奨 |

### 2026-07-31 (Pre-Tokyo Briefing)
| 前日PnL合計 | **-30.1 pips** |
| 全体WR | **0.0%** |
| Strategy | Pair | N | WR% | EV | PnL |
> **統計的判断**: 全戦略 N<10 → **「データなし」扱い**。EV・WR の数値は現時点で意思決定根拠として使用不可。N=30 まで最低27件不足。
| 1 | `vix_carry_unwind` がSL_HIT → EV=-30.1（N=1） | データ不足で戦略評価不能 |
- `vix_carry_unwind` は N=1 であるため、今日追加されるシグナルを蓄積する段階。評価保留。
- OANDA NAV/Balance が `None` の原因は接続または権限の問題と推定される。ライブ昇格判断に影響するため、状態確認を優先。
- エントリー数の少なさは VOLATILE レジームでのフィルター強化効果と見ることもできる。現段階では観察継続。

### 2026-08-03 (Pre-Tokyo Briefing)
- **前日（2026-08-02）トレード数: 0件** — 全セッション（東京・ロンドン・NY）通じてトレードなし
- **PnL: ±0 / WR: N/A** — エントリー機会自体が発生しなかった、または全ブロックされた
- Cutoff後累積（全期間）: **N=3、WR=33.3%、EV=−74.5（加重平均）、PnL=−152.7**
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
> **統計的評価不能**: N=3（全戦略合計）はサンプルサイズ基準（N≥10=「傾向」）を大幅に下回る。EV・WRの数値は参考値に過ぎず、判断材料としては使用不可。
- 前日の東京・ロンドン・NY 全セッションでエントリーゼロ
- Block Countsの構造が主因：**rnb_usdjpy:direction_filter（107件）**が最大ブロック要因 — これ単体で「USD_JPYが方向性フィルターを連続否決している」ことを示す。USD_JPYはATR%ile **93%（最高水準）**でVOLATILEレジームにあり、rnb（Range-and-Break）戦略が想定するレンジ環境と根本的に乖離している可能性が高い
- **daytrade:hedge_block（76件）** — ヘッジポジション検知によるブロックが2番目。オープントレードなし（OANDA Open Trades=0）にもかかわらずhedge_blockが多発している点は構造的に注目すべき

### 2026-08-03 (Pre-Tokyo Briefing)
前日は全セッション（東京・ロンドン・NY）を通じてトレード実行数 **0件**。PnL = ¥0、WR = N/A。Cutoff後の累積有効データは **N=2 / WR=0.0% / EV=−76.65p/t（平均）/ PnL=−153.3p** という極めて乏しい状態が継続。
| Strategy | Pair | N | WR% | EV (p/t) | PnL | 判定 |
- `order_bar_dedup`の多発 → VOLATILE相場でシグナル密度が上昇しているが、これは**意図的フィルターの正常作動**。対処不要。
- `direction_filter`（rnb_usdjpy×20） → USD_JPYのATR%ile=93%は極端なVOLATILE状態。レンジバウンド戦略が全遮断されるのは**設計通りの正常挙動**。
- `r2_shadow_demoted_cell` → 降格セルの自動除外機能が稼働。Scalp系の供給ラインが細っている点は**構造的懸念**として継続監視。
- **Daytrade系**: VOLATILE環境は本来DT有利のはずだが、`order_bar_dedup`が密集シグナルを大量排除している。実質的に「見ているが入れない」状態。
- **Scalp系**: スプレッド拡大（`spread_gate` 6件）＋`r2_shadow_demoted_cell`の二重抑制。VOLATILE相場でのScalp系は摩擦コストが上昇しており、フィルター強化は妥当。
- **RnB（rnb_usdjpy）**: ATR93%でdirection_filterが完全作動。VOLATILE相場が解消するまで実質的に機能停止。

### 2026-08-03 (Post-London Report)
| PnL | **0.0 pips** |
| PnL | 0 | 0 |
### 推奨戦略配分
**NYセッション：NO ACTION推奨**
| PnL | 0 | 0 | **0 pips** |
**OANDA転送率0%（50/50スキップ）＋agg_kelly=-0.469**という組み合わせは、Kelly基準がシステム全体に対して現在のセル群のEVを「負」と評価していることを意味する。これは防御の成功ではなく、**エッジを持つエントリー候補が存在しないことの確認**である。
**推奨アクション（判断のみ）**: NYセッションはNO ACTION維持。ただし「今日のゼロ」をKBの月次M1進捗として正式記録し、USD_JPYのATR%ile低下（93%→60%台以下）を条件に次のrnb_usdjpy稼働評価タイミングを設定することが優先度高い。agg_kelly負の状態でのエントリー解禁は現時点では支持しない。

### 2026-08-03 (Pre-Tokyo Briefing)
| 前日 PnL | ±0 |
| 前日 WR | N/A |
前日（2026-08-02）はシステム全体でトレードゼロ。Cutoff後の累計実績はN=2、PnL=−153.3pipsと極めて薄い。実質的に**稼働しているが取引が発生しない状態**が続いている。
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
> **統計的ステータス**: 両戦略ともN=1。「データなし」扱い。EVの絶対値に惑わされてはならない。昇格基準（N≥30 & EV≥1.0）・降格基準（N≥30 & EV<−0.5）のいずれにも到達していない。
- daytrade系15モード・scalp系5モード・rnb_usdjpy、すべてエントリー条件未成立
- Block Countsにある `daytrade_eur:hedge_block (9件)` および `rnb_usdjpy:direction_filter (7件)` が、潜在的エントリー候補を遮断した主因
- **Scalp系に最も不利**（spread_guardが頻繁に発動する帯域）

### 2026-08-04 (Pre-Tokyo Briefing)
前日（2026-08-03）はトレード**ゼロ**。Cutoff後累積でもN=2（うちどちらも判断不可水準）に留まり、PnL合計は**−153.3**。全モードが稼働中にもかかわらず、実質的にシステムはトレードを生成していない状態が継続している。
| Strategy | Pair | N | WR% | EV | PnL |
> **統計的判断**: N=2はいずれも「データなし」扱い。EVの数値は参考値に過ぎず、昇格・降格いずれの判断も不可。Sentinel N=30達成まで残り**28件**。
- 27モードが`ON`状態だが実行数は0。Block Countsを見ると**hedge_block・direction_filter・r2_shadow_demoted_cell・order_bar_dedup**が主因として計合計**310件以上**の阻止が発生している。システムはシグナルを生成しているが、多重フィルターが出口を塞いでいる構造。
- `hedge_block`（合計95件: EUR70 + EURJPY25）→ 現在のUSD_JPY急落局面（SMA20 Slope −0.00256）でEUR/GBP系が逆方向に引っ張られ、ヘッジロック状態が長期化していると推定
- `r2_shadow_demoted_cell`（合計104件）→ シャドウトラッキングが広範な戦略セルを降格済み状態に維持。これがN蓄積の最大障壁
- `direction_filter`（69件）→ RnB_USDJPYがVOLATILEレジーム（ATR%ile 91%）でほぼ機能停止
- 上記は**コード変更なし**の前提で静観継続。VOLATILE相場が落ち着き、direction_filterとhedge_blockの解除条件が揃うのを待つ。

### 2026-08-04 (Post-Tokyo Report)
| PnL | 0.0p |
| 勝率（WR） | N/A |
- **Fidelity Cutoff後の蓄積N=0**（本日セッション）— 統計的判断の材料が存在しない
- OANDA転送率 **0%（50/50がSKIP）** — 全トレードがshadow_trackingによりデモ専用。Live実績なし
- DD防御モード（**DD=100.01%バリア突破後 held**）発動中 — このフェーズでのパラメータ調整は混線要因
- 現状の問題はパラメータではなくhedge_blockによる執行機会そのものの消失。これはパラメータ変更で解決する性質のものではない
| USD/JPY | VOLATILE | **91%** | −0.00256（強下降） | 円高圧力強い。157.195は節目圏。ブレイク注意 |
| GBP/USD | VOLATILE | **67%** | +0.00153（上昇） | USD安バイアス。EUR/GBPとの逆相関に注意 |

### 2026-08-04 (Post-London Report)
| PnL | **0 pips / 0円** |
| WR | **N/A** |
| PnL | 0 | 0 |
| WR | N/A | N/A |
### 推奨戦略配分
**現時点での推奨: NO ACTION（静観）推奨**
- **daytrade_gbpusd / daytrade_gbpjpy** — 現在のhedge_blockはポジション0の状態でも発動しているため、NY序盤にブロック理由が変化するか否かを監視。263件という件数は過剰な可能性がある。
| 累計PnL | **0 pips** |

### 2026-08-04 (Pre-Tokyo Briefing)
| 前日 PnL | **-** |
| 全体 WR | **-** |
前日は完全なトレードゼロ日。システムは稼働中だが、シグナル発火なし。唯一の有効トレード記録（Cutoff後全期間）は `price_shock_rev_aud_jpy_h1_long / AUD_JPY` の N=1 / PnL=−123.2p のみ。
| Strategy | Pair | N | WR% | EV (p/t) | PnL |
> N<10 につき「データなし」扱い。EV −123.20 は一点観測のノイズであり、戦略の期待値を語れる水準にない。
- **課題A**: レジーム状況（後述）と照合し、現在 VOLATILE 環境が daytrade_1h 系フィルターと整合しているか確認。特に USD_JPY / EUR_JPY のATR91%ile がスプレッドガード（DT=20%閾値）に抵触していないか確認を優先する
- **課題B**: NAV=None のままでは Kelly計算の信頼性も損なわれる。OANDA接続の実態把握を急ぐ（コード変更なし、状況把握のみ）
- **課題C**: `shadow_tracking` 19件が SKIP の主因。シャドウ期間中のトレードは本番未転送が構造仕様であることは既知。現在は "shadow が明けるまで本番実績が積み上がらない" ループに入っている

### 2026-08-05 (Pre-Tokyo Briefing)
前日（2026-08-04）は**トレード完全ゼロ**。PnL = ¥0、N = 0、WR = N/A。
Cutoff後の有効データは `price_shock_rev_aud_jpy_h1_long / AUD_JPY` の N=1（EV=-123.20）のみ、実質的に統計的判断が不可能な水準。システムはONだが、全27モードで発注には至っていない状態が継続。
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
> **全戦略共通**: N=1のみ。統計的判断の閾値（N≥10）に到達していない。本レポート内のEV=-123.20は「1回の結果」に過ぎず、期待値として解釈してはならない。
- **hedge_block多発環境の継続**を前提に、発注期待値を低めに設定する
- **GBP系ペアはフラッシュクラッシュフィルターが引き続き高感度で作動**することを想定
- 発注があった場合、N蓄積の貴重な1件として記録の完全性を確認する
- **Daytrade系（JPY絡み）**: ATR%ile 84-91%は本来DT系が得意とする値幅環境だが、円高トレンドとの組み合わせでhedge_blockが多発。「値幅はあるが方向が偏っている」状態。

### 2026-08-05 (Post-Tokyo Report)
| PnL | — |
| WR | — |
| 本日累計 | N=1 / WR 100% / +29.0 pips |
東京セッション中の約定はゼロ。本日累計の1件（+29.0p, 100%WR）はセッション外（UTC 00:00以前）のもの。
本日唯一のトレード（+29.0pips）はセッション外記録であり属性詳細は本レポートスコープ外。参考として「正のPnL」を達成した事実のみ記録。
- 東京N=0で統計的判断材料が皆無
- Cutoff後の累計データも蓄積途上（N=30基準に対し本日N=1）
- 現在 **DD=100.01%（100%バリア突破後 held）** → DD防御0.2xモード継続中

### 2026-08-05 (Post-London Report)
| WR | — |
| PnL (pips) | **0.0** |
| WR | 100% (N=1) | — |
| PnL | +29.0 pips | 0.0 pips |
- 本日累計 N=1 / +29.0 pips は**東京早朝の単発ヒット**によるもの
- ロンドンでの完全沈黙は東京比でトレード機会が0に収縮
- ATR91%ile（EUR/JPY・USD/JPY）はロンドン開幕時点で既にピーク水準に達しており、spread拡大によるguard発動が最も有力な沈黙要因
### 推奨戦略配分

### 2026-08-05 (Pre-Tokyo Briefing)
2026-08-04（前日）は**トレードゼロ**。PnL合計 ¥0、トレード数 0、WR 算出不可。
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
> ⚠️ **N=2はシステム全体として「データなし」に等しい。** 両戦略ともN<10のため統計的判断は不能。EV・WRは参考値として記録するに留める。
- Total=50、SENT=0、SKIP=50 → Live Rate **0%**
- 50件全てがshadow_trackingまたはagg_kellyによりブロック → 本番口座への影響ゼロ、NAV変動なし（NAV=¥277,782）
- エントリー条件が成立しない原因がレジーム側（Volatile偏重）にあるか、シグナル生成側にあるかを、本日のBlock Counts推移で判別する。現時点のBlock TOP3はすべて件数が少ない（最大4件）ため、hedge_blockや direction_filter による抑制も限定的。問題は「そもそもシグナルまで到達していない」可能性が高い。
| EUR_USD | RANGING | 52% | +0.00224 | 1.15534 | DayTrade_eurには低ボラ帯。scalp_eur系はspreadがEVを圧迫しやすい |
- USD_JPY ATR91%ile は過熱水準。**急速なATR収縮（RANGING化）**が起きると、現在のVOLATILE前提のシグナルがミスマッチを起こす可能性。

### 2026-08-06 (Pre-Tokyo Briefing)
前日（2026-08-05）は **1トレード、WR 100%、PnL +29.0p** にて終了。
ただし Cutoff後累計では **N=2 / WR=50% / EV=−47.1p**（1件目の AUD_JPY −123.2pが大きく足を引く）と、累計EV は依然マイナス圏。
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
> **統計的判断**: 全戦略 N<10 → いずれも「データなし」扱い。EV・WRは現時点で判断根拠なし。
- `rnb_usdjpy:direction_filter` (81件) が最大ブロック要因 → USD_JPYが VOLATILE 91%ile の中でフィルタが連続発動している可能性。本日も同一レジームが継続する見込みのため、**rnb_usdjpyのエントリー頻度は引き続き低い前提で計画**。
- `r2_shadow_demoted_cell` 系（scalp合計146件）→ shadowセルがデモシグナルを押さえている構造。**スキャルプ系の実質的な供給源はほぼ枯渇状態**であることを認識した上で監視。
- `order_bar_dedup` (daytrade計50件) → 同バーでの重複が多発。レジームが不規則な短期動意を繰り返している兆候として観察継続。
- **Daytrade系（JPYクロス）**: VOLATILE環境はATRが広いため方向性フィルタが頻発ヒット。エントリー条件が厳しくなりブロック増加は合理的。逆に抜けた場合のペイオフは大きくなる可能性。

### 2026-08-06 (Post-Tokyo Report)
| PnL | — |
| WR | — |
- **`hedge_block` (最多・3戦略一致):** EUR_JPY/GBP_JPY/USD_JPY がいずれもATR%ile **84–91%（VOLATILE）** かつSMA20 Slope がマイナス（円高方向へのトレンド）。ヘッジポジションが既存または潜在的に検出され、新規エントリーを全ブロック。JPY系ペアが高ボラ環境で一方向性圧力を受けている状況下で設計通り機能している。
- **`order_bar_dedup` × GBP_JPY (17件):** 同バー内の重複注文抑制。GBP_JPYのATR%ile 84%という高ボラ環境で短時間内に複数シグナルが重複発生しているとみられる。
- **`direction_filter` × rnb_usdjpy (17件):** USD_JPY がVOLATILE + Slope −0.00608（本日最大の円高傾斜）。レンジブレイク戦略のディレクション条件と相反する方向性が継続判定されたと解釈。
- **`r2_shadow_demoted_cell` × scalp系 (16件):** Shadow demotion済みセルへの到達が継続。これはv6.3以降の構造的フィルタが機能している正常動作であり、エラーではない。
- **`agg_kelly<0` (−0.426):** Kelly推定がマイナスでOANDA Bridgeがブロック。現在のEV構造がliveエントリーに耐えない水準。
- ブロックは全て既存ロジックの**設計通りの動作**（hedge_block、dedup、direction_filter）。

### 2026-08-07 (Pre-Tokyo Briefing)
前日（2026-08-06）のPnL合計・トレード数・WRを算出するソースデータがいずれも欠落しています。「トレード0件」と「APIタイムアウト/接続障害」の区別もこの時点では確認できません。
| 戦略 | N | WR | EV | 判定 |
- clean live 30d: N=93 / -245.0p / payoff 0.274
- 摩擦調整EV: 全セルで負（最良TPでも -2.96p/t）
- 昇格基準（N≥30 & EV≥1.0）達成戦略: **なし（直近確認時点）**
**課題B: 摩擦調整EV の構造的負値（継続）**
KB確定事項: exit-repair verdict ❌ FAIL（2026-07-08）。WS3 stage-2 barrier/EV も FAIL（2026-07-10）。外部仮説スクリーンフェーズ（2026-07-13〜）へ移行済みですが、現時点で正のEVセルは確認されていません。
0.2xロット制限下では、たとえ正のEVシグナルが出ても収益貢献が構造的に制限されます。

### 2026-08-07 (Pre-Tokyo Briefing)
前日（2026-08-06）はトレードゼロ。Cutoff後の累積では N=2、PnL=-94.2、WR=50.0%。システムは稼働中だが実質的に執行停止状態が継続している。
| Strategy | Pair | N | WR% | EV | PnL |
> **統計的判断**: N=2は「データなし」水準（統計的閾値N=10未満）。EV・WRともに参考値にすら達していない。両戦略とも判断保留。
- **direction_filter(78)**：USD_JPY VOLATILEレジーム（ATR%ile 93%）下でrnb戦略の方向性フィルターが強く機能している。この抑制はレジーム整合的であり、**介入不要**と判断。
- **hedge_block(76)**：JPY全般の強い方向性バイアス（USD_JPY/EUR_JPY/GBP_JPY全てVOLATILE×下落スロープ）がヘッジブロックを多発させている。**現状維持が適切**。
- **r2_shadow_demoted_cell(計100超)**：scalp系の実行可能セルが枯渇状態。Shadow蓄積が進むまで待機が必要。**N=30到達まで強制的にトレードは増えない構造**。
- **gbp_asia_flash_crash(54)**：GBP_JPY ATR%ile 86%という高ボラ環境への正常応答。**保護機能として肯定的に評価**。
- **USD_JPY ATR%ile=93%**：これ以上のVOLATILE深化は限定的だが、158円台サポート割れならレジーム転換（Trending化）の可能性。rnb戦略の方向性フィルターがさらに強化される方向。

### 2026-08-07 (Post-Tokyo Report)
| PnL | — |
| 勝率 (WR) | — |
- 東京セッションN=0のため統計的判断根拠なし
- OANDA転送率0%（50件中SENT=0）は全トレードがシャドートラッキング中であることを示す — これは**意図通りの挙動**（DD防御フェーズ + shadow_tracking=18）
- `agg_kelly=-0.426<0` ×2のOANDAブロックは Kelly基準によるリスク抑制が正常動作していることを示す
- 現在DD=100.01%（100%バリア突破後 held / no new high）のDefensive Mode継続中 — パラメータ変更でリスクを動かすタイミングではない
### 推奨戦略配分
**→ NO ACTION推奨**

### 2026-08-07 (Post-London Report)
| PnL | **0.0 pips / 0円** |
| 勝率 (WR) | **N/A** |
| PnL | 0 | 0 |
| WR | N/A | N/A |
**OANDA転送率0%の背景**: 全50件がデモ専用（SKIP）。agg_Kelly負値（−0.426）はポートフォリオ全体の期待値がマイナス評価である状態を示しており、これ自体は**リスクゲートの正常作動**。ただし、この状態が恒常化しているならば昇格基準（EV≥1.0）を満たすセルが存在しない状況が継続していることを意味する。
### NYセッション予測と推奨配分
- JPY系はNY入りでUSD主導の動きが加速する可能性。ATRパーセンタイル93%はすでに極限域にあり、**平均回帰（ATR縮小）リスクが高い**。
- EUR/GBP系はRANGINGが継続する可能性が高く、ブレイクアウト戦略には不向き。

### 2026-08-07 (Post-NY Report)
| PnL | **+0.0p** |
### セッション別PnL比較
| Session | N | WR% | PnL |
- **最良セッション**: なし（全セッション同値）
- **最悪セッション**: なし（同上）
- **稼働モード数**: 25モード ON、2モード OFF（daytrade_xau、scalp_xau、scalp_eurjpy）
- ヘッジブロックが継続中かどうかをblock_counts冒頭で確認
- hedge_block件数が前日比で減少していればレジーム転換のシグナル

### 2026-08-10 (Pre-Tokyo Briefing)
前日（2026-08-09）はトレード**ゼロ**。PnL: ±0、WR: N/A。
| Strategy | Pair | N | WR% | EV | PnL |
> **統計的判断**: N=1は「データなし」扱い。WR100%・EV+29.00は参考値にすら値しない。
> 昇格基準（N≥30 & EV≥1.0）まで残り**29件**。降格判断も不可能な段階。
- `direction_filter`(66件)は最多。現在のJPY系VOLATILE環境で方向が定まらず、フィルタが方向性を全拒絶している可能性が高い
- `r2_shadow_demoted_cell`(計96件: scalp56+scalp_eur26+scalp_5m14)はシャドウ降格が実質的にscalp系を無効化している
- `regime_squeeze_mr`(計32件: gbpjpy22+eurjpy10)はVOLATILE判定が逆説的にMR系をスクイーズしている
- Block構造はコードではなく**現在のレジーム環境が主因**と判断。本日も同様のブロック継続を想定し、稼働状況を受容モードで監視する

### 2026-08-10 (Post-Tokyo Report)
UTC 00:00–06:00の範囲でクローズされたトレードはゼロ。本日累計は参考値として N=1 / WR=100% / +63.7pips が存在するが、東京セッション時間帯外のものと判断される。システムは全主要モード稼働中（daytrade_xau / scalp_xau / scalp_eurjpy はOFF）、ポジション保有なし。
- 東京セッションN=0のため統計的判断材料がない
- 本日累計N=1は「データなし」扱い（N<10基準）
- ブロック機構は設計通り作動しており、異常ではない
- DD防御モード（DD=100.01%、defensive 0.2x）継続中であり、追加リスクテイクの状況にない
| USD_JPY | VOLATILE | 91% | ATR91%ile、SMA-0.007で最も強いJPY買いシグナル。スプレッド拡大に注意 |
| EUR_USD | RANGING | 59% | レンジ中位。+SMAスロープでUSD弱含み。Scalpには適度な環境だがEV確認必要 |
**JPY系3ペアが一斉VOLATILE（ATR 84–91%ile）** は通貨リスク集中の観点で要注意。同方向JPY買いポジションが重なった場合の相関リスクが高い。

### 2026-08-10 (Post-London Report)
| 勝率（WR） | 100.0% |
| セッションPnL | **+63.7 pips** |
| 平均EV/trade | +63.70 |
| 戦略 | ペア | PnL | 方向 | 決済 |
- **モード稼働数**: 27モード中 25モードがONであったにもかかわらず、成立トレードは1件のみ
- `daytrade_xau`・`scalp_xau`・`scalp_eurjpy` は**OFF状態**で機会寄与なし
- EUR_JPY（ATR 91%）・GBP_JPY（ATR 84%）のVOLATILEペアでデイトレードモードが稼働中にもかかわらず**無発火** — シグナル条件未成立または後述のブロック要因によるフィルタリングの可能性
| WR | — | 100% | — |

### 2026-08-10 (Post-NY Report)
| PnL | **0.0 pips** |
| WR | **— (N=0)** |
### セッションPnL比較
| Session | N | WR% | PnL (pips) | 評価 |
- **本日合計**: N=1、WR=100%、PnL=+63.7 pips
- **最良セッション**: Londonセッション（唯一のトレード、1勝0敗）
- **最悪セッション**: 定義上「不活性」であるTokyo・NYは損失ゼロだが、機会コスト的には劣後
**評価**: 全50件がSKIPされており、本番OANDA口座への発注はゼロ。`shadow_tracking`（17件）は意図的なシャドー追跡モードであり異常ではない。`agg_kelly<0`（3件）はポートフォリオ全体のEVが負の局面でのゲート遮断であり、**リスク管理として正常機能している**。NAV/Balanceが`None`であることはOANDA接続の読み取りに課題を示唆するが、発注ゼロのため実害なし。

### 2026-08-11 (Pre-Tokyo Briefing)
前日（2026-08-10）は **1トレード、PnL +63.7p、WR 100%**。
Cutoff後累計はN=2、PnL +92.7pと極めて小規模。全モードでOANDA転送率は **0%（50件全SKIP）**。
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
> **注意**: N=2はデータとして成立しない（統計的有意性ゼロ）。EV +46.35は参考値に過ぎず、昇格判断には使用不可。N=30到達まで判断保留が原則。
| EUR_USD | RANGING | 60% | +0.00287 | daytrade_1h_eur、scalp_eur向けには比較的安定。ただしRANGINGでは方向性シグナルの精度低下に注意 |
- **hedge_block（計94件、daytrade_eur=40/daytrade=34/daytrade_1h_nzdjpy=20）**: 最大の機会損失源。既存ポジションとのヘッジ判定によるブロック。ポジションが閉じるまで継続的に発生する構造的ブロック。
- **order_bar_dedup（計66件）**: 同一バー内での重複シグナルを除外。正常動作だが、シグナル過多の可能性も示唆。
- **r2_shadow_demoted_cell（計60件）**: scalp/scalp_5m_gbp/scalp_eurで多発。これらのセルがシャドウデモート済みであり、本番昇格条件未達のためスキップされている。

### 2026-08-11 (Post-Tokyo Report)
| セッション PnL | 0.0 pips |
| 勝率 (WR) | N/A |
- セッション N=0 のため統計的根拠が一切存在しない
- 調整判断に必要な最低 N=10 すら未達
- VOLATILE レジーム（EUR/JPY・USD/JPY・GBP/JPY 全て ATR%ile 86–90%）における無トレードは、spread_guard・ボラティリティフィルタが設計通り機能している可能性が高い
- DD防御モード（DD=100.01%、defensive mode 継続中）下では保守的不作為を肯定的に評価すべき局面
### 推奨戦略配分
| daytrade_eurjpy / gbpjpy | EUR/JPY・GBP/JPY | **回避推奨** | ATR%ile 86–90%の VOLATILE 環境 + JPY 下落トレンド継続。DT spread_guard 20% 閾値での遮断が頻発する可能性 |

### 2026-08-11 (Post-London Report)
| PnL | **0 pips / 0円** |
| 勝率（WR） | **計測不能（N=0）** |
| PnL | 0 | 0 |
### 推奨戦略配分
> **⚠️ NO ACTION推奨（条件付き）**
- EUR_USD RANGING確認後 → `scalp_eur`（RANGING×中ATRは最も相性良）
- JPY系VOLATILE収束確認後 → `daytrade_eurjpy`再試行（ただしhege_block解除確認必須）
| 累計PnL | **0 pips** |

### 2026-08-11 (Post-NY Report)
| PnL | **+0.0p** |
### セッション別PnL比較
| Session | N | WR% | PnL |
- **合計PnL**: +0.0p
- **合計トレード数**: 0
- **WR**: 算出不能
### 推奨アクション判断
> **NO ACTION推奨**

### 2026-08-12 (Pre-Tokyo Briefing)
前日（2026-08-11）は**トレードゼロ**。PnL = ¥0、N = 0、WR = N/A。
Cutoff後全期間で有効トレードは `usdjpy_carry_dip_accumulator / USD_JPY` の **N=2のみ**（EV=+46.35、PnL=+92.7）。
| Strategy | Pair | N | WR% | EV | PnL | 評価 |
> **注記**: N=2は統計的に「データなし」水準。WR 100%・EV+46.35 はいずれも解釈不可能。昇格基準（N≥30 & EV≥1.0）まで残り**28件**が必要。
- `r2_shadow_demoted_cell`の累積件数がスキャルプ系全戦略で高水準であることを認識し、**シャドウセルの回復状況を継続モニタリング**すること
- `gbp_asia_flash_crash`ブロック（80件）はGBP/JPYの特殊ガードが継続発動中。**現在のGBP/JPY（ATR86%ile・RANGING）においてこのガードが適切に機能しているか**を確認することを推奨
- `direction_filter`主導のブロックはレジームと整合しており、現時点では**フィルタが意図通り機能している**と判断できる
- 全5ペアが**RANGING判定**（USD/JPYのみVOLATILE）。しかしATR%ileが90%に達するペアが複数あり、「RANGING×高ATR」という矛盾した環境が生じている。これはトレンドの方向性が定まらないまま値動きの振れ幅だけが大きい**混乱レジーム**を示す。

### 2026-08-12 (Post-Tokyo Report)
| PnL | — |
| WR | — |
- `scalp系`: `r2_shadow_demoted_cell`によるフィルタリングが正常作動（13+12+6+3+2=36件）
- `daytrade系`: `hedge_block`が複数ペアで発動（EUR_JPY/USD/GBP_USDで計58件）
- 東京セッションN=0、判断に必要な統計的根拠が存在しない
- `hedge_block`・`r2_shadow_demoted_cell`はリスク管理機能として**正常作動**しており、誤動作ではない
- OANDA転送率0%はshadow_tracking（19件）が全件を説明しており、システム異常ではない
- DD防御モード（DD=100.01%、0.2x防御）継続中であり、パラメータ介入の優先度は低

### 2026-08-12 (Post-London Report)
| 勝率 (WR) | **0.0%** |
| PnL | **−13.3 pips** |
| 戦略 | ペア | 方向 | PnL | 理由 |
| WR | — | 0.0% |
| PnL | 0 | −13.3 pips |
東京セッションのデータは本集計に含まれていないため詳細比較は不可だが、本日累計がN=1、PnL=−13.3pipsと一致していることから、**東京セッションのトレードはゼロ**であったと判断できる。ロンドン入りでようやく1件が発火したが、それ自体が損失で終了。
- **USD_JPY（VOLATILE 90%ile）** はNY時間に入り米経済指標（CPI/PPI系の余波 or 指標なし日でも短期流動性増加）でボラ継続が予想される。SMA Slopeの下向き（−0.00585）はNY初動でも圧力が残存する可能性。
- **EUR/GBP系（RANGING 62–90%ile）** はロンドン・フィックスを通過済みのため、NY時間は方向感が薄れやすい。レンジ・スキャルプには一定の機会があるが、ATR高水準でスプレッド比が悪化しやすい点に注意。

### 2026-08-12 (Post-NY Report)
| WR | — |
| PnL | **±0.0 pips** |
### セッション別PnL比較
| Session | N | WR% | PnL (pips) | 評価 |
- **合計PnL**: -13.3 pips（N=1、WR=0.0%）
- **最良セッション**: Tokyo / NY（±0、トレードなし）
- **最悪セッション**: London（唯一の執行で-13.3pips喪失）
- **特記**: Londonセッションの1件のみが本日全ての損益を決定。戦略・ペアの詳細はAPIに記録なし（セッション内トレード詳細=空）

### 2026-08-13 (Pre-Tokyo Briefing)
| 前日PnL | **−13.3p** |
| 全体WR | **0.0%** (1/1 LOSS) |
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
- Cutoff後の有効データは**N=2のみ**。「昇格基準（N≥30 & EV≥1.0）」「降格基準（N≥30 & EV<−0.5）」いずれにも到達不能。
- 前日1件で累計N=2に到達した点は記録するが、EV±25は極めて不安定な推定値であり参照価値はない。
- `hedge_block`がdaytrade系を566件ブロック。現在のレジーム（RANGING多数 + USD_JPY VOLATILE）において、ヘッジ判定が過敏に反応している可能性が高い
- `r2_shadow_demoted_cell`による294件ブロックは、scalp系がシャドウ降格セルのまま復帰していないことを示す。これは意図的な品質フィルタとして機能しているが、同時にスループットをほぼ消滅させている
- `gbp_asia_flash_crash`：GBP_JPYのATR90%ile（高ボラ）が継続中のため、このフィルタは正当に発動していると判断

### 2026-08-13 (Post-Tokyo Report)
| PnL | 0.0p |
| WR | N/A |
- `hedge_block`が最大因子（全体ブロックの最多カテゴリ）。GBP/EUR/AUD系DT戦略でヘッジ状態が継続しており、新規エントリーを全面封鎖。
- `order_bar_dedup`はGBPUSD・GBPJPYで頻発——同一バーに複数シグナルが集中する価格帯への到達が繰り返されているが、重複排除で吸収されている。
- `r2_shadow_demoted_cell`の計22件は、scalp_5m系がシャドーR2評価でセル降格を受けていることを示す。ライブ昇格前の品質フィルターとして機能中。
- `rnb_usdjpy`の`direction_filter`16件は、USD/JPY VOLATILE + SMA20 Slope -0.00520（下降方向）のレジーム下でlong方向シグナルが連続ブロックされている可能性が高い。
| GBP_USD | RANGING | 43% | 中ATR×RANGINGは相対的に安定。ただし東京でhedge_block+dedupが発生しており引き続き注意 |
- EUR_JPY・GBP_JPY・USD_JPYのATR90%ile水準は、ロンドン初動（UTC 07:00–08:00）でスプレッドが一時拡大する局面と重なりやすい。spread_guardブロックが追加発生する可能性がある。

### 2026-08-13 (Post-London Report)
| PnL | **0 pips / 0円** |
| PnL | 0 | 0 |
| WR | N/A | N/A |
- **USD_JPY VOLATILE継続見込み**：ATR90%ile + SMA slope急落（−0.00520）は構造的な円高圧力の継続を示唆。NYオープン時のドル売り加速リスクあり。
- **EUR/GBP系**：RANGINGが継続する可能性が高い。ロンドンフィックス（UTC 16:00）通過済みのため、一時的な方向性の発生は期待薄。
- **ATRの方向**：USD_JPY・EUR_JPY・GBP_JPYの高ATRは、NYセッション序盤に継続する可能性あり。ただしRANGINGラベルの中での高ATRは「往復」の危険性も内包。
### 推奨戦略配分
**⚠️ NO ACTION推奨（条件付き）**

### 2026-08-13 (Post-NY Report)
| PnL | **+0.0p** |
| Session | N | WR% | PnL |
- **本日合計PnL**: +0.0
- **本日合計トレード数**: 0
- **本日合計WR**: 測定不能
- **最良セッション**: なし（全セッションノートレード）
- **最悪セッション**: なし（同上）
> **NO ACTION推奨**

### 2026-08-14 (Pre-Tokyo Briefing)
**2026-08-13（前日）：トレードゼロ**。PnL = ¥0、N = 0、WR = N/A。全27モードが稼働中にもかかわらず、一件の約定も発生しなかった。Cutoff後累積では N=2 / WR=50% / EV=+25.20p（USD_JPY carry戦略のみ）と、統計的判断に足るサンプルは皆無の状態が続いている。
| Strategy | Pair | N | WR% | EV (p/t) | PnL | 判定 |
> **昇格基準（N≥30 & EV≥1.0）達成戦略：なし**
> **降格基準（N≥30 & EV<-0.5）該当戦略：なし**
- **USD/JPYが159.5付近を維持 → VOLATILE継続** → 本日もゼロトレード日の公算大
- **USD/JPY 160超え回復 or 158割れ安定化 → VOLATILE→RANGING遷移** → hedge_block解除、carry戦略ゲート再開の可能性
- **r2 demotedセル問題は短期解消の見込み薄**（157件 / 継続的ブロック）
- 現在：N=2 / 目標：N=30

### 2026-08-14 (Post-Tokyo Report)
| PnL | 0 pips |
- 本日のブロックはシステム設計通りの動作（シャドウセル降格・ヘッジブロック・dedupは意図的フィルター）
- コード変更禁止原則に加え、現データからパラメータ調整を正当化するN≥30の統計的根拠が存在しない
- EUR/JPY・GBP/JPYともにヘッジポジション由来のブロックであり、手動介入より次シグナルを待つのが合理的
### 推奨戦略配分
- daytrade_1h_eurusd / daytrade_eurusd
- scalp_5m_gbp（GBP/USD）
- daytrade_1h_gbpusd

### 2026-08-14 (Post-London Report)
| 勝率（WR） | 100.0% |
| PnL | +0.8 pips |
| 戦略 | ペア | 方向 | PnL | 決済理由 |
**成功要因**: USD_JPY がVOLATILE/ATR90%ile環境にもかかわらず、carry dip accumulator がディップ押し目を捕捉し、設計通りSL/TPで決済完了。スプレッド0.8に対してネットPnL+0.8は摩擦調整後ほぼゼロ利益圏であり、「勝利」と呼ぶには過剰評価に注意。
東京セッションの記録が本データセットに存在しないため、直接比較は不可。ただし本日累計N=1・PnL=+0.8pipsという数値が東京+ロンドン全体を表している点から推定：
| WR変化 | 比較不能（東京データなし） |
| PnL変化 | 東京N=0 → ロンドンN=1(+0.8p)で初トレード発生 |
### 推奨戦略配分

### 2026-08-14 (Post-NY Report)
| PnL | **+0.0 pips** |
### セッション別PnL比較
| Session | N | WR% | PnL (pips) | 評価 |
- 本日は**ロンドンセッションの1トレード（+0.8p, 勝利）のみ**で実質休眠日
- 3セッション中2セッションでゼロ稼働。N=1は統計的に意味を持たない
- **最良セッション**: London（唯一稼働、+0.8p）
- **最悪セッション**: Tokyo & NY（両者 N=0、PnL=0.0）— ただし「悪い」というより「存在しない」
- `shadow_tracking (19件)`: システムが本番送信前の観察フェーズにあるシグナルを遮断。N蓄積前の安全機構が正常作動

### 2026-08-17 (Pre-Tokyo Briefing)
**2026-08-16（前日）: トレードゼロ。PnL = ±0、執行件数 = 0。**
| Strategy | Pair | N | WR% | EV | PnL |
- 統計的判断不能（N<10基準）。EV+9.85は表面上は優秀だが、N=4では偶発的偏差の範囲内。
- 昇格基準（N≥30 & EV≥1.0）まで残り **26件**。
- 他の全戦略：Cutoff後の有効トレード = **0件**（Shadow除外後）。
- **hedge_block支配**: daytrade_audjpy(30)・scalp_5m_gbp(28)・daytrade(10)・scalp_5m(6) — 複数ペアで同方向ヘッジ条件が長時間継続し、新規エントリーを完全封殺した模様。
- **r2_shadow_demoted_cell**: scalp(15)・scalp_eur(12)・scalp_5m(5)・daytrade_gbpusd(3) — シャドウ降格セルによる抑制が積み上がっており、Scalpファミリーのシグナル通過率を恒常的に低下させている。
- **rnb_usdjpy:direction_filter(29)**: RnBが方向フィルタで29回連続ブロックされている。USD/JPYのトレンドが方向定義と合致していない状態（後述レジーム参照）。

### 2026-08-17 (Post-Tokyo Report)
| WR | **0.0%**（0勝1敗） |
| PnL | **−11.8 pips** |
| 戦略 | ペア | 方向 | 結果 | PnL | 主因 |
- USD/JPYは現在ATR%ile **90%（20日比較）** かつSMA20 Slope **−0.00463**（下向きトレンド）
- レジーム分類は「RANGING」だが、ATR%ile=90%はボラティリティが高い水準にある矛盾状態（高ボラ+横ばい＝ノイズ相場）
- "dip_accumulator"（押し目買い蓄積）系戦略にとって、下向きSlopeかつ高ATR環境は逆方向フォローが発生しやすく、SL_HIT率が構造的に高まる条件
- スプレッド=0.8（USD/JPYとして許容範囲内）であり、スプレッド問題ではない
- N=1は統計的根拠として完全に不十分（判断閾値はN≥30）

### 2026-08-17 (Post-London Report)
| **WR** | 0.0% |
| **セッション PnL** | **−11.6 pips** |
| 戦略 | ペア | 方向 | PnL | 失敗要因 |
| WR | 0.0% | 0.0% |
| PnL | −11.8 pips（推定） | −11.6 pips |
> 本日累計: N=2, WR=0.0%, PnL=−23.4 pips
- **USD/JPY ATR%ile 90%、Slope −0.0046**: NYオープンにかけて対USD強化の地合いが継続する可能性。JPY安トレンドは継続しているが、直近はSMA20を下抜け中。
- **全ペアRANGING**: NYセッション序盤はロンドンフィックス後の調整で方向感が出にくい。米国経済指標（本日予定があれば）が発表されない限り、レジーム転換は期待しにくい。

### 2026-08-17 (Post-NY Report)
| WR | — |
| PnL | +0.0 pips |
### セッション別PnL比較
| Session | N | WR% | PnL (pips) | 評価 |
| 合計PnL | -23.4 pips |
| WR | 0.0%（2戦0勝） |
**補足**: N=2は統計的判断の土台にならない（N<10=「データなし」基準）。本日の損失は構造的問題の証拠とはならず、1日単位のノイズとして扱う。ただし2戦2敗・WR 0%・-23.4pipsという数値は記録に留める。
| 本日WR 0%（2戦2敗） | 🟡 中 | N=2なのでノイズだが、戦略名・ペア詳細が不明。翌朝ログで確認推奨 |

### 2026-08-18 (Pre-Tokyo Briefing)
前日（2026-08-17）のトレード数は **2件**、PnL合計 **−23.4p**、WR **0.0%**。
| Strategy | Pair | N | WR% | EV | PnL |
| Trade | Dir | PnL | Spread | Outcome |
- **Spread自体は0.8pips**と許容範囲内（DT閾値20%未達）であり、摩擦問題ではない
- 問題の本質は **エントリー方向（BUY）とUSD_JPYレジームの不整合**
- USD_JPYは現在RANGING・ATR%ile=90%・SMA20 Slope=**−0.00459**（明確な下降バイアス）
- キャリー系「押し目買い」戦略が、下降モメンタムが強い局面で買いを繰り返した
- EV = −8.97（N=4）は「傾向として深刻」だが、統計的確定判断はN≥30まで保留

### 2026-08-18 (Post-Tokyo Report)
| PnL | 0.0p |
| WR | N/A |
- ブロックは設計通りのリスクゲート（r2_shadow_demoted / hedge_block）が機能した結果であり、システムの誤作動ではない
- OANDA転送率 **0%**（50件中50件 SKIP）は shadow_tracking が全件適用中のためで、デモ→本番昇格未実施の現状と整合
- `agg_kelly=-0.364<0` による1件ブロックは Kelly基準が負EVを正しく検知している証拠
- 現在 **DD=100.01%（バリア突破後 held、DD防御0.2x モード）** のため、新規パラメータ投入によるリスク増加は許容不可
### 推奨戦略配分
**NO ACTION推奨**

### 2026-08-18 (Post-London Report)
| PnL | **0 pips / 0円** |
| 勝率 (WR) | **N/A** |
- **OANDA Block理由 TOP1**: `shadow_tracking` 20件（全ブロック100%）
- **OANDA転送率**: SENT=0 / SKIP=50 → **ライブ転送率 0%**
- システムはシグナルを一定数生成しているが、全件がshadow_trackingフェーズに留まり本番執行に到達していない
| PnL | 0 | 0 |
| WR | N/A | N/A |
- **EUR/JPY・USD/JPY・GBP/JPY**: ATR%ile 86–90%と高水準 → ボラティリティは存在するが方向性なし（SMA20 Slope全てマイナス）

### 2026-08-18 (Post-NY Report)
| PnL | **+0.0 pips** |
### セッション別PnL比較
| Session | N | WR% | PnL |
- **最も成績が良かったセッション**: 評価不能（全セッションN=0）
- **最も成績が悪かったセッション**: 評価不能（同上）
- **最もアクティブだった戦略**: なし
- **`shadow_tracking`が唯一の遮断理由（20/20件 = 100%）**
- これはシステムが意図的にシャドウモード（is_shadow=1）として処理しているトレードであり、OANDAブリッジが設計通りにフィルタリングしていることを示す

### 2026-08-19 (Pre-Tokyo Briefing)
| PnL合計 | ±0（取引なし） |
| 全体WR | N/A |
| Strategy | Pair | N | WR% | EV | PnL | 評価 |
- **N=4** はFidelity基準上「データなし」に相当。統計的判断は保留。
- Cutoff後の有効戦略サンプルはこの1セルのみ。昇格基準（N≥30 & EV≥1.0）・降格基準（N≥30 & EV<−0.5）のいずれの判断域にも達していない。
- **Sentinel蓄積進捗：N=4/30（残26件で判断域到達）**
- `r2_shadow_demoted_cell` ブロックの多寡は現行セルのシャドウ評価結果に依存。**降格済みセルのN蓄積を継続し、再昇格条件の充足を待つ**以外の選択肢はない（コード変更禁止原則の範囲内）。
- `rnb_usdjpy:direction_filter` の27件ブロックは、USD/JPY が強い下落バイアス下にある間は継続すると見込む。レジーム転換まで許容範囲内と判断。

### 2026-08-19 (Post-Tokyo Report)
| WR | 0.0% (0/1) |
| PnL | **−11.7 pips** |
| 戦略 | ペア | 方向 | PnL | 失敗要因 |
- スプレッド0.8pipは許容範囲内であり、執行品質自体に問題はない
- **SMA20 Slope = −0.00478（全ペア中最大の下降傾き）**の環境下でBUY（carry dip accumulation）は逆風であり、レジーム適合性に疑問が残る
- N=1は統計的根拠なし。単一SL_HITで調整判断を下すことは統計的に不適切
- ただし**レジーム観察事項**として記録：USD/JPYはATR90%ile×下降SMAであり、carry dip accumulator（BUY bias）との相性が構造的に問われる局面。N≥10蓄積後に再評価要
| GBP_JPY | RANGING | **84%** | 同上。GBP絡みはロンドンopen特有の急動意注意 |

### 2026-08-19 (Post-London Report)
| セッション内PnL | **0.0 pips** |
| セッション内WR | **N/A** |
- **agg_kelly=-0.371<0（3件ブロック）**: アグリゲートKellyがマイナスに振れており、システムが自律的に新規ポジション開放を抑制。DD防御モード（DD=100.01%）が継続中であることと整合する。
- **shadow_tracking（17件スキップ）**: デモ専用フロー。本番転送率0%は構造的設定であり異常ではないが、学習素材としてのトレード自体もゼロであった点が問題。
| PnL | -11.7 pips（本日唯一） | 0.0 pips |
| WR | 0.0%（1/1負け） | N/A |
- EUR/USD・GBP/USDはATR%ile 41%と**低ボラティリティ**。NYオープン（UTC 13:00以降）でUSD統計イベントがあれば一時的ATR拡張の可能性あり。
- JPYクロス系（EUR/JPY 90%、GBP/JPY 84%、USD/JPY 90%）は引き続き高ATR——方向性が定まらない中での高ボラは**Scalp系にはノイズ**、DT系にはフォルスブレイクアウトリスクを高める。

### 2026-08-19 (Post-NY Report)
| WR | — |
| PnL | ±0.0 pips |
### セッション別PnL比較
| Session | N | WR% | PnL (pips) | 評価 |
| 本日合計 PnL | **−11.7 pips** |
| WR | **0.0%** |
> **注記**: 本日の全活動は東京セッションの1トレードに集約。ロンドン・NYは完全に沈黙。「N=1 / WR=0%」は統計的判断不可領域（N<10）のため、戦略評価には使用不可。
- `shadow_tracking` 18件は設計通りの除外。デモ段階のシャドウトレードがLive送信をブロックするのは仕様通り。

### 2026-08-20 (Pre-Tokyo Briefing)
| PnL合計（前日） | **-11.7 pips** |
| 全体WR | **0.0%** |
| Strategy | Pair | N | WR% | EV | PnL |
> **注意**: N=4 は統計的判断不可領域（データなし扱い）。EV=-8.57は現時点では参考値に留める。ただし4/4で全損失のうち3件・BUY方向のSL_HIT連続は、TRENDING_DOWN（後述）環境との方向性ミスマッチを示唆する。
- `usdjpy_carry_dip_accumulator`のBUY方向シグナルはTRENDING_DOWN継続中は**信頼度低**と認識して監視
- Kelly負の状態が継続する限り、OANDAへのSENTは構造的に0件が続く（設計通り）
- シグナルの枯渇が「フィルタ過剰」か「正当なno-trade」かは本日の相場展開で判断
- **JPY全般が高ATR・下降トレンド**: JPYクロスのロング戦略は全てレジーム逆風

### 2026-08-20 (Post-Tokyo Report)
| PnL | 0.0 pips |
| WR | N/A |
| GBP_JPY | RANGING | 79% | 同上。EUR_JPY相関に注意 |
### 推奨戦略配分
**NO ACTION推奨 — ただし監視強化**
| 推奨度 | 戦略 | 理由 |
| 🟡 監視 | daytrade_eurjpy / daytrade_gbpjpy | 高ATR RANGINGでシグナル出現可能性あり、hedge_block頻度に注意 |
**NO ACTION推奨の根拠:**

### 2026-08-20 (Post-London Report)
| 勝率（WR） | 50.0% |
| セッション PnL | **+29.1 pips** |
| 平均 EV/トレード | +7.28 pips |
| 戦略 | ペア | 方向 | PnL | スプレッド |
**成功要因**：USD_JPY が ATR%ile=86%・TRENDING_DOWN レジームにおいて、キャリー押し目戦略の両エントリーが OANDA_SL_TP による規律ある決済で完結し、スプレッド摩擦（0.8）が十分に低く実EV を損なわなかった。
※ただし2件のうち1件は PnL=+0.7 pip と最低限の勝利であり、実質的な稼ぎは1件目（+38.2）に依存している点に留意。
| 戦略 | ペア | 方向 | PnL | 敗因 |
本日データには東京セッション（UTC 00:00–07:00）分の別集計が提供されていないため、**直接比較は不能**。本日累計 N=4・PnL=+29.1 がそのままロンドン分と一致していることから、**本日は東京セッションでのトレード発生なし**と判断される。

### 2026-08-20 (Post-NY Report)
| WR | — |
| PnL (pips) | +0.0 |
### セッション別PnL比較
| Session | N | WR% | PnL (pips) | 評価 |
- **本日合計**: N=4 / WR 50.0% / +29.1 pips
- **最良セッション**: Londonセッション（全4トレード集中）
- **最悪セッション**: 東京・NYは同率最下位（無活動）
- **最良戦略**: セッション内詳細データ欠如のため特定不可。ただしロンドン時間帯の4トレード中2勝2敗、pips合計+29.1は**ペイオフ比が勝ち側に非対称（≒プラス摩擦構造）** であることを示唆

### 2026-08-21 (Pre-Tokyo Briefing)
前日（2026-08-20）総PnL：**+29.1p**、トレード数：**4件**、WR：**50.0%**
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
> **注記**: 全体集計 N=8 / WR=37.5% / PnL=-5.2p（Cutoff後全期間）
> 両戦略ともN<10。「データなし」ゾーン。EVの数値は参考値として見るが判断の根拠にはしない。
| 前日2件 | 両方LOSS / EV -4.90 / PnL -9.8p |
- **問題の本質**：`horizon`決済はエントリー方向に価格が動かず時間切れになったケース。価格ショックリバーサル戦略がEUR_GBPで機能していない可能性が高いが、**N=2では判断不能**。
- **今日の対処**：観察継続のみ。N=10到達前に降格判断を下すのは早計。ただし連続`horizon`決済は「シグナル質の低下」のプロキシとして警戒継続。
- Cutoff後N=8という極端なスロー蓄積は、shadow_trackingによるスキップ（本日ブリッジ確認: 19件スキップ）と、direction_filter/hedge_blockによる大量ブロックが主因。システムは動いているが「弾が出ていない」状態。

### 2026-08-21 (Post-Tokyo Report)
| PnL | — |
| WR | — |
- 今日のゼロトレードは「エントリー抑制が設計通り機能した結果」であり、誤作動ではない
- USD_JPY TRENDING_DOWN（ATR%ile 81%）下での `rnb_usdjpy:direction_filter` 多発は適切なリスク回避
- OANDA転送率0%（SENT=0/50）は全50件がshadow_tracking(15件) or agg_kelly<0(5件)でフィルターされており、Kelly gate が正常にリスク遮断中
- **agg_kelly=−0.331<0** のブロックが5件 — 現在のポートフォリオEV構造がマイナスと判定されており、昇格条件（N≥30 & EV≥1.0）を満たすセルが存在しない状態を反映
- コード変更は本分析の対象外であり、データが「何もするな」と告げている
| ペア | 現在レジーム | ロンドン移行予測 | 注意点 |

### 2026-08-21 (Post-London Report)
| 勝率 (WR) | 0.0% |
| PnL | +0.0 pips |
| セッション寄与 | BREAKEVEN |
**該当なし。** 唯一のトレード（`price_shock_rev_eur_gbp_h1_long`）はBREAKEVENで、勝利とは計上できない。
| 戦略 | ペア | PnL | 失敗要因 |
| price_shock_rev_eur_gbp_h1_long | EUR_GBP | +0.0 | horizon終了によるクローズ——価格インパルスが持続せずBREAKEVEN着地 |
**補足**: GBP_USDレジームがRANGING（ATR%ile 34%）、GBP_JPYもRANGING（67%）という低ATR環境下では、price_shock系戦略のトリガー条件を満たしても値動きが続かない構造的不利があった。スプレッド1.3pipsはEUR_GBPとして許容範囲内だが、EVに寄与できるほどの方向性が出なかった。
| WR | — | 0.0% |

### 2026-08-21 (Post-NY Report)
| WR | — |
| PnL (pips) | **+0.0** |
### セッション別PnL比較
| Session | N | WR% | PnL (pips) | 評価 |
- **PnL**: +0.0 pips（実質フラット）
- **トレード数**: 1（ロンドンのみ、PnL=0.0で詳細不明）
- **最も成績が良かったセッション**: ロンドン（唯一のトレード発生セッション、ただしEV評価不能）
- **最も成績が悪かったセッション**: 東京・NY（完全無取引、機会損失）

### 2026-08-24 (Pre-Tokyo Briefing)
**2026-08-23（前日）: トレードゼロ。PnL = 0、約定件数 = 0、WR = N/A。**
| Strategy | Pair | N | WR% | EV | PnL |
**全体評価: N=9 / WR=33.3% / 合計PnL=-5.2**
- `rnb_usdjpy:direction_filter` **334件** — 最大の単一ブロック要因。USD_JPYがTRENDING_DOWN（ATR%ile 74%）という高ボラ下降トレンド局面で、RnBストラテジーの方向フィルターが全シグナルを弾き続けている。フィルターが機能している状態であり、異常ではないが、**このペアでの機会が構造的に消滅している**ことを示す。
- `scalp:r2_shadow_demoted_cell` **74件** / `scalp_5m_gbp:r2_shadow_demoted_cell` **42件** / `scalp_eur:r2_shadow_demoted_cell` **40件** — Scalp系の主要ブロック。R2シャドウセルの降格が複数スキャルパー戦略の供給ライン全体を絞っている。これはシステムの設計通りの自己保護だが、**シグナル供給がほぼ枯渇している**ことを意味する。
- `daytrade_eur:order_bar_dedup` **52件** — 重複バーフィルターが多発。EUR系デイトレードでシグナルが生成→即フィルタリングされるサイクルが繰り返されている。
- `daytrade_eurgbp:score_gate` **28件** — スコアが閾値未満のシグナルが多数発生も全て不採用。
- rnb_usdjpyについては、USD_JPYのTRENDING_DOWN継続中は約定ゼロが続く可能性を前提として許容する（フィルターが仕事をしている）。

### 2026-08-24 (Post-Tokyo Report)
| PnL | 0.0p |
| WR | N/A |
- 東京セッションはN=0のため統計的判断の根拠なし
- ブロック構造（shadow_demoted_cell / direction_filter）は設計通りの動作であり、誤作動ではない
- OANDA転送率4%（2/50 SENT）はshadow_tracking 18件 + agg_kelly負値ブロック2件が主因であり、現行リスクゲートが正常機能している証左
- コード不変原則の下、判断変更の根拠となるN≥30データが東京時間帯には存在しない
| GBP_USD | RANGING | ATR%ile 28%（最低）、静穏継続 | ロンドン入りでの急変に注意 |
### 推奨戦略配分

### 2026-08-24 (Post-London Report)
| PnL | **0.0 pips** |
| 勝率（WR） | **N/A** |
| WR | N/A | N/A |
| PnL | 0 | 0 |
### 推奨戦略配分
**⚠️ NO ACTION推奨**
| 累計PnL | **0.0 pips** |
### 最重要シグナル：「稼働25モード・トレードゼロ」は**システム機能不全の警告**

### 2026-08-24 (Post-NY Report)
| PnL | **+0.0** |
### セッション別PnL比較
| Session | N | WR% | PnL |
- **最も成績が良かったセッション**: 該当なし（全セッションゼロ）
- **最も成績が悪かったセッション**: 該当なし（同上）
- **最も成績が良かった戦略**: 該当なし
**本日の引き継ぎ判断**: **NO ACTION推奨** — コード変更なし。現在のゼロトレードはシステムの各フィルターが設計通り機能した結果である可能性が高く、外部介入の根拠となるN≥30の統計データが存在しない。
累積50件中2件のみSENT。これはシャドートラッキングの設計仕様とはいえ、月次目標M1（符号転換）すら達成困難な配管状態。KBで確認されている通り、「正の摩擦調整EVセルの不在」が根本であり、Live転送率を上げる前にEV構造の修復が必要という順序は正しい。現状は正しい順序で詰まっている。

### 2026-08-25 (Pre-Tokyo Briefing)
**2026-08-24（月）はトレードゼロ**。前日NYクローズまで全セッション無約定。現時点でCutoff後の累積N=9、PnL=**−5.2p**、全体WR=**33.3%**。システムは稼働中だが実質的に不活性状態が続いている。
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
- **JST 15:00-17:00（ロンドンオープン前後）**: EUR/USD・GBP/USDがTRENDING_UP構造のため、ロンドンセッション開始でブレイクアウト的動きが出る可能性。ATR%ile低水準から上昇する場合はscalp条件に近づく
- **JST 21:00-23:00（NY前半）**: USD/JPY TRENDING_DOWNのモメンタムが継続するかどうかの判断ポイント。74%ile ATRが更に上昇する場合はrnb_usdjpyの全面封鎖継続
- **GBP系フラッシュクラッシュリスク**: gbp_asia_flash_crashが70件発動中という事実は今朝のアジアセッションでも要注意
- USD/JPYが159付近で下値支持を見せる場合、TRENDING_DOWNからRANGINGへの遷移可能性 → direction_filterのブロック件数が急減するシグナルとして監視
- EUR/USD 1.1664でTRENDING_UP維持中 — ここから押し目形成でRANGING転換した場合、scalp系の条件変化に注意
本番Bridgeで記録された `agg_kelly=-0.336<0` は、現在の戦略ポートフォリオ全体の摩擦調整EVが**構造的に負**であることを示している。これは個別戦略の成績の問題ではなく、システムが「勝てる状態にない」という集約判断をKelly計算が正直に出力している。N=9という小サンプルのため確定はできないが、KB蓄積知見の「正の摩擦調整EVセルの不在」という診断と完全に整合している。

### 2026-08-25 (Post-Tokyo Report)
| PnL | — |
| WR | — |
- トレードゼロは「ブロックが機能した証拠」であり、誤作動ではない
- `r2_shadow_demoted_cell`による861件ブロックはScalpセル品質管理の正常動作
- `gbp_asia_flash_crash`415件は東京時間GBP保護として設計通り
- DD防御モード（DD=100.01%）継続中 — この状況での積極的調整判断はリスク管理上不適切
### ロンドン戦略配分推奨
**NO ACTION推奨**

### 2026-08-25 (Post-London Report)
| PnL | **0.0 pips / 0円** |
| 勝率 (WR) | **N/A** |
| PnL | 0 | 0 |
| WR | N/A | N/A |
### 推奨戦略配分
**NO ACTION推奨**
- 現在のOANDA Live転送率が**4%**（50件中2件）と極端に低く、そのうち`shadow_tracking`（18件）と`agg_kelly=-0.336<0`（2件）がブロック主因
- `agg_kelly<0`はシステムが自己判定でリスクオフを選択している状態であり、これを上書きする判断材料がセッションデータから得られない

### 2026-08-25 (Post-NY Report)
| PnL | +0.0 p |
### セッション別PnL比較
| Session | N | WR% | PnL |
- **合計PnL**: ±0.0 p
- **合計トレード数**: 0
- **WR**: 計測不能
- **最良セッション**: 該当なし（全セッション同率ゼロ）
- **最悪セッション**: 該当なし（同上）

### 2026-08-26 (Pre-Tokyo Briefing)
前日全セッション（東京・ロンドン・NY）を通じてトレード実行なし。PnL = ±0、N = 0。システムは稼働中（26モード中24がON）だが、信号生成またはフィルター通過率が実質的にゼロとなった一日。
> **注意**: 全期間累積N=9。いずれもN<30のため「傾向参照」段階。判断不可水準。
| Strategy | Pair | N | WR% | EV | PnL | 統計的ステータス |
**全体合算**: N=9、WR=33.3%、PnL=−5.2p
- `usdjpy_carry_dip_accumulator` はEV+0.77と唯一ポジティブだが、N=6では統計的ノイズの範囲内
- `price_shock_rev_eur_gbp_h1_long` はN=3、EV=−3.27と深刻なマイナスだが、サンプル数が極小であり評価保留が妥当
- **昇格基準（N≥30 & EV≥1.0）到達まで：最低+24件が必要**
- 全26モード稼働中にもかかわらず約定ゼロ

### 2026-08-26 (Post-Tokyo Report)
| PnL | — |
| WR | — |
- 東京セッション N=0 のため統計的判断の基盤なし
- OANDA転送率 4%（50件中2件のみLIVE送信）は低水準に見えるが、`shadow_tracking`（19件）が主因であり、Shadowフェーズが意図通り機能している証拠
- `agg_kelly=-0.336<0` ブロック（1件）はKellyがネガティブを検出してリスク遮断 → 防御機能正常作動
- Block要因はいずれもロジック設計内の動作
| GBP_USD | TRENDING_UP（29%） | 29% | 超低ATR水準でのトレンド。スプレッドコスト対比EVが薄い可能性 → 過度な期待は禁物 |
### 推奨戦略配分

### 2026-08-26 (Post-London Report)
| PnL | **0.0 pips** |
| 勝率 (WR) | **N/A** |
| PnL | — | — |
| WR | N/A | N/A |
### 推奨戦略配分
> **⚠️ NO ACTION推奨（以下の根拠による）**
| 累計PnL | **0.0 pips** |
**推奨確認事項**：Open Trades 1件の方向性とUSD_JPYのTRENDING_DOWN方向が逆張りになっていないか。Kellyマイナス（-0.336）の構造的原因（損失サイドの偏りか、WR低下か）の特定を優先すべき。NYセッション終了後もゼロ約定が継続する場合、「システム稼働中」と「実質的機能停止」の境界線に達したと判断すべきタイミングである。

### 2026-08-27 (Pre-Tokyo Briefing)
前日全セッション（東京・ロンドン・NY）を通じてシステム発注は一切なし。PnL = 0、N = 0、WR = N/A。稼働モード27本は正常稼働中だが、実質的に静止状態だった。
| Strategy | Pair | N | WR% | EV | PnL |
**全体集計（N=9、WR=33.3%、PnL=+14.1）**
> ⚠️ **統計的注意**：最大N=5。全戦略がN<10の「データなし」域。**数値は傾向参照レベルにも達しておらず、いかなる判断の根拠にもなり得ない。** N=30達成を最優先課題として観察継続。
- 方向フィルター: USD_JPYのTRENDING_DOWN継続中 → `rnb_usdjpy`の発注機会は引き続き限定的と予測。期待値を下げて監視。
- Hedge_block: オープンポジションがゼロ（OANDA Open Trades=0）にもかかわらずhedge_blockが頻発している点は要観察。ポジション管理状態とblock理由の整合性を確認。
- **USD_JPY（最重要）**：ATR%ile 71% + TRENDING_DOWN。このATR水準では急反転リスクも高い。`usdjpy_carry_dip_accumulator`のN=5はこの環境で蓄積されたデータ — バックグラウンド・レジームのバイアスに注意。
- **EUR/GBP系**：TRENDING_UPだが、`price_shock_rev_eur_gbp_h1_long`はN=3でWR 0% — 現トレンドに逆らうLong戦略が機能不全を起こしている可能性（N少なく断定不可）。

### 2026-08-27 (Post-Tokyo Report)
| セッション PnL | **+20.1 pips** |
| 戦略 | ペア | PnL | 成功要因 |
- **`rnb_usdjpy:direction_filter` 309件ブロック** — USD/JPY TRENDING_DOWN（ATR%ile 71%）レジームに対し方向フィルターが大量抑制。これは保護機能の正常作動だが、トレンド環境でのシグナル供給がほぼ機能していないことを示す
- **`daytrade:hedge_block` 299件 / `daytrade_gbpjpy:hedge_block` 90件** — ヘッジブロックが最大ボトルネック群。相互ポジション打消しが常態化しているか、エントリー条件が両方向同時充足している可能性
- **`scalp:r2_shadow_demoted_cell` 202件** — Shadow降格セルによる大量ブロックはR2スクリーニングが正常稼働の証左だが、scalp系の有効シグナル密度の低さを示す
### 推奨戦略配分
| **慎重観察** | scalp / scalp_5m | r2_shadow_demoted_cellブロックが多く有効シグナル密度低い。ロンドン急変には注意 |
### → **基本は NO ACTION 推奨**

### 2026-08-27 (Post-London Report)
| PnL (pips) | **0.0** |
東京セッションデータは今回提供なし。ただし**本日累計N=1（WR 100%、+20.1 pips）**という事前集計値が存在しており、これは東京早朝の単発取引と推定される。
| PnL (pips) | +20.1 | 0.0 | → |
| WR | 100% | N/A | 評価不可 |
| GBP/USD | TRENDING_UP (ATR 33%) | 同上 | 低ATR、NY初動に注意 |
### 推奨戦略配分
**⚠️ NO ACTION推奨 — ただし条件付き**
| 累計PnL | **+20.1 pips** |

### 2026-08-28 (Pre-Tokyo Briefing)
前日（2026-08-27）はトレード **N=1**、**WR=100%**、**PnL=+20.1p**。
| Strategy | Pair | N | WR% | EV | PnL | 判定 |
> **全戦略 N<10**。統計的有意性ゼロ。EVの正負いずれも「傾向」と呼べる段階にも達していない。
> 昇格基準（N≥30 & EV≥1.0）・降格基準（N≥30 & EV<−0.5）の対象戦略は現時点で**ゼロ**。
- 27モード稼働中、前日実行は **1件のみ**。
- Block Countsを見ると実質的な通過阻止が多重に機能している状態。
- **最大抑制要因**は `rnb_usdjpy:direction_filter`（2,153件ブロック）— このフィルターが単体でシステム全体の機会を最も強く制限している。
- Cutoff後累計でさえ N=7。昇格判断に必要なN=30まで、**最低あと23件**必要。

## Related
- [[index]] — 戦略Tier分類
- [[bb-rsi-reversion]] — 主要分析対象
- [[research/index]] — 学術的裏付け
- [[lessons/index]] — 過去の教訓
- [[friction-analysis]] — 摩擦モデル
