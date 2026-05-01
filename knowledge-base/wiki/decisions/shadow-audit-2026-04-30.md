# Shadow 含む 4/30 トレード監査 — 結論: Mixed (R3 即修正対象 + 統計的優位性は未確立)

**監査日**: 2026-05-01
**観測者**: ユーザー
**対象**: `https://fx-ai-trader.onrender.com/demo-analysis` で 4/30 単日 shadow 含むトレードが「かなり大きな勝ち」に見えた件のシニアクオンツ監査

## TL;DR

| 仮説 | 結論 |
|---|---|
| H_design (BE/Trail revert fix で利益確定が機能) | **不支持** — close_reason に BE_HIT/TRAIL_HIT が一件も出現せず |
| H_runaway (rsk_gbpjpy_reversion の per-bar dedup gate 欠落) | **強く支持** — 76件中63件が <90s 間隔、20:16-20:30 で 27 連発、全敗 -813.7p |
| H_smallN (右尾外れ値依存) | **支持** — top10 winners +1261p / 全体 -154.4p、bootstrap CI95 = [-1101, +914] で 0 跨ぎ |
| H_corruption (PnL 計算誤り) | **不支持** — 432件全件で `(exit-entry)*pip*sign` ≡ `pnl_pips` (誤差 <1p) |
| H_misroute (shadow → OANDA 実弾誤送信) | **未検出** — close_reason / oanda_audit 突合で異常なし |

**最終判定**: **Mixed (介入相場での意図通り発火 + 未修正 R3 バグの併走)**

**Critical context (2026-05-01 user 追記)**: 2026-04-30 は **日本政府の為替介入** が発生し、USD_JPY を中心に異常チャート形成。このため:
- post_news_vol / vix_carry_unwind の USD_JPY TP_HIT 連発（+361.7p / +583.0p）は **戦略クラス設計通りに介入ボラを捉えた windfall**。汎用エッジ評価には**使えない単日特異点**
- rsk_gbpjpy_reversion 76件全敗は単なる per-bar dedup バグだけでなく、**regime break 中に MR 戦略が走り続けた** 二重失敗。bar-close gate 修正に加え **介入/規制相場検出時の MR 抑止 (regime gate)** が要検討

**意味づけ**:
- ユーザーが見た「+828.1p / 174t」は **rsk runaway が完全に走り切る前の partial snapshot** + 介入ボラを捉えた高R戦略の TP_HIT 集中。**「設計通りに走るべき戦略がきちんと走った」**点で僥倖だが、**汎用エッジの根拠にはならない**
- 日終わりは shadow 全体 -154.4p。bootstrap CI95 が 0 を跨ぐため **統計的優位性なし**
- vix_carry_unwind / post_news_vol / sr_fib_confluence / xs_momentum / dt_fib_reversal / ema_cross は PF > 2 の候補だが Wilson_BF lower < 50% + **介入日含む N で評価しているため pre-reg LOCK 維持必須**

## 即時アクション

### Rule R1 候補 — 介入日除外 / regime gate 追加
- 4/30 USD_JPY 介入により、vol-spike 系戦略の N に **政治的尾事象**が混入。pre-reg LOCK 期間中の N カウントから除外する仕組みを検討
- MR 系戦略（rsk, bb_rsi_reversion, sr_channel_reversal, engulfing_bb 等）に **介入相場検出時の自動抑止** (例: ATR 5σ シグナル / 中銀発表時刻ブラックアウト) が必要
- 関連 lesson: [lesson-mid-day-regime-shift.md](../lessons/) があれば参照、無ければ新規起票候補

### R3 (構造バグ即修正) — rsk_gbpjpy_reversion bar-close gate

**根拠**:
- [strategies/daytrade/rsk_gbpjpy_reversion.py:31](../../../strategies/daytrade/rsk_gbpjpy_reversion.py) は `iloc[-1]` 参照のみで bar-close gate / per-bar dedup を実装していない
- 既存の vsg fix [commit 8719a44](../../../) で確立されたパターン: `iloc[-2]` を closed bar として参照、`self._last_emit_bar_ts` で同一バー再発火を抑止
- 実測: 4/30 で rsk shadow 76件中 61件が <60s 間隔、ユニーク signature 39 / 76 (50% が同一 SL/TP の重複)
- [lesson-shadow-emit-dedup-2026-04-30.md](../lessons/lesson-shadow-emit-dedup-2026-04-30.md) の shadow_emit dedup gate は demo_trader レイヤだが、rsk は **戦略ロジック側で同一バー intra-bar 多重発火** が止まっていないため、demo_trader gate を貫通している

**修正範囲**:
- vsg と同じパターンで rsk_gbpjpy_reversion に bar-close gate + `_last_emit_bar_ts` 導入
- 副次: 同様の戦略を grep で洗い出し（`iloc[-1]` を closed bar 扱いしている候補）
- 既存テスト `tests/test_phase5_strategies.py::TestRskGbpjpyReversion` に bar-close gate 仕様の regression 追加

