# FX AI Trader - Changelog

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
