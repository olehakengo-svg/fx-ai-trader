# Pre-Registration: bb_rsi_reversion RR 1.5 救済 BT 365日検定 (2026-04-25)

> ⚠️ **撤回 (2026-04-25 同日)** — 本 pre-reg は [[lesson-asymmetric-agility-2026-04-25]] Rule 3 (Immediate, 算数破綻修正) により**撤回**.
> 365日 BT を待たず本番コードに RR=2.5 (Tier2) / RR=3.0 (Tier1) 即時適用済.
> 詳細: [[bb-rsi-fix-rr-2.5-2026-04-25]]
> 本ドキュメントは規律改定の証跡として参考保管 (削除しない).

## 1. 背景と動機

TP-hit deep-mining ([[tp-hit-deep-mining-grail-2026-04-25]]) で
`bb_rsi_reversion × USD_JPY × RANGE` の構造病理が確定:

- N=217 closed (Tokyo+London+NY 統合)
- TP-rate 32.3% (Wilson_lo 26.4%)
- EV **-0.58p** / trade, PF **0.75**
- AvgWin **+4.24p** / AvgLoss **-3.94p** (W:L 1.08)
- TP距離 4.92p / SL距離 4.27p → **RR=1.17**
- **Break-even WR 必要値 = 48.1%** ← 実測 32.3% で構造的 EV負

平均回帰仮説自体は機能 (32% > random 25%) だが、RR 1.17 設定が WR を救えない.

緊急トリップ ([[tp-hit-deep-mining-grail-2026-04-25]] Patch A) で OANDA 送信停止済.
本 BT は救済可能性検定. **データ覗き禁止 — pre-reg LOCK 済**.

## 2. 仮説 (Pre-Registered)

### H0 (帰無): RR 拡張は EV 改善に寄与しない
RR 1.5/2.0/2.5 のいずれも 365 日 BT で EV ≤ 0.

### H1 (代替): RR 1.5 で EV+ になる構造的閾値が存在する
- 既存設定 (RR 1.17) → EV -0.58p
- RR 1.5 で TP 撤退率は同程度 (TIME_DECAY_EXIT 16.6%) でも、
  AvgWin が +4.24p × 1.5/1.17 ≈ +5.43p に拡大すれば
  WR 32% × +5.43p − WR 68% × -3.94p = +1.74 - 2.68 = **-0.94p**
- ただし TP 撤退率上昇分 (∆) を加味: ∆ ≤ 6.6% なら EV+ 維持
- つまり **TP 距離拡張による撤退率増加が +6.6 pt 以下** なら救済成立

### H1 詳細閾値

| RR | 期待 AvgWin | 必要 WR (BE) | 観測 WR 必要差分 |
|---|---|---|---|
| 1.17 (現状) | +4.24p | 48.1% | +15.8 pt 不足 |
| 1.50 | +5.43p | 42.1% | +9.8 pt 不足 |
| 1.75 | +6.34p | 38.3% | +6.0 pt 不足 |
| 2.00 | +7.25p | 35.2% | +2.9 pt 不足 |
| **2.50** | **+9.06p** | **30.3%** | **-2.0 pt (救済可能)** |

→ **RR 2.5 が break-even, RR 1.5 では不足** が事前期待.
ただし TP 距離拡張で TP 約定率が下がる (撤退率増加) ため、要 BT 実測.

## 3. データセット

- ペア: USD_JPY のみ (他ペアは別 pre-reg)
- 期間: 365 日 (2025-04-26 〜 2026-04-25)
- 戦略: `bb_rsi_reversion`
- Regime フィルタ: local regime=RANGE のみ
- 摩擦モデル: v2 (spread, slippage, wick noise)

## 4. 検定軸 (4 cells)

| Cell | TP 距離倍率 | SL 維持 | 期待 RR |
|---|---|---|---|
| A0 (baseline) | 1.0× (現行) | 4.27p | 1.17 |
| A1 | 1.30× | 4.27p | 1.50 |
| A2 | 1.50× | 4.27p | 1.75 |
| A3 | 1.70× | 4.27p | 2.00 |
| A4 | 2.13× | 4.27p | 2.50 |

## 5. SURVIVOR Gate (Pre-Registered, Bonferroni 補正済)

- α = 0.05 / 5 = 0.01 (Bonferroni for 5 cells)
- Cell 通過条件 (AND):
  1. EV > +1.0p (摩擦 + slippage マージン)
  2. PF > 1.30
  3. Wilson_lo (WR) > BE 必要値 (cell 別)
  4. WF 同符号 (90 日 × 4 期間 ぜんぶ EV > 0)
  5. p < 0.01 (Welch t-test vs A0 baseline)

## 6. CANDIDATE / REJECT 判定

- **SURVIVOR**: 上記 5 条件全通過 → Live deploy 候補 (別 deploy pre-reg 起案)
- **CANDIDATE**: 1〜2 条件未達 → Holdout (2026-05-25) で再判定
- **REJECT**: 3 条件以上未達 → bb_rsi_reversion × USD_JPY × RANGE は構造的に救済不能と確定

## 7. 副次仮説 (Secondary, Bonferroni対象外)

H2: **エントリー時 RSI 極値深さ** で TP-rate 救済.
- RSI < 25 (BUY) / RSI > 75 (SELL) サブクラスタで WR > 48.1% か
- N≥30 を要件、Bonferroni α=0.01

## 8. 実装注記

- BT harness: `scripts/bb_rsi_rr15_rescue_bt.py` (新規)
- Pipeline: `app.py` の既存 `_bt_bb_rsi_*` 系を流用、`_TP_DIST_MULT` env で倍率指定
- Output: `raw/bt-results/bb-rsi-rr15-rescue-{date}.json`

## 9. 凍結ルール

- 本 pre-reg LOCK 後、**コード変更禁止**まで BT 完走.
- BT 結果が出るまで bb_rsi_reversion の OANDA trip は維持 (`BB_RSI_OANDA_TRIP=1`).
- SURVIVOR 判定 → 別 pre-reg "deploy plan" を起案して trip 解除.
- REJECT 判定 → bb_rsi_reversion × USD_JPY を `_FORCE_DEMOTED` に追加 (Shadow 継続のみ).

## 10. タイムライン

| 日付 | アクション |
|---|---|
| 2026-04-25 | 本 pre-reg LOCK + BT harness 実装 |
| 2026-04-26〜2026-04-28 | 365日 BT 実行 |
| 2026-04-29 | 結果分析 + SURVIVOR/CANDIDATE/REJECT 判定 |
| 2026-05-07 | Phase 1 holdout 期限と並走 |

## 11. メモリ整合性チェック

- [部分的クオンツの罠]: PF/Wilson_lo/RR/Break-even WR/W:L 全て本 pre-reg に含む ✅
- [ラベル実測主義]: TP-rate/EV はコード演繹ではなく 365日 BT 実測で判定 ✅
- [成功するまでやる]: REJECT 判定の場合、別セッションで RSI 深さサブクラスタ深掘り ✅
- [XAU除外]: USD_JPY 専用 ✅

## 参照
- [[tp-hit-deep-mining-grail-2026-04-25]] (本 pre-reg の根拠データ)
- [[bb-rsi-reversion]] (戦略 KB)
- [[lesson-preregistration-gate-mechanism-mismatch]] (gate 機構整合性 sanity)
