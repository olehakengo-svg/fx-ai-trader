# 単一エンジン化 deploy 後の readout — (iv) 近接ペア 0 ✅ + shadow 生成率 −33% の regime break (2026-10-13、autopilot、rule:R3 record-only)

**読み手**: registry `dual-engine-master-worker-disposition` (iv) 翌週 readout (10-13) / [[http-blind-fork-poisoning-2026-09-22]] §6 / [[dual-engine-dup-rate-readout-2026-09-24]] §4 の「regime break は単一化後の before/after 層別で判定」の執行。**母集団は件数・時刻・marker のみ (outcome / EV / WR は読まない)**。
**データ**: 本番 `/api/demo/trades?limit=5000` (2026-10-13T01:0xZ 取得、窓は 07-28T16:13Z〜10-13T01:01Z = 両期間を被覆)。regime break 二次キー = **2026-10-04T06:03:40Z** (PR #308 merge 95d58906 → `dep-db0unirtqb8s738pta40`)。

## 0. 要旨

| 問い | 答え | 節 |
|---|---|---|
| (iv) deploy 後 1 週間の近接ペア (同 type×pair×dir、Δ≤45s) | **0 ペア** (364 行、Δ≤600s の同セル連続も 4 組で全て >120s) | §1 |
| (iii) marker | **364/364 `forked:forkchild`**、`import:*` 0 / marker 無し 0 / `statusheal` 0 | §1 |
| `dedup_violation=1` の share | 8.2% (dual 期) → **0.9%** (3 行、全て直前同セル行から >120s = bar 内 re-emit 型、cross-process ではない) | §1 |
| shadow 生成率 (kept = `is_shadow=1 ∧ dedup_violation≠1`、取引日あたり) | **87.0 → 58.2 (中央値 89 → 57)、−33%** — 09-24 readout §4 の「30% 未満は検出できない」自然実験 (N=2 日) では見えなかった **regime break が実在** | §2 |
| どこが減ったか | **15m daytrade 系のみ** (72.3 → 46.0/日、−36%)。5m scalp / 1m / rnb は不変。`daytrade` (USD_JPY 15m) が −62% で最大 | §2 |
| 機構仮説 H1 | 減った行は**同セルの短間隔 re-emit** (直前 kept 行から ≤4h) に集中 (≤30m −69% / ≤1h −47% / ≤2h −47% / ≤4h −60%、≤8h ±0、>8h −23%) = dual 期は master/worker が**別々の in-memory 状態** (recent_emit 60–900s / cooldown 1 bar / ORDER_BAR_DEDUP 予約) を持ち、片方が cooldown 中でももう片方が次 bar で同セルを emit できた。write-time dedup は**同 bar の twin しか捕捉しない**ので、これらは kept として残った | §3 |
| 含意 | dual 期 (〜10-04) の 15m shadow N 蓄積率は構造 artifact で ~1.5× 膨張していた。**行自体は無効ではない** (各行は実シグナル評価) が、BT の COOLDOWN=1 bar では出ない行を含む → cadence 前提 (t8 13.3/週 / t9 3.9/週 / ecg 4.0/週 / sr_anti_hunt・ws3 の ETA) は post 期の率で読み直す。LOCK 母集団の規則変更は R1 (user) — 本 readout は層別キーの提供のみ | §4 |

## 1. (iii)(iv) 検証 — 単一化は設計どおり

窓 = deploy 10-04T06:03:40Z 以降の新規 row **364** (10-05T00:00:19Z〜10-13T01:01:25Z; shadow 355 / live 9)。

- marker: `[EMIT_PROC] forked:forkchild` **364/364**。2 系列目なし。status: `engine_pid` 96 / `engine_import_pid` 60 / role forked / origin forkchild (10-13T01:0xZ、10-10 ps demote deploy で pid 95 → 96)
- 近接ペア (同 entry_type×instrument×direction で連続 2 行の Δ≤45s): **0**。Δ≤600s の同セル連続は 4 組で全て 120s 以上の bin
- `dedup_violation=1`: **3 行** (10-05 00:02:45 gotobi_fix USD_JPY BUY Δ146s / 10-05 11:47:30 session_time_bias EUR_USD SELL Δ847s / 10-07 08:16:45 vix_carry_unwind USD_JPY SELL Δ295s) — いずれも直前同セル行から >120s = 09-24 readout §2 の「同一プロセス bar 内 re-emit (54/195)」型。cross-process 型 (Δ≤45s、dual 期 132/195) は **0**
- → registry (i)〜(iv) 全て着地。`dual-engine-master-worker-disposition` **resolved** (本 doc §0 + 二次キー 10-04T06:03:40Z)

## 2. regime break — shadow 生成率 before/after

kept shadow 行 / 取引日 (平日のみ、`is_shadow=1 ∧ dedup_violation≠1`):

| 期間 | 日数 | 平均 | 中央値 | range |
|---|---|---|---|---|
| pre (09-14〜10-02、dual) | 15 | **87.0** | 89 | 63–102 |
| post (10-05〜10-12、single) | 6 | **58.2** | 57 | 50–67 |

post の 6 日は全て pre の最小 (63) を下回る (順位検定の必要なし — 分布が重ならない)。⚠️ post N=6 日・1.5 週。10-27 (2 週目終了) に再読して確定する (registry `single-engine-shadow-rate-attribution-readout`)。

TF 別 (行/日): 15m **72.3 → 46.0** (−36%) / 5m 7.3 → 6.2 / 1m 5.7 → 5.2 / 1h 1.7 → 0.8 (N 小)。
mode 別 (行/日、pre → post): `daytrade` (USD_JPY) **23.1 → 8.8** / gbpusd 11.2 → 9.5 / eurjpy 10.3 → 5.7 / eur 9.3 → 7.3 / audjpy 8.2 → 6.7 / gbpjpy 6.5 → 4.8 / eurgbp 2.7 → 2.2 / scalp 系 合計 12.9 → 11.3 / rnb_usdjpy 0.9 → 1.0。
entry_type 別 (上位): dual_sr_bounce 13.3 → 9.3 / dt_sr_channel_reversal 10.4 → 5.7 / session_time_bias 6.3 → 4.7 / wick_imbalance_reversion 5.3 → 3.2 / streak_reversal 5.3 → 2.5 / sr_break_retest 3.9 → 4.5 / bb_squeeze_breakout 3.6 → 3.7 / xs_momentum_rsi 2.4 → 0.3 / london_fix_reversal 1.7 → 0。
時間帯: 全時間帯で減少 (07–16Z の London/NY 帯が絶対数で最大の減少)、特定 session に偏らない。

## 3. 機構仮説 H1 — per-process 状態の二重化が短間隔 re-emit を許していた

15m shadow kept 行について「直前の同セル kept 行からの Δ」(行/日):

| Δ | pre | post | 変化 |
|---|---|---|---|
| ≤30m | 9.13 | 2.83 | **−69%** |
| ≤1h | 8.53 | 4.50 | −47% |
| ≤2h | 7.53 | 4.00 | −47% |
| ≤4h | 5.87 | 2.33 | −60% |
| ≤8h | 4.27 | 4.33 | ±0 |
| >8h | 36.1 | 27.7 | −23% |

- 減少は **≤4h の短間隔 re-emit に集中**し、≤8h は不変。dual 期は master と worker が別々の in-memory 状態 (`recent_emit` 60–900s 窓 / COOLDOWN 1 bar = 15m / `ORDER_BAR_DEDUP` 予約) を持つため、A が emit → A は cooldown、B は同 bar では DB gate (open trade / max_per_mode_pair) で block されるが、A の shadow 行が閉じた**次 bar 以降**に B は自分の cooldown を持たないので同セルを再 emit できる。write-time dedup (2026-09-02) は同 bar の twin のみ捕捉 → これらは `dedup_violation=0` の kept 行として残った。単一化で消えたのはこの経路
- `daytrade` (USD_JPY 15m) が最大 (−62%) なのは、同 mode が cooldown 系 counter (persisted `daytrade:consec_loss` 40 / `cascade_cd` 5 / `cooldown` 5) を最も多く持つことと整合
- **>8h の −23% は H1 で説明されない残余** (市場 regime / 週構成 / N=6 日)。10-27 再読で分離する (H1 なら短間隔のみ、regime なら >8h も残る)
- H1 は**仮説**。確定には dual 期の短間隔 re-emit 行が 2 プロセスのどちらから出たか (marker は 09-24 計装以降のみ) の層別が要る — 09-24〜10-02 の marker 付き dual 期 kept 行で `import:*` vs `forked:*` の Δ 分布を出せば検証できる (10-27 readout に含める)

## 4. 含意 (record-only、挙動変更なし)

1. **単一化は正しい設計で、post 期の率が「本来の」shadow 生成率**。dual 期 15m shadow は BT (COOLDOWN=1 bar) が出さない短間隔 re-emit を ~1.5× 含んでいた = BT⇄shadow の cadence 乖離の一因
2. **行の有効性**: dual 期の kept 行は各々実シグナル評価であり無効化しない。ただし pre-reg / LOCK の母集団に「同セル ≤4h の re-emit」が含まれる割合が dual 期と post 期で異なる → **deploy 時刻 10-04T06:03:40Z で層別できるようにしておく** (09-24 readout §6 の設計どおり)。LOCK 母集団規則の変更は R1 = user 決裁 (`sr-anti-hunt-eurjpy-count-basis-declaration` と同じ決裁点に「re-emit の扱い」を載せるかは user)
3. **cadence 前提の読み直し**: `t8-hull-shadow-freq` (期待 13.3/週) / `t9-kalman-d7-fire-info` (3.9/週) / `ecg-stb-postfix-fire-info` (4.0/週) / sr_anti_hunt EUR_JPY ETA (1.75 本/週) / ws3 recheck の retire 判定は post 期の率で再見積りする — 10-27 readout で post N≥2 週になってから
4. **やらないこと**: 生成率を戻すための gate 緩和・cooldown 短縮 (= dual 期の artifact を意図的に再現すること) はしない。4原則 #4 は「データ蓄積優先」だが、BT が出さない行を増やすのは蓄積ではなく汚染

## 5. 開示

本 readout の (iii)(iv) 集計スクリプトで live 9 行 (kalman_d7_po_dn_flip 4 / usdjpy_carry_dip_accumulator 4 / price_shock_rev_eur_gbp_h1_long 1、10-05〜10-09) の `outcome` 列を 1 回印字した (件数確認の print に outcome を含めてしまった)。R2 `t9-kalman-d7-live-n10-ev-check` (N=9/10) と carry_dip の母集団に対する outcome 観測 1 回。統計は計算していない。kalman C0 readout ([[kalman-d7-live-constrained-bt-2026-09-27]] §3′) は outcome 列を除去した JSON で別途実行した。

## 関連
[[http-blind-fork-poisoning-2026-09-22]] §6 / [[dual-engine-dup-rate-readout-2026-09-24]] / MEMORY `project_single_engine_deploy_regime_break_2026_10_04` / registry `dual-engine-master-worker-disposition` (resolved 10-13) → `single-engine-shadow-rate-attribution-readout` (10-27) / [[2026-10-13-session]]
