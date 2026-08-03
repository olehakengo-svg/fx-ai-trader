# weekend_gap_fade — 週末ギャップ・フェード

- **Status**: 🟢 LIVE (固定 1000u sentinel) — rule:R1 pre-reg LOCK、user 最終承認 2026-07-24 (option (b) 直接 live MIN lot)
- **Tier**: PAIR_PROMOTED (EUR_USD, USD_JPY, AUD_USD) + UNIVERSAL_SENTINEL 併存 (vix_carry_unwind と同型)。GBP_USD は永久対象外 (逆符号 family 用に OOS 清浄維持)
- **実装**: 2026-07-24 (本カードと同一コミット)

## 根拠 (凍結統計 — OOS 再接触・再集計は §8 で禁止)

| 項目 | 値 | 出典 |
|---|---|---|
| OOS verdict | **arm B PASS**: N=177 pair-events / 112 週末、gross +15.60p/event、weekend-block bootstrap p<1e-4、stressed-net +9.04p、knife-edge 4/4 維持 | [[weekend-gap-oos-prereg-2026-07-24]] §11 |
| 実測 RT 置換 (R1 step①) | pooled 初バー実測 RT mean 7.70p / p90 12.34p → net **+7.90p / +3.26p (p90 tail)** — 正 EV 保存 | `reports/sunday_open_spread-2026-07-24.md` §3 |
| 頻度 | ~3.28 イベント/月 (2.07 qualifying 週末/月)、cap skip 計画値 10–20% | OOS report §6 |
| 月次期待 | +22〜26 pip ≈ +$2 @1000u、σ_month ≈ 63p (単月負け 34% = 正常挙動) | 執行 pre-reg §3.2 |
| 執行 pre-reg (LOCKED) | [[weekend-gap-stage2-execution-prereg-2026-07-24]] — §2/§3/§5 の凍結値変更は R1 | user 承認 2026-07-24 |

## シグナル定義 (explore ツールと同一 — `tools/weekend_gap_fill_explore.py` を厳密複製)

- Friday close = Fri 21:00 UTC 境界前の最終 15m バー Close (≤6h guard、mid)
- Sunday open = Sun 21:00 UTC 以降の最初のバー Open (≤24h guard、mid — 冬の 22:0x open もガード内)
- qualify: |gap| ≥ **EUR_USD 20.0p / USD_JPY 21.4p / AUD_USD 25.0p** (凍結。再計算禁止)
- 方向: gap fade (gap up → SELL / gap down → BUY)
- entry 窓: 初バー open ts から 4 bars (bar-length terms、15m→60分)。窓外は不発 (追いかけ禁止)
- **shadow row も同一シグナル経路** — live/shadow の分岐は demo_trader の共通ガードチェーンのみが行う (§4.0: shadow 分母は常に完全、cap は LIVE 側 winning-location フィルタ)

## 執行仕様 (凍結)

| 項目 | 実装 |
|---|---|
| entry | 成行 1 回のみ、**リトライなし** (bridge `max_attempts=1` — timeout retry の二重約定を封鎖) |
| spread cap | 発注時 quoted spread > **10.0p** → live 送信スキップ + shadow row (`block_cause=weekend_gap_spread_cap(spread=X.XXp)`、実測値保存 = 分母保存)。quoted 取得不能時も fail-closed で shadow |
| E1 置換の範囲 | **置換 = E1 per-pair limit + 動的 spread/TP guard の 2 つのみ (entry_type-scoped)**。共有 = is_shadow/is_promoted チェーン、daily loss gate (bridge)、watchdog/blacklist、exposure (1000u 実値で見積)、spike/velocity、order-bar dedup、agg-Kelly (min-lot bypass 登録) / MC-ruin gate |
| exit | **entry+4h (14400s) 成行 time-exit のみ** (`close_reason="horizon"`、exact override — mode default 8h と max() 合成しない)。TP/BE/Trail/BE_LOCK/C1/SIGNAL_REVERSE 全て無効化済み |
| disaster SL | entry ∓ **150p** (OANDA stopLossOnFill)。発火時は `close_reason="disaster_sl"` で個別 flag (G3③ 審査対象)。OANDA 注文に takeProfit は付けない (demo row の TP 500p は engine placeholder) |
| サイジング | **固定 1000u** (`WEEKEND_GAP_FADE_MIN_LOT`)。lot 3-factor / Kelly / DD lever / FLAT_UNITS / agg-Kelly boost 全て非適用を code で固定 |
| dedup | **per-pair per-weekend latch を system_kv 永続** (`weekend_gap_fade:{pair}:{sunday_date}` = EXECUTED / SKIPPED_SPREAD)。row 作成直後・OANDA 送信前に set。DB read 失敗は fail-closed (= latched 扱い) |
| 同時ポジション | 3 ペア同時 qualify は全執行 (§2.4 — 選択的執行禁止。cap skip のみが正当な未執行)。exposure 見積を 1000u 実値にして 20k cap 誤衝突を回避 |

