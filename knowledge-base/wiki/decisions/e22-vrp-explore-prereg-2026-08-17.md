# e22_fx_variance_risk_premium (台帳 #24) explore pre-reg — 観測前プロトコル凍結 (2026-08-17)

**状態**: 🔒 FROZEN (本コミットが凍結点 — 以後の定義・閾値変更禁止、逸脱は verdict 無効)
**family**: vol モダリティ。[[external-hypothesis-scan-round3-2026-08-14]] §2 が explore 枠 1/3 に条件付き採用 (§2.1 事前コミット節必須)。前史 = round-2 E9 (条件付き採用・無料 probe 先行、data-blocked であって falsified ではない — 本 family は E9 の正当な再裁定)。
**敵対的検証**: [[../raw/analysis/e22-vrp-adversarial-verification-2026-08-17|e22-vrp-adversarial-verification-2026-08-17]] = **GO-WITH-CONDITIONS (17 条 / blocking 10 条)** — 同 report が SSOT。本書 §10 に条件番号→解決の全マッピング。payload: `knowledge-base/raw/analysis/e22-vrp-explore-candidate-2026-08-17.json`。
**ハーネス**: `tools/e22_vrp_explore.py` (凍結コミット同梱、seed 20260817)。**測定は凍結コミット後のみ・two-pass 厳守**。
**台帳スロット**: #24 explore = **1/3 active** (cc-mr #21 クローズ 2026-08-05 以降 0/3 → 本件で 1/3。E21 #23 は診断枠・E1/E7/E12/#22 は LOCK/クローズ別枠)。
**live への影響**: ゼロ。live/tier/lot/Kelly/shadow 構成は一切変更しない。

## §1 仮説と prior (正直申告)

**H1**: EUR_USD の通貨 variance risk premium — VRP(t) = EVZ(t) − RV21(t) (両者とも年率 vol point) — は、+21 営業日ホライズンの EUR_USD 方向純移動に対して時系列予測力を持つ (**両側登録** — G10 での符号 prior は不確実。Della Corte+ 2016 JFE はクロスセクション・ソートで「保険が割高な通貨 = 高 VRP は以後増価」方向だが、単一ペア時系列への外挿符号は文献で不確定 → 符号は主張しない)。

**機構**: FX オプションの IV は実現 vol に対して系統的プレミアムを含む (vol 売り手への保険料)。プレミアムの拡縮はリスク回避度・ヘッジ需要の変動を反映し、スポットのリスクプレミアム (キャリー巻き戻し/リバランス) と相関する。取る相手 = 保険料の過払い/過小払いをする hedger。

**負の prior (正直申告)**:
1. **explore→OOS 生存率 0/15 系統** (scan §2.1 逐語)。「有償決裁点に到達する」確率は低く、**無料で vol モダリティに白黒をつけられること自体が主たる価値**。
2. daily 頻度 × 21bd hold = 「方向は合うが弱い」slow 死型 4 例 (ppp/qs/rn/cc-mr) と同じ帳簿ゾーン。文献の効果量 (G10 で IC ~0.05-0.15) は本設計の正直 MDE (§6: IC ≈ 0.28) を**下回る公算が高い** — 真の IC 0.10 での検出力 ≈ 17%。これは意図された「安価で正直にゲートされた kill attempt」であり、power 不足を後から言い訳にしない (gate B は N floor で定義、UNDERPOWERED は N 未達時のみ)。
3. Della Corte 2016 の主戦場は EM 込みクロスセクション。G10 単一ペアでの減衰は正面から想定する (scan §2 C4 欄の前置)。
4. EVZ は FXE (EUR ETF) オプション由来の**間接** IV 指数 — OTC FX オプション IV との乖離 (配当・ETF プレミアム・米国市場時間) は残余ノイズ源。2021 以降は FXE オプション流動性低下で stale print が増える (QA §2 実測: 同値連続 run ≥3 は全系列 30 件、**explore 窓内 7 run (4,3,3,3,3,6,6 — 全て 2021 年)、帰属 day share 1.45%**、全系列の 96.7% が 2021+) — knife-edge (v) で感度検査 (条件 9)。
5. **E24 棄却を補強した 2026 年研究「currency vol risk の予測力は 3 ヶ月超 horizon」は、本設計の 21bd horizon への負の prior でもある** (estimand は別 [17 通貨クロスセクション vs 単一ペア時系列] なので ban ではない — 条件 15)。
6. 「0/15」の計数対象は外部/新規 family 系統の explore→OOS。内部 family には weekend_gap #3 (arm B) という生存反例が 1 件ある (条件 12 脚注 — §9 の scan §2.1 逐語 quote は不変)。

