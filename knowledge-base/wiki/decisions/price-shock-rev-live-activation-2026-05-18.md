# Price-Shock Rev Live Activation v2 — 2026-05-18

## 決定

Price-Shock Reversion H1 の 5 戦略を Phase B-1 Shadow-only から Tier 2 (Live MIN lot) に移行する。

対象:
- `price_shock_rev_eur_gbp_h1_long` x EUR_GBP
- `price_shock_rev_eur_aud_h1_long` x EUR_AUD
- `price_shock_rev_usd_cad_h1_long` x USD_CAD
- `price_shock_rev_nzd_jpy_h1_long` x NZD_JPY
- `price_shock_rev_aud_jpy_h1_long` x AUD_JPY

## Shadow-first 緩和の根拠

通常は Shadow N>=30 後に Live 化する。本件は以下の BT 品質を理由に、MIN lot で直接 Live 観測へ進める。

- Wilson_lo >= 0.58 が 5/5 strategy で成立。
- Bonferroni passing cells は family あたり 9-28。
- 12.3y MASSIVE data と BH-FDR m=3744 により post-hoc selection risk を抑制。
- Cross-pair 5 family で single-pair selection effect を回避。
- Qiita 原典 AUDJPY WR=60.06% を WR=60.00% で再現し、方法論の妥当性を確認。

## 実行制約

- Live lot は 1000 units 固定。Kelly half / DD multiplier / lot ramp は bypass する。
- EUR_GBP と EUR_AUD は shared lock を維持し、同時 active position は 1 個まで。
- Keltner Squeeze Breakout と Donchian Momentum Breakout は Shadow-only 維持。
- XAU は対象外。
- Live/Shadow 集計分離を維持し、Live evaluator は `is_shadow=0` のみを見る。

## Safety Net

`tools/price_shock_rev_live_watchdog.py` を 4 時間ごとに実行する。

- Live N >= 10 かつ EV < 0 または Wilson_lower < 0.40 で auto demote。
- auto demote は `data/price_shock_rev_auto_demotions.json` に記録し、`DemoTrader` runtime gate が OANDA Live を遮断する。
- Discord 通知は demote を赤、継続観察を緑で送る。

## Promote Criteria

Lot ramp は自動禁止。`tools/price_shock_rev_promote_evaluator.py` は提案のみ行う。

全 pass 条件:
- Live N >= 30
- Wilson_lower >= 0.50
- Bonferroni-corrected p < 0.01 (m=5)
- 6 週間 sliding window EV > 0

通過時は司令塔へ lot ramp 提案を通知し、別 task の承認まで MIN lot を維持する。

## リスク認識

- Shadow-first 違反: 本件は BT 高品質 + 直接 Live MIN lot。Wilson_lo>=0.58 (5/5) + Bonf 9-28/family を根拠に例外扱い。
- DD 危機継続: project_fxai_state_2026_05_11 で DD=47.22%。5 戦略の Live 追加で DD 悪化 risk があるため MIN lot と N=10 watchdog で bound。
- Cross-pair concentration: EUR_GBP + EUR_AUD shared lock で 50% 軽減。他の USD/EUR 軸 concentration は portfolio task で別途扱う。
- Live regime shift: Backfill 2021-12 から 2026-04 の edge が 2026-05 以降も成立するかは Live 観測でのみ確定する。
