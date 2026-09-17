# Sub 4: 戦略ライブラリ — Scalp / MicroScalp / Hourly

## Scope
- `strategies/base.py:1-49`
- `strategies/scalp/*.py` を横断確認。深掘り: [ema_trend_scalp.py](/Users/jg-n-012/test/fx-ai-trader/strategies/scalp/ema_trend_scalp.py:37), [bb_rsi.py](/Users/jg-n-012/test/fx-ai-trader/strategies/scalp/bb_rsi.py:34), [squeeze.py](/Users/jg-n-012/test/fx-ai-trader/strategies/scalp/squeeze.py:7), [mtf_trend_follow_scalp.py](/Users/jg-n-012/test/fx-ai-trader/strategies/scalp/mtf_trend_follow_scalp.py:47), [mtf_regime_trend_cascade_scalp.py](/Users/jg-n-012/test/fx-ai-trader/strategies/scalp/mtf_regime_trend_cascade_scalp.py:66), [mtf_regime_range_cascade_scalp.py](/Users/jg-n-012/test/fx-ai-trader/strategies/scalp/mtf_regime_range_cascade_scalp.py:48), [__init__.py](/Users/jg-n-012/test/fx-ai-trader/strategies/scalp/__init__.py:43)
- `strategies/micro_scalp/*.py`: [base.py](/Users/jg-n-012/test/fx-ai-trader/strategies/micro_scalp/base.py:1), [tvsm.py](/Users/jg-n-012/test/fx-ai-trader/strategies/micro_scalp/tvsm.py:45), [ofi_mr.py](/Users/jg-n-012/test/fx-ai-trader/strategies/micro_scalp/ofi_mr.py:56), [vbp.py](/Users/jg-n-012/test/fx-ai-trader/strategies/micro_scalp/vbp.py:48)
- `strategies/hourly/*.py`: [__init__.py](/Users/jg-n-012/test/fx-ai-trader/strategies/hourly/__init__.py:19), [donchian_momentum_breakout.py](/Users/jg-n-012/test/fx-ai-trader/strategies/hourly/donchian_momentum_breakout.py:48), [keltner_squeeze_breakout.py](/Users/jg-n-012/test/fx-ai-trader/strategies/hourly/keltner_squeeze_breakout.py:50)
- MTF/ルックアヘッド確認用参照: [modules/regime_classifier.py](/Users/jg-n-012/test/fx-ai-trader/modules/regime_classifier.py:1), [modules/htf_data_source.py](/Users/jg-n-012/test/fx-ai-trader/modules/htf_data_source.py:86), [modules/bt_vec_harness.py](/Users/jg-n-012/test/fx-ai-trader/modules/bt_vec_harness.py:446), [strategies/context.py](/Users/jg-n-012/test/fx-ai-trader/strategies/context.py:103)

## 1. Bugs Found
| # | Severity | File:Line | Description | Root Cause | Suggested Fix |
|---|----------|-----------|-------------|-----------|--------------|
| 1 | Sev1 | `strategies/scalp/__init__.py:92-105`, `strategies/hourly/__init__.py:39-53` | エンジンが `Candidate` 返却後に `SL` だけを ATR floor で拡大し、`TP` と `RR` を再計算しない。戦略内で成立していた RR が live で崩れる。 | Strategy contract が「`evaluate()` が完成済みの `Candidate` を返す」前提なのに、エンジン側が事後ミューテーションしている。BT では個別戦略を直呼びするため、この変形が入らず BT-Live 乖離も発生。 | SL floor は各戦略の `evaluate()` 前提に統一するか、エンジン適用後に `tp`/`rr` を再計算して不適合候補を破棄する。 |
| 2 | Sev2 | `strategies/scalp/mtf_regime_range_cascade_scalp.py:76-82`, `modules/regime_classifier.py:29-35`, `57-82` | `mtf_regime_range_cascade_scalp` の regime gate は「range」ではなく実質 `no_go` を見ている。再有効化すると「moderate_trend 以外すべて」で発火する。 | `REGIME_RANGE = REGIME_NO_GO` の後方互換 alias を、そのまま range 専用戦略で使っている。classifier は現行 binary `{moderate_trend, no_go}` しか返さない。 | この戦略を正式に削除するか、真の range classifier を別名で追加して alias を使わない。 |
| 3 | Sev2 | `strategies/scalp/ema_trend_scalp.py:50`, `102-103`, `200-204`, `243-252` | `ema_trend_scalp` は「強トレンドでは pullback が育たない」と自認しているのに、`ADX>=30` にボーナスを付けて hard-block しない。最悪セルに流量を送る設計。 | エッジ否定を `confidence` penalty にだけ押し込み、発火条件は `ADX>=15` のまま残している。 | `ADX>=30` はボーナスではなく reject、または `modules/regime_classifier` の `moderate_trend` を hard gate に使う。 |
| 4 | Sev2 | `strategies/scalp/squeeze.py:18-72`, `knowledge-base/wiki/syntheses/roadmap-v2.1.md:82-88` | `bb_squeeze_breakout` は pair/TF/side 非依存の 1m 汎用ロジックのまま。roadmap が示す「USD_JPY=5m」「EUR_USD=1m」のエッジを実装していない。 | 強いセル知見を戦略分岐へ落としておらず、負のセルまで同一ロジックで発火する。 | `USD_JPY-5m` と `EUR_USD-1m` を別 entry_type へ分離するか、現行汎用版は停止する。 |
| 5 | Sev3 | `strategies/base.py:30-31`, `strategies/hourly/donchian_momentum_breakout.py:50`, `strategies/hourly/keltner_squeeze_breakout.py:52` | `StrategyBase.mode` の契約コメントは `"scalp" or "daytrade"` だが、hourly 戦略は `"hourly"` を使っている。 | base 契約文書が実装の拡張に追随していない。 | `StrategyBase.mode` のコメント/型期待値を `hourly` 含みに更新。 |

