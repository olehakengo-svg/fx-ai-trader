# Edge Factor Audit 2026-06-12 — #6 session_time_bias (シリーズ最終)

Edge 別 N 降順要因解析シリーズ第 6 弾（最終）。母集団は本番 re-fetch 2026-06-18 clean。

## Verdict: 🟢 retire せず — 既存管理を検証、EUR_USD London 劣化を watch (user 決裁: 現状維持)

#1-#5 と異なり **dormant な死戦略ではなく活発に管理中**。因子分解は既存設計
(LIVE を {London} に絞り込み + LDN朝 SIZE lever 0.5x) を**正当化**した。コード変更なし。

## 対象 N

| population | N | WR | net EV | PF | gross EV |
|---|---|---|---|---|---|
| clean 全体 | 417 | 32.6% | −2.13 | 0.55 | +0.20 |
| LIVE (E8 で 06-04 停止) | 30 | 40.0% | −2.26 | 0.40 | −0.09 |
| SHADOW | 387 | 32.0% | −2.09 | 0.58 | +0.25 |

15m / median SL 7.6p / TP 16.6p / friction 2.33p = TP の 14% (survival line 内)。
SL_HIT 65.9%、敗者 MAFE favorable 中央値 0.1p。

## 要因分解 — 敗因は「非 London セッション」(全て shadow-only)

| session | N (shadow) | gross EV | Wilson_lo | 評価 |
|---|---|---|---|---|
| **London** | 146 | **+1.55** | 0.347 | LIVE が絞り込む場所 = 設計正 |
| Overlap | 108 | +0.73 | 0.260 | 弱 |
| Asia | 98 | **−1.63** | 0.136 | 出血源 (shadow-only) |
| NY | 24 | **−2.96** | 0.043 | 出血源 (shadow-only) |

pair×dir: GBP_USD SELL (shadow N=212, net −2.94, friction 2.80) が最大出血、
EUR_USD SELL (N=175, gross +0.72) は相対良。**aggregate net 負けは Asia/NY/GBP_USD-SELL
= 非 London・全て shadow-only が駆動**。LIVE が {London} に絞られているのは正しい設計で、
#1-#5 のような全面崩壊ではない。

## 🟠 watch item: 昇格セル EUR_USD London の劣化

| EUR_USD London | N | net | gross | Wilson |
|---|---|---|---|---|
| 昇格根拠 (2026-05-29) | 58 | +1.44 | — | 0.327 |
| 現 ALL | 102 | −0.87 | +0.80 | 0.330 |
| **現 last30d** | 79 | **−1.75** | **−0.02** | 0.304 |
| LIVE | 19 | −1.43 | +0.50 | 0.231 |

#5 sr_fib GBP_USD と同型の「昇格根拠劣化」だが、相違点:
1. LIVE は既に E8 emergency disable で 2026-06-04 以降停止中 (実弾リスク現状なし)
2. LDN朝 SIZE lever 0.5x が劣化対策として既に投入済 (task done、live 未検証)
3. 明示 demote trigger (Cell-Live N≥10 ∧ EV<0 or Wilson<34.4%) が実装済 → 自動発動を待つ

**user 決裁 (2026-06-18): 現状維持・トリガー監視**。独断の demote はせず、既存の
自動 demote trigger に委ねる。LDN朝 lever の live 再開時に EUR_USD London を再評価。

## 実装
コード変更なし (report-only)。

---

# Edge Factor Audit シリーズ 総括 (#1-#6 完了)

Fable 5 起動を機に「現エッジがなぜ勝てないか」を N 降順で 6 戦略監査。
本番 clean データ (XAU + dedup_violation 除外) ベース。

| # | edge | N | verdict | 敗因 |
|---|---|---|---|---|
| 1 | ema_trend_scalp | 1,117 | 🔴 KILL | シグナル=ノイズ + friction (SL の 44%) |
| 2 | bb_rsi_reversion | 780 | 🟠 統合退役→dt_bb_rsi_mr | friction (TP の 24.7%)、思想は DT 版が継承 |
| 3 | fib_reversal | 638 | 🔴 KILL | friction (TP の 29.2%)、統合先なし |
| 4 | sr_channel_reversal | 584 | 🔴 KILL | friction (TP の 23.7%)、統合先なし |
| 5 | sr_fib_confluence | 453 | 🔴 KILL + LIVE demote | JPY 96% + SELL 逆 + 昇格根拠反転 |
| 6 | session_time_bias | 417 | 🟢 現状維持 | 非 London が shadow-only 出血、LIVE は設計正 |

## 横断発見 1: friction ≤ TP の 10% が scalp 生存線
全滅 scalp (#1/#3/#4) は friction = TP の **23-44%**。生存 dt_bb_rsi_mr は 10.8%。
**新 scalp 戦略は設計時に「friction ≤ TP の 10%」を必須条件にすべき**。
反例補強: dt_sr_channel_reversal は gross +2.25 でも friction 22%/TP で net 負け。

## 横断発見 2: 「正式退役の不在」が出血を延命させる
#1-#5 全てで per-cell registry が一部ペアのみ列挙 → 新 mode/pair (特に HourlyEngine
slot) から漏れ続けた。`SHADOW_RETIRED_STRATEGIES` (戦略単位・全ペア・将来閉) が正解。
LIVE 側は別途 `_PAIR_PROMOTED` 削除が必要 (#5 で実証: SHADOW_RETIRED だけでは
`_is_live_tier_exempt` で短絡される)。

## 横断発見 3: 昇格根拠は N 増加で反転する (small-sample 罠)
sr_fib GBP_USD (N=39 +1.35 → N=132 −1.66)、STB EUR_USD London (N=58 +1.44 →
N=102 −0.87)。**PAIR_PROMOTED は定期的に N 増加後の再検証が必須**。
[[feedback-cohort-time-check]] / [[feedback-partial-quant-trap]] と整合。

## 残存 follow-up 仮説 (シリーズ完了後に別途 pre-reg 検証)
1. **dt_sr_channel_reversal pair-restriction** (#4): gross +2.25 を tight-spread pair 限定で表出
2. **fib-confluence BUY-major-only** (#5): EUR_USD/GBP_USD BUY が gross +1.85、15m で friction 8.7%
3. **dt_bb_rsi_mr promotion** (#2): Shadow clean N≥165 ∧ Wilson_lo≥0.40 で審査 (pre-reg LOCK 済)

いずれも現状は非有意 or net 負け = 昇格不可。新規 pre-reg として規律的に再挑戦する場合のみ。
