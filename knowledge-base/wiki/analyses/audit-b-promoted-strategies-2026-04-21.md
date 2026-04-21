# Audit B: 既存 PAIR_PROMOTED 戦略の quant 再審査

**実施日**: 2026-04-21
**目的**: 2026-04-21 に設定した quant 基準 (PF>1.1, Wilson CI 下限>BEV, WF 3/3 正) を既存 PAIR_PROMOTED 戦略に後ろ向き適用し、過剰昇格 (over-promotion) を検出する.

---

## 1. 監査対象

N<30 で promoted された 3 entry (CLAUDE.md の「365日BT or Live N≥30 → GO」を満たさない):

| Strategy × Pair | promotion時 BT | promotion時 N |
|---|---|---|
| doji_breakout × USD_JPY | EV=+0.339 WR=61.9% | 21 |
| dt_fib_reversal × GBP_USD | EV=+0.310 WR=72.7% | 22 |
| squeeze_release_momentum × EUR_USD | EV=+0.460 WR=66.7% | 15 |

---

## 2. 監査手順

1. 365d 15m DT BT を実行 (2026-04-21 データ時点)
2. N, WR, EV, PF を再計測
3. Wilson 95% CI を計算、BEV_WR と比較
4. LIVE データ (`/api/demo/trades`) と照合
5. 判断: 維持 / demote / 保留 (N不足)

BT 深部分析スクリプト: `/tmp/audit_promoted_bt.py` (pre-registration §3 と同等の rigor)

---

## 3. 結果

### 3.1 dt_fib_reversal × GBP_USD — **DEMOTE 実施**

| 時点 | N | WR | EV | PF | 判定 |
|---|---|---|---|---|---|
| promotion時 | 22 | 72.7% | +0.310 | 1.63 | ✓ |
| **2026-04-21** | **30** | **53.3%** | **-0.224** | **<1.0** | ✗ 劣化 |

- Wilson 95% CI [35.5%, 70.4%] → 下限 35.5% < GBP_USD BEV 37.9% — **edge 非有意**
- LIVE: GBP_USD N=0 (未発火) — 安全弁として撤回可能
- **Action**: `_PAIR_PROMOTED` から `("dt_fib_reversal", "GBP_USD")` 削除 → UNIVERSAL_SENTINEL 復帰

### 3.2 doji_breakout × USD_JPY — **保留 (insufficient)**

| 時点 | N | WR | EV | 判定 |
|---|---|---|---|---|
| promotion時 | 21 | 61.9% | +0.339 | ✓ |
| 2026-04-21 | **7** | 57.1% | +0.435 | **N 不足** |

- 365d BT で N=7 — 年間発火率が極低. BT フィルタ変化で trades が減少.
- LIVE: USD_JPY N=1 EV=+12.40 (単一観測、判断不可)
- CLAUDE.md gate N≥30 に未達. 既存 positive signal は弱い.
- **Action**: 現状維持 (PAIR_PROMOTED 継続). watch list 登録. Live N≥15 到達時に再審査.

### 3.3 squeeze_release_momentum × EUR_USD — **保留 (insufficient)**

| 時点 | N | WR | EV | 判定 |
|---|---|---|---|---|
| promotion時 | 15 | 66.7% | +0.460 | ✓ |
| 2026-04-21 | **10** | 70.0% | +0.411 | **N 不足** |

- 365d BT で N=10 — 低頻度. EV/WR 維持は positive signal.
- LIVE: EUR_USD N=0 (未発火). GBP_USD (非 promoted) で live N=2 EV=-5.6, shadow EV=-6.17 (EUR_USD 相関 注意)
- **Action**: 現状維持. watch list 登録.

---

## 4. Multiple Testing Correction

今回の audit で 3 戦略を一括検定.
- Family-wise error rate control: Bonferroni α/3 = 0.0167 (z=2.39)
- dt_fib_reversal × GBP_USD: Bonferroni 98.3% CI [33.8%, 72.0%] → 下限 < BEV 37.9% → **non-significant** 確定
- doji_breakout / squeeze_release: N 不足のため Bonferroni 計算意味なし

---

## 5. 今後のプロトコル

本 Audit で確認された課題:

1. **小-N promotion の再発防止**: CLAUDE.md gate (N≥30) を PAIR_PROMOTED 新規追加時の pre-commit 検証項目に昇格させる
2. **定期監査**: PAIR_PROMOTED の 365d BT を月次で自動再計測 (次回 2026-05-21)
3. **LIVE 未発火の検出**: promotion 後 30日で LIVE N=0 なら watch list に自動追加

## 6. 次 audit 候補 (次セッション)

監査未実施だが要確認:
- vwap_mean_reversion × {EUR_JPY, GBP_JPY, EUR_USD, GBP_USD} — 4 entries (同等 rigor 適用必要)
- xs_momentum × {EUR_USD, GBP_USD} — 180d BT のみ、365d 未検証
- vix_carry_unwind × USD_JPY — N=49 境界
- wick_imbalance_reversion × GBP_USD — N=40 境界
- post_news_vol × {GBP_USD, EUR_USD} — BT positive と称されるが未検証

---

## 7. 本 Audit のコミット
- `TBD` — feat(tier): dt_fib_reversal×GBP_USD PAIR_PROMOTED 撤回
- `TBD` — docs(quant): audit-b-promoted-strategies-2026-04-21 (this doc)

関連:
- [[pre-registration-2026-04-21]] — 新規 promotion の pre-reg
- [[negative-strategy-stop-conditions-2026-04-21]] — negative 側の対称文書
- [[2026-04-21-session]] — セッションログ
