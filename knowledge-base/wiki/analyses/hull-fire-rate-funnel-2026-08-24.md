# hull_donchian_fade 発火率ギャップの funnel 分解 (2026-08-24, rule:R3)

> **verdict**: 「13.3/週 期待 vs 1.62/週 実測 = 8.2x 欠損」のうち **約 1.7x は estimand
> 不一致 (signal-rate を trade-rate と比較していた)**。残り **~4.7x は未説明で実在**。
> 未説明分をこれ以上外部から絞り込めなかった真因 = **C1 `evaluated_candidates` が
> 4 ヶ月間 write-only** だったこと。読み出し経路を本 PR で新設した。

## 1. 背景 — 49 日間滞留していた info トリガ

registry `t8-hull-shadow-freq` (since 2026-07-03, `expected_per_week: 13.3`) は
`prereg_trigger_watch` で毎回 `実測 1.62/週 vs 期待 13.3/週 (N=12)` と表示され続け、
[[t8-week1-gate-breach-2026-07-06]] §89 で「頻度 band 割れは独立の問題として残存」と
記録されたまま **49 日間** 未診断だった。type が `shadow_count_info` (判定なし) の
ため自動エスカレーションも無い。

**最初に見落とされていた事実**: これは平均レートの不足ではなく **階段関数**。

| 実測 | 値 |
|---|---|
| hull 全 trade 行 (本番 API) | 17 (全て `is_shadow=1`、`oanda_trade_id=''`) |
| since 2026-07-03 | 12 |
| **最終発火** | **2026-08-06T15:31Z** |
| 以後の無発火期間 | **18 日** |

週平均表示が step-function を平滑化して隠していた。

## 2. シグナル生成器は健全 — 市場は setup を提供していた

凍結スペック (`strategies/daytrade/hull_donchian_fade.py`、再最適化禁止) を
MASSIVE EUR_USD 15m にオフライン再生 (2026-05-01..08-23、16.3 週、`backtest_mode=True`)。

- **205 signals = 12.59/週** → registry の 13.3/週 期待値をほぼ再現。期待値自体は妥当。
- 無発火だった 08-06〜08-21 の窓にも **33 signals** が存在。
  → 「相場が圧縮 regime を提供しなかった」仮説は **棄却**。

## 3. Funnel 分解

| # | 段 | 件数 | /週 | 減衰 |
|---|---|---|---|---|
| 1 | registry 期待値 | — | 13.30 | — |
| 2 | 凍結スペック signals (offline replay) | 205 | 12.59 | — |
| 3 | v9.1 HTF Hard Block 通過後 | 153 | 9.39 | **−25.4%** |
| 4 | 1-position 直列化 (実測 median hold 0.57h) | 124 | 7.61 | −19% |
| 5 | **本番 live shadow trades 実測** | — | **1.62** | — |
| | **残余 (未説明)** | | | **~4.7x** |

### 3.1 HTF Hard Block (寄与 1.34x) — 直感より遥かに小さい

`app.py` v9.1 の HTF Hard Block は **候補リスト段階**で counter-HTF 候補を除外する
(`htf_agreement in ("bull","bear")` のとき逆方向を drop)。除外は shadow / side-channel
の全記録経路より前なので **block counter に一切残らない silent drop**。

hull は exemption リスト (intraday_seasonality / atr_regime_break /
wick_imbalance_reversion / tokyo_nakane_momentum / weekend_gap_fade) にも
`HTF_BLOCK_SHADOW_RESCUE` (= `{sweep_reversion_eurgbp_late}` のみ) にも**不在**。

コードコメントは「逆張り (MR) 戦略は発火瞬間が構造的に counter-HTF なので kill 率
~100%」と述べており、hull は `strategy_type = "MR"` なので同型に見える。
**しかし実測は 25.4% であって ~100% ではない** — 生存 153 件のうち 119 件が
`htf=mixed` 窓 (Hard Block は bull/bear 限定で mixed には発動しない) での発火。
sweep で観測された「HTF gate 100% silent drop」を hull にそのまま外挿してはならない。

### 3.2 直列化 (寄与 ~1.23x) — 当初 3.06x と誤推定した

`max_hold_bars = 96` (24h) から「1 ポジション直列化で 24h ブロック」と仮定すると
3.07/週 まで落ち、残余は 1.90x に見えた。**この仮定は誤り**。本番 closed 17 件の
実測保有時間は median **0.57h** / mean 2.32h / p90 3.86h / max 20.96h であり、
24h キャップはほぼ拘束していない。実測 hold を使うと直列化の寄与は 9.39→7.61/週
に留まり、**残余は 1.90x ではなく ~4.7x**。