## §2 データ凍結と QA (2026-08-17 実測済み)

| 項目 | 凍結値 / 実測 |
|---|---|
| IV 系列 | `data/external/vrp/EVZCLS.csv` (FRED EVZCLS、本 PR で git 追跡化)。**4,529 行 (2007-11-01→2025-03-11、系列は 2025-03 で公表終了・確定)**。有効 4,360 行 / 欠損 169 行 (= 米祝日 placeholder、17.3y × ~9.8/y と一致)。単位 = 年率 vol point (実測レンジ 4.13–30.66、p50 8.82 — VIX 型スケールと整合)。重複 0・単調 ✓・週末行 0 ✓ |
| stale print QA | 同値連続 run ≥3 = 30 件 / max run = 8 (2024-10-02)。**explore 窓内 = 7 run (2021-02-09:4 / 04-01:3 / 04-07:3 / 05-07:3 / 06-09:3 / 07-01:6 / 08-06:6 — 全て 2021 年)、帰属 day share 1.45%** (条件 9 訂正)。**除外はしない** (stale EVZ = stale 情報として保守側) — knife-edge (v) で除外感度を検査 |
| RV/リターン系列 | `data/cache/massive/EUR_USD_15m.parquet` (**backfill 後 318,442 行**、2013-10-24→2026-08-17、UTC open-label — 日曜初バー 21:00 UTC (2018-07 夏) **かつ 22:00 UTC (2015-01 冬)** = NY17 アンカー実証、cc-mr 条件 4 と同規約)。**`EUR_USD_1d_2014_2026.parquet` は使用禁止** (週末行 714 実測 = 既知の罠) |
| **2020-10 ベンダー穴の修復 (条件 1)** | explore 窓内に MASSIVE ベンダー穴 **2020-10-23→2020-11-16 (24 暦日、取引日 16 日、米大統領選挙 2020-11-03 を含む)** を敵対的検証が実測発見 (guard 群は正しく発火し silent 汚染なし)。**`tools/e22_gap_backfill.py` (本コミット同梱) で OANDA v20 mid backfill 済み: +1,440 行 (窓内既存 208 行不変 assert / era pattern guard / .bak / audit 来歴、07-29・08-05 手法継承)**。修復後の再 census: explore 窓の >4 暦日 D1 gap = 年末休場 (12-28→01-04) のみ、rv/fwd/returns void = **全ゼロ**、2020 N = 196→**253** |
| audit.json 乖離 | 同梱 audit.json は旧 fetch (rows 311,035 / start 2014-01-05) だったが backfill 実行で最新化 (来歴 append 済み)。**凍結はファイル実体 sha256 + 行数 assert で行い audit.json に依存しない** (MASSIVE drift 教訓)。**living-cache 注意 (条件 16)**: 15m parquet は日次更新されうる生キャッシュ — 凍結コミットと測定は同一セッションで実行し、drift 検出時は manifest 編集でなく再凍結コミットで対処 (EVZCLS = 系列確定終了 / e20 csv = 静的で drift リスクなし) |
| D1 再構築 | trading day T = close-time ∈ (NY17:00\_{T−1}, NY17:00\_T]、境界 = **America/New_York zoneinfo** (固定 21/22:00 UTC 禁止)。close-time = open ラベル +15m。週末ラベル bar は除外 (実測 1,587 bars、件数報告)。D1 close = 最終バー close、**最終バー close-time < 14:00 NY → day void** (実測 <40 bars/day は 15 日 — 元日・クリスマス等)。**assert PASS: bars/week p50 = 5.0、曜日 share 0.199–0.201 一様、構成バー p50 = 96** |
| リターン端点規則 | 日次 log return r = log(C_T/C_{T−1}) は連続する有効 D1 間のみ。**span > 7 暦日 → 当該 return void (件数報告)**。\|r\| > 5%/日 → assert 停止 (silent 処理禁止、手動検分) |
| EVZ↔FX 整合 | join = FX trading day ラベル T ↔ EVZ observation_date T。EVZ print (~16:15 ET) は FX D1 close (17:00 ET) に**先行** = lookahead なし。同日一致 97.1% (explore 実測)、as-of backward join の staleness p95 = 0 日 / max 3 暦日。**staleness > 3 暦日 → 当該日 void** |
| swap panel | `knowledge-base/raw/bt-results/e20/e20_carry_level.csv` EUR_USD 列 (base−quote %/yr)。2013-01-01→2022-12-30 = **explore 完全被覆**。符号検証: 2013-01-02 = +0.625 (ECB 0.75 − Fed 0.125) / 2022-12-29 = −1.875 (ECB 2.50 − Fed 4.375) ✓ |
| 窓被覆 (条件 2 訂正、backfill 後実測) | explore 窓 FX D1 = **2,066 日** (曜日 share 0.1980–0.2014)、EVZ print あり 2,017 日。**最終有効 N = 2,066 (rv_void/evz_void/fwd_void 全ゼロ) / 非重複窓 = 98 / IC MDE = 0.283**。年次 N = 253–260。RV21 warmup: 15m 左端 2013-10-24 → 最初の有効シグナル日 2013-11-22 → **explore 2014-01-01 開始は全域適格 (リスケールなしの原型)** |
| sha256 pin | `knowledge-base/raw/bt-results/e22/data_freeze_manifest_2026-08-17.json`: EVZCLS.csv + EUR_USD_15m.parquet + e20_carry_level.csv の sha256 + 行数。**ハーネスはロード時に sha256 + 行数 assert = フル parquet 強制** (worktree 部分 parquet 罠対策) |
| P-10 (E12 ban) | ハーネスは parquet を `columns=["Close"]` でロードし **Volume/vwap 非読取をコード assert** (E12 ban 2027-02-05 まで)。H/L も不使用 (MFE/MAE 系なし、fixed-horizon close-to-close のみ) |

