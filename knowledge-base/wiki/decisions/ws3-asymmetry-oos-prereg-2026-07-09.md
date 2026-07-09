# Pre-registration LOCK: WS3 方向性非対称の OOS 検証 (rule:R1 stage-1)

**登録日**: 2026-07-09 (BT 実行前に設計固定 — カーブフィッティング禁止の遵守)
**Status**: 🔒 **LOCKED** — 本文書の変更はレビュー必須 PR のみ。結果を見た後のエンドポイント/候補セット/閾値の変更は禁止
**起点**: [[ws3-mfe-distribution-2026-07-08]] (探索診断) / [[roadmap-v2.3-payoff-friction-repair]] WS3 (T2 FAIL 後の主戦線)
**承認**: user ミッション委任 (2026-07-08「運用はまかせるよ」) に基づく純研究 (live パラメータ変更なし)。**stage-2 (barrier/EV 設計) と live 実装は本 verdict PASS 後に別 pre-reg + user 最終承認**

## 1. 仮説 (H1)

探索標本 (2025-07-08〜2026-06-07) で観測された MFE/MAE 方向性非対称 (ratio≥1.3、母集団中央値 0.88 に対する上位テール) のうち、少なくとも 1 セルは選択バイアスではなく実在の情報であり、**重ならない期間 (OOS) でも非対称が再現する**。

H0: 全候補セルの OOS ratio ≤ 1 (探索の非対称は m=79 事後選択の産物)。

## 2. 候補セット (a priori 固定、m=8 — 探索診断 §2 の ratio≥1.3 (N≥20) ∪ 持続型)

| # | cell | 型 (固定) | 探索 ratio (h24→h96) | Primary horizon |
|---|---|---|---|---|
| 1 | htf_false_breakout×EUR_JPY | 減衰 | 1.81→0.90 | h24 |
| 2 | trendline_sweep×EUR_USD | 減衰 | 1.65→0.82 | h24 |
| 3 | dt_sr_channel_reversal×EUR_USD | 減衰 | 1.55→1.18 | h24 |
| 4 | london_fix_reversal×EUR_USD | 減衰 | 1.51→1.24 | h24 |
| 5 | htf_false_breakout×AUD_JPY | 減衰 | 1.39→1.02 | h24 |
| 6 | lin_reg_channel×EUR_USD | **持続** | 1.38→**1.94** | **h96** |
| 7 | hull_donchian_fade×EUR_USD | 減衰 | 1.30→0.97 | h24 |
| 8 | dt_fib_reversal×USD_JPY | **持続** | 1.29→**2.05** | **h96** |

- 型と primary horizon は探索標本で固定 — OOS で horizon を選び直すことは禁止 (リーク)
- **lin_reg_channel 注記**: channel 系は [[project-channel-edge-falsified]] (IC null、2026-06-25) 済みだが、falsified 仮説は「チャネルライン接触→方向」。本候補は「本番 engine のエントリー母集団の forward 非対称」という別 estimand であり再試行禁止に非該当と裁定。OOS FAIL なら falsification を補強する方向で整合

## 3. 評価プロトコル

- **エンジン**: `tools/ws3_mfe_scan.py` と同一 (本番 signal 関数 baseline、V2 parity 3flag、exit 非依存 forward MFE/MAE)
- **OOS 窓**: **2024-07-07〜2025-07-07** (探索窓 2025-07-08〜2026-06-07 および診断窓 2026-06-07〜07-08 と重複ゼロ)。実装 = 隔離 worktree に末尾 2025-07-07 で切詰めた parquet を配置し lookback 365d (loader は tail−365d 窓)
- **データ制約 (a priori 宣言)**: EUR_USD / EUR_JPY は 2014〜フル 15m あり。**USD_JPY / AUD_JPY の 15m ローカルは 2025-04〜のみ** — Massive API から 2024-07〜2025-07 の 15m を追加取得して評価する。取得不能な場合、セル #5/#8 は短縮 OOS (2025-04〜2025-07、検定力低下) で評価し verdict に明記 (除外はしない)
- **エントリー母集団**: OOS 窓での BT baseline エントリー (探索と同一定義)

## 4. エンドポイント (固定)

- **Primary (セル毎)**: OOS 窓の MFE/MAE 比 (primary horizon、中央値ベース: median(MFE)/median(MAE))
- **検定**: 日次ブロックブートストラップ (B=10,000、day resample → median ratio 分布)。p = P(ratio ≤ 1) one-sided。**多重性 m=8、BH-FDR q=0.10**
- **PASS 条件 (セル毎、全て充足)**: (a) BH-FDR 通過 (b) OOS point ratio **≥ 1.2** (探索 1.3 に対する事前設定の shrinkage 床) (c) OOS N ≥ 30
- **全体 verdict**: PASS セル ≥1 → **stage-2 へ**: PASS セル限定の barrier/EV 設計 pre-reg + TV Pine canon 再現 (MEMORY `feedback_tv_edge_discovery_loop`) + user 承認。PASS ゼロ → **現行シグナル母集団からの張り替えは断念し、新シグナル系統 (外部仮説) の探索へ** — v2.3 WS3 に反映

## 5. ナイフエッジ3点検査 (verdict 時必須)

