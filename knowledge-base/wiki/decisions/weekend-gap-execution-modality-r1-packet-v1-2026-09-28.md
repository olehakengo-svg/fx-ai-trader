# weekend_gap 執行モダリティ R1 再審 — 起案 packet v1 (2026-09-28)

> **Status: 📨 R1 起案 (user 決裁待ち、W1〜W6)。LOCK ではない。** [[weekend-gap-execution-contract-r1-packet-2026-09-10]] §6 の事前コミット「改定後の最初の 2 qualifying イベントで **2 連続 fill 不成立 → 執行モダリティ自体を再審 (R1 再起案)** — 3 度目の『観測して待つ』はしない」が **2026-09-27 21:05Z の event #2 (`ABANDONED_DRIFT`) で発動**した。本文書は骨子 [[weekend-gap-execution-modality-r1-redraft-DRAFT-2026-09-22]] §4 の構成に一次データを入れて起案したもの。
> rule:R3 (文書 + registry 記録のみ。code / 凍結値 / live 経路 不変更 — 契約 B は fail-closed で継続中)。候補の選択・凍結値の変更・新フィルタは全て **R1 + user 承認**。
> **本文書で計算していないもの**: shadow row の outcome (pnl / MFE / 埋め率)、G1 slippage 集計、G2 累積、OOS 窓 (2022-01-01〜2026-06-30) の再接触、drift 帯別・gap 帯別の 4h 回帰。数字は全て価格系 (gap / drift / basis / 時刻) と既存凍結値の引用のみ ([[weekend-gap-stage2-execution-prereg-2026-07-24]] §8)。
> 一次データ: Render ログ API 実読 (service `srv-d6va1of5r7bs73en10vg`、2026-09-27T20:58–21:12Z、text=`WEEKEND_GAP` 27 行・hasMore=false) / 本番 `/api/demo/trades` row **18538** / `/api/oanda/audit` **17930** / `bt-results/wg_gap_drift-2026-09-28.json` (本 PR で新規、read-only 価格計測) / `bt-results/wg_gap_drift-2026-09-10.json` (packet 2026-09-10 の凍結計測)。

---

## 0. 決裁サマリ (user 向け 3 行)

