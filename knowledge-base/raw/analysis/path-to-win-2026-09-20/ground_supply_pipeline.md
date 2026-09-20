# 仮説供給パイプライン 現状棚卸し (ground truth、文書のみ) — 2026-09-20

作業規律: 本ノートは KB/MEMORY/registry の読取りのみで構成。価格データ・DB への計算は一切行っていない。P-10 型 LOCK (E1 / ECG #22 / E12) の outcome ジョイント量は記載しない。数値は全て出所パス併記。

略号: KB = `/Users/jg-n-012/test/fx-ai-trader/knowledge-base/wiki/`、MEM = `/Users/jg-n-012/.claude/projects/-Users-jg-n-012-test-fx-ai-trader/memory/`、REG = `KB/decisions/prereg-trigger-registry.json`

---

## 0. 一枚要約

| 項目 | 値 | 出所 |
|---|---|---|
| 外部仮説 explore→OOS 生存 | **0/18 系統** (第4次時点 0/17 → E23 park で 0/18) | KB research/external-hypothesis-scan-round4-2026-09-10.md §4 / MEM project_e23_cb_text_underpowered_2026_09_15.md |
| base rate | **≈4.0% [Wilson 95% CI 0.7–19.5%]** (家族級 verdict ~25 件中 OOS PASS 1 = weekend_gap) | MEM project_process_meta_audit_2026_09_07.md / KB analyses/daily-market-review-protocol.md §1 |
| 月次スキャン新規採用 | 第3次 2 → 第4次 0 → 第5次 0 (**3 周連続 0**) | KB research/external-hypothesis-scan-round5-2026-09-17.md §3 |
| 着手可能 (能動) ライン | 09-17 時点 **1 本 (#27 family A)** → **09-18 に #27 FAIL クローズ** ⇒ 現在 **0 本** (推論、§2 参照) | round5 §2.3 + MEM project_family_a_ladder_frozen_2026_09_18.md |
| 時限ロック (受動) | 3 本: E1 2026-10-15 / ECG #22 2026-11-06 / E12 2027-02-05 | REG (verified) |
| 条件付き (受動) | 2 本: MoF #4 再判定 (REG deadline 2026-11-14) / ws3-round4 EUR divergence (ZN cache threshold 2026-11-15) | REG (verified) |
| park | 2 本: E23 (#25 UNDERPOWERED) / family B (番号非付与) — ほか #20 composite PARK-UNTIL | catalog #25 / round4 §2.3 / catalog #20 |
| 次回定例スキャン | 第6次 **2026-10-18** (四半期モダリティ棚卸し同乗) | REG `edge-supply-scan-monthly` (verified) |

---

## 1. 生きている pre-reg ライン (open) — first look / 検出力予想

### 1.1 時限ロック (P-10 型、ジョイント計算禁止中)

| ライン | 台帳 # | LOCK 日 | first look | 事前記録された検出力予想 | 備考 | 出所 |
|---|---|---|---|---|---|---|
| **E1 retail positioning contrarian** (Myfxbook Community Outlook aggregate、13 ペア) | #8 | 2026-07-17 self-LOCK | **2026-10-15** (cutoff 10-08) / second look **2027-01-06** | **modal 予想 = UNDERPOWERED** を事前記録。h=24h は first look Gate 2 構造的不達。grid = 2 統計 × {4h,24h} × barrier 2 = 6 combo、look 毎 BH q=0.05 | 蓄積 t0 = 2026-07-16T06:33:31Z (6 ペア) / 07-16T07:51:18Z (確証 7 ペア)。09-17 実測 13 ペア available、failures=0。Wayback 歴史 30,231 行は校正専用・確証検定禁止 | MEM project_ws3_external_hypothesis_transition_2026_07_13.md / round5 §1 / REG `e1-prereg-verdict-deadline` deadline=2026-10-15 |
| **ECG #22 equity_curve_shadow_gating** (forward v2) | #22 | 2026-08-03 | **2026-11-06** (forward 窓 [08-04, 11-01) 13 週、backstop 2027-01-31) | primary = active 4 セル × K{5,10,20}、**m=12**。遡及 v1 は合成データで偽陽性 100% を実証して KILL → forward 化。PASS でも live gate R1 は forward 再現後のみ | first look まで gate×outcome ジョイント計算全面禁止 | catalog #22 / REG `ecg-forward-first-look` deadline=2026-11-06 |
| **E12 CME 先物 volume flow** (unsigned abnormal volume primary) | #10 | 2026-07-29 | **2027-02-05** (cutoff 2027-01-31)、陳腐化 review **2026-11-30** | 「~3 ヶ月」目安は検定力根拠付きで 2027-02-05 に置換 (pre-reg §6)。BVC-signed は非 claimable secondary。増分 IC 必須検定 | 09-16 実測 cme_bars 7/7 verified。E13 再入場は E12 PASS 時のみ | catalog #10 / REG `e12-volume-first-look-deadline` 2027-02-05, `e12-volume-prereg-staleness-review` 2026-11-30 |

**F1 falsification (メタ監査、registry 凍結済み)**: 上記 3 時限系統から OOS PASS が 1 つも出なければ現行パイプライン棄却。判定期日 = **2027-02-05** (REG `project-falsification-f1-supply-space`)。

### 1.2 条件付き (受動)

| ライン | 条件 / 期日 | 内容 | 出所 |
|---|---|---|---|
| **MoF #4 次エピソード再判定** (`mof-next-episode-reverdict`) | REG deadline **2026-11-14** (round4 本文では「Q3 日次開示 ~11-06 見込み」) | 1 回限り同一仕様再判定。E-A primary は forward 的中 p=0.0143 (PASS) だが E-C は符号逆 FAIL (+188.1p、N=1 エピソード)。prior = 「介入後 SELL drift は 2026 で符号逆」 | catalog #4 / REG (verified) |
| **ws3-round4 EUR divergence conditional** | ZN_F_1h cache が **2026-11-15** まで延伸で発火 (REG threshold_date) | round-3 凍結外の EUR_USD/EUR_JPY OOS 生存 (claimable 不可) の fresh OOS。zn-cache-refresh は 09-10 修復・2/2 success 実測 | MEM project_ws3_... / round5 §1 / REG `ws3-round4-eur-divergence-conditional` |

### 1.3 受動 shadow 蓄積 (台帳内、蓄積待ち)

| ライン | deadline | 見込み | 出所 |
|---|---|---|---|
| htf_fb×AUD_JPY recheck (#11、volstate split 併設) | 2027-01-31 | 実測ペースで N≈14–41 << 100 → stale クローズ公算 | catalog #11 / REG `volstate-split-htf-fb-recheck` |
| sr_anti_hunt×EUR_JPY BUY forward 枠 (#12) | 2027-02-28、N≥40 fresh、中間再計算禁止 | 84.9%/0.0% の旧数値は虚構 (引用禁止) | REG `sr-anti-hunt-eurjpy-buy-forward-confirm` / MEM MEMORY.md |
| weekend_gap live 変換 (F2) | 2026-12-31 までに live N=0 なら PASS→live 変換未実証と認定 | 唯一の OOS PASS セル (arm B)。live 約定通算 0 | REG `project-falsification-f2-wg-live-conversion` / MEM MEMORY.md |

### 1.4 S0 intake 層 (仮説ではない)

日次市場レビュー+観測採集プロトコル (2026-09-14 新設、PR #256)。記述級のみ・α 予算消費ゼロ・台帳番号なし。卒業 = 同一 family ≥3 独立観測 or user 指名。30d 有効性レビュー **2026-10-14** (稼働率 <50% または「執行 QA 発見 0 ∧ 卒業 0」で廃止提案)。「毎日エッジ設計」は base rate 4% で不成立と明記。出所: KB analyses/daily-market-review-protocol.md §1, §5, §6 / REG `daily-market-review-30d-effectiveness`。

---

## 2. 現在の WIP 会計 (推論を含む)

- 統治規則 = 「今日着手できる本数 ≥1」(パイプライン §5 追補、2026-08-14 user 承認) — round5 §2.1。
- 09-17 (第5次) の訂正会計: 着手可能 1 (#27) / 時限ロック 3 / 条件付き 2 / park 2 — round5 §2.3。
- round5 §2.3 は「臨時スキャンの再発動条件 = #27 が凍結され測定待ちに移り、かつ他に着手可能な線が無い時点」と明記。
- **09-18 に #27 は FAIL クローズ** (J=0.2978 / p=0.1074、MEM project_family_a_ladder_frozen_2026_09_18.md)。
- ⇒ **推論 (inferred)**: 2026-09-20 現在、着手可能ライン = **0 本**。統治規則上、臨時スキャン発動条件が成立している (定例第6次は 10-18)。ただし round5 §4 は「毎月同じ 3 理由 (C1 有償 / C2 既 ban / C4 正 EV ホスト不在) で棄却」の実測を根拠に「四半期+イベント駆動」への cadence 移行を **user 決裁材料**として提案済み (執行はしていない)。臨時スキャンを撃つか cadence 決裁を先に取るかは判断事項。

---

## 3. モダリティ × 状態 × 根拠 棚卸し表

状態の定義: **closed** = explore/OOS FAIL or 敵対的検証 KILL で ban/クローズ条項が発効 / **open** = pre-reg LOCK 走行中 or 条件付き受動 / **park** = 未測定のまま保留 (窓は焼けていない) / **data-blocked** = C1 (無料経路なし・有償) で棄却、仮説内容は未検証 / **untested** = 未起案。

### 3.1 価格・OHLCV 内部

| モダリティ | 状態 | 根拠 (estimand) | 出所 |
|---|---|---|---|
| OHLCV 内部パターン (15m–1h) / cross-asset lead-lag (E3/E4) | **closed** | 内部 2 周 + 外部 1 周 = 3 周 FAIL。lead-lag は Lo-MacKinlay 非同期 artifact (IC 0.373→0.004)。Mesfin 2026 (OHLCV 14 family 全滅) が独立一致。round-3 divergence OOS 8/8 反転 | MEM project_ws3_external_hypothesis_transition_2026_07_13.md / round3 §3 |
| 水平線 / 平行線 / 斜め TL / ラウンドナンバー (wave-4 #18/#19 + L-c/d/e) | **closed** | #18 D1 失敗ブレイク fade −4.91p 符号逆 p=0.702 / #19 RN +6.34p p=0.117 (方向正だが弱い) / L-c,L-d,L-e 敵対的検証 KILL。zz pivot×線目処 FAIL (08-12) で補強。「ページのライン→エッジ」全滅 | catalog #18/#19 + wave-4 triage / MEM archive |
| H4 level / channel / sweep&reclaim / mtf SELL / bb_rsi / T11 | **closed** (falsified 6 系統) | 3-way IC null (N=10k–15k) 等、2026-06 系列 | MEM project_memory_archive_closed_2026.md |
| slow location-anchor MR (ppp #14 / cc-mr #21 / range fade #28 / quote-spread #17) | **closed** | 「方向は合うが弱い」死型 5 例 (ppp IC +0.113 p=0.129 / cc-mr +3.96p p=0.266 / #28 0/32 min p_block 0.1133 / qs −0.237σ p=0.3228) | catalog #14/#17/#21/#28 |
| ML / 深層学習 FX 予測 (E6/E28/E31) | **closed** (原則棄却 + OHLCV 閉鎖) | in-sample R² 家系、無料 OHLCV×intraday 同型は起案しない | round1 E6 / round4 E28 / round5 E31 |
| zz pivot × 線目処 | **closed** | explore FAIL 2026-08-12 (PR #179) | MEM MEMORY.md |

### 3.2 イベント / カレンダー

| モダリティ | 状態 | 根拠 | 出所 |
|---|---|---|---|
| 無条件イベント窓 (E15 FOMC/NFP/CPI) | **closed** | phase-0 OOS FAIL 0/6、min p=0.214 ≫ 0.0083 | MEM archive (E15+E7 行) |
| 指標サプライズ sign-follow (E7 phase-1) | **closed** | discovery 0/24、time-exit EV 全負 (−0.31〜−8.15p) = 符号系統逆。NFP/CPI z × sign-follow × M15 全変種再試行禁止。fade 追試は新 family + 敵対的検証 (CPI-fade C5 が負 prior) | catalog #9 |
| 発表前ドリフト (E8) | **closed** (C4 構造衝突) | エッジ窓 = スプレッド拡大窓 = 動的デスゾーンが正しく block する帯 | round2 E8 |
| 月末リバランス (無条件 WMR-fix + 条件付き #6) | **closed** | WMR REJECT (2026-06-18) + #6 IC(1d) −0.052 p=0.608 | catalog #6 / MEM archive |
| 祝日/休場 × D1–D2 (#15) | **closed** | レグ c 符号逆 (継続 −7.61p p=0.973) / レグ a explore PASS → OOS 崩壊 (+2.06p p=0.3145) | catalog #15 |
| gotobi / 仲値 (#13) | **closed** (較正成功・昇格 kill) | 効果 +1.92p < RT 2.14p = sub-friction。執行コスト構造変化なしに再昇格不可 | catalog #13 |
| VIX onset × JPY cross short 1–5d (#7) | **closed** (knife-edge) | 厳密 p=0.050091 > 0.05 (m=2)。headroom 32–55× 通過 = power 不足型。再挑戦 = 新データ + 隣接差分節、ban 例外は user 決裁 | catalog #7 |
| pre-FOMC transcription / MOVE bond-vol shock | **closed** (triage KILL) | headroom 4–12× < 10× / killed-VIX と重複 | catalog wave-2 triage |
| 中銀声明テキスト (E23 #25、ABG 辞書 × G4 × ΔNH × D1+5) | **park (UNDERPOWERED)** | Gate A 3/3 PASS (median |fwd5| 71.5/95.0/81.9p) / **Gate B N=56 < 100**。pass-2 未解錠 = explore/OOS 窓非接触。死因 = 特徴量疎性 (NH=0 が 279/327 = 85.3%)。**「CB テキスト falsified」引用禁止**。⚠️ park 根拠に未消化 P1 3 件 (Gate A が OOS 窓込み計算等、registry `review-backlog-253-257-digest` 期日 10-03) | catalog #25 / MEM project_e23_cb_text_underpowered_2026_09_15.md |

### 3.3 介入 / 政策 (MoF / 中銀)

| モダリティ | 状態 | 根拠 | 出所 |
|---|---|---|---|
| MoF 介入 forward pre-reg (#4、価格シグネチャ→ラベル) | **open (条件付き)** | E-A PASS p=0.0143 (forward primary 初的中) / E-C FAIL 符号逆 (+188.1p, N=1)。PARTIAL → 次エピソード 1 回限り再判定 (REG 11-14) | catalog #4 / REG |
| family A 発言ラダー → 介入ラベル (#27、価格不使用) | **closed (FAIL)** | J=0.2978 p=0.1074 (TPR 3/7, FPR 144/1101)。**観測効果量 (block 2/4) の検出力 0.130** = 非有意≠不在。凍結欠陥 2 件 (介入日 10→7 カレンダー / null の 20.3% が 5 block)。**「口先介入に情報なし」引用禁止、引用時カレンダー欠陥併記必須**。forward 期 (2026-07-30〜) は未接触凍結 | MEM project_family_a_ladder_frozen_2026_09_18.md / catalog #27 |
| family B 介入イベント → 回避/執行 | **park (番号非付与)** | C1: 公式ラベルが四半期ラグで執行条件付け不能、E-A 検知器のラベル代用は #4 OOS burn で禁止。C5: episode blocks ≤4 + 2026-05 outcome 既公表。再裁定条件 = A verdict (済、FAIL) + #4 reverdict (11-14)。**family A FAIL 後は「発言層なしで設計」が凍結指示** | round4 §2.3 / MEM family_a §How to apply |
| family C 金利差アンカー帯 × USD_JPY 帯下 LONG (#26) | **closed (FAIL、符号情報あり)** | N=41、net −24.2p、gate C p=0.527、価格のみ z はさらに悪い −65.8p。復活 = OIS/policy-path (有償) + 新 family | catalog #26 / round4 §2.1 |
| E26 BoJ 当預残高予想 / 短資会社経路 | **data-blocked** | 歴史系列の無料経路なし (BoJ 公表は事後) | round4 §3 |

### 3.4 金利 / キャリー / バリュー

| モダリティ | 状態 | 根拠 | 出所 |
|---|---|---|---|
| E20 carry-level (sign 政策金利差) × テクニカル entry 1–10d | **closed (S2 棄却)** | pooled IC **−0.047 p≈0 (機構と逆符号で有意)**、quintile 単調逆行 (Q1 +7.3 → Q5 −16.0)、financing 込み EV −3.4p/5d。carry 同型再提案禁止 | KB research/e20-rate-differential-s2-diagnostic-2026-07-24.md §3–4 |
| E20 mom63 (sign Δ63bd 2y 差) | **closed (S2 棄却)** | IC +0.026 p=0.003 だが効果量≈0、非単調 (Q2 −12.9 中抜け)、fold 3 単独駆動、cell IC 有意 0/78。**探索窓で完全死ではない** — 再起案は Q2 中抜け・fold 3 集中を機構で説明できる仮説に限る | 同 §2–4 |
| hull-donchian USD_CHF 金利差 range-pinning ゲート | **closed (falsified 2026-06-15)** | 反証窓 2018–19 で −1.14p、単調性逆 | KB research/e20-rate-differential-feasibility-2026-07-22.md §2b |
| D1 TSMOM basket | **closed (NULL 2026-06-08)** | USD 集中 (net 54%)、2016–26 トレンドプレミア圧縮 regime | 同 §2c |
| ppp 実質為替回帰 (#14) | **closed** | IC 42bd +0.113 p=0.129、探索窓が USD 一方的割高 (z>2: 96 vs z<−2: 5)。再挑戦 = 実質金利差込みモデル + 差分 or 2022+ 込み split | catalog #14 |
| E5 term-structure / forward bias、E18 factor timing | **data-blocked** | forward/swap curve 無料経路なし (spot only)。E20 が日次粒度で部分復活したが S2 棄却 | round1 E5 / round2 E18 / e20 feasibility §2d |
| 長ホライズン β (週次〜月次キャリー) | **untested・起案しない (U4 (d))** | edge 供給ではない: user 手動収益 = β (swap 28% + drift 72%、α p=0.32)、無レバ +0.3–0.4%/月 = バラスト | round4 §4 (d) / MEM user_manual_edge_usdjpy_carry_2026_08_12.md |
| OIS / policy-path anchor (family C 復活経路) | **untested** ($0 種まき可) | US レグは既存 CME capture に ZQ=F/SR3=F 追加で go-forward 蓄積開始可。JP レグ (TONA 先物) は無料経路細い。family C 点推定負で prior 低 | round4 §4 (c) |
| E29 インフレリスク conditioning | **closed (C4)** | 条件付けるべき正 EV ホストが母集団に不在 (摩擦調整 EV マップ)。ホスト出現で再検討 (条件付き保存) | round5 §3 E29 |

### 3.5 ポジショニング / フロー / 出来高

| モダリティ | 状態 | 根拠 | 出所 |
|---|---|---|---|
| E1 retail positioning (aggregate) | **open (LOCK)** | §1.1 参照。OANDA v20 book は 2024-09-14 に retail API 全体で終了、fxlabs 2020 廃止 = bucket 級無料ソース消滅 | MEM project_ws3_... |
| OANDA Data Services (bucket 級 positioning) | **data-blocked (有償 ~$1,850/月)** | M1 段階で非推奨 (選択肢 C) | 同 §8c |
| COT non-commercial level 極値 (#5) / commercial Δflow (#16) / CFTC TFF (E27) | **closed** | #5 BH 0/36+0/6、#16 IC +0.0186 p=0.5652、**鏡像恒等 corr(Δcomm, −Δnoncomm)=0.93** = 実質 1 モダリティ。ban = 「COT Δ/flow × 週次固定ホライズン全変種 (母集団問わず)」→ TFF も正面衝突 | catalog #5/#16 / round4 E27 |
| E12 CME 先物 volume (unsigned) | **open (LOCK)** | §1.1 参照 | catalog #10 |
| E2 order-flow imbalance / E13 BVC × tick volume | **data-blocked (E2) / closed-adjacent (E13)** | signed flow 未取得。tick volume は弱 proxy、BVC sign = 価格変化 = 価格モダリティ隣接。E13 再入場 = E12 unsigned PASS 時のみ (Databento 12y) | round1 E2 / round2 E13 |
| E14 CME 日次 volume/OI regime | **保留 (data 半分)** | OI 歴史は無料経路ゼロ = 今から蓄積のみ。単独エッジでない | round2 E14 |
| anchored VWAP deviation (L-c) | **KILL (再入場条件付き)** | FX spot に実約定 volume 不在。再入場 = E12 PASS 後に CME 実約定 anchor 版を新 family/R1 | catalog wave-4 triage L-c |
| E30 CLS 決済フロー / FX Outstanding | **data-blocked (商用)** | 母集団独立性は本物だが価格未取得 (下 3 桁以上の可能性)。U4 有償候補に条件付き追加、優先度は OTC 面の下 | round5 §3 E30 |
| E19 LOB cross-currency | **data-blocked + 重複** | EBS/LSEG 有償のみ、E4 閉鎖と重複 | round2 E19 |
| E21 human signal stream (user 手動) | **closed (診断、α 不検出)** | 3 ソース (bot 40 / 旧個人 45 / 外部 247 往復) 全て α なし、日次 block perm p=0.32、最大単一トレード寄与 68%。非 claim 所見: 保有 8h+ 勝ち / <1h 負けの方向一貫 — 検証は forward 明細 + 観測前凍結の新 family のみ | catalog #23 |

### 3.6 ボラティリティ / オプション

| モダリティ | 状態 | 根拠 | 出所 |
|---|---|---|---|
| E22 通貨 VRP (EVZ−RV21 × EUR_USD × 21bd) | **closed (完全 null)** | IC −0.0249 p=0.760、stressed-net −11.2p、swap −16.2p が支配。**vol モダリティ恒久クローズ** (無料 proxy 系列込み)。power caveat: 検出力 8–17% だが点推定≈0。復活 = 有償 OTC 面 + 新 family | catalog #24 |
| E9/E10/E11 (VRP contrarian / 25Δ RR crash ゲート / ATM IV→レンジ) | **E9 は E22 に吸収 closed / E10・E11 保留** | E10 = 方向でなく防御ゲート (4原則と緊張)、E11 = 既存セル conditioning (正 EV ホスト不在) | round2 E9–E11 |
| E17/E24 17 通貨 global vol risk | **data-blocked + horizon 不整合** | OTC IV パネル有償のみ、2026 研究で「予測力は 3 ヶ月超」再確認 | round2 E17 / round3 E24 |
| E25 synthetic vol surface (yfinance) | **closed-adjacent** | 実質 realized vol 変換 = 価格モダリティ再着せ替え | round3 E25 |
| OTC FX オプション面 (RR/BF/smile) | **untested (有償 ~$2k+/月 or CME DataMine 数百$)** | U4 (b): U1「継続」解決時の第 1 候補として条件付き凍結。G10 日次〜週次の系統エッジは文献でも EM 比で弱い | round4 §4 (b) |

### 3.7 マイクロストラクチャ / 執行

| モダリティ | 状態 | 根拠 | 出所 |
|---|---|---|---|
| BBO スプレッド状態 × fwd 方向 (#17) | **closed** | −0.237σ p=0.3228。副産物 = onset-entry RT 5.9–9.5p (正常化後の 2–3 倍) = デスゾーン防御の実測正当化。78k サンプルパネル残置 | catalog #17 |
| weekend_gap fill (#3) | **PASS (arm B、唯一の OOS PASS)** → live 変換未実証 | pooled exGBP 4h N=177、gross +15.60p、stressed-net +9.04p。live 約定通算 0 (F2 2026-12-31) | catalog #3 / REG F2 |
| sweep_reversion EUR_GBP (#1) | **exit-free 生存 → P-S1(a) retire (Option C、user 決裁 09-17)** | 12h net med +5.10p。estimand 監査で凍結閾値 net vs shadow EV gross の不整合、spaced net −3.33p 符号反転。再挑戦 = net estimand 新規 pre-reg (R1) | catalog #1 / MEM project_t8_week1_gate_breach.md |
| price_shock 5 席 (#2) | **監査 PASS (demotion 0/5)** + feed artifact 発見 | 土曜行 + spike-revert 不良プリントが 4–12.8% 汚染 | catalog #2 |
| ナイトスキャルパー家系 / gotobi 型 (overnight スプレッド封筒内側) | **closed (NOT-FEASIBLE-RETAIL)** | グロス 5–15p < headroom 21.4p、発火窓 = デスゾーン。再入場 = 執行コスト構造の変化なしに不可 | catalog wave-6 triage |
| グリッド / ナンピン | **closed (RISK-ILLUSION)** | negative-skew 変形、archetype として不可 | 同 |
| sub-friction gross 構造 | **park (台帳外)** | 07-24 parked 一覧 | catalog parked |
| composite weak-signal portfolio (#20) | **PARK-UNTIL** | K=2 (rn+ppp) では最楽観でも OOS t≈1.37 / power <50%。復帰 = K≥3 or user の vix #7 ban 例外決裁 | catalog #20 |

### 3.8 exit 側 / 執行層 (供給ではなく変換層)

| 項目 | 状態 | 根拠 | 出所 |
|---|---|---|---|
| exit 側改善 (mafe exit / momentum-decay trailing) | **closed (T2+stage-2 完全否定、正 EV ホスト不在)** | WS3 stage-2 PASS ゼロ / UNDERPOWERED | MEM archive WS3 行 / catalog parked |
| live 転換層 | **故障 (メタ監査 根本原因 ②)** | PASS→live 変換 0 / 測定不能 (weekend_gap live N=0)。最短縮レバーは探索増産でなく live 層回収 (rnb 登録 / wg 執行契約 / E2_SILENT) | MEM project_process_meta_audit_2026_09_07.md |

---

## 4. base rate と「時間」の分解

- 実測 base rate ≈ **4.0%** [Wilson 0.7–19.5%] (家族級 verdict ~25 件中 OOS PASS 1)。外部仮説 explore→OOS 生存 **0/18**。両者は母集団が違う (前者は wave-0 内部 family weekend_gap を含む、後者は外部仮説スキャン系統のみ) — 引用時に混同しないこと。出所: MEM project_process_meta_audit_2026_09_07.md / round4 §4 / round5 §3.1 / daily-market-review-protocol §1。
- 外部較正: McLean–Pontiff 2016 (公表後 58% 減衰) / Hou et al. 2020 (多重補正下 82% 不通過)。当プロジェクトの候補は「既公表仮説」母集団から引いているので 0/18 は設計が厳しすぎる証拠ではなく母集団選択の必然 — round5 §3.1。
- 「次の live 有望セルまでの期待 family 数 ~53」は **未検証モデル (funnel-5 confidence medium)** — daily-market-review-protocol §1。
- メタ監査の分解: 「時間かかりすぎ」 = (a) 存在しないエッジの正当な棄却時間 + (b) 欠陥税 (PR の 55–70/195、潜伏中央値 ~124 日) / live 層故障 / enforcement 不在の待ち時間。**(b) だけが短縮可能** — MEM project_process_meta_audit_2026_09_07.md。
- 4 本のロック済みラインは**どれも金で前倒しできない** (pre-reg がトリガー前倒しを禁止) — round4 §4 U4 上程要点。

---

## 5. 未着手モダリティと障害の分類 (U4 材料の再整理)

| 障害分類 | 項目 | 概算コスト / 条件 | 出所 |
|---|---|---|---|
| **有償** | Databento CME (E12 歴史 + E13 12y) | ~$200–1,000/月 + 歴史従量。E12 verdict (2027-02) 後が合理的 | round4 §4 (a) |
| 有償 | OTC FX オプション面 (RR/BF) | ~$2k+/月 (Bloomberg/Refinitiv) or CME DataMine 数百$。U1「継続」時の第 1 候補 | round4 §4 (b) |
| 有償 | CLS FX Outstanding (E30) | 価格未取得、下 3 桁以上の可能性 | round5 E30 |
| 有償 | OANDA Data Services bucket positioning | ~$1,850/月 | MEM ws3 §8c |
| 有償 | 17 通貨 OTC IV パネル (E17/E24)、EBS/LSEG LOB (E19)、メディアトーン proprietary (E16) | — (horizon 不整合も併発) | round2/3 |
| **data-blocked (無料経路なし)** | BoJ 当預残高予想 / 短資会社経路 (E26) | BoJ 公表は事後 | round4 E26 |
| data-blocked | forward/swap curve (E5/E18) | spot only | round1/2 |
| data-blocked | AUD/NZD 国債利回り go-forward (WAF 403) / CHF SNB cube 凍結 2025-07-31 | 政策金利 (BIS) fallback のみ | e20 feasibility §3 D6–D8 |
| data-blocked | CME OI 歴史 (E14) | 今から蓄積のみ、verdict 最低 1y 先 | round2 E14 |
| data-blocked | CAD_JPY 価格 (in-repo ゼロ、1d/1h/15m 全て) | vix #7 再挑戦の障害の 1 つ | catalog wave-5 横断発見 |
| **禁止 (ban 正面衝突)** | CFTC TFF (E27)、ML OHLCV (E28/E31)、COT 全週次変種、slow-MR band fade 全着せ替え、VIX×JPY short 1–5d 同型、祝日フラグ D1–D2、BBO spread 状態、無条件イベント窓、サプライズ sign-follow M15、gotobi 昇格、E20 凍結 2 variant 同型 | 各原本 ban 条項 | catalog 各行 / MEM archive |
| **原則棄却** | 長ホライズン β (バラスト用途のみ)、E29 型 conditioning (正 EV ホスト不在)、grid/ナンピン archetype | — | round4 (d) / round5 E29 / wave-6 |
| **ライセンス決裁待ち** | TDW / WCB (CC BY-NC) — E23 secondary・復活経路 | user 決裁点 (E23 primary 単独では決裁不要と 09-04 確認) | catalog #25 / round4 §2.4 |
| **LOCK ゲート付き** | E13 tick volume 12y / anchored VWAP (CME 実約定 anchor 版) | E12 unsigned PASS (2027-02-05) 後のみ | catalog #10 / wave-4 L-c |
| LOCK ゲート付き | 「A 検出器 → B 回避設計」統合 | family A は FAIL したため、B は発言層なしで設計 (or 独立裁定)。#4 reverdict 11-14 後 | round4 §2.3 / MEM family_a |

---

## 6. 引用規律の要点 (本ノートの数字を再利用する際)

1. 「CB テキスト falsified」「口先介入に情報なし」「VRP falsified」型の引用は estimand 監査なしに禁止 (E23 = 測定可能性の否定、#27 = 検出力 0.130 領域の非有意、E22 = 検出力 8–17%)。
2. #27 引用時はカレンダー欠陥 (介入日 10→7) と null 構造欠陥 (20.3% が 5 block) を必ず併記。
3. 「供給ライン全滅 / 能動 0 本」型の会計は 09-17 に phantom blocker として訂正された前例あり — 本ノート §2 の「現在 0 本」は #27 FAIL (09-18) 後の推論であり、他に採用済み・未凍結の family が無いことは catalog 台帳 (#1–#28) の全行で確認済み。
4. weekend_gap の唯一 PASS は live 約定 0 — 「PASS セルがある」と「live に変換できた」は別 estimand (F2 2026-12-31)。
5. E1 / ECG / E12 の中間 outcome 量は本ノートに一切含めていない (P-10 型)。
