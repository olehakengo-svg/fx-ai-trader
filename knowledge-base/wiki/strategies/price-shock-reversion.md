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
- **🎉 2026-07-29 04:44 UTC — 3.5 ヶ月ぶりの初 live fill (経路検証全クリーン)**: aud_jpy セルが OANDA **#549235** BUY 1000u @113.466 (slip +0.8p / spread 1.6p)。実測確認済み: ① `[SHIELD] Aggregate Kelly gate BYPASS` ログ実射 (累積 Kelly −0.343 でも 1000u 契約で live 維持 = D-c-1 carve-out 作動) ② broker 側 STOP_LOSS #549237 @112.467 (=台帳 2×ATR SL) / TAKE_PROFIT #549236 付帯 (二層防御) ③ 同一バー重複シグナルは dedup/slot 遮断 ④ BE_LOCK/ATR-BE/trail 不作動 — **fill は §7 免除 deploy (04:22 UTC) の後 = 完全な LOCK 設計 estimand 下の第 1 号**。horizon close 16:44 UTC 予定、判定は registry `ps-carveout-firstweek-regate` (08-11)
- 執行 note: broker TP は Quick-Harvest ×0.85 で 988p→840p に短縮された注文が付く (horizon 12h では実質非拘束 — 第 5 のオーバーレイだが binding しない。§7 スコープ外として記録のみ)
- **live 実績 (2026-08-03 時点): N=2, cum −122.6p** — #549235 +0.6p (07-29 horizon) / #549250 **−123.2p (07-31 horizon, slip 0.9p)**。後者は JPY 急騰局面 (AUD_JPY 114→110.7) で 1%-tile shock BUY が逆行継続したもの — SL 2×ATR は crash で 393.6p に拡大しており horizon exit が先行 (**設計どおりの負け方**、クリップ・逸脱なし)。同期間 shadow は +60.9 (07-30 horizon) / −126.5 (07-31 WEEKEND_CLOSE)。watchdog 全席 WATCH 継続、正式判定 = firstweek-regate 08-11
- **2026-07-28 live 再武装** (PR #119): `_is_xau_inst` バグ (2026-04-10〜) で 3.5 ヶ月 live 送信死 → 修復 + user 決裁「7 席全部再武装」で 5 セル live 送信可 ([[lesson-preserve-sltp-unboundlocal-2026-07-28]])。実効化は Track C D-c-1 carve-out (PR #124)
- ✅ **exit オーバーレイ逸脱 → 2 段階で是正完了 (2026-07-28)**: BE_LOCK A/B + ATR-BE/trail + SIGNAL_REVERSE が本 family に適用され LOCK 済み Exit 設計 (horizon or 2×ATR のみ) と乖離していた。第 1 段 = user 決裁 (同日) で **BE_LOCK 5 種 OFF (trig 0.0) 執行** ([[preserve-exit-overlay-2026-07-28]] §5 決裁記録、PR #124/#126)。第 2 段 = horizon-exit counterfactual 定量化 (同 §6) 完了後の user「進めて」決裁で **ATR-BE/trail + SIGNAL_REVERSE も免除 = 案(b) 完全整合** (同 §7 執行記録)。**是正以前の close_reason=`sl_2atr` はクリップ発火を含むラベル汚染あり** (歴史系列の解釈時に注意、遡及換算は `tools/price_shock_exit_counterfactual.py`)。WEEKEND_CLOSE のみ既知の残存逸脱 (§7)
- ⚠️ **供給スロットリング発覚 (2026-07-29)**: HourlyEngine の winner-take-all × score 非対称 (DMB 5.0+ vs ps 1.0、crash bar で構造的共起) により family 供給が design の **~31%** (eur_aud/usd_cad は 0%)。「rare-event による N 蓄積待ち」の従来解釈は不正確 — root cause / 修正パケット (user R1 決裁待ち) = [[price-shock-seat-supply-audit-2026-07-29]]
- 2026-06-08 再監査: 5 戦略とも正常稼働、rare-event (発火 ~0.33%/bar) による Shadow N 蓄積待ち ([[price-shock-promote-readiness-2026-06-08]]) — ※上記のとおり実際は選抜層で抑制されていた
- SHORT_SHOCK は grid で promote 級エッジ無し (downside-shock asymmetry) — short 側 deploy は正当に不可

## 関連
- 実装 base: `strategies/hourly/price_shock_reversion_base.py`
- BT runner: tools/price_shock_reversion_bt.py
- Promote/demote 基準: [[price-shock-rev-promote-criteria-2026-05-18]]
