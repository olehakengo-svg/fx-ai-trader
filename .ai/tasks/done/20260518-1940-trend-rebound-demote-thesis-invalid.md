---
id: 20260518-1940-trend-rebound-demote-thesis-invalid
title: "[trend_rebound demote] THESIS_INVALID 確定 → PAIR_PROMOTED から除外 + KB 降格"
owner: codex
status: queued
priority: P0
created_at: 2026-05-18T19:40:00+0900
roadmap_gate: "C (20260518-1730-prime-v2-shadow-audit-w4eda) で `trend_rebound` を **THESIS_INVALID** 判定: N=60 WR=33.3% spread-adj EV=-1.29p PF=0.66 WF=0/3 (Walk-Forward 全 3 fold で EV+ 0 件 = 設計が時間軸に対し全く再現性なし)。再計算 trend_rebound_ATRQ2 cell でも N=12 WR=50% EV=+0.05p Kelly=0.005 で edge 不在。Render API 21 日 fetch (2026-04-27 → 2026-05-18) で trend_rebound は最後 fire 2026-05-12 14:14 → **6 日無 emit**、engine 内で実質停止状態。code 側で `_PAIR_PROMOTED.add(('trend_rebound', 'USD_JPY'))` (modules/demo_trader.py:6658) と `_PAIR_DEMOTED.add(('trend_rebound', 'EUR_USD'))` (L6550) が並存しており、JPY の LIVE 昇格設定は C verdict と矛盾。dead code 化していても LIVE 設定残置はロードマップ整合性チェック (tier_integrity_check) と整合性監査の負担になる。"
rule: R2
related:
  - modules/demo_trader.py
  - knowledge-base/wiki/tier-master.json
  - knowledge-base/wiki/tier-master.md
  - knowledge-base/wiki/strategies/trend_rebound.md
  - knowledge-base/wiki/sessions/prime-v2-shadow-audit-2026-05-18.md
  - research/prime_v2_audit_2026_05_18.md
  - feedback_codex_stash_leak
---

# 0. 背景

C audit verdict (`knowledge-base/wiki/sessions/prime-v2-shadow-audit-2026-05-18.md`):

| 軸 | 値 | 評価 |
|---|---|---|
| Shadow N (21d) | 60 | 🟢 |
| WR | 33.3% | 🔴 |
| spread-adj EV | -1.29p | 🔴 |
| PF | 0.66 | 🔴 |
| Kelly | 0.000 | 🔴 |
| WF (3-fold) | **0/3** | 🔴 |
| best cell (ATRQ2) | N=12 WR=50% EV=+0.05p | 🔴 (edge ない) |
| 直近 emit | **2026-05-12 14:14** | 🔴 (6 日無 fire) |

**Verdict: THESIS_INVALID** — 設計の核 (強トレンド時の Stoch/RSI/BB%B 極端値 + 反転足) が 21 日 N=60 で完全に edge 不在。redesign で救済可能性なし。

# 1. Pre-registered scope (LOCKED)

## 1.1 修正対象

`modules/demo_trader.py` のみ。

## 1.2 必須変更 (機械的、3 ステップ)

### Step 1: `_PAIR_PROMOTED` から trend_rebound × USD_JPY を削除

L6658 付近の以下行を **削除**:

```python
("trend_rebound", "USD_JPY"),          # shadow N=17 EV=+1.14 PF=1.52
```

理由: shadow N=17 当時 (~2 ヶ月前) の EV=+1.14 は small-N curve-fit、N=60 で EV=-1.29 に decay (C audit verdict)。

### Step 2: `_PAIR_DEMOTED` から trend_rebound × EUR_USD を削除

L6550 付近の以下行を **削除**:

```python
("trend_rebound", "EUR_USD"),       # N=6 WR=16.7% EV=-1.85 Kelly=-43.0%
```

理由: Step 3 で `_FORCE_DEMOTED` に追加するため、PAIR_DEMOTED 指定は重複・優先順位逆転。

### Step 3: `_FORCE_DEMOTED` に trend_rebound を追加

L6454 付近 (`"post_news_vol",` の周辺) に **追加**:

```python
# 2026-05-18 (rule:R2): trend_rebound C audit verdict THESIS_INVALID.
# 21d shadow N=60 WR=33.3% EV=-1.29p PF=0.66 WF=0/3 (Walk-Forward 全 fold EV+ 0).
# 直近 emit 6 日無 (engine 内 dead)。設計が時間軸 reproducibility ゼロ、redesign 不可。
# Ref: knowledge-base/wiki/sessions/prime-v2-shadow-audit-2026-05-18.md §trend_rebound
"trend_rebound",
```

