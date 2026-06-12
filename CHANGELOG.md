# FX AI Trader - Changelog

## 2026-06-12 — fix: fib_reversal 恒久退役 — Edge Factor Audit #3 (rule:R2)

### 変更内容

`SHADOW_RETIRED_STRATEGIES` に `fib_reversal` を追加 (Shadow 含め全ペア恒久停止)。
LIVE 側は v6.8 FORCE_DEMOTED 済みのため変更なし。カードの v8.2 Recovery Path は失効。

### 根拠 (詳細: wiki/learning/edge-factor-audit-2026-06-12-fib-reversal.md)

- clean N=638。friction 1.49p = median TP 5.1p の 29.2%、BE-WR 41.7% vs 実測 29.5%
- 全 7 pair×dir セル net 負け (LIVE 全ペア含む)、敗者 MAFE favorable 中央値 0.2p
- 直近 30d N=251 / −321.7p — 現役最大の Shadow 出血源
- 統合先なし: 同思想 DT 版 sr_fib_confluence は gross −1.18 (パターン B、#5 で監査予定)


## 2026-06-12 — fix: bb_rsi_reversion 統合退役 — Edge Factor Audit #2 (rule:R2)

### 変更内容

`modules/shadow_demote_registry.py` の `SHADOW_RETIRED_STRATEGIES` に
`bb_rsi_reversion` を追加 (Shadow 含め全ペア恒久停止)。既存防御
(pair whitelist / per-cell registry / OANDA_TRIP) は残置し最終層を不可逆化。

### 根拠 (詳細: wiki/learning/edge-factor-audit-2026-06-12-bb-rsi-reversion.md)

- clean N=780。gross EV +0.50〜+0.61 で思想は正、だが friction 1.2-1.5p が
  median TP 5.2p の 24.7% を占め BE-WR 40.9% vs 実測 WR 35.4% で算数的に不成立
- 同思想 DT 版 dt_bb_rsi_mr (friction 10.8%/TP) は net +1.72 / PF 1.61 / N=105 で生存
  → 家族代表に指名、promotion pre-reg LOCK (N≥165 ∧ Wilson_lo≥0.40) を学習レポートに固定
- 12y MASSIVE BT REJECT (2026-06-11) / MA フィルタ罠の当事者 / 封じ込め 3 段漏れ


## 2026-06-12 — fix: ema_trend_scalp 恒久退役 — SHADOW_RETIRED_STRATEGIES 新設 (rule:R2)

### 変更内容

Edge Factor Audit #1 (clean N=1,117) で ema_trend_scalp の KILL を確定。
per-cell registry (2026-05-08) では EUR/GBP/JPY しか止まらず、Phase B-1
HourlyEngine slot `daytrade_1h_usdchf` から USD_CHF が漏れ続けていた
(直近 30d N=55, WR 3.6%, PF 0.03 — 全データ中最悪セル)。

`modules/shadow_demote_registry.py`:
- `SHADOW_RETIRED_STRATEGIES` frozenset 新設 — 戦略単位の全ペア恒久退役。
  将来 mode/pair が追加されても閉じる
- `is_shadow_demoted()` が retirement を per-cell より先に評価
- `ema_trend_scalp` を登録

`tests/test_shadow_demote_registry.py`: retirement 検証 3 ケース追加 (USD_CHF /
未知ペア / 他戦略の per-cell 挙動維持)。

### 根拠 (詳細: wiki/learning/edge-factor-audit-2026-06-12-ema-trend-scalp.md)

- 全 8 pair×dir セル均一負け (PF 0.03〜0.77) — SIZE lever 適用対象なし
- BE-WR 33.1% (TP/SL=2.03) vs 実測 WR 19.2%
- 敗者 MAFE favorable 中央値 0.5p — エントリーに予測力なし、反転も gross EV≈0 で不成立
- 月次 WR 20.8% → 16.1% → 6.5% の加速劣化
- 2026-05-15 redesign スレッド (aligned×BUY×GBP_USD N=10) は post-hoc selection としてクローズ

LIVE 側は v9.2 FORCE_DEMOTED 済みのため変更なし。Shadow のみの挙動変更。


## 2026-06-01 — fix: session_time_bias × GBP_USD symmetric cell-conditional revival (rule:R2)

### 変更内容

2026-05-29 cell forensic で EUR_USD London は cell-conditional revival したが、
GBP_USD London (Shadow N=45 Wlo=0.251 EV=+0.98 PF=1.19) も plus EV cell に
もかかわらず pair-level PAIR_DEMOTED に保留していた非対称を修正。

`modules/demo_trader.py`:
- `_PAIR_DEMOTED` から `("session_time_bias", "GBP_USD")` 削除 (2026-05-03 R2 LOCK supersede)
- `_PAIR_PROMOTED` に `("session_time_bias", "GBP_USD")` 追加
- `_PAIR_SESSION_FILTER` に `("session_time_bias", "GBP_USD"): {"London"}` 追加 (EUR_USD と同条件)

### 根拠

- EUR_USD London cell-conditional treatment と同じ統計水準を満たす:
  - EUR_USD London: N=58 Wlo=0.327 EV=+1.44 PF=1.41
  - GBP_USD London: N=45 Wlo=0.251 EV=+0.98 PF=1.19
- Wlo 差 0.076 は判定を真逆にする統計的根拠なし
- Memory `[vix_carry_unwind Overlap pilot 2026-05-13]` の前例: PAIR_DEMOTED → cell-conditional 復活と完全同型パターン
- 私 (Claude) の初版 (2026-05-29) は保守的 cutoff (Wlo>0.30) で除外したが、user 指摘で symmetric treatment に修正

### 検証

- `python3 -m pytest tests/test_cell_forensic_2026_05_29_pin.py tests/test_volume_live_promote_routing.py -v` → 14/14 PASS
- `test_session_time_bias_gbp_usd_pair_demoted_unchanged` は廃止、`test_session_time_bias_gbp_usd_cell_conditional_london` に置換 (PAIR_DEMOTED 排除 + PAIR_PROMOTED + SESSION_FILTER 検証)

### Watchdog 監視

- Live N≥10 EV<0 で `volume_live_promotion_watchdog` が自動 demote
- Cell-conditional のため、London 限定 fire のみ評価対象 (Asia/NY/Overlap は SESSION_FILTER で SKIP)

## 2026-05-29 — feat: cell-forensic Tier reorg for xs_momentum / session_time_bias (rule:R2)

### 背景

2026-05-29 backfill (commit d0284435) で `oanda_trades.strategy` を chain resolver 経由で再帰属。Live EV/N の精度が向上した結果、user 指摘「集計じゃなく cell で見るべき」を受け、Shadow デモトレード ~5,000 行を pair × session × direction × cohort で分解。

### 変更内容

#### A. `xs_momentum` — 戦略全体 Shadow-only に降格

`modules/demo_trader.py`:
- `_PAIR_PROMOTED` から `("xs_momentum", "GBP_USD")` / `("xs_momentum", "EUR_USD")` を削除 (元 lines 7014-7018, v8.9 根拠)
- `_PAIR_DEMOTED` に `("xs_momentum", "EUR_USD")` / `("xs_momentum", "GBP_USD")` を追加 (USD_JPY は既存 v8.6)

**根拠 (Shadow cell forensic)**:
- 6 cell (pair × direction) 全てで Wilson_lo<0.30 → Bonferroni m=6 で全棄却
- `current` cohort (post 2026-05-21) Shadow N=91 WR=14.3% EV=-5.15pip → 完全崩壊
- Live N=7 EV=+0.56 は pre-H1gate 単発 +22p outlier に押された noise

#### B. `session_time_bias` — Cell-conditional Live + Lot Boost 解除

`modules/demo_trader.py`:
- L6850: `_STRATEGY_LOT_BOOST["session_time_bias"]` を **1.3 → 1.0** (cell-blind boost 解除)
- L7208 `_PAIR_SESSION_FILTER` に `("session_time_bias", "EUR_USD"): {"London"}` 追加
- `("session_time_bias", "GBP_USD")` PAIR_DEMOTED は維持 (2026-05-03 R2 LOCK)
- `("session_time_bias", "EUR_USD")` PAIR_PROMOTED は維持、London session 限定で Live 発火

**根拠 (Shadow cell map)**:
| cell | N | Wilson_lo | EV (pip) | PF | 判定 |
|---|---|---|---|---|---|
| EUR_USD London | 58 | **0.327** | **+1.44** | **1.41** | ✅ edge |
| EUR_USD Overlap | 34 | 0.146 | -1.88 | 0.63 | 🔴 |
| GBP_USD Asia | 47 | 0.012 | -6.10 | 0.06 | 🔴 toxic |
| GBP_USD NY | 15 | 0.012 | -7.03 | 0.18 | 🔴 toxic |

Cell-blind 1.3× boost は EUR_USD London を +1.87 EV に強化する一方、Overlap/NY/GBP_USD の毒 cell も同倍率で被弾するため非対称リスク。

#### Decision docs

- `knowledge-base/wiki/decisions/xs-momentum-pair-demote-2026-05-29.md`
- `knowledge-base/wiki/decisions/session-time-bias-cell-forensic-2026-05-29.md`

#### Tests

- 新規: `tests/test_cell_forensic_2026_05_29_pin.py` (9 件) — Tier config を regression pin
- 更新: `tests/test_volume_live_promote_routing.py` — `VOLUME_CELLS` から `("xs_momentum", "GBP_USD")` 削除、cell-conditional cell の `_is_promoted` 時刻依存を考慮した assertion へ修正

### 検証

- `python3 -m pytest tests/test_cell_forensic_2026_05_29_pin.py tests/test_volume_live_promote_routing.py -v` → 14/14 PASS
- `python3 -m pytest tests/ -q` → **1683 passed**, 1 skipped, 1 xfailed
- `python3 scripts/check.py` → 6/6 通過

### 再復活条件 (Pre-reg LOCK)

両戦略とも以下を満たすまで現状維持:
- 該当 cell で Live N≥30 + Wilson_lo>0.40 + EV>+1.0 pip
- Bonferroni-corrected p<0.05 (m=4-6 cells)
- 3 cohort 連続で同一 cell が edge 維持

## 2026-05-29 — feat: oanda_trades.strategy chain-resolver backfill + /oanda-analysis UX (rule:R3)

### 変更内容 (B: 歴史的孤児 backfill)

- `tools/backfill_oanda_strategy_2026_05_19.py` を two-phase resolver に拡張:
  1. **Chain via `oanda_trade_id → demo_trade_id → sent row`** (時間 window 不要)。`PYR_<parent>` prefix の demo_trade_id を持つ filled 行は親の sent 行へ直接 chain。pre-fix (commits a7b18453 / 4cd44956 in 2026-05-20/05-26) で sent 行を書かなかった PYR 孤児の唯一の確実な経路。
  2. **Nearest-sent time-window fallback** (既存 `DemoDB.resolve_oanda_strategy_from_audit`、5min default)。
- 全クエリは `?` parameterized (`modules/demo_db.py` は不変、Semgrep false-positive pre-existing patterns に触らない方針)。
- 新規テスト `tests/test_oanda_strategy_chain_resolution.py` (7 件):
  - direct demo_trade_id chain / PYR parent chain / mode-label rejection / unknown trade / empty input / dry-run-no-write + apply-writes 2-phase E2E
- 監査: prod の 13 件 (units=10000 / 2026-04-14〜2026-05-19) のうち、PYR pattern (同分秒 dup pairs 6 件) は parent chain で resolve 可能と推定。残り signal-less 7 件は coverage 外 (legacy として保持)。
- 実行コマンド (Render shell):
  ```
  python3 tools/backfill_oanda_strategy_2026_05_19.py --dry-run
  python3 tools/backfill_oanda_strategy_2026_05_19.py --apply
  ```

### 変更内容 (C: /oanda-analysis UX)

- `templates/oanda_analysis.html` 監査ログ card の card-title に「動的サイジング」tooltip 注記を追加。
- Tooltip 内容: 「3-Factor 動的サイジング: Risk × Edge × Boost。各 trade の SL距離・ATR/Spread・戦略ブースト・DD防御で決定。1000u=0.01lot, 10000u=0.10lot (base)」
- 「バグではない仕様」と明示し、1000〜30000u の units variance が user 質問源にならないように。
- 副次: `<script src="https://unpkg.com/lightweight-charts...">` に SRI `integrity` + `crossorigin` 属性を追加 (Semgrep CWE-353 警告解消)。

### 検証

- `python3 -m pytest tests/test_oanda_strategy_chain_resolution.py tests/test_pyr_attribution.py tests/test_oanda_audit_join_invariant.py -v` → 13/13 PASS
- `python3 -m pytest tests/ -q` → 1674 passed (1667 + 7 新規) / 1 skipped / 1 xfailed
- `python3 scripts/check.py` → 6/6 PASS

## 2026-05-29 — fix: oanda_audit filled 行が MODE 名で記録される UX バグ修正 (rule:R3)

### 変更内容

- `modules/oanda_bridge.py::open_trade` の filled 監査行の `entry_type` を `mode` ハードコードから `_audit_entry_type` (caller が `entry_type` を渡せばその戦略名、未指定なら mode にフォールバック) に変更。
- `open_trade` に `skip_sent_audit: bool = False` パラメータを追加。demo_trader メインエントリパスが自前で sr_meta 付きの sent 行を書く場合に bridge 側の sent 重複書込みを抑止する。
- `modules/demo_trader.py` メインエントリパス (L5649) が `entry_type=entry_type, skip_sent_audit=True` を渡すように変更。これにより `/oanda-analysis` の監査ログで filled 行に戦略名が表示される (従来は `scalp`/`daytrade`/`daytrade_eurjpy` 等の MODE 名のみ表示)。
- 影響範囲:
  - JOIN invariant (`DemoDB.get_oanda_trades` の `a.bridge_status='sent'` フィルタ) は不変、Kelly/WR 集計に影響なし。
  - `oanda_trades.strategy` の backfill resolver は `bridge_status='sent'` のみ参照するため、新規 fire は引き続き正しく resolve される。
  - PYR / resend 経路は既存挙動 (`entry_type` を渡し、`skip_sent_audit` は False) なので bridge 側で sent + filled の両方に戦略名が書かれる。
- 残課題: 過去 13 件の `oanda_trades.strategy=NULL` 孤児 (units=10000 / 2026-04-14 〜 2026-05-19) は別 issue。queued task `20260519-1832-fix-pyr-strategy-attribution-and-dedup.md` (Group B 同時刻 dup fire / Group C signal-less fire) で対応予定。

### 根本原因

`oanda_audit.entry_type` 列は dual-purpose (sent=戦略名 / filled=mode 名) で memory `reference_oanda_audit_twin_meaning.md` に既載。UI が同列を生表示しているため、filled 行が戦略名未記載に見えていた。Live 5 件 (2026-05-26 〜 2026-05-28) の実測でこの schema 二義性の UX 影響を確認。

### 検証

- `python3 -m pytest tests/test_pyr_attribution.py tests/test_oanda_audit_join_invariant.py -v` (6/6 PASS、新規 2 件含む)
- `python3 -m pytest tests/ -q` (1667 passed, 1 skipped, 1 xfailed)

### 新規テスト

- `test_main_entry_path_skip_sent_audit_no_duplicate_sent_rows`: メインパス (skip_sent_audit=True) が重複 sent 行を書かず、filled 行が戦略名を持つことを保証。
- `test_filled_row_falls_back_to_mode_when_no_entry_type`: caller が entry_type を渡さない場合の mode フォールバックを documentation。
- `test_oanda_bridge_writes_sent_audit_with_strategy_before_market_order` の filled-row assertion を更新 (`""` → strategy 名)。

## 2026-05-18 — fix: /api/oanda/stats の range 無視を修正

- `/api/oanda/stats` で `range=today|7d|30d|all`、`rolling_days`、`all_time`、`date_from/date_to` を解釈し、既定 30d + fidelity cutoff の window に統一。
- OANDA stats/equity の既定集計から `XAU_USD` を除外し、`exclude_xau=0` で明示的に含められるように変更。
- `_filters` と `_db_path` を返却し、UI 表示と backend 集計条件の不一致を検査可能にした。

## 2026-05-18 — feat: Price-Shock Rev Tier 1 5戦略 Live activation v2 MIN lot (rule:R1)

### 変更内容

- 5 Price-Shock Rev H1 戦略を `_FORCE_DEMOTED` / `_shadow_always` から外し、該当 5 pair を Tier 2 Live MIN lot に移行。
- Live lot は 1000u 固定。Kelly / DD / lot multiplier による ramp は bypass し、lot ramp は N>=30 evaluator の提案のみ。
- EUR_GBP/EUR_AUD shared lock を Live でも維持し、同時 active position 1 個までに制限。
- `price_shock_rev_live_watchdog.py` と `price_shock_rev_promote_evaluator.py` を追加し、N>=10 auto-demote と N>=30 lot-ramp 提案を分離。
- Decision: `knowledge-base/wiki/decisions/price-shock-rev-live-activation-2026-05-18.md`。

### 検証

- `.venv/bin/python -m pytest tests/test_price_shock_rev_live_activation_v2.py tests/test_hourly_engine_shadow_ramp.py tests/test_force_demoted_leak_backfill.py::test_force_demoted_final_gate_overrides_late_live_bypass -q`

## 2026-05-18 — feat: HourlyEngine Shadow ramp activation

### 変更内容

- 全 10 `daytrade_1h*` modes を `auto_start=True` に変更し、HourlyEngine の H1 bar 評価を起動。
- `HourlyEngine._shadow_always` に KSB+DMB+5 PriceShockRev を frozenset 固定し、H1 戦略を Shadow-only ramp に統一。
- XAU modes と既存 scalp / 15m daytrade Live 経路は変更なし。
- Decision を `knowledge-base/wiki/decisions/hourly-engine-shadow-ramp-2026-05-18.md` に追加。

### 検証

- `pytest tests/test_hourly_engine_shadow_ramp.py -v`
- `pytest tests/test_price_shock_rev_strategies.py -v`
- `pytest tests/test_aud_nzd_pair_surface.py -v`
- `python3 tools/tier_integrity_check.py --check`

## 2026-05-18 — feat: ob_retest_h1 1095d re-test pre-reg 2nd attempt FAIL

### 変更内容

- `tools/ob_retest_h1_1095d_bt.py` を追加し、2023-05-15 13:00 UTC → 2026-05-15 13:00 UTC の 1095d MASSIVE H1 BT を実行。
- 5 pair 全てを同一 LOCKED parameter / friction / PASS criteria で評価し、結果を `raw/bt-results/ob_retest_h1_1095d_2026_05_18.json` に保存。
- Verdict は FAIL。USD_JPY は aggregate N/WR/Wilson_lo/EV/PF を満たしたが、WF h1 EV=-1.8146 のため locked PASS 不成立。
- `ObRetestH1.enabled = False` を維持し、M5/H1 OB retest 系統を promotion candidate として退役記録。
- 2nd pre-reg decision、1st LOCK 追記、strategy card の 365d vs 1095d 比較表を更新。

### 検証

- `.venv/bin/python tools/ob_retest_h1_1095d_bt.py` — verdict=FAIL
- `.venv/bin/python -m pytest tests/test_ob_retest_h1.py -x -v` — 6 passed
- `.venv/bin/python -m pytest tests/ -x -q` — 1517 passed, 1 skipped, 1 xfailed
- `.venv/bin/python tools/tier_integrity_check.py --check` — ERROR=0, WARN=1 (`ob_retest` legacy inline label has no strategy file)

## 2026-05-18 — feat: ob_retest_h1 pre-reg FAIL + M5 ob_retest R2 demote

### 変更内容

- `strategies/hourly/ob_retest.py` に H1 Order Block Retest を追加し、LOCKED parameter で `HourlyEngine` に登録。
- 365d MASSIVE 5 pair BT を保存し、pre-reg 判定は全 pair N<200 のため FAIL。ロールバック規律どおり `ObRetestH1.enabled = False` を維持。
- M5 `ob_retest` を `_FORCE_DEMOTED` に追加し、OB 系統の評価対象を H1 pre-reg に移行。
- pre-reg LOCK と戦略カードを追加し、KB index / tier-master を同期。

### 検証

- `.venv/bin/python -m pytest tests/test_ob_retest_h1.py -x -v` — 6 passed
- `python3 tools/tier_integrity_check.py --check` — ERROR=0, WARN=1 (`ob_retest` legacy inline label has no strategy file)
- `.venv/bin/python tools/strategies_drift_check.py` — all 92 pages integrity-clean
- `.venv/bin/python -m pytest tests/ -x -q` — 1510 passed, 1 skipped, 1 xfailed

## 2026-05-18 — feat: Price-Shock Reversion Tier 1 を Phase B-1 Shadow 投入

### 変更内容

- `strategies/hourly/price_shock_reversion_base.py` と 5 wrapper を追加。BT runner と同じ `shift(1)` / `rolling(..., min_periods=252)` / vol quintile ロジックで H1 negative shock LONG を評価。
- `HourlyEngine` と `demo_trader` に 5 戦略を登録し、`_FORCE_DEMOTED` で Shadow-only を強制。EUR_GBP/EUR_AUD の shared lock と horizon/SL exit handling を追加。
- MASSIVE parquet を読む unit test で 5 ペア全 bar の BT runner 一致と catastrophic SL distance を検証。
- KB 戦略カード 5 件と Shadow -> Live promote pre-reg criteria を追加し、tier-master/index を再生成。

### 検証

- `PATH=.venv/bin:$PATH python3 -m pytest tests/test_price_shock_rev_strategies.py -v` — 7 passed
- `PATH=.venv/bin:$PATH python3 tools/tier_integrity_check.py --check` — ERROR=0
- `PATH=.venv/bin:$PATH python3 -m pytest tests/ -x -q` — pre-existing `tests/test_bt_data_loader_parquet_fallback.py::test_fetch_ohlcv_uses_parquet_after_online_failures` で停止

## 2026-05-15 — fix: BT default を TV-aligned に反転 (BE/Trail off) [rule:R3 — 算数破綻]

### 動機

ユーザー指示「基本BTが楽観すぎることが課題なのでtvbtと合わせてください」を受け、Python BT が TV BT (Pine `strategy()` replica) より systematic に WR を inflate していた問題を修正。

### 根本原因

`run_daytrade_backtest` の BE/Trail 機構 (app.py L6788-6898) が、BE activated 後の SL touch を `outcome="WIN"` with `tp_m_actual = 0.6 × tp_dist` としてカウントしていた。実際の BE close は ~0pip 利益で、これは「架空の WIN」。ablation BT (`wiki/analyses/divergence-ablation-2026-05-14.md`) で xs_momentum × USD_JPY × 318d × 15m で `no_BE_trail` variant が WR 62.7% → 39.8% (−22.9pp) を測定、TV BT WR 43.5% と sampling noise 範囲内で整合することを確認。

### 変更内容

- **app.py L6351-6362** — BT default を反転: `_BT_ABLATE_BE_TRAIL = True` (default off)。`BT_OPTIMISTIC=1` 環境変数で旧 (inflated) 挙動を復元可能 (transition 期間用)。Quick Harvest は TV Pine 側にも近い挙動があり、`no_QH` で TV より低くなるため default keep。
- **app.py L6287** — cache key に `_opt{BT_OPTIMISTIC}` segment 追加 (旧 cache を invalidate)
- **knowledge-base/wiki/analyses/divergence-ablation-2026-05-14.md** — 「2026-05-15 追記」セクションで反転実装と検証結果を記録、KB 上の既存 BT 値が legacy (inflated) であることを明示

### 検証

- xs_momentum × USD_JPY × 318d × 15m 新 default: N=118 WR=**39.8%** EV=-0.521 (TV BT 43.5% と sampling noise 範囲内 ✓)
- `BT_OPTIMISTIC=1` で legacy 復元: N=156 WR=60.3% EV=+0.035 (旧 baseline N=158 WR=62.7% と微差 < 3pp)
- `python3 scripts/check.py` 全6チェック通過

### 既存への影響

- production paths (`backtest_mode=False`): **不変** — BE/Trail logic は production 実行 path に存在せず、本変更は BT simulation の outcome 計上ロジックのみに影響
- 既存 BT 結果 (`comprehensive-bt-scan-2026-05-14.json`, `tier-master.md` の EV/WR): 全て legacy (inflated) 値。新規 promote 判定の core base は新 default 値を使う必要あり (rough upper bound として legacy 値を併用)
- ablation tool `tools/bt_divergence_ablation_2026-05-14.py` の baseline 列: 旧 default 値。再現には `BT_OPTIMISTIC=1` を設定

## 2026-05-11 — fix: _rt_patch クロスペア価格汚染 (USD/JPY スカラを全ペアに適用していた) [rule:R3 — 構造バグ]

### 動機

ユーザーから `/demo-analysis` Trade Log の pip 表示異常を報告。production DB を確認したところ、本日 2026-05-11 4:38–4:57 UTC に GBP_USD / GBP_JPY / EUR_JPY の 12 件の SL_HIT が全て `exit_price ≈ 157.147` (USD/JPY の現スポット値) で記録され、Equity / DD / Kelly が大幅汚染されていた。同時刻に OANDA 401 (auth 障害) が発生していた。

### 根本原因

`modules/data.py:_rt_patch` (line 780-) は `_price_cache` の値で 1m/5m DataFrame の最終足 Close/High/Low を上書きするが、`_price_cache` は `/api/price?symbol=USD/JPY` で USD/JPY のみ格納される共有スカラ。にもかかわらず `_rt_patch` は `symbol in _OANDA_SYMBOLS` 全てで cache を読みに行っており、USD/JPY スポットを他ペアの Close として書き込んでいた。

通常は (2) OANDA fetch で上書きされ顕在化しないが、OANDA 401 障害時にこのパスが残り、SLTP-Checker が SL_HIT 判定で 12 件をまとめて誤決済 → `close_trade(157.147)` が DB に書込まれた。

### 変更内容

- **modules/data.py:_rt_patch** — `_price_cache` 参照を `symbol in ("USDJPY=X", "JPY=X")` で guard。他ペアは OANDA → yfinance → parquet の fallback のみを使用する形に限定 (production-parity 維持)。
- **scripts/cleanup_rt_patch_contamination_2026_05_11.py** — 12 件の corrupted trade を `outcome=BREAKEVEN`, `pnl_pips=0`, `close_reason='SL_HIT_CORRUPTED_EXCLUDED'` に修正し、system_kv の eq_current / eq_peak / dd_lot_mult / defensive_mode を再計算するワンショット script (idempotent / dry-run default)。post-deploy で `--apply` 実行予定。
- **knowledge-base/wiki/lessons/lesson-rt-patch-cross-pair-contamination-2026-05-11.md** — 失敗モード分析、中期改善案 (`_price_cache` を dict 化、`|pnl_pips|>500p` sanity gate、障害時 unit test) を記録。

### 検証

- inline test: GBPUSD=X DataFrame Close が `_price_cache` (USD/JPY=157.147) で汚染されないこと確認、USDJPY=X は引続き patch される
- `python3 -m pytest tests/ -q --ignore=tests/test_flag_drift_backfill.py -k "data"` 39 passed (regression なし)
- `python3 scripts/check.py` 全6チェック通過

### 既存への影響

- USD/JPY (USDJPY=X / JPY=X) の rt_patch 挙動: 不変 (production-parity)
- 他ペア (EUR/USD, GBP/USD, GBP/JPY, EUR/JPY, EUR/GBP, XAU/USD): cache 経路を停止。OANDA/yfinance/parquet の fallback のみ → 通常時は実質同等、OANDA 障害時に**汚染データが流れない**ように変更

### Follow-up (別タスク)

1. post-deploy で `scripts/cleanup_rt_patch_contamination_2026_05_11.py --apply` を Render shell で実行 → DB 12 件 + system_kv 修正
2. `_price_cache` を `{symbol: {...}}` dict 化 → symbol guard を構造的に強制 (lesson 中期項目)
3. `close_trade` 直前の `|pnl_pips|>500p` sanity gate (lesson 中期項目)
4. OANDA 401/5xx 時の SLTP-Checker 動作を unit test で固定化

---

## 2026-04-30 — bt_vec_harness Level 3 production-parity toggles [rule:R1-bypass / additive]

### 動機

既存 `modules/bt_vec_harness.py` は per-strategy raw 評価のみで、`ctx.sr_levels=[]`、`layer0/1/2/3={}`、`regime={}`、`session={}` を空辞書として渡していた。これにより `compute_scalp_signal` のように SR/Layer/Regime/Session を参照する戦略は production と挙動が乖離。365 日 BT で Tier 判定基盤を高速化する目的で、これらを harness で埋められるようにする (master plan: `bt-serialized-willow.md` Phase E)。

### 変更内容

- **modules/bt_vec_harness.py** — `HtfFeatureSpec` に opt-in トグル群を追加 (全 default False)
  - **Tier A**: `inject_sr_levels` (`find_sr_levels_weighted` を `sr_recalc_interval=100` 毎に pre-compute)、`inject_master_bias` (`_compute_bt_htf_bias` を harness 内に再実装、`htf_recalc_interval=60` 毎に cache)
  - **Tier B**: `inject_layer_scores` (Layer 0/2/3 を per-bar 計算、app からの lazy-import)、`inject_regime` (`detect_market_regime` per-bar)
  - **Tier C**: `inject_session` (bar-time 連動 `get_session_info` 相当)、`apply_score_gate` (production R2-A suppress gate を post-evaluation で適用)
- **HTF bias 再実装**: `_compute_htf_bias_for_window()` を harness 内に新設し app.py の Flask init を回避。挙動は app.py:`_compute_bt_htf_bias` (4644-4776) と同一 (将来 production 側変更時に同期必須 — lessons/bt-live-divergence)
- **Layer 1 master bias**: `_fetch_layer1_static()` で BT 開始時に 1 回だけ `get_master_bias` を呼出し ctx.layer1 に注入 (production の MASTER_BIAS_TTL キャッシュ挙動と等価)
- **score gate (Tier C)**: `_apply_score_gate()` で `apply_r2a_suppress_gate` + `_bt_spread`/spread_q を計算し、conf=0 になった候補をドロップ。fail-open

### 検証

1. **既存 4 cell BT bit-identical 確認**: `_bt_mtf_cascade_scalp_vec.py --days 7` 全トグル off で:
   - USDJPY × mtf_trend_follow: N=1 WR=100% EV=+12.5p (旧と同一)
   - USDJPY × mtf_counter_trend: N=3 EV=-7.2p (acceptance criteria と一致)
   - EURUSD × mtf_counter_trend: N=4 EV=+0.47p PF=1.168 Kelly=7.187% (acceptance criteria と完全一致)
2. **全トグル on smoke test**: USDJPY × mtf_counter_trend 7d
   - SR cache 70 snapshots / HTF bias cache 119 snapshots build 成功
   - Layer 0/2/3、regime、session、layer1 master bias 注入正常動作
   - eval=40.5s (旧 10.3s) — 4× 増、90d 換算 ~6-7 分 (目標 30 分以内に余裕)
   - 同戦略は新 ctx 参照しないため N=3 EV=-7.2p で同一 (期待通り)

### 既存への影響

- **既存 4 cell BT (mtf_trend_follow_scalp / mtf_counter_trend_scalp)**: bit-identical (default toggles off)
- **既存 commit 8f2150e / 13f7d24**: 破壊変更なし (additive only)
- live trading コードへの影響: なし (BT 専用)

### 次のステップ

1. 365 日 production parity BT を `inject_sr_levels=True, inject_master_bias=True, inject_layer_scores=True, inject_regime=True, inject_session=True` で実行し `_bt_mtf_cascade_scalp.py` (run_scalp_backtest 経由) と数値同値性検証
2. Level 2 (76 戦略 sanity check) を harness 経由で再走させ Tier 判定基盤として活用
3. master plan `bt-serialized-willow.md` Phase F (`compute_scalp_signal` の harness 化) へ進む

---

## 2026-04-30 — Regime Cascade Empirical Redesign v2 (data-driven binary gate) [rule:R1+R3]

### 動機

別軸 cascade scalp 戦略 (2026-04-29 着工) について、demo_trades.db (N=462) のラベル実測クエリで v1 仮説「regime ∈ {trend_up, trend_down} で TF 戦略、regime == range で MR 戦略」が**否定方向**であることを発見:

- ema_trend_scalp × **trend_up_strong**: N=30 WR=**16.7%** (Wilson_lo=7.34%) — 強トレンドで TF が最低
- ema_trend_scalp × **trend_up_weak**: N=12 WR=**41.7%** — 中庸が最高
- bb_rsi_reversion × **range_tight**: N=8 WR=**12.5%** (Wilson_lo=2.24%) — range で MR が最低
- sr_channel_reversal × range_tight: N=10 WR=**0%** (Wilson_lo=0%)

CLAUDE.md「KB は更新するもの」原則に基づき、教科書仮説を実測で更新。`{moderate_trend, no_go}` の binary classifier に簡素化。

### 変更内容

- **modules/regime_classifier.py** v2 — 4 ラベル → binary `{moderate_trend, no_go}` に変更
  - moderate_trend = ADX 18-25 + |slope|>0 + Hurst 0.40-0.55 (実測 trend_up_weak 相当)
  - 新ヘルパ `slope_direction(htf_m15) -> {-1, 0, +1}` で BUY/SELL 方向を ema_slope 符号から決定
  - 旧定数 (REGIME_TREND_UP 等) は backwards-compat で REGIME_MODERATE_TREND/NO_GO の alias
- **strategies/scalp/mtf_regime_trend_cascade_scalp.py** — moderate_trend gate に書換
  - confidence sweet-spot を `21 ≤ ADX ≤ 24` (中庸帯センター) に変更
  - score 式を ADX 18-25 帯対応 (`min((adx-18)*0.10, 0.7)`)
- **strategies/scalp/mtf_regime_range_cascade_scalp.py** — `enabled = False` (rule:R3)
  - 実測根拠で 365 日 BT を待たず即停止 (bb_rsi×range Wilson_lo=2.24%)
  - 失敗時継続検証で別 trigger を試す場合は enable に戻す
- **knowledge-base/wiki/strategies/mtf-regime-trend-cascade-scalp.md** — v2 仕様 + 実測表
- **knowledge-base/wiki/strategies/mtf-regime-range-cascade-scalp.md** — DEPRECATED 反映
- **knowledge-base/wiki/decisions/regime-cascade-empirical-redesign-2026-04-30.md** (新規) — 実測根拠と判断ロジック

### 検証要件 (Rule 1)

1. 365 日 BT (USD_JPY + EUR_USD) — WR≥52% / PF≥1.20 / Wilson_lo≥50% / N≥50/cell / Kelly>0
2. Bonferroni: 戦略×ペア×セッション = 6 cell, α=0.05/6=0.00833
3. Walk-Forward: 240d/60d 3 分割, 評価期間 Wilson_lo≥48% を 3/3
4. Pre-reg LOCK 14 日 (shadow only)
5. shadow 後の SQL ラベル実測クエリで moderate_trend cell の WR を検証

### 失敗時継続検証 (closure 短絡禁止)

- ADX band 感度: 18-25 → {16-22, 20-28, 18-30}
- Hurst band 感度: 0.40-0.55 → {0.35-0.60, 0.45-0.55}
- 1m trigger 差替え: ema_pullback → stoch_trend_pullback / engulfing_bb 派生
- range cascade 復活 (3-bar reversal / vol_surge climax を 1m trigger に)

### 教訓

「N=8〜30 でも複数戦略が同じ regime ラベルで collinear に低 WR を示すなら、構造的方向性として設計に反映できる」— 部分的クオンツの罠 (PF/Wilson 必須) と KB-defer の両極端を回避し、実測駆動で設計を更新する勇気。


## 2026-04-29 — MTF 15m/5m/1m Cascade Scalp Strategies (順張り + 逆張り) [rule:R1]

### 動機

scalp モードの WR が伸び悩んでおり、ユーザー要望は教科書的 MTF 階層を満たす順張り・逆張り両方の新規戦略追加。既存 22 個の scalp 戦略はすべて 1m 単独評価 + ぼんやりした H1/H4 HTF で、教科書的な M15→M5→M1 3 段カスケードを厳密に踏む戦略は不在 (overlap audit 確認済み)。3 段カスケードで誤シグナルを段階的に削減し WR を上げる狙い。

ユーザー指示「対応通貨ペアはスプレッドの低いもの・タイムゾーンもスプレッドが低いことを条件」と CLAUDE.md「静的時間ブロック禁止」を両立するため、`friction_model_v2.hour_mult_for(hour_utc) <= 0.95` による**動的時間帯ガード**を採用。

### 変更内容

- **modules/friction_model_v2.py** — `hour_mult_for(hour_utc)` getter 追加
- **modules/htf_data_source.py** — `_TTL` に M15/M5 追加 + `compute_mtf_features(symbol)` helper 新設 (M15 trend features + M5 SMA21/BB%B/RSI div features を一括計算)
- **app.py:get_htf_bias** — 戻り値辞書に `m15`, `m5` キーを追加 (既存 h1/h4 callers は非破壊)
- **strategies/scalp/mtf_trend_follow_scalp.py** (新規) — strategy_type="trend"
  - USD_JPY/EUR_USD のみ、hour_mult ≤ 0.95
  - M15: ADX≥22 + EMA9>EMA21 + ema_slope 一致
  - M5: SMA21 プルバック反発 + BB%B 中間帯
  - M1: 直前3本 micro pivot break + MACD-H 上昇 + Stoch GC + 陽線
  - SL = 直前3本 Low - 1pip, TP = max(M5 swing, RR×1.3)
- **strategies/scalp/mtf_counter_trend_scalp.py** (新規) — strategy_type="MR"
  - USD_JPY/EUR_USD のみ、hour_mult ≤ 0.95
  - M15: ADX≥25 + 明確トレンド方向
  - M5: BB%B≥0.92 (or ≤0.08) + RSI divergence (両方要求)
  - M1: engulfing/pin bar + Stoch cross + 陰陽線確認
  - SL = M5 wick + 1pip (max 12pip), TP = 固定 5-6pip OR RR×1.2
- **strategies/scalp/__init__.py** — 2 戦略を ScalperEngine に登録
- **knowledge-base/wiki/strategies/mtf-trend-follow-scalp.md** (新規)
- **knowledge-base/wiki/strategies/mtf-counter-trend-scalp.md** (新規)

### Pre-reg LOCK (rule:R1, 14 日)

- **LOCK 期間**: 2026-04-29 ~ 2026-05-13
- **検証**: 365 日 BT (USD_JPY + EUR_USD scalp mode) → Bonferroni (12 cell, α=0.0042) → Pre-reg shadow N≥15/strata
- **合格 KPI**:
  - 順張り: WR≥52%, PF≥1.20, Wilson下限≥50%, N≥50
  - 逆張り: WR≥52%, PF≥1.15, Wilson下限≥48%, N≥30
- **即停止 (rule:R2)**: shadow N≥10 で WR<35% (順張り) / <30% (逆張り)、PF<0.7、6連敗

### Out of Scope

- micro_scalp/ への追加 (scalp/ のみ)
- daytrade モードへの 1h/15m/5m 版拡張 (将来検討)
- ML スコアリング (現時点はルールベース)

---

## 2026-04-28 — SCORE_GATE Direction-Aware Misalignment [rule:R1]

### 動機

P0 audit で判明した ELITE_LIVE 戦略の構造的 LIVE 発火不能問題を解消。本番 12日間で `session_time_bias` (ELITE_LIVE) が全期間 0 件、`trendline_sweep` / `gbp_deep_pullback` も SELL 0 件 / BUY のみ発火という偏在を確認。真因は app.py daytrade pipeline の score 符号反転 (BUY=正 / SELL=負) と modules/demo_trader.py SCORE_GATE の `score<0` 一律 block の**設計衝突**。詳細: [raw/audits/low_firing_root_cause_2026-04-28.md](raw/audits/low_firing_root_cause_2026-04-28.md)

### 変更内容

- **modules/demo_trader.py:2862-2880** — SCORE_GATE を direction-aware misalignment 判定に変更
  - 旧: `_entry_score < 0` 一律 block
  - 新: `(BUY × score<0) or (SELL × score>0)` のみ block (戦略 signal と combined score の符号アラインメント)
  - score=0 はそのまま通過 (未実装戦略デフォルト保護を維持)
  - Sentinel系 (SCALP_SENTINEL / UNIVERSAL_SENTINEL) は引き続き bypass

### Pre-reg LOCK (rule:R1, 2週間)

- **LOCK 期間**: 2026-04-28 ~ 2026-05-12
- **Pre-reg 文書**: [knowledge-base/wiki/decisions/score-gate-direction-aware-2026-04-28.md](knowledge-base/wiki/decisions/score-gate-direction-aware-2026-04-28.md)
- **Primary KPI**: ELITE_LIVE 3戦略 × {BUY, SELL} = 6 strata で N≥15, WR≥40% (Wilson下限>30%), PF≥0.8, EV≥-0.5p, 連敗<6
- **即停止条件 (rule:R2)**: ELITE_LIVE×SELL N≥10 で WR<30%, 全体 N≥15 で PF<0.6, 同一戦略×ペアで6連敗, Live累計損失>-¥10,000
- **Re-eval 2026-05-12**: 全KPI通過 → 定着、1つでも失格 → revert + app.py符号反転の根本見直しPhaseへ

### 期待効果

ELITE_LIVE × SELL の構造block解消により:
- session_time_bias (EUR_USD/GBP_USD SELL bias 設計) の Live 発火復旧
- trendline_sweep × {EURUSD, EURGBP, XAUUSD} (SELL_ONLY_PAIRS) の Live 発火復旧
- gbp_deep_pullback × GBP_USD × SELL の Live 発火復旧

---

## 2026-04-28 — Promotion Infrastructure Rewire [rule:R1+R3]

### 動機

obs 252/254/257/258/259/267/268/298 で確認された昇格ゲートの構造的欠陥群を一括修正。Sentinel/UNIVERSAL_SENTINEL 戦略が `is_shadow=0` フィルタにより N=0 で永久凍結する構造バグ (obs 257)、algo_change_log がランタイム昇格・降格イベントで未配線 (obs 298 致命的欠落 #1)、KPI 閾値が UI 表示のみで判定に未使用 (obs 298)、FORCE_DEMOTED からの自動復帰メカニズムが完全欠如、Walk-Forward 復帰パターン (H1≤0 & H2>0) の自動検出が欠落、を同時解消。

### Commits

- **4bc55bd** `feat(strategies): S/R anti-hunt-bounce + liquidity-grab + audit tooling [rule:R3]`
  pre-commit hook の auto-stage 副作用で `modules/demo_db.py +33` および `modules/demo_trader.py +459` (Shadow methods + Kelly clean + KPI gate + WF recovery + algo_change_log 配線) も同梱。S/R 戦略本体と昇格ゲート改修本体が同 commit に共存。
- **bb43385** `feat(promotion): KPI thresholds + Pre-reg LOCK + 5 test suites + auto-recovery cron [rule:R1+R3]`
  config.py (STRATEGY_PROFILE_MODE_A/B), 5 テストスイート 67 件, tools/auto_force_demoted_recovery.py, Pre-reg LOCK 文書を追加。

### 変更内容

#### 1. Shadow-aware promotion gate (obs 257 解消, rule:R3)
- 新規メソッド: `_binomial_two_sided_p` (staticmethod), `_shadow_promotion_decision` (pure), `_evaluate_shadow_promotions` (DB integration)
- `modules/demo_db.py:get_shadow_trades_for_evaluation` (L1200) を消費
- shadow-contamination 防止: aggregate Kelly / lot sizing / 学習エンジンは引き続き `is_shadow=0` 維持。本パスは「昇格候補の探索」専用
- 判定基準: N≥20 AND Wilson_BF lower (Z=3.29) > 0.50 AND Bonferroni p < 0.05
- 結果は `algo_change_log` に `change_type="shadow_promotion_candidate"` で記録のみ。tier-master.json には書き込まず

#### 2. FORCE_DEMOTED 自動復帰 cron (obs 255/267 解消, rule:R3)
- `tools/auto_force_demoted_recovery.py`: tier-master.json の `force_demoted` 配列をスキャンし、復帰条件を満たす戦略を atomic write + .bak で外す
- 復帰条件: N≥30 AND Wilson_BF lower>0.50 AND Bonferroni p<0.05
- スケジュールタスク `fx-ai-auto-force-demoted-recovery` で daily 09:31 (local) 実行
- **Dry-run 結果 (2026-04-28)**: 18 force_demoted 戦略のうち復帰条件達成は **0 件** (false positive ゼロ実証)。intraday_seasonality は N=6 で N≥30 未達、sr_channel_reversal は p_bonf=0.0001 で**有意にマイナス**で正しく拘束維持

#### 3. Kelly clean helper (obs 298 #2 解消, rule:R2)
- 新規ヘルパー `_get_strategy_kelly_clean(entry_type)`: aggregate Kelly L5842-5880 と厳密に同じフィルタ条件 (CLOSED + is_shadow=0 + XAU除外 + FIDELITY_CUTOFF) で Kelly fraction を返す
- `_evaluate_promotions` の事前ゲートに Kelly<0 ブロックを追加 (L5172-5184)
- 既存 SHIELD gate (L4571-4590) は冗長な防御層として保持
- ⚠️ **2026-04-28 lesson との関係**: CLAUDE.md の新ルール「Kelly は事後指標、発掘段階の gate として使わない」と整合確認が必要。本変更は**昇格** (発掘ではなく既知エッジの実弾投入判断) ゲートに使用しているが、Day-7 ratification で再評価予定

#### 4. Walk-Forward 復帰パターン (obs 298 #3 解消, rule:R2)
- `modules/demo_db.py:_calc_wf_halves` を拡張し、Mann-Whitney U one-sided test (H2 > H1) の p_value を返す
- `_evaluate_promotions` の demoted→pending 復帰条件に WF パターン追加: N≥20 AND H1≤0 AND H2>0 AND p<0.10
- 既存 v8.9 復帰条件 (N≥30 AND EV>0) と OR 結合
- FORCE_DEMOTED は手動フラグなので touch しない (cron 経由のみ復帰)

#### 5. STRATEGY_PROFILES KPI 閾値配線 (obs 298 解消, rule:R1)
- `modules/config.py` に `STRATEGY_PROFILE_MODE_A` (22 戦略, scalp/Trend Following), `STRATEGY_PROFILE_MODE_B` (51 戦略, daytrade/Mean Reversion), `get_strategy_profile_mode()` を追加
- `_evaluate_promotions` でハードコード閾値 (`WR≥60%`) を Mode 別 `kpi_wr`/`kpi_ev` 動的参照に置換
- **Mode 未定義の戦略は legacy 閾値にフォールバック (back-compat)**
- **R1 Pre-reg LOCK 適用**: `wiki/decisions/pre-reg-promotion-rewire-2026-04-28.md`。Day-7 ratification (2026-05-05 09:00 JST、scheduled-task `promotion-rewire-day7-ratification` 登録済) で rollback trigger 監視

#### 6. algo_change_log 配線 (obs 298 致命的欠落 #1 解消, rule:R3)
- `_evaluate_promotions` 内で status 変更 (pending→promoted, promoted→demoted, demoted→pending) ごとに `_db.save_algo_change(change_type="tier_transition", ...)` を呼出
- 記録項目: timestamp, entry_type, old_status, new_status, decision_reason, N, WR, EV, friction_pip, kelly_f, wilson_bf_lower
- exception 安全 (失敗時は print log のみ、commit はブロックしない)

### テスト

| ファイル | テスト数 | 対象 |
|---|---:|---|
| `tests/test_shadow_promotion_gate.py` | 18 | `_binomial_two_sided_p`, `_shadow_promotion_decision`, `_evaluate_shadow_promotions` |
| `tests/test_kelly_promotion_gate.py` | 12 | `_get_strategy_kelly_clean` + 事前 gate |
| `tests/test_kpi_threshold_promotion.py` | 20 | Mode A/B 閾値の正しい適用 + back-compat fallback |
| `tests/test_wf_recovery.py` | 9 | Mann-Whitney p<0.10 復帰、FORCE_DEMOTED 非干渉 |
| `tests/test_auto_force_demoted_recovery.py` | 8 | cron 単体: dry-run, atomic write, .bak |
| **合計** | **67** | **全 pass** |

回帰テスト: full suite 622 passed, 1 xfailed (regression なし)

### Pre-reg LOCK Day-7 検証

`wiki/decisions/pre-reg-promotion-rewire-2026-04-28.md` 参照。

**Rollback trigger** (任意ヒットで該当戦略を pending 降格 + STRATEGY_PROFILE から削除):
1. 新ゲート下で promoted になった戦略が post-flip N≥10 で EV<0 (72h 以内)
2. aggregate Live PnL が pre-deploy baseline から 2σ 以上乖離 (7d)
3. `tests/test_kpi_threshold_promotion.py` が schema drift で fail

**Day-7 ratification**: scheduled-task `promotion-rewire-day7-ratification` (one-time fireAt=2026-05-05T09:00:00+09:00, enabled) が algo_change_log を audit して ratify or rollback を判定

### 残課題 (statusとして wiki に追記予定)

- BT_COST_PER_TRADE のペア別化 (`friction_model_v2` per-pair 値を `_evaluate_promotions` 摩擦閾値に反映)
- tier-master.json の動的生成化 (現在 2 日陳腐化)
- per-pair-direction セル拡張 (`dt_bb_rsi_mr` BUY/SELL 非対称性検出)
- Codex レビュー結果に基づく追加修正

---

## 2026-04-27 evening — Kelly Recompute + bb_squeeze_breakout 縮小 + thaw CLI [rule:R2/R3]

### 動機
本日の P0 (commit 9e53794, fe5344d, 9ded0e7) で評価系の bias 補正が完了したため、memory 175 の **「Kelly = -17.97% / DD = 32.32% / 危機状態」** の前提を再検証。Live aggregate を seed-exclusion 込みで再計算し、live-thaw-gate G1 の現実値を確定。

### 1. kelly-recompute-2026-04-27.md (rule:R3)
seed-exclusion 適用後の Live aggregate Kelly を計算:

| 計算 | N | WR | total_pip | full_Kelly |
|------|--:|---:|---------:|----------:|
| LEGACY (seed込み) | 36 | 50.00% | +6.0p | +1.14% |
| **CLEAN (seed除外)** | **34** | **50.00%** | **+4.3p** | **+0.87%** |

**結論**: Live Kelly は補正後 **+0.87% borderline positive**。memory 175 の -17.97% は別 metric (おそらく friction-adjusted or Track5 MC) 由来で、本日の Live aggregate Clean とは異なる。

戦略・ペア別内訳:
- **bb_rsi_reversion**: Live N=20 WR=65% Wilson 43% +190.6pip — 唯一の真エッジ候補
- **GBP_USD Live**: N=4 全敗だが、うち 1 件 (turtle_soup -170p) が支配的 → outlier-driven、構造的問題ではない
- **USD_JPY Live**: N=29 WR=55% (主に bb_rsi_reversion 寄与)
- **EUR_USD Live**: N=1 評価不能

配置: `knowledge-base/wiki/decisions/kelly-recompute-2026-04-27.md`

### 2. bb_squeeze_breakout × USD_JPY lot 縮小 (rule:R2)
`_PAIR_LOT_BOOST` に `("bb_squeeze_breakout", "USD_JPY"): 0.01` を追加。
- 365d BT N=42 WR=76.2% → PAIR_PROMOTED (2026-04-21) したが Live N=5 全敗 (-11.9pip)
- Wilson 95% CI: BT [60%, 88%] vs Live [0%, 52%] **完全非重複** (p<0.001)
- N=10 達成まで 0.01x trial で出血最小化、その時点で Rule 1 撤回判断

### 3. tools/live_thaw_check.py (rule:R3)
G1-G4 を CLI で一括判定する道具を実装。

```bash
$ python3 tools/live_thaw_check.py
  ✅ G1 Live Kelly > 0          — Kelly=+0.87% (Wilson WR L=34.1% — noise範囲)
  ❌ G2 ELITE cell Wilson > BEV — no cell with Wilson_pip > BEV (need N>=10 per cell)
  ❌ G3 SR Anti-Hunt EUR_USD    — N=0 < 30 (Sentinel 未開始)
  ✅ G4 14d DD < 10%            — max_dd_14d=35.7pip (0.36% proxy)
  OVERALL: BLOCKED (2/4)
```
- `--gate G1` で単独評価、`--json` で機械可読出力
- exit code: 0 ALL PASS / 1 BLOCKED → cron で alert subsystem 連携可

### 認識更新

- **「全面 lot=0 凍結」は過剰**。bb_rsi_reversion は Live で機能している実エッジ候補
- **GBP_USD は単発 outlier (turtle_soup -170p) 支配のため freeze せず、daily_live_monitor 経由で監視**
- **解凍 gate は依然 BLOCKED (G2/G3 未充足)**。G2 は cell-level audit (P1) で評価、G3 は SR Anti-Hunt Phase 6 Sentinel 観測 (P2) で蓄積

### 回帰テスト
506 passed, 1 xfailed (新規追加なし、既存全通過)

### 残課題 (P1+)
- bb_rsi_reversion cell-level audit (G2 評価準備)
- SR Anti-Hunt Phase 4 BT (pre-reg LOCK) → Phase 5/6 で G3 評価
- block-bootstrap (block=4h) を net_edge_audit に追加 (autocorr-aware)
- bb_squeeze_breakout × USD_JPY 追加 5 件で Rule 1 撤回判定

---

## 2026-04-27 M2: Regime Gate Over-block Fix [rule:R3]

### 動機
M1 (commit 641bfe4) で `spread_sl_gate` に ELITE_LIVE bypass を追加したが、post-deploy 4 時間で
ELITE_BYPASS log = 0 / ELITE 3 戦略 Live fire = 0 継続。Production trade を解析したところ
**streak_reversal × USD_JPY (PAIR_PROMOTED)** が `mtf_gate_action=kept` にもかかわらず is_shadow=1
強制で 4/4 trade が Shadow-only になっていた。Root cause: `modules/demo_trader.py` の
**DT TREND_BULL TF bypass gate** (旧 line 3046-3056) が `not _is_mr_entry` の negation form で
`_RANGE_MR_STRATEGIES` 未登録の全戦略を一括 shadow 化していた。RANGE gate (line 3024) は
positive list を使う対称な実装だったため、TREND_BULL gate のみ bug。

### 修正
1. **TREND_BULL gate を positive list 化**: `not _is_mr_entry` → `entry_type in _DT_TREND_STRATEGIES`
2. **両 regime gate (RANGE / TREND_BULL) に ELITE_LIVE / PAIR_PROMOTED 例外を追加**:
   `_regime_gate_exempt = entry_type in self._ELITE_LIVE or (entry_type, instrument) in self._PAIR_PROMOTED`

### 影響
**Direct targets** (intended Live 復活):
- streak_reversal × USD_JPY: PAIR_PROMOTED (二重 WF stable, BT 5streak BUY p=1.3e-5)
- session_time_bias / gbp_deep_pullback (ELITE_LIVE)
- trendline_sweep (ELITE_LIVE — RANGE / TREND_BULL 両方の gate から免除)

**Side-effect** (UNIVERSAL_SENTINEL 系の TREND_BULL × daytrade での発火許可):
- liquidity_sweep, gotobi_fix, trend_rebound, dt_fib_reversal 等
- N<10 sentinel lot (0.01) で発火可、`_is_promoted()` default True のまま
- 原則 #1/#4 と整合。daily_live_monitor.py で発火頻度を観察、予期せぬ Live promotion を
  検知した場合は positive list を適切に拡張

### 検証
- 511 tests pass (回帰なし)
- AST parse OK
- `tests/test_signal_dedup.py` 9 件 (M1 と同 commit) も継続 pass

### KB
- 詳細: [lesson-trend-bull-gate-overblock-2026-04-27](knowledge-base/wiki/lessons/lesson-trend-bull-gate-overblock-2026-04-27.md)
- KB streak-reversal.md は MR 分類だが code MR set 未登録 = code/KB 不整合発見

### 後続
- post-deploy で ELITE_BYPASS log と ELITE 3 戦略 / streak_reversal の Live fire を確認
- 1日 Live N≥5 達成しない場合は更なる gate 調査 (HTF self-block / SELL_ONLY / pair filter)


## 2026-04-27 P0-2/P0-3 Live-thaw Discipline — net_edge monitor + thaw gate [rule:R2/R1]

### 動機
本日のクオンツ提案ロードマップ P0 のうち、P0-1 (post_news_vol demote) は commit fe5344d に取り込み済。本コミットは P0-2 (daily_live_monitor + net_edge_audit) と P0-3 (live-thaw-gate doc) を別単位で投入する。Kelly=-17.97% / DD=32.32% の危機状態下で、**負エッジの常設監視と解凍判断の文書化**を pre-register する目的。

### 1. daily_live_monitor に net_edge_audit を組み込み (P0-2, rule:R2)
- 全戦略で `net_edge_wr_pt` を毎日算出 (N≥5 のみ採用)
- `net_edge_wr_pt ≤ -10pt` を WARNING alert に昇格 (severity 1)
- 出力 JSON に `net_edge` フィールド追加 — 監視サブシステム連携用
- 配置: `tools/daily_live_monitor.py:415-444`

実測 alert (2026-04-27 初回実行):
```
NET_EDGE post_news_vol: -50.0pt (-14.65pip) N=6
NET_EDGE dt_fib_reversal: -20.8pt (+1.09pip) N=6
NET_EDGE bb_squeeze_breakout: -17.1pt (-1.64pip) N=15
NET_EDGE orb_trap: -16.7pt (-8.18pip) N=5
NET_EDGE sr_channel_reversal: -15.3pt (-1.08pip) N=24
```

うち `bb_squeeze_breakout × USD_JPY` は `_PAIR_PROMOTED` (BT N=42 WR=76.2%) と矛盾しており、Live N=5 全敗 (post-promotion 2026-04-21〜) は **BT-Live divergence** の典型。Rule 1 撤回判断は別途。

### 2. live-thaw-gate-2026-04-27.md 起票 (P0-3, rule:R1)
Live 解凍条件を **4 項目 AND** で pre-register:
- G1: seed-exclusion 適用後の aggregate Kelly > 0
- G2: ELITE_LIVE 候補 (bb_rsi_reversion / fib_reversal) の cell-level Wilson > BEV
- G3: SR Anti-Hunt EUR_USD Sentinel N≥30 で WR>60% かつ Wilson>55%
- G4: 直近 14 日の DD < 10%

撤回条件 (Rule 2/R3) も明文化: net_edge alert 2 戦略同時 / 連続 SL 4 回 / DD>15% (7d) 等で即 Live=0 復帰。配置: `knowledge-base/wiki/decisions/live-thaw-gate-2026-04-27.md`

### 回帰テスト
482/482 通過 (新規追加なし)

### 残課題 (P1+)
- `tools/live_thaw_check.py` 実装 (4 条件を CLI で一括判定)
- bb_squeeze_breakout × USD_JPY の Rule 1 撤回判断
- SR Anti-Hunt Phase 4 BT (pre-reg LOCK)

---

## 2026-04-27 P1 Aggregation Hygiene — seed-exclusion + net_edge_WR audit [rule:R3]

### 問題
集計クエリ (`get_stats` / `get_all_closed` / `get_shadow_trades_for_evaluation` / `get_trades_for_learning`) が **entry→exit < 5秒の seed/backfill replay artifact** を含めていた。Apr 8 fib_reversal の 16件 instant-exit (TP_HIT 同時刻 約0.1秒で達成) が WR 67% / cum_pip +342.8 を inflate していた。これは **TP まで瞬時到達 = 未来情報の漏洩** で、リアルタイム経済性とは別物。

### 修正 (`modules/demo_db.py`)
- 定数 `SEED_HOLD_SEC_THRESHOLD = 5` 追加
- リテラル SQL 断片 `_SEED_EXCLUSION_SQL` 追加 (parameterized 不要、untrusted input なし)
- `exclude_seed: bool = True` パラメータを以下 3 関数に追加 (default ON):
  - `get_all_closed()` — Kelly/学習エンジン source
  - `get_stats()` — UI/ダッシュボード aggregate
  - `get_shadow_trades_for_evaluation()` — Sentinel 昇格判定

### 新規ツール (`tools/net_edge_audit.py`)
戦略の **net_edge_WR** = strat_WR − benchmark_WR を算出。benchmark は同期間×同 instrument×同 direction の **他戦略 Shadow**。市場ベータ便乗 (例: GBP/USD 単一ラリーに乗っただけ) と真のエッジを分離。Wilson 95% 下限も同時表示。
- `--strategy <entry_type>`: 単一戦略
- `--all`: 全戦略ランキング (n_strat ≥ 5 を上位ソート)
- `--db <path>`: SQLite ファイル指定 (default `demo.db`)

### 実測結果 (2026-04-27, demo_trades.db, --all)
ポジティブ候補:
- `bb_rsi_reversion` N=32 strat 47% / Wilson 31% / bench 27% / **net +20pt +6.21pip**
- `fib_reversal` N=31 strat 48% / Wilson 32% / bench 19% / net +30pt +4.59pip (seed 除外後)
- `intraday_seasonality` N=6 strat 67% / Wilson 30% / bench 50% / net +17pt +4.64pip (Wilson 下限が広く有意性弱)

Suppress 候補:
- `post_news_vol` N=6 / **net -50pt -14.65pip**
- `bb_squeeze_breakout` N=15 / net -17pt
- `sr_channel_reversal` N=24 / net -15pt

### conftest.py 修正
`pytest fixture autouse` で `_SEED_EXCLUSION_SQL` を `1=1` に patch。テストは `db.open_trade()→db.close_trade()` を即時連続で呼ぶため hold<5s となり seed 扱いされる。新規 `tests/test_seed_exclusion.py` は `monkeypatch.undo()` で patch を外しタイムスタンプ手作りで検証。

### 回帰テスト
- 既存: 467/467 通過 (15.8s)
- 新規 `tests/test_seed_exclusion.py` 7件 (全 PASS):
  - 閾値定数, get_all_closed default/opt-in, get_stats inflation 検証, shadow eval, 境界 (4s 排除 / 5s 通過)

### 分類根拠 (rule:R3 = Immediate)
構造バグ (集計の bias) のため 365日BT 不要。data-derivation で原因特定済み。

---

## 2026-04-27 Cross-thread Signal Dedup Guard — race-condition下の二重発火防止 [rule:R3]

### 問題
複数モードスレッド (scalp / daytrade / daytrade_gbpusd 等) が同一シグナルを並行評価する際、各々が `get_open_trades()` で「open なし」と判定したまま `self._lock` 外で同時 INSERT する race condition により、同一 (entry_type, instrument, direction) が二重発火していた。既存の `same_price` ガードは DB 反映前のため無効、`cooldown` は post-exit 限定で機能せず。

### 実測重複発火 (Shadow, instant-exit replay 除外後)
- `vol_spike_mr` 389/390: USD_JPY BUY, **0.0002秒差** (純粋 race condition)
- `sr_fib_confluence` 360/361: GBP_USD BUY, 0.0002秒差・0bp 差
- `intraday_seasonality` 436/437: GBP_USD BUY, 6秒差, 0.44bp
- `stoch_trend_pullback` 183/184: USD_JPY SELL, 35秒差・同pnl

### 修正 (`modules/demo_trader.py`)
- `__init__`: `self._recent_signal_emits: dict[(entry_type, instrument, direction), datetime]` 追加
- `_tick_entry`: 既存 `same_price` ガードの直前に in-memory dedup を挿入。`self._lock` 配下で 60秒以内の同一キーをブロック (DB を介さない即時判定)。120秒で stale 自動掃除。
- ブロック理由ログ: `recent_emit({entry_type},{age}s<60s)`

### 回帰テスト (`tests/test_signal_dedup.py`)
9 件追加、全 PASS:
- 1st emit / 同キー連発 / 別方向 / 別pair / 別戦略の境界
- 60秒境界 (61秒で解放、6秒・35秒以内ブロック)
- 8並行スレッド race → 1 winner / 7 BLOCK
- stale 掃除でメモリ有界

### 既存テスト
432/432 通過 (回帰なし)

### 分類根拠 (rule:R3 = Immediate)
構造バグ (ガード漏れ) のため 365日BT スキップ可。データ駆動分析 (sqlite-fx 実測 6 件) で原因特定済み。Rule 2 監視に格下げ (誤ブロック発生時即 revert)。

---

## 2026-04-07 v6.1 収益構造安定化 — GBP依存脱却 + USD/JPY救済 + Confidence Lot

### P0: USD/JPY デイトレ救済
- **htf_false_breakout × JPY**: RSIダイバージェンス or H1 OB接触を必須化 (WR 33%→~67%)
- **orb_trap × JPY**: LDN session仲値フィルター (00:45-01:30 UTC ATR×1.2超→ブロック)

### P1: Confidence-based Lot Scaling (_N_LOT_TIERS)
- N<10: ブースト上限 1.0x (Standard) → gbp_deep_pullback(N=3) 2.0x→1.0x
- 10≤N<30: ブースト上限 1.5x (Elite Candidate) → orb_trap(N=13) 1.5x維持
- N≥30: フルブースト許可 (Proven Elite) → sr_fib_confluence(N=35) 1.3x維持

### P1: EUR/USD Profit Extender ADX緩和
- orb_trap, london_ny_swing のTP到達時: ADX>25 (従来30) でTP 50%延伸
- DT Profit Extender新設: _PE_DT_ELIGIBLE + _PE_ADX_THRESHOLD ペア別制御

### P2: GBP/USD Strict Friction Guard
- 指値失効後 180s 同方向再エントリー完全禁止 (_LIMIT_EXPIRE_CD_SEC)
- 成行追っかけゼロ: 指値期限切れ = トレード無効扱い

### KPI比較
- GBP依存度: 71.1% → 53.7% (✅ 脱却)
- JPY寄与度: -2.1% → +12.2% (✅ 救済)
- Top1集中度: 39.8% → 22.8% (✅ 分散化)
- 月次: ¥+336K → ¥+305K (攻撃力-10%、安定性+40%)
- 攻撃/防衛比: 3.9x (DD 2.8日で回復)

## 2026-04-07 Pair-Specific Strategy Lifecycle — 通貨ペア別戦略管理 + 転送司令部可視化

### 背景
v5.95 統合BT監査（14日間, 340t, 摩擦モデルv2）で通貨ペア別の戦略パフォーマンス格差が判明:
- bb_rsi×EUR_USD: WR=20% EV=-1.500 (全ペア中最悪)
- macdh×GBP_USD: WR=40% EV=-0.818 (GBP高摩擦 RT=3.06pip)
- fib_reversal×USD_JPY: WR=86.7% EV=+0.848 (全ペア中最良)
- gbp_deep_pullback×GBP_USD: WR=100% EV=+4.747 (DT最強)

### 1. ペア特化デモーション (_PAIR_DEMOTED)
- `(bb_rsi_reversion, EUR_USD)` → エントリー完全停止 (月間 +68pip 節約)
- `(macdh_reversal, GBP_USD)` → エントリー完全停止 (月間 +68pip 節約)

### 2. ペア特化プロモーション (_PAIR_PROMOTED)
- `(sr_fib_confluence, USD_JPY)` → FORCE_DEMOTED から復帰 (WR=76.9% EV=+0.470)

### 3. ペア特化ロットブースト (_PAIR_LOT_BOOST)
- `(fib_reversal, USD_JPY)`: 1.5x, `(sr_fib_confluence, USD_JPY)`: 1.3x
- グローバル _STRATEGY_LOT_BOOST より優先

### 4. ユニバーサル Sentinel (_UNIVERSAL_SENTINEL)
- `stoch_trend_pullback` → _SCALP_SENTINEL (scalp限定) から全モードSentinel化

### 5. USD/JPY SR閾値緩和 (_PAIR_SR_THRESHOLD)
- USD_JPY: 2.0 → 1.5 (SR品質が高くフィルター過剰回避)

### 6. GBP/USD スキャルプ指値限定 (_LIMIT_ONLY_SCALP)
- GBP_USD scalp成行注文禁止 → 指値エントリーのみ (RT friction=3.06pip対策)

### 7. _is_promoted() v4 判定優先順位
Bridge mode → PAIR_DEMOTED → PAIR_PROMOTED → FORCE_DEMOTED → auto_demotion → default allow

### 8. 転送司令部 通貨ペア別可視化 (Frontend)
- ペアフィルタボタン (ALL / USD_JPY / EUR_USD / GBP_USD / EUR_JPY)
- 戦略ごとのライフサイクルバッジ (Elite / Active / Sentinel / Demoted / Promoted / Force_Demoted)
- `_build_strategy_status_map()` → (strategies, instruments) 返却形式に変更

### 月間PnL証明
- v5.95 Raw: +857 pip/月 (lifecycle なし)
- v5.95+LC: +1,831 pip/月 (lifecycle uplift +107%)
- DT GBP_USD: +1,180 pip/月 (gbp_deep_pullback 2.0x = +470pip 寄与)
- DT EUR_USD: +510 pip/月 (orb_trap/htf_fbk/london_ny 1.5x)

## 2026-04-07 SR決済ノイズフィルター — スコア閾値 + ADXレンジブロック + 詳細ログ

### 1. 逆転強度の閾値導入 (Score Threshold)
- **`_SR_SCORE_THRESHOLD = 2.0`**: 逆転シグナルのスコアが `abs(score) >= 2.0` を満たす場合のみSR決済を実行
- 弱い逆転シグナル(ノイズ)でのSR発動を防止 — 既存のconfidence閾値に加え、スコア品質でもフィルタリング
- 抑制時ログ: `🚫 SR抑制（スコア不足）: BUY→SELL [SR] Score: +1.20 | ADX: 25.1 | ...`

### 2. ADXによるSR制限 (Range Market Block)
- **`_SR_ADX_MIN = 20`**: ADX > 20 のトレンド相場でのみSR決済を許可
- レンジ相場(ADX≤20)では逆方向シグナルが頻発→往復ビンタの原因 → SL/TPに委ねる
- 抑制時ログ: `🚫 SR抑制（レンジ相場）: SELL→BUY [SR] Score: +2.80 | ADX: 15.2 | ...`

### 3. SR理由のログ詳細化
- **`[SR]` 詳細行**: SR決済実行後に根拠情報を1行出力
  - `[SR] Score: +2.50 | ADX: 28.3 | Conf: 65 | Trend_Mismatch: True | L1: bull | Type: sr_fib`
- **Trend Mismatch検出**: Layer1トレンド方向と反転シグナル方向の不一致を検出（bull + SELL = mismatch）
- フィルター通過・抑制いずれの場合もSR詳細を出力 → 後続分析に活用可能

### 4. BT同期
- **Scalp BT**: `run_scalp_backtest()` 内のSR判定に `score >= 2.0 AND ADX > 20` フィルター追加
- **DT BT**: `run_daytrade_backtest()` 内のSR判定に同一フィルター追加
- BT/本番の一貫性を維持 — フィルター非適用時は `pass` で通常SL/TP判定に継続

## 2026-04-07 OANDA Command Center — コントロールパネル & 連携ステータス完全可視化

### 1. OANDA 転送司令部 (Tri-state Control)
- **`/api/config/oanda_control`**: 戦略ごとに LIVE / SENTINEL / OFF / AUTO を即時切替
- **LIVE**: フルロットでOANDA転送（_FORCE_DEMOTED の手動昇格パスを含む）
- **SENTINEL**: 0.01lot固定でOANDA転送（データ収集モード）
- **OFF**: OANDA転送停止 / **AUTO**: 自動昇降格判定に委ねる
- **DB永続**: `oanda_settings.strategy_overrides` (JSON)
- **後方互換**: `/api/config/toggle_oanda` (ON/OFF) は引き続き利用可

### 2. 実行ログ 🔗 OANDA 連携ラベル
- **[SENT]**: OANDA注文送信時に即座にログ出力（ロット・SL/TP含む）
- **[FILLED]**: OANDA約定成功時にOrderID・約定価格・ロット倍率を1行出力
- **[FAILED]**: 約定失敗時にエラー理由を明示
- **[BLOCKED]**: Bridge非アクティブ or モード除外（Reason: bridge_inactive / mode_not_allowed）
- **[SKIP]**: 未昇格戦略（Reason: force_demoted / auto_demoted / 手動停止 / pending）
- **Execution Audit**: `/api/oanda/audit` でトレードごとの is_live / bridge_status / block_reason / oanda_trade_id を返却

### 3. スキャルプ v2 指値ログ
- **[LIMIT_PLACED]**: Confluence Scalp v2 の指値遅延エントリーで指値設置時にログ出力
- **[LIMIT_FILL]**: 価格が指値に到達し OANDA 注文が発火した時点でログ出力
- 両ログとも `🔗 OANDA:` プレフィックス付きで統一フォーマット

### 4. リアルタイム・ヘルスチェック
- **60秒間隔**: `_sltp_loop` から `run_heartbeat()` を120回(=60s)ごとに自動実行
- **計測項目**: API latency(ms) / balance / NAV / unrealized P/L / margin / open trade count
- **display文字列**: `OANDA: CONNECTED / LATENCY: 45ms / NAV: ¥467,608` フォーマット
- **`/api/oanda/heartbeat`**: 最新のハートビートを返却（?refresh=true で手動更新可）
- **`/api/oanda/status`**: audit_summary (live/demo比率) を含む統合ステータス

### 5. インフラ変更
- **oanda_bridge.py**: `get_strategy_mode()`, `set_strategy_mode()`, `is_strategy_sentinel()` 追加
- **oanda_bridge.py**: `open_trade()` に `log_callback` + `lot_label` パラメータ追加
- **oanda_bridge.py**: `_add_audit()` に `oanda_trade_id` フィールド追加
- **oanda_bridge.py**: `get_heartbeat()` に `display` フォーマット済み文字列追加
- **demo_trader.py**: `_is_promoted()` v3 — tri-state対応（sentinel で手動昇格可能）
- **demo_trader.py**: OANDA実行セクション全面改修（🔗ラベル + SENTINEL lot override）
- **app.py**: `/api/config/oanda_control` 新エンドポイント + `_build_strategy_status_map()` 共通関数

## 2026-04-07 Confluence Scalp v2 — Triple Confluence + MSS + Profit Extender

### 1. Triple Confluence Gate (攻撃層)
- **新戦略 `confluence_scalp`** (`strategies/scalp/confluence_scalp.py`)
- **3理論族合意**: EMA9/21整列(Trend) + RSI5/BB%B極端(Oscillator) + MACD-H反転(Momentum)
- 単一指標のノイズエントリーを排除 — 既存Sentinel戦略の構造的欠陥(83.5% instant death)を解消

### 2. 防御層 (3段階ゲート)
- **Session Gate**: UTC 12-17のみ (London/NY overlap, instant death率最低)
- **MFE Guard**: ATR/Spread >= 10 (SAR<1.0の摩擦死を構造的に回避)
- **HTF Hard Block**: HTF逆行エントリーを完全ブロック (ソフトペナルティではなくハードブロック)
- `app.py`: confluence_scalp をEMA200/HTFソフトペナルティ適用外に設定 (内部で制御済み)

### 3. Market Structure Shift (MSS) — CHoCH/MSB検出
- **CHoCH (Change of Character)**: Fractal(n=3)スイングポイント → 実体で割れ = 構造転換 (Wyckoff 1931)
- **MSB (Market Structure Break)**: CHoCH後のHH/LL更新 = 新トレンド確認
- **detect_choch() / detect_msb() / detect_mss_state()**: DataFrame分析関数
- CHoCH検出でスコア+2.0, MSB確認で+1.0のボーナス

### 4. Profit Extender (利益延伸 + 動的エグジット)
- **TP延伸**: TP到達時にMSS継続(MSB=True) + ADX>30 → TP距離を2倍に拡大
- **強化トレイリング**: ATR*0.4幅 (通常Tier2のATR*0.5より狭く利益ロック)
- **Climax Exit**: RSI divergence + 大ウィック(70%以上) → 即利確
- **_mss_tracker**: 毎tick(10s)でMSS状態を更新、_check_sltp_realtime(0.5s)で参照
- **_profit_extended**: TP延伸済みtrade_idのSet追跡

### 5. Friction Minimizer (指値遅延エントリー)
- **compute_limit_entry_price()**: 直近3本のウィック中間点で有利な指値価格を計算
- **指値待ち**: 現在価格が指値より不利 → _pending_limits に保存 (5分期限)
- **指値約定**: 次tick以降で価格到達 → 自動エントリー実行
- **__LIMIT_ENTRY__マーカー**: signal reasonsに指値価格を埋め込み、demo_trader が解析

### 6. インフラ変更
- **demo_db.py**: `update_sl_tp()` メソッド追加 (Profit ExtenderのTP動的変更用)
- **demo_trader.py**: `_mss_tracker`, `_profit_extended`, `_pending_limits` 追加
- **QUALIFIED_TYPES**: `confluence_scalp` を登録
- **ScalperEngine**: `ConfluenceScalp` を戦略リストに追加 (14戦略目)

## 2026-04-07 Elite Selection & Portfolio Restructuring (摩擦v2 BT監査)

### 1. Elite Track ロットブースト (P0)
- **gbp_deep_pullback**: 2.0x (EV=2.903, WR=90.3%, N=31 — 最高エッジ)
- **turtle_soup/orb_trap/htf_false_breakout/trendline_sweep/london_ny_swing**: 1.5x
- **ロットclamp上限**: 2.0→2.5 (Elite 2.0x + vol_mult 1.5 = 3.0 → 2.5でcap)

### 2. Scalp Sentinel Mode (P0 — 摩擦死撤退)
- **8戦略を Sentinel 降格**: bb_rsi, fib, macdh, vol_momentum, stoch_trend, vol_surge, ema_ribbon, bb_squeeze
- **処置B**: OANDA継続 / lot=1000units(0.01lot)固定 / デモ継続
- **根拠**: scalp EV=-0.17(JPY), -0.40(EURJPY) — 摩擦がエッジを完全消失

### 3. DT Spread Guard 強化 (P1)
- **DT/1H**: spread_cost閾値 30%→20% (エリート戦略のエッジ防御)
- **Scalp**: 30%据え置き

### 4. Friction Ratio 監視タグ (P2)
- **FR = (spread_entry + spread_exit + slippage) / |PnL|**
- **FR > 100%**: ⚠️警告表示 (ブローカー貢献度超過)
- 決済ログに自動付与、戦略別の摩擦耐性を可視化

### 5. Equity Curve Protector (ディフェンシブモード)
- **DD > 5%** (50pip / 1000pip基準) → 全ロット50%強制縮小
- **DD回復** (2.5%以下) → 自動解除
- **累計PnL peak/current をリアルタイム追跡**、OANDA再開でリセット

## 2026-04-07 BT Friction Model v2 — Phase A-D Reality Sync (461t監査)

### Phase A: ペア別スプレッドモデル + スリッページ係数
- **_bt_spread() v2**: non-JPY一律モデル → EUR_GBP/GBP_USD/EUR_USD/EUR_JPY個別分離
  - EUR_GBP: 旧0.2-0.8pip → 新1.0-2.0pip (実測1.367pip)
  - GBP_USD: 旧0.2-0.8pip → 新0.8-1.8pip (実測1.300pip)
  - EUR_USD: 旧0.2-0.8pip → 新0.3-1.0pip (実測0.658pip)
  - USD_JPY: 旧0.2-0.8pip → 新0.3-1.0pip (実測0.677pip, 微調整)
- **_BT_SLIPPAGE**: ペア別スリッページ定数 (実測平均0.489pip×80%)
  - エントリー・決済の両側に加算 → 往復摩擦の完全再現
- **exit_friction_m**: 全トレードに決済時摩擦(half spread+slippage)をATR倍率で記録

### Phase B: SL判定厳格化
- **_sl_genuine_threshold**: 0.3→0.1 (scalp/DT/1H全BT)
  - 本番のtick-by-tick判定に近似。「ヒゲで助かった」BT楽観を排除

### Phase C: SIGNAL_REVERSE BT実装
- **Scalp BT**: min_hold=5bars(300s)経過後、3barごとにcompute_scalp_signalを再呼出
  - 逆シグナル検出時: close±摩擦で決済 → outcome/PnLを正確に記録
  - 検証結果: 201t中37t(18.4%)がSR決済 (本番40.1%の約半分、チェック間隔差)
- **DT BT**: 毎bar compute_daytrade_signalを再呼出 → 0% SR (15m足は保持期間内に反転しない = 正常)

### Phase D: 執行制限ロジック同期
- **カスケードCD**: SL後の全戦略クールダウン (scalp: 90bars, DT: 12bars@15m)
- **Post-SLブロック**: 同方向エントリー制限 (scalp: 120bars, DT: 40bars@15m)
- SL LOSSのみカスケード発動 (SR決済はカスケート非対象)

### Phase 5: EV計算リベース
- **PnL関数**: WIN=tp_m-exit_friction_m, LOSS=-(sl_m+exit_friction_m)
- **昇格基準**: 摩擦込みEV > 1.0 AND N≥10 → 「昇格候補」フラグ付与
- **verdict更新**: 全BT関数のverdict判定を摩擦込みEVベースに統一
- **結果例 (scalp USD/JPY 7d)**: 旧WR≈59% → 新WR=54.2%, EV=-0.171 (摩擦がエッジを完全消失)

## 2026-04-07 461t Quant Analysis — Win-Rate Reversal Engineering

- **ATR Trailing Stop (Tier2)**: ATR*0.8→BE(Tier1)に加え、ATR*1.5→Trail(price-ATR*0.5)を導入
  - MFE>0→LOSS 18件の64.7p損失を救済。利益ロックイン機構
  - Tier1とTier2はシームレスに切替: BE→TS→TS(ラチェットアップ)
- **Session×Pair exclusion**: EUR_GBP全停止(WR=11%), EUR_USD Tokyo/Late_NY停止
  - コントラリアン(逆張り)検証済み: spread二重控除後 -1.1p → 逆張りもエッジなし → 除外が正解
  - EUR_USD 75t (54+21) の -88.7p + EUR_GBP 9t の -29.9p = -118.6p 遮断
- **SIGNAL_REVERSE min hold**: scalp 180→300s
  - <5m SIGNAL_REVERSE 72件: PnL≈0のノイズ循環。5-10m(WR=53.7%, +51.9p)は有効ゾーン
- **Phase3 Force-demote**: ema_pullback(WR=19%, EV=-0.77) → EMA系3戦略(cross/ribbon/pullback)全滅確認
- **461t構造分析**: MAFE有効率4/7で97.3%に改善、即死率67.3%(93%→補正)、BE救済3.6%

## 2026-04-07 448t Production Audit — Surgical Strategy Triage

- **Phase2 Force-demote**: ema_ribbon_ride(EV=-2.75), h1_fib_reversal(EV=-4.18), pivot_breakout(EV=-8.56) -> OANDA停止
  - 3戦略合計92t、全損失の54%(-198.5p)を生産。即時遮断で最大インパクト
- **Lot boost追加**: mtf_reversal_confluence -> 1.3x (EV=+1.49, WR=57%, instant-death率29%=最低)
- **監視継続**: fib_reversal(EV=-0.54, N=76), ema_pullback(EV=-0.77, N=21) — EV<1.0で自動昇格ブロック済み
- **448t統計**: WR=35%, PnL=-364.6p, PF=0.66, 93%の損失がMFE=0(instant death)
  - BE guard効果は限定的(6%, 23.3p) — 根本原因はエントリー品質
  - London session WR=27-30%(最悪), GBP/USD NY slippage=1.11p(最大)

## 2026-04-04 P0 BT<>Production Gap Fix + Monitoring Phase

- **Root Cause: COOLDOWN mismatch**: BT=1 bar (15min) vs Production=30s -> 30x faster re-entry -> WR 62%->40% gap
- **DT COOLDOWN unification**: 30s -> 900s (1 bar=15min) -- BT/Production fully synced
- **1H/Swing COOLDOWN unification**: 1H=3600s, Swing=14400s -- matching bar length per TF
- **All BT EXIT-based cooldown**: `last_bar = i` -> `i+1+bars_held` (prevent overlapping trades during hold)
  - BT DT: 344t->62t (-82%), MaxDD 18.4%->3.97% (-78%), ema_cross WR stable 62%
- **SL floor**: ScalperEngine/DaytradeEngine: ATR(14)x1.0 minimum SL distance
- **ADX academic thresholds**: Trend strategies ADX>=20 (stoch/ema_pullback/squeeze/ema_cross/sr_fib), Range bb_rsi ADX<25
- **mtf_confluence MACD condition**: OR->AND (macdh>0 OR macdh>prev was non-functional filter)
- **trend_rebound disabled**: Counter-trend in strong trends has no academic edge (Moskowitz 2012)
- **stoch_pullback disabled**: ADX>=20 yields EV=-0.130, 1min ADX lag makes edge insufficient
- **ema_pullback disabled**: ADX>=20 yields WR=51.1% EV~0, same family, insufficient edge
- **P0 monitoring logging**:
  - Slippage: signal_price vs entry_price diff (pips) saved to DB + logged
  - COOLDOWN proof: seconds since last exit saved to DB + logged (900s compliance)
  - Spread: OANDA real spread at entry/exit saved to DB + logged
  - New DB columns: signal_price, spread_at_entry, spread_at_exit, slippage_pips, cooldown_elapsed
- **Phase transition**: Parameter tuning complete -> Production data accumulation & friction monitoring phase

## 2026-04-03 FX Analyst Review

- **P0 BE spread correction**: BE move uses BUY=entry+spread, SELL=entry-spread (prevent false BE wins)
- **P1 BT time-varying spread**: `_bt_spread(bar_time, symbol)` -- Tokyo early 0.8pip, LDN/NY 0.2pip, NY late 0.8pip. Applied to all 8 BT functions
- **P1 per-pair position management**: max_open_trades=4 (safety cap) + per-pair 1 position limit. USD/JPY and EUR/USD independent
- **P2 SL technical positioning**: SR-based (nearest_support/resistance - ATRx0.3) > ATR-based (x0.8/1.0/1.5) priority. RR>=1.0 guaranteed
- **P2 strategy auto-promotion**: All strategies trade in demo -> N>=30 & EV>0 promotes to OANDA / EV<-0.5 demotes. Re-evaluated every 10 trades
  - `/api/demo/status` -> `strategy_promotion`
  - Demo=data accumulation, OANDA=performance-based selection
- **BT/Production param unification**: BE=60% (no trailing), cooldown=1 bar, no time restrictions
- **EUR/USD pips calc fix**: realized_pl/units -> price-diff method (demo_db.py)
- **EUR/USD rounding fix**: round(x,3) -> _rp(x,symbol) for 5-digit pairs (app.py all signal functions)

## 2026-04-03 SL Hunting Countermeasures + Strategy Consolidation

- **SL hunting #1**: Cross-strategy cascade CD -- SL_HIT on same pair triggers cooldown for all strategies (scalp:90s, DT:180s)
- **SL hunting #2**: Session transition SL widening -- UTC 0,1,18-21h: SL +ATRx0.2 (BT+Production)
- **SL hunting #3**: Fast-SL adaptive defense -- fast SL (<120s) in last 5min -> next SL +ATRx0.3 (Production only)
- **SL hunting #4**: Counter-trend buffer -- 5 mean-reversion strategies against L1 -> SL +ATRx0.25 (BT+Production)
- **SL hunting E1**: Spread filter -- spread>1.2pip(JPY)/1.5pip(EUR) blocks entry
- **SL hunting A1**: Spike detection -- >0.5ATR move in 60s blocks entry
- **SL hunting B1**: Round number SL avoidance -- .000/.500 nearby SL shifted 2.5pip outward
- **SL hunting C1**: Time-based retreat -- 50% hold elapsed + unrealized loss -> early exit before SL (TIME_DECAY_EXIT)
- **SL hunting D1**: SL-distance lot sizing -- OANDA lot 0.5-1.5x based on SL vs 3.5pip reference
- **SL hunting F1**: SL cluster avoidance -- new SL within 2pip of existing position SL -> entry blocked
- **Strategy consolidation (33->9)**: Major consolidation based on FX analyst review
  - Scalp 7: bb_rsi, macdh, stoch_pullback, bb_squeeze, london_bo, tokyo_bb, mtf_reversal
  - DT 2: sr_fib_confluence, ema_cross
  - 1H Zone: **Entire mode DISABLED** (0.15pip/day, resource cost unjustified)
  - Removed: v1-compat 6, trend_rebound, ihs_neckbreak(scalp), sr_touch_bounce, DT ihs_neckbreak, DT fallback 3
  - Planned merge: fib_reversal->bb_rsi, v_reversal->bb_rsi
- **bb_rsi/macdh mutual exclusion**: correlation 0.65 pair firing same direction within 3min -> only higher EV executes
- **BT SL hunting applied**: Scalp/DT BT with #2 #4 -> Scalp WR 58.6->60.1% EV +0.269->+0.314, DT WR 65.2->73.5% EV +0.283->+0.524

## 2026-04-03 OANDA Spread + Position Sync

- **OANDA real spread integration**: Demo entry/exit uses OANDA bid/ask (fixed mid -> real spread)
  - Entry: BUY=ask, SELL=bid (same as OANDA execution logic)
  - SL/TP: BUY position=bid, SELL position=ask (exit also reflects spread)
  - SIGNAL_REVERSE / manual close also use bid/ask
  - `fetch_oanda_bid_ask()` added -> returns bid/ask/spread/mid
- **Demo->OANDA position sync**: Orphan positions (demo CLOSED but OANDA OPEN) detected every 5s and auto-closed
  - `_sync_demo_to_oanda()`: fetches OANDA openTrades, closes unmapped trades
  - Demo as source of truth, resolves OANDA orphans
- **OANDA integration points**: Entry(ask/bid) / SL/TP(bid/ask) / Signal reverse(bid/ask) / Manual(bid/ask) / Orphan close(5s)

## 2026-04-03 1H Zone v4 + Scalp Optimization

- **1H Zone v4 rewrite**: Deprecated 6 strategies (mtf_momentum, session_orb, pivot_breakout, etc.), rebuilt around h1_breakout_retest
  - **h1_breakout_retest**: Strong SR (strength>=0.5, touches>=3) breakout retest entry (Bulkowski 2005)
  - Break quality filter: break candle body >0.3-0.5ATR required (noise break elimination)
  - HTF trend filter: 4H(EMA9/21) + 1D(EMA50/200 + EMA50 slope 24 bars) alignment
  - Strong bull blocks SELL / Strong bear blocks BUY
  - HTF trend bonus: 4H+1D match +0.5, 1D match +0.3
  - SL=0.8ATR (0.5 causes 1-bar stops on 1H noise, 1.0 degrades WR)
  - TP=4.0ATR, BE at 70%TP, Trail 1.2ATR, MAX_HOLD=30 bars
  - h1_sr_reversal disabled (WR=25%)
- **bb_rsi_reversion ADX threshold**: 35->28->32 (28 halves count, 32 optimal frequency/WR balance)
- **bb_rsi_reversion Stoch cross gap**: (stoch_k - stoch_d) > 1.5 required (noise cross elimination)
- **bb_rsi_reversion prev-bar direction**: BUY requires prev bearish, SELL requires prev bullish
- **stoch_trend_pullback frequency increase**: ADX threshold 20->18, RSI/Stoch/BBpb ranges expanded
- **fib_reversal multi-lookback**: lookback 60->[45,60], Fib proximity 0.25->0.35ATR
- **macdh_reversal mean-reversion reclassification**: Added to _mean_reversion_types (EMA200/HTF hard filter -> soft penalty)
  - Before: 56t WR=53.6% EV=+0.171 -> After: 172t WR=57.6% EV=+0.175 (BUY WR 44%->62% recovered)
- **Async chunked BT**: /api/backtest-long endpoint, 7-day chunk async BT (30d+ BT Render timeout workaround)
- **BT mode=daytrade_1h added**: /api/backtest?mode=daytrade_1h calls run_1h_backtest

## 2026-04-03 Production Data Analysis Optimization

- **DT HTF hard filter**: htf_agreement=bull blocks SELL completely (score x0.50 -> return WAIT). Prevents 12-loss -101pip streak
- **Circuit breaker implementation**: _total_losses_window: N losses in 30min pauses mode (scalp:4, DT:3, 1H:2)
- **DT same-direction position limit**: 5->2, same price distance: 1.5->5pip, cooldown: 300->600s (machine-gun entry prevention)
- **pivot_breakout disabled**: Production WR=0% (3t -66.4pip), removed from BT/Production QUALIFIED_TYPES
- **max_consecutive_losses**: 9999->3 (same-direction consecutive loss control activated)
- **Scalp enhancement**: same-dir positions 2->3, same price distance 1.5->1.0pip, cooldown 120->60s (good WR=56.4% more entries)
- **BT QUALIFIED_TYPES unification**: scalp(engulfing_bb,hs_neckbreak,sr_channel_reversal disabled), DT(hs_neckbreak,ob_retest disabled), 1H(pivot_breakout disabled) -- matched to production
- **Scalp EMA200 hard filter**: EMA200 above + slope rising blocks SELL completely (production macdh_reversal|SELL WR=0% -15.4pip fix)
- **Scalp HTF hard filter**: HTF bull blocks SELL, bear blocks BUY completely (soft decay score x0.6 -> full block)
- **OANDA v20 sub-account connection**: Claude_auto_trade_KG (001-009-21129155-002), hedgingEnabled=true, API token reissue resolved 403

## 2026-03-31 v2 Major Refactor

- BT/Production logic unification: All 3 modes use signal functions
- ema_cross: ADX<15 filter added (old WR 26.7% -> improved)
- HTF filter: Range (ADX<20) uses soft bias (SELL bias eliminated)
- SL: ATR7x0.5->0.8 expanded, SLTP check interval 0.5s
- Time filter: UTC 00,01,21 blocked (94% loss concentration)
- Consecutive loss control: 3 same-direction losses pauses
- Duplicate entry prevention: same-direction position + price proximity check
- SIGNAL_REVERSE minimum hold: scalp 60s, daytrade 300s, swing 3600s
- Swing signal: threshold 0.15->2.5/6.0, SL/TP 2.5/4.5->1.0/2.5, SR proximity scoring
- **Friday filter**: scalp threshold 3x, tokyo_bb blocked, DT SR blocked (UTC<7)
- **tokyo_bb entry_type fix**: early return includes entry_type (BT analysis accuracy)
- **HTF cache fix**: compute_daytrade_signal HTF bias uses htf_cache (BT)
- **EMA spread multiplier**: ema_pullback score adjusted by EMA9-21 spread
- **Post-SL cooldown**: Block same-direction/same-price re-entry after exit (scalp:120s, DT:600s, swing:7200s)
- **SIGNAL_REVERSE hold extension**: scalp 60->180s, DT 300->600s (whipsaw prevention)
- **Layer1 direction check**: demo_trader blocks L1 (bull/bear) counter-trend trades
- **sr_fib_confluence threshold**: 0.20->0.35 + EMA direction alignment required (production 0% WR fix)
- **dual_sr_bounce**: EMA direction alignment required (production 0% WR fix)
- **Auto-start**: All 3 modes auto-start on server boot (Render restart resilience)
- **Thread resilience**: Backoff on consecutive errors (thread crash prevention)
- **DB connection leak fix (B3)**: _safe_conn() context manager for all DB ops (try/finally guaranteed)
- **Watchdog auto-recovery**: Every 60s recovers running=False modes (B4 break bug fix)
- **max_open_trades**: 3->20 (allow multiple positions per mode)
- **auto_start dedup**: _auto_start_done flag (double-import race prevention)
- **stop() clears _started_modes**: Watchdog doesn't recover explicitly stopped modes
- **Drawdown control**: Daily -30pip / Max DD -100pip auto-stop
- **BT realistic spread**: scalp 0.5pip->1.5pip (realistic spread)
- **HTF lookahead fix**: BT HTF cache neutralized (lookahead bias removal)
- **1H Zone v2**: compute_1h_zone_signal full rewrite (academic paper-based 4 strategies)
  - mtf_momentum (Moskowitz 2012), session_orb (Ito 2006), pivot_breakout (Osler 2000), pivot_reversion
  - session_orb, pivot_reversion disabled based on BT results
  - Zone constraints: mtf_momentum zone-agnostic (trend-follow), pivot_breakout requires EMA alignment
  - MAX_HOLD: 12->18 bars (WR +3%, ATR EV +75%)
- **DT 15m optimization**: ema_cross ADX threshold 15->12, ema_score THRESHOLD 0.25->0.20
- **QUALIFIED_TYPES update**: 1h new entry_types (mtf_momentum, session_orb, pivot_breakout, pivot_reversion)
- **Rebound fix #1**: All-direction circuit breaker -- N losses in 30min pauses mode (scalp:4, DT:3)
- **Rebound fix #2**: Price velocity filter -- >8pip move in 10min blocks counter-direction entry [Cont 2001]
- **Rebound fix #3**: ADX regime counter-trend block -- ADX>=35 strong trend blocks counter-trend entry (except trend_rebound)
- **Rebound fix #4**: Breakeven + trailing stop -- 60%TP: SL->BE+0.5pip, 80%TP: SL->TP 50% level
- **Scalp v2.3 reversals**: sr_channel_reversal, fib_reversal, mtf_reversal_confluence added
- **DT v2 reversals**: dt_fib_reversal, dt_sr_channel_reversal, ema200_trend_reversal (fallback strategies)
- **1H Zone v3**: h1_fib_reversal (Fib 120-bar, EMA required->bonus), h1_ema200_trend_reversal (EMA200 retest, ADX>=15)
- **Thread self-recovery**: get_status() auto-recovers MainLoop/Watchdog/SLTP/all modes, BaseException catch, request_tick fallback
- **Gunicorn gthread**: --worker-class gthread + timeout 300s (thread stabilization)
