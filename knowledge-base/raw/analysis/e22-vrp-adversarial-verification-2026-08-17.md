# E22 fx_variance_risk_premium (台帳 #24) 敵対的検証 — 2026-08-17

**検証者**: adversarial verifier (独立セッション、worktree `research/e22-vrp-explore-2026-08-17`)
**対象**: `knowledge-base/raw/analysis/e22-vrp-explore-candidate-2026-08-17.json` + `knowledge-base/wiki/decisions/e22-vrp-explore-prereg-2026-08-17.md` (DRAFT) + `tools/e22_vrp_explore.py` (513 行、コード監査済み)
**照合**: scan round-3 §2/§2.1 / cc-mr pre-reg (2026-08-05) / hypothesis-catalog (台帳・ban) / ppp pre-reg (IC 型前例)
**接触規律の自己宣言**: 本検証で IC(VRP, fwd) および signal 値×outcome の join は**一切計算していない**。実測は signal 側統計・無条件 fwd 分散 (pass-1 相当)・OOS は EVZ 側/FX 側を**別々にカウント** (join なし、OOS シグナル行は未生成)。

---

## VERDICT: **GO-WITH-CONDITIONS (全 17 条 / blocking 10 条)**

一行理由: 設計核 (two-pass / 両側登録→g 条件付け / circular-shift null / 正直 MDE / §2.1 逐語内蔵 / ban 差分節) は健全で cc-mr 水準に達しているが、**explore 窓内に未開示のベンダー穴 (2020-10-23→11-16、米大統領選挙週を含む 16 取引日) を実測発見**、加えて凍結文書の数値誤り 3 件 (窓被覆 2,061→実測 2,051 / swap −2.9%/yr は panel に不存在 / stale run 3 件→実測 7 件) と OOS 側ハーネスの構造ギャップ 2 件があり、これらの解決なしの凍結は認めない。

---

## 条件表 (§10 マッピング対象)

