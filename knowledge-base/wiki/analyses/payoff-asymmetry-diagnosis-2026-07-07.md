# Payoff 非対称性診断 — clean live 30d payoff 0.27 の要因分解 (2026-07-07)

**Status**: 診断確定 (4サブ分析全て敵対的検証済 ✅、訂正反映済)。実装は未着手 — R1 レバーは §9 に候補列挙のみ、R2 候補は §7。
**Window**: entry_time ∈ [2026-06-07, 2026-07-08)。draft 窓 (06-06〜07-07) と行集合完全一致 (N=93、境界日 clean live 約定ゼロ)。draft 時点実測 (07-06 fetch) の 92件/−242.6p との差分は fetch 後クローズの USD_JPY SELL −2.4p 1件のみ。
**Data**: Render 本番 API snapshot 2026-07-07 (demo_trades 12,372行、max entry 07-07T04:24)。
**clean live 定義**: `oanda_trade_id 非空 ∧ status='CLOSED' ∧ pnl_pips 非NULL ∧ 非XAU ∧ COALESCE(dedup_violation,0)≠1`
**関連**: [[roadmap-v2.3-payoff-friction-repair]] / [[friction-analysis]] / MEMORY `project_be_trail_inflates_python_bt_wr` / `project_roadmap_v23_draft`

## 1. TL;DR

payoff 0.274 (avgW +2.40p / avgL −8.75p、N=93、WR 54.8%、30d net −245.0p) は**設計の非対称ではなく、100% 執行 (exit 実現) 側で発生**している。設計 R:R は条件付き 2.667 (中央値 1.96) と有利側。

厳密恒等式: **0.274 = 設計 2.667 × 勝ち側 capture 0.0944 ÷ 負け側 realize 0.9185** (log gap −2.274 の 103.7% が勝ち側、負け側は −3.7% = 改善方向)。

要因寄与順:
1. **(a) 早利確 = 勝ち側 capture 崩壊** (log share 103.7%) — 2層構造:
   - **follow-through 不足 (gap の 69.9%)**: winners MFE 平均 5.18p は設計 TP 平均 25.4p の 20%。TP 到達 3/93 (3.2%)、MFE≥TP半分も 9件のみ。設計 TP は実走距離の約5倍遠い。capture は TP 距離と逆相関 (TPd 5p→0.39、48p→0.03)。
   - **trail/BE 返上 (gap の 33.9%)**: 実現は MFE の 46%。**未捕獲 142.5p/30d、全額 OANDA_SL_TP 出口 (N=38) に集中**。完全回収でも payoff 0.59 / −102.5p 止まり。
2. **(d) close_reason 構造** — (a) の機構的実体 (独立加算なし)。BE+trail server stop が勝ち38件を med +1.8p (avg +2.08p、保有中央値9分) で確定。<3p スクラッチ 46/51勝 = gross win 122.3p の 64%。**WR 54.8% は BE/trail アーティファクト** (BT WR +20pp 水増しの live 鏡像)。
3. **(c) 摩擦** — 非対称成分 17.7p/30d = net 損失の 7% → **「負けだけ滑る」仮説は棄却** (55% が単一 8.3p ギャップ)。ただし対称摩擦の水準効果は大: gross payoff 0.44〜0.87 → net 0.27 (劣化の4〜7割、摩擦モデル依存)。
4. **(b) SL遠置き/負け引っ張り** — **棄却**。負け MFE med 0.1p / MFE≥3p 4.8%、loss realize 0.92、SL slip 平均 +0.35〜0.43p (med +0.10)。BE 移動救済は楽観 +24.9p (72% 単一トレード) / 悲観 −47.1p で**期待値マイナスの可能性が高くレバー化不適**。ただし「SL ~9p vs winners MFE 天井 ~5p の R:R ミスマッチ」は設計問題として実在。

