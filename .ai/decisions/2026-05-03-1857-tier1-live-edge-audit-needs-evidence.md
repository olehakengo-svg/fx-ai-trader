---
date: 2026-05-03
task: 20260503-1840-tier1-live-edge-audit
verdict: ACCEPT_NEEDS_MORE_EVIDENCE
rule: R2
gate: Gate 0 (生存) — Tier 1 LIVE lot ↑ 路線は本質的に不可能と判明
codex_session: 019ded40-127f-71d2-9962-76b73cc6ac76
---

# A1 Tier 1 LIVE edge audit — ACCEPT_NEEDS_MORE_EVIDENCE decision

## Verdict

**ACCEPT** — Codex は task §4 判定基準に従って `NEEDS_MORE_EVIDENCE` を honest に出力。実装は仕様通り (Bonferroni m=5, per-pair BEV_WR, delta-from-BT 表, 5 テスト pass, scope 厳守)。

ただし本タスクの結果は **「Tier 1 LIVE lot ↑」路線そのものへの致命的反証**を含む — 5 cells 中 3 cells で Live N=0、Tier 1 全体で 736 Live/OANDA 件中 7 件 (0.95%) のみ発火。

## Codex 結果の品質評価

- ✅ Read-only audit、本番 DB / `.env` / OANDA secrets / `live_ng_cells` / `app.py` / `modules` / `strategies` 一切 untouched
- ✅ `is_shadow=0 AND oanda_trade_id IS NOT NULL AND oanda_trade_id != '' AND status=CLOSED` filter 厳格適用 (memory feedback `live_vs_shadow_strict_separation` 整合)
- ✅ XAU 除外、per-pair BEV_WR (USD_JPY=34.4% / EUR_USD=39.7% / GBP_USD=37.9%) lockdown
- ✅ Bonferroni m=5, α'=0.010, one-sided binomial test
- ✅ 5/5 unit tests pass
- ✅ delta-from-BT 表 (ΔWR / ΔEV / ΔPF) 全 cell 出力
- ✅ proposal doc only、PR 作成なし、編集 scope spec 通り
- ⚠️ Codex sandbox の curl exit 6 で Render fresh fetch 失敗 → `/tmp/live-trades-20260503.json` 既存 snapshot (9.4 MB) 使用。Claude main 側で fresh fetch 確認推奨

## 致命的構造発見

### 1. Tier 1 ELITE が Live で事実上不在

736 Live/OANDA closed FX trades (snapshot) のうち、Tier 1 LIVE 5 cells に該当するのは **7 件 (0.95%)**:
- gbp_deep_pullback × GBP_USD: N=3
- trendline_sweep × GBP_USD: N=4
- session_time_bias × USD_JPY: **N=0**
- session_time_bias × EUR_USD: **N=0**
- xs_momentum × USD_JPY: **N=0**

→ 本来 Gate 0 救済の主力候補だった 5 cells のうち、3 cells が全く発火していない。BT で N=157/566/342 (合計 1,065 件) を稼いでいた戦略が Live で N=0。

### 2. 99% の Live 活動は non-Tier 1 で負

| bucket | N | EV | raw Kelly | PF | total pips |
|---|---:|---:|---:|---:|---:|
| all Live/OANDA | 736 | -0.81 | **-0.1854** | 0.680 | -597.4 |
| Tier 1 target 5 cells | 7 (0.95%) | -2.46 | -0.8190 | 0.411 | -17.2 |
| non-target | 729 (99.05%) | -0.80 | -0.1810 | 0.684 | -580.2 |

→ Aggregate raw Kelly=-0.1854 (負) は non-target 729 件の負 EV が支配。R2 counterfactual REJECT (all-target STOP でも Kelly=-0.25) の数学的真因がここにある — STOP 対象に non-target が含まれていなかった可能性。

### 3. 発火した Tier 1 7 件も directional に負

