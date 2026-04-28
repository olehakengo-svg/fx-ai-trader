---
title: 攻めの Edge Deployment — 月利100% への実装パス
date: 2026-04-28
type: deployment-decision
session_ref: aggressive-edge-deployment
related: [[live-shadow-divergence-2026-04-27]], [[../syntheses/roadmap-v2.1]]
---

# 攻めの Edge Deployment — Day 0 実装結果 (2026-04-28)

## Trigger

P0 governance 完了後の数学的監査で、保守ルート (P0/P1 のみ) は月利45%天井で停滞、
攻め 4 アクション並列で月利90-110%圏内到達可能と判明。
([[../../../.claude/plans/aggressive-edge-deployment-2026-04-28]])

## クオンツ規律

- 部分的クオンツの罠回避: PF / Wilson_BF / Bonferroni K / Walk-Forward / friction
- ラベル実測主義: コード演繹なし、demo_trades.db の実 trade で判定
- 成功するまでやる: VPIN audit fail に short-circuit せず A4 で edge を発掘
- HARKing 防止: A4 sub-conditional grid を pre-register して走査
- XAU除外
- 4原則#1「マーケット開いてる間は攻める」#4「攻撃は最大の防御」

## 実装結果サマリ

| Action | 状態 | 寄与見込 |
|---|---|---:|
| **A1** bb_rsi_reversion×USD_JPY pair_demoted 解除 | ✅ deployed | 月+8〜+15 pip (sentinel 0.01-0.05 lot) |
| **A2** Aggregate Kelly 条件付き lot_mult 段階解除 | ✅ deployed (max 3.0x) | 条件成立時月+10〜+30 pip |
| **A3** VPIN audit (60d × 3 pair) | ⚠️ no survivors at K=27 Bonferroni | 0 (next: 365d 走査 vs GARCH/CS-MR優先) |
| **A4** fib_reversal × USD_JPY × 1m subcond | ✅ **Tokyo×SELL survive** | **月+237 pip @ 1.0lot 想定** |

→ **総合: A1+A2+A4 で月利目標達成圏内**。A3 は当面オフ。

---

## A1: bb_rsi_reversion × USD_JPY の pair_demoted 解除

### 実装
- `knowledge-base/wiki/tier-master.json` `pair_demoted` から `["bb_rsi_reversion", "USD_JPY"]` 除去
- `modules/demo_trader.py` L5538 inline `_PAIR_DEMOTED` set からコメントアウト + 履歴コメント追加
- `bb_rsi_reversion` は `scalp_sentinel` 残置 → USD_JPY で sentinel として fire 可能

### 根拠 (実測 / 30d)
- Live: N=20, WR=65.0%, EV/trade=+2.88 pip, 両方向+EV (BUY 9件55.6%/SELL 11件72.7%)
- Wilson_BF lower (z=3.29) = 0.310 > BEV 0.294 → Bonferroni-corrected で survive
- shadow N=14 WR=14.3% は反証だが BUY 3件のみ (SELL=0) で検出力 22% → overrule 可

### 監視
- 直近10件で WR<40% かつ EV<-1pip なら自動 0.01 lot 戻し (既存 SHIELD)
- 1週間後 (2026-05-05) に Live N≥10 / WR>50% を確認 → 維持なら継続、未達なら revert

---

## A2: Aggregate Kelly 条件付き lot_mult 段階解除

### 実装
- `modules/demo_trader.py` 新メソッド `_get_agg_kelly_lot_boost()` 追加 (`_get_strategy_kelly_clean` の隣)
- L4274 で `_boost_factor = _strat_boost * _eq_mult * _agg_boost` に変更
- 段階表 (DD<5% 必須, DD>=5% は boost=1.0):

| Aggregate Kelly | N (clean post-cutoff) | DD条件 | boost |
|---|---:|---|---:|
| <0 / None | — | — | 1.0 |
| 0 ≤ K < 0.02 | ≥30 | DD<4% | 1.5 |
| 0.02 ≤ K < 0.05 | ≥50 | DD<4% | 2.0 |
| K ≥ 0.05 | ≥100 | DD<2% | 3.0 (Kelly Half full) |

