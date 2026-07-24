# WS3 round-2 §2(ii) 探索窓 first-touch EV スクリーン (機械計算、rule:R3)

- 生成: 2026-07-10T06:52:58.488694+00:00 / ws3-round2-explore-prereg-2026-07-10.md §2(ii) (origin/main, 2026-07-10 改訂 = round-2 スキャン結果観測前の a priori 変更)
- engine: tools/ws3_stage2_barrier_sim.py first_touch() 同形移植 (SL 優先 tie-break / timeout=最終バー close / BE・Trail なし)。stage-2 の結果数値は不参照 (ツールのみ流用)
- 窓: 探索窓 2025-07-08〜2026-06-07 (round-1 checkpoint 母集団と同一) / OOS 非接触 / 摩擦 (往復 pips): EUR_USD 2.0, USD_JPY 2.14, GBP_USD 4.53, AUD_JPY 3.125, GBP_JPY 4.53
- grid: TP=round(pct(mfe_H,{50,75,90})) / SL=round(pct(mae_H,{50,75,90})) per-cell、H=primary horizon、np.percentile linear、SL 下限1pip
- 通過条件: best 摩擦調整 EV>0 ∧ 隣接 (Manhattan 距離1、存在分) の過半 EV>0
- ep 復元検証不一致: 0 entries (許容 0.02p)

## sr_fib_confluence×GBP_USD×SELL (持続型, hold=96bars, N=95, friction=4.53)
- grid: TP=[47, 76, 111] / SL=[28, 62, 81] (凍結)
- best = tp111_sl62 EV_adj **8.879** / 隣接正 3/3 → **✅ 通過**

| config | EV_adj | TP% | SL% | TO% |
|---|---|---|---|---|
| tp47_sl28 | 2.845 | 0.4 | 0.474 | 0.126 |
| tp47_sl62 | 4.593 | 0.474 | 0.221 | 0.305 |
| tp47_sl81 | 4.575 | 0.474 | 0.074 | 0.453 |
| tp76_sl28 | 5.846 | 0.221 | 0.495 | 0.284 |
| tp76_sl62 | 7.426 | 0.242 | 0.242 | 0.516 |
| tp76_sl81 | 7.008 | 0.242 | 0.095 | 0.663 |
| tp111_sl28 | 7.458 | 0.095 | 0.505 | 0.4 |
| tp111_sl62 | 8.879 | 0.105 | 0.253 | 0.642 |
| tp111_sl81 | 8.262 | 0.105 | 0.105 | 0.789 |

## vol_spike_mr×USD_JPY×BUY (減衰型, hold=24bars, N=39, friction=2.14)
- grid: TP=[29, 43, 71] / SL=[20, 32, 63] (凍結)
- best = tp71_sl63 EV_adj **4.296** / 隣接正 2/2 → **✅ 通過**

| config | EV_adj | TP% | SL% | TO% |
|---|---|---|---|---|
| tp29_sl20 | 0.798 | 0.385 | 0.462 | 0.154 |
| tp29_sl32 | 2.432 | 0.462 | 0.256 | 0.282 |
| tp29_sl63 | 2.442 | 0.487 | 0.103 | 0.41 |
| tp43_sl20 | 0.596 | 0.179 | 0.462 | 0.359 |
| tp43_sl32 | 2.681 | 0.205 | 0.256 | 0.538 |
| tp43_sl63 | 3.05 | 0.231 | 0.103 | 0.667 |
| tp71_sl20 | 1.101 | 0.051 | 0.462 | 0.487 |
| tp71_sl32 | 3.904 | 0.077 | 0.256 | 0.667 |
| tp71_sl63 | 4.296 | 0.077 | 0.103 | 0.821 |

## sr_fib_confluence×EUR_USD×SELL (持続型, hold=96bars, N=99, friction=2.0)
- grid: TP=[34, 53, 70] / SL=[23, 42, 74] (凍結)
- best = tp53_sl42 EV_adj **6.631** / 隣接正 4/4 → **✅ 通過**