**両レバー完璧でも −77.6p (WR 54.8% の分岐 payoff 0.824 未達)** — 修理は exit 微調整ではなく「TP/SL を実走距離 (MFE 帯 4–6p) に整合させるか、5p しか走らないシグナルを 20p 走る場所に張り替えるか」の構造選択。v2.3 の reframe「正の摩擦調整EVセルの不在」と整合。早利確 vs 負け引っ張りの pip 寄与比 = **142.5 : 24.9 ≈ 5.7 : 1**。

## 2. close_reason 分布 (clean live 30d, N=93)

| close_reason | N | WR% | mean pnl | sum | mean win | mean loss | 備考 |
|---|---|---|---|---|---|---|---|
| OANDA_SL_TP | 42 | 90.5 | +0.94 | +39.5 | +2.08 | −9.85 | close_analysis 全NULL (server側)。勝ち38件 = BE+ trail stop (med +1.8p/9分)、負け4件 = 設計SLフル |
| SL_HIT | 41 | 24.4 | −6.80 | −278.9 | +2.11 | −9.68 | 負け31件 = 逆行SL (30/31 が close_analysis「逆行SL」)、勝ち10件 = BE移動後ローカルstop |
| SIGNAL_REVERSE | 6 | 0.0 | −4.05 | −24.3 | — | −4.05 | SLd の ~30–34% で早期カット (損失縮小に寄与) |
| TP_HIT | 3 | 100.0 | +7.43 | +22.3 | +7.43 | — | 設計TP到達 3.2% |
| TIME_DECAY_EXIT | 1 | 0.0 | −3.60 | −3.6 | — | −3.60 | |
| **TOTAL** | **93** | **54.8** | **−2.63** | **−245.0** | **+2.40** | **−8.75** | **payoff 0.274** |

## 3. 設計 vs 実現 (entry_type 別、中央値 pips)

| entry_type | N | 設計SLd | 設計TPd | 設計RR | win capture | loss realize | 実現payoff | EV p/t |
|---|---|---|---|---|---|---|---|---|
| trendline_sweep | 19 | 11.1 | 31.1 | 2.36 | 0.053 | 1.064 | 0.15 | −2.35 |
| wick_imbalance_reversion | 12 | 9.5 | 22.6 | 2.49 | 0.078 | 0.778 | 0.25 | −3.91 |
| bb_rsi_reversion | 11 | 4.2 | 5.0 | 1.20 | 0.387 | 1.006 | 0.59 | +0.82 |
| zz_pivot_v60_sr | 10 | 10.7 | 48.2 | 4.78 | 0.033 | 0.802 | 0.18 | −2.53 |
| vix_carry_unwind | 10 | 11.7 | 25.8 | 2.21 | 0.044 | 0.830 | 0.19 | −1.90 |
| dt_sr_channel_reversal | 9 | 10.0 | 16.2 | 1.81 | 0.464 | 1.015 | 0.82 | −1.87 |
| vsg_jpy_reversal | 7 | 12.4 | 18.8 | 1.69 | 0.100 | 1.025 | 0.18 | −1.96 |
| **ALL** | **93** | **9.6** | **21.5** | **1.96** | **0.094** | **0.919** | **0.274** | **−2.63** |

capture は TP 距離と逆相関 — 短TP の bb_rsi (TPd 5p) だけ capture 0.387 / 唯一の正EV。**ただし bb_rsi 11件は全て 2026-07-02 の watchdog DECREMENT 再武装バグ E4 漏出 (T10 KILL 済み戦略)**。除外すると N=82 / WR 52.4% / EV −3.10 / payoff 0.252 — 本診断の結論はむしろ強化。

## 4. 勝ち側/負け側の執行実測

勝ち (N=51): 実現/設計TPd = q25/med/q75 **0.04/0.07/0.13**。MFE/TPd med 0.19 [0.11–0.39]。実現/MFE med 0.60 (agg 0.463、分位 p10–p90 = 0.11/0.25–0.27/0.60/1.00/1.00)。SL_HIT 勝ち10件は pnl==MFE 完全一致 (trail がピーク約定)。giveback 142.5p は全額 OANDA_SL_TP (med 2.5p/件)。剥落上位セル: vix_carry_unwind×USD_JPY (41.8p, capture ~14%)、zz_pivot×EUR_USD、trendline_sweep×GBP_USD。

