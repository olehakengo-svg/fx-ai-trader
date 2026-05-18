---
id: 20260518-1413-usd-cad-usd-chf-pair-surface
title: "[USD_CAD / USD_CHF Pair Surface] aud-nzd 確立 pattern を literal 踏襲して 2 pair 追加"
owner: codex
status: queued
priority: P1
created_at: 2026-05-18T14:13:00+0900
roadmap_gate: "Price-Shock Dedup Phase A (commit f4883a92) で Tier 1 #3 = USD_CAD H1 LONG (N=247, WR=66.4%, Wilson_lo=0.603, PF=5.30, bonf=7), Tier 3 = USD_CHF H4 SHORT / USD_CHF H1 LONG が選定された。一方 fx-ai-trader 表層 (demo_trader / oanda_bridge / app.py / templates) は USD_JPY/EUR_USD/GBP_USD/GBP_JPY/EUR_JPY/EUR_GBP の 6 pair のみ。USD_CAD / USD_CHF は未配線。前 task 20260518-1351-aud-nzd-pair-surface が AUD_JPY/NZD_JPY/AUD_USD/NZD_USD/EUR_AUD 5 pair の surface pattern を既に確立しているため、本 task は **同 pattern を literal 踏襲** して USD_CAD + USD_CHF の 2 pair を同一構造で追加する。Phase B Week 1 で Tier 1 #3 (USD_CAD) 実装するための前提配線。"
rule: implementation
related:
  - .ai/tasks/done/20260518-1351-aud-nzd-pair-surface.md   # 完了後に done/ に移動する、本 task の precedent
  - modules/demo_trader.py
  - modules/oanda_bridge.py
  - modules/risk_analytics.py
  - app.py
  - templates/
  - static/
  - knowledge-base/wiki/index.md
  - knowledge-base/wiki/tier-master.json
  - knowledge-base/wiki/tier-master.md
  - tools/sync_kb_index.py
  - tools/tier_integrity_check.py
  - data/cache/massive/USD_CAD_1h.parquet
  - data/cache/massive/USD_CAD_4h.parquet
  - data/cache/massive/USD_CHF_1h.parquet
  - feedback_exclude_xau
  - feedback_live_shadow_separation
  - feedback_shadow_first_quant_architecture
  - feedback_codex_mock_test_trap
  - feedback_codex_stash_leak
  - project_price_shock_reproduction_success_2026_05_15
---

# 0. 背景 (Claude 司令塔)

前 task `20260518-1351-aud-nzd-pair-surface` (現在 running、本 task push 時点) が完了すると、AUD_JPY / NZD_JPY / AUD_USD / NZD_USD / EUR_AUD の 5 pair が demo_trader / oanda_bridge / app.py / templates / risk_analytics / tier-master / KB に配線される。

ただし Price-Shock Dedup Phase A の Tier 1/3 family には **AUD/NZD 系以外にも** USD_CAD / USD_CHF が含まれており、これらも同様に表層配線が必要:

| Pair | Tier | Rep cell stats |
|---|---|---|
| USD_CAD H1 LONG | **T1 #3** | N=247, WR=66.4%, Wilson_lo=0.603, PF=5.30, bonf_pass=7/13 |
| USD_CHF H4 SHORT | T3 (WATCH) | N=48, WR=70.8%, Wilson_lo=0.568, PF=2.43 |
| USD_CHF H1 LONG | T3 (WATCH) | N=216, WR=63.0%, Wilson_lo=0.563, PF=1.76 |
| USD_CHF H1 SHORT | T4 (RESERVE, cap overflow) | N=1597, WR=??, Wilson_lo=0.507 |

実測 (本 task 投入時):

| Pair | demo_trader | oanda_bridge | app.py | templates | MASSIVE 1h parquet |
|---|---|---|---|---|---|
| USD_CAD | ❌ | ❌ | ❌ | ❌ | ✅ |
| USD_CHF | ❌ | ❌ | ❌ | ❌ | ✅ |

# 1. 完了条件 (DoD)

## 1.1 Precedent 確認

本 task は **aud-nzd-pair-surface (前 task) の commit が確立した pattern を literal 踏襲する** ことを最優先とする。

- 開始時に `git log --oneline -20` で前 task の commit を特定 (期待: `feat:` or `chore:` で 5 pair 追加の commit が直前に存在)
- 前 task が修正した file 一覧を `git show --stat <commit>` で確認
- 各 file の AUD/NZD 系 entry を locate し、**同じ位置・同じ構造**で USD_CAD / USD_CHF entry を追加

**前 task が未完了 or failed の場合**: 本 task は abort して final.md に「前 task pending、本 task は precedent 不在のため REJECT」を明記し、queue に書き戻す。worker 側で自動 reject すること。

## 1.2 2 pair の literal 拡張実装

対象: **USD_CAD, USD_CHF**

- aud-nzd task と同等 layer (demo_trader / oanda_bridge / risk_analytics / app.py / templates / static / tier-master / KB) を全てカバー
- 既存 USD_JPY / GBP_USD の pip multiplier / spread / margin 等の定数を **そのまま流用** (USD_CAD と USD_CHF は USD クロスなので USD_JPY とは pip 桁が異なる: 10000、JPY pair でない)
  - pip_mult = 10000 for USD_CAD / USD_CHF (vs 100 for *_JPY)
  - 既存 logic `_pip_mult = 100 if (_inst in ("USD_JPY", "EUR_JPY", "GBP_JPY") or "XAU" in _inst) else 10000` で USD_CAD / USD_CHF は自動的に 10000 になるが、**明示的な assertion test を入れる**
- 既存 pair の挙動を **絶対に変更しない** (regression 厳禁)

## 1.3 自動テスト (mock 禁止)