| config | EV_adj | TP% | SL% | TO% |
|---|---|---|---|---|
| tp34_sl23 | 3.131 | 0.434 | 0.444 | 0.121 |
| tp34_sl42 | 4.519 | 0.485 | 0.232 | 0.283 |
| tp34_sl74 | 3.248 | 0.495 | 0.071 | 0.434 |
| tp53_sl23 | 4.179 | 0.192 | 0.465 | 0.343 |
| tp53_sl42 | 6.631 | 0.232 | 0.232 | 0.535 |
| tp53_sl74 | 5.553 | 0.242 | 0.071 | 0.687 |
| tp70_sl23 | 3.895 | 0.091 | 0.475 | 0.434 |
| tp70_sl42 | 5.427 | 0.101 | 0.242 | 0.657 |
| tp70_sl74 | 3.6 | 0.101 | 0.081 | 0.818 |

## vsg_jpy_reversal×GBP_JPY×SELL (減衰型, hold=24bars, N=106, friction=4.53)
- grid: TP=[35, 57, 86] / SL=[24, 43, 64] (凍結)
- best = tp35_sl64 EV_adj **1.167** / 隣接正 2/2 → **✅ 通過**

| config | EV_adj | TP% | SL% | TO% |
|---|---|---|---|---|
| tp35_sl24 | -1.021 | 0.396 | 0.462 | 0.142 |
| tp35_sl43 | 0.066 | 0.453 | 0.217 | 0.33 |
| tp35_sl64 | 1.167 | 0.481 | 0.094 | 0.425 |
| tp57_sl24 | -0.983 | 0.226 | 0.491 | 0.283 |
| tp57_sl43 | 0.013 | 0.245 | 0.226 | 0.528 |
| tp57_sl64 | 0.86 | 0.255 | 0.104 | 0.642 |
| tp86_sl24 | -3.014 | 0.057 | 0.491 | 0.453 |
| tp86_sl43 | -1.471 | 0.075 | 0.226 | 0.698 |
| tp86_sl64 | -0.351 | 0.085 | 0.104 | 0.811 |

## turtle_soup×GBP_USD (持続型, hold=96bars, N=40, friction=4.53)
- grid: TP=[44, 60, 94] / SL=[31, 60, 83] (凍結)
- best = tp44_sl83 EV_adj **2.24** / 隣接正 0/2 → **❌ 脱落**

| config | EV_adj | TP% | SL% | TO% |
|---|---|---|---|---|
| tp44_sl31 | -0.227 | 0.425 | 0.4 | 0.175 |
| tp44_sl60 | -2.295 | 0.475 | 0.225 | 0.3 |
| tp44_sl83 | 2.24 | 0.5 | 0.05 | 0.45 |
| tp60_sl31 | -3.418 | 0.225 | 0.475 | 0.3 |
| tp60_sl60 | -4.863 | 0.25 | 0.25 | 0.5 |
| tp60_sl83 | -2.34 | 0.25 | 0.075 | 0.675 |
| tp94_sl31 | -2.395 | 0.1 | 0.5 | 0.4 |
| tp94_sl60 | -4.318 | 0.1 | 0.25 | 0.65 |
| tp94_sl83 | -1.795 | 0.1 | 0.075 | 0.825 |

## dt_sr_channel_reversal×GBP_USD×SELL (持続型, hold=96bars, N=36, friction=4.53)
- grid: TP=[46, 68, 77] / SL=[33, 59, 79] (凍結)
- best = tp46_sl33 EV_adj **0.598** / 隣接正 0/2 → **❌ 脱落**

| config | EV_adj | TP% | SL% | TO% |
|---|---|---|---|---|
| tp46_sl33 | 0.598 | 0.444 | 0.444 | 0.111 |
| tp46_sl59 | -2.338 | 0.472 | 0.25 | 0.278 |
| tp46_sl79 | 0.542 | 0.5 | 0.111 | 0.389 |
| tp68_sl33 | -1.374 | 0.194 | 0.5 | 0.306 |
| tp68_sl59 | -4.327 | 0.194 | 0.25 | 0.556 |
| tp68_sl79 | -0.836 | 0.222 | 0.111 | 0.667 |
| tp77_sl33 | -2.499 | 0.056 | 0.5 | 0.444 |
| tp77_sl59 | -5.452 | 0.056 | 0.25 | 0.694 |
| tp77_sl79 | -2.33 | 0.056 | 0.111 | 0.833 |