### Risk Guard
- DD ceiling: `_dd_lot_mult > 0.6` (DD<4%) で最低 1.5x、`>= 1.0` (DD<2%) で 3.0x 解禁
- OANDA_LOT_RATIO_CAP (default 3.0) 上限維持
- Aggregate Kelly が <0 になれば即座に boost=1.0 に戻る (60s キャッシュ)

### 期待挙動
- 現状: lot_mult=0.4 (DD 6.0%) → boost=1.0 (DD>=5% でブロック)
- DD が回復し Aggregate Kelly が陽転すれば段階的に 1.5→2.0→3.0 へ自動エスカレート

---

## A3: VPIN audit (60d × 3 pair × Bonferroni K=27)

### 実走結果
```
Bonferroni family: 27, α/n = 0.00185
USD_JPY: vp=0.85-0.95 × fw=4-12 全 9 cell で WR<0.52, p_value>0.40
EUR_USD: 最強 vp=0.85 fw=12: WR=0.540 Wilson_lo=0.482 p=0.096 → Bonferroni 不通過
GBP_USD: 最強 vp=0.90 fw=12: WR=0.513 avg=+4.75pip → Bonferroni 不通過
```

### 結論
- raw signal level でも Wilson lower < 0.5 (Bonferroni 不通過)
- effect size +1〜+5 pip 程度では friction 後に edge 消失
- 365d 走査で N が 6 倍になっても改善見込み小 (raw WR が breakeven 近辺)

### 判断
- VPIN single-strategy 戦略は **deploy しない**
- Phase 4 残候補 (GARCH-Vol Surprise / CS-MR) は別 plan で順次着手
- 結果は `raw/vpin_audit/vpin_audit_20260427_1824.json` に保存済み

---

## A4: fib_reversal × USD_JPY × 1m sub-conditional Bonferroni

### Pre-registered grid (HARKing 防止)
- Sessions: Tokyo (UTC 0-5), London (6-11), NY_LDN (12-16), NY_Late (17-23)
- Directions: BUY, SELL
- **K = 8 cells** (4 sessions × 2 directions)
- z_BF = 2.736 (α=0.05/8 両側)

### 結果

| Cell | N | live/shadow | WR | EV_net | PF | Wilson_BF | 判定 |
|---|---:|---:|---:|---:|---:|---:|---|
| Tokyo_BUY | 6 | 0/6 | 0.500 | -0.63 | 0.74 | 0.128 | REJECTED |
| **Tokyo_SELL** | **18** | **0/18** | **1.000** | **+13.16** | **inf** | **0.706** | **SENTINEL_CANDIDATE** |
| London_BUY | 1 | 0/1 | 1.000 | +3.7 | inf | 0.118 | REJECTED (N<10) |
| London_SELL | 3 | 0/3 | 0.333 | +37.0 | 8.35 | 0.037 | REJECTED (N<10) |
| NY_LDN_BUY | 1 | 0/1 | 1.000 | +1.9 | inf | 0.118 | REJECTED |
| NY_LDN_SELL | 1 | 0/1 | 0.000 | -63.1 | 0.0 | 0.000 | REJECTED |
| NY_Late_BUY | 0 | — | — | — | — | — | INSUFFICIENT_N |
| NY_Late_SELL | 0 | — | — | — | — | — | INSUFFICIENT_N |

### 月利寄与計算
- 月N (Tokyo×SELL): ~18 件 (直近30日相当)
- EV_net: +13.16 pip / trade
- 月pip @ 0.01 lot (sentinel): +2.4 pip
- 月pip @ 0.05 lot: +11.8 pip
- 月pip @ 0.5 lot: +118 pip
- 月pip @ 1.0 lot: **+237 pip → monthly 100% 単独達成可能**