| # | B/n | 内容 | 根拠 (実測値) |
|---|---|---|---|
| 1 | **B** | **2020-10 ベンダー穴の処置**: `EUR_USD_15m.parquet` は explore 窓内 **2020-10-23→2020-11-16 (24 暦日、取引日 16 日、米大統領選挙 2020-11-03 を含む)** が欠落 — MEMORY 既知の MASSIVE ベンダー欠損窓 (2020-10 系) の**未修復残存**。ハーネスの guard は正しく機能し silent 汚染なし (returns_void=1 / rv_void=21 / fwd_void=21 に全て整合) だが、**pre-reg §2 の「QA 実測済み」表がこの穴に無言**なのは凍結文書として不可。解決 = (推奨) `cc_mr_gap_backfill.py` 前例の OANDA mid backfill (既存行不変 assert + census 再実測 + **manifest は backfill 後に生成**) / (最低限) §2 に穴の on-record 開示 + void 会計 + 「選挙週 obs 不在」の事前記録。正直な深刻度: 窓内 EVZ 実測 6.1–9.23 (explore 分布の ≤p74.7、explore 最大 19.31=2020-03-18 は保持) — 極値 censoring は限定的、影響 ≈ 16 欠落日 + ~42 void ≈ panel の 2.8% | 実測: D1 gap census で 2020-10-23→11-16 のみが年末休場以外の >4 暦日 gap。2020 有効 N=196 vs 他年 257–260 |
| 2 | **B** | **§2 窓被覆数値の訂正**: 「explore 窓 FX D1 = 2,061 日」→ **実測 2,051**。最終有効 N = **2,009** / 非重複窓 = **95** (98 でない) / IC MDE = **0.287**。曜日 share 「0.199–0.201」→ 実測 **0.1980–0.2014**。条件 1 の処置後に再実測し、実測値で凍結する (EVZ print 2,017 は正しい) | 実測: 2,051 / 2,009 / 95 / 0.2873 / [0.2014, 0.2009, 0.2004, 0.1994, 0.1980] |
| 3 | **B** | **§7 swap 量級 pre-record の訂正**: 「2018–19 の d ≈ −2.9%/yr」は凍結 e20 panel に**不存在** — 実測 2018 平均 **−1.779** / 2019 平均 **−2.158** / panel 全期間最小 **−2.375 (2018-12-20)**。adverse 例は panel 最小で ≈ **−36〜−38p/obs** (m=1.65、30 暦日、S≈1.15) に再計算して記載。「swap が支配的摩擦になり得る」結論自体は保存される。あわせて e20 列のレート規約 (MRO 型 policy rate、預金金利ではない — −2.9 は deposit-rate 算術の混入と推定) を §7 に明記 | 実測: 符号検証 2013-01-02=+0.625 ✓ / 2022-12-29=−1.875 ✓ / 40p 例の再計算 −38.0p |
| 4 | **B** | **OOS swap 延伸ファイルの仕様凍結**: ハーネス `load_swap(oos=True)` は `e20_carry_level_ext_2026-08.csv` **のみ**を読む。延伸が「2023-01..2025-04 の補完」だけだと **2022 年の OOS シグナルは ffill 起点不在 → NaN assert でクラッシュ** (§7 の宣言と実装が不整合)。解決 = (i) 延伸ファイル = 2013-01..2025-04 フル被覆 (or union ローダー) と pre-reg に明記、(ii) 重複日付の凍結 csv との等値 assert、(iii) sha256+行数の manifest 追補を **OOS touch 前に別コミット**で凍結 | コード実測: `reindex(union).ffill()` は延伸開始日前の日付を埋められない |
| 5 | **B** | **pass-1 firewall 条項の明文化**: pass-1 成果物に **per-date の forward 値を一切含めない** (無条件 fwd21 は aggregate 分位のみ) を §4 に明文で凍結。現ハーネスは適合済み (PASS1_CSV = signal 列のみ / JSON = median/sd/p25/p75) — 退行防止の pin。これで「pass-1 の無条件 fwd 分散 = 符号 peek」懸念は構造的に消える (|move| は符号不変量、cc-mr pass-1 前例と同型) | コード実測: `panel[["evz","evz_staleness","evz_stale_run3","rv21","vrp"]].to_csv` ✓ |
| 6 | **B** | **OOS モードの機械ロック強化**: 現行ロック = pass2 JSON verdict PASS + `--unlock-oos` + OOS_JSON 不在 assert。cc-mr の「OOS モード自体が存在しない」より弱い。解決 = OOS 実行前に **pass-2 verdict 成果物が git commit 済みであることを assert** (`git ls-files` / rev-parse 照合) を追加 + 単一接触の意味論を事前宣言 (「成果物出力前のクラッシュ再走は接触 1 回に数える / OOS_JSON 書出後の再走は恒久禁止 — 現 assert が担保」)。explore モードが 2022+ シグナル行を生成しないことはコード検証済み (窓フィルタ) | コード実測: `run_oos` asserts 3 点確認、explore 窓フィルタ ✓ |
| 7 | **B** | **FAIL 時クローズ文言に power caveat 義務付け**: §9 の恒久クローズ節に「**FAIL は効果不在の証明ではない (文献級 IC 0.05–0.15 への検出力 8–17%)。クローズの根拠は『無料経路での retail-viability 不成立 + 供給ライン経済性』**」を必ず併記。将来の「VRP は falsified」型過大引用の遮断 (user 恒久指示 2026-08-05 = 過去 verdict の estimand 監査に正面対応)。復活経路 (有償 OTC 面 + 新 family + 新敵対的検証) は現行どおり | 設計自身の §6 記載 (MDE 0.287 vs 文献 0.05–0.15) との整合 |
| 8 | **B** | **Gate D に RT 6.0p (3×) 感度の報告義務**: NY17 close 測定 convention は rollover 死圏に隣接、qs #17 実測は「異常時 RT = 正常の 2–3 倍」— stressed 4.0p は 2× 側のみ。binding は凍結どおり 4.0p のまま、**6.0p (3× 端) の gate D 感度を非拘束で報告** + honesty 条項「将来のいかなる実装経路も 17:00 NY 実スプレッド実測を必須とする (本測定は歴史 mid であり執行可能性を主張しない)」を §7 に追加 | qs #17 実測 2–3× / cc-mr §3 冬スプレッド honesty 条項の前例 |
| 9 | **B** | **stale-print 実測の訂正**: 「explore 窓内は 2021 年の 3 run (4/6/6 連) が主」→ 実測 **7 run** (2021-02-09:4 / 04-01:3 / 04-07:3 / 05-07:3 / 06-09:3 / 07-01:6 / 08-06:6 — 全て 2021)、帰属 day share **1.48%**。knife-edge (v) の設計は不変、数値のみ訂正 | 実測: run≥3 全 30 件中 explore 窓 7 件、96.7% が 2021+ |
| 10 | **B** | **circular-shift null の実測正当化を §6 に事前記録**: 実測 VRP ACF = **lag5: 0.63 / lag10: 0.33 / lag21: −0.09 / lag42: +0.02** → 脱相関長 ≈ 15–20bd < MIN_SHIFT=42 で**シフト最小距離は妥当** (シフト対象は VRP であり EVZ 単体 [ACF42=0.62] でないことが要点)。残余の小シフト相関は null を保守側 (false-kill 方向) に振ることも事前記録。pass-1 で ACF を再実測し report 記載 | 実測値どおり — 検証者測定で設計は**支持**された。記録義務のみ |
| 11 | n | payload `non_goals` の「no E23 contact (08-28 gate)」は stale — E7 verdict は 2026-08-17 に前倒し着地済みで E23 ゲートは解除されている。E22 verdict 前に E23 が起動する場合は既存の BH q=0.10 分母合流条項が governs、と参照を更新 | 台帳 #9 verdict 2026-08-17 |
| 12 | n | 「explore→OOS 生存 0/15」の正直 prior に脚注: weekend_gap #3 (arm B) は explore→OOS 生存の反例 (内部 family)。scan §2.1 逐語 quote は不変のまま、quote 外に「外部/新規 family 系統の計数」と脚注 | 台帳 #3 family PASS (2026-07-24) |
| 13 | n | gate F false-kill の定量事前記録 (cc-mr 水準): 真 IC 0.10 なら年次符号一致率 ≈0.6 前後 → P(≥6/8) ≈ 0.3–0.4 = **false-kill ≈60–70%**。「準コイン投げ」の定性記述を数値化 | cc-mr §5 「≈50% 事前記録」前例 |
| 14 | n | gate G は tercile 3 分位 = 隣接差分 2 本しかなく「違反 ≤1 ∧ T3−T1 符号」はほぼ T3−T1 符号のみと等価 (ppp quintile 版より弱い)。凍結のまま可 — 弱さを on-record 化のみ | 構造的事実 |
| 15 | n | §1 負の prior に 1 行追加: E24 棄却を補強した 2026 年研究「currency vol risk の予測力は 3 ヶ月超 horizon」は **21bd 設計への負の prior でもある** (estimand は別 [cross-section vs 単一ペア時系列] なので ban ではない) | scan §3 E17/E24 行 |
| 16 | n | living-cache drift: `EUR_USD_15m.parquet` は日次更新されうる生キャッシュ — 凍結コミットと測定を同一セッションで行う (sha assert は fail-safe に働くが、drift 時は manifest 編集でなく再凍結コミット)。EVZCLS (系列終了・確定) / e20 csv (静的) は問題なし | audit.json stale (311,035 vs 317,002) 実測 = drift の実在証拠 |
| 17 | n | EUR_USD の実勢 financing snapshot 照合は不在 (cc-g0-rt sampler は 3 クロスのみ)。m_adverse=1.65%/yr は cc-mr 実測 implied (1.075–1.155) の 1.4–1.5 倍で保守側 — 継承は妥当、照合不能である事実のみ §7 に正直記録 | cc-mr §7 実測 markup |

