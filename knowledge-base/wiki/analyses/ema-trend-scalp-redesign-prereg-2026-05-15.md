# Pre-reg LOCK — ema_trend_scalp redesign v3 (2026-05-15)

**Purpose**: `lesson-cell-audit-bt-required-2026-04-27` の 3 段防御 step 1 (Pre-reg LOCK)。後付け cell tuning を防ぐため、Phase 1-3 audit ([[ema-trend-scalp-redesign-2026-05-14]]) で発見した gate spec を **hash 固定**。

**Status**: LOCKED — 以降の cell tuning は本 page の hash を更新せず別 page で行う。

## Gate spec (hash 固定対象)

```python
# entry_type == 'ema_trend_scalp' の Sentinel signal を Live OANDA 送信する条件
ETS_REDESIGN_V3_GATE = (
    mtf_alignment == 'aligned'
    and direction  == 'BUY'
    and instrument == 'GBP_USD'
)
```

**根拠**: Live shadow data (`demo_trades` table, status=CLOSED, outcome ∈ {WIN, LOSS}) で N=10, WR=50%, EV=+2.16 pips/trade, NetP=+21.6 pips. 同 cell 以外の N=65 trades は WR=20.0%, EV=−1.94, NetP=−126.0.

## Pre-reg parameters

| Field | Value |
|---|---|
| Strategy | `ema_trend_scalp` |
| Pair scope | `GBP_USD` only |
| Timeframe | `5m` |
| Direction filter | `BUY` only (SELL は構造的に死に cell) |
| MTF filter | `mtf_alignment='aligned'` (DB 列、`compute_mtf_alignment()` 出力) |
| Lot factor | **shadow only (lot=0)**、Recovery Path で段階引上げ |
| Promotion gate | Live N≥30 (post-LOCK), WR≥45%, Wilson_lo≥0.30, EV≥+1.5 pips, Bonferroni p<0.05 |

## Audit hash

```
Source: knowledge-base/wiki/analyses/ema-trend-scalp-redesign-2026-05-14.md
SHA256: (computed at LOCK time below)
```

```bash
$ shasum -a 256 knowledge-base/wiki/analyses/ema-trend-scalp-redesign-2026-05-14.md
# → hash recorded in commit message at v9.6-prereg-lock
```

## 検証 promotion sequence (Recovery Path)

1. **本 LOCK page commit** (本日中) — gate spec hash 固定
2. **Cell-conditional 180d Python BT** (`ETS_REDESIGN_V3=1` env flag) — 別 session で `strategies/scalp/ema_trend_scalp.py` に flag 経由で gate を実装、production path には touch しない
3. **180d BT 結果 WR≥70%** クリアなら → 4 へ進む (Python BT は Live より 30-40pp optimistic と判明。WR=70% が Live=40% に対応)
4. **Sentinel shadow accumulation** with gate — Live shadow N=30 まで累積 (現 10 → 残 20、目安 6-10 週)
5. **N≥30 時点で再 audit** — WR≥45% かつ Wilson_lo≥0.30 かつ EV≥+1.5 pips ならば
6. **Recovery Path lot 引上げ** — shadow strict → 0.25x → 0.5x → 1.0x。各段階で +30 trades clean をクリア
7. **3 軸独立確認** — TV Strategy Tester / 180d Python BT / Live shadow の 3 軸で +EV 一致 → OANDA 転送開始

## What this LOCK forbids

- 本 cell 以外で「あとから cell tuning して +EV cell を発見」した変種を **本 redesign の延長として** promote すること
- 別 redesign を試す場合は別 Pre-reg page を作って別 hash で固定する
- N=10 を理由に「P 値を緩めて」promotion gate をクリアする操作

## Bonferroni 計算

試行軸 (本 audit で評価した cell の数):
- mtf_alignment × direction × pair = 4 × 2 × 3 = **24 cells**
- うち N≥5 で評価したのは 7 cells (mtf_alignment 別 × direction 別、aligned×BUY が唯一の prima facie +EV)
- m = 7 (effective tests)
- corrected α = 0.05 / 7 = **0.00714**
- Wilson 95% CI for WR=50% N=10 → [0.237, 0.763] — lower bound 0.237 < 0.379 (BEV_WR) → **本 N では Bonferroni 補正後の有意性は確保できない**

→ N=30 段階での再 audit で:
- WR=50% N=30 → Wilson [0.323, 0.677], lower bound 0.323 < 0.379 (まだ marginal)
- WR=50% N=50 → Wilson [0.363, 0.637], lower bound 0.363 → ほぼ BEV_WR=0.379 と並ぶ
- → **promotion 判断には N≥50 が安全寄り** (Bonferroni 厳密)

## 関連

- [[ema-trend-scalp-redesign-2026-05-14]] — 本 LOCK の audit 元
- [[lesson-cell-audit-bt-required-2026-04-27]] — 3 段防御の原典
- [[ema-trend-scalp]] — 戦略カード (LOCK 確認後に Recovery Path 進捗を反映)
- approved plan: `/Users/jg-n-012/.claude/plans/prancy-waddling-ullman.md` — 本セッションの全体計画
