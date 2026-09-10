# sweep_reversion_eurgbp_late — P-S1(a) HTF Exemption R1 決裁パケット

**Status: 🟢 条件付き承認 (user 決裁 2026-07-24) — 執行待ち (unique バー N=8/10、live 変更は未発生)**
起案: Claude 2026-07-24 / rule:R1 (live 経路の filter 変更 = Slow & Strict)
決裁トリガ: [[t8-week1-gate-breach-2026-07-06]] Forensic #1 DEFER 裁定の機械的決定点 (rescued shadow N≥10)

> **決裁記録 (2026-07-24)**: 本パケットの推奨アクション提示に対し user 「進めて」。以下を承認として記録:
> ① **Option B 条件付き承認** — 執行条件 = unique N≥10 到達 ∧ spaced EV>0。到達時は §3.3 の単一 PR
> (min-spacing + exemption + pin 解除 + 再ゲート、Codex review 必須) で再決裁なしに執行。spaced EV≤0 なら
> Option C (retire) — T8 DEFER の機械的規定どおり
> ② **計数意味論 = unique バー基準** (§1.4) — registry `count_basis: "unique"` に反映済み
> ③ **exit 整合 = 案 (i) 既定** (本番 exit のまま復帰、live N≥10 蓄積後に (ii) を再決裁)
> ④ **監視修正の実行** — §1.5 の undercount バグは同日修正済み (下記)。修正後実測で N=8/10 正常報告を確認

関連: [[sweep-reversion-eurgbp-late-live-2026-06-12]] (pre-reg LOCK) / [[sweep-hull-live-week1-prereg-2026-06-12]] (初週ゲート) / [[sweep_reversion_eurgbp_late]] (戦略カード) / [[zero-fire-diagnosis-carrydip-vix-2026-07-02]] §3 / **[[sweep-reversion-ps1a-execution-runbook-2026-07-31]] (執行手順書 — §8 準備完了、AMENDMENT 決裁待ち)**

---

## 0. 決裁事項と現在の判定状態

12.4y Bonferroni 唯一の生存戦略 (N=543, t=4.46) が、v9.1 HTF Hard Block により live 経路で構造的に発火不能
(逆張り BUY は発火瞬間が必ず htf=bear) となり、T8 ゲート①抵触で 2026-07-06 から live code pin OFF
([demo_trader.py:8871](../../../modules/demo_trader.py))。P-S1(b) shadow rescue (07-03〜) の蓄積データで
**HTF Hard Block の cell-scoped exemption を認めて live 復帰するか、retire するか**を判定する。

**2026-07-24 時点の状態**:

| 項目 | 状態 |
|---|---|
| 決裁トリガ (unique バー N≥10) | **未達 (N=8)** → 執行待ち。N 到達時は §6 手順で再決裁なしに執行 (条件付き承認済み) |
| 計数意味論 | **unique バー基準で確定** (user 決裁 2026-07-24、§1.4)。registry `count_basis: "unique"` 反映済み |
| EV 符号 (3 基準とも) | **正** (+2.13〜+3.14 p/t)。ただし exit estimand 乖離により entry 符号確認まで (§2) |
| 機械監視 (prereg_trigger_watch) | **修正済み (2026-07-24)** — undercount バグ解消、N=8/10 正常報告を本番確認 (§1.5) |
| 追加証拠 (07-24 後着、§2.5) | exit-free 12.4y 再検証: **エッジは exit 設計の産物ではない** (12h net mean +7.72p、boot p<1e-4)。ただし同一標本のため選択効果は未解消 — **rescued shadow が唯一の真 OOS** |

## 1. 実測: rescued shadow (P-S1(b)、2026-07-03〜2026-07-24)

**データソース**: 本番 API `https://fx-ai-trader.onrender.com/api/demo/trades?status=all&date_from=2026-07-01&mode=daytrade_eurgbp`
(offset pagination 全件、2026-07-24 10:20Z 取得)。ローカル demo_trades.db は 85 日 stale のため不使用。
全 14 行が `is_shadow=1` / `oanda_trade_id=""` / `[HTF_BLOCK_SHADOW_RESCUE]` タグ付き — 汚染なし。

### 1.1 三基準サマリ

| 基準 | 定義 | N | ΣPnL | EV (p/t) | WR | Wilson95 WR | t (mean≠0) |
|---|---|---|---|---|---|---|---|
| **row** | DB 全行 (dedup_violation=1 の重複行込み) | 14 | +29.8p | **+2.13** | 10/14 = 71.4% | [45.4%, 88.3%] | 2.42 |
| **unique バー** | dedup_violation=0 の primary 行 = 1 バー 1 観測 | 8 | +25.1p | **+3.14** | 6/8 = 75.0% | [40.9%, 92.9%] | 2.33 |
| **spaced (検証 estimand)** | unique に 12-bar (3h) min-spacing を後段適用 — 12y grid N=543 と同じ dedup 定義 | 6 | +14.8p | **+2.47** | 4/6 = 66.7% | [30.0%, 90.3%] | 1.60 |