## dt_sr_channel_reversal×GBP_JPY×BUY (持続型, hold=96bars, N=77, friction=4.53)
- grid: TP=[67, 105, 127] / SL=[51, 83, 132] (凍結)
- best = tp67_sl83 EV_adj **13.264** / 隣接正 3/3 → **✅ 通過**

| config | EV_adj | TP% | SL% | TO% |
|---|---|---|---|---|
| tp67_sl51 | 7.591 | 0.468 | 0.377 | 0.156 |
| tp67_sl83 | 13.264 | 0.506 | 0.156 | 0.338 |
| tp67_sl132 | 11.719 | 0.506 | 0.065 | 0.429 |
| tp105_sl51 | 3.502 | 0.221 | 0.455 | 0.325 |
| tp105_sl83 | 9.462 | 0.247 | 0.208 | 0.545 |
| tp105_sl132 | 6.664 | 0.247 | 0.091 | 0.662 |
| tp127_sl51 | 2.912 | 0.078 | 0.455 | 0.468 |
| tp127_sl83 | 9.443 | 0.104 | 0.208 | 0.688 |
| tp127_sl132 | 6.644 | 0.104 | 0.091 | 0.805 |

## sr_fib_confluence×AUD_JPY×SELL (減衰型, hold=24bars, N=119, friction=3.125)
- grid: TP=[24, 43, 74] / SL=[19, 34, 52] (凍結)
- best = tp24_sl19 EV_adj **-1.051** / 隣接正 0/2 → **❌ 脱落**

| config | EV_adj | TP% | SL% | TO% |
|---|---|---|---|---|
| tp24_sl19 | -1.051 | 0.429 | 0.412 | 0.16 |
| tp24_sl34 | -1.622 | 0.487 | 0.218 | 0.294 |
| tp24_sl52 | -1.585 | 0.504 | 0.076 | 0.42 |
| tp43_sl19 | -1.675 | 0.176 | 0.445 | 0.378 |
| tp43_sl34 | -1.891 | 0.218 | 0.235 | 0.546 |
| tp43_sl52 | -1.484 | 0.235 | 0.076 | 0.689 |
| tp74_sl19 | -2.098 | 0.067 | 0.454 | 0.479 |
| tp74_sl34 | -2.992 | 0.076 | 0.235 | 0.689 |
| tp74_sl52 | -2.063 | 0.092 | 0.076 | 0.832 |

## 結果: 通過 5/8

- ✅ sr_fib_confluence×GBP_USD×SELL
- ✅ vol_spike_mr×USD_JPY×BUY
- ✅ sr_fib_confluence×EUR_USD×SELL
- ✅ vsg_jpy_reversal×GBP_JPY×SELL
- ✅ dt_sr_channel_reversal×GBP_JPY×BUY

## 親セッション裁定の記録 (2026-07-10、EV スクリーン実行前に受領)

1. **turtle_soup×GBP_USD: 候補残置 (m=8 のまま §2(ii) に投入)** — falsified 系統「水平 sweep&reclaim」は探索ハーネス仮説 (ライン接触→方向) の再試行禁止であり、既存 production entry_type の非対称計測は estimand 相違 (stage-1 の lin_reg_channel 前例と同型裁定)。**OOS verdict にこの裁定を明記すること**。※結果として本セルは §2(ii) EV スクリーンで機械的に脱落 (孤立格子点、隣接正 0/2)
2. **dt_bb_rsi_mr 全除外 (保守的掃引): 承認**
3. **sr_fib_confluence SELL ×3 の相関クラスタ懸念: OOS で判別** — §2b に記録 (下記提案文に含む)

## ep 復元の方法論 (a priori 宣言、fail-loud 検証済み)

checkpoint entries は fill 価格 (ep) を持たないため、round-1 forward 計測の恒等式
ep = extremum(h96 窓) ∓ mfe_96·pip から復元した。独立復元 (MAE 側) との一致 +
h24 mfe/mae の再計算照合 (許容 0.02 pip) を全 616 entries に適用し**不一致 0** —
これは同時に、使用 parquet の履歴バーが round-1 実行時と同一であることの機械検証でもある。

