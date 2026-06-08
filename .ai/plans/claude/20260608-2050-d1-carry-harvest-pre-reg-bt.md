---
id: 20260608-2050-d1-carry-harvest-pre-reg-bt
priority: P2
gate: R1
rule: R1
status: queued
created: 2026-06-08
owner: claude
---

# D1 Carry 収穫バスケット — pre-reg BT (risk-premia)

**Rule classification**: R1 (Slow & Strict — 新規 risk-premia 戦略の pre-reg BT)
**Purpose**: `vix_carry_unwind` は VIX スパイク逆張りの intentional-exception 戦略 ([[project_vix_carry_1x_intentional_exception_2026_05_21]]) であり、**本来の carry risk-premium (金利差収穫) ではない**。本タスクで「金利差の対価を持ち切りで受け取る」正統な carry harvest を D1 で新規 pre-reg する。TSMOM ([[20260608-2040-d1-tsmom-basket-pre-reg-bt]] と同系統、risk-premia 2本目)。

## なぜこれか (司令塔の判断)

- Carry は数十年の文献を持つ documented risk-premium。高金利通貨を持ち低金利通貨を売る対価 (テールリスク負担の報酬) で、グロスが構造的にプラス。
- D1 月次リバランスで friction 極小。予測не要 = shadow-first 文化の grid 全滅パターンを構造的に回避。
- vix_carry の命名が誤解を生んでいる (carry と名乗るが carry ではない)。正統 carry を別戦略として立てて切り分ける。

### 学術的根拠

- Lustig & Verdelhan (2007, AER) — carry trade の consumption-risk 説明
- Menkhoff, Sarno, Schmeling & Schrimpf (2012, JF) — "Carry Trades and Global FX Volatility"
- Koijen, Moskowitz, Pedersen & Vrugt (2018, JFE) — "Carry" (asset class 横断)

## Pre-registration (m=2、LOCK)

**Primary 仮説**: G10 を金利差でランキングし、上位を long / 下位を short する carry factor portfolio。vol-target サイズ、月次リバランス、持ち切り (反転 exit)。
**Secondary (報告のみ)**: 高低 2 bucket (top1 long / bottom1 short) の単純版。
- Bonferroni m=2、α=0.05。

### バスケット
TSMOM と同一 8 pair (`EUR_USD, USD_JPY, GBP_USD, AUD_USD, USD_CAD, USD_CHF, NZD_USD, EUR_JPY`) を base currency 建てに揃えて金利差を算出。

## Required scope

### Phase 0: 金利差データソース決定 (blocker — 司令塔承認要)

carry シグナルには各通貨の金利が要る。MASSIVE に金利/フォワードがあるか不明。**実装前に以下の優先順で調査し、確定できなければ司令塔に差し戻す**:

1. **第一候補**: MASSIVE の forward/swap points endpoint (`mcp__Massive_Market_Data__search_endpoints` で "forward" / "swap" / "rate" を検索)。フォワードポイントは CIP より金利差を内包 → 最も理論整合。
2. **第二候補**: 中銀政策金利の月次テーブル (G10、手動メンテで可。月次リバランスなら更新頻度は十分)。`data/reference/policy_rates.csv` に置き、出典・更新日を明記。
3. **第三候補**: OANDA の rollover/swap 実績 (dexter 経由)。

**勝手に乱数や定数で代用しない**こと ([[feedback_codex_schema_hallucination]] の精神 — 不明データを推測で埋めない)。

### Phase 1: D1 データ
- `data/cache/massive/{PAIR}_1d.parquet` (TSMOM タスクの Phase 0 backfill を共有。未実施なら同様に backfill)。10年以上。

### Phase 2: BT
- carry portfolio equity curve、8軸 (Sharpe / ann.return / maxDD / Calmar / t-stat / 月次WR Wilson_lo / PF / Kelly)。
- Walk-Forward 3+ folds、各 fold Sharpe。
- Bonferroni m=2 α=0.05。

### Phase 3: 判定
- `knowledge-base/wiki/decisions/d1-carry-harvest-pre-reg-2026-06-08.md` に verdict (SHADOW_CANDIDATE / NULL)。
- 失格なら正直に NULL。本タスクでは投入しない。
- **TSMOM との相関も report** ([[project_tp_hit_12cell_portfolio_2026_06_05]] の相関分散思想): carry と momentum が低相関なら 2 factor 合成で分散効果 (AQR "Value and Momentum Everywhere")。

## Codex 注意

- 新規戦略本体 `strategies/daytrade/carry_harvest.py`、BT は同 signal を呼ぶ。
- E2E 必須 (mock 不可、[[feedback_codex_mock_test_trap]])、git 実 verify ([[feedback_codex_stash_leak]])。
- **データソース未確定のまま BT に進まない** — Phase 0 で詰まったら即差し戻し。
