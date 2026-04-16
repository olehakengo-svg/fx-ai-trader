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

## Related
- [[index]] — 戦略Tier分類
- [[bb-rsi-reversion]] — 主要分析対象
- [[research/index]] — 学術的裏付け
- [[lessons/index]] — 過去の教訓
- [[friction-analysis]] — 摩擦モデル
