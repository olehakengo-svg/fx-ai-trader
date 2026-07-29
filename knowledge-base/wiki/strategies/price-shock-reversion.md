# price_shock_reversion

## Status: UNIVERSAL_SENTINEL

- **Note**: 本カードは price-shock-rev family の親戦略 (surface)。ペア別 Live 昇格分は個別カードが一次ソース。

## 概要
H1 252-bar log return 1%-tile negative shock 後の horizon-exit LONG mean reversion (親戦略)。
ペア別セルは 12.3y MASSIVE grid スキャン (BH-FDR m=3744) で選抜し、Tier 1 shortlist 5 family を 2026-05-18 に Live MIN lot 活性化 ([[price-shock-rev-live-activation-2026-05-18]])。

## ペア別カード (Live 昇格分)
- [[price-shock-rev-aud-jpy-h1-long]] (AUD_JPY, horizon=12, vol_q=ALL)
- [[price-shock-rev-eur-aud-h1-long]] (EUR_AUD, horizon=12, vol_q=Q5)
- [[price-shock-rev-eur-gbp-h1-long]] (EUR_GBP, horizon=3, vol_q=Q5)
- [[price-shock-rev-nzd-jpy-h1-long]] (NZD_JPY, horizon=12, vol_q=Q5)
- [[price-shock-rev-usd-cad-h1-long]] (USD_CAD, horizon=3, vol_q=Q5)

## 現況
- **2026-07-28 live 再武装** (PR #119): `_is_xau_inst` バグ (2026-04-10〜) で 3.5 ヶ月 live 送信死 → 修復 + user 決裁「7 席全部再武装」で 5 セル live 送信可 ([[lesson-preserve-sltp-unboundlocal-2026-07-28]])。同日時点 live fill N=0 (次シグナル待ち)
- ✅ **exit オーバーレイ逸脱 → 是正済み (2026-07-28 執行)**: BE_LOCK A/B + ATR-BE/trail + SIGNAL_REVERSE が本 family に適用され LOCK 済み Exit 設計 (horizon or 2×ATR のみ) と乖離していた問題を、§5(a)+(b) 執行で解消 (BE_LOCK trig 0.0 code pin + ATR-BE/trail/SIGNAL_REVERSE 免除)。counterfactual 判断材料 = [[preserve-exit-overlay-2026-07-28]] §6、執行記録 = 同 §7。**是正以前の close_reason=`sl_2atr` はクリップ発火を含むラベル汚染あり** (歴史系列の解釈時に注意、遡及換算は `tools/price_shock_exit_counterfactual.py`)。WEEKEND_CLOSE のみ既知の残存逸脱 (§7)
- 2026-06-08 再監査: 5 戦略とも正常稼働、rare-event (発火 ~0.33%/bar) による Shadow N 蓄積待ち ([[price-shock-promote-readiness-2026-06-08]])
- SHORT_SHOCK は grid で promote 級エッジ無し (downside-shock asymmetry) — short 側 deploy は正当に不可

## 関連
- 実装 base: `strategies/hourly/price_shock_reversion_base.py`
- BT runner: tools/price_shock_reversion_bt.py
- Promote/demote 基準: [[price-shock-rev-promote-criteria-2026-05-18]]