1. **メカニズム整合**: PASS セルの ratio 構成 (MFE 増か MAE 減か) が探索標本と同型か
2. **擬似反復**: 日次クラスタ補正済み (ブートストラップ設計内蔵) + lag-1 ρ 記録
3. **horizon 隣接整合**: primary horizon の PASS が隣接 horizon (h48 等) と整合するか (格子点固有 PASS の排除)

## 6. 執行と監視

- **executor**: claude 直接実行 (exit-repair 方式)。タスク票 `20260709-ws3-asymmetry-oos-verification`
- **期日**: **2026-07-16** までに verdict (自己設定、T5 型ギャップ防止)
- **verdict 記録**: 本文書に追記 + `raw/bt-results/` 保存 + session log + roadmap 反映

## 7. 除外・注意 (LOCK 時点で明示)

- 本 pre-reg は **live パラメータを一切変更しない** (純研究 stage-1)
- 非対称の OOS 再現 ≠ 正 EV。EV 化は stage-2 (barrier 設計 + 摩擦控除 + TV canon) の責務 — stage-1 PASS を promote 根拠にしない
- MFE/MAE はバー粒度。2024-25 の市場レジーム差 (ボラ水準) は ratio (比) 指標により一次近似で中立化されるが、レジーム依存性は verdict に記述
- 探索標本での閾値 (1.3)・型分類を OOS で調整することは禁止

---

## 8. VERDICT (2026-07-09): ✅ **PASS — 2/8 セルが OOS 再現** (機械判定 + ナイフエッジ3点検査済)

**執行記録**: claude 直接実行、期日 07-16 の 7 日前倒し。OOS スキャン = 切詰め parquet (末尾 2025-07-07) の隔離 worktree で `tools/ws3_mfe_scan.py --pairs EUR_USD,EUR_JPY,USD_JPY,AUD_JPY --out-suffix _oos_2024_2025` (N=4,980 entries)。USD_JPY/AUD_JPY は Massive 15m を 2024-05 まで遡及取得して充足 (§3 の短縮 OOS 条項は不使用)。判定 = `tools/ws3_oos_verdict.py` (§4 実装、B=10,000, seed 固定)。

### 8.1 機械判定 (§4)

| cell | H | N | OOS ratio | 探索 | p | FDR | CI5% | 判定 |
|---|---|---|---|---|---|---|---|---|
| **london_fix_reversal×EUR_USD** | h24 | 41 | **1.429** | 1.51 | 0.0115 | ✓ | 1.14 | **PASS** |
| **htf_false_breakout×AUD_JPY** | h24 | 39 | **1.824** | 1.39 | 0.0118 | ✓ | 1.20 | **PASS** |
| trendline_sweep×EUR_USD | h24 | 44 | 1.695 | 1.65 | 0.116 | ✗ | 0.85 | fail (点推定は再現、分散で不通過) |
| htf_false_breakout×EUR_JPY | h24 | 32 | 0.99 | 1.81 | 0.44 | ✗ | — | fail (崩壊 = 選択バイアス) |
| dt_sr_channel_reversal×EUR_USD | h24 | 34 | 0.62 | 1.55 | 0.83 | ✗ | — | fail (崩壊) |
| lin_reg_channel×EUR_USD | h96 | 26 | 1.13 | 1.94 | 0.36 | ✗ | — | fail (持続型不再現、N<30) |
| hull_donchian_fade×EUR_USD | h24 | 46 | 1.11 | 1.30 | 0.41 | ✗ | — | fail |
| dt_fib_reversal×USD_JPY | h96 | 20 | 1.25 | 2.05 | 0.28 | ✗ | — | fail (持続型不再現、N<30) |

### 8.2 ナイフエッジ3点検査 (§5) — 全通過

1. **メカニズム整合 ✅**: 両 PASS セルとも構成が探索と同型 (MFE 優位、MAE 崩壊による見かけの比でない)。london_fix 14.3/9.5→18.0/12.6 (ボラ水準スケールで比保存)、htf_fb×AUD_JPY は MFE p50 40.5p (摩擦 ~3p の 13倍) と絶対量も充分
2. **擬似反復 ✅**: lag-1 ρ = −0.37 / +0.11 (日次ブロックで補正済、負値は保守方向)。n_days 39/35
3. **horizon 隣接整合 ✅**: london_fix 1.38/1.43/1.40/1.85、htf_fb 1.21/1.82/2.21/2.13 — 孤立格子点なし、htf_fb は単調増加 (持続性の示唆)

### 8.3 帰結 (§4 の固定分岐)

**PASS ≥1 → stage-2 へ**: PASS 2 セル限定の barrier/EV 設計 pre-reg + TV Pine canon 再現 + **user 最終承認** (live 実装はそこまで禁止)。「探索→OOS」2 段スクリーンを生き残った初のシグナル候補。注意: (a) 探索・OOS とも Python BT エントリー母集団 — TV canon 再現が stage-2 の必須ゲート (b) london_fix_reversal×GBP_USD の BT負EV 前歴 (EV −0.150) は**別セル** — EUR_USD への横展開禁止 (c) trendline_sweep×EUR_USD (点推定再現・FDR 落ち) は stage-2 には入れず、live N 蓄積で再評価 (ELITE_LIVE 稼働中のため自然に N が増える)

**成果物**: `raw/bt-results/ws3_asymmetry_oos_2026_07.{json,md}` + `_entries.json` (trade-level) + `ws3_mfe_scan_2026_07_oos_2024_2025.{json,md}`。判定器 = `tools/ws3_oos_verdict.py`
