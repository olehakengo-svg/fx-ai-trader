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

## Related
- [[index]] — 戦略Tier分類
- [[bb-rsi-reversion]] — 主要分析対象
- [[research/index]] — 学術的裏付け
- [[lessons/index]] — 過去の教訓
- [[friction-analysis]] — 摩擦モデル