---

## 実測検証セクション (QA スポットチェック、全て本検証で独立再実行)

### 検証 PASS (payload/pre-reg 主張と一致)

| 主張 | 実測 | 判定 |
|---|---|---|
| EVZCLS 4,529 行 / 欠損 169 / 有効 4,360 / 2007-11-01→2025-03-11 | 4,529 / 169 / 4,360 / 一致 | ✓ |
| 単位 = 年率 vol point (4.13–30.66、p50 8.82) | min 4.13 / max 30.66 / p50 8.82 | ✓ |
| 欠損 = 米祝日 placeholder ~9.8/y | 9.74/y | ✓ |
| stale run≥3 = 30 件 / max 8 (2024-10-02) / 大半 2021+ | 30 / 8 @2024-10-02 / 96.7% が 2021+ | ✓ (窓内件数は条件 9) |
| parquet 317,002 行 / 2013-10-24→2026-08-17 / UTC open-label | 317,002 / 一致 / 日曜初バー **21:00 UTC (2018-07 夏) かつ 22:00 UTC (2015-01 冬)** = NY17 アンカー実証 (payload の夏サンプルを冬側でも補強) | ✓+ |
| 週末ラベル bar 1,587 | 1,587 | ✓ |
| bars/week p50=5.0 / bars/day p50=96 / <40 bars 日 = 15 | 5.0 / 96.0 / 15 | ✓ |
| EVZ↔FX 同日一致 97.1% / staleness p95=0 / max 3 暦日 | 0.9714 / p95=0 / max 3 | ✓ |
| RV21 最初の有効シグナル ≈ 2013-11 末 → 2014-01-01 全域適格 | 2013-11-22 | ✓ |
| EVZ print (explore 窓) 2,017 | 2,017 | ✓ |
| swap panel 2013-01-01→2022-12-30 = explore 完全被覆 / 符号検証 2 点 | 一致 / +0.625 / −1.875 | ✓ |
| audit.json stale (311,035 / 2014-01-05) | 311,035 / 2014-01-05T22:00Z | ✓ |
| `EUR_USD_1d_2014_2026.parquet` 週末行 714 (使用禁止の根拠) | 714 | ✓ |
| RT point 2.0p の出典 (friction-analysis 表) | EUR_USD 行 **2.00pip** 確認 | ✓ |
| \|r\|>5%/d assert は explore で非発火見込み | 実測 max \|r\| = 3.02% | ✓ |
| P-10 / E20 firewall のコード構造 | `columns=["Close"]` + assert / signal builder は e20 csv 非アクセス (swap は gate D join 後のみ) | ✓ |
| scan §2.1 の pre-reg §9 への逐語内蔵 | 4 bullet 全文一致 | ✓ |

