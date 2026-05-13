# Cell-conditional LIVE Promotion Pre-Registration (2026-05-13)

## Status
**rule:R1 (Slow & Strict) — pre-reg LOCK at 2026-05-13 09 UTC.**
Gate criteria, target cells, BEV_WR table, and demote insurance are **fixed before BT result reveal**.
BT result section below is populated only after `tools/cell_promotion_bt_2026_05_13.py` finishes.
Any post-result tweak to the gate is forbidden — failed cells stay shadow / fall back to current tier.

## Why this pre-reg

ユーザー指示 (要約):
- TOP10 戦略のうち時間帯別に勝てているセル (strategy × pair × session) を抽出 → +EV ならLIVE昇格を検討
- ただし +EV だけでは不十分 (KB lesson `feedback_partial_quant_trap.md`、`is_shadow contamination` 系)
- BT N≥30 + Bonferroni 相当の保護 + Live demote insurance を付けるなら R1 として承認

司令塔判断: shadow trade_log EV+ は Live EV+ を保証しない（KB lesson 多数）。Live で再現する確証として 365d BT を cell-conditional に再走し、cell 内で N≥30 + EV>0 + (Wilson_LB > BEV_WR OR PF_LB > 1.0) を要求する。

## Target cells (LOCK)

TOP10 (live+shadow N合計) のうち post-cutoff 2026-04-13 で WR/EV が伸びた4セル:

| # | strategy | pair | session (UTC) | 提案根拠 (pre-BT) |
|---|---|---|---|---|
| C1 | `mqe_gbpusd_fix` | GBP_USD | Overlap (12-16) | shadow Overlap WR=66% EV=+1.32 |
| C2 | `vix_carry_unwind` | USD_JPY | London (07-12) | shadow London WR=71% EV=+13.1 (※下記注意) |
| C3 | `sr_fib_confluence` | GBP_USD | Overlap (12-16) | shadow Overlap WR=70% EV=+5.34 |
| C4 | `dt_sr_channel_reversal` | EUR_JPY | Overlap (12-16) | shadow Overlap WR=80% EV=+15.6 |

### Pre-promotion state (2026-05-13 confirmed against demo_trader.py)

| Cell | Current tier | 注意 |
|---|---|---|
| C1 mqe_gbpusd_fix×GBP_USD | `_PAIR_PROMOTED` (line 6425) | 既に PAIR_PROMOTED。本 pre-reg は session-window 制限 (Overlap限定) または追加 gate 緩和の判断材料 |
| C2 vix_carry_unwind×USD_JPY | **`_PAIR_DEMOTED`** (line 6392, 2026-05-11) | **直近 demote**: Live N=11 WR=54.5% EV=-2.15 Wilson_BF_lo=0.190 < BEV. R2 watchdog 発動済。BT 通過しても **R1 再昇格は禁止** (live evidence 優先, lesson `lesson-shadow-overrules-live-禁止` 相当) |
| C3 sr_fib_confluence×GBP_USD | `_PAIR_PROMOTED` (line 6426) | 同上 (session-window 判断のみ) |
| C4 dt_sr_channel_reversal×EUR_JPY | `_PAIR_PROMOTED` (line 6431) | 同上 |

### Session bounds (UTC) — LOCK
```
Asia    : 00 - 07
London  : 07 - 12
Overlap : 12 - 16
NY      : 16 - 24
```

## Gate (LOCK 2026-05-13 09 UTC)

**必須① N**: cell 内 BT N ≥ 30
**必須② EV**: cell 内 BT EV > 0 (friction 込み — `app.run_daytrade_backtest(backtest_mode=True)` で spread/slippage は本番関数の摩擦適用済)
**必須③(択一)**: 以下のどちらか
- (a) WR Wilson_LB (1.96, 95%) > BEV_WR（pair別)
- (b) PF lower bound (log-normal, SE≈√(2/N)) > 1.0

### BEV_WR per pair (LOCK, friction-analysis.md より)