**新規**: `tests/test_usd_cad_usd_chf_pair_surface.py`

検証 case:
1. demo_trader pair list に USD_CAD / USD_CHF が含まれる
2. oanda_bridge instrument mapping で 2 pair が解決される
3. risk_analytics が 2 pair の synthetic position 集計可能
4. `/api/demo/status` Flask test client response に 2 pair の slot がある
5. dashboard HTML を `render_template` 経由で取得し 2 pair の string が含まれる
6. tier-master 読み込み test で 2 pair が pair set に含まれる
7. **pip_mult 専用 test**: USD_CAD の pip_mult = 10000, USD_CHF の pip_mult = 10000 を assertion
8. **回帰 test**: USD_JPY / EUR_USD / GBP_USD 等の既存 pair が依然認識されること (前 task で追加された AUD_JPY / NZD_JPY / AUD_USD / NZD_USD / EUR_AUD も同様)

**Integration test**: Flask test client で 2 pair の API response を assertion。

**手動検証 (final.md 必須)**:
- `python3 app.py` 起動
- `curl http://localhost:<PORT>/api/demo/status` で USD_CAD と USD_CHF が含まれることを確認
- curl 出力 (JSON snippet) を final.md に貼る

## 1.4 tier-master / KB 同期

```bash
python3 tools/sync_kb_index.py --write
python3 tools/tier_integrity_check.py --write
```

- `knowledge-base/wiki/index.md` の pair tier 分類に USD_CAD / USD_CHF を追加
- price-shock Phase A 由来の Tier 1 #3 (USD_CAD) を「Phase B Wave 1 candidate」として記載

## 1.5 OANDA 本番口座 tradability 確認

- `OandaClient.list_instruments()` で USD_CAD / USD_CHF が trade 可能か確認
- 不可なら final.md に明記し Shadow only 制約として flag 化
- OANDA Japan は major + cross pair は基本問題ない想定だが必ず実測

## 1.6 commit & push

- 1 commit に集約 (or 論理分割)
- `git status` clean (新規ファイル含む全 stage)
- final.md に commit SHA + 修正 file list
- `git stash list` 完了時に空 or 関係ない entry のみ (`feedback_codex_stash_leak`)

# 2. 司令塔ガード

- [ ] **前 task (aud-nzd-pair-surface) の pattern を literal 踏襲**: 独自設計禁止、aud-nzd が立てた entry を見つけて同じ位置に USD_CAD / USD_CHF を挿入
- [ ] **前 task 未完了なら本 task abort** (precedent 不在で独自実装すると aud-nzd 完了後に conflict)
- [ ] **既存 pair の挙動変更禁止** (USD_JPY / EUR_USD / GBP_USD / 既存 AUD/NZD/EUR_AUD)
- [ ] **XAU 除外** (`feedback_exclude_xau`): XAU 触らない
- [ ] **Live 自動有効化禁止**: 表層に出すだけ、Shadow execution は Phase B 別 task
- [ ] **MASSIVE parquet 整合**: USD_CAD/USD_CHF 1h parquet 存在を pre-check
- [ ] **mock-only test 禁止** (`feedback_codex_mock_test_trap`): real module import / real Flask test client
- [ ] **stash 漏れ禁止** (`feedback_codex_stash_leak`): final で `git stash list` 確認
- [ ] **pip_mult 取り違い禁止**: USD_CAD/USD_CHF は JPY pair ではないので pip_mult=10000 (既存 logic で自動だが test で固定)

# 3. 想定変更ファイル

aud-nzd task が触ったファイル群と同一を想定:
- `modules/demo_trader.py`
- `modules/oanda_bridge.py`
- `modules/risk_analytics.py`
- `app.py`
- `templates/*.html`
- `static/js/*.js` (該当する場合)
- `knowledge-base/wiki/index.md`
- `knowledge-base/wiki/tier-master.{json,md}`
- `tests/test_usd_cad_usd_chf_pair_surface.py` (新規)
- `reports/aud_nzd_surface_audit/SURFACE_AUDIT.md` の補遺 or 同等 file

# 4. Verdict matrix

| 結果 | 条件 |
|---|---|
| **ACCEPT** | 1.1〜1.6 全達成。2 pair が全 layer で literal 認識、test 全 PASS、OANDA tradability 確認、`git status` clean、stash list clean、aud-nzd pattern を逸脱なし |
| **PARTIAL** | 一部 layer 未完了。final.md に未完了 layer と理由を明記 |
| **REJECT** | 既存 pair regression / XAU 混入 / Live flag 変更 / mock-only test / stash 漏れ / aud-nzd pattern からの逸脱 |
| **ABORT (pre-flight)** | 前 task `20260518-1351-aud-nzd-pair-surface` が done/ に存在しない (running/failed/queue にいる)。Codex は本 task を実行せず final.md に "precedent pending" を記して queue に書き戻し |

# 5. 期待実行時間

1-2 時間 (precedent 確認 ~15min + 2 pair 拡張 ~45min + test ~30min + 起動検証 ~15min + KB 同期 ~15min)。aud-nzd より対象が少ない (5→2 pair) ので短い想定。

# 6. 関連 commit / memory

- precedent: `20260518-1351-aud-nzd-pair-surface` (本 task push 時 running)
- price-shock Phase A: commit `f4883a92` (Tier 1 #3 = USD_CAD H1 LONG)
- MASSIVE backfill: commit `f7f9cd5e` (14 pair × {H4, H1})
- memory `project_price_shock_reproduction_success_2026_05_15`
- memory `feedback_codex_mock_test_trap`
- memory `feedback_codex_stash_leak`
- memory `feedback_exclude_xau`
- memory `feedback_live_shadow_separation`