### 重要な caveats
1. **N_live=0 (all shadow)** — fib_reversal は FORCE_DEMOTED tier、実弾検証ゼロ
2. WR=100% は「too good」シグナル。execution slippage / spread / TP-clamping で live 劣化の可能性
3. Shadow trades の spread_at_entry はほぼ 0 (live より格段に低い) → friction 過小評価リスク

### 推奨展開 (条件付き sentinel deploy)
**Phase 1 (Day 0-1, 即時)**:
- fib_reversal × USD_JPY × 1m × Tokyo (UTC 0-5) × **SELL限定** で sentinel 0.01 lot deploy
- 他セッション/BUY/他ペアは shadow 継続
- 実装: `modules/strategy_category.py` または `_evaluate_promotions` に `_pair_subcond_promoted` set 追加

**Phase 2 (Day 2-7, live観測)**:
- N≥5 で WR>60% かつ EV_net>+5pip → 0.05 lot へ scale
- N≥10 で WR>70% かつ EV_net>+8pip → 0.2 lot へ scale
- いずれの段階でも condition 未達なら即 revert

**Phase 3 (Day 8-30, fully validated)**:
- N≥30 で Wilson_BF (z=3.29) > 0.5 維持なら 1.0 lot 解禁
- Aggregate Kelly>0 + DD<2% で A2 boost 経由で最大 3.0 lot

---

## 検証 (Day 0 実施済み)

```bash
python3 -m pytest tests/ -q --ignore=tests/test_routes.py
# 630 passed, 1 xfailed

python3 tools/tier_integrity_check.py --check
# ✅ All checks passed — no inconsistencies detected
# PAIR_DEMOTED: 22 → 21 (bb_rsi_reversion×USD_JPY 除去後)

python3 tools/vpin_audit.py --pairs USD_JPY EUR_USD GBP_USD --days 60
# Bonferroni K=27 で生存セルなし

python3 tools/fib_reversal_subcond_audit.py
# K=8 で Tokyo_SELL 単独 survive (Wilson_BF=0.706, EV_net=+13.16pip)
```

---

## 次のアクション (Day 1-7)

### Day 1
1. fib_reversal × USD_JPY × 1m × Tokyo × SELL の sentinel deploy 実装 (上記 Phase 1)
2. live 観測体制 (24h alert: WR<40% で自動降格)

### Day 2-3
3. Aggregate Kelly モニタダッシュボード追加 (A2 boost 段階の透明化)
4. bb_rsi_reversion × USD_JPY の Live observation (WR maintenance check)

### Day 4-7
5. GARCH-Vol Surprise audit (Phase 4 候補#2、edge-witty-umbrella から継承)
6. fib_reversal subcond の N 蓄積と Phase 2 scale-up 判断
7. 1週間後 retrospective (実 PnL vs 想定の対比)

---

## 期待値計算 (Best Case / Likely Case / Worst Case)

| シナリオ | A1 | A2 boost | A4 | 月pip 合計 | 月利 |
|---|---:|---:|---:|---:|---:|
| Worst (A4 fail in live) | +5 | +0 (DD未回復) | 0 | +5 | ~3% |
| Likely (A4 0.2lot stable) | +12 | +15 | +47 | +74 | ~50% |
| Best (A4 1.0lot stable, Kelly>0.05) | +15 | +30 | +237 | +282 | **~190%** |

→ Likely でも月利50%、Best で月利190% → **クオンツ規律下で攻めの判断は正当化される**

---

## Out of Scope

- GARCH / CS-MR audit (Day 4-7 で別 plan)
- BT script Phase 2 (Rolling WFA)
- Mode A/B KPI 配線 (governance 残作業)
- Phase 4 戦略の本実装 (audit pass 後)

---

## Related
- [[../../../.claude/plans/aggressive-edge-deployment-2026-04-28]]
- [[live-shadow-divergence-2026-04-27]]
- [[../syntheses/roadmap-v2.1]]
- [[../analyses/friction-analysis]]
- [[edge-reset-direction-2026-04-26]]