負け (N=42): |実現|/設計SLd = q25/med/q75 **1.00/1.01/1.03**。MFE med 0.1p、MFE≥3p は 2件 (xs_momentum_rsi −18.0/MFE13.5 と trendline_sweep −6.9/MFE10.0) のみ。SL越え slippage 合計 12.3〜15.1p (定義依存: 設計SL比/記録ストップ比)、>1.05× は 6/35件、slip>2p は 1/42。MFE≥TP半分 0件、+1R 到達歴 1件 — **「trail が勝ちを負けに変えた」形跡なし**。pure SL/TP 反実仮想は −2.53〜−4.98 p/t (構成仮定依存) と実現 −2.63 より悪く、**trail 除去は解ではない**。

Counterfactual (base −245.0p): BE@+3p 移動 = 楽観 +24.9p (72%単一トレード) / 悲観 −47.1p (勝ち42/51件が MAE>0.5p 経由でBE転換リスクプール +72〜107p)。MFE 100% 捕獲 = +142.5p → −102.5p / payoff 0.59。両方 = **−77.6p、依然赤字** (分岐 payoff 0.824 必要)。

## 5. 摩擦の実測とモデル突合

- pnl_pips ≡ 方向符号付き (exit−entry)/pip、残差ゼロ = **摩擦は fill 価格内蔵** (app.py L10254 コメントと整合: spread+slippage の後付け控除は「真のコストの約2-3倍」の二重計上)。
- spread_at_entry は USD_JPY/EUR_USD/GBP_USD で**完全定数** (0.8/0.8/1.3) = 静的設定値。実測は EUR_JPY のみ。**異常スプレッド検出はこの列では構造的に不可能** (異常約定 0件 ≠ 無かった証明)。
- 非対称成分: WIN spread 1.16 / LOSS spread 1.16 (対称)、出口滑り LOSS +15.1p vs WIN(TP) −2.6p 有利 → 非対称計 17.7p/30d = net 損失の 7%。

| 摩擦モデル | /t | 30d計 | gross PnL | gross payoff (勝敗再分類) |
|---|---|---|---|---|
| 実測フロア (spread+出口滑り) | 1.30 | 120.6 | **−124.4p (符号反転せず)** | 0.44–0.46 |
| 理論 per-pair ([[friction-analysis]]) | 3.17 | 294.6 | +49.6p | 0.871 |
| dashboard 合成 (v2.3 draft 採用値) | 3.98 | 366.2 | +121.2p | 0.963 |

**v2.3 draft への更新提案**: draft の「摩擦 366.2p / 摩擦除去後 gross +123.6p = 摩擦が符号を反転」は risk_analytics.py L343-349 の診断用合成値 (実測フロア比 3.06倍、app.py 自認の過大計上) でのみ成立。**「friction ∈ [120.6, 294.6]p / gross ∈ [−124.4, +49.6]p、符号反転はモデル依存」へ修正**。ボトルネック再定義 (正の摩擦調整EVセル不在) 自体は全モデルで不変 — 実測フロアではむしろ決済非対称の相対重要度が draft 想定より高い。

## 6. pair × direction 分解 (平均の嘘チェック)

| pair | dir | N | WR% | EV p/t | payoff |
|---|---|---|---|---|---|
| GBP_USD | BUY | 28 | 53.6 | −3.02 | 0.21 |
| USD_JPY | SELL | 27 | 59.3 | −1.44 | 0.32 |
| EUR_JPY | SELL | 15 | 46.7 | −3.34 | 0.43 |
| GBP_USD | SELL | 10 | 50.0 | −4.54 | 0.16 |
| EUR_USD | SELL | 9 | 55.6 | −3.01 | 0.18 |

全セグメント payoff 0.16–0.43 で一様に低い — 構造的であり特定ペアの産物ではない。ただし pip 出血は GBP_USD 集中: N=38 / −129.9p (全体の 53%) / 理論 friction 172.1p (全体 294.6p の 58%)。

## 7. GBP_USD セル分解と R2 demote 候補 (Rule 2 即断可)

