# Post-Tokyo Report: 2026-04-13

## Analyst Report
# Post-Tokyo Report (JST 15:47 / UTC 06:47, 2026-04-13)

---

## 1. 東京セッション結果

| 指標 | 値 |
|---|---|
| **セッション PnL** | **-13.4 pips** |
| **トレード数 (N)** | **18件** |
| **WR** | **33.3% (6勝/18)** |
| **平均PnL/トレード** | **-0.74 pips** |
| **Spread** | 全件 0.8 pips（spread_guard発動なし） |

**総評**: 本日累計31件・PnL -21.8 pips。XAU別枠での-1,496 pipsが最大懸念（後述）。

---

## 2. What Worked ✅

| 戦略 | Pair | Dir | PnL | 成功要因 |
|---|---|---|---|---|
| **bb_rsi_reversion** | USD_JPY | BUY×2 | +6.0 pips合計 | TP_HIT含む2勝でEV+0.83達成、RANGINGレジームで平均回帰が機能した |
| **trend_rebound** | USD_JPY | SELL | +4.2 pips | OANDA_SL_TP到達、方向性（売り）が短期モメンタムと一致 |
| **engulfing_bb** | USD_JPY | BUY | +5.0 pips | TP_HIT達成、ローソク足パターンがBBサポートと整合 |

**共通成功因子**: RANGING相場(ATR%ile=38%)でのリバーサル系戦略が機能。TP_HIT/OANDA_SL_TPによる正常クローズが成功例の共通点。

---

## 3. What Didn't Work ❌

| 戦略 | Pair | PnL | 失敗要因 |
|---|---|---|---|
| **sr_channel_reversal** | USD_JPY | -12.5 pips (N=8, WR=25%) | 8件中6件が損失/BEで、SL_HITが複数発生——RANGING環境でもレンジブレイクに巻き込まれておりSR水準の信頼度が低い |
| **vol_surge_detector** | USD_JPY | -5.6 pips (N=2) | 両方向エントリー（BUY+SELL）でどちらもSL_HIT/BREAKEVEN——ボラ急騰シグナルが誤発し方向感のない値動きに対応できていない |
| **stoch_trend_pullback** | USD_JPY | -3.0 pips (N=1) | OANDA_SL_TP発動での損失——参考値のみ（N=1） |

**最大問題**: `sr_channel_reversal` が8件中2勝（WR=25%）でセッション損失の93%を占有。KB記録の`vol_surge_detector`（Tier2: WR=63.6%）とも今朝の実績（WR=0%）に乖離あり。

---

## 4. 戦略調整判断

**→ NO（コード変更なし）**

**根拠**:

- `sr_channel_reversal` (N=8, WR=25%)はカットオフ後の判断可能閾値N=30未満。今朝の8件だけで構造的問題と断定するのは早計。ただし**警戒フラグ**を立てる。
- `vol_surge_detector` (N=2, 今朝)は完全にサンプル不足。Tier2累計ではWR=63.6%/N=11であり平均回帰を考慮。
- `bb_rsi_reversion` は今朝EV+0.83と機能しており、Tier1(KB: WR=36.4%/N=77)の許容範囲内。
- Spread 0.8 pips全件——spread_guard調整不要。

**モニタリング指示（判断のみ）**:
- `sr_channel_reversal` のN=30到達時に改めてEV評価を行い、EV<-0.5で降格検討。

---

## 5. ロンドンセッション準備 (UTC 07:00-12:00)

### レジーム移行予測

| 要素 | 東京 | ロンドン移行予測 |
|---|---|---|
| USD_JPY ATR%ile | 38% (RANGING) | やや上昇（欧州参入でボラ増加）の可能性 |
| EUR_USD | RANGING 53% | ロンドンフィックスに向けトレンド発生の可能性 |
| GBP_USD | RANGING 52% | SMA Slope≈0でフラット、方向感なし |
| 全体 | 5ペア全RANGING | ロンドン初動でブレイク試行→フェイルのケースに注意 |

**重要コンテキスト**:
- **shield_mode_blocked(scalp_5m) = 5件** → DD防御が稼働中でスキャルプ系が抑制されている。ロンドンでも継続の可能性。
- **force_demoted = 2件, pair_demoted(USD_JPY) = 1件** → USD_JPYの本番昇格が一部制限中。

### 推奨戦略配分

| 優先度 | 戦略 | Pair | 根拠 |
|---|---|---|---|
| **継続** | bb_rsi_reversion | USD_JPY | 今朝機能、RANGINGで平均回帰有効 |
| **継続** | engulfing_bb | USD_JPY | TP_HIT実績あり |
| **監視強化** | sr_channel_reversal | USD_JPY | WR=25%（今朝）——ロンドン初動のブレイクアウト局面では誤作動リスク高 |
| **期待** | vol_momentum_scalp | USD_JPY等 | Tier2最高WR(80%/N=10)——ただしshield_mode解除待ち |
| **待機** | vol_surge_detector | — | 方向感のない局面での誤発リスク——RANGINGが続くなら非推奨 |

### ロンドン特記

- **OANDA転送率66%（SENT33/SKIP17）**: shield_modeが解除されれば転送率上昇の余地あり。force_demotedの2件は要確認。
- **XAU系は全OFF**: scalp_xau, daytrade_xau停止中——XAU別枠-1,496 pipsの損失発生経緯を確認すべき（後述）。

---

## 6. クオンツ見解

### 🚨 最重要シグナル

**XAU別枠 N=11 / PnL=-1,496 pips が最大リスク事案**

XAU系モードは現在OFF（scalp_xau, daytrade_xau停止中）であるにもかかわらず、本日11件・-1,496 pipsという異常な損失が計上されている。pip_mult=100のスケールを考慮しても-1,496 pipsは過大であり、**停止前に実行されたポジションのクローズ処理**または**集計バグの可能性**を排除できない。

→ **即刻確認すべき**: XAU 11件がいつ・どのモードで発生したか、OANDAポジション残高との整合を取ること。

### 構造的観察

1. **sr_channel_reversal の過集中リスク**: 東京セッション18件中8件（44%）がこの1戦略に集中。WR=25%で損失の大半を生成。N<30なので降格判断は時期尚早だが、**ポジション集中自体がリスク**。
2. **RANGING 5ペア全一致**: 全ペアがRANGINGという均質なレジームはリバーサル系には短期有利だが、同方向の連続損失（sr_channel_reversalのSL連発）が示すように、**見せかけのレンジ内でのフォールスブレイクに脆弱**。
3. **weekly audit 0件**: 監査パイプライン未稼働のため、force_demoted / pair_demotedの判断根拠が追跡できない状態。データ品質の盲点となっている。

### 推奨アクション

| 優先 | アクション |
|---|---|
| 🔴 最高 | XAU -1,496 pipsの発生源を手動で確認（OANDAポジションと照合） |
| 
