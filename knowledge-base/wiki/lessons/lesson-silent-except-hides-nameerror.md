### [[lesson-silent-except-hides-nameerror]]
**発見日**: 2026-04-22 | **修正**: commit `0981945` (app.py:L7992)

- 問題: `_compute_scalp_signal_v2` 内で `htf_agreement` 変数が未定義のまま L8276/8278/8305 で参照されていた。外側の `try: ... except Exception: pass` が `NameError` を silent に飲み込み、**10 cell すべてで `vwap_mean_reversion` が発火ゼロ**に。
- 症状:
  - 2026-04-22 Scalp 180d BT で EUR_JPY/GBP_JPY/USD_JPY/EUR_USD/GBP_USD/EUR_GBP × {1m, 5m} の **全 10 cell で `vwap_mean_reversion` trades=0**
  - DT 版 365d BT では EUR_JPY N=223 EV+0.672 / GBP_JPY N=267 EV+1.025 と正 EV → Scalp 側だけ異常
  - ログに `NameError: name 'htf_agreement' is not defined` は一切出ていない（silent except に飲まれた）
- 原因:
  - DT 側 `_compute_daytrade_signal_v2` L2074 で `htf_agreement = htf.get("agreement", "mixed")` を定義済み
  - Scalp 側 `_compute_scalp_signal_v2` L7991 で `h4_sc = htf.get("h4", {}).get("score", 0.0)` のみ抽出し、**同じパターンの `htf_agreement` 抽出をコピーし忘れた**
  - silent except が NameError を飲み込んだため、BT/Live で「vwap_mr が発火していない」ではなく「vwap_mr に優位条件が一度も揃わなかった」と誤認していた期間がある
- 修正:
  - `app.py:L7992` に `htf_agreement = htf.get("agreement", "mixed")` 追加（DT と同じパターン）
  - Post-fix Scalp BT で vwap_mr が 4 JPY cell で発火復活（N=36 合計）を確認
- 教訓: **silent except (`except Exception: pass`) は診断情報を消すだけでなく、戦略の「不発」と「ゼロ件」を区別不能にする。BT で trades=0 の cell が戦略仕様に反して多すぎる時は必ず silent except を疑え。**
  - 補足ルール: **類似 signal 関数（DT ↔ Scalp、Scope A ↔ B）で同じ htf/context オブジェクトを使う時、抽出パターンも完全同期させる。片方の変更忘れは silent except で検出困難。**
  - 構造的対策案: BT harness 側で「trades=0 の cell」を警告フラグにする（strategy A vs expected N から outlier 検出）。silent except の内側で最低限 `logger.warning` を残す。
- 関連 lesson:
  - [[lesson-conf-undefined-bug]] — 同種の変数未定義 NameError
  - [[lesson-reactive-changes]] — この発見直前、session 内で「vwap_mr が弱い」と言いかけたが、BT データが不完全だった事実を捉え損ねるところだった
- 関連:
  - [[vwap-mean-reversion]]
  - `knowledge-base/raw/bt-results/bt-scalp-180d-jpy-postfix-2026-04-22.json` (post-fix 実測)