7 件の小サンプルだが Tier 1 全体で WR=57.14%, EV=-2.46, raw Kelly=-0.8190, PF=0.411。
- BT 期待値からの delta: ΔEV=-1.93 程度 (5 cell 加重)
- 統計的に H1 (edge 残存) を否定するには N 不足、しかし directional には BT-Live divergence の存在示唆

## Data hygiene

- BT/Live/OANDA 一切混在なし (snapshot は live closed only)
- Shadow データは集計から完全除外
- XAU 除外確認済み
- `oanda_trade_id != ''` 厳格 (memory feedback `live_vs_shadow_strict_separation` の Live=`oanda_trade_id != ''` 整合)
- 唯一の懸念: snapshot は今朝時点で fresh fetch ではない → 影響軽微だが weekend 中の最新 fills 反映遅延は可能性

## Roadmap impact

### Gate 0 救済路線の再評価

**Tier 1 LIVE lot ↑ 路線は本質的に不可能** — 3 cells (60%) が Live で発火していない以上、lot を上げても寄与しない。session_time_bias × {USDJPY, EURUSD} と xs_momentum × USDJPY は **Live route そのものが喪失**。

### 真の Gate 0 ボトルネック

99% の Live activity は non-Tier 1 戦略の負 EV で構成。これは個別戦略レベルの cell-cut では解決不可能 (R2 REJECT で証明済み)。

→ **構造的問題**: 戦略 routing / eligibility / signal generation pipeline に Tier 1 ELITE を抑制する gate が存在する可能性。

### 教訓候補

「BT で +EV な elite 戦略が Live で N=0 の場合、lot promotion でなく **routing eligibility の構造監査** が precedent。Tier1/Tier2 分類は signal generation の必要条件であって十分条件ではない」

## Artifacts

- 監査スクリプト: `tools/tier1_live_edge_audit.py` (新規)
- テスト: `tests/test_tier1_live_edge_audit.py` (5 passed)
- 決定レポート: `knowledge-base/wiki/decisions/tier1-live-edge-audit-2026-05-03.md`
- run report: `.ai/runs/20260503-185128-20260503-1840-tier1-live-edge-audit/final.md`
- 親 R2 audit: `wiki/decisions/r2-strategy-instrument-counterfactual-2026-05-03.md`
- 親 review: `.ai/decisions/2026-05-03-1834-r2-strategy-instrument-counterfactual-reject.md`

## Next task

ロードマップ上の最優先は **Gate 0 (生存)**。本 audit で Tier 1 LIVE lot ↑ 路線が消えた今、次の 1 タスクは:

→ **Tier 1 ELITE routing eligibility audit (新規, R3)**

具体的には:
1. **session_time_bias × {USD_JPY, EUR_USD}** と **xs_momentum × USD_JPY** が Live で N=0 の原因を構造的に診断
2. signal generation 関数 (`strategies/`) → entry gate (`app.py`/`modules/demo_trader.py`) → OANDA 送信 (`modules/oanda_bridge.py`) のどこで suppress されているか
3. Render `/api/demo/trades?is_shadow=1` 含むスナップショットで shadow には出ているか確認 (出ているなら gate 問題、出ていないなら signal 問題)
4. KB の既存 lesson `feedback_check_orphan_local_app` / `feedback_bypass_share_guard_chain` / `feedback_eligible_vs_effective` を踏まえた構造監査

並行で 1 つは:
- **Live snapshot fresh refresh** (Claude main 側 network-enabled で `curl /api/demo/trades?limit=100000` → 再 audit) — 5 分作業、確認用

ただし fresh refresh で結論が大きく変わる可能性は低い (snapshot は本日 fetch、N の order が変わるとは考えにくい)。

→ **Codex 次タスク提案**: `.ai/tasks/queue/20260503-1900-tier1-elite-routing-eligibility-audit.md` を新規作成し、Tier 1 ELITE 3 cells (N=0) の Live route 喪失原因を構造監査。実装は Claude main で fresh fetch を並行実施。
