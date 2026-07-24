# エッジ開発 Postmortem — 成功パターンと「なぜ勝てないか」の全数検死 (2026-07-24)

**方法**: 13-agent ワークフロー (4並列 KB 全数リーダー → 統合 → 根本原因 4 クレームの敵対的検証×2レンズ)。
失敗仮説 **54 件** + 生存候補 **21 件** の全数棚卸し。一次資料 341 tool 参照。
**性格**: 分析ドキュメント (tier action なし)。既存 verdict の統合であり新規エッジ主張ではない。

関連: [[roadmap-v2.3-payoff-friction-repair]] / [[payoff-asymmetry-diagnosis-2026-07-07]] /
[[exit-repair-tp-sl-prereg-2026-07-07]] / [[ws3-asymmetry-oos-prereg-2026-07-09]] / [[audit-index]]

---

## TL;DR — 「勝てるエッジ開発ができない」は半分誤診 (3層診断)

1. **失ったのはエッジではなく幻影** — 「勝てていた時期」は一度も存在しない (live 累計 N=563 / −552.7p)。
   Era-1 (4月) の昇格は BE/Trail の WR +10〜23pp 水増し (ablation 実測: 62.7%→39.8% ≒ TV 43.5%) +
   短窓選択の産物。深い検証にかけた favorable-BT 昇格は全て反転 (trendline_sweep 365d WR73-81% →
   12y 41-44%, p=0.88-1.0 で 0/3)。21.6%/月目標自体がこの水増し経路から導出されていた。
   ⚠️ 敵対的検証の訂正: 「全席が幻影」は**検証済みサブセット内で 100%** であり census ではない —
   doji_breakout 等 10 席超は未検証のまま着席、昇格根拠も heterogeneous (shadow 小N / TV+user override /
   12y+Bonferroni の price_shock 5席 等)。
2. **検証装置はすでに完成している** — healthy-kill : false-claim 比 = Era-1 0:10 → Era-2 12:6 →
   Era-3 (WS3) 28:0 → Era-4 (E15/E20) 2:0。観測前 LOCK 体制以降、**false positive の live 到達 = 0**。
3. **問題は sourcing** — 検証リソースの ~80% を「無料 OHLCV × intraday × リテール摩擦」に投下したが、
   その空間の摩擦調整後エッジ密度は巨大 N でほぼゼロ (外部独立 falsification Mesfin 2026 とも同型一致)。
   **完璧な検証器 × 不毛な探索空間 = 0 勝は仕様どおりの出力**。
   ⚠️ 訂正: 正確には「エッジ密度ゼロ」ではなく「**edge < リテール摩擦 + 認定閾値**」— sub-friction の
   gross 構造は複数実在 (trendline 12y gross +0.94p、mtf RANGE SELL +1.85p 等)。拘束条件は条件付き。

## §1 Funnel — EV はどこで死ぬか

仮説ファミリー投入 ≈**60** (2026-04→07)
→ 長窓・無バイアス測定で大半即死 (Era-1 短窓合格 ≈10-15 は 365d/12y 再検証で **0/15** 生存。
マススクリーン: regime-2D 0/43、TP-hit Bonferroni 合格 5/m=107 ≒ 帰無 FP 期待 5.4、12-cell 0/12)
→ pre-reg 統計ゲート通過 **3** (lfr×EUR_USD 1.43 p=0.0115 / htf_fb×AUD_JPY 1.82 p=0.0118 / C4)
→ 収益化 **0** (stage-2: lfr 9/9 負 −6.5~−8.3 p/t、htf_fb 8/9 負で UNDERPOWERED、C4 live −2.95 p/t)。

**二段構造**: 大半の仮説は「測定を直した瞬間」に死に (最大の集中点)、実在が証明された少数の非対称性は
「first-touch EV 変換 + 摩擦」で死ぬ。live N≥30 で摩擦調整正 EV のセルは **0**。ELITE tier は空集合 (07-15)。

## §2 死因タクソノミ (54 件)

| 死因 | 件数 | 代表例 | 教訓 |
|---|---|---|---|
| IC-null (シグナル自体不在) | 15 | H4 レベル \|IC\|<0.05 @N=10-15k、チャネル 0/48、EMA10 13y PF0.28、E20 carry IC 逆符号有意 | 巨大 N でフラット = 本当に無い |
| OOS-fail / winner's curse | 12 | round-3 top-8 が OOS 8/8 符号反転、round-2 ratio 1.48→0.88 崩壊 | top-by-EV 凍結は最過学習セルを選ぶ |
| BT-artifact (測定器故障) | 9 | BE/Trail +10-23pp、orb 60d→365d 反転、trendline 365d→12y 崩壊 | 統計は偏った推定器を救えない |
| friction > edge | 9 | mtf_switch 実在 +0.73p < 2.0p、bb_rsi 上限 = breakeven、1m USDJPY ATR≈friction | ±1-3p/t の帯は実在しても黒転不能 |
| execution-collapse (公正な live テスト未受験) | 6 | **sweep_reversion_eurgbp: 12.4y Bonferroni 生存 (t=4.46) が 24 日 fill=0 (HTF gate silent drop)**、agg-Kelly cutoff で live 発火不能 ≈3ヶ月 | edge の死因と process の死因を混同するな |
| 小N昇格 | 5 | trend_rebound N=17 +1.14 → N=60 −1.29 | N≤40 の正 EV は全て消えた |
| knife-edge 多重比較 | 3 | T11 p=0.0497 → cluster 補正 0.15 | 3点検査を制度化させた |
| process 設計エラー (本物を殺した可能性) | 2 | MAFE exit: ΔEV+0.54p p≈0 なのに WR ゲートで SURVIVOR=0 | mechanism-gate alignment |
| data-blocked | 1 | S4 (介入イベントリスト不在、正しい中止) | 外部データ死は恒常リスク |