- spaced 基準が 12y 検証 (`dedup_indices(ev, DEDUP_GAP=12)`) と同一の estimand。unique→spaced で落ちる 2 バー
  (07-06 21:32 / 07-07 21:47、初回 emit の 1-2 バー後) は、**strategy 内 12-bar cooldown が live で死んでいる**
  (engine 毎 poll 再構築、MEMORY `project_engine_reconstruction_live_dedup_dead`) ことの実データ実証でもある → §3.1 の根拠。
- 参考: 12y 設計値は WR 59.7% / +6.22 p/t (net 1.5p spread)。shadow WR 75% が設計値を上回るのは §2 の
  BE/trail 型 exit による既知の WR 押し上げ (+20pp 級、MEMORY `project_be_trail_inflates_python_bt_wr`) と整合的で、エッジ改善の証拠ではない。

### 1.2 発火頻度 vs pre-reg ゲート①帯 (0.3〜2.6 件/週)

| 基準 | 件数 / 3.06 週 | 週次換算 | 帯内? |
|---|---|---|---|
| unique バー | 8 | 2.61/週 | ⚠️ 上限 2.6 を僅かに超過 |
| spaced | 6 | 1.96/週 | ✅ 帯内 |
| (参考) rescue 前の silent-drop 期 06-12〜07-01 | 4 emit / 2.86 週 | 1.4/週 | ✅ 帯内 |

発火日: 07-06×2, 07-07×2, 07-08, 07-09, 07-13, 07-15 (全て 21:16-21:47 UTC = LATE 窓)。
**07-16〜07-24 は発火 0 (8.5 日)** — 期待 3-4 件/月なら平均ギャップ ~9 日で lumpy の範囲内。
12y 平均 (0.85/週) より高いのは、エッジが 2021+ regime 集中である (LOCK 文書 Caveat) ことと矛盾しない。

### 1.3 生データ (unique バー 8 件)

| id | entry (UTC) | PnL(p) | outcome | close_reason | hold | spread@entry | spread@exit |
|---|---|---|---|---|---|---|---|
| 12359 | 07-06 21:16 | −1.9 | LOSS | SIGNAL_REVERSE | 15m | 6.9 | 7.0 |
| 12361 | 07-06 21:32 | +2.0 | WIN | SL_HIT (trail) | 16m | 6.1 | 4.0 |
| 12480 | 07-07 21:16 | +2.6 | WIN | SIGNAL_REVERSE | 2h54m | 6.3 | 1.2 |
| 12486 | 07-07 21:47 | +8.3 | WIN | SL_HIT (trail) | 8h32m | 5.4 | 1.4 |
| 12625 | 07-08 21:16 | −1.5 | LOSS | SIGNAL_REVERSE | 20m | 6.1 | 2.9 |
| 12747 | 07-09 21:16 | +5.3 | WIN | SL_HIT (trail) | 22m | 16.6 | 7.3 |
| 13025 | 07-13 21:16 | +2.5 | WIN | SL_HIT (trail) | 15m | 7.9 | 8.9 |
| 13273 | 07-15 21:46 | +7.8 | WIN | SL_HIT (trail) | 3h52m | 7.7 | 1.5 |

「SL_HIT」5 件は全て exit > entry の勝ち trail (SL が entry 上に移動済み) = BE/trail エンジンの痕跡。

### 1.4 計数意味論の確定 (user 判断事項)

T8 DEFER 裁定は「shadow N≥10」の row/unique を明記していない。registry 実装
(`tools/prereg_trigger_watch.py count_matching`) は **row 基準** (dedup_violation フィルタなし) で、
row なら既に N=14≥10 = トリガ成立済み。一方 clean live 計数 (`count_live_matching`) は dedup_violation≠1 を
既に除外しており、estimand 忠実なのは unique/spaced 側。**提案: unique バー基準を正とする**
(本パケットはそれを前提に「トリガ待ち」)。row 基準を採る場合は §5 の判定を即時実施できる。

### 1.5 機械監視の故障 (重大、決裁の前提インフラ)

