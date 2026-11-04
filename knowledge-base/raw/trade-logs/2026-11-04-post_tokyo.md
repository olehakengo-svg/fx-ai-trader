# Post-Tokyo Report: 2026-11-04

## Analyst Report
# Post-Tokyo Report（JST 15:00 / 2026-11-04）

---

## 1. 東京セッション結果

| 指標 | 値 |
|---|---|
| セッション内 N | 1 |
| WR | 100.0%（参考値: N<5） |
| PnL | +10.2 pips |
| 戦略 | usdjpy_carry_dip_accumulator / USD_JPY |
| 本日累計 PnL | +10.2 pips（全1件） |

> ⚠️ N=1 は統計的に「データなし」扱い。勝率・EVいずれも本セッション単独では判断不可。

---

## 2. What Worked

| 戦略 | ペア | PnL | 成功要因 |
|---|---|---|---|
| usdjpy_carry_dip_accumulator | USD_JPY BUY | +10.2 pips | Spread 0.8p（ガード閾値DT=20%以内）でエントリー、SL_HIT（相手方決済）で正常クローズ。 |

**補足:** Spread 0.8p / USD_JPY は許容範囲内。SL_HIT による利益確定は正常動作（逆張りアキュムレーターの設計通り）。

---

## 3. What Didn't Work

| 戦略 | ペア | PnL | 失敗要因 |
|---|---|---|---|
| — | — | — | 失敗トレードなし（N=1の唯一トレードは WIN） |

**実質的な不発点:** 多数の戦略モード（27モード稼働中）が1件しか執行できていない点そのものが最大の「機能しなかった」シグナル。Block件数上位を見ると：

| ブロック主因 | 件数 | 意味 |
|---|---|---|
| rnb_usdjpy: no_signal | 203 | レンジ相場でシグナル生成なし（設計通り） |
| scalp系: r2_shadow_demoted_cell | 71〜105 | Shadow降格セルによる静的ブロック（累積） |
| daytrade_eurjpy: order_bar_dedup | 88 | 重複バー排除（レンジ内の往復を抑制） |
| daytrade_eur: hedge_block | 82 | ヘッジ検出によるブロック |

**構造的結論:** r2_shadow_demoted_cell が scalp系4戦略で合計307件をブロック。Shadow降格セルが実執行の主要抑制装置として機能している。

---

## 4. 戦略調整判断

**→ NO（コード変更なし）/ パラメータ変更: NO**

| 判断根拠 | 詳細 |
|---|---|
| N≥30 未達 | Fidelity Cutoff後の全戦略でN<30。統計的判断基準に達していない |
| DD防御中 | 実DD **−24.01%**（KB記録）。DD防御0.2xモード稼働中。積極的な調整は禁忌 |
| レジーム一致 | 全5通貨ペアRANGING。現在の抑制動作（no_signal多発）はレジームと整合 |
| Sentinel蓄積優先 | 現段階はN蓄積フェーズ。介入よりデータ収集が優先 |

---

## 5. ロンドンセッション準備（UTC 07:00〜）

### ATR/レジーム変化予測

| 観点 | 現状（東京終盤） | ロンドン移行予測 |
|---|---|---|
| 全ペアレジーム | RANGING（5/5） | RANGING継続の可能性高（SMA20 Slopeが全ペア±0.002以内） |
| ATR%ile | USD_JPY 38%（低）、EUR_USD 67%（中高） | EUR系はロンドン開場でATR拡大の可能性。USD_JPYは低ボラ継続か |
| 方向性バイアス | USD_JPY +SMA slope微小（+0.00012）/ EUR系弱マイナス | 明確なトレンドシグナルなし |

**EUR_USD ATR%ile 67% + GBP_USD 64%** → ロンドン勢参入でさらに拡大した場合、DT系がシグナルを出す可能性は僅かにある。ただしSMA Slopeがネガティブ（EUR/GBP系）であり方向感は不明瞭。

### 推奨戦略配分

**NO ACTION推奨（現行稼働状態の維持のみ）**

| 推奨根拠 | 詳細 |
|---|---|
| DD防御0.2xモード稼働中 | 追加ポジション増強の根拠なし |
| 全ペアRANGING | スケーラブルなトレンドフォロー戦略の有効性低 |
| N蓄積フェーズ | 昇格基準（N≥30 & EV≥1.0）に達している戦略が存在しない状態での配分変更は非効率 |
| OANDA転送率4%（2/50） | shadow_tracking / pair_demoted によるブロックが支配的。ライブ執行インフラの制約内での自然な動作 |

**ロンドンで注視するシグナル:**
- EUR_USD または GBP_USD の ATR%ile が 70%超 → DAYTRADEシグナル発火の可否を事後確認
- hedge_block（現在82件）の増減 → ヘッジ対象ポジションの展開方向を示す先行指標

---

## 6. クオンツ見解

### 最重要シグナル

**OANDA転送率4%（50件中SENT=2）とShadow降格ブロック307件の複合：システムは「正しく止まっている」が、M3達成経路との乖離を直視すべき。**

東京セッション全27モード稼働で実執行1件・OANDA LIVE到達2件（累計）という状況は、フィルタリング構造が意図通りに機能していることを示す一方で、**DD −24%状態でのN蓄積ペースがM3目標（+2〜3%/月複利）の経路に乗れていない**という根本的緊張を示している。

r2_shadow_demoted_cell による静的ブロックが累計307件に達しており、これらのセルが「誤って降格されたままになっていないか」を昇格基準（N≥30 & EV≥1.0）に照らして定期的に審査することが、現状を打開する唯一の合法的手段である。コードに触れずに実行できる判断：**Shadow降格セルの統計的再評価タイミング（N蓄積完了後）を明示的にスケジュールすること**。

---
*Report generated: 2026-11-04 04:43 UTC | Data fidelity: Cutoff後有効 | 次回報告推奨: UTC 12:00（ロンドン中間）*

## SL replacement storm guard（決定的出力 — LLM 非経由、読み方: storm-guard-design-2026-09-22 §3）
### SL replacement storm guard
| enforce | max_tx/h | max_tx/day | deadband | evaluated | sent | failed | breaker_trips | detected (brk/idem/mono/dead/ser) | skipped (brk/idem/mono/dead/ser) |
|---|---|---|---|---|---|---|---|---|---|
| ON | 50 | 200 | 1.0p | 70 | 5 | 0 | 0 | 0/0/0/0/0 | 0/0/0/65/0 |

(guard 登録建玉なし)

