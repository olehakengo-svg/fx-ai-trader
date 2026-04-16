### lesson-clean-slate-2026-04-16
**発見日**: 2026-04-16 | **修正**: v9.0 (demo_trader.py)

- **問題**: 1,034トレード・edge=-22.3%・Kelly=0.0。システム全体でLiveエッジ未証明
- **根本原因**: 
  1. ExposureManager ghost bug → 大量のエントリーブロック → 偏ったサンプル
  2. SR dict型エラー → dt_sr_channel_reversal がLive無効化
  3. Watchdog _mode_config bug → 30秒毎クラッシュ
  4. FORCE_DEMOTED戦略がデモ実行→aggregate Kellyを汚染
  5. trendline_sweep がELITE_LIVEかつFORCE_DEMOTEDの矛盾
  6. 負EV戦略(bb_rsi N=267 edge=-3.3%)にLOT_BOOST適用
- **修正**: 
  - _FIDELITY_CUTOFF → 2026-04-16（クリーンスレート）
  - trendline_sweep をFORCE_DEMOTEDから除外
  - bb_rsi_reversion, ema_trend_scalp をLOT_BOOSTから除去
- **教訓**: 
  1. **BT正EVはLiveエッジの証明ではない** — BT-Live乖離(Scalp -14〜27pp, DT -5〜10pp)を常に考慮
  2. **複雑な制御レイヤーは副作用を生む** — ELITE/FORCE_DEMOTED/PAIR_PROMOTEDの8層が交差して矛盾
  3. **エンジニアリング的修正よりデータが先** — フィルター追加ではなくクリーンN蓄積が最優先
  4. **aggregate Kelly汚染に注意** — バグ影響下のデータが混入するとKelly Gateが正常に機能しない