基準: N≥10 ∧ EV<0 ∧ Wilson_lo < BEV_WR ([[friction-analysis]])

| cell | N | WR% | EV | sum | Wilson_lo | BEV_WR | verdict |
|---|---|---|---|---|---|---|---|
| GBP_USD×wick_imbalance_reversion×BUY | 12 | 41.7 | −3.91 | −46.9 | 19.3% | 37.9% | **R2 demote 候補** |
| USD_JPY×vix_carry_unwind×SELL | 10 | 60.0 | −1.90 | −19.0 | 31.3% | 34.4% | **R2 demote 候補** |
| 2セル合計 | 22 | | | **−65.9** | | | 閉鎖で 30d 出血の **27%** 削減 (GBP単体では wick 閉鎖で −129.9p 中 36%) |

wick×BUY 精査: 勝ち5件全て +1.3〜+2.3p / 負け7件 (6件 −7.5〜−10.9p、1件 −0.5p SIGNAL_REVERSE) / 負け MFE≈0 = entry premise 即死型。dedup 漏れ1件 (06-19T06:00 13秒差 2件、oanda 541297/541301、dedup_violation=0 のまま — engine 再構築 dedup 死と整合) を除外した N=11 でも判定不変。

**BEV 基準の歪み (重要 caveat)**: BEV_WR 37.9%/34.4% は payoff≈1.64 前提。live 実 payoff 0.15–0.27 での整合 BEV は 78–87% であり本基準は**過小フラグ** — 上記2セルは「保守的基準ですら落ちる最弱セル」と読む。trendline_sweep×BUY (Wlo 42.4% > 37.9%) も payoff 整合 BEV 82.7% には遠く及ばない。

### trendline_sweep×GBP_USD forensic (N=19, ELITE_LIVE — demote 保留)

- **WR 68.4% は BT 73.1% と統計整合** (Wilson95 [46.0, 84.6]) — エントリシグナルは BT どおり機能。
- **payoff 0.15 (avgWin +1.67 / avgLoss −11.07)** が崩壊点。BT EV+0.599@WR73.1% の breakeven 要求 payoff ≥0.368 の半分以下。
- 機構: 勝ち13件 = 「SL_HIT|SMC完全反発」trail lock +2.0〜2.3p 固定 6件 + OANDA_SL_TP 平均 +1.31p 7件 (MFE 最大 9.1p 未実現)。負け = フル SL 7.2〜20p、大負け4発 −53.6p は MFE≈0 即逆行。
- 出血の 87% (−38.9p) が UTC12–15 NY overlap、SELL avgLoss −17.70p 最悪。UTC04–07 は ≒breakeven。
- 窓前 13件も EV −0.38 / payoff 0.43 — **live は BT +0.599 を一度も再現していない**。
- 摩擦副因: spread 1.3p ≈ avgWin 1.67p (摩擦全額戻しても payoff 0.15 構造では正転せず)。
- **異常**: 大負け4発の close_analysis 全てに「⚖️ 4H+1D 不一致 → シグナル抑制中」タグ付きで live 発注 — MTF ゲートが LIVE 転送を block すべきだったかは engine 側別調査 (本 forensic の範囲外)。

## 8. R2 即応候補 (Fast & Reactive、本文書は診断 — 執行は別コミットで rule:R2 明示)

1. GBP_USD×wick_imbalance_reversion×BUY の live 転送停止 (+46.9p/30d)
2. USD_JPY×vix_carry_unwind×SELL の live 転送停止 (+19.0p/30d)

## 9. R1 候補レバー (列挙のみ — 365日BT + Bonferroni + Pre-reg LOCK 必須、user 承認前実装禁止)