## (v') pre-reg DRAFT §2b への追記提案 — 改訂版 (§2(ii) 反映。ws3_round2_scan_2026_07.md §(v) を置換する)

```markdown
## 2b. 候補セット (診断 + §2(ii) EV スクリーン 2026-07-10 実行済み、m=5 — self-LOCK 対象、以後変更禁止)

- 1次スクリーン (§2(i)): raw/bt-results/ws3_round2_scan_2026_07.{json,md} — 8 セル
  (選抜規則 N≥30 ∧ (ratio_h24≥1.3 ∪ 持続型)、除外機械適用済み)
- 2次スクリーン (§2(ii)): raw/bt-results/ws3_round2_ev_screen_2026_07.{json,md} —
  探索窓 first-touch EV (stage-2 sim 同形、SL 優先、per-pair 摩擦控除) で 5/8 通過。
  脱落 = turtle_soup×GBP_USD (孤立格子点 0/2) / dt_sr_channel_reversal×GBP_USD×SELL
  (孤立格子点 0/2) / sr_fib_confluence×AUD_JPY×SELL (best EV −1.05 < 0)

| # | cell | 型 (固定) | 探索 ratio (h24→h96) | N | Primary H | 凍結 grid TP/SL | best (探索窓 EV) | 隣接正 |
|---|---|---|---|---|---|---|---|---|
| 1 | sr_fib_confluence×GBP_USD×SELL | 持続 | 1.18→1.66 | 95 | h96 | [47,76,111]/[28,62,81] | tp111_sl62 (+8.88) | 3/3 |
| 2 | vol_spike_mr×USD_JPY×BUY | 減衰 | 1.49→1.38 | 39 | h24 | [29,43,71]/[20,32,63] | tp71_sl63 (+4.30) | 2/2 |
| 3 | sr_fib_confluence×EUR_USD×SELL | 持続 | 1.36→1.49 | 99 | h96 | [34,53,70]/[23,42,74] | tp53_sl42 (+6.63) | 4/4 |
| 4 | vsg_jpy_reversal×GBP_JPY×SELL | 減衰 | 1.48→1.23 | 106 | h24 | [35,57,86]/[24,43,64] | tp35_sl64 (+1.17) | 2/2 |
| 5 | dt_sr_channel_reversal×GBP_JPY×BUY | 持続 | 0.97→1.33 | 77 | h96 | [67,105,127]/[51,83,132] | tp67_sl83 (+13.26) | 3/3 |

- 型・primary horizon・**grid は探索標本で凍結** — OOS での horizon 選び直し・再アンカー禁止 (§3(B))
- 摩擦 (往復、判定値、凍結): EUR_USD 2.00 / USD_JPY 2.14 / GBP_USD 4.53 / AUD_JPY 3.125 /
  GBP_JPY 4.53 (理論テーブル不在のため GBP_USD 同値の保守採用 — a priori 宣言)
- 探索窓 EV は選抜にのみ使用 (選択バイアス込み — OOS §3(B) が確認的根拠)
- **相関クラスタ記録**: sr_fib_confluence×SELL が 2/5 (GBP_USD/EUR_USD)。共通 USD 方向
  レジームの可能性は OOS で判別。stage-2 移行時は同一戦略クラスタとして barrier 設計を共通化
- **裁定記録**: turtle_soup×GBP_USD は親裁定 (2026-07-10) で falsified 非該当として
  §2(ii) に投入されたが EV スクリーンで機械的脱落 — OOS には進まない。
  dt_bb_rsi_mr 系統の保守的全除外は親承認済み
- 軸(b) EUR_GBP は BT 最小サンプルガード (<20 trades/365d) で候補到達不能 (診断 md §(i))
- OOS 判定 = §3 の 2 レグ (A: ratio BH-FDR **m=5** / B: 凍結 grid の OOS first-touch EV、
  best 3×3 近傍平均 ≥ +0.5 p/t ∧ 隣接過半 EV>0) + ナイフエッジ3点検査。
  OOS-1 窓 (2024-07-07〜2025-07-07) の再利用 = 2 回目 (per-cell 未使用のため有効)
```
