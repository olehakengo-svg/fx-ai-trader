# Post-Tokyo Report: 2026-10-12

## Analyst Report
# Post-Tokyo Report — 2026-10-12 04:10 UTC (JST 13:10)

---

## 1. 東京セッション結果

**東京セッション: トレードなし**

| 項目 | 値 |
|---|---|
| セッション PnL | ¥0 |
| トレード数 | 0 |
| WR | N/A |
| OANDA Open Trades | 0 |

UTC 00:00–06:00 の範囲に決済・発注ともゼロ。全27モードが稼働中（daytrade_xau / scalp_eurjpy / scalp_xau を除く）にもかかわらず、約定ゼロという完全な不活性セッション。

---

## 2. What Worked

**該当なし**（トレード発生せず）

---

## 3. What Didn't Work

**該当なし**（トレード発生せず）

ただし、ブロックログが活発であり「発注試行→遮断」の構造は存在する。主要ブロック要因を以下に整理する：

| ブロック要因 | 件数 | 関連モード |
|---|---|---|
| `rnb_usdjpy:no_signal` | 668 | rnb_usdjpy |
| `r2_shadow_demoted_cell` | 677（scalp系合計）| scalp / scalp_eur / scalp_5m / scalp_5m_gbp / scalp_5m_eur |
| `gbp_asia_flash_crash` | 213（eurgbp+gbpjpy+gbpusd）| GBP系DT |
| `order_bar_dedup` | 228（eurjpy+eur+audjpy+gbpusd）| DT複数 |
| `daytrade:score_gate` | 32 | daytrade |

**主因分析：**

- **scalp系の完全封鎖**: `r2_shadow_demoted_cell` が677件。Shadow demoteされたセルが東京時間帯のscalp系を実質的にシャットアウト。シャドウ追跡中（OANDA Block Reasons: shadow_tracking 18件）と整合的であり、構造的ブロックであって一時的ノイズではない。
- **GBP系の`gbp_asia_flash_crash`**: 213件。東京時間帯のGBPボラティリティ防御が継続的に発動。EUR_GBP(71% ATR%ile, RANGING)・GBP_JPY(71%)・GBP_USD(TRENDING_DOWN)のATRレジームが高めに推移しており、ガード発動継続は合理的。
- **`order_bar_dedup`**: 228件。EUR_JPY / EUR / AUD_JPY / GBP_USDで重複発注排除が多数。シグナル自体は生成されているが、bar内重複として棄却されており、シグナル生成器は機能している証拠でもある。
- **`rnb_usdjpy:no_signal`**: 668件。USD_JPY(TRENDING_UP, 57%ile)のレジームでRnBがシグナルを出せないのは、レンジ戻りストラテジーとしてトレンド相場に適応できていない構造的問題。

---

## 4. 戦略調整判断

**NO — コード変更・パラメータ変更は行わない**

理由：
- トレードゼロはシステム異常ではなく、ガード群（spread_guard / shadow demote / flash_crash / dedup）が設計通りに機能した結果。
- scalp系の shadow_demote は評価プロセス中であり、N蓄積途上での介入はデータ汚染を招く。
- DD防御0.2x モード継続中（KB確認）。現NAV ¥273,565 / floor ¥262,000、クッション ¥11,565（約4.2%）。不確実なセッションで強制的に発注を増やすことはミッション整合性に反する。

---

## 5. ロンドンセッション準備（UTC 06:00–）

### ATR / レジーム変化予測

| ペア | 現レジーム | ロンドン移行予測 |
|---|---|---|
| EUR_JPY | RANGING (71%ile, slope -0.00217) | ロンドン初動でボラ上昇の可能性。RangingからVolatileへ短期移行リスクあり |
| EUR_USD | VOLATILE (78%ile, slope -0.00879) | 高ボラ継続。下落バイアス継続、scalp系には不利 |
| GBP_USD | TRENDING_DOWN (71%ile, slope -0.00560) | ロンドン主力ペア。トレンド継続なら daytrade_gbpusd に理論上優位だが `gbp_asia_flash_crash` ガード次第 |
| GBP_JPY | RANGING (71%ile) | GBPクロスは flash_crash ガードが外れないと約定困難 |
| USD_JPY | TRENDING_UP (57%ile, slope +0.00650) | rnb系には不利なトレンド環境継続 |

**ATR%ile全体が70%台**：ボラティリティが高止まりしており、spread_guard の発動頻度は引き続き高い状態が予想される。

### 推奨戦略配分

| 優先度 | 戦略 | ペア | 根拠 |
|---|---|---|---|
| 監視 | daytrade_gbpusd | GBP_USD | TRENDING_DOWN 環境でDTシグナルが出れば order_bar_dedup 通過後に有効候補。ただし `gbp_asia_flash_crash` の解除タイミング依存 |
| 監視 | daytrade_1h系 | USD_JPY | TRENDING_UP 57%ile、1h足ではトレンドフォロー戦略に一定適性 |
| 待機 | scalp系全般 | 全ペア | shadow_demote 継続中、介入不可 |
| 待機 | rnb_usdjpy | USD_JPY | トレンド相場でno_signal継続。ロンドンでも改善見込み薄 |

**NO ACTION推奨** — 積極的なポジション追加や設定変更の根拠なし。ロンドン初動のボラ上昇を確認してから自然発生シグナルの通過を観察する姿勢が適切。

---

## 6. クオンツ見解

### 最重要シグナル: OANDA転送率8%の構造的低迷とshadow_demote飽和

**転送率8%（50件中4件LIVE送信）は機能的にほぼデモ専用運用状態である。**

現状の内訳を見ると、OANDA Bridgeのblock 20件のうち18件が `shadow_tracking`（評価待ち）であり、残り2件が auto_demoted / pair_demoted によるプロモーションブロック。すなわち「評価プロセス待ち」が転送率低迷の主因であって、システム障害ではない。しかしこの状態が長期化すると、ミッションM3（月次+2〜3%複利）への寄与がデモPnLのみに留まり、実口座NAVへの反映が構造的に遅延する。

scalp系のN蓄積状況（r2_shadow_demoted_cellによるブロック677件）は逆説的に「シグナル候補は存在するがshadow評価待ちで全てフィルタリングされている」ことを示す。N=30到達が昇格の唯一の経路であるが、東京セッション約定ゼロのペースでは蓄積が極めて遅い。

**推奨判断（コード変更なし）：**
1. scalp系のshadow N蓄積進捗を次回レポートで定量確認（現在何件/30件か）— 最優先監視項目。
2. `rnb_usdjpy` は 668件の `no_signal` が示す通り、USD_JPYトレンド継続中はシステム的にシグナル非生成状態。降格判断の前にレジームが変化するまで待機継続が合理的（N=0のため降格判断基準N≥30にも未到達）。
3. DD防御0.2x モード下でのNAVクッション¥11,565（4.2%）は十分ではあるが、拡大していない。トレードゼロセッション継続はflooring圧力がないという意味では安全だが、M3目標への距離は縮まらない
