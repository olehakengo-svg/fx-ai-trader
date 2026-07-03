# Price-Shock Reversion — promote-readiness 再監査 (2026-06-08, 訂正版)

**Verdict: 正常稼働・Shadow N 蓄積待ち (quick revival は不可能)**。
**Rule**: R1 | **Pre-reg**: `.ai/plans/claude/20260608-2030-price-shock-promote-readiness-reaudit.md`
**一次ソース**: Render production (sentinel by_type = Shadow track / `/api/demo/trades` = Live track)

> ⚠️ 本 doc は調査途中の早期結論 (「fire-rate / wiring blocker」) を**全面訂正**した最終版。
> 早期結論で挙げた3つの blocker は検証の結果いずれも**誤り**だった (下記)。

## 実態 (検証で確定)

| 項目 | 検証結果 |
|---|---|
| HourlyEngine への登録 | ✅ 5戦略全部ロード (`strategies/hourly/__init__.py:19-23`) |
| 評価ループ稼働 | ✅ `daytrade_1h_*` モードが全ペア active tick (38-39 ticks, running=True)。毎 H1 バー `HourlyEngine.evaluate_all` 経由で price_shock を評価 |
| 専用 `price_shock_rev_*` モード | 走っていないが**冗長な重複**。daytrade_1h_* 経由で評価されるため無害 (3発火はこの経路) |
| promote evaluator の名前 | ✅ `WATCHED_CELLS` は正しく `*_h1_long` (stale ではない) |
| short 側未 deploy | ✅ **正当**。shortlist Tier 1 (TOP PROMOTE) = 5 family 全部 LONG_SHOCK。SHORT_SHOCK は Tier 3 WATCH / Tier 4 REJECT のみ |

## 早期結論の誤り (記録)

1. ❌ 「wiring blocker」→ 実際は daytrade_1h_* 経由で毎バー評価済。
2. ❌ 「evaluator 名 stale」→ 実際は正しい名前。
3. ❌ 「short deploy で機会倍増」→ short は grid で promote 級エッジ無し (downside-shock asymmetry: 下落ショックのみ確実に反転)。
4. evaluator N=0 の理由: line 118 で `is_shadow!=0` を skip = **Live track 専用ツール**。price_shock は強制 Shadow 稼働なので N=0 は正しい (Live 未投入)。Shadow 実績は sentinel by_type が正 population。

## 真の状況 — rare-event による N 枯渇

production sentinel (Shadow track, by_type all-time):
- aud_jpy_h1_long: N=1 (+6.9p), eur_gbp_h1_long: N=1 (-4.5p), nzd_jpy_h1_long: N=1 (+54.0p)
- eur_aud / usd_cad: 0

BT rep cell は N=239〜426 (≈12年 H1) = **bar の ~0.33% でしか発火しない 1%-percentile shock**。3週・5ペア long-only では期待発火 ~6件 (Poisson)、実測3件は order 整合。**設計通りの希少さ**であって異常ではない。

→ **N>=30/cell の promote 到達には数ヶ月の Shadow 蓄積が必要**。short 追加は正当に不可 (エッジ無し)。**quick revival の lever は存在しない**。正しい行動は「Shadow を回し続けて待つ」。

## 唯一の実アクション (任意)

- **Shadow-track 専用 readiness evaluator が無い**: 現 evaluator は Live 段階用 (is_shadow=0)。Shadow→Live 昇格判定には is_shadow=1 を読む別系統が要る。ただし現状 N=1-3 では作っても全 WATCH なので、N が二桁に乗ってから着手で十分。
- by_type(N=1) と Live-evaluator(N=0) の差は「Shadow と Live の population 違い」で説明済 = バグではない。

## 教訓
段階的に「blocker だ」と早期結論を3回出し、3回とも検証で覆った。**production 監査は実コード+実 API で1つずつ潰すまで verdict を出さない** ([[feedback_success_until_achieved]] / [[feedback_label_empirical_audit]])。

## 関連
- `project_price_shock_phase_b1_done_2026_05_18` / [[project_risk_premia_pivot_2026_06_08]]