`t8-sweep-defer-decision` は 2026-07-24 実行で **「shadow N=0/10」と誤報告**。原因を実 API で再現確認済み:
`fetch_shadow_count` が limit=800 単発・mode フィルタなしで取得するため、全 mode 合算の直近 800 行
(実測: **07-16 以降のみ**) しか見えず、sweep の最終発火 07-15 が窓外。帰結:
- N≥10 トリガは**永遠に発火しない** (発火が古くなるほど 0 に向かう)
- **2026-09-30 の「N<5 → retire (R2、裁量禁止)」が偽 N=0 で誤発動する** — 実測 unique N=8 > 5 で本来非該当
- ws3-stage2 / ws3-t11 / t8-hull / t9-kalman の同型カウンタも undercount の疑い

修正タスクは chip 起票済み (コード変更は本タスクのスコープ外)。**exemption/retire いずれの裁定でも、この修正が先行必須。**

**→ 修正済み (2026-07-24、user 承認後に同日実装)**: `fetch_shadow_count`/`fetch_live_count` を offset pagination
全量取得に置換 (max_pages 到達 = DATA_UNAVAILABLE の fail-loud、silent truncation 再発防止)、`mode` サーバ側
絞り込みと `count_basis: "unique"` (dedup_violation=1 除外) を registry に追加。修正後実測:
t8-sweep **N=8/10** (手動集計と一致) / t8-hull N=3 / ws3-t11 N=9 — undercount 解消を本番 API で確認済み。

## 2. Exit estimand 乖離 — shadow EV の解釈限界

pre-reg 検証済み exit (LOCK 文書): **time-stop 48 bars (12h) 一次 / SL −4×ATR / TP +6×ATR (tail-cap)**。
rescued shadow の実際の close_reason は **SIGNAL_REVERSE 3 / SL_HIT(BE-trail) 5** (unique 基準)、
hold は中央値 ~21 分 (最長 8.5h)、**time-stop 到達 0 件** — 本番 exit エンジン (BE/trail + signal-reverse) が
設計 exit を全面的に上書きしている。したがって:

- **shadow EV (+2.47〜+3.14 p/t) は「entry 方向の符号確認」まで**。検証済み +6.22 p/t の再現確認ではない
- WR 75% は BE/trail 型の既知バイアス (+20pp 級) 込み。12y WR 59.7% と直接比較不可
- T3 診断 ([[payoff-asymmetry-diagnosis-2026-07-07]]) の「trail 返上による勝ち側 exit 崩壊」がこの戦略にも
  そのまま作用する — 07-06 21:32 の +2.0p (16 分 trail close) は、設計上 12h ホールドすべきトレードだった
- exemption 承認しても、**exit を整合させない限り live EV は検証と別 estimand の測定になる** → §3.4

## 2.5 追加証拠 — exit-free 12.4y 再検証 (2026-07-24 後着、別セッション wave-0 explore)

**結論: エッジは entry+12h 平均回帰そのものに存在し、BE/trail・TP/SL・time-stop など exit 機構の産物ではない。**
出典: `reports/sweep_reversion_exitfree_reverify-2026-07-24.md` / `bt-results/sweep_reversion_exitfree_reverify-2026-07-24.json` /
`tools/sweep_reversion_exitfree_reverify.py` (2026-07-24 時点 branch `research/trendline-sweep-12y-pairscope-2026-07-13` 着地中 —
本パケット更新時に主要数値を JSON と突合済み)。

- **凍結トリガ完全再現**: N=543 / WR 59.7% / +6.22p / t=4.46 — 登録値 (2026-06-12) と一致
- **exit-free forward 計測** (exit 設計なし、next-bar open entry からの純粋 forward): 12h net mean **+7.72p** /
  median **+5.10p** (bootstrap p<1e-4)、RT 3.0p 控除後 **+4.72p**、per-year 11/13 年正
- **エッジは ~12h 平均回帰に局在**: MFE/MAE p50 非対称は 4h (1.16) / 12h (1.25) のみで、**≥24h で反転**
  (24h 0.94 / 72h 0.80 / 120h 0.67) — pre-reg の 12h ホールド設計 horizon と整合。**長ホールドへの外挿は禁止**
- 本パケット §2 との関係: shadow EV 正符号 (entry 符号) と exit-free 正 EV は同じ向きの証拠。ただし §2 の
  「本番 exit は検証 estimand と別物」という注記は不変 — exit-free 証拠は「どの exit でもエッジが消えるわけではない」
  ことを示すが、本番 BE/trail の実現 payoff が +4.72p 相当を回収できるかは別問題 (T3 trail 返上の実証あり)

**敵対的レビュー注記 (同セッション指摘、パケット判断に影響)**:
1. **weekend 跨ぎの estimand 乖離**: BT の H=48 bars は bar-time で、weekend を跨ぐ窓が **~11-13%**
   (本パケット更新時の独立概算 13.3%、金曜 entry 12.7%)。live の time-stop は 43200s **wall-clock**
   (`_ENTRY_TYPE_MAX_HOLD`) — 金曜 entry は live では週末中に time-stop 期限が来るのに対し BT は翌週まで
   48 営業バー保有する。**BT/live の第 3 の estimand 乖離軸** (①HTF gate ②12-bar spacing に続く) → §4 リスク 9
