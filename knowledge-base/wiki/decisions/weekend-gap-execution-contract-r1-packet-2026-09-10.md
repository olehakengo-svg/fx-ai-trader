# weekend_gap 執行契約 R1 改定パケット (2026-09-10)

> **Status: 📋 DRAFT — user 決裁待ち (R1)。決裁期限: 2026-09-12 (土) 中 — 次イベント 2026-09-13 (日) 21:00 UTC の前に実装 PR + deploy を完了するため。**
> 起点: [[process-meta-audit-2026-09-07]] §4.2 R1(b) 勧告 + §6 F2 (2026-12-31 までに live 執行 N=0 なら「PASS→live PnL」変換未実証と正式認定)。user 09-10 「全て進めて」承認によるパケット起案。
> 本パケットは**文書のみ** — live コード変更なし。実装は user 承認後の別 PR (レビュー必須)。
> rule:R3 (観測は read-only 実測、契約変更本体は R1 = user 最終承認)

---

## 0. 決裁サマリ (user 向け 3 行)

1. **何が壊れているか**: 唯一の OOS 確定 PASS セル weekend_gap_fade が live 化 (07-25) 以降 **live 約定 0/3 イベント**。機構は確定 — エンジンは日曜 21:01 UTC に発火するが、**OANDA の実開場は毎週 21:04–21:05** (直近 16 週末 × 3 ペア = 48/48 で初 M1 バー 21:04、09-06 は tx 実測で 21:04:58 解除)。FOK 1 回・リトライ禁止の現行契約では**構造的に fill 率 ≈ 0%**。
2. **何を変えるか (推奨案 B)**: エントリー送信を「**OANDA tradeable 確認後の最初の評価 tick**」(実測 ~21:05、凍結 pre-reg §2.2 の目標時刻 21:05±2 分の字義に整合) へ繰り下げ。打ち切り (open+15 分) と gap 先行 fade 時の放棄境界 (+8.0p) を凍結値で併設。**G1/G2/G3 ゲート・qualify 閾値・cap 10.0p・1000u・4h exit は一切不変更**。
3. **見積り**: 改定後 fill 成立率 **点推定 ~94% / 保守 (Wilson95 weekend-block LB) ~75%** (現行 ~0%)。エントリー繰下げの estimand コスト実測 = qualifying・cap 通過週末 (N=8) で **mean +3.15p** → 実効 EV ≈ **+4.75p/event** (凍結 stressed-net +7.90p 基準、tail は §5.3)。月 ~3 イベントで G2 (N=12) 到達 ~2027-01、**F2 期限 (12-31) までに N≈8–11 見込み = F2 失敗を回避**。

---

## 1. 故障の機構特定 (live 0/3 の執行レイヤ分解)

### 1.1 イベント別 root cause (全て一次データで確定)

