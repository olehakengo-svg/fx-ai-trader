---
id: 20260531-1636-donchian-nzd-365d-bt-pre-reg
priority: P1
gate: R1
rule: R1
status: queued
created: 2026-05-31
owner: claude
---

# Donchian × NZD pair 365d BT — pre-reg LOCK evidence reinforcement

**Rule classification**: R1 (Slow & Strict — pair promote + lot↑ 用 pre-reg LOCK evidence)
**Purpose**: 既に LIVE 投入済の `donchian_momentum_breakout × NZD_JPY / NZD_USD` (commit 91dda4ce) の Rule 1 充足条件を後追いで強化。Live N=10 到達 (~5-10 日) 前に BT 根拠を揃え、撤退/継続判断の補強材料にする。

## 背景

2026-05-27 (commit 91dda4ce) で donchian_momentum_breakout × NZD pair を user judgment R1-EXCEPTION で LIVE 投入済。実装:
- `_FORCE_DEMOTED` 解除 → NZD_JPY / NZD_USD のみ `_PAIR_PROMOTED` + `_PAIR_LOT_BOOST=1.0x`
- 他 6 pair は `_PAIR_DEMOTED` で個別遮断

LIVE 投入時の Shadow 実測 (sentinel API dedup-clean since 2026-04-01):

| Pair | N | WR | EV | Total | Wlo95 | BFlo (m=8) |
|---|---:|---:|---:|---:|---:|---:|
| NZD_JPY | 14 | 71.4% | +20.49p | +287p | 0.453 | 0.388 |
| NZD_USD | 16 | 68.8% | +15.52p | +248p | 0.445 | 0.384 |

Rule 1 未充足項目:
- N<30 (Shadow N=14/16)
- BFlo<0.50 (0.388 / 0.384)
- **365d BT 未実施** ← 本タスクで補完
- Pre-reg LOCK: `knowledge-base/wiki/decisions/donchian-nzd-live-exception-2026-05-27.md` 作成済

**動機**: Live N=10 (~5-10 日後) で撤退条件チェック前に BT エビデンスを揃え、Shadow → Live degradation (spread/slippage 乖離) のリスク評価を可能にする。BT で edge 否定なら早期撤退判断、肯定なら継続根拠。

## Files & references

- 戦略本体: `modules/demo_trader.py:donchian_momentum_breakout` (関連 line: 4041, 4608, 6815 周辺)
  - BT 関数は本番 signal 関数を `backtest_mode=True` で呼ぶこと (CLAUDE.md "BT 関数は本番 signal 関数")
- データソース: `data/cache/massive/{NZDJPY,NZDUSD}_15m.parquet` (MASSIVE Market Data API 由来)
  - `feedback_bt_must_use_massive` 参照: Yahoo は 60d 制限で 365d BT 不可、MASSIVE 必須
- Live 投入実装: commit 91dda4ce
- Pre-reg doc: `knowledge-base/wiki/decisions/donchian-nzd-live-exception-2026-05-27.md`
- 類似 BT 前例:
  - `tools/sr_weight_gate_audit_v2.py` (SR-weight Phase 2 365d MASSIVE 4942 events)
  - `tools/post_news_vol_shadow_bt.py` / `tools/stoch_pullback_shadow_bt.py` (shadow BT pattern)
- Sentinel スコア取得 API: `/api/sentinel/stats?entry_type=donchian_momentum_breakout&after_date=2026-04-01`

## Required scope (BT specification)

### 1. 戦略実装と pair selection

- 戦略: `donchian_momentum_breakout` を本番 signal 関数 (`backtest_mode=True`) で呼ぶ
- Pairs: **NZD_JPY, NZD_USD** (LIVE 投入済 2 pair に限定)
- Comparison pair (sanity floor): AUD_JPY (Shadow EV=-12.18p) と USD_CAD (Shadow EV=-9.05p) を **対照群** として同 spec で BT し、NZD pair の edge が pair-specific であることを確認

### 2. データ範囲と TF

- Source: `data/cache/massive/{pair}_15m.parquet` (実装時 missing なら **代替 source 明記必須**、勝手に Yahoo に fallback しない)
- Range: **365 日** (実装時の `pd.Timestamp.utcnow() - 365d` ~ `utcnow()`)
- TF: 15m (戦略デフォルト)
- Spread / friction: 戦略デフォルトをそのまま使用（変更しない）