## 2. Structural Issues
1. MTF の look-ahead 自体は概ね抑止されている。live 側 HTF fetch は `complete=False` を破棄して未確定 M5/M15 を落としており、[modules/htf_data_source.py](/Users/jg-n-012/test/fx-ai-trader/modules/htf_data_source.py:89) の実装は妥当。BT 側も `merge_asof(..., direction="backward")` で直近確定 HTF のみを 1m に注入しており、[modules/bt_vec_harness.py](/Users/jg-n-012/test/fx-ai-trader/modules/bt_vec_harness.py:446) との整合はある。
2. ただし MTF cascade の設計意図は live で崩れている。`mtf_regime_trend_cascade_scalp` は 5pip floor と RR floor を内包するのに、ScalperEngine が後段で ATR floor に上書きするため、[mtf_regime_trend_cascade_scalp.py](/Users/jg-n-012/test/fx-ai-trader/strategies/scalp/mtf_regime_trend_cascade_scalp.py:144) の設計 RR が本番では保存されない。
3. `ema_trend_scalp` の負けはセッション偏在が明確。`06a-cell-stats.csv` では `EUR_USD/NY` EV=-1.708pip、`USD_JPY/NY` EV=-1.81pip、`GBP_USD/London` EV=-1.595pip と主要セルがほぼ全面赤字で、プラスは `USD_JPY/Tokyo` の N=6 に限られる ([06a-cell-stats.csv](/Users/jg-n-012/test/fx-ai-trader/knowledge-base/raw/audits/codex-2026-04-30/06a-cell-stats.csv:53), [59](/Users/jg-n-012/test/fx-ai-trader/knowledge-base/raw/audits/codex-2026-04-30/06a-cell-stats.csv:59), [60](/Users/jg-n-012/test/fx-ai-trader/knowledge-base/raw/audits/codex-2026-04-30/06a-cell-stats.csv:60))。戦略内にセッション別制御はなく、`ADX>=15` の広い許容で悪い時間帯も拾う。
4. `bb_rsi_reversion` の aggregate 黒字は session mix に依存しており、安定 edge ではない。`USD_JPY/Tokyo` EV=+2.812、`USD_JPY/London` EV=+1.35 に対し、`USD_JPY/NY` EV=-3.4、`EUR_USD/NY` EV=-4.85 と毒セルがはっきりある ([06a-cell-stats.csv](/Users/jg-n-012/test/fx-ai-trader/knowledge-base/raw/audits/codex-2026-04-30/06a-cell-stats.csv:6), [7](/Users/jg-n-012/test/fx-ai-trader/knowledge-base/raw/audits/codex-2026-04-30/06a-cell-stats.csv:7), [8](/Users/jg-n-012/test/fx-ai-trader/knowledge-base/raw/audits/codex-2026-04-30/06a-cell-stats.csv:8), [3](/Users/jg-n-012/test/fx-ai-trader/knowledge-base/raw/audits/codex-2026-04-30/06a-cell-stats.csv:3))。現コードはこれを session-aware に制御していない。
5. `bb_rsi_reversion` は MR なのに `ADX>=30` をスコア加点しており、[bb_rsi.py](/Users/jg-n-012/test/fx-ai-trader/strategies/scalp/bb_rsi.py:218) と anti-trend penalty の思想 ([226](/Users/jg-n-012/test/fx-ai-trader/strategies/scalp/bb_rsi.py:226)) が内部矛盾している。aggregate が最近崩れやすいのは、この「強トレンド寄せのスコア」と整合する。
6. MicroScalp 群は base 契約順守と look-ahead 回避が比較的きれい。`bars[:-1]` で ATR/分布を作る箇所が多く、[tvsm.py](/Users/jg-n-012/test/fx-ai-trader/strategies/micro_scalp/tvsm.py:59), [ofi_mr.py](/Users/jg-n-012/test/fx-ai-trader/strategies/micro_scalp/ofi_mr.py:89), [vbp.py](/Users/jg-n-012/test/fx-ai-trader/strategies/micro_scalp/vbp.py:66) に即時のルックアヘッド問題は見当たらなかった。