### Rule R2 (Reactive 降格) — 個別戦略の即時抑制

| 戦略 | N | sumP | 措置 |
|---|---|---|---|
| rsk_gbpjpy_reversion | 76 | -813.7 | R3 修正後再評価。修正前は SHADOW 抑制 |
| vsg_jpy_reversal | 8 | -163.1 | fix 済みだが effect 未現出。1日では判断保留 |
| htf_false_breakout | 6 | -126.7 | N=6 / 0win → cell-level 監視継続 |
| engulfing_bb | 20 | -106.2 | WR 15.8% / PF 0.15。直近 14d で再評価 |
| sr_anti_hunt_bounce | 5 | -83.8 | 0win — but small N |

## Phase A — Integrity 詳細

### A1: 174 trade snapshot vs 443 trade end-of-day

| ソース | 件数 | sumP | 備考 |
|---|---|---|---|
| ユーザー観測 (UI partial) | 174 | +828.1 | 4/30 途中、rsk runaway 完了前 |
| `/api/demo/stats` (4/30, include_shadow=1, dedup_violation=0) | 404 | +287.7 | dedup_violation=1 を 39件除外 |
| `/api/demo/trades` (4/30, all closed) | 443 | -158.7 | 生データ全量 |

差分:
- 443 - 404 = 39件 が `dedup_violation=1` で stats から除外されている
- 174 → 404 = 230件 が観測時点以降に追加クローズ → そのうち rsk runaway 76件中の大半 (-813.7p)

### A2: PnL 妥当性
- 432 shadow trades 全件で `(exit_price - entry_price) × pip_multiplier × direction_sign` と `pnl_pips` の差分 < 1p
- **mismatch 0** → bookkeeping 異常なし

### A3: shadow ⇄ LIVE 経路混入
- close_reason cross-tab で shadow=1 ⊆ {SL_HIT, TP_HIT, SIGNAL_REVERSE, TIME_DECAY_EXIT, MAX_HOLD_TIME, MANUAL_CLOSE}（virtual exit のみ）
- shadow=0 ⊆ {SL_HIT, TP_HIT, OANDA_SL_TP}
- **OANDA_SL_TP は shadow に出現せず** → shadow 経路から OANDA 実弾送信は発生していない

### A4: dedup_violation 残存
- 4/30 内訳は `/api/demo/trades` payload に `dedup_violation` カラムが入っており、stats 側で除外されている
- ただし **rsk runaway は dedup_violation=0 のまま大量計上** されており、`_backfill_dedup_violation_impl` は 「同一 (entry_type, instrument, direction) で 60s 以内」を見ているはずが rsk の同 60s 内クラスター 13個 (うち 27連発含む) を捕捉していない
- → backfill ロジック自体に miss があるか、または signal_emit 時点で SHADOW_EMIT dedup gate が rsk に対して機能していない

### A5: 右尾外れ値
- top10 winners 計 +1261.2p（全体 -154.4p の対比）
- 1位 post_news_vol +196.3p (USD_JPY TP_HIT)
- 2-7位 vix_carry_unwind 系 +140 〜 +96p (USD_JPY TP_HIT 連発)

## Phase B — Quant 詳細

### B1: 戦略別フルメトリクス（4/30 単日 shadow only, N≥5）

| Strategy | N | WR% | Wilson95 | Wilson_BF (z=3.29) | PF | sumP | EV |
|---|---:|---:|---:|---:|---:|---:|---:|
| **vix_carry_unwind** | 31 | 32.3 | 18.6 | 12.6 | 2.30 | +583.0 | +18.81 |
| **post_news_vol** | 7 | 42.9 | 15.8 | 8.4 | 7.41 | +361.7 | +51.67 |
| **sr_fib_confluence** | 21 | 57.9 | 36.3 | 25.1 | 3.84 | +187.1 | +8.91 |
| **xs_momentum** | 18 | 61.1 | 38.6 | 26.8 | 3.13 | +174.2 | +9.68 |
| dt_sr_channel_reversal | 7 | 57.1 | 25.0 | 14.0 | 2.24 | +76.0 | +10.86 |
| dt_fib_reversal | 5 | 80.0 | 37.6 | 20.5 | 24.18 | +64.9 | +12.98 |
| ema_cross | 5 | 100.0 | 56.6 | 31.6 | inf | +62.4 | +12.48 |
| ema_trend_scalp | 77 | 33.8 | 23.7 | 18.4 | 0.97 | -7.5 | -0.10 |
| bb_rsi_reversion | 30 | 32.0 | 17.2 | 11.2 | 0.57 | -32.3 | -1.08 |
| sr_channel_reversal | 25 | 20.8 | 9.2 | 5.5 | 0.35 | -68.0 | -2.72 |
| engulfing_bb | 20 | 15.8 | 5.5 | 3.0 | 0.15 | -106.2 | -5.31 |
| **rsk_gbpjpy_reversion** | **76** | **0.0** | **0.0** | **0.0** | **0.00** | **-813.7** | -10.71 |