## 1.3 不変条件

- 戦略ファイル本体 (`strategies/scalp/trend_rebound.py` 等) は **削除しない** (shadow N 観測継続 + 万一の復活用に保持)
- 別戦略への波及禁止

# 2. テスト要件

## 2.1 既存テスト

```bash
python3 -m pytest tests/ -x -q
python3 scripts/check.py
python3 tools/tier_integrity_check.py --check   # FORCE_DEMOTED ∩ PAIR_PROMOTED 重複 0 確認
```

## 2.2 新規 sanity test (推奨)

`tests/test_trend_rebound_demote.py`:

1. `test_trend_rebound_in_force_demoted` — `"trend_rebound" in DemoTrader._FORCE_DEMOTED`
2. `test_trend_rebound_not_in_pair_promoted` — `("trend_rebound", "USD_JPY") not in DemoTrader._PAIR_PROMOTED`
3. `test_trend_rebound_not_in_pair_demoted` — `("trend_rebound", "EUR_USD") not in DemoTrader._PAIR_DEMOTED`

# 3. KB 更新 (同一 commit)

- `knowledge-base/wiki/strategies/trend_rebound.md` の Status/Stage を `FORCE_DEMOTED (THESIS_INVALID, 2026-05-18)` に更新
- `knowledge-base/wiki/changelog.md` エントリ追加
- `knowledge-base/wiki/decisions/trend-rebound-thesis-invalid-2026-05-18.md` (新規) — 1 ページ判決文 (C audit verdict 引用 + 上記 8 軸表)
- `tools/sync_kb_index.py --write` && `tools/tier_integrity_check.py --write`

# 4. 完了条件 (DoD)

- [ ] `modules/demo_trader.py` の 3 step 反映
- [ ] `tests/test_trend_rebound_demote.py` 3 test PASS
- [ ] `python3 -m pytest tests/ -x -q` 全 PASS
- [ ] `python3 scripts/check.py` ERROR=0
- [ ] `python3 tools/tier_integrity_check.py --check` 重複 0
- [ ] KB 3 ファイル更新
- [ ] git commit + push (single commit)
- [ ] `git log -1 origin/main -- modules/demo_trader.py` で push 確認

# 5. Out of scope

- strategies/scalp/trend_rebound.py 本体の削除 (保持)
- 他戦略への波及
- 設計改修案 (THESIS_INVALID なので不要)

# 6. 注意 (Codex)

- [feedback_codex_stash_leak](memory/feedback_codex_stash_leak.md): final.md ACCEPT で完了させない、`git log/diff` で実 verify
- 削除する 2 行 (PAIR_PROMOTED, PAIR_DEMOTED) を **コメントアウトではなく完全削除** (dead code 残置 = tier_integrity_check ノイズ源)
- FORCE_DEMOTED 追加位置は alphabetical 順序を尊重 (`post_news_vol` の前後どちらでも可)


## Result (2026-05-18T10:50:39Z)

exit=0 · 701s

```
完了しました。`main` に single commit push 済みです。

Commit:
`545f6b5e Demote trend_rebound thesis invalid`

実施内容:
- `modules/demo_trader.py`
  - `_FORCE_DEMOTED` に `trend_rebound` 追加
  - `_PAIR_PROMOTED` から `trend_rebound × USD_JPY` 削除
  - `_PAIR_DEMOTED` から `trend_rebound × EUR_USD` 削除
- `tests/test_trend_rebound_demote.py` 追加
- staleだった `tests/test_volume_live_promote_routing.py` の volume promote 期待値から `trend_rebound × USD_JPY` を除外
- KB更新:
  - `knowledge-base/wiki/strategies/trend-rebound.md`
  - `knowledge-base/wiki/changelog.md`
  - `knowledge-base/wiki/decisions/trend-rebound-thesis-invalid-2026-05-18.md`
  - `sync_kb_index.py --write` / `tier_integrity_check.py --write` 生成物反映

検証:
- `.venv/bin/python -m pytest tests/test_trend_rebound_demote.py -q` → `3 passed`
- `.venv/bin/python -m pytest tests/ -x -q` → `1565 passed, 1 skipped, 1 xfailed`
- `python3 scripts/check.py` → ERROR=0 / 全6チェック通過
- `python3 tools/tier_integrity_check.py --check` → exit 0、重複なし
- `git log -1 origin/main -- modules/demo_trader.py` → `545f6b5e Demote trend_rebound thesis invalid`

補足: この環境のシステム `python3` には `pytest` が入っていなかったため、pytestだけは repo の `.venv/bin/python` で実行しました。
```
