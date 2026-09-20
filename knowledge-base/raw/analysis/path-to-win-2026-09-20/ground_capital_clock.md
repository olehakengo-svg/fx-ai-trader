# Ground: 資本と時計の制約 (クオンツ監査ノート、2026-09-20、文書のみ・価格/DB 非接触)

規律: 正式ミッション = M3 系列 (+2〜3%/月 複利)、経路 M1→M2→M3、スコアリング分母 = time-to-M2 短縮 (U1=(b) 2026-09-17、`wiki/decisions/u1-mission-redecision-2026-09-17.md`)。旧 anchor 21.6%/20% は除去済み — 本ノートでは歴史文書の参照点としてのみ言及し、宣言・スコアリングには使わない。

---

## 0. 現在値 (一次ソース)

| 量 | 値 | 出所 | 確度 |
|---|---|---|---|
| NAV (実口座 JPY) | **¥275,517** (2026-09-14〜09-19 不動、broker tx 0 本) | `data/monitoring/nav_floor_projection.csv` 末尾行 (2026-09-19) / `wiki/index.md` L6 (¥275,516.83 @09-17) | verified (CSV/KB 実読) |
| floor | **¥262,000** = OANDA JP 残高条件 ¥250,000 + バッファ ¥12,000 | `tools/nav_floor_projection.py` L34 / `modules/status_volume_keeper.py` L74 (`SVK_NAV_FLOOR_JPY` default 262000) / `scripts/anomaly_watcher.py` L1011 | verified (コード実読) |
| floor までの余裕 | **¥13,517** | 上 2 行の差 | verified (算数) |
| days_to_floor (最新) | **242 日 → 2027-05-19** (method=fit, burn 55.8 JPY/日) | CSV 2026-09-19 行 | verified (CSV 実読) — ⚠️ 推定器の欠陥は §3 |
| 監査中心推定 | 2027-02〜04 (burn 82 JPY/日 audit_default、09-10 時点 days_to_floor≈164/165) | `wiki/decisions/process-meta-audit-2026-09-07.md` §2 goals-1 / `mission-capital-redecision-packet-2026-09-10.md` §U3 / CSV 09-07〜09-15 行 | stated-in-kb |
| OANDA API 存続条件 | Gold (前月取引量 USD 50 万、新規+決済双方カウント、毎営業日判定、昇格は翌月末まで) + プロコース + 残高 25 万 | `wiki/analyses/live-frequency-and-oanda-status-survival-2026-09-01.md` Part 1 (FAQ 720/1730 引用) | stated-in-kb |
| keeper 9 月実績 | rt_count **26** / volume **$520,000 / $520,000 (100%)**、last_rt 09-14T01:01Z、以後支出 ¥0 | `wiki/index.md` L122 (09-18) / L130 (09-17) | stated-in-kb (本番 API 実測の転記) |
| keeper 1 RT 実測コスト | **−¥80** (0.8p RT spread × ¥100/pip @10,000u)、時に −¥70 | `wiki/index.md` L149 (tx 709548〜709596) / L139 (tx 893148〜893159) | stated-in-kb (tx 単位で照合済) |

---

## 1. 算数 #1 — M2 = +0.5%/月 は現 NAV で何円・何 pips・何トレードか

NAV ¥275,517 基準 (**M2 定義 = NAV 実現月利、30d rolling** — `wiki/analyses/monthly-target-rederivation-2026-07-10.md` §4。NAV 実現なので keeper 支出も含んだ後の数字が対象)。

| 目標 | 月額 (円) | 1000u USD_JPY (¥10/pip) | 5000u (¥50/pip) | 10000u (¥100/pip) |
|---|---|---|---|---|
| **M2 +0.5%** (net) | **¥1,378** | **137.8 pips/月** | **27.6 pips/月** | **13.8 pips/月** |
| M3 +2% (net) | ¥5,510 | 551 p | 110 p | 55 p |
| M3 +3% (net) | ¥8,266 | 827 p | 165 p | 83 p |