| # | 日付 | ペア | 執行レイヤの事実 | root cause 分類 |
|---|---|---|---|---|
| ① | 2026-07-26 | USD_JPY | OANDA 送信前に `_is_xau_inst` UnboundLocalError でクラッシュ (04-10 から chronic、07-28 修復済み + regression pin) | **インフラ障害** (執行契約の証拠にならない、G 分母外) |
| ② | 2026-08-02 | USD_JPY | 21:01:27.9Z 送信 → **tx 549257 MARKET_ORDER / tx 549258 ORDER_CANCEL reason=`MARKET_HALTED`** (同 ms)。row 14996: signal 157.469、shadow 化 | **OANDA 実開場前送信** |
| ③ | 2026-09-06 | USD_JPY | 21:01:12.0Z 送信 (oanda_audit #16503 `bridge_status=sent`, is_live=true, 1000u BUY) → **tx 837792 MARKET_ORDER / tx 837793 ORDER_CANCEL reason=`MARKET_HALTED`**。row 17179: signal 156.269、spread_at_entry 3.1p (cap 通過)、shadow horizon −35.4p | **OANDA 実開場前送信 (②と同一機構)** |

③ の「fill なし」の実体 (本パケットで一次確定、2026-09-10 read-only 実査): **シグナル成立・ガードチェーン通過・live 送信成功・FOK 注文作成まで正常 — broker 側が市場 halt 中で即時 cancel**。送信失敗でもシグナル不成立でもない。さらに tx 837767–837941 (同日 21:00:37–21:04 台) は**別トレードの TRADE_CLOSE リトライも全て MARKET_HALTED で cancel され続け、21:04:58.2Z (tx 837943) に初めて fill** — halt 解除時刻の直接実測。

### 1.2 機構 (コード + broker 実測)

```
エンジン発火:  Sun 21:01:1x UTC (2/2 イベントで一致)
  ← MASSIVE 15m forming bar (21:00 stamped) が 21:00 台に取得可能
  ← scoped Sunday runner (demo_trader._weekend_gap_tick) は market-closed gate より前に評価
  ← 送信は _tick_entry 共有ガード → bridge max_attempts=1 (pre-reg §2.2 リトライ禁止)、FOK
OANDA 実開場: Sun 21:04–21:05 UTC (毎週固定)
  ← 直近 16 週末 × 3 ペア = 48/48 で初 complete M1 バー = 21:04 stamped (bt-results/wg_gap_drift-2026-09-10.json)
  ← 12 週末実測 (reports/sunday_open_spread-2026-07-24.md) でも「全週末で初 M1 = 21:04」— 当時から既知の事実だった
  ← 09-06 実測: halt 解除 21:04:58 (tx 837943)
⇒ 送信 (21:01) < 実開場 (21:05) が毎週成立 → MARKET_HALTED cancel が決定論的に発生
```

**結論**: live fill 0 は確率的な不運ではなく**契約の構造欠陥**。stage-2 pre-reg §2.2 は「目標 21:05±2 分」と書いたが、実装はデータソース (MASSIVE) の先行により 21:01 に発火し、OANDA の実開場 (21:04:58) より常に早い。08-05 決裁時の残存仮説「大 gap ほど FOK 不成立」は棄却 — gap サイズと無関係に、開場前送信は必ず cancel される。FOK→IOC も無効 (halt は注文タイプ以前の問題、08-05 確定済み)。

**副次欠陥 (同根)**: 現行の spread cap 判定は halt 中の indicative quote に基づく — ③ で記録された 3.1p に対し、OANDA 実開場初バーの実 spread は 6.1p。改定案 B は cap 判定も実 quote 化する (§4)。

## 2. 一次データと測定 (2026-09-10 実施、全て read-only)

| データ | 取得方法 | 保存先 |
|---|---|---|
| ③ の row / audit | 本番 `/api/demo/trades` `/api/oanda/audit` GET | 本文 §1.1 |
| ②③ の cancel reason | 本番 `/api/oanda/transactions` GET (idrange 二分探索) | 本文 §1.1 |
| OANDA 実開場時刻 + Sunday open 後ドリフト | **新規 read-only ツール `tools/wg_gap_drift_measure.py`** — 直近 16 週末 (2026-05-24〜09-06) × 3 ペア、MASSIVE 1m aggs + OANDA M1 candles GET | `bt-results/wg_gap_drift-2026-09-10.json` |

**look-burn 回避 (厳守済み)**: 測定は価格データのみ。戦略 outcome (4h PnL/WR/EV) との新規 joint 計算はゼロ。OOS 窓 (凍結統計) の再集計もゼロ — 対象は直近 16 週末のみ。EV への言及は全て凍結値 (stressed-net +7.90p 等) からの単純減算。

## 3. 改定案の比較 (執行契約の設計空間)

| 観点 | **(A) halt 検出時の限定リトライ** (bridge 内で MARKET_HALTED cancel 時のみ 30s×最大 8 回再送) | **(B) エントリー繰り下げ (推奨)** (OANDA tradeable 確認後に送信、scoped runner 側) | (C) FOK→別 TIF (IOC / 指値 GTD) |
|---|---|---|---|
| fill 成立率見積り | ~94% (halt 解除 21:05 を 30s 以内に捕捉) | **~94% (同左 — poll 30–60s 間隔で解除後 0–60s に送信)** | **~0%** — halt 中は注文タイプ無関係 (08-05 tx 実測で確定)。指値 GTD は fill 特性が estimand 外 (adverse selection、pre-reg §2.2 で既却下) |
| estimand 保存 | entry ≈ open+4–5.5 分。OOS entry (21:00 open 価格) は元々 OANDA で約定不能 — 実行可能な最近接点 | **同左 (A と同時刻)** + 凍結 pre-reg §2.2 の目標時刻「21:05±2 分」の字義に一致 | — |
| **G1 ゲート整合 (+2.0p 凍結)** | ❌ **G1 を汚染する**: slippage 基準 (`slippage_signal_price_basis="entry_fill"`、2026-07-25 review fix) は「送信時 quote」— bridge 内リトライは初回 21:01 quote を signal_price に固定したまま 21:05 に fill するため、**4 分のドリフト (qualifying mean +3.15p) が G1 に混入し、真の slippage ゼロでも N=6 で恒久誤停止する** (07-25 に潰した half-spread 混入バグの同型) | ✅ **G1 校正を保存**: 送信自体が 21:05 に移るため、signal_price = 送信時 quote → G1 は純粋な fill slippage のみを測る (凍結 semantics「spread とは独立」どおり)。繰下げドリフトは G1 に入らず、per-event 放棄境界 (+8.0p、§4) と G2 (cum −60p、不変更) が防ぐ | — |
| 実装面 | bridge 深部 (リトライ + cancel reason 分岐 + quote 再読) の変更 — 全戦略共有経路に触る | **scoped runner (`_weekend_gap_tick`) に前置条件 1 つ追加** — wg 専用経路のみ、共有ガードチェーン不変。tradeable 確認は既存 read-only pricing GET | client 1 行だが無効 |
| DST 頑健性 | 冬 22:04 開場にも自然対応 | **同左 (tradeable poll は時計に依存しない)** | — |
| リスク | 再送 race での二重約定は FOK cancel 確認で排除可能だが、検証面が広い | halt 解除直後の race で 1 回だけ cancel を踏む可能性 (~数十秒の残存窓) → §4 の限定再送 1 回で吸収 | — |

**判定: (B) 採用を推奨、(C) 棄却、(A) は (B) の残存 race 用の限定再送 (1 回) としてのみ内包。** 決定的根拠は G1 整合 — (A) 単独は G1 の estimand (「送信時 quote に対する fill の逸脱」) を壊し、07-25 に修正済みの誤発火バグを別経路で再導入する。

## 4. 推奨案 B — pre-reg AMENDMENT 草案 ([[weekend-gap-stage2-execution-prereg-2026-07-24]] §2.2 置換)

**不変更 (凍結のまま)**: シグナル定義・qualify 閾値・対象 3 ペア・fade 方向・entry 窓 4 bars / spread cap 10.0p / 1000u 固定 / exit +4h horizon / disaster SL 150p / latch 永続 / **G0・G1 (+2.0p)・G2 (−60p)・G3 の全ゲート定義と閾値** / GBP_USD 永久対象外 / shadow 全件記録 (分母保存)。

**§2.2 改定条項 (承認時にこの文言で LOCK)**:

1. **送信前置条件 (新設)**: シグナル成立後、live 送信は **OANDA 実開場確認後の最初の評価 tick** まで保留する。実開場確認 = OANDA pricing の当該 instrument `tradeable` 状態 (poll 間隔 ≤60s、quote age <10s)。保留中は latch を立てない (検出は entry 窓ガードの下で継続)。
2. **打ち切り (新設・凍結値)**: Sunday open 初バー ts + **15 分** を過ぎても halt 継続 → 当該ペアの live 執行を放棄し latch=`ABANDONED_HALT`、shadow row は従来どおり記録 (分母保存)。根拠: 実測 48/48 で開場 ≤ +5 分 — +15 分は 3 倍マージン。それを超える halt は異常週末 = OOS 未検証領域。
3. **放棄境界 (新設・凍結値)**: 送信直前の fade 方向 adverse drift (送信時 mid − シグナル mid、fade 方向を正) > **+8.0p** → live 執行を放棄し latch=`ABANDONED_DRIFT`、shadow row 記録。根拠: 凍結 stressed-net mean +7.90p を全消しする水準 ≈ 全週末実測ドリフト p90 (6.7p) + マージン。実測では qualifying・cap 通過 8 週末の抵触 0 件 (§5.2)。gap 比例境界 (0.4×|gap| 等) はパラメータ面拡大のため不採用。
4. **限定再送 (新設・凍結値)**: 前置条件通過後の FOK 送信が `MARKET_HALTED` cancel で返った場合 (解除直後 race) に限り、**30 秒後に 1 回だけ再送可** (最大計 2 送信、いずれも FOK・cancel transaction 確認済みの場合のみ = 二重約定構造なし)。他の cancel/エラー reason は従来どおり再送禁止。
5. **slippage 基準 (semantics 確認、変更なし)**: G1 入力は「**実際に fill した送信 attempt の直前 quote** vs fill」— 07-25 fix の意図 (spread/ドリフト独立の純 slippage) を維持。
6. **観測強化 (新設、08-05 followup (iii) の履行)**: 送信 attempt ごとに halt/tradeable 状態・quote age・送信時 mid・シグナル mid からの drift (pips) をログ + demo row に永続化。cap 判定は実開場後 quote で行う (indicative quote による判定を廃止)。
7. **G0 の読み替え不要の確認**: 発火時刻仕様 21:05±5m (冬 22:05±5m) は改定後の実送信時刻 (~21:05–21:07) を含む — G0 文言は不変更で成立。exit は entry+4h のまま (≈ 01:05–01:22 UTC、通常 spread 帯)。

**禁止事項の継続**: OOS 再接触・再集計 / qualify 閾値・cap・G1/G2/G3 凍結値の変更 / スプレッド低下待ちの条件付け (本改定は「約定可能性」の条件であり spread 条件ではない — cap 10.0p が引き続き唯一の spread 判定) / BE/Trail/TP 追加 / GBP_USD 拡張。

## 5. fill 成立率の事前見積り (F2 テンプレ初適用 — 価格データのみ、outcome 非結合)

### 5.1 現行契約 (ベースライン)

- 送達イベント 2/2 とも MARKET_HALTED cancel (①はインフラ障害で送達前)。発火 21:01 (実測 2/2) vs 実開場 21:04–21:05 (48/48 + tx 実測) → **P(fill) ≈ 0** (デプロイ遅延等で偶発的に 21:05 以降へずれた場合のみ fill し得る)。

### 5.2 改定後 (案 B)

| 成分 | 実測 | 見積り |
|---|---|---|
| P(実開場 ≤ open+15m) | 48/48 pair-weekend (16 週末、2026-05-24〜09-06、全て夏時間) + 09-06 tx 実測 21:04:58。全サンプルで初 M1 = 21:04 | 点 ~1.00 / **Wilson95 LB 0.926** (pair-event N=48)、**0.806** (weekend-block N=16、保守) |
| P(drift 放棄なし \| +8.0p 境界) | qualifying・cap 通過 8 週末で抵触 0/8。全 48 pair-weekend では 3/48 (6.2%) 抵触 | 点 ~0.94 (全週末ベース、保守側) |
| **総合 P(fill)** | — | **点推定 ~0.94 / 保守 ~0.75** (0.806 × 0.94)。現行 ~0 → 改定で fill 転換 |

**頻度への含意**: ~3.3 qualifying イベント/月 × fill ~0.9 × cap skip 10–20% → live 執行 ~2.4–2.9/月。**G2 (live N=12) 到達 ~2027-01、F2 期限 2026-12-31 時点で live N ≈ 8–11 見込み** — F2 の「N=0 のまま」条件を回避できる唯一の経路。

### 5.3 estimand コスト (繰下げの正直な会計)

- 直近 16 週末の qualifying 9 件中 cap 通過 8 件の **open→+5m fade 方向 adverse drift: mean +3.15p / p50 +4.6p** (bt-results/wg_gap_drift-2026-09-10.json)。→ 実効 EV ≈ 凍結 stressed-net mean **+7.90p − 3.15p ≈ +4.75p/event**。
- **tail 開示**: 全週末 +5m adverse drift p90 = 6.7p → tail 週末の実効 EV ≈ +1.2p、p90 RT (凍結 +3.26p 会計) と重なると負圏があり得る。防波堤 = +8.0p 放棄境界 (per-event 上限) + G1 (純 slippage) + G2 (cum −60p) — いずれも凍結値のまま。
- **選択肢の非対称**: 現行契約の EV 捕捉は 0 (fill しない)。案 B は mean 基準で per-event EV の ~60% を回収する。「21:00 open 価格での entry」という OOS 上の estimand は **OANDA では最初から約定不能だった**ことが本測定の主結果であり、案 B は「実行可能な最近接 estimand」への写像。真の変換係数は G2/G3 の forward 実測が最終判定する (それが F2 の要求そのもの)。
- 測定の限界: (i) 16 週末は全て夏時間 — 冬時間初週末 (11 月) は常設 gate (月次 `tools/sunday_open_spread_measure.py` re-run) で実測し、開場 22:04–22:05 を確認するまで冬の初回イベントは G0 相当の注視対象。(ii) qualifying サブセット N=8 は小 — mean ±(セッション内バラつき大)。(iii) MASSIVE 1m 近似のため engine の 15m 計算と gap 値が数 p ずれる週末がある (08-02 AUD: engine 23.0p vs 1m 近似 25.7p) — drift 測定は Sunday バー内の相対値のみ使うため影響なし。

## 6. 採用/棄却境界 (forward、承認時に凍結)

| 判定点 | 境界 | アクション |
|---|---|---|
| 改定後の最初の 2 qualifying イベント | fill 成立 (cap skip / 正当放棄を除く) | 成立 → G0' 配管確認完了、通常運用へ |
| 同上 | **2 イベント連続で fill 不成立** (halt >15m / drift 放棄 / 新種 cancel) | 執行モダリティ自体を再審 (R1 再起案 or family live-execution 保留) — 3 度目の「観測して待つ」はしない |
| 冬時間初週末 (2026-11-01) | 実開場が 22:04–22:05 から大きく乖離 (>±10 分) | R3 で打ち切り時刻の再導出 (凍結値変更は R1) |
| G1/G2/G3 | **従来どおり (不変更)** | 従来どおり |
| F2 (meta-audit §6) | 2026-12-31 live N=0 | 従来どおり発動 — 本改定はその回避手段であって免除ではない |

## 7. registry 変更提案 (⚠️ 本 PR では registry ファイル不変更 — 実装 PR で反映)

1. `weekend-gap-live-g1-slippage` / `weekend-gap-live-g2-cumloss`: message に「2026-09-1x 執行契約 AMENDMENT (エントリー = OANDA 実開場確認後) 発効、live N カウントは発効後 fill から開始。G1 の slippage 基準 = 実 fill attempt 直前 quote」を追記 (閾値・deadline 不変)。
2. 新規エントリ `weekend-gap-execution-amendment-g0prime` (提案): deadline 2026-09-28 — 改定後最初の 2 qualifying イベントの G0' 検証 (送信時刻 = 実開場 +0〜2 分 / halt 状態記録 / latch 新値 / fill or 正当放棄の分類) を週次監査で確認。
3. `volstate-split-weekend-gap-recheck`: 変更不要 (N 到達が前提のため、本改定はその前提を回復するのみ)。

## 8. 実装チェックリスト (承認後の別 PR — 本 PR ではコード不変更)

- [ ] `_weekend_gap_tick`: tradeable 前置条件 (pricing GET、poll ≤60s) + 打ち切り +15m + drift 放棄 +8.0p + latch 新値 (`ABANDONED_HALT`/`ABANDONED_DRIFT`)
- [ ] bridge: MARKET_HALTED cancel 時の限定再送 1 回 (wg entry_type のみ、cancel tx 確認済みのみ、30s 後、FOK 維持)。slippage 基準 = 実 fill attempt 直前 quote
- [ ] 観測: 送信 attempt ごとの halt/tradeable/quote-age/drift 永続化、cap 判定の実 quote 化
- [ ] `tests/test_weekend_gap_fade.py` 拡張: 前置条件 / 打ち切り / 放棄境界 / 再送 1 回上限 / G1 基準の pin
- [ ] KB 同コミット: 戦略カード §執行仕様 + 本パケット Status 更新 + registry §7 反映
- [ ] pre-reg 突合チェックリストを実装 PR 本文に付す (stage-2 §8 様式)

## 参照

- 一次データ: 本番 tx 549257/549258 (08-02)・837792/837793・837943 (09-06)、oanda_audit #16503、demo rows 14996/17179 (§1.1)
- 実測: `bt-results/wg_gap_drift-2026-09-10.json` (16 週末 × 3 ペア) / `tools/wg_gap_drift_measure.py` (read-only、本 PR 同梱) / `reports/sunday_open_spread-2026-07-24.md` (凍結 12 週末: 初 M1 = 21:04 の先行観測)
- pre-reg: [[weekend-gap-stage2-execution-prereg-2026-07-24]] (AMENDMENT 対象) / [[weekend-gap-oos-prereg-2026-07-24]] (OOS verdict、不変更)
- 勧告: [[process-meta-audit-2026-09-07]] §4.2 R1(b)・§6 F2 / 戦略カード [[weekend-gap-fade]] イベントログ / MEMORY `project_live_fill_estimand_shadow_conflation_2026_09_03` (fill 検知の estimand 教訓)
