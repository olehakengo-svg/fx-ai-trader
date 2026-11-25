# Post-Tokyo Report: 2026-11-25

## Analyst Report
# Post-Tokyo Report — 2026-11-25 04:49 UTC (JST 13:49)

---

## 1. 東京セッション結果

**東京セッション: トレードなし**

| 項目 | 値 |
|---|---|
| セッション内トレード数 | 0 |
| PnL | ¥0 |
| WR | — |
| アクティブモード数 | 25 / 27 (OFF: daytrade_xau, scalp_xau, scalp_eurjpy) |

東京セッション（UTC 00:00–06:00）における約定ゼロを確認。システムは起動済みだが、全エントリーがブロックまたは非シグナルで終了。

---

## 2. What Worked

**該当なし** — 東京セッション内に約定トレードが存在しないため、成功事例の抽出不可。

---

## 3. What Didn't Work

**東京セッション内のブロック主因（Block Counts より）:**

| Reason | Count | 主因 |
|---|---|---|
| `rnb_usdjpy:no_signal` | 230 | RnB戦略がシグナル生成に至らず（レンジ判定しながらエントリー条件不成立） |
| `scalp:r2_shadow_demoted_cell` | 157 | Shadow降格セルによるスカルプ封鎖が最大ブロック要因 |
| `daytrade_gbpjpy:gbp_asia_flash_crash` | 156 | GBP/JPY アジアフラッシュクラッシュガード発動（VOLATILE判定と整合） |
| `scalp_eur:r2_shadow_demoted_cell` | 82 | EUR系スカルプも同様に降格セル封鎖 |
| `daytrade:order_bar_dedup` | 63 | 重複注文防止フィルター（高頻度ブロック） |
| `scalp_5m:r2_shadow_demoted_cell` | 52 | 5mスカルプも Shadow降格圧力下 |

**主要失敗要因の構造分析:**

1. **Shadow降格セル（r2_shadow_demoted_cell）の支配**: scalp系4戦略合計 157+82+52+44+16 = **351件** がこの1原因でブロック。東京セッションの実質的エントリー停止をもたらした最大因子。
2. **GBP/JPY flash crash guard**: レジーム分類がVOLATILEであることと完全整合しており、ガードは正当に機能している。ただし156件という高頻度は、GBP/JPYが継続的にVOLATILE域で推移していることを示唆。
3. **RnBシグナル不発**: USD/JPYはRANGING(ATR%ile 43%)でRnBに有利なはずだが、230件のno_signalは価格がR/Bレベルに到達しなかったことを示す（バンド内中間域での推移）。

---

## 4. 戦略調整判断

**NO — パラメータ変更不要**

**根拠:**
- 東京セッションN=0。統計的判断に必要なサンプルが皆無。
- DD防御が**0.2x (defensive mode, 10.01% DD)**で稼働中。現時点での戦略拡張・パラメータ緩和は禁忌。
- Block原因はすべてシステム設計通りのガード機能（Shadow降格、flash crash guard、dedup）であり、誤動作ではない。
- Shadow降格セルの解除はR²実績改善によってのみ正当化される。現在のN蓄積状況でのmanual解除判断は根拠不足。

---

## 5. ロンドンセッション準備 (UTC 06:00–)

### ATR/レジーム変化予測

| ペア | 現在レジーム | ロンドン移行予測 | 根拠 |
|---|---|---|---|
| GBP/JPY | VOLATILE (67%ile) | VOLATILE継続 or 拡大 | ロンドン開始でGBP流動性増加 → ATR上昇圧力。flash crash guard継続発動リスク高 |
| GBP/USD | VOLATILE (69%ile) | VOLATILE継続 | 同上。GBP系はロンドン移行で更にATR拡大しやすい |
| EUR/USD | TRENDING_DOWN (67%ile) | TRENDING継続 | SMA20 slope −0.00530の下降トレンド。ロンドン参入でトレンド加速または一時反発 |
| EUR/JPY | RANGING (55%ile) | RANGING or TRENDING転換注意 | EUR/USDの下降とUSD/JPYの緩やかな上昇が競合。方向感不鮮明 |
| USD/JPY | RANGING (43%ile) | RANGING継続 | 低ATR%ile。ロンドンでの急動意は低確率だがSMA20 slope +0.00272で微妙な上昇バイアス |

### 推奨戦略配分

**NO ACTION推奨**（以下の複合条件による）

| 条件 | 状態 |
|---|---|
| DD防御 | 0.2x defensive 発動中（DD 10.01%） |
| OANDA転送率 | 0% (50/50がSKIP) — live填充なし |
| Shadow降格 | scalp系で大規模封鎖中（解除条件未達） |
| GBP系 | VOLATILE + flash crash guard で実質封鎖 |
| RnB | シグナル不発継続中（no_signal 230件） |
| agg_kelly | −0.223 < 0（ブロック1件確認）— Kelly負でエントリー積極化は不合理 |

**ロンドンで観察すべきチェックポイント（アクションではなく監視）:**
- EUR/USD TRENDING_DOWN がロンドン移行後に continuationするかどうか（daytrade_eur系のシグナル生成条件と照合）
- GBP系 flash crash guard の発動継続頻度（VOLATILE継続の確認）
- agg_kellyが0以上に転換するタイミング（bridge blockの解消条件）

---

## 6. クオンツ見解

### 最重要シグナル：**「システム全体がDD防御+Shadow封鎖+agg_kelly負の三重停止状態にある」**

東京セッションのゼロ約定は異常ではなく、**設計通りの多層防御が同時発動した結果**として読む。しかし問題はその期間の長さだ。

- **DD 10.01%、lot mult 0.2x** — EQ Peak ¥359,288 → Current ¥323,346という¥35,942のドローダウンは、KB記録の実DD −24.32%（broker基準）とも整合しており、defensive modeの解除には明確なリカバリーが必要。
- **OANDA転送率0%（50トレード全てSKIP）** — Shadow降格とagg_kelly負が生きている限り、デモで約定しても本番には流れない。現状はデモシステムがN蓄積のためだけに稼働している状態に近い。
- **推奨アクション**: DD回復（EQ ≥ ¥359,288復帰）まで現状維持を堅持。ロンドンセッションで強制的にパラメータ拡張する根拠は一切なし。N蓄積の進捗監視を継続し、scalp系でN=30到達戦略が出た段階で個別評価を行う判断タイミングとする。

## SL replacement storm guard（決定的出力 — LLM 非経由、読み方: storm-guard-design-2026-09-22 §3）
### SL replacement storm guard
| enforce | max_tx/h | max_tx/day | deadband | evaluated | sent | failed | breaker_trips | detected (brk/idem/mono/dead/ser) | skipped (brk/idem/mono/dead/ser) |
|---|---|---|---|---|---|---|---|---|---|
| ON | 50 | 200 | 1.0p | 0 | 0 | 0 | 0 | 0/0/0/0/0 | 0/0/0/0/0 |

(guard 登録建玉なし)

