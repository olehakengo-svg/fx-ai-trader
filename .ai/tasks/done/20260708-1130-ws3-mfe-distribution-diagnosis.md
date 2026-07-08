---
id: 20260708-1130-ws3-mfe-distribution-diagnosis
title: "[v2.3 WS3/R3] MFE 分布診断 — 現行シグナル母集団に「20p 走る場所」は存在するか"
owner: claude
status: done
priority: P1
created_at: 2026-07-08T11:30:00+0900
roadmap_gate: "v2.3 WS3 (T2 FAIL 後の主戦線)。R3 純診断 — live パラメータ変更なし。促進判断は別途 R1 pre-reg"
rule: R3
prereq_artifacts:
  - knowledge-base/wiki/decisions/exit-repair-tp-sl-prereg-2026-07-07.md   # §8 verdict (FAIL → WS3 全振り)
  - knowledge-base/wiki/analyses/friction-adjusted-ev-map-2026-07-07.md    # 優先母集団 (§5-3)
  - knowledge-base/wiki/analyses/payoff-asymmetry-diagnosis-2026-07-07.md  # MFE 帯 4-6p の live 実測
related:
  - knowledge-base/wiki/syntheses/roadmap-v2.3-payoff-friction-repair.md
---

# 0. なぜこのタスクか

T2 exit-repair FAIL (2026-07-08) により pre-reg §4 の固定分岐が発動: 黒字化の唯一の経路 =
「20p 走る場所への entry 張り替え」(WS3)。その初手は **現行シグナル母集団の entry 後
MFE 分布の網羅計測** — exit 設計から独立に「entry の後に価格がどれだけ走るか」を測り、
(a) 現行母集団に MFE ≳15-20p (摩擦の4-8倍) のセルが存在するか
(b) 存在するならどの条件 (pair / session / HTF / regime) が MFE を延伸するか
(c) 全滅なら新シグナル系統の探索へ — の分岐を確定する。

# 1. 設計 (R3 診断 — 判定閾値は事前固定しない、分布の記述が目的)

- **母集団**: 本番 signal 関数 (backtest_mode=True) の 365d BT baseline (TP/SL 倍率なし) が
  生成する全エントリー (全 entry_type × 6 pair: GBP_USD/EUR_USD/USD_JPY/EUR_JPY/GBP_JPY/AUD_JPY
  — parquet 鮮度 OK の pair のみ。診断窓 2026-06-07〜 は exit-repair と同基準で除外)
- **計測**: 各エントリーから forward H ∈ {6, 12, 24, 48, 96} bars (15m) の
  MFE = max favorable excursion (BUY: max(High)−ep / SELL: ep−min(Low))、MAE 同型。
  ep は摩擦込み fill 価格 (BT と同一)。exit 設計非依存 (TP/SL/trail/timeout を見ない)
- **出力**: entry_type × pair 別に N / MFE p50/p75/p90 (pips) / P(MFE≥15p) / P(MFE≥20p) /
  MAE p50、horizon 別。friction-adjusted-ev-map の「高 gross WR × 深 net−」群
  (gbp_deep_pullback / sr_anti_hunt_bounce / trendline_sweep) を重点比較
- **ツール**: `tools/ws3_mfe_scan.py` (grid BT インフラ流用、read-only)
- **成果物**: `raw/bt-results/ws3_mfe_scan_2026_07.json` + `analyses/ws3-mfe-distribution-2026-07-08.md`

# 2. 注意 (lessons)

- ペア×戦略粒度で見る (集計は相殺する)。aggregate だけの結論禁止
- MFE はバー粒度 (tick 未満は不可視) — live 診断 (payoff-asymmetry §1) との比較時に明記
- これは screen であり promote 判定ではない。有望セルが出ても R1 pre-reg (TV canon / Bonferroni /
  診断窓除外) を経ずに live 化しない。falsified 6系統の再試行禁止
- 「20p 走る」の分岐判定は本診断の分布を見た上で次の pre-reg で事前固定する (ここで閾値を
  fit しない — カーブフィッティング禁止)

# 3. Claude Review (2026-07-09)

## Claude Review

- **実行**: claude 直接実行 (owner 通り)。`tools/ws3_mfe_scan.py` — 365d baseline (V2 parity 3flag、診断窓除外) 6 pair、N=6,995 entries / 104 cells、forward H∈{6,12,24,48,96} bars の MFE/MAE を exit 非依存で計測。初回 run はセッション再起動で kill → per-pair checkpoint 追加後に完走
- **主要所見の検証**: (1) MFE 絶対量は豊富 (h24 p50 15-30p) — live 診断の「winners MFE 5.18p」は exit 打ち切りアーティファクトと確定 (診断 §10-2 caveat と整合) (2) MFE/MAE 比 中央値 0.88 (N≥20 の 79 cells) = 母集団に方向性なし — T2 FAIL・IC null 履歴・負 EV と機構的に整合 (3) ratio≥1.3 は 7/79 のみ、うち horizon 持続型 2 (lin_reg_channel×EUR_USD, dt_fib_reversal×USD_JPY)
- **規律チェック**: 閾値 fit なし (記述のみ)、事後選択セルの promote 禁止を文書に明記、falsified 系 (channel IC null) との仮説差異を注記。成果物 = analyses/ws3-mfe-distribution-2026-07-08.md + raw/bt-results/ws3_mfe_scan_2026_07.{json,md}
- **帰結**: WS3 選抜基準を「MFE 絶対量」→「MFE/MAE 非対称 + 持続性」へ改訂 (roadmap 反映済み)。次 = 候補 7+2 cells の OOS 検証 pre-reg 起案