### 検証 FAIL (虚偽/誇張 — 条件 1/2/3/9 で解決)

| 主張 | 実測 | 乖離 |
|---|---|---|
| explore 窓 FX D1 = 2,061 日 | **2,051 日** | −10 日 (条件 2) |
| 実効非重複窓 ~98 (2061/21) / MDE ~0.28 | 最終 N **2,009** / 窓 **95** / MDE **0.287** | 条件 2 |
| (未開示) 窓内データ穴なしを示唆する QA 表 | **2020-10-23→11-16 の 24 暦日穴 (16 取引日、選挙週含む)**、2020 有効 N=196 | 条件 1 |
| 「2018-19 d ≈ −2.9%/yr → adverse ~40p/obs」 | 2018 平均 **−1.779** / 2019 **−2.158** / panel 最小 **−2.375** → adverse ≈ −36〜−38p | 条件 3 |
| explore 窓 stale run = 「2021 年の 3 run (4/6/6)」 | **7 run** (4,3,3,3,3,6,6) | 条件 9 |
| 曜日 share 0.199–0.201 | 0.1980–0.2014 | 条件 2 (軽微) |

### 検証者による追加実測 (設計の較正確認)

- **gate A 余裕**: 無条件 median \|fwd21\| = **138.8p** vs floor 40.0p = **3.47×** — knife-edge ではない (p25=63.7 / p75=250.0、sd=230.8p)。
- **gate B 余裕**: N=2,009 vs 1,500 / 窓 95 vs 70 — knife-edge ではない (条件 1 backfill 後は N≈2,06x に増える)。
- **tercile-mean MDE (cluster-worst)**: 2.487×230.8/√95 ≈ **58.9p** — gate D の「mean net > 0」に対し、真の効果が文献級なら構造的に届かない帳簿であることを再確認 (§1 の「意図された kill attempt」framing と整合)。
- **OOS power の side-count 事前確認 (join なし)**: FX D1 (2022-01-01..2025-03-11) = **831 日** / EVZ print 同窓 = **799 本** → OOS N は floor 600 / 窓 28 を join なしで余裕クリアの見込み — OOS UNDERPOWERED 分岐が実質デッドレターでないことも確認 (EVZ 側が縮む series 終端リスクなし、系列は確定終了済み)。
- **VRP ACF (条件 10 の根拠)**: lag5 0.63 / lag10 0.33 / lag21 −0.09 / lag42 +0.02 — VRP は EVZ (lag42 ACF 0.62) と違い高速脱相関。MIN_SHIFT=42 は実測上十分。
- **VRP 分布 (signal 側のみ)**: p5 −1.87 / p50 +0.95 / p95 +3.05 vol point — IV premium の存在と整合、単位整合の傍証。