pip 価値: USD_JPY 1000u = ¥10/pip (`wiki/analyses/lot-ladder-template-2026-08.md` L172 「10 JPY/p/1000u」、rederivation §2 AUD_JPY 1000u=10 と同型) — verified (算数)。

トレード数換算 (net M2、keeper 無視の場合):
- 1000u: EV +1p/t → 138 t/月、+2p/t → 69 t/月、+3p/t → 46 t/月。PASS 床 EV +0.5〜1p/t (rederivation §3) なら **138〜276 t/月**。
- 5000u: +3p/t → 9.2 t/月、+1p/t → 27.6 t/月。
- 現行 live 供給: 8 月 LIVE 14 件 (`live-frequency-...-09-01.md` Part 2)、9 月は 09-01 時点 0 件、LIVE 発火セル 3/30d (roadmap v2.3 M3 行) → 1000u × 14 t/月で M2 net を満たすには **+9.8p/t** が必要。

⚠️ packet §U2 の「現 NAV で M3 = 月 ¥6,500〜9,700」は 2〜3% × ¥276k = ¥5,520〜8,280 と一致しない (¥6,500〜9,700 は 2.35〜3.5% 相当)。分母か率のどちらかが本文と異なる — 引用時は再計算値を使う (inferred)。

---

## 2. 算数 #2 — keeper (Gold $500k/月) の摩擦コスト vs M2 【最重要】

### 2a. KB に既にある算数 (出所付き)
- **¥2,080/月 = 26 RT × ¥80 = NAV の ~0.75%/月、「M2 目標 +0.5%/月 を上回る恒常的な逆風」** — `wiki/index.md` L149 (09-04) / `wiki/log.md` L903, L932 (09-04/09-05)。
- **「M2 の必要エッジは keeper 込みで実質 +1.25%/月へ 2.5 倍化しているが再導出されていない」** — `process-meta-audit-2026-09-07.md` §3.5 goals-1 訂正版 (L91)。同 §7-8 で「keeper ¥5-7k/月」は REFUTED (target 到達で自動停止、上限 ¥2,080〜2,600)。
- **「M1/M2 の目標基準が keeper を差し引いた後の値か確認」= open item** — index.md L149 / log.md L932。**09-20 時点で KB 内に解消記録なし** (grep: roadmap v2.3 / m1-kpi-readout に net-of-keeper の記述なし) → 未消化。
- decision doc 見積「月 ¥1,000-4,000」(`status-volume-keeper-2026-09-01.md` 設計節) は実測 ¥2,080 で範囲内。

→ **「KB に算数はある」。ただし 3 箇所に散在し、M2/M3 定義文書 (rederivation §4、roadmap v2.3 KPI 表) には反映されていない。** 以下は再計算・拡張。

### 2b. 再計算 (NAV ¥275,517)

keeper 構造 (`modules/status_volume_keeper.py` L45-78, L298): USD_JPY 10,000u 市場即時往復、1 RT = $20k 出来高 (新規+決済)、月次 target $520k → **26 RT/月** (target は $500k + バッファ)。cost/RT = spread_pips × ¥100。

| シナリオ | RT/月 | 円/月 | NAV 比 %/月 | vs M2 +0.5% |
|---|---|---|---|---|
| **実測** spread 0.8p、26 RT (現行 target) | 26 | **¥2,080** | **0.755%** | **1.51 倍 (超過)** |
| 実測 0.8p、$500k ちょうど (25 RT) | 25 | ¥2,000 | 0.726% | 1.45 倍 |
| 最良 fill 0.7p × 26 RT | 26 | ¥1,820 | 0.661% | 1.32 倍 |
| **KB 標準 RT 摩擦 2.14p** (spread 0.7 + slip 0.5、`wiki/analyses/friction-analysis.md` L6) × 26 RT | 26 | **¥5,564** | **2.02%** | **4.04 倍** |
| 2.14p × 25 RT | 25 | ¥5,350 | 1.94% | 3.88 倍 |

