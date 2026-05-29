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

## Related
- [[index]] — 戦略Tier分類
- [[bb-rsi-reversion]] — 主要分析対象
- [[research/index]] — 学術的裏付け
- [[lessons/index]] — 過去の教訓
- [[friction-analysis]] — 摩擦モデル