## §3 成功パターン (生存物が共有する形)

1. **exit 機構フリーの測定** (forward MFE/MAE) + ゼロ重複 OOS + block bootstrap + FDR + 事前凍結 —
   pre-reg 通過 3 件は全部この形。BE/Trail 込み測定で通過した昇格は 100% 反転
2. **friction headroom ≥10x** — htf_fb×AUD_JPY: MFE p50 = 摩擦の 13 倍 (KB 中唯一の実 headroom)。
   sweep_reversion_eurgbp は 12h ホールド設計で摩擦をクリア
3. **低頻度・イベント/レベルアンカー・長ホールド** — fix-time / HTF 日足レベル / 月3回級。
   15m 連続足スキャン系 (channel/level/candle/momentum) は全滅
4. **counterparty 機構の明示は生存を予測しない** (fixing flow も stop-hunt も同率で死亡)。
   一方 **live 実データ由来の「負の場所フィルタ」は一度も覆っていない** (session_pair 停止、GBP-Asia block、
   HTF_MIXED stop)。「どこで勝つか」は未発見、「どこで負けるか」は再現的に既知
5. **観測前 LOCK + 固定 branch + 敵対的検証 + 凍結候補** → false positive の live 到達 0

## §4 根本原因 (敵対的検証済み)

| # | クレーム | 判定 | 検証後の訂正 |
|---|---|---|---|
| f | 5月以前の「勝てるエッジ」は BT 測定器が製造した幻影 | ACCEPT (PARTIAL 訂正) | 検証済みサブセット内 100% 反転。未検証席 10+ 残存、反転機構は BT 水増しの他に摩擦・小N運も |
| a | 無料 OHLCV リテールパターンのエッジ密度 ≈0 | ACCEPT (PARTIAL 訂正) | 正確には edge < 摩擦+認定閾値。sub-friction gross 構造は実在。Mesfin 2026 は MNQ での同型一致 (追試ではない) |
| b | 1m-15m×摩擦 (RT 2.0-4.5p) が実在シグナルすら殺す | ACCEPT (PARTIAL 訂正) | 1m は budget-parity で構造 bound 成立。15m の主因は gross 不在 + artifact + EV 変換失敗で、摩擦は狭い marginal band (+1〜3p/t) のみ binding。**実測フロア摩擦は 1.30p/t** (理論 2.0-4.5p は過大)、T2 verdict は摩擦モデルに頑健 |
| c | 「ボトルネックは BT→live 変換でシグナルは有る」説 | REJECT 支持 | 会計上 2/3 は execution 破壊 (pip 台帳) だが log-share では 1/3。修復可能性では符号不反転 (counterfactual ladder −60p 残存)。WS3 stage-2 は 17/18 負 (htf_fb 1 構成 +1.15 は p=0.594 の孤立点、recheck 枠残置) |
| d | hit rate 0/60 は業界期待値どおり | PARTIAL ACCEPT | pre-reg 通過率 7.5% は業界正常域。異常は Era-1 の false-promotion 100% と測定器故障 3ヶ月放置と sourcing 配分 |
| e | 「DD はサイジングのせい」説 | REJECT | DD100.8% は分母 1000pip ハードコードの artifact (実 NAV −22%)。pip 穴の 102% 相当は XAU 期 (−2,280p)。現行は逆に過剰防御 (正セルすら発火不能) |
| 追加 | 供給スループットが目標に対し数学的不足 | ACCEPT | 21.6% には ~90 stage-2 級セル、M3 でも 5+ セル必要。発見レート 0/60 では規模 problem が先 |

## §5 業界比較

公表アノマリー追試失敗率 ~65% (Hou-Xue-Zhang 系)、公表後減衰 ~50% (McLean-Pontiff)、体系的ファンドの
BT→本番到達は数%。本プロジェクトの「pre-reg 40 本 → 統計通過 3 (7.5%) → 収益化 0」はリテール摩擦込み
intraday FX (期待生存率 ~0 に漸近する最効率検証環境) では**分布の範囲内**。業界比で劣後したのは hit rate
ではなく: (a) Era-1 の無統制昇格、(b) BT 測定器バイアスの ~3ヶ月放置、(c) 期待密度 ≈0 空間への資源 80%
先行投下。逆に Era-3/4 の pre-reg 規律は多くの実務チームより厳格。

## §6 処方箋 — プロセス強化ではない (もう十分強い)

1. **modality 単位の期待値評価を仮説より先に行う** — 「このデータ×ホライズンに摩擦比 <10% のエッジが
   構造的に存在しうるか」を掘る前に問う。E1 positioning / E7 surprise への転進はこの実装であり正しい
2. **friction headroom ≥10x を入場条件化** — headroom のない仮説は検証前に落とす
3. **KPI の変更** — 「エッジの有無」ではなく「単位時間あたり検証済み仮説処理数 × modality 事前確率」
4. **市場に否定されていない棚卸し資産の回収** — sweep_reversion_eurgbp (execution 死のみ、12.4y Bonferroni
   生存) の公正な live テスト、htf_fb×AUD_JPY shadow N≥100 recheck (registry 済)

## §7 本ドキュメントの位置づけ

falsified 済み仮説の再試行禁止は各 MEMORY / KB verdict に従う。本 postmortem は優先順位判断の参照点であり、
個別の tier action / 実装は従来どおり R1/R2/R3 プロトコルに従うこと。