## §3 シグナル・サンプリング定義 (全 DoF 凍結 — 単一構成、grid なし)

| 要素 | 凍結値 |
|---|---|
| RV21 | RV21(t) = 100 × √(252 × mean(r²)) — 直近 21 本の有効日次 log return (**当日 t の return r_t = log(C_t/C_{t−1}) を含む**、平均引きなしの標準 RV)。21 本のうち最古の return が t から 45 暦日以内でなければ当該日 void (件数報告) |
| VRP | VRP(t) = EVZ_asof(t) − RV21(t) (両者とも年率 vol point、単位整合は §2 QA で確認済み) |
| シグナル確定時刻 | FX D1 close (17:00 NY) 時点。使用情報 = EVZ 同日 print (16:15 ET 公表、45 分先行) + 当日までの D1 close 系列 — lookahead なし |
| サンプリング | **全有効 FX D1 日** (daily、overlapping)。有効 = EVZ staleness ≤3 暦日 ∧ RV21 有効 ∧ fwd21 有効 |
| horizon | **PRIMARY = +21 営業日** (valid-D1 系列上の 21 ポジション先、文献の月次リバランスに整合)。fwd21(t) = log(C_{t+21}/C_t)、pip 換算 move = (C_{t+21} − C_t)/1e-4。span > 45 暦日 → void。**他ホライズンなし** (14/28 等は knife-edge のみ、選択不使用) |
| 窓 | **explore = シグナル日 2014-01-01..2021-12-31** (本セッション)。12 月末シグナルのホライズン完了が 2022-01 に食い込むのは explore イベントの outcome 完了であって OOS シグナル接触ではない (cc-mr §3 前例、on-record)。**OOS = シグナル日 2022-01-01..2025-03-11 (EVZCLS 終端)、候補凍結後 1 回のみ・explore 全 gate PASS 時のみ接触** |
| pair | EUR_USD 単独 (pip = 1e-4)。EVZ は EUR 系 IV であり他ペアへの横展開はしない (family 拡張は新 pre-reg + 新敵対的検証) |
| 方向 | **両側登録**。pass-2 の観測 IC 符号 g = sign(IC_obs) が gate C 通過時のみ経済 gate (D/E) の「予測方向」を定める。**OOS は g への片側化** (holiday レグ a / cot #16 前例) |

## §4 接触順序 (two-pass、cc-mr §4 パターン)

1. **pass-1**: `date|evz|evz_staleness|rv21|vrp` のみ export (**リターン/シグナル×outcome join 系はゼロ**) + 無条件 fwd21 分散 (シグナル非依存の \|move\| 分布 — gate A 判定 + MDE 再計算用) + VRP ACF 再実測 (条件 10) + N/年次分布/void 件数 census。**コミットしてから pass-2 解錠**。
   **firewall 条項 (条件 5、明文 pin)**: pass-1 成果物には **per-date の forward 値を一切含めない** — 無条件 fwd21 は aggregate 分位 (median/sd/p25/p75) のみ。CSV は signal 列のみ (`evz|evz_staleness|evz_stale_run3|rv21|vrp`)。\|move\| は符号不変量であり符号 peek にならない (敵対的検証 lens C 裁定)。
2. **pass-2**: IC + gates C–G + knife-edge + verdict。stats はハーネス同梱 (seed 20260817)。
3. gate A または B 不通過 → pass-2 の gate C 以降に進まない (UNDERPOWERED / KILL) — ハーネスが assert で機械強制。
4. **OOS pass** (explore 全 binding gate PASS 時のみ、1 回): 同一定義・片側化・§5 OOS gates。実行前に swap panel フル被覆延伸 (§7) を**別コミットで**先行。**機械ロック (条件 6)**: OOS 実行は (i) `--unlock-oos` flag、(ii) pass-2 verdict JSON が **git commit 済み** (ハーネスが `git cat-file` + clean status を assert)、(iii) OOS 成果物の不在 assert (書出後の再走は恒久禁止)、(iv) swap 延伸 manifest 追補の commit 済み assert — の 4 点を全て要求。**単一接触の意味論 (事前宣言)**: OOS 成果物書出前のクラッシュ再走は同一の 1 接触と数える / 書出後の再走は恒久禁止。

## §5 統計 gates (凍結)

- **Gate A (headroom、pass-1)**: 無条件 median \|fwd21 move\| ≥ **10× stressed_RT = 40.0p**。不通過 → family KILL (pass-2 非解錠)。
- **Gate B (power、pass-1)**: 有効シグナル日 **N ≥ 1,500** ∧ 非重複窓数 floor(N/21) ≥ **70**。未達 → verdict = **UNDERPOWERED** (PASS/FAIL ではない)。閾値いじり禁止。
- **Gate C (primary)**: pooled Spearman IC(VRP(t), fwd21(t)) の**両側 p < 0.05 (単独 family m=1)**、null = **circular-shift permutation** (§6)。
- **Gate D (stressed-net)**: 上下 tercile (window-local、VRP 3 分位) の日次 obs について、per-obs net = g_tercile × move_pips + swap_pips(side) − stressed_RT (g_tercile = 上 tercile なら g、下 tercile なら −g)。**pooled mean net > 0 を adverse 端 (stressed_RT 4.0p、markup 1.65%/yr) で要求**。point/favorable (2.0p、1.0%/yr) に加え **RT 6.0p (3× 端) 感度を非拘束で報告** (条件 8 — qs #17 実測「異常時 RT = 正常の 2–3 倍」の 3× 側)。gate D は有意性を主張しない経済 floor であり、per-obs overlapping の相関は gate C (block null) と gate E (年次集中) が別途拘束する。
- **Gate E (集中)**: S_y = 暦年 y の extreme-tercile 符号付き gross 和 (g 方向)。**max_y \|S_y\| / Σ_y \|S_y\| ≤ 0.50** (分母凍結)。
- **Gate F (一貫性)**: 年次 (シグナル年) Spearman IC の符号が pooled 方向に **≥ 6/8** ∧ **LOYO 8/8 で pooled IC 符号不変**。**事前記録 (条件 13 で定量化): 真 IC 0.10 なら年次符号一致率 ≈0.6 前後 → P(≥6/8) ≈ 0.3–0.4 = false-kill ≈60–70%。それでも binding (cc-mr/#19 前例 — 今緩めるのは gate-shopping)。C-PASS/F-FAIL は「regime-inconsistent の FAIL close」で再審禁止**
- **Gate G (単調性)**: tercile 平均 fwd21 が g 方向に単調 (隣接違反 ≤1) ∧ T3−T1 スプレッド符号 = g (ppp gate ii の tercile 版 — 実効 95–98 窓では quintile 極値 bin ≈19 窓で薄すぎるため tercile、凍結)。**on-record (条件 14): 3 分位 = 隣接差分 2 本のため本 gate は実質 T3−T1 符号チェックと等価 (ppp quintile 版より弱い) — この弱さを認識した上で凍結**。
- **knife-edge (全 gate PASS 後のみ、選択不使用)**: (i) RV window {14, 28}、(ii) permutation 代替 = 42bd-block sign-flip (returns 側、seed 20260818)、(iii) 週次 (水曜) サブサンプル IC、(iv) fwd を pip 単純差 (log でなく) で再計算、(v) stale-print 日 (run ≥3 帰属日) 除外。**いずれかで primary IC 符号反転 → FAIL**。
- verdict: 全 binding gate (A, C–G) 通過 = **explore PASS** → OOS pass へ。gate B 未達 = **UNDERPOWERED**。他 = **FAIL クローズ** (OOS 非接触)。**閾値の事後変更禁止**。
- **OOS gates (explore PASS 時のみ、事前凍結)**: (i) OOS Spearman IC の **g への片側** circular-shift p < 0.05、(ii) OOS gate D (adverse 端) > 0、(iii) OOS N ≥ 600 ∧ floor(N/21) ≥ 28 未達なら OOS UNDERPOWERED (= 有償決裁点に**到達しない**)。(iv) 最小効果 floor: OOS extreme-tercile gross mean ≥ +5.0p (holiday レグ a 前例 — 統計有意でも economic floor 未達は PASS にしない)。**全通過 = family PASS**。
- **BH 分母合流条項**: 本 verdict 前に他の explore family が起動した場合は BH q=0.10 で分母合流 (cc-mr §5 補償 (c) 継承)。
- **claim 範囲の恒久限定**: family-pooled EUR_USD のみ。サブ期間/サブ tercile/staleness 条件付き等の per-slice claim は結果如何によらず禁止。

## §6 permutation と正直 MDE (完全凍結)

- **primary null = circular-shift permutation**: VRP 系列を有効日 index 上で k だけ循環シフト (k ~ Uniform{42, ..., N−42}、returns 系列は固定)、B = 10,000、numpy `default_rng(20260817)`。**p_two = (1 + #{\|IC_perm\| ≥ \|IC_obs\|}) / (1 + B)**。シグナル・リターン両系列の自己相関 (VRP 持続性 + 21bd overlap) を**そのまま保存**して cross-alignment のみ破壊する null — 過分散を握り潰さない (naive Spearman p は本設計では引用禁止)。
- **MIN_SHIFT=42 の実測正当化 (条件 10、事前記録)**: 実測 VRP ACF = **lag5 +0.63 / lag10 +0.33 / lag21 −0.09 / lag42 +0.03** → 脱相関長 ≈ 15–20bd < 42 でシフト最小距離は妥当。**シフト対象は VRP であり EVZ 単体 (lag42 ACF 0.62) でないことが要点**。残余の小シフト相関は null を保守側 (false-kill 方向) に振る。pass-1 で ACF を再実測し report 記載。
- OOS 片側: p_one = (1 + #{g×IC_perm ≥ g×IC_obs}) / (1 + B)、seed 20260819。
- knife-edge (ii) 代替 null: 42bd 連続 block 単位で returns の符号を flip (seed 20260818) — 診断併記、選択不使用 (IC 点推定は不変のため符号反転判定の対象外)。
- **正直 MDE (事前記録、条件 2 訂正済み)**: 実効独立標本 ≈ 非重複窓数 = **98** (2,066/21)。IC の MDE = (1.96+0.84)/√98 ≈ **0.283** (両側 α=0.05、power 0.8)。文献級の真効果 IC 0.05–0.15 に対する検出力 ≈ 8–17%。tercile-mean 版 MDE (cluster-worst 2.487×σ/√98) は検証者事前実測で ≈59p — 文献級効果は構造的に届かない帳簿であることを事前記録 (§1 の「意図された kill attempt」framing)。**pass-1 が無条件 fwd21 分散から再計算し report 記載する (gate 閾値は変えない)**。

## §7 摩擦・swap (凍結)

- **RT friction (EUR_USD)**: point = 2.0p (friction-analysis 表)、**stressed = 4.0p (2.0×)** — 測定 convention の NY17 close は rollover 死圏に隣接するため保守化 (qs #17 実測: 異常時 RT は正常時の 2–3 倍)。gate A/D の binding は stressed 4.0p。**加えて 6.0p (3× 端) の gate D 感度を非拘束報告 (条件 8)**。**honesty 条項 (条件 8)**: 本測定は歴史 mid であり執行可能性を主張しない — **将来のいかなる実装経路も 17:00 NY 実スプレッド実測を必須とする** (cc-mr §3 冬スプレッド honesty 条項の同型)。
- **swap (per-obs、サイド符号付き)**: swap_pips = (rate_used/100) × (H_cal/365) × S_entry/1e-4。rate_used = side × d_EUR_USD(t) − m (side = +1 long / −1 short、d = e20 列 %/yr、負 = コスト)。H_cal = per-obs 実暦日数 (t → t+21 の暦日)。**m_adverse = 1.65%/yr (gate D binding、cc-mr §7 の adverse floor 継承) / m_point = 1.0%/yr (感度併記)**。
- **規模の事前記録 (条件 3 訂正)**: 凍結 e20 panel の実測 = 2018 平均 **−1.779%/yr** / 2019 平均 **−2.158%/yr** / 全期間最小 **−2.375%/yr (2018-12-20)**。adverse 例 = panel 最小 + m_adverse で ≈ **−36〜−38p/obs** (30 暦日、S≈1.15) — 21bd 設計では swap が支配的摩擦になり得る (multi-week 純額込み原則、台帳ハード条件)。**e20 列のレート規約 = MRO 型 policy rate** (預金金利ではない — 旧 draft の「−2.9%/yr」は deposit-rate 算術の混入と推定され棄却)。
- **EUR_USD financing snapshot 照合の不在 (条件 17、正直記録)**: cc-g0-rt financing sampler は 3 コモディティクロスのみで EUR_USD の実勢 markup 照合は不能。m_adverse=1.65 は cc-mr 実測 implied (1.075–1.155%/yr) の 1.4–1.5 倍 = 保守側継承として妥当、ただし EUR_USD 固有の実測ではないことを on-record。
- **E20 ファイアウォール**: rates の使用は outcome join 後の gate D 減算コストのみ (ハーネス構造で分離 — signal/sampling builder は e20 csv に非アクセス、敵対的検証がコード実査済み)。イベント選択・方向・サイズのいかなる rate 条件付けも E20 隣接違反。
- **OOS swap ソースの事前宣言 (条件 4 で仕様凍結)**: e20_carry_level.csv は 2022-12-30 終端 (explore 完全被覆・OOS は 2023+ 不足)。OOS pass 実行前に `tools/e20_rates_ingest.py` の BIS 再 ingest 拡張で延伸ファイル `knowledge-base/raw/bt-results/e20/e20_carry_level_ext_2026-08.csv` を生成する。**仕様 (ハーネス assert 済み)**: (i) **2013-01..2025-04 フル被覆** (2023+ のみの部分ファイルは 2022 OOS シグナルの ffill 起点不在で不可)、(ii) 重複日付は凍結 csv と**等値 assert**、(iii) sha256+行数の manifest 追補 (`oos_swap_manifest_addendum.json`) を **OOS touch 前に別コミットで凍結** (実行は explore PASS 後のみ、公開政策金利の決定論データで look 問題なし)。

## §8 ban 隣接差分節 (必須)

- **#7 vix_carry_unwind (2026-07-28 knife-edge kill、同型再試行禁止 = VIX レベル閾値 × JPY クロス short × 固定 1-5d)**: 差分 = ① 指数が別 (EVZ = FXE オプション由来 EUR 通貨 IV ≠ VIX = S&P500 equity IV)、② ペアが別 (EUR_USD ≠ JPY クロス)、③ シグナル形が別 (IV−RV **差分・連続値 IC** ≠ レベル閾値 onset イベント)、④ ホライズン別 (21bd ≠ 1-5d)、⑤ 方向仮説別 (両側 VRP ≠ risk-off continuation short)。ban の「再挑戦は新データ + 隣接差分節必須」は本節 + EVZCLS (新データ源) で充足。ADJACENT, not re-skin。
- **#17 fx_quote_spread_state (ban = 実測 BBO スプレッド状態 × 固定ホライズン fwd 全変種)**: 差分 = 実測 quote spread (執行摩擦の状態変数) ≠ オプション市場 IV (将来 vol の市場価格)。データ源・情報内容とも直交 (spread panel は OANDA BBO、EVZ は CBOE オプション)。
- **E20 (凍結 = 金利差シグナル 2 変種 + carry 同型)**: VRP に金利入力ゼロ。rates は §7 の減算コストのみ (ppp/cc-mr と同型のソースコード分離)。非違反。
- **E24 (global currency vol risk、round-3 で棄却・再提案禁止)**: E24 = 17 通貨 OTC IV パネル (有償) × 3 ヶ月超 horizon。E22 = 単一ペア無料 EVZ × 21bd。scan 本文が両者を別候補として裁定済み (E22 条件付き採用 / E24 棄却) — 本 pre-reg は E24 の再提案ではない。
- **E25 (synthetic vol surface、C2+C3 二重 FAIL 棄却)**: E25 の死因 = 「IV」が Yahoo 価格系列由来 = 実質 RV の再着せ替え。**E22 は真正のオプション市場価格 (CBOE 算出 EVZ) を使う — E25 を殺した差分そのものが E22 の存在理由**。E25 を E22 の代替として再提案することは scan で明示禁止済み (本件はその逆方向で非該当)。
- **価格モダリティ 3 周 FAIL / cc-mr クローズ範囲 (slow location-anchor band fade × 3 クロス)**: VRP は価格 location アンカーではなく vol 市場の相対価格。ペア (EUR_USD) もクローズ範囲外。家系 resemblance (slow・daily・multi-day) は §1 負の prior に正直継承 (ban 違反ではない)。
- **E15 無条件イベント窓 / E7 サプライズ (棄却/FAIL)**: イベント時刻条件付けなし — 非干渉。
- **#22 ECG P-10 (gate×outcome 計算禁止)**: 本件は shadow equity curve に非接触。E12 P-10 (volume×価格) は §2 の columns assert で遮断。E1 positioning / E21 口座データにも非接触。

## §9 分岐 (凍結) と scan §2.1 事前コミット節の内蔵

**[[external-hypothesis-scan-round3-2026-08-14]] §2.1 を無変更で内蔵する (逐語)**:

> - explore 窓 2014-01→2021-12 / OOS 窓 2022-01→**2025-03-11** (EVZCLS 終端)。OOS は候補凍結後 1 回のみ接触 — 既存規約どおり。
> - **PASS 時の帰結を先に凍結**: PASS は「live 実装の承認」ではなく「**有償データ (Databento) 調達の user 決裁点**」に到達したことのみを意味する。user が調達しない判断をした場合、E22 は PASS のまま **implementable でない**として棚上げし、**その事実をもって設計を緩める再訴訟を禁止**する。
> - **FAIL 時の帰結**: vol モダリティを (E24/E25 の棄却と合わせて) 恒久クローズ扱いにでき、探索空間が確定的に縮む。
> - **期待値の正直な見積り**: 当プロジェクトの explore→OOS 生存率は現時点で **0/15 系統**。よって「有償決裁点に到達する」確率は低く、**無料で vol モダリティに白黒をつけられること自体が主たる価値**。この非対称 (コストほぼゼロ / 情報価値は高い) が、forward 経路が閉じているにもかかわらず枠を使う正当化である。

- **FAIL / UNDERPOWERED** → 台帳 #24 verdict + report + KB 永続化。explore FAIL 時は OOS 非接触保存。**FAIL 時クローズ範囲 (事前凍結)**: 「**通貨 VRP (IV−RV 差分・レベル・比率の全変種) × G10 ペア × 日次〜月次固定ホライズン、EVZ/VXFXICLS 等の無料 proxy 系列を含む** — vol モダリティは E24/E25 棄却と合わせ恒久クローズ」。**power caveat (条件 7、クローズ文言に義務付け)**: **FAIL は効果不在の証明ではない (文献級 IC 0.05–0.15 への検出力 8–17%)。クローズの根拠は『無料経路での retail-viability 不成立 + 供給ライン経済性』であり、将来「VRP は falsified」型の引用は estimand 監査なしに禁止** (user 恒久指示 2026-08-05)。復活経路 = 新データ (真正 OTC FX オプション面 = Databento 等有償) + 新 family + 事前差分節 + 新規敵対的検証のみ。
- **explore PASS** → §4 手順 4 の OOS pass (単一接触、片側化) を同 wave 内で実行 — §2.1 の「候補凍結後 1 回のみ」の実装形 (weekend_gap #3 / holiday #15 の同日 OOS 前例)。**OOS 全 gate PASS = family PASS → 上記逐語のとおり Databento 調達の user 決裁点到達のみ。live/shadow/tier/lot 変更ゼロ、autopilot による実装着手も禁止 (user 決裁が先)**。
- **接触規律**: 測定は凍結コミット後のみ。pass-1 → コミット → pass-2。OOS はシグナル日 2022+ に explore pass 中非接触 (ハーネスの explore モードは 2022+ シグナル行を生成しない)。
- 動機記録 (R1 手続き): データ駆動 — scan 第 3 次の裁定 (explore 枠 1/3 採用、能動可能 2 系統の 1 つ) + WIP 原則の探索アクティブ枠 0/3 解消 + user ミッション委任 (2026-07-08)。感情的動機なし。

## §10 敵対的検証 17 条件 → 解決マッピング ([[../raw/analysis/e22-vrp-adversarial-verification-2026-08-17|report]] が SSOT)

| 条件 | [B] | 解決 |
|---|---|---|
| 1 2020-10 ベンダー穴の処置 | B | §2 (推奨形 = OANDA backfill 実行済み: `tools/e22_gap_backfill.py` +1,440 行、既存行不変 assert、選挙週回収、再 census 全 void ゼロ、**manifest は backfill 後に生成**) |
| 2 窓被覆数値の訂正 | B | §2/§6 (処置後再実測で凍結: FX D1 2,066 / N 2,066 / 窓 98 / MDE 0.283 / 曜日 share 0.1980–0.2014) |
| 3 swap 量級 pre-record の訂正 | B | §7 (2018 −1.779 / 2019 −2.158 / min −2.375、adverse ≈ −36〜−38p、MRO 型レート規約明記) |
| 4 OOS swap 延伸ファイル仕様凍結 | B | §7/§4 (フル被覆 2013-01..2025-04 + 重複等値 assert + manifest 追補別コミット — ハーネス `load_swap(oos=True)` に assert 実装) |
| 5 pass-1 firewall 明文 pin | B | §4 (per-date forward 値の非出力を明文凍結、ハーネス適合確認済み) |
| 6 OOS 機械ロック強化 | B | §4 (pass-2 verdict の git commit 済み assert `_assert_committed` + 単一接触意味論の事前宣言) |
| 7 FAIL クローズ文言 power caveat | B | §9 (「FAIL ≠ 効果不在の証明」+ クローズ根拠の限定 + falsified 型引用禁止) |
| 8 gate D RT 6.0p 感度 + honesty 条項 | B | §5/§7 (非拘束 3× 感度報告 `mean_net_rt6_sensitivity_nonbinding` + 実装時 17:00 NY 実スプレッド実測必須) |
| 9 stale-print 実測訂正 | B | §1/§2 (explore 窓 7 run [4,3,3,3,3,6,6] 全て 2021、day share 1.45%) |
| 10 circular-shift 実測正当化の記録 | B | §6 (VRP ACF lag5/10/21/42 = +0.63/+0.33/−0.09/+0.03、脱相関長 15–20bd < 42、保守側バイアスの事前記録、pass-1 再実測) |
| 11 E23 参照の stale 解消 | n | payload 更新 (E7 verdict 08-17 着地済み → E23 ゲート解除済み。E22 verdict 前に E23 起動時は BH q=0.10 合流条項が governs) |
| 12 0/15 の計数脚注 | n | §1 負の prior 6 (外部/新規 family 系統の計数、weekend_gap #3 arm B は内部反例) |
| 13 gate F false-kill 定量化 | n | §5 (真 IC 0.10 → P(≥6/8) ≈ 0.3–0.4 = false-kill ≈60–70%) |
| 14 gate G 縮退の on-record 化 | n | §5 (実質 T3−T1 符号チェック等価の弱さを明記) |
| 15 E24 補強研究の負 prior 転記 | n | §1 負の prior 5 |
| 16 living-cache drift 運用 | n | §2 (同一セッション凍結+測定、drift 時は再凍結コミット) |
| 17 EUR_USD markup 照合不能の正直記録 | n | §7 (cc-g0-rt sampler は 3 クロスのみ、1.65 は cc-mr implied の 1.4–1.5×) |

**コミット規律**: 本文書 + `tools/e22_vrp_explore.py` + `tools/e22_gap_backfill.py` + data manifest + EVZCLS.csv (git 追跡化) + 検証 report + payload を**同一コミットで凍結 (rule:R1 手続き)**。測定はコミット後開始。
