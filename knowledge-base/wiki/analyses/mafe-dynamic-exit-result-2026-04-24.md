---
pre_reg: pre-registration-mafe-dynamic-exit-2026-04-24
status: §6.2 Extended Shadow path (LOCKED)
verdict: 0 SURVIVOR / 16 CANDIDATE / 32 REJECT (N=14,185)
---

# MAFE Dynamic Exit — BT Result (2026-04-24)

**Pre-registration**: [[pre-registration-mafe-dynamic-exit-2026-04-24]] (LOCKED 2026-04-24)
**BT window**: 2025-04-09 → 2026-04-08 (365 days, pre-cutoff)
**Pairs**: USD_JPY, EUR_USD, GBP_USD, EUR_JPY, GBP_JPY (XAU除外)
**Target**: `bb_rsi_reversion` (PAIR_DEMOTED, Shadow)
**N (baseline)**: 14,185 trades
**α_cell (Bonferroni, M=48)**: 1.042e-3
**Generated**: 2026-04-24T13:12 UTC

## 0. TL;DR — §6.2 Extended Shadow path

> **SURVIVOR=0 / CANDIDATE=16 / REJECT=32**
> ΔEVは top cell で **+0.54p** (Welch p=0, Fisher p=0, WF 2-bucket 同符号) と
> 統計的にも大きく有意だが、**Wilson 95% lower on V2_WR が max=34.0% < 53% ゲート**
> で SURVIVOR に到達しない。LOCKED 判定木に従い §6.2 Extended Shadow path 適用。
>
> **code deploy は認可されない。** 2026-05-07 以降の holdout 追加 N で再検定。
>
> 同時に、Wilson WR ゲートが cut-loss 機構に対して **構造的に不整合** という
> pre-reg 設計欠陥を独立の lesson として記録 (本 pre-reg の遡及変更は禁止=HARKing 回避)。

## 1. Verdict matrix (48 cells)

### By Z (MAE limit, decisive axis)

| Z (pips) | verdict | mean ΔEV | mean truncated_ratio | 解釈 |
|---------:|---------|---------:|---------------------:|------|
| 3 | 16 CANDIDATE | **+0.53p** | 0.83 | 83% の trade を早期 cut → EV 最大改善 |
| 5 | 16 REJECT | +0.12p | 0.73 | MAE 許容 5p では発動率低下 / ΔEV 不十分 |
| 8 | 16 REJECT | **-0.22p** | 0.53 | 許容広すぎ ΔEV 負転 (遅い cut は悪化) |

**観察**: `Z`(MAE limit) がほぼ 100% の支配因子。`X`(time window) と `Y`(MFE min) の
変動は CANDIDATE 内で ΔEV を ±0.01p しか動かさない → 動的 exit の alpha は
「**3 pips 逆行したら即切る**」という単純ルールに収束する。

### Top 10 cells by ΔEV (from summary.json)

| X | Y | Z | N | base_ev | v2_ev | ΔEV | v2_wr | wilson_lo | welch_p | fisher_p | WF | verdict |
|--:|--:|--:|--:|--------:|------:|----:|------:|----------:|--------:|---------:|:--:|:-------:|
| 3 | 2 | 3 | 14185 | -2.78 | -2.24 | +0.54 | 17.0 | 16.4 | 0e+00 | 0e+00 | Y | CANDIDATE |
| 3 | 1 | 3 | 14185 | -2.78 | -2.24 | +0.54 | 17.3 | 16.7 | 0e+00 | 0e+00 | Y | CANDIDATE |
| 5 | 2 | 3 | 14185 | -2.78 | -2.24 | +0.54 | 17.3 | 16.6 | 0e+00 | 0e+00 | Y | CANDIDATE |
| 12 | 3 | 3 | 14185 | -2.78 | -2.24 | +0.54 | 17.3 | 16.7 | 0e+00 | 0e+00 | Y | CANDIDATE |
| 3 | 0 | 3 | 14185 | -2.78 | -2.24 | +0.53 | 17.3 | 16.7 | 0e+00 | 0e+00 | Y | CANDIDATE |
| 5 | 0 | 3 | 14185 | -2.78 | -2.24 | +0.53 | 17.3 | 16.7 | 0e+00 | 0e+00 | Y | CANDIDATE |
| 5 | 1 | 3 | 14185 | -2.78 | -2.24 | +0.53 | 17.3 | 16.7 | 0e+00 | 0e+00 | Y | CANDIDATE |
| 8 | 0 | 3 | 14185 | -2.78 | -2.24 | +0.53 | 17.3 | 16.7 | 0e+00 | 0e+00 | Y | CANDIDATE |
| 8 | 1 | 3 | 14185 | -2.78 | -2.24 | +0.53 | 17.3 | 16.7 | 0e+00 | 0e+00 | Y | CANDIDATE |
| 8 | 2 | 3 | 14185 | -2.78 | -2.24 | +0.53 | 17.3 | 16.7 | 0e+00 | 0e+00 | Y | CANDIDATE |