---

## 5 レンズ分析

### A. 統計設計 — 健全 (条件 10/13/14 で補強)
- **両側登録 → pass-2 で g に経済 gate を条件付ける構造**: 健全。符号多重性は gate C の両側 p が負担し、D–G は連言 (conjunctive) の整合チェックであり選択自由度を追加しない。OOS 片側化は holiday レグ a / cot #16 前例どおり。
- **circular-shift permutation**: overlapping daily 21bd 設計に対し、シグナル・リターン両系列の自己相関を保存し cross-alignment のみ破壊する正しい null。block sign-flip (returns 側) との比較は knife-edge (ii) に診断併記で配置済み — 「(ii) は符号を生まないので sign-flip 判定に入らない」というハーネス実装は pre-reg 文言と整合。シフト最小距離 42 は**実測 VRP ACF で支持** (条件 10 で記録義務化)。
- **gate F 較正**: 年次 N≈196–260 で年次 IC は高分散 — false-kill ≈60–70% (真 IC 0.10)。binding 維持は cc-mr/#19 前例どおり gate-shopping 回避として正当、数値の事前記録のみ要求 (条件 13)。
- **tercile (quintile でなく)**: 実効 95 窓では quintile 極値 bin ≈19 窓で薄すぎ — tercile 選択は妥当。gate G が実質 T3−T1 符号チェックに縮退する弱さは on-record 化 (条件 14)。
- **MDE の正直さ**: 0.287@95 窓、文献効果への検出力 8–17% の自己申告は正直。gate B が N floor のみで定義され「power 不足の言い訳」経路を塞いでいるのも cc-mr 継承で正しい。**ただしこの正直さの帰結として条件 7 (FAIL ≠ falsification の caveat) が必須になる。**

### B. データ整合 / leakage — 1 件の重大未開示 (条件 1) + OOS 実装ギャップ (条件 4/6)
- **EVZ 16:15 ET 先行主張**: 成立。EVZ は FXE (ETF) オプション由来で CBOE の当日 close print は 16:00–16:15 ET 帯に確定、FX D1 close (17:00 ET) に 45–60 分先行。FRED observation_date = 当日 close 値 (系列は 2025-03 で公表終了・確定 = revision リスクもゼロ)。RV21 が当日 return を含む定義とも整合 (シグナル確定時刻 17:00 NY で両入力とも利用可能、45 分の測定時刻差は lookahead でなくノイズ)。
- **staleness join**: as-of backward + >3 暦日 void — 実測 p95=0 / max 3 で設計どおり。
- **explore 窓リターンの 2022-01 食い込み**: cc-mr §3 と同型の on-record 許容 — outcome 完了であって OOS シグナル接触ではない。適法。
- **OOS 単一接触の構造保証**: explore モードが 2022+ シグナル行を生成しないことはコード検証済み。ロックの機械形は cc-mr より弱いので条件 6 で強化。
- **ベンダー穴**: 条件 1 のとおり。guard 群 (span>45 / gap>7 / \|r\|>5%) が正しく発火しており**測定の汚染はない** — 問題は凍結文書の開示義務と標本の選挙週欠落のみ。

### C. 多重性 / プロセス — m=1 成立
- **m=1**: 台帳実査 — #21 クローズ (08-05)、#9 E7 verdict 着地 (08-17)、#20 PARK、#22/#4/#8/#10 は forward LOCK 別枠、#23 E21 は診断枠。**アクティブ explore 0/3 → 本件 1/3 は正**。worktree/branch 実査でも競合 draft なし (cc-mr 時の並行セッション競合の再演なし)。BH q=0.10 合流条項も内蔵済み — E23 が early unlock された事実だけ参照更新 (条件 11)。
- **two-pass**: pass-1 に「リターン系ゼロ + 無条件 fwd 分散」を置く設計は、\|move\| が符号不変量である限り符号 peek にならない — ハーネスは per-date fwd 値を非出力で適合済み (条件 5 で明文 pin)。
- **knife-edge の選択転化防止**: 全 gate PASS 後のみ・符号反転=FAIL・選択不使用 — cc-mr 同型で健全。
- **claim 範囲**: family-pooled EUR_USD 恒久限定 ✓。

