# Price-Shock Reversion Tier 1: Shadow -> Live Promote Pre-reg

## 対象
2026-05-18 Phase B-1 で Shadow 投入された 5 戦略:
- price_shock_rev_eur_gbp_h1_long
- price_shock_rev_eur_aud_h1_long
- price_shock_rev_usd_cad_h1_long
- price_shock_rev_nzd_jpy_h1_long
- price_shock_rev_aud_jpy_h1_long

## Live promote 基準 (LOCK、戦略ごとに独立判定)

戦略 X が以下を全て満たす場合のみ Live promote 提案 (司令塔別判断):

1. **Live shadow N >= 30 trades** (closed)
2. **Shadow Wilson_lo (95%) >= 0.50** を維持
3. **Bonferroni m=5** (本ファミリー 5 戦略同時昇格判定) で **p < 0.01** (= raw p < 0.05/5)
4. **6 週連続 EV > 0** (週次集計)
5. **Cross-correlation**: EUR_GBP と EUR_AUD は portfolio sizing で 同時 active position 1 個まで (demo_trader 側に shared lock 実装済)

## 棄却基準 (即 demote)

- N=15 蓄積時点で Wilson_lo < 0.40 -> Shadow 内で deactivate
- 2 週連続 EV < 0 (週次) -> 緊急 review
- catastrophic SL hit 比率 > 30% -> 戦略構造再検討

## Post-hoc tune 禁止

percentile / horizon / vol_q は Tier 1 確定時の literal (§0.1 表) から変更しない。
変更したい場合は 新 Codex BT task -> 新 family として queue (本 task の派生扱い禁止)。