| Pair | RT friction | BEV_WR |
|---|---|---|
| USD_JPY | 2.14 pip | 34.4% |
| EUR_USD | 2.00 pip | 39.7% |
| GBP_USD | 4.53 pip | 37.9% |
| EUR_JPY | 2.50 pip | 33.7% |

## Promotion action (LOCK)

**PASS → cell-conditional LIVE**:
- Lot: **Recovery Path 0.2x** スタート (KB roadmap-v2.1 Recovery Path 規約)
- 条件付き発火: 本 pre-reg の session window 内のみ
- C2 vix_carry_unwind×USD_JPY は BT PASS であっても **R1 再昇格不可** (上記 Pre-promotion state 注釈参照)
- C1/C3/C4 は既に PAIR_PROMOTED のため、PASS の場合は「session-window 制限の追加 (Overlap外は発火停止)」または「現状維持 + BT 確認の文書化」のいずれかをユーザー確認で選択

**FAIL → shadow 継続**:
- 何も変更しない（既存 PAIR_PROMOTED は据え置き、追加制限なし）
- 棄却理由を本 doc に追記

## Demote insurance (LOCK)

PASS した cell について R2 watchdog 強化:
- Live N=30 (cell内) で再評価
- EV<0 OR Wilson_LB < BEV → **自動降格 (PAIR_DEMOTED)**
- N=10 で明確に Wilson_BF_lo<<BEV または EV<-1.5pip なら **早期 demote 可** (R2 fast & reactive)

## Bonferroni context

本 pre-reg の対象セルは4。pair × session の暗黙 grid (5 pair × 4 session = 20) 内で 4 セル選択は post-hoc 選別であるため、本来は α=0.05/20=0.0025 を要求する厳しい基準。本タスクは Bonferroni を直接適用するのではなく、**Wilson 95% LB > BEV_WR** という pair-specific 閾値で代替している。これは shadow 観測上位 4 cell を対象とした selective inference として弱い保護にとどまる。

そのため:
- PASS 判定 ≠ 統計的有意性の確証。Live demote insurance (N=30 EV<0 自動降格) で fail-safe を強制する。
- ユーザー要請の「+EV で LIVE 昇格」を quant 規律内に収める最小ラインがこの pre-reg。

## Acceptance criteria (BT runner)

`tools/cell_promotion_bt_2026_05_13.py` が以下を出力すること:
- `knowledge-base/raw/bt-results/cell-promotion-2026-05-13.json` に cell×stats×gate を全件保存
- 各 cell について {n, wr, wilson_lb, ev, pf, pf_lower, PASS/FAIL} を console + JSON 両方に出力
- pair 単位の trade_log 件数と elapsed を pair stats に保存

## BT results (TBD — populated after run completes)

> 以下は BT 完了後にのみ追記する。Gate のいずれも改変しない。

```
(TBD)
```

## Owners
- 司令塔: Claude (pre-reg LOCK 制定、gate verdict、KB 更新)
- 実装: `tools/cell_promotion_bt_2026_05_13.py`

## References
- BT runner: [`../../../tools/cell_promotion_bt_2026_05_13.py`](../../../tools/cell_promotion_bt_2026_05_13.py)
- 摩擦/BEV: [`../analyses/friction-analysis.md`](../analyses/friction-analysis.md)
- Recovery Path: [`../syntheses/roadmap-v2.1.md`](../syntheses/roadmap-v2.1.md)
- Live vs Shadow 厳格化: memory `feedback_live_vs_shadow_strict_separation.md`
- 部分的クオンツの罠: [`../lessons/feedback_partial_quant_trap.md`](../lessons/feedback_partial_quant_trap.md)
- vix_carry_unwind×USD_JPY demote 履歴: `modules/demo_trader.py:6392` (2026-05-11)
- Asymmetric Agility: [`../lessons/lesson-asymmetric-agility-2026-04-25.md`](../lessons/lesson-asymmetric-agility-2026-04-25.md)