## 実行経路 (夏/冬の非対称に注意)

1. **Primary: scoped Sunday runner** (`demo_trader._weekend_gap_tick`) — `_is_fx_market_closed()` が日曜 22:00 UTC まで True のため、market-closed gate より**前**に本 entry_type 専用の評価だけを走らせる (夏 21:05±2 の estimand を満たす唯一の経路)。発注は通常の `_tick_entry` 共有ガードチェーン — **別送信経路は作らない**。
2. **冗長系: DaytradeEngine 登録** (`strategies/daytrade/__init__.py`) + `LIVE_PROMOTE_LOSERS` side-channel (select_best silent-drop の 7 例目回避)。latch が二重発注を防ぐ。
3. **AUD_USD**: 15m mode が無かったため `daytrade_audusd` を新設 — ただし `weekend_gap_only=True` で**本戦略以外は一切走らない** (他戦略の挙動へ波及ゼロ)。
4. estimand 保存のための scoped 免除 (§2.4「cap スキップのみが正当な未執行」): HTF Hard Block (app.py 候補段, T8 と同型の silent-drop 防止) / EUR_USD Late-NY 静的 gate / MTF tactical bias / SL狩り対策②③B1 (150p 凍結 SL の改変防止)。**口座防御系 gate は全て共有**。

## 前向きゲート (pre-reg §5 — R2 自動停止、code + system_kv)

| gate | 発動 | 実装 |
|---|---|---|
| G0 配管 | 最初の 2 qualifying 週末: 発火時刻 21:05±5m (冬 22:05±5m) / latch / exit 4h±10m / cap 判定ログ | 週次監査 + 月曜 daily report で人手確認 (不備 = R3) |
| **G1 slippage** | live N≥6 rolling mean slippage > +2.0p | `_weekend_gap_check_r2_gates()` が送信前に毎回評価 → 恒久 kv flag `WEEKEND_GAP_LIVE_STOPPED` + `[ALERT][WEEKEND_GAP]` print + AlertManager 通知。**一度 fire したら code 上の再武装経路なし** (watchdog DECREMENT 教訓)。slippage は OANDA 実 fill vs signal_price を bridge が demo row に永続化 (`record_fill_slippage`) |
| **G2 first-look** | live N=12 cumulative net < −60p | 同上 (同一 flag) |
| G3 confirm | live N=30: mean>0 ∧ WR≥35% ∧ disaster SL 0 件 → lot ladder の R1 起案権のみ (自動増額なし) | 人手 (R1) |
| 常設 | 月次 `tools/sunday_open_spread_measure.py` re-run (冬時間初週末は注視) | 既存ツール |

**解除**: `WEEKEND_GAP_LIVE_STOPPED` kv の手動削除 + R1 決裁のみ (code は削除経路を持たない)。stop 後も shadow 蓄積は継続 (分母保存)。

## 監視

- N 定義: live 執行済み pair-event (cap skip は分母記録のみ)。統計検定は weekend-block。
- 週次戦略監査 (`raw/audits/`) に weekend_gap 行を追加、月曜 daily report で前週末イベントに言及 (T5 教訓: 執行されない pre-reg を作らない)。
- 観測点: system_kv `weekend_gap_fade:*` (latch) / `WEEKEND_GAP_LIVE_STOPPED` (stop flag) / oanda_audit `block_reason=weekend_gap_spread_cap*` (cap skip 分母)。

## イベントログ

### 2026-08-02 (日) — 第 2 イベント: qualify → OANDA FOK 不成立 → fail-closed shadow (設計どおり)

