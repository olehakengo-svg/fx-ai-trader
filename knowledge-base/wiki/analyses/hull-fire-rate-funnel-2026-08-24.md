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
  ([[lesson-vendor-daily-boundary]] 系の既知の罠)。25.4% は ±数 pp の推定値。
- 本番 HTF は `df_h.iloc[-1]` = **進行中バー**を読む。再生では signal 時刻を含む
  バーで近似した。
- `recent_emit` 900s dedup の寄与は **ゼロ** (205→205、同方向 15m 以内の重複無し)。
- 保有時間分布は N=17 と小さい。median 0.57h は点推定。

## 関連
- [[t8-week1-gate-breach-2026-07-06]] (§89 で本件を「独立の問題」として残置)
- [[lesson-select-best-bottleneck-2026-04-28]] (C1 テーブルの設置根拠)
- [[zero-fire-diagnosis-carrydip-vix-2026-07-02]] (sweep の HTF gate 100% silent drop)
- MEMORY: `project_trigger_reachability_evaluator_fix_2026_08_19` (条件付きトリガの滞留)