- 出来高 $1 あたりのコストは lot サイズに**依存しない**: 0.8p → 0.008 JPY/unit ÷ 2 (往復で 2 倍カウント) = **0.004 JPY / $1 volume → $500k = ¥2,000 が spread 0.8p での下限**。size を変えても削れず、削れるのは spread (0.8→0.7p で −¥260/月) と RT 数 (26→25 で −¥80/月) のみ。edge trade の出来高 (8 月 $28k = 1.4 RT 相当 ≈ ¥112/月) は現状 target 計算に**含めていない** (`volume_usd` は SVK 自身の RT のみ加算、L298/L321) — 含めても効果 ≈ −¥100/月。
- 2.14p は edge trade の RT 摩擦 (slippage 込み) であり、keeper は同一秒内の market in/out で実測 0.8p → **keeper の estimand は 0.8p 行。2.14p 行はストレス上限**であって観測値ではない (index.md L149/L139 の tx 照合が根拠)。

### 2c. 帰結 — 構造的な算数破綻候補 (Rule 3 型)
1. **keeper の実測コスト 0.755%/月 > M2 目標 0.5%/月**。M2 が NAV 実現で定義されている限り、**edge 側は gross で +1.255%/月 = ¥3,458/月** を出さなければ M2 に届かない。
   - pips 換算: **1000u → 346 p/月、5000u → 69 p/月、10000u → 35 p/月**。
   - トレード換算 (1000u): +1p/t → 346 t/月、+3p/t → 115 t/月。現行 14 t/月では **+24.7p/t** 必要 (M1 検出可能最小エッジ 15.7〜27.7p/t と同水準 = 非現実、`live-frequency-...-09-01.md` Part 2)。5000u なら +5p/t × 14 t/月 で到達。
   - 監査 viability-2 訂正版は keeper **無視**でも「wg 級 1 本 L1=5000u で +0.46%/月 < 0.5%」(process-meta-audit §3.7)。keeper 込みでは wg 級 L1 が **≥3 本**相当必要 (0.46 × 3 = 1.38% > 1.255%)。
2. **M3 も keeper 込み gross は +2.755〜3.755%/月 (¥7,590〜10,346)**。
3. **keeper と floor は結合している**: keeper だけで NAV は月 ¥2,080 減 → 余裕 ¥13,517 は **6.5 ヶ月 (edge PnL=0 仮定) → 2027-04 上旬**に floor 到達。**Gold を spread で買い続けると、edge が月 +0.755% 以上 (= M2 超) を出さない限り、残高条件の方が先に割れる**。2.14p ストレスなら 2.4 ヶ月。
4. keeper には `nav_floor < ¥262,000 → 発注停止` ガード (L74, L235) があるが、これは floor を守るのではなく **失敗モードを「残高割れ」から「翌月 Gold 失効」に変えるだけ** — どちらでも API 停止。

---

## 3. 算数 #3 — floor 到達推定の前提と keeper の含まれ方

### 3a. 推定器 2 本 (`tools/nav_floor_projection.py`)
| method | 定義 | keeper 含む? |
|---|---|---|
| `audit_default` | burn = **82 JPY/日** 固定 = (276,304 − 262,000)/~175d。コメント L35-36 で「keeper ~¥2,080/月 + エッジドリフト」と明記 | **含む (明示)**。分解: keeper 2,080/30.44 = **68.3 JPY/日 (83%)**、残余 13.7 JPY/日 ≈ **¥416/月 (17%)** = エッジドリフト想定 |
| `fit` (行数 ≥7 で自動切替、窓 60 行) | CSV の (date, nav) 直近行の線形回帰 slope | **暗黙に含む (NAV 実測に keeper 支出が乗っている分だけ)** — ただし §3b の季節性欠陥 |