- **TP 短縮**: 設計 TP を実走距離 (winners MFE 帯 4–6p) に整合。傍証 = bb_rsi 型 TPd 5p で capture 0.387 (ただし T10 KILL 戦略 + watchdog 漏出コホートであり根拠には使えない)
- **SL 短縮**: SL ~9p vs MFE 天井 ~5p の R:R ミスマッチ解消 (loss 側は設計どおり執行されるため SL 距離が直接 avgL を決める)
- **シグナル張り替え**: 5p しか走らない場所ではなく 20p 走る場所への entry 再設計 (v2.3 reframe と同型)
- **GBP_USD 露出削減**: 理論 friction の 58% が GBP_USD (pair demotion 形式なら R2 の範疇に落とせる可能性)
- **trail/BE パラメータ変更は単独レバー化非推奨**: BE 移動悲観バウンドが負 (−47.1p)、trail 除去反実仮想も実現より悪い。shadow 側 (退出なし追跡) or tick 価格再構成での検証が先

## 10. Caveats

1. **N=93 (1ヶ月)、セル単位 N=1–19** で全て Rule 1 基準未満。entry_type/セル別数値は方向性の示唆であり有意性主張ではない (Bonferroni 未補正。ただし demote は Rule 2 範疇で許容)。
2. **MFE/MAE は exit 時点打ち切り + path ordering 不明** — counterfactual は楽観/悲観バウンドのみ。SL_HIT 勝ち10件の pnl==MFE 完全一致はバー粒度記録の疑い → capture 0.46 は上方バイアスの可能性 (真の早利確はさらに大きい)。tick 粒度検証未実施。
3. **spread_at_entry は 3/4 pair で静的定数** — 実測フロア 1.30/t は文字通り下限。指標時スプレッド拡大は過小計上。エントリー側滑りは列未輸出で観測不能 → 真の摩擦は [1.30, ~3.17]/t の区間推定 (API 輸出 chip 化済: task_d932525c)。
4. **sl 列は trail で書き換わる row 混在** (SLd 1.4p で 4.93× overshoot の外れ値1件)。「元の設計 SL」が別列に無いのは執行監査上の欠陥。
5. close_analysis 42/93 が NULL (server 側クローズ全件) — trailed stop か原SL かは pnl 符号と価格からの推定で、OANDA transaction log 直接確認は未実施。
6. pure SL/TP 反実仮想 −2.88 p/t は構成仮定非明示のため再現レンジ −2.53〜−4.98 で幅記載。方向 (実現より悪い) は全構成で支持。
7. shadow (N=583) は同方向の結論 (capture 0.63 / payoff 0.38 / losers MFE≥3p 7.5%) だが friction 実負担なし + entry_type 構成差の交絡あり。
8. 30d 窓と draft 窓の一致は偶然であり将来の再現を保証しない。friction-analysis.md 理論値は旧レジーム計測で BEV 前提の更新未実施。

## 11. 検証状態

| サブ分析 | 状態 | 主要訂正 (反映済) |
|---|---|---|
| t3a close_reason 分解 | ✅ 敵対的検証済 | pure SL/TP 反実仮想を幅記載化; SL_HIT 負け「逆行SL」30/31; SIGNAL_REVERSE カット 30→~34% |
| t3b MFE/MAE counterfactual | ✅ 敵対的検証済 | 未捕獲 142.0→**142.5p** (比 5.72:1、両レバー −77.6p); OANDA_SL_TP 単体返上は 64–65% (主張より悪化方向); BE 悲観バウンド下端 −47.1p は頑健 |
| t3c 摩擦・slippage | ✅ 敵対的検証済 | payoff(f) 式行は撤回 (再分類ベースが正); OANDA_SL_TP 勝ち平均 +2.3→**+2.08p**; floor gross payoff は 0.44–0.46 幅記載 |
| t1 GBP_USD セル分解 | ✅ 敵対的検証済 | 大負け4発 −54.6→**−53.6p**; wick 負けは 7件 (−0.5p の SIGNAL_REVERSE 含む); OANDA_SL_TP 勝ち +1.4→**+1.31p**; 「勝ち幅 1.2–2.4p 圧縮」は trendline/wick/vix 限定 (dt_sr +8.00 / bb_rsi +3.06 は範囲外) |

再利用スクリプト: scratchpad `t1_gbpusd_cells.py` / `t1_forensic2.py` (session-specific のため恒久化するなら tools/ へ移設要)。
