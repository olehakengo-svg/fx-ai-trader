# Pre-reg: donchian_momentum_breakout × NZD pair 1.0x intentional exception (2026-05-27)

**Rule classification**: R1-EXCEPTION (intentional, vix_carry 1.0x / Kalman D7 0.5x 型 precedent)
**Author**: goto (user judgment) + Claude (audit + implementation)
**Effective**: 2026-05-27 (commit pending)
**Supersedes**: 2026-05-01 P0-8 phase 1 FORCE_DEMOTED 全 pair stop (Live N=3 PnL=-32.1p で全 pair Live 停止)

---

## Decision

`donchian_momentum_breakout` を `_FORCE_DEMOTED` から外し、**NZD_JPY / NZD_USD のみ** `_PAIR_PROMOTED` + `_PAIR_LOT_BOOST=1.0` (full size) で **LIVE 復活**。
他 6 pair (AUD_JPY / USD_CAD / EUR_USD / USD_JPY / AUD_USD / EUR_AUD) は `_PAIR_DEMOTED` で個別遮断（Shadow 蓄積は継続）。

## Empirical evidence (Shadow since 2026-04-01, dedup-clean sentinel API)

| Pair | N | WR | EV | Total PnL | Wilson_lo 95% | BF_lo (m=8) | Verdict |
|---|---:|---:|---:|---:|---:|---:|:---|
| **NZD_JPY** | 14 | 71.4% | +20.49p | +287p | 0.453 | 0.388 | 🟢 PROMOTE 対象 |
| **NZD_USD** | 16 | 68.8% | +15.52p | +248p | 0.445 | 0.384 | 🟢 PROMOTE 対象 |
| EUR_AUD | 9 | 44.4% | +6.77p | +61p | 0.188 | 0.148 | 🟡 弱プラス、N<10 で安全側遮断 |
| USD_JPY | 3 | 0% | -6.00p | -18p | 0 | 0 | 🔴 N不足、安全側遮断 |
| AUD_USD | 3 | 0% | -7.80p | -23p | 0 | 0 | 🔴 N不足、安全側遮断 |
| USD_CAD | 11 | 27.3% | -9.05p | -100p | 0.098 | 0.075 | 🔴 R2 demote |
| AUD_JPY | 10 | 10.0% | -12.18p | -122p | 0.018 | 0.012 | 🔴 R2 demote |
| EUR_USD | 8 | 0% | -13.10p | -105p | 0 | 0 | 🔴 N=8 + WR=0 + EV<-3 三条件 |
| **Overall** | **74** | **39.2%** | **+3.09p** | **+229p** | — | — | polarized: NZD系がエッジ源 |

## Rule 1 violation 認識

CLAUDE.md Rule 1 (pair promote + lot↑) は以下を要求するが、本変更時点で **3 項目すべて未充足**:

| Rule 1 要件 | 現状 (2026-05-27) | Gap |
|---|---|---|
| Live N ≥ 30 | Live N=0 (FORCE_DEMOTED で全 pair 停止中) | -30 trades, Shadow N=14/16 |
| Bonferroni 有意 (BF_lo ≥ 0.40 相当) | BF_lo=0.388 (NZD_JPY), 0.384 (NZD_USD) | -0.012 / -0.016 |
| Pre-reg LOCK (pair promote + lot 1.0x) | 本 doc で新規作成 | この doc で充足 |
| 365 日 BT | 未実施 | C-1 タスクとして別途投入 |

これは [vix_carry 1.0x 2026-05-21](./vix-1x-intentional-exception-2026-05-21.md) / [Kalman D7 LIVE 2026-05-20](../../../../.claude/projects/-Users-jg-n-012-test/memory/project_kalman_d7_regime_bound_live_2026_05_20.md) と同じ **discretionary edge / user judgment 例外** に該当。

## 動機 (データ駆動 vs 感情 の自己宣言)

**主にデータ駆動**:

- ✅ **Pair-level polarized edge** が cell-decomposition で明確
  - Overall N=74 EV=+3.09p は弱プラスだが、pair 別では **NZD系平均 +18p × 30件** vs **その他 6 pair 平均 -10p × 44件**
  - 「全 pair で弱平均」ではなく「NZD系で強プラス、その他で強マイナス」の二極化
- ✅ **方向性ある不一致 (direction of evidence)**: 2 つの独立した NZD pair で同方向の強プラス
- ✅ **FORCE_DEMOTED の元根拠が古い**: 2026-05-01 時点の Live N=3 (WR=33.3%) は決定するには明確に少なく、その後 Shadow N=74 で異なる景色が見えた → CLAUDE.md 規律「新データが KB と矛盾なら KB 更新を提案する」

**Shadow-first quant の意図的例外**:

- N=14/16 (BFlo<0.50) で 1.0x は CLAUDE.md Rule 1 の statistical rigor に反するが、CLAUDE.md 4原則 #1「マーケット開いてる間は攻める — トレード機会を逃すのが最大の敵」を優先
- 機会損失試算: NZD系 EV +18p × 月 ~30 件 × 1 pip ¥10 (10k unit) ≈ **¥5,400/月** の機会損失 (現状 Shadow only)

**感情要素 (透明性)**:

- Donchian は 2 ヶ月間 Live ゼロで「動いていないのが見ていられない」要素はある（user 観察）
- Shadow → Live degradation 前例 (vol_surge / streak_reversal) のリスクは認識

## 撤退条件 pre-reg (binding)

以下のいずれかに該当した瞬間、LIVE 停止 (`_PAIR_PROMOTED` から外す or `_PAIR_LOT_BOOST` 縮小):

| 条件 | アクション |
|---|---|
| Live N=10 EV<-0.5p | `_FORCE_DEMOTED` に戻す (全 pair) |
| Live N=15 WR<50% | `_PAIR_LOT_BOOST=0.05` に縮小 |
| 14 日連敗 (Live 連続 WIN なし) | 即 demote |
| MaxDD > 5×ATR(NZD_JPY) | 即 demote |
| watchdog 自動 demote (`volume_live_promotion_watchdog.py`, Live N≥10 EV<0) | 自動執行 |

撤退判断時、本 doc に `## Withdrawal record` セクション追加 + memory 更新。

## 実装変更

`modules/demo_trader.py`:

1. **`_FORCE_DEMOTED`**: `"donchian_momentum_breakout"` をコメントアウト (経緯 inline 記載)
2. **`_PAIR_PROMOTED`**: NZD_JPY / NZD_USD 追加
3. **`_PAIR_DEMOTED`**: AUD_JPY / USD_CAD / EUR_USD / USD_JPY / AUD_USD / EUR_AUD 追加 (個別遮断)
4. **`_PAIR_LOT_BOOST`**: NZD_JPY / NZD_USD = 1.0 (full size)

## 並行アクション

C-1 (推奨): Codex に **365 日 BT** タスク投入 → BT side でも edge 確認、Bonferroni 通過なら本 LIVE の根拠強化。Live N=10 到達 (~5-10 日) までに BT 結果到着すれば、撤退/継続判断の補強材料になる。

## Memory references

- `project_vix_carry_1x_intentional_exception_2026_05_21` — 同 1.0x 例外の判例
- `project_kalman_d7_regime_bound_live_2026_05_20` — discretionary edge precedent
- `feedback_quant_first` — クオンツ判断の規律 (本件は明示的例外)
- `feedback_label_empirical_audit` — ラベル実測主義 (本件 cell-decomposition がこの実践)
- `feedback_live_shadow_separation` — Live/Shadow 分離、本件は Shadow → Live への migration

## 関連 commits

- 本 doc 作成 + 実装変更: 別コミット (本セッションで対応)
- 365 日 BT 結果: 別コミット (Codex 完了後)