### 3b. fit 推定器の構造欠陥 (Rule 3 型、検知器の estimand 不一致)
- keeper は **月初に前倒し**で走る (3 RT/日 × 26 RT ≈ 9 営業日で target 到達 → 09-14 に完了、以後 ¥0)。NAV は「月初 2 週間で −¥2,080、残り 2 週間フラット」の**周期構造**。
- fit は 7 行 (~7 暦日) から発動し、9 月の観測は「09-07〜09-14 下降 → 09-14〜 フラット」。フラット行が積み上がるごとに slope が縮み、**burn 74.8 → 64.3 → 55.8 JPY/日、days_to_floor 164 → 242 (5 日で +78 日)、floor_est 2027-02-25 → 2027-05-19** (CSV 09-15〜09-19 行)。10 月 1 日から keeper が再稼働すれば逆に急増する。**周期 30 日の burn を 7〜60 行の窓で線形回帰する推定器は月内位相で振動する** — `MIN_ROWS_FOR_FIT=7` は keeper 周期 (30 日) より短い。
- F4 トリガ (`prereg-trigger-registry.json` `project-falsification-f4-nav-floor-clock`、条件 days_to_floor ≤ 90) は **この振動する数字を読む** → 発火日が月内位相で前後し、フラット期には「安全」寄りに偏る (今は 242 日 = 発火まで 152 日 ≈ 2027-02-18 と読めるが、audit_default では 164 − 90 = 74 日後 ≈ 2026-12-03 発火)。packet §U3 の「2026-11〜12 発火」は audit_default 前提。
- CSV 行に欠落 (09-08, 09-09, 09-13) — 書き手 daily-report.yml が毎日書いていない (registry の「7 日未更新 = 書き手死亡」閾値内ではあるが、fit の点密度に影響)。
- 正しい estimand 候補: **月末→月末の NAV 差分 (keeper 1 周期を必ず含む)** または窓 ≥ 30 暦日の最小長を課す。または burn を「keeper 確定分 (target × cost/RT、決定論) + edge 実現 PnL の 30d 実測」に分解して加算 — keeper 分は推定不要。

### 3c. 到達推定の再計算 (余裕 ¥13,517)
| burn 前提 | days_to_floor | floor 日 | F4 (−90d) 発火 |
|---|---|---|---|
| audit_default 82/日 | 164 | 2027-03-03 | 2026-12-03 |
| keeper のみ 68.3/日 (edge PnL=0) | 198 | 2027-04-06 | 2027-01-06 |
| fit 現値 55.8/日 | 242 | 2027-05-19 | 2027-02-18 |
| keeper 2.14p ストレス 182.8/日 | 74 | 2026-12-03 | **既に発火圏** |
| keeper 停止 (U3 (ii) 縮退) + edge 0 | ∞ (sentinel 99999) | — | — (ただし翌月 Gold 失効 → API 停止) |

- ⚠️ process-meta-audit §2「7 月以降 ≈−0.47%/月 (keeper コスト支配)」は整合しない: keeper 初 RT は 2026-09-02 (`project_oanda_status_api_survival_2026_09_01.md`) なので 7〜8 月の drift に keeper は含まれない。−0.47%/月 ≈ ¥1,300/月 は keeper 前の edge+事故ドリフト。keeper 加算後の実効 burn は ¥2,080 + (edge drift) で、audit_default の 82/日 (= ¥2,496/月) はこの和に近い (inferred)。

---

## 4. DD 防御 0.2x の意味

- `modules/risk_analytics.py` L382-388 `DD_LOT_TIERS`: DD≥8% → **×0.20** / ≥6% → 0.40 / ≥4% → 0.60 / ≥2% → 0.80 / <2% → 1.0 (verified)。
- dd_pct 分母 = `OANDA_EQ_BASE_PIPS` (default 1000.0、`modules/demo_trader.py` L993) の pip 基準、eq_peak **非減衰 (ラチェット)**。2026-07-10 時点 eq_peak +16.9 / eq_current −991.1 → **0.4x 復帰に +928.1p、1.0x に +988.2p の回復が必要 = 取引による解除は数学的に不可能、解除 = 再基準化のコード変更 (user 決裁)** (`shortest-path-decision-memo-2026-07-10.md` §1c / rederivation §2)。stated-in-kb、07-10 の数値で以後の更新なし。
- lot chain: 0.2x × `OANDA_FORCE_FLAT_UNITS` 5000 → **実効 1000u**、絶対上限 `_OANDA_LOT_CAP = 10000` (`demo_trader.py` L10237、verified)。lot ladder L0 = 1000u (min-lot bypass) と一致 → **現状は「0.2x 防御」と「L0 階段」が同じ 1000u に縮退**しており、M2 の 5000u (L1) へ行くには (a) 再基準化 or (b) `edge_cell_promote` force-live の L1 経路 (ladder 配管) が必要。
- ladder 側の binding (`project_lot_ladder_template_frozen_2026_08_05.md`): wg は disaster SL 150p で **L1=5000u が実質上限 @NAV 326k**、L2 は NAV≥600k or SL 再設計 R1。現 NAV ¥275k では L1 の制約 4.2 (worst-case ≤2.5% NAV = ¥6,888) に対し 5000u × 150p × ¥10 = ¥7,500 で **違反** (template 表は NAV 326k 前提で ¥7,500 = 2.3%) → **現 NAV では wg の L1 も不成立** (inferred、要 `lot_ladder_calc.py` 再計算)。

