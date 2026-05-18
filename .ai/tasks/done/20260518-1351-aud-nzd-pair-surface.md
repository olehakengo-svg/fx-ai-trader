---
id: 20260518-1351-aud-nzd-pair-surface
title: "[AUD/NZD Pair Surface] demo_trader / OANDA bridge / UI / API / risk_analytics 5 layer に AUD_JPY/NZD_JPY/AUD_USD/NZD_USD/EUR_AUD を表層化"
owner: codex
status: queued
priority: P1
created_at: 2026-05-18T13:51:00+0900
roadmap_gate: "Price-Shock Reversion BT (commit 1576dcfd) で Tier 1 strategies が AUDJPY / NZDJPY / EUR_AUD / AUD_USD / NZD_USD 系を選定。MASSIVE parquet は backfill 済 (commit f7f9cd5e、14 pair × {H4,H1})。しかし表層 (demo_trader pair list / app.py API / templates / static / oanda_bridge / risk_analytics / tier-master / KB) に 5 pair が未反映の疑い。Phase B-1 (price-shock 戦略実装) は本 surface に依存。本 task は (a) 8 項目 surface audit (b) 未対応 layer の literal 拡張 (c) 5 pair が各 layer で認識されることを test で検証 (d) OANDA 本番口座での tradability 確認。Live 自動有効化は本 task では行わず Shadow 経路のみ表層化。"
rule: implementation
related:
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
  - data/cache/massive/AUD_JPY_H1.parquet
  - data/cache/massive/NZD_JPY_H1.parquet
  - data/cache/massive/AUD_USD_H1.parquet
  - data/cache/massive/NZD_USD_H1.parquet
  - data/cache/massive/EUR_AUD_H1.parquet
  - feedback_exclude_xau
  - feedback_live_shadow_separation
  - feedback_shadow_first_quant_architecture
  - feedback_codex_mock_test_trap
  - feedback_codex_stash_leak
  - project_price_shock_reproduction_success_2026_05_15
---

# 0. 背景 (Claude 司令塔)

Price-Shock Reversion BT 完全再現成功 (2026-05-15, commit 1576dcfd) により AUDJPY H4 (Qiita 公開と一致)、EUR_GBP H1 (Wilson=0.66) 等 227 SHADOW_CANDIDATE を発見。Tier 1 候補 pair に **AUD_JPY / NZD_JPY / EUR_AUD / AUD_USD / NZD_USD** を含む。

BT は internally に `data/cache/massive/{PAIR}_{TF}.parquet` を直接読むため動いたが、Live/Shadow execution は `modules/demo_trader.py` 等の **表層 pair list** に依存。これら 5 pair が demo_trader / OANDA bridge / dashboard / API / risk_analytics で **literal 登録されていない**と Phase B-1 (price-shock 戦略の Shadow ramp) が実行時 KeyError / 表示欠落で停止する。

MASSIVE parquet は commit `f7f9cd5e` で backfill 済み (14 pair × {H4, H1})。表層への配線だけが残っている状態。

## 司令塔の事前推定 (Codex は実測で再検証すること)

| 想定 layer | 想定 file | 想定 status |
|---|---|---|
| demo_trader pair list | `modules/demo_trader.py` | USD_JPY/EUR_USD 等のみ、5 pair 未登録の疑い |
| OANDA bridge instrument | `modules/oanda_bridge.py` | mapping に AUD/NZD pair 不在の疑い |
| UI dashboard | `templates/*.html`, `static/js/*.js` | pair selector / status table に 5 pair 不在の疑い |
| API endpoints | `app.py` (`/api/demo/status`, `/api/demo/trades`, `/api/risk/dashboard`) | response が pair-aware で AUD/NZD を返すか未確認 |
| Strategy registration | `QUALIFIED_TYPES` / `STRATEGY_TYPES` 等 | pair-strategy mapping 未調査 |
| Risk analytics | `modules/risk_analytics.py` | VaR/CVaR/Kelly が AUD/NZD position を集計するか未確認 |
| tier-master | `knowledge-base/wiki/tier-master.{json,md}` | AUD/NZD pair の戦略未列挙の疑い |
| KB index | `knowledge-base/wiki/index.md` | pair list / Tier 分類未反映の疑い |

# 1. 完了条件 (DoD)

## 1.1 Surface Audit Report

**生成物**: `reports/aud_nzd_surface_audit/SURFACE_AUDIT.md`

- 上記 8 項目を実測し以下 table 化:
  | layer | file | 5 pair 対応状況 (対応済 / 一部 / 未対応) | downstream impact |