### 3. Direction × cell decomposition

各 pair で:

- Overall (BUY+SELL): N, WR, EV, PF, MaxDD, Sharpe
- Direction-split: BUY only / SELL only
- Time cohort: Asia (0-7 UTC) / London (7-12) / Overlap (12-16) / NY (16-24)
- Pair × Direction × Session の 8 cell (2 dir × 4 session) ごとに N/WR/EV/PF/Wilson_lo

### 4. Statistical gates

- **Bonferroni** m = 9 (LIVE 投入 2 pair + 対照 2 pair = 4 pair × 2 direction = 8 cell + overall) → α = 0.05/9 ≈ 0.00556、z ≈ 2.536
- **Wilson lower bound** (95% 単純 + Bonferroni 補正版) を全 cell に対して計算
- **Walk-Forward** (3 fold 以上、各 fold で BUY/SELL の sign 一致確認、p-value sign test)
- **Bootstrap 95% EV CI** (n=10,000 resamples)
- **Kelly criterion** (raw + Half) per cell

### 5. Verdict gates

NZD_JPY / NZD_USD それぞれで:

| 結果 | Verdict | アクション提案 |
|---|---|---|
| BFlo > 0.50 AND WF 3/3 same-sign AND Bootstrap CI not crossing 0 | 🟢 PROMOTE_CONFIRMED | LIVE 1.0x 継続、撤退条件緩和提案 |
| BFlo 0.40-0.50 OR WF 2/3 OR CI marginal | 🟡 NEEDS_MORE_LIVE_N | LIVE 1.0x 継続だが N=30 まで撤退条件厳格化 |
| BFlo < 0.40 OR WF 1/3 OR CI crosses 0 | 🔴 PRE_REG_FAIL | LIVE 即時 demote (LOT_BOOST 0.05x), Live N=10 で撤退条件発動 |
| 戦略バグ (entry signal が NaN / 0 件) | ⚠️ BLOCKED_DATA | data prep 別タスク |

## Acceptance criteria

1. 出力: `raw/bt-results/2026-XX-XX-donchian-nzd-365d.md` (rich report)
   - per-pair × direction × session table (N/WR/EV/PF/Wilson_lo/BFlo/Kelly/MaxDD)
   - Walk-Forward 3 fold 結果 + sign test p-value
   - Bootstrap 95% EV CI per cohort
   - 対照群 (AUD_JPY, USD_CAD) 同 spec 結果
   - Final verdict 4 cell (NZD_JPY/NZD_USD × overall/best-cell) と推奨アクション
2. tests/test_donchian_nzd_bt_regression.py 追加（実 BT 関数が呼べる sanity test、N>0 / pip_mult 検証）
3. `python3 -m pytest tests/ -x -q` (除 pre-existing pin failure 5件): 全 pass
4. `python3 scripts/check.py`: 6/6 pass
5. Pre-reg LOCK doc 更新: `knowledge-base/wiki/decisions/donchian-nzd-live-exception-2026-05-27.md` に `## Post-BT verdict (2026-XX-XX)` セクション追記、BT verdict 反映
6. Final report に **Shadow N=14/16 vs BT N≥XXX の比較 table** 必須 (Shadow→BT degradation 評価)

## Out of scope

- DO NOT modify `_FORCE_DEMOTED` / `_PAIR_PROMOTED` / `_PAIR_DEMOTED` / `_PAIR_LOT_BOOST` (LIVE 状態は本タスク完了後に user 判断で変更、Codex は提案のみ)
- DO NOT touch shadow_emit / dedup gate (別 PR scope, 20260527-1435 で対応済)
- DO NOT modify oanda_audit / heartbeat (orthogonal)
- DO NOT touch xs_momentum / session_time_bias cell-forensic (pin test の半完成状態は別 PR scope)
- 他 6 pair (AUD_JPY/USD_CAD/EUR_USD/USD_JPY/AUD_USD/EUR_AUD) の BT は対照群 (AUD_JPY/USD_CAD) 2 個のみ。他 4 pair は本タスク scope 外 (Live で既に止まっているので urgency 低い)

## Memory references