---

## 5. 未決裁 U2 / U3 / U5 (packet 2026-09-10、U1 は 09-17 決裁済)

| # | 内容 | 選択肢 | 無回答時の既定 | 期限 |
|---|---|---|---|---|
| **U2** | M3 統計確認後に投入しうる**資本上限を 1 数字で凍結** (ladder L2+ / exposure cap の分母) | 現 NAV ¥276k のまま (M3 = 月 ¥5.5〜8.3k 再計算値) / ¥1M (月 ¥20〜30k) / ¥10M (月 ¥200〜300k)。凍結しない = 「研究プロジェクト」の暗黙決裁 | F4 発火時に再上程 | U1 と同時 (2026-10-15 推奨) — **超過中ではないが未決** |
| **U3** | NAV floor 前の決裁点を事前設定 | (i) 入金 (額は U2 連動) / (ii) 縮退 = keeper 停止 + shadow 蓄積のみ (API 停止・Gold 放棄を受容) / (iii) 停止 | F4 発火時に再上程 | **2026-11-30** (F4 発火前) |
| **U5** | Codex 実行チャネル正式廃止の残り 1 手 = Render dashboard で `fx-codex-runner` を **Suspend** (API/MCP 経路なし、user のみ) | Suspend / 課金継続 | worker 課金継続 | 期限なし (純コスト継続) |

- U4 は 09-17 に推奨手順 (feasibility 先行、`wiki/analyses/supply-space-feasibility-2026-09-17.md`) 採択、仮決め 10-15/10-18。同メモ §資本: 「可動余剰 ≈ ¥13.5k、既存口座から取引資本を割く選択肢は物理的に存在しない」。
- U3 (ii) を選ぶと keeper 停止 → burn は edge drift のみになるが翌月 Gold 失効で API 停止。U3 (i) は keeper 継続を前提にすると **入金額 = 毎月 ¥2,080 の消耗 + edge drift を何ヶ月分賄うか**で決まる (12 ヶ月なら ¥25k + drift)。

---

## 6. M1 / M2 / M3 の円・pips・トレード数訳

| 段 | 定義 (出所) | 円/月 @¥275,517 | pips/月 | トレード数 / 到達条件 |
|---|---|---|---|---|
| **M1** | clean live (`oanda_trade_id != ''`) 30d PnL の統計確認済み符号転換。強定義 = セル単位 live N≥30 の正EVセル ≥1 ∧ book Wilson 下限 >0 (rederivation §4)。roadmap v2.3 KPI 表は弱定義「30d PnL>0」で併存 (goals-3) | 金額目標なし (符号のみ) | 符号のみ。09-04 +19.8p/N=15 MET_UNDERPOWERED → 09-07 −22.4p NOT_MET (roadmap v2.3 M1 行 / process-meta-audit goals-3) | **セル単位 N≥30**。最速 live セル carry_dip 2.10/週 → ~3.3 ヶ月/セル。統計判定 (+3p/t、80% power) は N=385 = 現 14/月で 27.5 ヶ月 (`live-frequency-...-09-01.md`)。**M1 は keeper と無関係** (keeper は DB 非経由、clean live 母集団に入らない — `status-volume-keeper-2026-09-01.md` データ規律) |
| **M2** | +0.5%/月 NAV 実現 30d rolling。M1 + 防御解除ラダー (0.2x→1000u→5000u) + **2 セル以上** | **net ¥1,378 / gross (keeper 込) ¥3,458** | net 138p@1000u / 27.6p@5000u ; **gross 346p@1000u / 69p@5000u / 35p@10000u** | 1000u: gross +3p/t で 115 t/月 (現 14 t/月の 8 倍)。5000u: +5p/t × 14 t/月。監査: wg 級 L1 単独 +0.46% < 0.5% (keeper 無視)、keeper 込みでは wg 級 L1 ≥3 本相当。中央シナリオ **2027-Q4〜2028** (viability-2 訂正版、keeper 未反映) |
| **M3** | +2〜3%/月 (return 版) = 正EVセル **5 個以上** + Kelly Half + FLAT units 再スコープ。throughput 版 (clean live N≥30 セル ×3) が roadmap v2.3 に併存 (goals-4) | **net ¥5,510〜8,266 / gross ¥7,590〜10,346** | net 110〜165p@5000u ; gross 152〜207p@5000u (5 セル合算) | ETA 最短 ~14 ヶ月 (2027-11)、return 版は 2027 年内径路確認できず、中央 2029+ (process-meta-audit §2, §3.7)。U2 未凍結のため「M3 達成時の月額」は現 NAV の ¥5.5〜8.3k が既定 |

