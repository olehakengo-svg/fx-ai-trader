# Grail #19 ny_close_reversal 撤去 (rule:R2, 2026-07-31)

## Status
**EXECUTED** — `_GRAIL_CANDIDATES` から `ny_close_reversal` を除外 + `_check_grail_filter` の Grail #19 分岐撤去。
Regression pin: `tests/test_grail19_ny_close_removal_pin.py`

## 分類: Rule 2 (Fast & Reactive — 損失停止)
- 対象は **live 送信経路の停止のみ**。shadow emit は継続 (4原則-3: 静的時間ブロックは Shadow に適用しない)
- 前例: Grail #2 vix_carry_unwind × London×squeeze 撤去 (2026-06-15, rule:R2)

## 動機 (データ駆動)
2026-07-31 quant-eval (shadow 含む post-cutoff 全数 14,329 行の 3 バケット監査、
`raw/trade-logs/quant-eval-2026-07-31.md`) で 7 月 live 出血経路として特定。

### 証拠
| 系列 | N | WR | PnL | 備考 |
|---|---|---|---|---|
| live (post-cutoff, oanda_trade_id≠'') | 4 | **0%** (0W/3L/1BE) | **−9.7p** | 全て Grail #19 窓 (17-22 UTC)。07-06 −2.4 / 07-08 −7.9 / 07-15 +0.1 |
| shadow USD_JPY | 7 | 33% | −4p | |
| shadow GBP_USD | 9 | 50% | −41p | |

- **登録根拠が N=4** (2026-04-25 TP-hit deep-mining、Wlo=51% EV=+2.15) — Rule 2 の
  「数トレード〜N=10 で即断可」は登録根拠と同粒度であり非対称性なし
- 登録後 3 ヶ月の forward 実績が live/shadow とも負 = クラスタは curve-fit だったと判断
- 7 月 live 反実仮想: 修正済みバグ経路 (07-01/02 watchdog 再武装) 除去後の −52.1p のうち、
  ny_close −10.2p + vix −34.3p を除くと **−7.6p** — M1 (月次符号転換) の主要残存出血源

## 整合性チェック (Rule 共通要件)
- KB 参照: [[tp-hit-deep-mining-grail-2026-04-25]] (登録元) / [[vix-carry-grail-removal-overlap-1000u-2026-06-15]] (前例) / tier-master (ny_close は PP/EL 未指定 = Grail が唯一の live 経路)
- 既存 Bonferroni 有意エッジとの衝突: なし (ny_close はどの有意セルにも不在)
- 残存 Grail: #1 ema200_trend_reversal (live N=4 WR25% −17.5p ⚠️ 監視強化、shadow セルは
  BEV 対比 Bonferroni PASS p=2.6e-6 で thesis 自体は生存) / #4 vol_surge_detector
  (live N=26 −9.4p、EV −0.36 微負 — 次回 eval で N≥30 到達時に再判定)

## 再 live 化条件 (R1)
forward shadow N≥30 ∧ Wilson_lo > BEV_WR(USD_JPY)=34.4% ∧ Bonferroni PASS ∧ pre-reg LOCK + user 承認

## Related
- [[quant-eval-2026-07-31]] (raw/trade-logs/)
- [[tp-hit-deep-mining-grail-2026-04-25]] / [[tier-master]]