### Full distribution ranges

- `wilson_lo`: 16.1 .. 34.0% (全 48 cells で < 53% ゲート)
- `v2_wr`: 16.7 .. 34.7%
- `delta_ev`: -0.24 .. +0.54
- `truncated_ratio`: 0.50 .. 0.84 (全 cell で ≥ 50% の trade が早期 cut 対象)
- `base_ev`: -2.78 (定数 — baseline は X/Y/Z 非依存)
- `base_wr`: 39.9%

## 2. Binding criteria — なぜ SURVIVOR=0 か

Top cell (X=3, Y=2, Z=3) を binding gates に通す:

| Gate | 値 | 判定 |
|------|-----|------|
| ΔEV ≥ +0.5p | +0.54 | ✅ PASS |
| Welch p < 1.04e-3 | 0.0 | ✅ PASS |
| Fisher p < 1.04e-3 | 0.0 | ✅ PASS |
| WF 2-bucket 同符号 | True | ✅ PASS |
| V2 engaged N ≥ 80 | 11,723 | ✅ PASS |
| exit_dist 比率 20:80〜80:20 | 11723/0/2462 (mae_breach heavy) | ⚠️ 偏りあり(but not triggered) |
| **Wilson 95% lower > 53%** | **16.4%** | ❌ **FAIL** (36.6pp 不足) |

単一ゲートで SURVIVOR 否決。その他 5 件は **統計的に極めて強く PASS**。

## 3. 本質所見 — 「効いている、ただし WR ゲートで拾えない」

### 3.1 ΔEV は実在する
- 16 cells 全てで ΔEV > +0.5p、**Welch / Fisher が literally p=0** (N=14,185 の実力)
- WF 2-bucket 同符号 → 時期依存でない安定したゲイン
- **これは統計的偶然ではなく、real loss-magnitude reduction alpha**

### 3.2 だが WR は上がらない (mechanism の構造)
- baseline: WR=39.9%, EV=-2.78p
- V2 (X=3,Y=2,Z=3): WR=17.0%, EV=-2.24p → ΔEV=+0.54p
- 意味: cut-loss 機構は **"winners を TP まで持つか SL まで持つか" を変えない** ——
  **"SL まで待っていた大損トレードを、より早く小損で切る"** だけ
- 結果: V2_WR は baseline より**低くなる** (TP 途中で cut される winner が出るため),
  しかし V2 の平均損失**絶対値**が縮小 → 総合 EV 改善
- これは mean-reversion setup の性質とも整合: 早期に順行しない = setup rejected =
  SL まで持ってもほぼ確実に負け → 早切りで損失縮小

### 3.3 Wilson WR ゲートが構造的に不整合
- 53% ゲート (BEV + 3pp) は **"対称 R:R で WR を上げて勝つ"** 機構を想定
- 本 mechanism は **"WR は下げる / 損失を縮める"** 型
- 実際: **48 cells 全てで wilson_lo < 35%**, N を倍増しても 53% 到達は mathematical に不可能
- **→ pre-reg の binding criteria に mechanism 不整合の欠陥あり**