| pair | gap | 判定 | 結果 | 備考 |
|---|---|---|---|---|
| USD_JPY | **−22.5p ≥ 21.4p** | qualify → BUY fade | **live 送信 → FOK キャンセル → shadow row (id 14996)** | 経路は完走: Kelly BYPASS → [SENT] 1000u SL 155.646 / TP なし → OANDA `orderCreateTransaction` #549257 生成、しかし**日曜オープンの激動で FOK 不成立 (tradeID なし)**。pre-reg §2.2「成行 1 回・リトライなし」どおり fail-closed shadow 化 (分母保存)。shadow 追跡結果 = **disaster_sl −182.7p** — fill されていれば実損 ≈ −¥1,600〜1,800 で、fill 失敗が結果的に回避。**live 執行分母 (G1/G2) には fill なしのため入らない** |
| EUR_USD | +17.5p < 20.0p | no-qualify | 不発 (正常) | 07-28 追加の週末 gap 診断ログが正常動作 |
| AUD_USD | +23.0p < 25.0p | no-qualify | 不発 (正常) | 同上 |

- 背景: 週末を挟む大規模 JPY 買いイベント (USD_JPY 160.5→155.6 の急落局面)。gap fade BUY は逆行し shadow で disaster SL (signal open −150p = 155.646) 到達
- **観測 (N=1、変更提案なし)**: FOK は「激しい gap ほど不成立になりやすい」可能性があり、実現 live 系列が OOS estimand (bar open fill 仮定) から fill-rate 選択でずれ得る。**執行方式の変更は estimand 破壊 = R1 事項** — 現時点は記録のみ、G3 (N=30) 審査時に fill 失敗率を並記して評価する
- live fill N は依然 0 (07-26 バグ / 08-02 FOK)。G1/G2 未起動

### 2026-07-26 (日) — 初回 qualifying イベント

| pair | gap | 判定 | 結果 | 備考 |
|---|---|---|---|---|
| USD_JPY | qualify | 発火 → row 挿入 + latch 済み | **shadow −22.8p = バグ起因の未送信** | `_is_xau_inst` UnboundLocalError (2026-04-10 から chronic) で OANDA 送信前にクラッシュ。live 執行分母 (G1/G2/G3 の N) には**入れない** — pre-reg 上の正当な未執行ではなくインフラ障害。詳細: [[lesson-preserve-sltp-unboundlocal-2026-07-28]] |
| EUR_USD | **+19.9p < 20.0p** | no-qualify | 不発 (正常) | 閾値 0.1p 差の near-miss。当時 no-qualify は無音 — 2026-07-28 rule:R3 で週末ごと 1 行の gap 診断ログを追加 (分母保存、行挿入なし)。**閾値は凍結値 — near-miss を理由とした再調整は §8 で禁止** |
| AUD_USD | no-qualify | — | 不発 (正常) | — |

**フォローアップ (2026-07-28 rule:R3)**: ① `_is_xau_inst` スコープ修正 + regression pin `tests/test_preserve_types_tick_entry.py` (preserve 全型を送信判定直前まで通す統合テスト)、② wg tick error handler に traceback 追加、③ **データソース**: AUD_USD を `_MASSIVE_SYMBOLS` に追加 — 凍結統計は Massive parquet ベースであり **Massive が estimand 正** (従来 AUD_USD だけ live が OANDA fallback でソース不一致だった)。

## テスト

`tests/test_weekend_gap_fade.py` (29 tests): 検出 (qualify/非qualify/方向/ガード/窓/凍結閾値) / cap 境界とスコープ / latch dedup + fail-closed / G1/G2 発火・境界・**非再武装** / 1000u・horizon・disaster SL・no-TP・登録 4 点 pin。

## 参照

- [[weekend-gap-stage2-execution-prereg-2026-07-24]] (執行 pre-reg LOCK) / [[weekend-gap-oos-prereg-2026-07-24]] (OOS verdict)
- `reports/sunday_open_spread-2026-07-24.md` (実測スプレッド)
- MEMORY: `project_engine_reconstruction_live_dedup_dead` / `project_be_trail_inflates_python_bt_wr` / `project_watchdog_decrement_rearm_bug` / `project_t5_jpy_cap_prereg_executed` / `project_t8_week1_gate_breach`