---

## 7. 監査所見サマリ (重要度順)

1. **[Rule 3 算数破綻候補・最重要] keeper 実測コスト 0.755%/月 (¥2,080) > M2 +0.5%/月。** KB 3 箇所 (index.md L149 / log.md L903,L932 / process-meta-audit goals-1) が既に指摘、必要 gross +1.25%/月も記載済みだが、**M2/M3 定義文書 (rederivation §4 / roadmap v2.3 KPI 表) に未反映、open item「目標基準は keeper 差し引き後か」未解消**。M2 は「+0.5%」ではなく実質 **「edge gross +1.255%/月 = 346p@1000u」**。
2. **[結合] keeper のみで floor 余裕 ¥13,517 は 6.5 ヶ月 (→2027-04 上旬)。** Gold 維持コストが残高条件を侵食する構造 — U3 は「keeper を続けるか」と同義であり、続けるなら入金額が算数で決まる。
3. **[検知器欠陥] F4 fit 推定器は keeper の月内周期 (前倒し 9 営業日 → フラット) で振動** (5 日で days_to_floor 164→242)。`MIN_ROWS_FOR_FIT=7` < 周期 30 日。発火日は位相依存。estimand を「月末差分」または「keeper 確定分 + edge 実測」に分解すべき。
4. **[整合性] packet §U2 の M3 月額 ¥6,500〜9,700 は 2〜3% × ¥276k = ¥5,520〜8,280 と不一致**; process-meta-audit §2「7 月以降 −0.47%/月 (keeper コスト支配)」は keeper 開始 09-02 と時系列不整合。
5. **[階段] 現 NAV では wg 級セルの L1 (5000u) は制約 4.2 (≤2.5% NAV) を ¥7,500 > ¥6,888 で違反 (inferred)** → 0.2x 防御を解除しても ladder が 1000u に縛る可能性。5000u 前提の M2 pips 換算 (27.6p) は現 NAV では使えず、1000u 換算 (138p net / 346p gross) が実効。
6. **[未決裁]** U2/U3/U5 とも未決。U3 期限 2026-11-30、audit_default 前提なら F4 は 2026-12-03 発火 = 期限直後。

## 8. 引用注意
- 2026-07-10 文書群 (shortest-path memo / rederivation) の「21.6%」「60,244 JPY/月」は **U1=(b) で除去済みの旧 anchor** — 本ノートでは DD 0.2x / lot chain / M 定義の出所としてのみ参照。
- `project_oanda_status_api_survival_2026_09_01.md` の「10 月 SILVER 降格見込み / kalman fill ゼロ」は stale (09-17 更新で keeper $520k 到達・kalman 初 fill #859468 発生済み)。
- P-10 LOCK (E1 10-15 / ECG 11-06 / E12 2027-02-05) には非接触 — 本ノートは価格・DB 計算ゼロ。