2. **同一標本の限界**: 再検証は元 grid と同じ parquet (〜2026-05-05) 上であり、m=1,728 max-t 選択効果は
   未解消。**選択効果を解消できる新データは rescued shadow (07-03〜) のみ** — 本パケットの N≥10 トリガ設計が
   その役割を担う、という論理構成を再確認 (§1 の unique/spaced 計測の重要性が上がる)

## 3. 復帰前提条件と設計案 (設計のみ、実装しない)

T8 裁定の復帰前提 = 「N≥10 EV>0 でも、再有効化には **order 層 12-bar min-spacing 実装が必須**」(Forensic #3)。

### 3.1 order 層 12-bar min-spacing (T8 必須条件)

- **配置**: `DemoTrader._maybe_reserve_order_bar_emit` ([demo_trader.py:1097](../../../modules/demo_trader.py)) の拡張。
  新レイヤーを作らず、既存 order-bar dedup (PR #49) と同じ受理点に同居させる
- **登録**: code 定数 `_ORDER_MIN_SPACING_BARS = {"sweep_reversion_eurgbp_late": 12}` (戦略別 opt-in、他戦略無影響)
- **状態**: `(entry_type, instrument, signal) → 最終受理 bar_ts` の map。受理時に更新、
  `bar_ts − last < 12 × tf_sec` なら block + block_counts に **専用 reason key `order_min_spacing`**
  (`order_bar_dedup` と区別して観測可能に)
- **再起動耐性**: 現行 hydration (`get_recent_signal_emits(window_sec=3600)`) は 1h 窓で、12×15m=3h に不足。
  hydration 窓を `max(3600, min_spacing_bars × tf_sec)` へ拡張 (これを怠ると deploy 直後に spacing が素通り)
- **スコープ**: live 送信の受理にのみ執行。shadow 行は従来通り記録 (4原則#3 の LIVE/Shadow 非対称:
  Shadow は蓄積、LIVE は検証済み条件のみ転送)。分析側は本パケット同様 spaced 基準で集計
- **pin test**: 同夜 2 バー目 (12 バー以内) → live block + counter 増分 / 12 バー超 → 通過 / 再起動後 hydration 維持

### 3.2 HTF Hard Block exemption (P-S1(a) 本体)

- **配置**: [app.py:2615](../../../app.py) 付近の HTF Hard Block 候補フィルタ。redesign-v2 系の既存 exemption
  条件列と同じ位置に、cell-scoped の免除条件を追加
- **形式**: code 定数 `HTF_HARD_BLOCK_EXEMPT_CELLS = frozenset({("sweep_reversion_eurgbp_late", "EUR_GBP")})`。
  **env ではなく code 定数** — T8 code pin と対称 (lesson: KV/env は pin にならない。有効化も無効化も code で、
  変更 = テスト変更を伴う PR = レビュー必須構造を維持)
- **正当性 (estimand 論)**: 12y grid pre-reg には HTF gate が存在しない。逆張り BUY は構造的に htf=bear で
  発火するため、gate 維持 = 発火 0 の恒久化 (T8 で 24 日間実証)。本 exemption は新フィルタの付与ではなく
  **BT/本番統一の回復** (ゲート①抵触の根本原因除去)
- **blast radius**: この 1 cell のみ。HTF Hard Block 本体・HTF_MIXED_LIVE_STOP_CELLS・他戦略は不変。
  exemption 発動時、P-S1(b) rescue 分岐は当該候補を見なくなる (blocked でなくなるため) — rescue 機構自体は他戦略用に残置
- **guard chain 宣言** (lesson: bypass 経路は共有 guard を明示): 外すのは **HTF direction filter のみ**。
  維持 = dynamic Spread/SL Gate / order_bar_dedup / order_min_spacing (新設) / recent_emit /
  既存 `_sweep_reversion_eurgbp_live_eligible` の bypass 範囲 (SHADOW_MODE, Phase0, _OANDA_MODE_BLOCKED) /
  lot 1000u 固定 / LOCK 文書 Withdrawal triggers 5 項 (継続有効)

### 3.3 単一 PR 要件 (R1 手続き)

復帰 PR は以下を**同一 PR** に含める (T8 が設計した review-required 構造の通り):
1. §3.1 min-spacing 実装 + pin tests
2. §3.2 exemption 定数 + pin tests (htf=bear で sweep×EUR_GBP のみ生存、他戦略 block 継続)
3. `_SWEEP_REVERSION_EURGBP_LIVE_ENABLE` code pin 解除 ([demo_trader.py:8871](../../../modules/demo_trader.py)) +
   `tests/test_t8_week1_r2_stop_code_pin.py` の対応変更
4. registry 更新: `t8-sweep-defer-decision` クローズ → live N 蓄積 checkpoint (`live_count_decision`,
   LOCK Withdrawal trigger 1 = live N≥10 EV<0 撤退の監視) に置換 — §1.5 の監視修正が前提
5. 復帰初週の再ゲート: 頻度帯 (spaced 基準 0.3〜2.6/週) + spread 実測 + ゲート④(改) — 初週 pre-reg の再 LOCK
6. Codex review (LOCK 文書と同型の必須レビュー)

### 3.4 exit 整合の扱い (open design question — 決裁時に user 選択)

| 案 | 内容 | 利害 |
|---|---|---|
| (i) 本番 exit のまま復帰 | 追加実装ゼロ。EV 判定は LOCK Withdrawal triggers (estimand 非依存) で運用 | live EV は検証 +6.22p と別物のまま。T3 の trail 返上がそのまま作用 |
| (ii) entry_type 限定 exit override | BE/trail・SIGNAL_REVERSE を本 cell で無効化し 48-bar time-stop を執行 | 検証 estimand に忠実。ただし exit エンジン改修 = 変更面積とリスク増、R1 審査対象が拡大 |
| (iii) (i) + MFE 計測 | 本番 exit のまま、48-bar 時点 MFE を並行記録し estimand 比較を後日実施 | 中間。計測配線の小改修が必要 |

提案: 初回復帰は **(i) を既定**とし、live N≥10 蓄積後に (ii) 移行を再決裁 (exit-repair 系は T2 で
「現行母集団の exit 側改善」が否定済みだが、それは負エッジ母集団の話であり、正エッジ検証済み cell の
estimand 忠実化は別問題である点に注意)。

§2.5 の追加証拠による補強: (a) ≥24h で MFE/MAE が反転するため、**time-stop の執行 (12h で必ず切る) は
どの案でも死守すべき制約** — 本番の 43200s wall-clock time-stop が実際に発火するかの検証を復帰初週の
監視項目に含める。(b) 金曜 entry の weekend 跨ぎ (§2.5 注記 1) は (ii) を採る場合の time-stop 定義
(bar-time vs wall-clock) の明示選択を要求する — 検証 estimand に忠実なのは bar-time (48 営業バー) だが、
±24h 反転を踏まえると wall-clock の方が安全側。決裁時に指定。

## 4. リスク列挙

1. **摩擦 — 最大のリスク**。BT 仮定 spread 1.5p / 反証耐性 3.5p に対し、**実測 entry spread は
   中央値 6.6p (5.4〜16.6p)** — LATE 窓 (21:16-21:47 UTC、rollover 直後) の構造的ワイド。設計 12h ホールドの
   exit 側は翌朝で 1.2-1.5p に回復するため、往復摩擦 ≈ entry/2 + exit/2 ≈ **~4.0p (中央値) 〜 ~9p (worst)**。
   gross edge +7.72p (= +6.22 + 仮定 1.5) に対し**残余 ≈ +3.7 p/t (中央値)、worst tail では負**。
   friction-analysis の EUR_GBP「STRUCTURALLY IMPOSSIBLE (~3.0p RT, BEV_WR 57.1%)」は日中摩擦の値であり、
   本 cell は LATE 窓でさらに悪い。**live 実測での摩擦再推定こそが exemption で得るべきデータ**
2. **Spread/SL Gate との相互作用**。entry 時 5-17p の spread は動的 gate (デスゾーン検出) に当たり得る:
   block されれば zero-fire 再演、通れば spike spread 約定。復帰初週は spread-gate block_counts を監視項目に含める
3. **exit estimand 乖離** (§2)。live EV は当面、検証と別 estimand の測定
4. **統計的弱さ**。spaced N=6, t=1.60 (有意でない)。エッジは 2021+ regime 集中 (LOCK Caveat)。
   直近 8.5 日発火 0 (lumpy の範囲内)。現時点の shadow EV 正符号は「exemption を正当化する最低条件を満たす」
   以上のものではない
5. **期待寄与は絶対額で微小**。1000u EUR_GBP ≈ ¥22/pip。設計 EV でも 3.5 件/月 × +6.22p ≈ **¥480/月**、
   摩擦調整後 ≈ ¥200-300/月、tail リスク ≈ SL 25p ≈ ¥550/trade。**M1 への数値寄与はほぼゼロ** —
   価値は (i) 供給枯渇環境で唯一の 12.4y Bonferroni 生存 cell の live 経路保全、(ii) emit→fill 翻訳と
   LATE 窓摩擦の実測 (T8 forensic #3 の未了項目)、(iii) M1 (月次符号転換) に必要な clean live 正セル候補
6. **DD 防御 mode との整合**。現在 DD 100.01% held・0.2x 防御中。1000u は MIN lot floor のため 0.2x が
   適用されない (縮小不能)。絶対額は微小だが「防御 mode 中に新規 live 経路を開く」こと自体の方針判断は user 決裁事項
7. **監視系の故障** (§1.5)。修正前に exemption しても、撤退側トリガ (live N≥10 EV<0 等) の機械監視が
   同じ undercount で沈黙する — **修正はどのオプションでも先行必須**
8. **ゲート④(改) の解釈メモ** (小、forensic 行き)。rescued shadow に同一 (entry_type, instrument, signal,
   bar_ts) の 2 行 insert が 6 バー分ある (2-mode スレッド由来、2 行目は dedup_violation=1 でフラグ済み)。
   ゲート④(改) の文言「DB insert が 2 件以上検出 — 即停止」を literal に読むと抵触に見えるが、
   flag 付き記録は「検出済み・観測可能」であり silent runaway ではない。**「unflagged insert に限る」旨の
   文言明確化を推奨** (LOCKED 変更 = レビュー必須 PR)
9. **weekend 跨ぎの time-stop estimand 乖離** (§2.5 注記 1)。事象の ~11-13% (金曜 entry) で BT (48 営業バー
   bar-time) と live (43200s wall-clock) のホールド期間が構造的に異なる。live 復帰後の EV を BT と突合する際、
   金曜 entry セグメントは別集計すること (教訓「集計値は必ずセグメント分解する」)

## 5. 判定オプション表

| オプション | 内容 | pre-reg 整合性 | 評価 |
|---|---|---|---|
| **A. 即時 exemption 承認** | 今すぐ復帰 PR | ❌ 三重不整合: (1) unique N=8 < 10 でトリガ未達 (row 基準なら達成 — §1.4 の確定が先)、(2) T8 必須条件 min-spacing 未実装のままなら「検証と別 estimand の運用」= ゲート①と同型の再演、(3) 監視故障未修正 | 非推奨 |
| **B. 条件付き承認** | unique N≥10 到達 && spaced EV>0 を確認後、§3.3 の単一 PR (min-spacing + exemption + pin 解除 + 再ゲート) で復帰 | ✅ T8 DEFER の機械的決定点そのもの。R1 手続き (12.4y Bonferroni 事前証拠 + pre-reg 済み判定基準 + Codex review) を満たす | **推奨**。今日の決裁は「B を承認 (トリガ到達を執行条件とする条件付き決裁)」が可能 — 到達時に再決裁不要になる。exit 整合 (§3.4) の案選択のみ併せて指定 |
| **C. Retire** | 戦略登録解除 + registry クローズ | ❌ retire 分岐の成立条件は「09-30 に N<5」— 実測 unique N=8 > 5 で非該当。EV 符号も 3 基準とも正。現時点の retire は pre-reg 外の裁量判断になる | 非推奨 (不可逆。12.4y Bonferroni 唯一生存 cell の破棄は、供給枯渇 (内部母集団三重確認済み) の下で回収不能な選択) |

**推奨アクション (2026-07-24)**: B の条件付き決裁 + §1.4 計数意味論の確定 (unique 推奨) + §1.5 監視修正の実行承認 + §3.4 exit 案の選択 (既定 (i))。

**→ 決裁済み (2026-07-24 user「進めて」)**: 上記推奨アクションを全て承認 (冒頭の決裁記録参照)。以後この
パケットは「執行待ち」— unique N≥10 到達で §6 を執行する。

## 6. トリガ到達時の更新手順 (このパケットを FINAL 化する手順)

1. 本番 API から再取得 (§1 と同一クエリ、pagination 全件) → §1.1 三基準テーブルと §1.3 生データを更新
2. 判定規則 (T8 裁定 + 本パケット提案): **spaced 基準 EV>0 → Option B 執行 / spaced EV≤0 → Option C**
   (unique 基準を感度チェックとして併記。両基準で符号が割れた場合は user 再決裁)
3. Status を DRAFT → FINAL に変更、判定結果と user 承認記録を追記
4. Option B なら §3.3 の単一 PR を起票 (R1: 実装 Claude / review Codex / user 最終承認)

## 7. Appendix — 再現手順

```bash
curl -s "https://fx-ai-trader.onrender.com/api/demo/trades?status=all&date_from=2026-07-01&limit=500&mode=daytrade_eurgbp" \
  | python3 -c "import json,sys; ts=[t for t in json.load(sys.stdin)['trades'] if t['entry_type']=='sweep_reversion_eurgbp_late']; print(len(ts))"
```

- row = 全行 / unique = dedup_violation==0 / spaced = unique に 12×15m=3h の min-gap を entry_time 昇順で適用
- Wilson 95% は z=1.96。EV は pnl_pips 単純平均 (shadow の pnl は entry ask-side 反映と整合的だが、摩擦包含の完全検証は未了 — live 実測で置換されるべき数値)
- 12 行の raw ペア (dedup_violation=0/1) は同一バーの 2-mode スレッド重複。row 14 = unique 8 + 重複 6
- §2.5 の exit-free 再検証: `tools/sweep_reversion_exitfree_reverify.py` (決定論、seed=20260724、bootstrap n=10,000)。
  weekend 跨ぎ ~13.3% は本パケット更新時の独立概算 (トリガ近似再現 N=639 — swing_lo/ATR 定義差により
  凍結 tool の N=543 と一致しないが、weekday 分布の推定には十分)

## 8. 執行準備 (2026-07-31 追記 — user 指示「トリガ成立日に機械的に完遂できる状態にする」)

> **zero-fire forensic 決裁記録 (2026-08-17)**: 28 日 zero-fire の原因 = gbp_asia gate の rowless drop
> (実イベント 4 件消失、[[../analyses/sweep-zero-fire-forensic-2026-08-12]]、記録経路は PR #180 で
> R3 修復済み — 修復後初 LATE 窓 08-12 で新イベント記録、unique N=9/10)。user「進めて」で承認:
> (1) 再構成イベント (unique N=12 相当) は凍結トリガに**算入しない** — 字義 (DB 行) 維持で fresh 蓄積待ち、
> (2) retire 期日 09-30 → **10-28** (計数器故障 28 日分の繰り延べ、checker/registry 反映済み)、
> (3) 日曜 LATE イベントの恒久欠測 (12.4y 10.3% / 2021+ 4.5%) を初週再ゲート頻度帯の割引として凍結
> (runbook §5)。**執行条件そのもの (unique N≥10 ∧ spaced EV>0) は不変**。

> **AMENDMENT 決裁記録 (2026-08-03)**: §8.1 の提示 (第3/第4 ブロッカー + gbp_asia cell 免除
> + 専用 spread cap 10.0p の提案) に対し user 「進めて」。以下を承認として記録:
> **AMENDMENT (commit `dfec4343`) 承認** — トリガ成立日は commit 1+2 を含む単一 PR で
> 再決裁なしに執行可 (runbook §2.5 の停止分岐は解除)。**執行条件 (unique N≥10 ∧
> spaced EV>0) 自体は不変** — 決裁時点の再実測 N=8/10 (最終発火 07-15、18.1 日静止、
> spaced EV +2.47p) で未成立のため live 変更は未実施。

**状態: N=8/10 のまま (07-24 から新規発火 0、最終発火 07-15)。準備は完了、執行はトリガ待ち。**

| 準備物 | 場所 |
|---|---|
| 執行条件判定器 (凍結文言 dry-run) | `tools/ps1a_execution_check.py` + pin tests 12 件。2026-07-31 本番実測で §1.1 と完全一致 (row +2.13 / unique +3.14 / spaced +2.47) を確認済み |
| Option B 実装 (§3.3-1〜4) | draft branch `draft/ps1a-option-b-20260731` **commit `8272f994`** (マージ禁止、origin push 済み、pre-commit full pytest green) |
| §8.1 AMENDMENT 実装 | 同 branch **commit `dfec4343`** (user 決裁待ち) |
| 執行手順書 | [[sweep-reversion-ps1a-execution-runbook-2026-07-31]] — トリガ成立日はこれを上から実行するだけ |
| 機械監視 | `t8-sweep-defer-decision` N=8/10 正常報告 + Tier A cron (00:20 UTC) → Discord 配線確認済み |

### 8.1 ⚠️ 新発見: 第 3・第 4 の estimand ブロッカー (user 決裁事項)

§3.2 の guard chain 宣言にはゲート網羅の漏れがあった。2026-07-31 準備セッションのコード
実測で、承認済み Option B (§3.3) をそのまま merge しても**発火しない**ことを確認:

1. **第 3 ブロッカー — `gbp_asia_flash_crash`** (v8.6 静的、`_tick_entry`: "GBP" in
   instrument ∧ UTC 21-06): 本 cell の LATE 窓 (21-24 UTC) を 100% 内包。sweep は
   `_is_shadow_eligible_full` (FORCE_DEMOTED ∪ SCALP/UNIVERSAL_SENTINEL ∪ trendline-v2)
   の**全て非該当**のため hard block (`_block` + return、行も残らない)。さらに fallback
   (`elif _kalman_live_pre and not _is_shadow`) は先行ゲートの shadow 降格を live に
   戻さないため、仮に shadow-eligible でも live 送信は不可能だった
2. **第 4 ブロッカー — 静的 per-pair spread limit + spread/TP 比 gate**:
   `_SPREAD_LIMITS["EUR_GBP"] = 1.5p` に対し LATE rollover 実測 quoted spread は
   5.4〜16.6p (§1.3 の全 8 発火が超過) → `spread_wide` hard block。spread/TP 比 gate
   (20%) も TP=6×ATR tail-cap 設計 (一次 exit は 12h time-stop で TP は稀にしか
   触れない) に対し比の分母が過小 → 構造的に全 block

**帰結**: Option B (commit 1) 単独 merge は (1) live fill 0 の再演 (ゲート①と同型) に
加え、(2) **HTF exemption が rescue 経路を外すため shadow 蓄積まで消滅** (htf=bear:
現状 = rescue → shadow 行 / commit 1 後 = primary → 上記ゲートで hard block → 行なし)。
4原則#3 違反 + Withdrawal trigger 監視の母数消滅。**T8 期にこれらが未観測だったのは
上流 HTF Hard Block が emit を 100% 削っており、下流ゲートが一度もテストされて
いないため** (ゲート積層の shadowing — 教訓化対象)。

**AMENDMENT 提案 (07-24 承認スコープ外 → ✅ user 承認 2026-08-03「進めて」、commit `dfec4343` 実装済み)**:
- (a) `_GBP_ASIA_FLASH_CRASH_EXEMPT_CELLS = frozenset({("sweep_reversion_eurgbp_late",
  "EUR_GBP")})` — §3.2 と同一の estimand 論 (12.4y grid pre-reg にアジア時間フィルタは
  存在せず、cell 定義が全部ブロック帯内 = gate 維持は発火 0 の恒久化)。GBP フラッシュ
  クラッシュ tail の防御は本 cell では 1000u 固定 lot + SL −4×ATR + 動的 spread_sl_gate が担う
- (b) 専用 spread cap **10.0p** — [[weekend-gap-stage2-execution-prereg-2026-07-24]] §2.2
  の前例と同型・同値。cap 内 = live / cap 超過 = shadow row 記録 (分母保存)。静的 limit と
  比 gate は本 cell のみ置換。**動的 spread_sl_gate (spread/SL>35%) は維持** — §4-2 の
  「デスゾーン = 動的検出」防御はそのまま。実測 8 発火中 7 が cap 内 (worst 16.6p は遮断)
- blast radius = 本 cell のみ (ゲート本体・他戦略は不変 = 原則3 の LIVE 側
  winning-location フィルタ設計は維持)。cap 経路は `_sweep_reversion_eurgbp_live_eligible`
  連動で pin 再無効化 (R2 stop) 時に自動不活性化
- **摩擦論との整合**: cap 10p 採用は「spread 5-17p での約定を意図的に受ける」ことを意味
  する。§4-1 の摩擦計算 (RT 中央値 ~4.0p vs gross +7.72p → 残余 +3.7p、worst tail 負) が
  その根拠で、worst tail は cap + 動的 gate の二段で遮断。**live 実測での摩擦再推定こそが
  exemption で得るべきデータ** (§4-1) という本パケットの結論と一貫

**執行規律**: ~~AMENDMENT 未決裁のままトリガが成立した場合、commit 1 のみの執行は禁止
(上記帰結)。runbook §2.5 が執行を停止し user 決裁を要求する構造にしてある。~~
→ **2026-08-03 決裁で解消** — トリガ成立時は commit 1+2 で §3.3 単一 PR を直接執行
(commit 1 単独 merge の禁止は引き続き有効)。

### 8.2 残余の観測ポイント (執行後初週、runbook §5 に反映済み)

- **select_best 競争**: exemption 後は rescue (blocked 候補を無条件退避) と違い同 bar の
  他候補との score 競争に入るが、sweep は select_best side-channel 登録済み (2026-06-12
  Codex review I-3 同型) のため理論上取り逃しなし — 初週の頻度帯監視 (spaced 0.3〜2.6/週)
  で実証する
- **confidence gate**: sweep candidate は confidence=65 固定 — threshold 通過見込み、
  初週 block_counts で確認
- **spread_sl_gate (維持)**: SL=4×ATR ≈ 16-27p に対し spread 中央値 6.6p → ratio ~25-40%
  で閾値 35% 近傍。中央値帯は通過、worst tail は遮断される見込み — block_counts の
  `spread_sl_gate` sweep 行で実測する