- `feedback_quant_first` — 本件 R1-EXCEPTION user judgment の事後検証
- `feedback_partial_quant_trap` — N/WR/EV だけでなく PF/Wilson/WF/Bonferroni/Kelly 全部要求
- `feedback_bt_must_use_massive` — MASSIVE Market Data parquet 必須、Yahoo fallback 禁止
- `feedback_shadow_first_quant_architecture` — Shadow が真の estimator、BT は軽量 sanity filter
- `feedback_codex_schema_hallucination` — BT で扱う DB スキーマは CREATE TABLE 文を spec に直貼り (本タスクでは demo_trades, oanda_audit を direct query しないため不要)
- `project_vix_carry_1x_intentional_exception_2026_05_21` — 同 R1-EXCEPTION の判例

## Verification (Codex must run before reporting done)

```bash
python3 -m pytest tests/test_donchian_nzd_bt_regression.py -v
python3 -m pytest tests/ -x -q --ignore=tests/test_cell_forensic_2026_05_29_pin.py
python3 scripts/check.py
git diff --stat HEAD
git status
git stash list   # ensure nothing leaked
ls -la raw/bt-results/ | grep donchian-nzd | tail -3
```

All must pass except pre-existing pin failures.

Final.md MUST include:
- per-pair × direction × session table (N/WR/EV/PF/Wilson_lo/BFlo/Kelly/MaxDD)
- WF 3-fold sign test result
- Bootstrap 95% EV CI
- 対照群 (AUD_JPY/USD_CAD) 比較 table
- Verdict per pair (4 cell: NZD_JPY overall / NZD_JPY best-cell / NZD_USD overall / NZD_USD best-cell)
- Shadow vs BT degradation 評価


## Result (2026-05-31T08:11:13Z)

exit=0 · 1834s

```
Implemented the Donchian NZD 365d BT package and report.

Key files:
- [tools/donchian_nzd_365d_bt.py](/data/repo/fx-ai-trader/tools/donchian_nzd_365d_bt.py)
- [tests/test_donchian_nzd_bt_regression.py](/data/repo/fx-ai-trader/tests/test_donchian_nzd_bt_regression.py)
- [raw/bt-results/2026-05-31-donchian-nzd-365d.md](/data/repo/fx-ai-trader/raw/bt-results/2026-05-31-donchian-nzd-365d.md)
- [knowledge-base/wiki/decisions/donchian-nzd-live-exception-2026-05-27.md](/data/repo/fx-ai-trader/knowledge-base/wiki/decisions/donchian-nzd-live-exception-2026-05-27.md)

BT verdict is unfavorable:

| Pair | BT N | WR | EV | BFlo | WF | Bootstrap EV CI | Verdict |
|---|---:|---:|---:|---:|---:|---|---|
| NZD_JPY | 136 | 33.1% | -4.64p | 0.238 | 0/3 | [-7.65, -1.49] | PRE_REG_FAIL |
| NZD_USD | 236 | 29.2% | -3.95p | 0.224 | 0/3 | [-5.78, -2.05] | PRE_REG_FAIL |

Shadow → BT degradation:
- NZD_JPY: Shadow N=14 EV +20.49p → BT N=136 EV -4.64p, delta -25.13p.
- NZD_USD: Shadow N=16 EV +15.52p → BT N=236 EV -3.95p, delta -19.47p.

The report includes the full direction/session cell table, Wilson/BFlo, Kelly, MaxDD, bootstrap CI, 3-fold WF, controls AUD_JPY/USD_CAD, final verdict cells, and action proposal. I did not modify `_FORCE_DEMOTED`, `_PAIR_PROMOTED`, `_PAIR_DEMOTED`, or `_PAIR_LOT_BOOST`.

Verification:
- `python3 -m pytest tests/test_donchian_nzd_bt_regression.py -v`: blocked because system `python3` has no pytest.
- `./.venv/bin/python -m pytest tests/test_donchian_nzd_bt_regression.py -v`: 2 passed.
- `./.venv/bin/python -m pytest tests/ -x -q --ignore=tests/test_cell_forensic_2026_05_29_pin.py`: 1682 passed, 1 skipped, 1 xfailed.
- `python3 scripts/check.py`: 6/6 passed.
- `git stash list`: empty.

Note: to satisfy existing unrelated integration tests during the full-suite run, I populated ignored MASSIVE cache prerequisites for USD_JPY/GBP_JPY M5 data.
```