### 3.4 Closure 判定は下せない — §6.2 を遵守
- LOCKED criteria は data look 前に固定 → 遡及変更は HARKing
- §6.2 は "CANDIDATE ≥ 1, SURVIVOR = 0 → Extended Shadow for holdout"
- 本回避は不可能 — 規律どおり hold

**ただし、§6.2 が holdout 追加 N で SURVIVOR 到達を前提にしているが、本ケースでは
Wilson gate が構造的に到達不能なため、2026-05-14 再集計でも SURVIVOR=0 で確定する。**
これは `lesson-preregistration-gate-mechanism-mismatch` として別途記録し、
将来 pre-reg の gate 設計に反映する。

## 4. LOCKED action (per pre-reg §6.2)

### 4.1 今セッションで実施するもの
- [x] `raw/bt-results/mafe-dynamic-exit-2026-04-24/{summary,trades}.json` 保存
- [x] `result-stub.md` auto-generated
- [x] 本 analysis doc (`mafe-dynamic-exit-result-2026-04-24.md`) 執筆
- [x] lesson `lesson-preregistration-gate-mechanism-mismatch` 執筆 (独立の learning)
- [x] KB unresolved に 2026-05-14 再集計タスク追加
- [x] git commit + push

### 4.2 明示的に実施しないもの (violation guard)
- ❌ **code deploy**: §6.2 は Shadow 延長観察のみ、`modules/` の bb_rsi_reversion に
  `_dynamic_exit()` を**追加しない** (§6.1 限定の action)
- ❌ **binding gate の遡及変更**: Wilson WR gate が不整合と判明したが、本 pre-reg の
  criteria は LOCKED → 変更禁止 (§7 Anti-pattern Guard の "Bonferroni loosening" と
  同等の post-hoc 救済に相当)
- ❌ **secondary BT 実行 (ema_trend_scalp)**: §2 の "primary で NULL なら secondary は
  実行しない" ルールに従い中止 (family-level null と判断)
- ❌ **target swap**: sr_channel_reversal への流用 禁止 (§7)

### 4.3 2026-05-14 時点の予定アクション
- holdout 2026-05-07 以降の追加 N で同 48-cell BT を再実行
- SURVIVOR 到達なら §6.1 (code deploy の別 pre-reg) へ
- SURVIVOR 未達なら §6.3 Closure 確定 + bb_rsi_reversion FORCE_DEMOTED 維持
- **実際には Wilson gate の mathematical 到達不能性から §6.3 収束を予想**
  (本予想は action に影響させず、規律どおり holdout データで再検定)

## 5. 本 analysis の meta-audit

- ✅ XAU 除外 (CLAUDE.md + [[lesson-xau-friction-distortion]])
- ✅ Post-cutoff 2026-04-08 を BT window 上限 (holdout 保全)
- ✅ `base_ev` が 48 cells で定数 (-2.78) — baseline simulation 正確性の sanity
- ✅ `wf_sign_match` を確認 (時期依存でない)
- ✅ `v2_engaged_n` (早期 cut 発動数) を全 cell で確認 — baseline 数と分離
- ⚠️ `truncated_ratio` が最大 0.84 (83% 早期 cut) — live では OANDA order flow 遅延で
  cut タイミングズレる可能性、Shadow 実装時に measurement bias 注意

## 6. References

- [[pre-registration-mafe-dynamic-exit-2026-04-24]] — 本 BT の LOCKED 契約
- [[shadow-deep-mining-2026-04-24]] — Option C 経路の根拠
- [[cell-level-scan-2026-04-23]] — Phase 2 Scenario A (sr_channel / bb_rsi / ema null)
- [[lesson-preregistration-gate-mechanism-mismatch]] — 本 BT から学んだ gate 設計 lesson
- [[lesson-reactive-changes]] — 結果を見ての code 変更禁止プロトコル
- [[friction-analysis]] — per-pair RT friction model

---

**Author**: Claude (quant-analyst mode)
**Review status**: §6.2 適用、code deploy 未認可
**Next milestone**: 2026-05-14 holdout 再集計 (別セッション)