- 未対応箇所を「変更必要ファイル」として列挙
- 影響範囲 (loaded by which downstream system) を明記
- 調査コマンド (grep / find / pytest --collect-only) を再現可能な形で記録

## 1.2 5 pair の literal 拡張実装

対象 5 pair: **AUD_JPY, NZD_JPY, AUD_USD, NZD_USD, EUR_AUD**

- demo_trader / OANDA bridge / app.py / templates / static / risk_analytics の各 layer で **既存 USD_JPY / EUR_USD の追加パターンを literal に踏襲**
- 既存 pair の処理ロジックを **絶対に変更しない** (regression 厳禁)
- Phase B-1 の strategy 登録時に pair list で `KeyError` / `UnknownPair` 等が出ない状態に揃える
- pair list が config / constants として定義されている箇所 (例: `SUPPORTED_PAIRS`) は **明示的に列挙**

## 1.3 自動テスト (mock 禁止、feedback_codex_mock_test_trap)

**新規**: `tests/test_aud_nzd_pair_surface.py`

検証 case:
1. `modules/demo_trader.py` の pair list に 5 pair が含まれる
2. `modules/oanda_bridge.py` の instrument mapping で 5 pair が解決される (実 OANDA call は不要、mapping table のみ assertion)
3. `modules/risk_analytics.py` が 5 pair の synthetic position を集計可能 (KeyError raise しない)
4. `app.py` の `/api/demo/status` (Flask test client 経由) response JSON に 5 pair の slot がある
5. dashboard HTML を `render_template` 経由で取得し、5 pair の string が文字列として含まれる
6. tier-master 読み込み test で 5 pair が pair set に含まれる

**Integration test**: Flask test client で `app.py` 起動状態をシミュレートし `/api/demo/status` `/api/risk/dashboard` の response を assertion。

**手動検証セクション (final.md に必須記載)**:
- `python3 app.py` で実際に起動
- `curl http://localhost:<PORT>/api/demo/status` で AUD_JPY 等が含まれることを確認
- curl 出力 (JSON snippet) を final.md に貼る

## 1.4 tier-master / KB 同期

```bash
python3 tools/sync_kb_index.py --write
python3 tools/tier_integrity_check.py --write
```

- `knowledge-base/wiki/strategies/` ディレクトリで AUD/NZD pair が表示される pattern を維持
- `knowledge-base/wiki/index.md` の pair tier 分類に 5 pair の slot を追加 (Tier 未確定なら "Phase B-1 Shadow candidate" として記載)

## 1.5 OANDA 本番口座 tradability 確認

**実測必須** (Codex は OANDA_API_KEY を環境変数経由で参照、credential は queue file に書かない):

- `OandaClient.list_instruments()` (or 等価メソッド) で 5 pair が本番口座 (Live + Practice 両方) で trade 可能か確認
- 不可な pair があれば final.md に **明記**し、その pair は "Shadow only / OANDA execution disabled" 制約として `modules/oanda_bridge.py` に flag 化
- OANDA Japan は CFD 制約あり (project_cfd_trader_phase0_2026_05_07 参照) — FX major pair は問題ない想定だが必ず実測

## 1.6 commit & push

- 全変更を 1〜複数の論理コミットに分割
- `git status` が clean (新規ファイル含めて全 stage 済)
- final.md に commit SHA を列挙
- **stash 漏れ厳禁** (feedback_codex_stash_leak): `git stash list` を完了時に空 or 関係ない entry のみであることを確認

# 2. 司令塔ガード (絶対遵守)

- [ ] **既存 pair の処理ロジックを変更しない**: USD_JPY / EUR_USD 等の挙動を保ったまま AUD/NZD を追加
- [ ] **XAU は引き続き除外** (feedback_exclude_xau): XAU pair を pair list に追加しない、XAU 関連の触り厳禁
- [ ] **Live trading 自動有効化は禁止**: 表層に出すだけ、Shadow 実行 / Live promotion は別 task の Phase B-1 が担う。本 task で `LIVE_ENABLED=True` / `is_shadow=False` 等の flag を変えない
- [ ] **MASSIVE parquet との整合**: `data/cache/massive/{PAIR}_1h.parquet` が存在する pair のみ表層化 (5 pair は backfill 済、commit f7f9cd5e)。parquet 不在 pair の表層化は禁止
- [ ] **stash 漏れ禁止** (feedback_codex_stash_leak): final commit 時に `git stash list` clean、untracked test file が `git add` 漏れしていないこと
- [ ] **mock-only test 禁止** (feedback_codex_mock_test_trap): test は real module import / real config 読み込みで通すこと、self-mock で 10/10 PASS を final 報告にしない
- [ ] **本番 DB / `.env` / OANDA secret 破壊禁止**

