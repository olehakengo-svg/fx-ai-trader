# Post-Tokyo Report: 2026-11-24

## Analyst Report
# Post-Tokyo Report — 2026-11-24 08:15 UTC（JST 15:15）

---

## 1. 東京セッション結果

| 項目 | 値 |
|---|---|
| セッション内 N | 1 |
| WR | 0.0% |
| PnL | **−18.2 pips** |
| 有効判定 | ⚠️ N<5 — 参考値のみ（統計的意味なし） |

唯一のトレード：`usdjpy_carry_dip_accumulator` / USD_JPY / BUY / SL_HIT / スプレッド 0.8p

---

## 2. What Worked

**該当なし。**
東京セッション中の成功トレードはゼロ。

---

## 3. What Didn't Work

| 戦略 | ペア | PnL | 失敗要因 |
|---|---|---|---|
| `usdjpy_carry_dip_accumulator` | USD_JPY | **−18.2 pips** | USD_JPY はRANGING（ATR%ile 45%）かつ SMA20 Slope +0.00269 とモメンタム弱く、carry dip 買いが逆行してSL到達。 |

補足：KB記録でも USD_JPY が 94p 下落局面で carry_dip が発火せず、今回は発火したが逆方向に動いた。エントリー条件の閾値と実相場の乖離が疑われる。

---

## 4. 戦略調整判断

**NO**

理由：
- N=1 は統計的根拠なし。単一SL_HITからパラメータ変更を行うのはカーブフィットリスクが高い。
- DD防御 **0.2x Lot Mult / Defensive ON** が既に発動中（DD 10.01%、EQ ¥323,346 vs Peak ¥359,288）。現状は縮小リスクの局面であり、パラメータ変更より状態維持が優先。
- Fidelity Cutoff 後の当該戦略のN蓄積量が不明（本セッション N=1 のみ確認）——昇格・降格判断に必要な N≥30 に遠く及ばない。

---

## 5. ロンドンセッション準備

### ATR・レジーム変化予測

| ペア | 東京終値 | 現レジーム | ロンドン移行予測 |
|---|---|---|---|
| EUR_JPY | 173.36 | RANGING (ATR 53%) | ロンドン流入でボラ拡大、TRENDING化の可能性あり |
| EUR_USD | 1.0903 | TRENDING_DOWN (ATR 69%) | トレンド継続警戒。EUR売り圧力継続見込み |
| GBP_JPY | 207.188 | VOLATILE (ATR 64%) | ロンドン朝は最もスパイクリスク高。スプレッド拡大注意 |
| GBP_USD | 1.30312 | TRENDING_DOWN (ATR 71%) | EUR_USDと連動したGBP下落トレンド。高ATRで摩擦コスト増 |
| USD_JPY | 159.004 | RANGING (ATR 45%) | レンジ継続想定。carry dip 再エントリー条件に要注意 |

### 推奨戦略配分

**NO ACTION推奨**

根拠：
1. **DD防御 0.2x 発動中**（10.01% DD）——lot sizeが既に最縮小状態。追加エントリーの期待値インパクトは微小。
2. **OANDA転送率 4%**（50件中 SENT=2、SKIP=48）——本番フィルは事実上停止状態。shadow_tracking block が全18件のOANDAブロックの主因（13件 shadow_tracking）。live eligible ポジションへの移行ができていない構造問題が継続中。
3. **GBP_JPY VOLATILE / EUR_USD・GBP_USD TRENDING_DOWN** ——ロンドン朝のスプレッド拡大局面でスキャルプ系はspread_guardに引っかかるリスク高（DT閾値20%、Scalp閾値30%）。
4. `r2_shadow_demoted_cell` ブロックがscalp系全体で多数（scalp: 3979、scalp_eur: 2680、scalp_5m: 1559 等）——ロンドン高ボラ環境でこのブロックが増加する可能性あり。

---

## 6. クオンツ見解

### 最重要シグナル：**システムが「動いているが機能していない」状態の継続**

東京セッション N=1（SL_HIT）という結果以上に問題なのは構造側である。OANDA転送率 **4%**（SENT 2/50）は本番稼働率として著しく低く、shadow_tracking blockが主因であることは確認できているが、**live eligible 判定が通らないまま時間が経過している**。KBにも「open live 0 が 7.2 市場日継続」との記録があり、今回もその延長線上にある。

DD 10.01%・lot 0.2x・Defensive ON という三重の守備体制は適切だが、**守備のまま時間を消費するだけではM3ミッション（+2〜3%/月複利）への経路が開かない**。N蓄積が進まない → 昇格判断ができない → live fill が出ない、という連鎖が固着している点を最重要シグナルとして認識すべきである。

**推奨アクション（判断のみ）：** ロンドンセッションはNO ACTION。現状でのアクティブ介入よりも、N蓄積の進捗監視（carry_dip, vsg_jpy_reversalのCutoff後N確認）を優先し、N≥30到達後に昇格判断を行うサイクルへ戻ることを推奨する。

## SL replacement storm guard（決定的出力 — LLM 非経由、読み方: storm-guard-design-2026-09-22 §3）
### SL replacement storm guard
| enforce | max_tx/h | max_tx/day | deadband | evaluated | sent | failed | breaker_trips | detected (brk/idem/mono/dead/ser) | skipped (brk/idem/mono/dead/ser) |
|---|---|---|---|---|---|---|---|---|---|
| ON | 50 | 200 | 1.0p | 0 | 0 | 0 | 0 | 0/0/0/0/0 | 0/0/0/0/0 |

(guard 登録建玉なし)

