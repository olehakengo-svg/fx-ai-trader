---
id: 20260612-1640-live-tier-exempt-leak-audit
priority: P1
gate: R3
rule: R3
status: queued
created: 2026-06-12
owner: codex
---

# live_tier_exempt 経路監査 — PAIR_DEMOTED 戦略が LIVE 発火するリークの code derivation

**Rule 分類**: R3 (構造バグ疑い / tier 制度の整合性。365日BTスキップ、code derivation で判定)

## Background (Claude 一次データ実測 2026-06-12)

30d clean live (is_shadow=0, dedup_violation除外) の監査で、**tier 上 LIVE 資格がない戦略が live 発火**している:

- `xs_momentum` — tier=**PAIR_DEMOTED** なのに live fill 3 件 (5/13, 5/18, 5/20 GBP_USD, 計-1.4p)。3 件とも `demo_trades.mtf_gate_action='live_tier_exempt'`、`edge_cell_id` 空 (edge cell 経由ではない)
- 参考: `bb_rsi_reversion` (PAIR_DEMOTED) の live 20 件は edge cell E4 経由 = 設計通り (E4 は 6/4 停止済み)。問題は **edge cell を経由しない exempt 経路**
- `zz_pivot_v60_sr` も同じ `mtf_gate_action='live_tier_exempt'` で発火しているが、こちらは PAIR_PROMOTED なので資格はある (経路の確認のみ)

## Tasks

1. `mtf_gate_action='live_tier_exempt'` を付与するコードパスを特定し、**tier チェック (PAIR_DEMOTED/FORCE_DEMOTED 除外) がその経路に存在するか** derivation を書く
2. 判定:
   - **設計** (意図的に tier を免除する仕様) なら → 対象戦略の明示 allowlist 化 + KB `wiki/analyses/system-reference.md` に文書化。PAIR_DEMOTED が含まれる場合はその根拠を書く
   - **バグ** なら → demoted tier を exempt 経路から除外する修正 + 回帰テスト (`PAIR_DEMOTED` 戦略が exempt 経路で live 転送されないこと)
3. 過去 90d で同経路から live 発火した全戦略×tier の実測リスト (demo_trades: `mtf_gate_action='live_tier_exempt' AND is_shadow=0`) を final.md に添付

## 制約

- データ一次ソースは Render 本番 API (`/api/demo/trades`)。ローカル DB は 5 週 stale
- `force_demoted_live_leak` カラム (既存の leak 検知) が今回のケースで 0 だった理由も確認 — 検知器の盲点なら検知器も直す
- 修正は demo_trader の LIVE 転送側のみ。**Shadow 発火は絶対に削らない** (CLAUDE.md 原則3)

## 採用/棄却条件

- 修正 PR は `pytest tests/ -x -q` 全通過 + `scripts/check.py` 通過
- final.md は git log/diff で実 verify (stash leak 教訓 2026-05-11)


## Result (2026-06-12T07:55:20Z)

exit=0 · 608s

```
実装完了。判定は **バグ** として修正しました。

主な変更:
- [modules/demo_trader.py](/data/repo/fx-ai-trader/modules/demo_trader.py:3932)
  - `_is_live_tier_exempt` から `PAIR_DEMOTED` / `FORCE_DEMOTED` を明示除外。
  - `_is_pair_demoted_entry()` を追加し、tier 解決・promote 判定・送信直前 gate に再利用。
  - OANDA 送信直前と pending resend で `PAIR_DEMOTED` を shadow 強制。
- [modules/demo_db.py](/data/repo/fx-ai-trader/modules/demo_db.py:1478)
  - pending resend 用 row に `entry_type` を追加。
- [scripts/check_force_demoted_leak_safety.py](/data/repo/fx-ai-trader/scripts/check_force_demoted_leak_safety.py:138)
  - 既存 `force_demoted_live_leak` の盲点として、`q5_pair_demoted_live` 検出を追加。
- [tests/test_force_demoted_leak_backfill.py](/data/repo/fx-ai-trader/tests/test_force_demoted_leak_backfill.py:117)
  - `PAIR_DEMOTED` live 漏れ検出、final gate、resend row の回帰テストを追加。
- [final.md](/data/repo/fx-ai-trader/final.md:1)
  - code derivation、Render 90d 実測表、検知器盲点、検証結果を記載。

Render `/api/demo/trades?limit=100000` 実測では、`live_tier_exempt AND is_shadow=0` の invalid 行は `xs_momentum × GBP_USD` が `PAIR_DEMOTED` で 5 件、edge 経由なしでした。`force_demoted_live_leak=0` だった理由は、既存検知器が FORCE_DEMOTED strategy 名だけを対象にしていたためです。

検証:
- `.venv/bin/pytest tests/ -x -q`
  - `1845 passed, 1 skipped, 1 xfailed`
- `.venv/bin/python scripts/check.py`
  - exit 0, 全6チェック通過
- `git diff --check`
  - OK

作業ツリーの変更は今回対象の 5 ファイルのみです。
```