> 教訓: 設計上のキャップ値 (`max_hold_bars`) を実効値の代理にすると、
> 残余を過小評価して「ほぼ説明できた」と誤結論する。保有時間は実測分布で入れる。

### 3.3 残余 ~4.7x は名前付き gate に帰属しない

本番 `/api/demo/block-counts?strategy=hull_donchian_fade` は
`per_strategy_counts = {}` (**ゼロ**)。同時刻の `daytrade_eur:order_bar_dedup = 52` は
`wick_imbalance_reversion 27 + doji_breakout 25` で完全に説明され、hull の寄与は 0。

つまり残余は「名前付き gate が hull を拒否している」形では発生していない。
ただし block counter は restart でリセットされ、観測窓は ~3h しかない
(`main_loop_restarts=1`, tick 340×30s) ため、**この証拠だけでは残余を否定も特定もできない**。

## 4. 診断が 49 日間止まっていた真因 — C1 テーブルが write-only

`evaluated_candidates` (modules/candidate_logger.py) は
[[lesson-select-best-bottleneck-2026-04-28]] を受けて 2026-04-28 に新設され、
`evaluate_all()` の**全候補 (敗者含む)** を毎バー記録している。app.py 起動時に
`init_candidates_table(_db_path)` が走り、Render Disk `/var/data/demo_trades.db` に
書かれ続けている。

**しかし読み出し経路が存在しなかった**:

- HTTP route: **無し**
- `query_candidate_summary()` の呼び出し元: **`tests/test_candidate_logger.py` のみ**
  (本番コードからの参照ゼロ = 実質 dead code)

silent drop を可視化するために作られた観測基盤が、観測できない状態で 4 ヶ月
データを溜めていた。「候補は出たが trade にならない」という funnel 段が本番で
読めないので、hull の残余 4.7x を **外部から localize する手段が無かった**。

### 4.1 本 PR の fix

`GET /api/demo/evaluated-candidates` を新設 (read-only, GET のみ):

| view | 返すもの |
|---|---|
| `summary` (既定) | 戦略別 total_candidates / n_selected / BUY / SELL |
| `rows` | 直近の個別行 (bar_time, instrument, signal, score, selected, selected_strategy) |
| `meta` | 総行数・被覆窓・戦略数 |

パラメータ: `strategy` / `instrument` / `days` (既定 7) / `limit` (既定 200、上限 2000)。

**estimand 警告 (route docstring と関数 docstring の両方に明記)**:
本テーブルへの記録は app.py で **HTF Hard Block が候補リストを削った後**に行われる。
HTF-blocked 候補は本テーブルに **入らない** (可視化は `[DTE] HTF_HARD_BLOCK` の
stdout 行のみ)。したがって count=0 は「シグナルが出なかった」ではなく
**「select_best 段まで生き残った候補が無かった」**を意味する。

### 4.2 付随観測 — retention job が無い

`meta.rows` を露出させたのは、本テーブルに **削除・rotation 処理が存在しない**ため。
全 DT モード × 30s poll × 候補数で単調増加し、Render Disk を圧迫し得る。
本 PR では計測のみ (挙動不変)。retention は別途 R3 で要検討。

## 5. 次アクション (機械的)

1. デプロイ後 **1 週間以上**蓄積してから
   `GET /api/demo/evaluated-candidates?strategy=hull_donchian_fade&days=14&view=summary`