**重要**:
- どの戦略も Wilson_BF (z=3.29) lower > 50% を満たさない → **shadow promotion gate を 4/30 単日では誰も通過できない**（pre-reg LOCK 維持で正解）
- ema_cross は PF=inf (5戦5勝) だが N=5 で N≥20 ゲート未達。ただし [_decide_promotion_status](../../../modules/demo_trader.py:5365) の通過候補
- vix_carry_unwind / post_news_vol は EV/PF が突出するも N が薄い + WF h1=139 / h2=-14 (post_news_vol) のような**強い時間内 decay** → 4/30 一日単独現象の可能性大

### B2: Bootstrap 95% CI（shadow 全体 N=432）

| 推定 | 値 |
|---|---|
| 点推定 sumP | -154.4 |
| Bootstrap 95% CI | **[-1101.5, +914.4]** |

→ **CI が 0 を大きく跨ぐ** ⇒ 「shadow 全体は 4/30 に勝った」と統計的に主張できない。ユーザーの観測は intra-day partial と右尾依存の合作。

### B3: Counterfactuals（仮想 population）

| 構成 | N | sumP |
|---|---:|---:|
| Full shadow | 432 | -154.4 |
| **Without rsk + vsg (R3 修正後の想定)** | 348 | **+822.4** |
| Without top concentration (post_news_vol + vix_carry_unwind) | 394 | -1099.1 |

→ rsk + vsg を取り除けば +822p。これは ユーザーの観測 +828p と近似 (実は ユーザー snapshot 時点 ≒ runaway 完了前 = rsk 寄与が小さかった時点)。

### B4: 4/30 コミット効果 vs 実測

| Commit | 予測効果 | 実測 | 整合性 |
|---|---|---|---|
| `8719a44` vsg gate | vsg shadow 件数大幅減 | 4/29: 4t / 4/30: 8t (むしろ増) | **未達** — fix 後も 8件 (うち 0win, -163.1p)。fix の効果はテスト green でも production runtime まで届いていない可能性 |
| `7227a6f` UTC22-23 soft-shadow | 当該時間帯 shadow 件数増 | UTC22-23 件数: 詳細未集計 | 要追加検証 |
| `5b555fd` BE/Trail silent revert fix | BE_HIT/TRAIL_HIT 増 | **BE_HIT/TRAIL_HIT が 1件も出現せず** | **未現出** |
| `a88852f` instrument dedup gate | 件数減 | 443 件は依然として高頻度 | **不十分** — rsk が貫通 |

## Phase C — KB 更新提案

### 新規 lesson 起票候補

`wiki/lessons/lesson-rsk-gbpjpy-bar-close-gate-2026-05-01.md`:
- vsg と同根の per-bar dedup gate 欠落が rsk_gbpjpy_reversion にも存在
- 修正パターンは [commit 8719a44](../../../) のテンプレ流用

### CLAUDE.md / 運用ルール強化提案

- 「`iloc[-1]` を closed bar として直接参照する戦略候補」の grep 監査を pre-commit hook 化
- shadow_emit dedup gate は demo_trader レイヤだが、戦略ロジック側の bar-close gate と二段で守るべき（strategy + dedup gate の二重防御）

### Memory 更新候補

`/Users/jg-n-012/.claude/projects/-Users-jg-n-012-test/memory/`:
- 既存 `feedback_live_shadow_separation.md` に追記: 「demo-analysis UI の partial-day snapshot は intra-day で大きく振れる。日終わりまで待って bootstrap CI を取らないと判断しない」
- 新規 `feedback_intraday_pnl_volatility.md` 候補: 「shadow 単日 PnL は bootstrap CI が容易に 0 を跨ぐ。1日の P/L だけで判断しない」

## ユーザーへの一行回答

> **エラーでも純粋な設計通りでもなく、Mixed**: 観測時点 (+828.1p / 174件) は本物の TP_HIT 大当たりの集中だが、その後 rsk_gbpjpy_reversion の **未修正 per-bar dedup gate バグ** が 76 件 runaway を発射し、最終的に shadow 全体 -154p で着地。bootstrap CI95 は [-1101, +914] で「勝ち」とは統計的に言えない。**rsk に R3 修正コミット即発行**、shadow 昇格判断は引き続き保留が正解。

## Verification 完了状況

- [x] 3 ソース突合（user UI / `/api/demo/stats` / `/api/demo/trades`）— 件数差は dedup_violation 除外 + intra-day timing で説明可
- [x] テスト回帰: `pytest tests/test_entry_gates.py tests/test_shadow_promotion_gate.py tests/test_p2_system.py` 40/40 PASSED
- [ ] Codex review: **2026-05-01 時点でレート上限到達 (5/7 解除)。解除後に独立レビュー実施予定**
- [x] 監査 SQL/queries 保存: `queries.sql` 同階層