# 3. 推定変更ファイル (Codex は実測で確定すること)

- `modules/demo_trader.py` (pair list、initialization)
- `modules/oanda_bridge.py` (instrument mapping)
- `modules/risk_analytics.py` (pair-wise aggregation)
- `app.py` (API endpoint response)
- `templates/*.html` (dashboard pair selector / status table)
- `static/js/*.js` (frontend pair handling)
- `knowledge-base/wiki/index.md` (pair tier 分類)
- `knowledge-base/wiki/tier-master.{json,md}`
- `tests/test_aud_nzd_pair_surface.py` (新規)
- `reports/aud_nzd_surface_audit/SURFACE_AUDIT.md` (新規)

# 4. Verdict matrix

| 結果 | 条件 |
|---|---|
| **ACCEPT** | 1.1〜1.6 すべて満たし、5 pair が全 layer で literal 認識される。test 全 PASS。OANDA tradability 確認済 (不可 pair は明記)。`git status` clean、stash list clean |
| **PARTIAL** | 一部 layer (e.g. tier-master / KB のみ) 未完了。final.md に未完了 layer と理由を明記 |
| **REJECT** | 既存 pair の挙動 regression / XAU 混入 / Live flag 変更 / mock-only test / stash 漏れ |

# 5. 期待実行時間

2-3 時間 (audit ~30min + 実装 ~60min + test ~30min + 起動検証 ~30min + KB 同期 ~15min)

# 6. 関連 memory / commit

- commit `f7f9cd5e`: 14 pair × {H4, H1} MASSIVE parquet backfill
- commit `1576dcfd`: Price-Shock Reversion BT 完全再現、227 SHADOW_CANDIDATE
- memory `project_price_shock_reproduction_success_2026_05_15`
- memory `feedback_exclude_xau`
- memory `feedback_live_shadow_separation`
- memory `feedback_shadow_first_quant_architecture`
- memory `feedback_codex_mock_test_trap`
- memory `feedback_codex_stash_leak`


## Result (2026-05-18T05:11:39Z)

exit=0 · 605s

```
**Verdict: PARTIAL vs strict DoD**

実装・テスト・commit/push は完了しました。Strict DoD では以下 2 点だけ未達です。

- Practice OANDA tradability: practice 用 env がなく、practice base URL は 401 で未検証。
- `git status` clean: 作業前から存在した OB retest 系 untracked files が残っています。今回分は commit 済み、stash は空です。

Commit pushed:

```text
9a86556452ad19434ecc8a73ad51d17ba65167f7 Add AUD/NZD pair surface slots
```

実装内容:

- `AUD_JPY / NZD_JPY / AUD_USD / NZD_USD / EUR_AUD` を demo/API/OANDA/UI/risk/KB に surface 追加
- 追加 mode は `daytrade_1h_*`、すべて `auto_start=False`
- `price_shock_reversion` は `UNIVERSAL_SENTINEL` として登録。Live promotion flag は変更なし
- Audit report: `reports/aud_nzd_surface_audit/SURFACE_AUDIT.md`
- Test: `tests/test_aud_nzd_pair_surface.py`

検証:

```text
python3 -m py_compile ... -> PASS
.venv/bin/python -m pytest tests/test_aud_nzd_pair_surface.py tests/test_risk_analytics_mc_lot_multiplier.py tests/test_edge_activation_review_fixes.py
16 passed
```

OANDA tradability:

```text
Live: AUD_JPY=True, NZD_JPY=True, AUD_USD=True, NZD_USD=True, EUR_AUD=True
Practice: not verified, missing practice credentials; request returned 401
```

手動起動検証:

- `python3 app.py`: system Python に Flask がなく失敗
- `NO_AUTOSTART=1 PORT=5018 .venv/bin/python app.py`: 起動成功
- `curl http://127.0.0.1:5018/api/demo/status` snippet:

```json
{
  "pairs": {
    "AUD_JPY": {"instrument": "AUD_JPY", "modes": ["daytrade_1h_audjpy"]},
    "NZD_JPY": {"instrument": "NZD_JPY", "modes": ["daytrade_1h_nzdjpy"]},
    "AUD_USD": {"instrument": "AUD_USD", "modes": ["daytrade_1h_audusd"]},
    "NZD_USD": {"instrument": "NZD_USD", "modes": ["daytrade_1h_nzdusd"]},
    "EUR_AUD": {"instrument": "EUR_AUD", "modes": ["daytrade_1h_euraud"]}
  }
}
```

Final checks:

```text
git stash list: empty
server on :5018: stopped
git status: only pre-existing OB retest untracked files remain
```
```