### D. 摩擦 / 経済 — 概ね保守的 (条件 3/8/17 で補正)
- **swap 式**: 構造検証 ✓ (side×d−m、負=コスト、1%/yr ≈ 9p/21bd@S=1.15)。markup は両サイド減算 = 保守的。cc-mr の worse-of(snapshot) が EUR_USD には存在しない点は条件 17 で正直記録。
- **量級 pre-record の誤り**: 条件 3 (−2.9 は panel に不存在)。訂正後も「21bd 設計では swap が支配的摩擦になり得る」は成立 (−36〜−38p vs RT 4p)。
- **stressed_RT 4.0p**: NY17 死圏隣接に対し 2× 側のみ — 条件 8 で 3× 感度 + 実装時 honesty 条項。gate A (10×=40p vs 実測 138.8p) には非拘束。
- **gate D の per-obs overlapping 解釈**: 有意性を主張しない経済 floor としてのみ運用され、regime 集中は gate E が別途拘束 — 解釈は健全。

### E. ban 隣接 / 帰結 — 全差分節成立
- **#7 vix**: 差分 5 軸 (指数/ペア/シグナル形/ホライズン/方向仮説) + 新データ (EVZCLS) — ban の再入場条件「新データ + 隣接差分節」を字義どおり充足。ADJACENT, not re-skin と裁定。
- **#17 qs**: 実測 BBO スプレッド (執行摩擦状態) と option IV (将来 vol の市場価格) はデータ源・情報内容とも直交 — 成立。
- **E20**: シグナルに金利入力ゼロ、rates は gate D join 後の減算コストのみ — **ソースコード実査で確認済み** (ppp/cc-mr 同型)。
- **E24**: scan 本文が E22/E24 を別候補として個別裁定済み (E22 条件付き採用 / E24 棄却) — 再提案に該当せず。2026 年研究の「>3mo horizon」は 21bd への負の prior として §1 に転記 (条件 15)。
- **E25**: E25 の死因 (IV が価格系列由来 = RV 再着せ替え) の**否定形が E22 の存在理由** (CBOE 実オプション価格) — scan の禁止方向 (E25 を E22 の代替に再提案) の逆であり非該当。
- **cc-mr #21 クローズ範囲**: VRP は price location anchor でなく、ペアもクローズ範囲 (3 クロス) 外。slow 家系 resemblance は §1 負の prior に正直継承 — ban 違反なし。
- **E12 P-10 / #22 ECG / E1 / E21**: columns=["Close"] コード assert 実査 ✓ / shadow equity curve 非接触 / positioning・口座データ非接触 — 全て成立。
- **FAIL クローズ範囲の妥当性**: 「通貨 VRP 全変種 × G10 × 日次〜月次 + 無料 proxy 系列」は一見広いが、(i) EUR 以外の G10 に無料 IV 系列が現存しない (VXFXICLS 2022-02 終了実査済み)、(ii) 復活経路 (有償 OTC 面 + 新 family + 新敵対的検証) が明示、の 2 点で運用上正当。**ただし条件 7 の power caveat 併記が成立条件** — これなしでは「vol モダリティ falsified」型の過大引用装置になる。
- **PASS 時の帰結**: §2.1 逐語内蔵を全文照合で確認 — 「Databento 調達の user 決裁点のみ / live 承認と誤読される余地ゼロ / 非調達時の設計緩和再訴訟禁止」全て内蔵済み。live/tier/lot/shadow 変更ゼロ + autopilot 実装着手禁止も明記済み。

---

## 凍結手続きへの指示

1. 条件 1 の処置 (backfill 推奨) → 条件 2/9 の数値を**処置後に再実測して**凍結値に反映。
2. 条件 3/5/6/7/8/10 の pre-reg / ハーネス修正。
3. §10 に本 report の条件番号→解決マッピングを記入。
4. pre-reg + ハーネス + manifest + EVZCLS.csv (git 追跡化) + payload + **本 report** を同一コミットで凍結 (rule:R1)。測定はコミット後のみ。

**この report が §10 マッピングの SSOT である。**