2. `total_candidates` と同期間の hull trade 数を突合し、残余 4.7x を
   **(a) select_best 段に到達していない** / **(b) 到達したが下流で落ちている**
   に二分する。(a) なら HTF Hard Block 側 (= `HTF_BLOCK_SHADOW_RESCUE` への hull 登録が
   4原則#3 の観点で要検討)、(b) なら `_tick_entry` の未計装 gate。
3. registry `t8-hull-shadow-freq` の `expected_per_week` は **signal-rate (13.3)** であり
   trade-rate ではない。突合に使う際は §3 の funnel を通すこと。
   2026-09-30 の retire 判定 (`shadow N<5`) もこの band 誤指定の上に乗っている。

## 6. 検証上の留保

- HTF 再現は MASSIVE 15m→4H resample + `EUR_USD_1d.parquet` を使用。本番は
  `fetch_ohlcv` + `TF_CFG` 経由で、日足境界がベンダー間で一致する保証はない
  ([[lesson-yfinance-jpy-daily-utc-shift-2026-08-18]] 系の既知の罠)。25.4% は ±数 pp の推定値。
- 本番 HTF は `df_h.iloc[-1]` = **進行中バー**を読む。再生では signal 時刻を含む
  バーで近似した。
- `recent_emit` 900s dedup の寄与は **ゼロ** (205→205、同方向 15m 以内の重複無し)。
- 保有時間分布は N=17 と小さい。median 0.57h は点推定。

## 7. 追記 (同日、デプロイ後の初回読み出し) — 2 つの新事実

読み出し経路が本番に乗った直後に `/api/demo/evaluated-candidates` を実行した
(このテーブルが**読まれたのは新設から 4 ヶ月で初めて**)。

`view=meta`: **517,378 行 / 54 戦略 / 2026-04-28 09:55 〜 2026-08-21 21:59**
(最終行が 08-21 なのは 08-22/23 が週末で市場閉鎖のため。retention 不在の実測値でもある)

### 7.1 hull は select_best に**勝っている** — 「敗者の側路」問題ではない

直近 30 日の hull: **total_candidates 1,139 / n_selected 998 (87.6%)**。

`LIVE_PROMOTE_LOSERS` に hull を登録した根拠 (2026-06-12 Codex review I-3) は
「score 3.0-5.0 は session_time_bias 等 ~6.0-6.5 に敗北し side-channel 不在だと
prod fires=0」だったが、**実測では hull が primary slot を取っている**。
side-channel の要否は別として、**残余 4.7x の原因は select_best 競争ではない**。

さらに hull は **08-07 / 08-11 / 08-12 / 08-13 / 08-18** にも候補を出して
selected になっている — すなわち最終 trade (08-06) 以降も**候補生成と選択は
継続していた**。→ 残余の落下点は **`_tick_entry` / order 層に確定的に絞られた**。

### 7.2 🔴 `bar_time` が live 行で全て NULL — C1 テーブルの第 2 の欠陥

取得した 1,139 行の `bar_time` は **全て NULL**。原因は call site:

```python
_log_cands(_db_path, _dt_candidates, _dt_best,
           instrument=symbol, tf=tf, bar_time=bar_time)   # ← live では常に None
```

`bar_time` が渡るのは BT 経路のみで、**live 経路
(`demo_trader._tick` → `compute_fn(df, tf, sr, symbol)`) は渡さない** —
2026-08-09 に修復した `ctx.hour_utc` 凍結 (PR #168) と**同一の call-site 欠落**
であり、そのとき同関数内の他の派生値は直したが本 call site は見落とされていた
(同型 **4 例目**)。

影響: `bar_time` は C1 テーブルで唯一 bar 粒度への正規化を可能にする列。NULL だと
**「1 バーを 30 秒 poll で 30 回記録した」と「30 本の別バー」が区別できない**。
実際 1,139 行は 12 日分の poll 膨張であって 1,139 バーではない。
→ funnel 分解 (候補 → select_best → trade) が**原理的に計算できない**。

fix (別 PR): PR #168 が確立した fallback `_dt_bar_dt`
(`bar_time or df.index[-1]`、UTC 正規化) を渡す。`df.index[-1]` は order 層 dedup の
`_closed_bar_ts_from_df` と同一基準なので `order_bar_dedup` の 1 バー 1 emit と
直接突合できる。counterfactual (旧コードに戻すと落ちること) を確認済み。

> 教訓: **「観測基盤を作った」は 3 段階ある — 書ける / 読める / 読んだ値が意味を持つ。**
> C1 は 4 ヶ月にわたり 1 段目しか満たしていなかった。読み出しを繋いだ瞬間に
> 2 段目の欠陥 (bar_time NULL) が即座に露出した = **読まれない計装は劣化を検知できない**。

### 7.3 残余 4.7x の localize は bar_time 修復後に再実行

§5 の next action は `bar_time` 非 NULL の行が 1 週間以上蓄積してから実行する
(それ以前の行は bar 粒度に正規化できないため funnel 分母に使えない)。

## 8. 残余 4.7x の帰属確定 (2026-09-11, rule:R3 — P8 localize 完結)

> **verdict**: 残余は **order 層 (OANDA 送信) ではなく、select_best 通過後の
> `_tick_entry` ガードチェーン内の 6 gate の合算**で全数説明された。
> さらに「未計装」の正体は「gate が計装されていない」ではなく
> **「計装が永続面を持たない」** (in-memory counter は再起動毎ゼロ +
> Render ログ実効 retention ~2 週) だった。本 PR で gate_block_daily
> 永続集計を併設 (記録のみ、挙動不変)。

### 8.1 readout (bar デデュープ + trades 全ページ突合)

`bar_time` 修復後の C1 行 (取得 1,230 行、うち非 NULL 973 行) を
unique (bar_time, instrument) にデデュープ (生行は 30s poll で **~52x inflation**
— 1 バーあたり polls 中央値 52):

| 量 | 値 |
|---|---|
| unique 候補バー (08-26〜09-10、16 日) | 20 |
| select_best 勝者バー | **18** (敗北 2: 09-01 07:30 → session_time_bias / 09-03 03:15 → zz_pivot_v60_sr) |
| 勝者バー rate | **7.9/週** — §3 funnel の offline 期待 7.61/週 と一致。**上流 (signal→HTF→直列化→select_best) は無傷** |
| 同期間の hull trade 行 (本番 /api/demo/trades 全ページ 2,517 行突合) | **1** (09-01 08:19 shadow、oanda_trade_id='') |
| **勝者バー生存率** | **1/18 = 5.6%** |

直近 7d の勝者バーは 4 本 (09-04 08:15 / 09-04 10:00 / 09-10 09:45 / 09-10 10:45)
で **全て trade 化ゼロ** — blocker-refutation t8-hull 行の前提を再確認。

### 8.2 勝者バー 1 本ずつの死因 (Render ログ SENTINEL_BLOCK_DIAG 突合)

hull は `_SILENT_DROP_DIAG_TYPES` 登録済みのため、`_block()` 発火は全て
`[SENTINEL_BLOCK_DIAG] hull_donchian_fade blocked at: <reason>` として stdout に
出る。当該バーの entry 窓 (bar close 後 ~15 分) を全て実査した:

| bar (UTC) | signal | 死因チェーン (時系列) |
|---|---|---|
| 08-26 04:45 | BUY | ⚠️ Render ログ失効 (実効 retention ~2 週) — 帰属不能 |
| 08-26 13:00 | BUY | ⚠️ 同上 |
| 08-27 00:30 | SELL | ⚠️ 同上 |
| 08-27 09:45 | BUY | ⚠️ 同上 |
| 08-31 08:00 | SELL | hedge_block(daytrade/EUR_USD:SELL) ×~13分 → score_gate(misalign:SELL,3.50) ×窓終端まで |
| 08-31 14:45 | SELL | same_price_5pip |
| 09-01 01:30 | BUY | session_pair(EUR_USD_Tokyo,WR=20%) |
| 09-01 07:45 | BUY | hedge_block ×~11分 → mtf_strong_bias(SELL_vs_BUY) |
| **09-01 08:15** | BUY | hedge_block ×7 tick → **08:19:43 に対向ポジ解消 → 通過 → shadow row 成立 (期間内唯一の trade)** |
| 09-01 14:15 | SELL | score_gate(misalign:SELL,3.47/0.05) |
| 09-02 01:00 | BUY | session_pair(EUR_USD_Tokyo) |
| 09-02 07:00 | BUY | score_gate(misalign:BUY,-0.28) |
| 09-03 01:30 | SELL | session_pair(EUR_USD_Tokyo) → score_gate(misalign:SELL,0.07..0.09) |
| 09-03 04:45 | SELL | same_price_5pip → score_gate(misalign:SELL,0.21) |
| 09-04 08:15 | BUY | [SHADOW] H8 alpha_scan で shadow 降格**後**に spread_guard(cost=1.6p/profit=4.5p=36%>20%) hard block |
| 09-04 10:00 | BUY | spread_guard(31%>20%) |
| 09-10 09:45 | BUY | spread_guard(36%/29%>20%) |
| 09-10 10:45 | BUY | same_price_5pip |

第一死因の分布 (帰属可能な kill 13 本): **spread_guard 3 / same_price 3 /
session_pair(Tokyo) 3 / score_gate 2 / hedge_block 2** (+二次死因として
score_gate 3、mtf_strong_bias 1)。

### 8.3 構造的読み (挙動変更はしない — 記録と帰属のみ)

1. **order 層は無実**。ガードチェーンを通過した唯一の 1 件 (09-01 08:15) は
   正常に shadow row 化した (`OANDA [SKIP] shadow_tracking`)。残余の落下点は
   `_tick_entry` ガードチェーン内で完結。
2. **単一 gate ではなく合算**。「どれか 1 個の犯人」を探す問いは不成立 —
   時間帯 (Tokyo)・方向 (SELL×score 符号)・経済性 (spread/TP 比)・同時
   ポジション (hedge/same_price) の 4 系統が独立に削っている。
3. hull 固有の構造衝突が 2 つ:
   - **spread_guard × TP=basis 契約**: hull は高WR/低RR 設計 (TP 近接、RR~0.25
     契約 — RR 床 2 箇所は既に免除済み) だが、spread_guard (往復 spread/TP >20%)
     には免除が無い。EUR_USD spread 0.8p で TP dist 4.4-5.6p → 29-36% で常時
     閾値超え。**spread が平常でも TP が近いだけで死ぬ**。
   - **score_gate × SELL**: hull SELL が正 score のまま score_gate に届く tick
     は全滅 (misalign:SELL,+3.5 等)。SELL 側勝者バー 5 本中 4 本で発火。
4. **shadow 蓄積も削られている**: 09-04 08:15 は alpha_scan H8 で既に
   `_is_shadow=True` になった後、spread_guard の hard block (行ゼロ) で消えた。
   これらの gate の shadow 分岐は `_is_shadow_eligible_full` (静的 tier) を見て
   おり、動的 `_is_shadow` を見ない。hull は LIVE 意図的例外 (FORCE_DEMOTED/
   Sentinel ではない) のためどちらの資格も持たず、**shadow 行として残る道が
   ない**。4原則#3 (Shadow 蓄積は削らない) とのテンションは実在するが、
   gate 挙動の変更は R1/R2 の別決裁 — 本 PR は帰属確定と計装のみ。

### 8.4 「残余=未計装」の正体 — 計装はあった、永続面が無かった

killer gate は全て `_block()` 経由で (i) in-memory `_block_counts(_per_strategy)`
に計上済み、(ii) hull は SENTINEL_BLOCK_DIAG ログにも出ていた。それでも 49 日+
診断不能だった理由:

- **in-memory counter は再起動/デプロイ毎にゼロ**。本番実測 (2026-09-11):
  `/api/demo/block-counts` は total=9 / hull の per_strategy_counts={} —
  同時刻の Render ログには hull block が毎日出ているのに、永続面からは
  「blockゼロ」に見えた (§3.3 の観測と同一の罠)。
- **Render ログ実効 retention ~2 週**: 08-26/27 の勝者バー 4 本は本診断時点で
  既に帰属不能 (carry-dip 08-27 証拠の時限消滅と同型)。

**fix (本 PR)**: `gate_block_daily` (day×mode×entry_type×instrument×reason の
日次集計、retention 90d) を新設。`_block()` → `_record_entry_block` と
order_bar_dedup の両経路から best-effort 永続化。読み手は
`/api/demo/block-counts?days=N` の `persisted` セクション (writer と同一
コミット、write-only 禁止則)。estimand 宣言 `gate_block_attribution` +
counterfactual テスト (`tests/test_block_event_logger.py`) 同梱。
**per-tick 計数のままなので unique bar 数として読まないこと** (較正は
本表 §8.1 のとおり C1 側でデデュープして行う)。

### 8.5 registry `t8-hull-shadow-freq` / 09-30 retire 判定への含意

- 頻度 band 割れの実体 = **「シグナル枯渇/エッジ消滅」ではなく「下流 gate に
  よる shadow 蓄積遮断」**。シグナル生成器と select_best 競争は期待レート
  どおり動いている (§8.1: 7.9/週 vs 期待 7.61/週)。
- したがって **shadow N<5 を根拠とする 2026-09-30 の retire は誤帰属**になる。
  registry message に注記済み。retire/復帰/gate 免除の判断は
  gate_block_daily の帰属データを経由すること。
- 付随観測 (別 issue 候補、本 PR 非対象): (a) same_price ブロックのログ表記が
  `same_price_0pip` (`{dist*100:.0f}` が非 JPY で 0.05→"0" と印字するラベル
  バグ、カウンタキーへの影響なし)。(b) score_gate が hull SELL を構造的に
  殺している件は sign-flip 経路 (app.py) との整合監査が必要。

## 関連
- [[t8-week1-gate-breach-2026-07-06]] (§89 で本件を「独立の問題」として残置)
- [[lesson-select-best-bottleneck-2026-04-28]] (C1 テーブルの設置根拠)
- [[zero-fire-diagnosis-carrydip-vix-2026-07-02]] (sweep の HTF gate 100% silent drop)
- MEMORY: `project_trigger_reachability_evaluator_fix_2026_08_19` (条件付きトリガの滞留)
- MEMORY: `project_dt_ctx_hour_utc_live_freeze_2026_08_09` (同型 call-site 欠落の 3 例目)