## 3. Losing Edge Analysis
| Strategy | Cell | N | WR | PF | Wilson Lower | Kelly | 負けの帰属 | 調整案 |
|---|---|---:|---:|---:|---:|---:|---|---|
| ema_trend_scalp | Aggregate | 88 | 20.5% | 0.519 | 13.35% | -0.1952 | regime mismatch / signal lag / friction | `ADX>=30` bonus を削除し、`moderate_trend` hard gate 化。London/NY は停止か Shadow 限定。 |
| ema_trend_scalp | USD_JPY × NY | 10 | 10.0% | 0.213 | 1.79% | -0.3694 | session concentration / trend-chase | NY セル撤退。Tokyo 以外はまず停止して再検証。 |
| bb_rsi_reversion | Aggregate | 36 | 44.4% | 2.906 | 29.54% | 0.2915 | aggregate mask。利益は Tokyo/London 偏重で recent は不安定 | 維持ではなく条件付き維持。`USD_JPY Tokyo/London` と `EUR_USD BUY` 以外は縮退。 |
| bb_rsi_reversion | USD_JPY × NY | 5 | 20.0% | 0.224 | 3.62% | -0.6939 | friction 過小評価 / regime mismatch | NY ブロック、少なくとも Shadow 降格。 |
| bb_squeeze_breakout | Aggregate | 17 | 5.9% | 0.053 | 1.05% | -1.0564 | wrong TF / wrong cell mix / breakout false positives | 現行汎用版は撤退。roadmap 準拠の `USD_JPY-5m` / `EUR_USD-1m` に分離しない限り維持不可。 |

## 4. Roadmap Alignment
- Gate 進行を最も阻害しているのは Scalp 側の BT-Live 不整合。とくに engine 後段の SL floor 変形が、勝てる/負ける以前に統計母集団を汚染している。
- 律速要因は Kelly と DD。`ema_trend_scalp` と `bb_squeeze_breakout` は aggregate Kelly が明確に負で、Scalp +200pip/年 の枝に逆寄与している。
- `mtf_regime_trend_cascade_scalp` 自体の設計は roadmap に近い。`15m regime → 5m pullback → 1m execution` の分離、macro gate、complete-bar guard は筋が良い。ただし現状は engine SL floor で設計 RR が壊れるため、修正前は寄与評価不能。
- `mtf_regime_range_cascade_scalp` は撤退が妥当。binary regime 化後に存在意義が薄く、再有効化しても classifier 契約が壊れている。

## 5. Top 3 Action Items (impact 順)
1. `ScalperEngine/HourlyEngine` の post-return SL floor mutation を廃止または TP/RR 再計算に変更 — Impact: BT-Live 統計汚染の除去、cascade 系の真の性能測定が可能 — Confidence: high
2. `ema_trend_scalp` を `moderate_trend` hard gate 化し、少なくとも London/NY を停止 — Impact: N 最大の出血源を即止血 — Confidence: high
3. `bb_squeeze_breakout` を現行汎用版から撤退し、roadmap 記載の pair×TF 専用 variant に再設計 — Impact: 負EV 戦略の整理と Scalp枝の再建 — Confidence: high

## 6. Out-of-Scope Findings (オプション)
- `SignalContext`/HTF 注入まわりの未確定足処理は、今回見た範囲では live/BT とも大きな look-ahead バグは見当たらなかった。問題は「未確定足」より「確定後に SL/TP 契約を壊している」点にある。
- `bb_rsi_reversion` の score は strategy 内で強トレンド側へ寄る一方、別分析では score inverse 傾向が記録されている。selection layer まで含めた再監査価値は高いが、これは本スコープ外。
