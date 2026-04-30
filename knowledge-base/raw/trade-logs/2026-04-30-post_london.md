# Post-London Report: 2026-04-30

## Analyst Report
# ロンドンセッション Post-London Report
**2026-04-30 UTC 16:00 → JST 01:00**

---

## 1. ロンドンセッション結果

| 指標 | 値 |
|---|---|
| セッション内トレード数 | **7件** |
| 勝率 (WR) | **71.4%** (5勝2敗) |
| セッション PnL | **+6.4 pips** |
| 平均勝ちトレード | +7.2 pips |
| 平均負けトレード | -14.7 pips |
| Payoff比 | **0.49** (非対称リスクに注意) |

---

## 2. What Worked ✅

| 戦略 | ペア | PnL | 成功要因 |
|---|---|---|---|
| **xs_momentum** | GBP_USD | **+22.2 pips** | ロンドン序盤のGBP上昇モメンタムをキャプチャ、OANDA_SL_TPによる適切な利確実行 |
| **bb_rsi_reversion** | USD_JPY | +6.9 pips | TP_HIT達成、USD/JPYのレンジ内RSI平均回帰が機能 |
| **bb_rsi_reversion** | EUR_USD | +4.3 pips | EUR_USDの低スプレッド(0.8pip)環境でTP_HIT、摩擦コスト最小 |
| **session_time_bias** | GBP_USD | +1.3 pips | OANDA_SL_TP管理下で小幅利確 |
| **gbp_deep_pullback** | GBP_USD | +1.1 pips | SL_HITにもかかわらず利益確定（逆指値が利益圏内に設定済みの状態での決着） |

**本セッションの最大貢献:** xs_momentum GBP_USD (+22.2p) がセッションPnLの347%分を単独で稼ぎ、他の損失を相殺した構造。

---

## 3. What Didn't Work ❌

| 戦略 | ペア | PnL | 失敗要因 |
|---|---|---|---|
| **streak_reversal** | USD_JPY | **-23.4 pips** | SL_HIT — USD/JPYはATR%ile=29%のRANGING低ボラ環境でストリーク反転シグナルが機能せず、Payoff比の悪さが直撃 |
| **bb_rsi_reversion** | GBP_USD | -6.0 pips | SL_HIT — スプレッド1.3pipのGBP_USDで同一戦略がEUR_USD(0.8pip)比 摩擦不利、bb_rsi_reversionのGBP_USD適用の構造的懸念 |

> ⚠️ **streak_reversalの-23.4pipsは本セッション最大損失**。xs_momentumの+22.2pipsとほぼ相殺される規模であり、1トレードでセッションPnLを破壊しうるリスクが顕在化。

---

## 4. 東京セッションとの比較

| 指標 | 東京（推定） | ロンドン | 変化 |
|---|---|---|---|
| 本日累計 N | 11件 | うち7件がロンドン | ロンドン集中型 |
| 本日累計 PnL | **-4.3 pips** | ロンドン単体 +6.4 pips | 東京: -10.7 pips（逆算） |
| WR | 54.5%(全体) | 71.4%(ロンドン) | ロンドンで改善 |
| レジーム | RANGING全対 | RANGING継続 | 変化なし |

**構造的観察:**
- 東京セッションは推定 **N=4, PnL≈-10.7pips** と苦戦
- ロンドン移行後にWR・PnL双方が改善したが、xs_momentumの+22.2pipsという**単一外れ値依存**の改善であることに留意
- レジームはUSD_JPY(ATR=29%ile)を筆頭に**全通貨RANGING継続**— トレンド追従型は構造的不利

---

## 5. NYセッション準備

### ATR/レジーム変化予測
- **UTC 16:00-21:00**: NY主導セッション移行期
- USD_JPY ATR%ile=29%（超低ボラ）→ **ADP/ISM等指標で一時的スパイクの可能性**
- GBP_USDは本日BUY一辺倒（3/3件）— ロンドンクローズ後の**ポジション整理売りリスク**に注意
- EUR_USD/GBP_USDはSMA20 Slope+0.003～+0.005と緩やかな上昇トレンドも、RANGING判定が優先

### 推奨戦略配分

| 戦略 | ペア | 推奨 | 理由 |
|---|---|---|---|
| **bb_rsi_reversion** | EUR_USD | 🟢 継続 | 低スプレッド0.8pip + 本日TP_HIT実績、RANGINGに適合 |
| **bb_rsi_reversion** | USD_JPY | 🟡 条件付き | 低ボラ継続なら機能、指標発表前後は回避 |
| **session_time_bias** | GBP_USD | 🟡 条件付き | BTデータなし・WR=33.3%(N=3)の懸念あり、小サイズ |
| **xs_momentum** | GBP_USD | 🟢 継続 | NY序盤モメンタム継続期待、ただし今日の+22.2は外れ値認識で過信禁物 |
| **streak_reversal** | USD_JPY | 🔴 **NO ACTION推奨** | 本日-23.4pips、低ボラRANGING環境で機能しない、BTデータなし |

> **「NO ACTION推奨」:** streak_reversal/USD_JPYは本日のパフォーマンスとレジーム環境の双方からNYセッション新規エントリーを推奨しない。

---

## 6. 本日暫定結果

| 指標 | 値 |
|---|---|
| 累計トレード数 | **11件** |
| 累計 WR | **54.5%** (6勝5敗) |
| 累計 PnL | **-4.3 pips** |
| OANDA Live転送率 | **0%** (50件全SKIP、shadow_tracking=20件) |
| 最大単発損失 | streak_reversal USD_JPY **-23.4 pips** |
| 最大単発利益 | xs_momentum GBP_USD **+22.2 pips** |

---

## 7. クオンツ見解

### 🔴 最重要シグナル: streak_reversalの構造的脆弱性

本日のセッションPnL+6.4pipsは実質的に**xs_momentumの+22.2pipsという1件の外れ値で成立**しており、streak_reversalの-23.4pipsとほぼ相殺されている。この2トレードを除外すると残5件は**+7.6pips**と地味な正EVが確認できるが、現状のポートフォリオはテール損失の管理が課題。

streak_reversalはKB上「BTデータなし・PAIR_PROMOTED」ステータスであり、N蓄積フェーズにある。しかしUSD_JPY ATR%ile=29%という**低ボラRANGING環境でのストリーク反転は、そもそも機能しないレジーム**である。N=30到達まで稼働継続するにしても、現在のレジーム下では**期待値がマイナスに偏っている可能性**を統計的に否定できない。

**推奨アクション: streak_reversal/USD_JPYについて、現在のRANGINGレジーム解除まで新規エントリーの停止を判断すべき。** NYセッション内で指標イベントによりATR%ileが上昇・レジームがTRENDINGに移行した場合に限り、再評価を検討する。

---
*Report generated: 2026-04-30 17:10 UTC | Data Cutoff: 2026-04-08T00:00:00Z | OANDA Live: INACTIVE*