1. **何が起きたか**: 執行契約 (B) 発効 (09-10) 後の qualifying pair-event は **2 件とも `ABANDONED_DRIFT`** — 09-13 USD_JPY (gap −50.0p、drift +41.0p) / **09-27 USD_JPY (gap −22.0p、drift +18.4p)**。live fill は live 化 (07-25) 以降 **0/5 qualifying イベント**、契約 B 下 **0/2**。packet §6 の「2 連続不成立」が成立 = **G0' 終了・R1 再審発動**。
2. **機構 (価格のみ、新所見)**: 2 件とも「drift」の実体は **開場後の値動きではなく、OOS estimand の entry 価格 (MASSIVE 日曜 21:00 バー open) と OANDA が提示した最初の価格との差 (basis)** — 09-13 basis **+41.0p** (live drift +41.0p)、09-27 basis **+19.3p** (live drift +18.4p)。OANDA 基準で測った gap は **−9.0p / −2.7p = どちらも qualify 閾値 21.4p 未満**。つまり OOS が PASS した「Sunday open で入る fade」の entry 価格は、**OANDA が tradeable になった最初の quote の時点で既に 41 / 19p 消費されていた**。MASSIVE の 21:00 print が pre-open / 他 venue の stale print で OANDA が一度も提示しなかったのか (H1)、halt 窓 ~4 分の間に市場が実際に動いたのか (H2) は、OANDA の pre-open tick / 初 M1 の range を持たない本計測では**識別できない** (Codex P1 4117990982、§1.2・§2) — どちらでも送信タイミングでは取り戻せない点は同じ。契約 B の drift 境界 +8.0p を導出した実測 (MASSIVE 内部 +5m drift、qualifying 0/8 抵触) は **この basis 成分を含んでいない** = 見積り (fill 率 点 ~0.94) は測定基準の不一致で過大だった (§5)。
3. **選択肢 (§3、user 決裁 W2)**: 09-13 / 09-27 型を live に到達させられるのは **(2d) drift 境界撤廃** か **(5/5′) シグナル基準の OANDA 化** のみで、どちらも **OOS PASS とは別の estimand** を live で始めることになる (F2 の趣旨「PASS→live 変換の実証」とは別の問い、W3)。起案者推奨 = **W1 (3) 契約 B 継続を明示決裁** (packet §6「3 度目の観測はしない」の撤回を記録した上で) + 候補 6 の価格系 forward 観測、**11-15 checkpoint 付き** (§6)。理由: 契約 B の drift 境界は「tradeable 時点で既に消費された gap」を fade する entry を正しく止めており、entry 価格の estimand 乖離を 8p に上限した fill を **~0.4〜0.5 × qualifying** で生む (engine 確定 5 event で 2/5 通過、json 拡張 10 event で 5/10; F2 期待 fill ≈ 3.5〜4.3 event / 12-31 [pair-event 率 3.28/月]、N=0 確率 ≈ 1〜3%、§5。**選択された部分集合の EV は凍結 pooled mean から導けない — forward のみ**)。**(5′) LIVE 側 OANDA-basis 再 qualify** (shadow 不変、4原則#3 の非対称) は estimand 純度では優るが、機会 5/57 ≈ 1.1/月 → drift・cap 通過後の fill ≈ 0.75/月、Rule 1 リードタイム込みで 12-31 まで **実効 ~1.4 event** と F2 で劣後 → **後続 R1 候補** (checkpoint で契約 B が N=0 なら起案)。2d は estimand 変更 (W3)。

---

## 1. 故障の機構 — 2 不成立の root cause 分解

### 1.1 event #2 (2026-09-27、USD_JPY) — 一次データ (全て Render ログ / 本番 API 実読 2026-09-28 01:10Z)

| 時刻 (UTC) | 事象 | 出所 |
|---|---|---|
| 21:00:00 | MASSIVE 15m 初バー (`first_bar=2026-09-27 21:00:00`)、engine `sunday_open` **157.059**、Fri close **157.279** → gap **−22.0p ≥ 21.4p** → BUY fade | EXEC_B ログ / row 18538 reasons |
| 21:01:06.9 〜 21:04:54.5 | `[WEEKEND_GAP][EXEC_B] USD_JPY decision=HOLD tradeable=False` **20 行** (poll 間隔 12–19s ≤ 60s ✓)。`quote_age` 172,921→173,149s = **金曜 quote** (send_mid 157.295 は金曜終値 mid、drift +23.6p は stale quote 由来で判定には未使用) | Render ログ |
| 21:01:10.3 / 21:01:20.6 | `AUD_USD gap=-12.8p < 25.0p no-qualify` (2 行 = tick 再評価の再ログ、row/latch なし) | Render ログ |
| 21:01:18.7 / 21:01:29.1 | `EUR_USD gap=-12.7p < 20.0p no-qualify` (同上) | Render ログ |
| 21:04:54.5 < 開場 ≤ 21:05:10.9 | OANDA 実開場 (最終 HOLD tradeable=False → 次 poll tradeable=True、quote ts = 21:05:13.36 − 2.456s)。OANDA 初 M1 candle = **21:04:00Z** (json) — 契約 B 導出時の 48/48 「+4 分」と整合 | Render ログ / `wg_gap_drift-2026-09-28.json` |
| **21:05:13.36** | `decision=ABANDONED_DRIFT tradeable=True quote_age=2.456s drift=+18.40p (abandon>+8.0p) send_mid=157.243 sunday_open=157.059` → 同 ms `qualifying event: gap=-22.0p → BUY fade → _tick_entry` (**初回発火 1 回のみ、再発火なし**) | Render ログ |
| 21:05:14.0 | `live execution abandoned (ABANDONED_DRIFT) → shadow record (分母保存)` | Render ログ |
| 21:05:14.74 | shadow row **id 18538** (`is_shadow=1`、`oanda_trade_id` 空、`entry_time` 21:05:14.74Z、signal=entry 157.274、spread_at_entry **6.1p** (cap 10.0p 内)、slippage 0.0、`[SLTP_CONSTRUCT] sl=preserve` decl 150p → 155.4p / TP 500p → 494.6p、`[EMIT_PROC] import:autostart`) | `/api/demo/trades` |
| 21:05:16.43 | oanda_audit **id 17930** `bridge_status=skipped` `block_reason=weekend_gap_exec_abandon(ABANDONED_DRIFT,drift=+18.40p)` `is_live=false` | `/api/oanda/audit` |
| — | `[HALT_RACE]` なし (送信ゼロなので再送なし)。`[SENTINEL_BLOCK_DIAG] weekend_gap_fade candidate built but shadow-downgraded before OANDA promotion` 21:05:17 = 放棄後の shadow 化 (設計どおり) | Render ログ |

**分類 (DRAFT §2)**: 不成立 **(i) `ABANDONED_DRIFT`** (row + latch あり = `PRE_ROW_BLOCK` ではない)。当該週末の pair-event 列 = **[USD_JPY ABANDONED_DRIFT] の 1 件のみ** (AUD_USD / EUR_USD は gap 診断行で no-qualify **確定**、分母外) → (α) 単一クラス、順序問題 (W5) 不発生。**G0' event #2 = 不成立 → 改定後 2 連続 = packet §6 row 2 発動、G0' 終了 (event #3 は存在しない)**。shadow outcome は転記しない。

**G0' 手順 (1)〜(5) の判定 (registry g0prime)**: (1) decision 遷移 HOLD×20 → ABANDONED_DRIFT、tradeable / quote_age / drift 記録あり ✓ / (2) 送信時刻 = 該当なし (放棄)。tradeable 確認は実開場 +≤19s = 「+0〜2 分」内 ✓ / (3) 正当放棄の分類 = drift 放棄 (packet §6 row 2 の「drift 放棄」= 不成立に含む) / (4) fill なし → 突合対象なし / (5) 再送なし ✓。**契約 B の配管は仕様どおり作動した。放棄は契約の欠陥ではなく契約の仕様 — 問題は仕様が前提にした estimand (§1.2)。**

### 1.2 root cause 分解 (2 件、価格のみ)

| | event #1 09-13 USD_JPY | event #2 09-27 USD_JPY |
|---|---|---|
| MASSIVE gap (engine、OOS estimand) | −50.0p (153.620 → 153.120) | −22.0p (157.279 → 157.059) |
| live drift (契約 B: OANDA send_mid − MASSIVE sunday_open) | **+41.0p** (send_mid 153.53、quote_age 7.5s) | **+18.4p** (send_mid 157.243、quote_age 2.5s) |
| basis (OANDA 初 M1 21:04 open mid − MASSIVE 21:00 open、json) | **+41.0p** (153.53 − 153.12) | **+19.3p** (157.252 − 157.059) |
| drift − basis (= 開場後の実際の値動き成分) | **0.0p** | **−0.9p** |
| MASSIVE 1m 内部 drift (+2m〜+15m、json) | +39.3p で全 offset 一定 | +9.3p で全 offset 一定 |
| OANDA 基準 gap (OANDA 初 M1 mid − Fri close) | **−9.0p** (< 21.4p) | **−2.7p** (< 21.4p) |
| 分類 | 不成立 (i) drift 型 | 不成立 (i) drift 型 |

**読み**: 2 件とも drift ≈ basis = **OANDA の最初の tradeable quote の時点で、OOS estimand の entry 価格 (MASSIVE 21:00 open) との差は既に 41.0 / 19.3p あった**。この事実と整合する仮説は 2 つ: **(H1)** MASSIVE の 21:00 print が pre-open / 他 venue の stale print で OANDA は同価格を一度も提示していない、**(H2)** halt 窓 ~4 分の間に市場 (両 venue) が実際に動いた。MASSIVE 1m 系列が +2m で +39.3 / +9.3p 跳んで以後一定なのは H1 と整合するが **H2 を排除しない** — 本計測は OANDA 初 M1 の **open** しか持たず、pre-open tick・初 M1 の range・後続価格を見ていない (Codex P1 4117990982)。識別は §2 の追加計測 (次 event から EXEC_B に永続、§8) で行う。**決裁に効く含意は H1/H2 で変わらない**: (a) 送信タイミング (+15 分 / poll 短縮 / 22:01) では 21:00 の価格は取り戻せない (DRAFT §3 の結論は維持 — ただし「venue に存在しなかった」とは書かない)、(b) drift 境界を動かしても「tradeable 時点で既に消費された gap の残余」を fade する entry になる (2b/2d の estimand 問題を具体化)、(c) 契約 B の +8.0p 境界は「開場後 drift」を制限するつもりで導出されたが、実装の drift 定義は basis 込みなので **導出と実装で estimand が違う** (§5)。

### 1.3 契約 B 導出時 (packet 2026-09-10 §5.2) の見積りとの突合

- 導出は `wg_gap_drift-2026-09-10.json` の **MASSIVE 内部** adverse drift (+5m、MASSIVE 1m mid − MASSIVE open): 全 48 で +8.0p 抵触 3/48、qualifying・cap 通過 8 で 0/8。**basis (OANDA 初 M1 open − MASSIVE open) は別集計 (`oanda_vs_massive_open_basis_pips` mean 4.82 / p90 10.0 / max 24.6) で、境界判定に足していなかった。**
- 同 json で **fade 方向 adverse basis** (= live drift の in-sample proxy: OANDA 初 M1 open − MASSIVE open。forward 2 件で live drift との差 0.0 / −0.9p) を取る。**分母は engine 確定の qualifying pair-event に限る** (json の MASSIVE 1m 近似は engine 15m と乖離し、08-02 AUD_USD は json 25.7p だが engine 23.0p で no-qualify、08-09 AUD_USD / 06-07 AUD_USD / 05-24 ×3 は live 化前 or 診断行なしで engine 分類が無い — Codex P2 4117897191): **engine 確定 qualifying = 07-26 / 08-02 / 09-06 / 09-13 / 09-27 の USD_JPY 5 event、adverse basis > +8.0p は 3/5** (09-06 +9.7 / 09-13 +41.0 / 09-27 +19.3; 通過 07-26 +2.9 / 08-02 +1.9) → **P(drift 放棄なし) ≈ 0.4 (N=5、点推定のみ)**。参考 (json 近似で拡張: engine 未確定 5 件 = 05-24 ×3 / 06-07 AUD / 08-09 AUD を加えた **10 event**。08-02 AUD は engine no-qualify 確定なので除外): 10 event 中 5 が > +8.0p → **0.50** (上限側の参考値。前版の 6/11 は偽 qualifying 08-02 AUD を含んでいた — Codex P2 4117990995)。packet §5.2 の P(drift 放棄なし) 点 ~0.94 は **MASSIVE 内部 drift の定義でのみ成立する値**。⚠️ 本 packet 初版は「basis + MASSIVE 内部 +5m drift」を足して 7/11 と書いたが、両者は同じ MASSIVE open から測った量で開場ジャンプを二重計上する (09-13 なら 41.0 + 39.3 = 80.3p vs live 41.0p、09-27 は 28.6p vs 18.4p) — Codex P1 4117843802 で撤回。MASSIVE 内部 drift は proxy に使わない (09-27 で 9.3p vs live 18.4p と過小)。
- ⚠️ 注意: json の gap は MASSIVE 1m 近似で engine の 15m 値と乖離する (09-13 AUD_USD: json −27.2 / engine **−14.7 no-qualify**、08-02 AUD 25.7 / 23.0)。**qualify の確定源は engine の診断ログ**、json は basis / drift の計測にのみ使う。live 実測 drift (+41.0 / +18.4) が event の一次値。

---

## 2. 一次データと測定 (2026-09-28、全て read-only)

| データ | 取得 | 保存先 |
|---|---|---|
| event #2 の EXEC_B 全遷移 / 診断行 | Render ログ API (`list_logs`、20:58–21:12Z、text=`WEEKEND_GAP`、27 行、hasMore=false) | §1.1 |
| shadow row 18538 / audit 17930 | 本番 `/api/demo/trades?date_from=2026-09-26&include_shadow=true` / `/api/oanda/audit` | §1.1 |
| 直近 3 週末 (09-13 / 09-20 / 09-27) × 3 ペアの Sunday open drift + OANDA 初 M1 + basis | `tools/wg_gap_drift_measure.py --weekends 3 --date 2026-09-28` (MASSIVE 1m aggs + OANDA M1 candles GET) | `bt-results/wg_gap_drift-2026-09-28.json` |
| 19 週末 × 3 ペア = 57 pair-weekend の basis / 両基準 qualify | 上 json + 09-10 json の単純結合 (再計測なし) | §3 / §5 の表 |
| **未取得 (H1/H2 識別に必要)**: OANDA halt 中の indicative quote 列 (HOLD 行の send_mid は quote_age ~172,9xx s の金曜 quote = OANDA は halt 中 indicative を更新していない)、OANDA 初 M1 candle の **high/low**、tradeable 後 60s の tick、第 2 venue の日曜 21:00 1m | 次 qualifying event から EXEC_B / row reasons に永続 (R3、凍結値不変、§8)。過去 2 event は OANDA candles GET (M1 の high/low、S5) で事後取得可 — 本 PR では未実施 | — |

**look-burn 回避 (厳守)**: 価格のみ。outcome との joint 計算ゼロ、OOS 窓再接触ゼロ (対象は 2026-05-24 以降の 19 週末のみ)。EV への言及は凍結値 (stressed-net +7.90p) からの単純減算のみ。

**basis の全体像 (57 pair-weekend、2026-05-24〜09-27、全て夏時間)**: |basis| mean **6.3p** / median 4.1 / p90 12.1 / max 41.0。ペア別 mean: USD_JPY **8.9** / AUD_USD 7.6 / EUR_USD 2.5。fade 方向 adverse basis > +8.0p は 14/57。**USD_JPY の basis は 09-06 以降 4 週末連続で 9.7 / 41.0 / 17.7 / 19.3p** (05-24〜08-30 の 15 週末は median 4.6 / max 13.5) — 時変・N 小、記述のみ (O-2026-09-28-1 として観測登録、[[daily-observations-2026-09]])。

**両基準 qualify (57 pair-weekend)**: MASSIVE (json 近似) 12 / OANDA 基準 7 / **両方 5** (05-24 ×3 ペア、07-26 USD_JPY、09-06 USD_JPY)。MASSIVE のみ 7 (06-07 AUD / 08-02 USD_JPY・AUD / 08-09 AUD / 09-13 USD_JPY・AUD / 09-27 USD_JPY)、OANDA のみ 2 (07-26 EUR 25.7 / 08-02 EUR 20.5)。

---

## 3. 候補比較 (DRAFT §3 を一次データで確定)

| # | 候補 | 触る凍結値 | 09-13 / 09-27 型への効果 (§1.2 の機構で再評価) | estimand | 起案者評価 |
|---|---|---|---|---|---|
| 1 | 打ち切り +15 分の変更 | `WEEKEND_GAP_HALT_ABANDON_MIN` | **なし** — 2 件とも tradeable 確認済み (開場 +4 分)、放棄理由は drift | 不変 | 据え置き。11-01 DST は `wg-dst-cutoff-basis-r3` (10-25) |
| 2a | drift 境界 +8.0p 据え置き (契約 B 継続) | — | なし。live 定義の drift で qualifying の ~45% が放棄され続ける (§1.3) が、通過した event は estimand 乖離 ≤ 8p の fill になる。F2 期待 fill ≈ 3.5〜4.3 event (N=0 確率 ≈ 1.4〜3%、§5) | entry 価格は不変 (乖離 ≤ 8p) だが **basis ≤ 8p の event に選択される** — この部分集合の EV は凍結 pooled mean から導けない (forward のみ) | **起案者推奨** — ただし packet §6 が「3 度目の観測はしない」と凍結しているので **選ぶなら §6 の撤回を明示決裁 (W1 選択肢 3)** + 11-15 checkpoint (§6) で開放的な「待つ」にしない |
| 2b | drift 境界の引き上げ (12p / 15p / 全 57 p90 12.1p) | `WEEKEND_GAP_DRIFT_ABANDON_PIPS` | 09-27 (+18.4) は 15p でも放棄、09-13 (+41.0) は不可。**救済は実質 2d** | 「tradeable 時点で既に消費された gap の残余」を fade する entry が live 母集団に入る | 中間案の合理性なし。不採用推奨 |
| 2c | gap 比例境界 | 同上 | 0.4×22 = 8.8p → 09-27 も放棄 | packet §4-3 で不採用済み | 不採用維持 |
| 2d | drift 境界の撤廃 (tradeable 確認のみで送信) | 同上 + packet §4-3 削除 | **送信適格化のみ**。09-13 なら OANDA 基準 gap −9.0p、09-27 なら −2.7p を fade する entry = **qualify 閾値 (21.4p) の 1/2〜1/8 の gap を fade** する。下流の cap / pre-send guard / cancel / 送信失敗は残る (DRAFT §3 2d) | **OOS PASS の estimand (Sunday open 価格 entry、gap ≥ 閾値) とは別物**。EV は凍結値から導けない (stressed-net +7.90p は gap ≥ 閾値の母集団の値) | F2 を最速で「live fill N≥1」にする唯一の案だが、**その fill は PASS→live 変換の実証にならない** (W3)。選ぶなら「F2 の解釈変更」を同時決裁 |
| 3b/3c/3d | 送信 22:01 / poll 短縮 / 開場前 pending | packet §4-1 | なし (basis は送信タイミングと無関係)。3d は OANDA halt 中の pending 受理が未確認 | — | 不採用維持 |
| 4 | 指値化 (Sunday open 価格 limit) | stage-2 §2.2 | **なし** — OANDA は MASSIVE open 価格を提示していないので limit は fill しない (09-13: 153.12 の BUY limit に対し OANDA 初値 153.53) | adverse selection | 不採用維持 |
| 5 | シグナル基準の executable 化 (sunday_open = OANDA 初 tradeable mid、shadow も同基準) | シグナル定義 = OOS estimand | 09-13 / 09-27 は **NO-QUALIFY (分母外)** になる = 不成立が消える (救済ではない)。両基準 qualify は 5/57 | **新 family** (OOS verdict は適用不能、fresh forward OOS のみ、N floor 数年)。**shadow の MASSIVE 基準蓄積が止まる = 4原則#3 違反** | shadow まで変える形は **不採用推奨** |
| **5′** | **LIVE 側 OANDA-basis 再 qualify** — shadow は MASSIVE 基準のまま (分母・OOS estimand 保存)、live 転送は「tradeable 確認時の OANDA mid − Fri close が同じ凍結閾値以上」のときのみ (drift 境界 +8.0p は不変) | 新フィルタ (LIVE 転送条件の追加) — qualify 閾値・cap・G1/G2/G3・1000u・4h は不変 | 09-13 / 09-27 は live 分母外 (放棄ではなく NO-QUALIFY(venue))。**fill を生むのは両基準 qualify のときだけ = 5/57 pair-weekend ≈ 1.1 event/月** (直近 19 週末、夏時間) | live 母集団 = 「MASSIVE で qualify ∧ venue でも gap が実在」= OOS estimand の **部分集合** (venue に存在した event に限る) — 変換係数の実証としては最も素直。**shadow 不変で 4原則#3 の非対称 (LIVE 側 winning-location フィルタ) に合致** | **後続 R1 候補** (checkpoint で契約 B が N=0 なら起案)。estimand 純度では最良だが F2 timing で 2a に劣後 (§5)。Rule 1 (新フィルタ) = pre-reg LOCK + 365d 相当の根拠。根拠は価格のみ (OANDA M1 の日曜初足 vs MASSIVE 15m open の basis 履歴) で可だが **OOS 窓 (2022〜2026-06) の価格再接触が要る → W6**。⚠️ 履歴は OANDA **M1 open** を proxy にするが、配備 gate は tradeable **初 tick** の mid で判定する (数秒〜60s の差) — 5/57 は proxy 基準の**機会率**であって配備 gate の率ではない (Codex P1 4117843807、§4-1・§5 の注意) |
| 6 | 契約不変更の forward 観測 (放棄 event の価格系蓄積) | なし | 救済しない。本 PR の card 転記 + json がその第 2 行 | — | **実施済み (R3)**。継続 |
| 7 | packet §6 文言整備 (「正当放棄」/ 単位) | なし | — | — | 本 packet §6 で文言確定 (下記) |

**表の読み方**: 2 件の不成立は「**estimand の entry 価格が tradeable 時点で既に消費されていた**」型 (§1.2、H1 stale print / H2 halt 窓内の実移動 は未識別)。この型に対して契約 B の drift 境界は **正しく作動して負 EV entry を止めた** (drift 境界を外せば gap の 1/2〜1/8 を fade する entry になる)。したがって「契約 B の欠陥」ではなく「**OOS estimand と執行 venue の価格基準のずれ**」が問題で、解は (2d) estimand を live で変える か (5′) venue で estimand が成立した event だけ転送する かの二択。**どちらも F2 を 12-31 までに資料どおり回避する見込みは薄い** (§5)。

---

## 4. AMENDMENT 条項案 (採用候補 5′ のみ、**未承認・LOCK ではない**、W2 で 5′ が選ばれた場合の文言)

**不変更**: シグナル定義 (MASSIVE 15m 日曜初バー open) / qualify 閾値 20.0 / 21.4 / 25.0p / 対象 3 ペア / fade 方向 / entry 窓 / spread cap 10.0p / 1000u / +4h horizon / disaster SL 150p / latch 永続 / shadow 全件記録 / 契約 B §4.1–4.6 (送信前置条件・打ち切り +15 分・drift 境界 +8.0p・halt-race 再送 1 回・slippage 基準・観測強化) / G0・G1・G2・G3 / GBP_USD 永久対象外。

**追加条項 (契約 B §4.1 の直後、live 転送条件として)**:
1. **venue 再 qualify (新設)**: tradeable 確認後の最初の評価 tick で、**§4.3 の drift 判定と同一の quote** (同 tick の OANDA mid) と金曜終値 (engine が gap 計算に用いた `fri_close` と同一値) の差 `gap_venue` を計算し、**|gap_venue| ≥ 当該ペアの凍結 qualify 閾値** かつ符号が MASSIVE gap と同じときのみ live 送信へ進む。満たさなければ latch=`NO_QUALIFY_VENUE`、shadow row は従来どおり記録 (分母保存、reasons に `[WG_VENUE] gap_venue=…p thr=…p` を永続)。
2. **drift 境界との関係**: §4.3 の +8.0p 判定は venue 再 qualify の**後**にそのまま適用 (両方通過で送信)。venue 再 qualify は drift 境界の代替ではない。
3. **観測**: `NO_QUALIFY_VENUE` は G0''/G1/G2/G3 の分母外 (cap skip と同じ扱い)。EXEC_B ログに `gap_venue` を追加。
4. **Rule 1 根拠 (LOCK 前に必須)**: OANDA M1 日曜初足 vs MASSIVE 15m open の basis 履歴を **価格のみ**で 365 日以上 (OOS 窓を含む → W6 で許可が要る) 計測し、(i) 両基準 qualify の event 頻度 (proxy 基準の機会率)、(ii) drift・cap 通過率を掛けた forward 期待 fill N を pre-reg に書く。**EV は pre-reg に書かない** — 凍結 stressed-net +7.90p は OOS qualifying 全体の pooled mean で、venue 選択された部分集合の条件付き mean は basis の減算では導けない (§5、Codex P1 4117990988)。EV は G0''/G2 の forward 実測のみ。**quote 基準の不一致を明示する**: 履歴の OANDA M1 **open** は proxy で、配備 gate は tradeable **初 tick** の mid (数秒〜≤60s 後) — 閾値近傍 (|gap_venue| が閾値 ±(spread/2 + 開場後 60s の p90 変動)) の event は proxy と gate で分類が入れ替わり得るので、頻度は感度帯付きで書き、**EXEC_B ログに tradeable 初 tick mid と当該 M1 open を両方永続**して forward で proxy 誤差を測る (forward 2 件の差は 0.0 / −0.9p)。履歴の 5/57 は「機会率」であって fill 率ではない (Codex P1 4117843807 / 4117843813)。**OOS 窓の outcome には触れない** (両基準 qualify event の 4h PnL を OOS で再集計するのは再接触 = 禁止)。
5. **G0'' (forward、承認時に凍結)**: 5′ 発効後の最初の 2 「両基準 qualify」event で fill 成立 → 通常運用。2 連続不成立 → family live-execution 保留 (3 度目の再審はしない)。

---

## 5. fill 成立率の見積り修正 + estimand コスト (F2 テンプレ、価格のみ)

| 成分 | packet 2026-09-10 §5.2 | 本 packet (live 定義の drift で再評価) |
|---|---|---|
| P(実開場 ≤ open+15m) | 48/48 | **57/57** (09-13 / 09-20 / 09-27 も初 M1 21:04)。不変 |
| P(drift 放棄なし \| qualifying) | 点 ~0.94 (MASSIVE 内部 +5m drift、qualifying 0/8 抵触) | **live 定義 (basis proxy)、engine 確定 qualifying 5 event 中 3 が > +8.0p → 点 ~0.4** (07-26 / 08-02 通過、09-06 / 09-13 / 09-27 放棄、N=5、区間は出さない)。json 近似で拡張した 10 event (engine 未確定 5 件込み、08-02 AUD は除外) では 5/10 通過 → ~0.50 を上限側参考値とする。⚠️ 導出時の 0/8 は drift の定義が live と違っていた (§1.3)。初版の 7/11 (~0.36) は二重計上で撤回、2 版の 5/11 は json 分母 (08-02 AUD 等の偽 qualifying を含む) で撤回 |
| 総合 P(fill \| qualifying) | 点 ~0.94 / 保守 ~0.75 | **点 ~0.35–0.43** = 0.4〜0.5 (drift) × 0.85 (cap 通過) × ~1.0 (tradeable 確認済み + halt-race 再送、送信失敗は forward で計測) |
| qualifying 頻度 (直近 19 週末、engine 確定分) | 3.3 event/月 (凍結 OOS report) | 契約 B 発効 (09-10) 後 3 週末 (09-13 / 09-20 / 09-27) で qualifying **2** pair-event (09-13 / 09-27 USD_JPY、いずれも G0' event)、09-20 は NO-QUALIFY。頻度の再推定はしない (N 小) |
| **F2 (12-31 live N≥1) 見込み** | N≈8–11 | **契約 B 継続 (2a)**: 残 ~3.1 ヶ月 × **3.28 qualifying pair-event/月** (凍結 stage-2 prereg §1、週末単位 0.48 ではなく pair-event 単位 — 同一週末の複数ペア qualify を数える、Codex P2 4117897187; 契約 B 下 3 週末で 2 pair-event ≈ 2.9/月は整合) ≈ 10 pair-event × 0.4〜0.5 drift 通過 × ~0.85 cap 通過 ≈ **3.5〜4.3 event**、N=0 で終わる確率 ≈ 3〜1.4% (Poisson)。fill する event は「basis ≤ 8p」に選択される (entry 価格の乖離上限 = 8p、EV は forward のみ) / **5′**: 両基準 qualify は**機会率** 5/57 ≈ 1.1/月 (proxy 基準)。§4 は +8.0p drift 境界 → cap → 送信を残すので fill はさらに掛かる: in-sample 両基準 5 件のうち adverse basis > 8p は 1 件 (09-06 USD_JPY +9.7) → drift 通過 ~0.8、cap ~0.85 → **fill ≈ 0.75/月**。3 ヶ月 ≈ 2.2 event から Rule 1 全段 (pre-reg + 計測 + 実装 + review) 3–4 週を引くと **実効 ~1.4 event**、N=0 確率 ≈ 25% (Codex P1 4117843813 で fill 率と機会率を分離) / **2d**: 送信適格 event ≈ qualify 全件 × cap 通過 → 最速で N≥1 だが **その fill は OOS estimand の外** |

**estimand コスト (正直な会計)**: 契約 B の実効 EV は packet §5.3 の「+7.90p − 3.15p ≈ +4.75p/event」から **live 定義の drift 分布** で再計算が要るが、**本 packet は EV の下限も点推定も出さない**: 凍結 stressed-net +7.90p は OOS qualifying 母集団全体の pooled mean であって、drift 境界が選択する「basis ≤ 8p の部分集合」の条件付き mean でも per-event の最小値でもない (Codex P1 4117897184 — 初版の「> −0.1p/event の下限」は撤回)。選択された部分集合の 4h リターンは系統的に異なり得る (basis 小 = MASSIVE と OANDA の日曜初値が近い週末 = gap の性質自体が違う可能性) ので、**契約 B の EV は G2/G3 の forward 実測のみが答える** (それが F2 の要求)。5′ の両基準 qualify event も同じ理由で EV は forward のみ。2d は母集団が OOS の外で減算自体が定義できない。

**測定の限界**: (i) 57 pair-weekend は全て夏時間 — 冬時間 (11-01〜) は `wg-dst-cutoff-basis-r3` (10-25) で 22:04 開場を確認するまで別レジーム。(ii) json の MASSIVE gap は 1m 近似で engine の 15m と乖離しうる (§1.3)。(iii) basis は OANDA **初 M1 candle の open** で、live が見る tradeable 初 tick の mid とは数秒〜数十秒ずれる (09-13 は差 0.0p、09-27 は −0.9p)。(iv) USD_JPY basis の 9 月拡大 (§2) が MASSIVE 側のデータ品質変化か venue 側かは未特定 — MASSIVE 日曜 21:00 バーの provenance (どの venue の print か) は本 packet では調べていない (W6 の計測に含める)。

---

## 6. 採用/棄却境界 (forward、承認時に凍結) + packet 2026-09-10 §6 の文言確定

| 判定点 | 境界 | アクション |
|---|---|---|
| **G0' (契約 B、改定後最初の 2 qualifying pair-event)** | **09-13 / 09-27 の 2 件とも不成立 → 終了・発動** (本 packet)。event #3 は存在しない | R1 再審 (本 packet)。**契約 B は決裁まで fail-closed で継続** (放棄は記録のみ、G0' には数えない、rolling gate は未承認) |
| W1 決裁 | 不成立 2 件目 (09-27) + 7 日 = **2026-10-04** までに user 決裁 (registry `wg-execution-modality-r1-packet-v1-w1-decision`) | 未決なら契約 B 継続 + 週次 event 転記 (候補 6) のみ。**「観測して待つ」の 3 度目に当たるため、未決の継続は明示決裁 (W1 選択肢 3) として記録する** |
| **W1 (3) 契約 B 継続 採用時の checkpoint (新設、承認時に凍結)** | **2026-11-15** までに契約 B 下の qualifying pair-event が ≥3 件追加 (累計 ≥5) で live fill N=0、または 12-31 F2 到来 | 5′ (venue 再 qualify) の R1 起案へ自動移行 (W6 の計測を先行して許可しておく) — 「待つ」に終端を付ける。fill N≥1 なら G0'' 相当の配管確認 (手順 (1)–(5)) を当該 fill で実施し F2 を明示 resolve |
| 5′ 採用時 G0'' | 発効後最初の 2 両基準 qualify event | fill 成立 → 通常運用 / 2 連続不成立 → family live-execution 保留 (再審はしない) |
| 冬時間初週末 2026-11-01 | 実開場 22:04–22:05 から >±10 分の乖離 | R3 打ち切り時刻再導出 (`wg-dst-cutoff-basis-r3`) |
| G1/G2/G3 | 不変更 | 不変更 |
| F2 (meta-audit §6) | 2026-12-31 live N=0 | 従来どおり発動 — 本 packet はその回避手段の再審であって免除ではない |

**文言確定 (packet 2026-09-10 §6 row 1/2 の「正当放棄」と「drift 放棄」の矛盾、DRAFT §2 末尾)**: 運用どおり **drift / halt 放棄 = 不成立、cap skip (`SKIPPED_SPREAD`) のみ = 正当な未執行**。5′ 採用時は `NO_QUALIFY_VENUE` も正当な未執行 (分母外)。判定単位 = pair-event。

---

## 7. registry 変更 (本 PR で反映)

1. `weekend-gap-execution-amendment-g0prime`: **resolved 2026-09-28** — event #2 不成立で G0' 終了・§6 発動。message に 09-27 実測を追記。
2. **新規** `wg-execution-modality-r1-packet-v1-w1-decision` (deadline_info、**2026-10-04**、doc = 本 packet): W1〜W6 の user 決裁点。user 専権 — autopilot は繰越・代行決裁不可。
3. `project-falsification-f2-wg-live-conversion`: message に「09-27 ABANDONED_DRIFT、live fill 通算 0/5、契約 B 下 0/2、R1 再審発動 (本 packet)」を追記 (閾値・deadline 12-31 不変、**resolve しない**)。
4. `weekend-gap-live-g1-slippage` / `g2-cumloss`: 変更なし (live N=0 のまま)。

---

## 8. 実装チェックリスト (5′ 採用時の別 PR — 本 PR ではコード不変更)

- [ ] W6 許可後: `tools/wg_venue_basis_history.py` (新規 read-only) — OANDA M1 日曜初足 (v20 candles GET) × MASSIVE 15m 日曜初バー open の basis を 2022-01〜 で計測 (**価格のみ、outcome 列を読み込まない実装**、OOS 窓の 4h 結果は触らない)。出力 `bt-results/wg_venue_basis-<date>.json`
- [ ] pre-reg LOCK 文書 (`weekend-gap-venue-requalify-prereg-<date>.md`): §4 条項、両基準 qualify 頻度、forward N 見込み、G0'' 境界、禁止事項
- [ ] `strategies/daytrade/weekend_gap_fade.py`: `gap_venue` 計算 + `NO_QUALIFY_VENUE` latch + `[WG_VENUE]` reasons + EXEC_B ログ拡張。凍結値は import 済み定数を再利用 (閾値の二重定義禁止)
- [ ] `tests/test_weekend_gap_execution_contract_b.py` 拡張: venue 再 qualify 境界 (閾値ちょうど / 符号不一致 / quote 取得不能 fail-closed) + **counterfactual kill pin** (再 qualify を外すと 09-13 型の fixture で送信判定に到達することを実証)
- [ ] registry: G0'' エントリ新設 + F2 message 追記 + 本エントリ resolve
- [ ] pre-reg 突合チェックリスト (stage-2 §8 様式) を実装 PR 本文に添付。市場安全窓 (日曜 20:00–22:30Z 除外) でデプロイ
- [ ] **H1/H2 識別計測 (R3、W1 の結論に依らず次 qualifying event から)**: EXEC_B / row reasons に (a) tradeable 直前の最終 indicative quote (quote_age 付き)、(b) OANDA 初 M1 candle の open/high/low (candles GET、事後)、(c) tradeable 後 60s の tick 数点 を永続。過去 2 event は OANDA M1/S5 candles で事後取得して packet §1.2 に追記。第 2 venue 1m が取れれば MASSIVE 21:00 print と突合

---

## 9. user 承認が必要な点 (W1〜W6)

| id | 問い | 選択肢 | 起案者推奨 |
|---|---|---|---|
| **W1** | R1 再審起案の承認 | (1) 起案する (本 packet §3 の候補を審議) / (2) family live-execution 保留 (shadow 蓄積のみ継続) / (3) 契約 B 継続 = packet §6「3 度目はしない」の撤回を明示決裁 + §6 の 11-15 checkpoint を凍結 | **(3)** — 契約 B は設計どおり作動し、不成立は modality ではなく estimand-venue basis の問題 (§1.2)。F2 期待 fill は 2a が最大 (§5、pair-event 率基準)。EV は forward のみ (pooled mean からの下限は撤回) |
| **W2** | 候補の選択 (§3、W1=(1) の場合) | 2a / 2b / 2d / 5 / 5′ / 6 のみ (1・2c・3・4 は不採用維持) | W1=(3) なら 2a + 6。W1=(1) なら **5′** (shadow 不変・4原則#3 整合・OOS estimand の部分集合) — ただし F2 timing では 2a に劣後 (実効 ~1.4 vs ~3.5〜4.3 event、§5) |
| **W3** | F2「PASS→live 変換の実証」の解釈 | (a) Sunday open 基準 (MASSIVE) estimand の live fill のみ / (b) venue で estimand が成立した event (5′) の fill を含む / (c) executable 基準 (2d) の fill も含む | (b)。(c) を選ぶなら F2 は別の命題になる |
| **W4** | 4原則#3 の解釈 — drift 境界・venue 再 qualify は「勝てる場所で勝つ条件だけ転送する LIVE 側フィルタ」か | 裁定 | 該当する (shadow 不変が条件) |
| **W5** | 混在週末の event #2 裁定 | — | **不要** (09-27 は単一クラス) |
| **W6** | 5′ の Rule 1 根拠計測のための **OOS 窓 (2022-01〜2026-06) の価格再接触** (basis 履歴のみ、outcome 非読込) を許可するか | 許可 / 不許可 (forward のみで N を積む → LOCK まで数ヶ月) | 許可 (W1=(3) でも checkpoint 移行に備えて先行計測。outcome 列を読まない実装 + 敵対的レビューで担保) |

---

## 禁止事項 (継続)

OOS 窓の outcome 再接触・再集計 / shadow outcome の転記 / G1・G2 の中間計算 / qualify 閾値・cap・G1/G2/G3・契約 B 凍結値の autopilot 変更 / near-miss を理由にした閾値再計算 / 「live fill 0/5 累計」型の改定前後混在カウントで契約 B を評価すること (契約 B 下は 0/2) / 本 packet を LOCK・決裁済みとして引用すること / watcher の `TRIGGERED` を F2 resolved と読むこと / G0' 終了後の放棄 event を G0' に数えること (rolling gate 未承認) / 5′ を「F2 を救う案」として引用すること (§5: 機会 1.1/月・fill ≈ 0.75/月、実効 ~1.4 event) / 5/57 を fill 率として引用すること (機会率、proxy 基準) / 「basis + MASSIVE 内部 drift」を live drift の近似として使うこと (二重計上、§1.3) / json の MASSIVE 1m 近似で qualify を分類すること (確定源は engine 診断行、§1.3) / 凍結 pooled mean +7.90p から選択部分集合の EV 下限を導くこと (§5)。

## 参照

- [[weekend-gap-execution-modality-r1-redraft-DRAFT-2026-09-22]] (骨子、本 packet で昇格。archive はしない — §2/§3/§6/§7 の規則は本 packet が引き継ぐ)
- [[weekend-gap-execution-contract-r1-packet-2026-09-10]] (契約 B、§6 の事前コミット)
- [[weekend-gap-stage2-execution-prereg-2026-07-24]] / [[weekend-gap-oos-prereg-2026-07-24]] (凍結 estimand)
- [[weekend-gap-fade]] (イベントログ 09-27 節) / [[daily-observations-2026-09]] O-2026-09-28-1 / [[process-meta-audit-2026-09-07]] §6 F2
- `bt-results/wg_gap_drift-2026-09-28.json` / `bt-results/wg_gap_drift-2026-09-10.json`
- MEMORY: `project_weekend_gap_fade_live_2026_07_25` / `feedback_check_the_symmetric_side_2026_09_19` (導出と実装の drift 定義の不一致 = 対称側の未確認)
