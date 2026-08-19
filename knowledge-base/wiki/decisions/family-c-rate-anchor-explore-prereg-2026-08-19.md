# family_c_rate_anchor_deviation (台帳 #26) explore pre-reg — 観測前プロトコル凍結 (2026-08-19)

**状態**: 🚧 DRAFT → 敵対的検証 → 🔒 FROZEN (凍結コミットが凍結点 — 以後の定義・閾値変更禁止、逸脱は verdict 無効)
**family**: rates-anchor モダリティ (family C)。user「水平線理論」最終形の機械核 v2 ([[family-c-anchor-automation-2026-08-18]] §4 / MEMORY `user_manual_edge_usdjpy_carry_2026_08_12` 追記 7)。user 承認 2026-08-19「進めて」。
**臨時裁定 (§0)**: 改訂 WIP 原則 (「今日着手できる本数 ≥1」、scan round-3 §5 追補) — E21/E22 クローズ (08-17/18)・E23 は S2 設計中 (TDW ライセンス user 決裁待ちの残タスクあり) で**能動 explore 枠 0/3、今日着手可能 = 本件のみ** → 期日 (09-18) を待たず R3 臨時裁定。
**敵対的検証**: [[family-c-adversarial-verification-2026-08-19]] — §10 に条件→解決マッピング。
**ハーネス**: `tools/family_c_anchor_explore.py` (凍結コミット同梱、seed 20260819)。**測定は凍結コミット後のみ・two-pass 厳守**。
**台帳スロット**: #26 explore = **1/3 active** (E22 #24 クローズ 08-17 以降 0/3 → 本件で 1/3)。
**live への影響**: ゼロ。live/tier/lot/Kelly/shadow 構成は一切変更しない。

## §0 臨時裁定 (C1-C6、round-2/3 と同一 hard constraints)

| 制約 | 判定 |
|---|---|
| C1 データ | ✅ 全 keyless・in-repo: `data/external/rate_anchor/` (JGB/DGS 日次、PR #193) + Massive USD_JPY 15m (gap-fill 済) + e20 swap panel |
| C2 falsified 除外 | ✅ 最近接 corpse は ppp #14 (explore FAIL、falsified 6 系統ではない)。ban 隣接は §8 で明示差分 |
| C3 非重複 | ✅ rates-anchor 乖離は未測定モダリティ (E20 = rates **シグナル** ランキング、ppp = CPI 価格水準 — いずれも別 estimand) |
| C4 摩擦生存 | ✅ 21bd 保有 × USD_JPY RT 2.14p — 無条件 21bd 変動は数百 p 規模 = headroom は gate A で機械確認 |
| C5 反 curve-fit | ✅ 単一構成凍結 (anchor 1 本 / Z_th は pass-1 機械選定 / grid なし / 片側登録) |
| C6 revealed-edge | ✅ user 実трейド thesis の明文化 (追記 7) — 帰属分解 (E21) は α 不検出だが thesis の機械核は本件が初検定 |

## §1 仮説と prior (正直申告)

**H1 (片側登録・LONG)**: 日米 2y 国債利回り差が定義する rolling フェアバリューから USD_JPY spot が**下方に大きく乖離した onset イベント**は、+21 営業日の LONG 方向純移動 (swap 込み) に正の EV を持つ。片側の根拠 = user thesis の方向固有性 (「帯より下 = 買って待つ」) + LONG 側は swap を稼ぐ (§7) + 介入 dip の実測リトレース (E-C median +188p、記述級 N=3)。**上方乖離 (ショート側) は claim しない** — E-C 符号逆 prior + swap adverse。descriptive 記録のみ。

**機構**: 金利差はキャリーと政策期待の集約価格。spot の帯下 undershoot は一時的リスクオフ/ポジション解消フローで、金利差が不変なら carry 引力 + リバランスで回帰する。取る相手 = 短期制約で投げる主体。**取り分の源泉は timing** — 常時ロング (drift β) は E21 で user 収益の主成分と判明済みのため、null に year-matched placebo を採用して「同年の任意日ロング」に対する超過を直接検定する (§6)。

**負の prior (正直申告)**:
1. **ppp #14 (最近接 corpse): USD_JPY は 7 ペア中唯一の per-pair IC 負 (−0.027 h42 / −0.051 h63)** — CPI アンカー版の回帰はこのペアで最も効かなかった。
2. **slow-MR 死型 4/4 全滅** (ppp/qs/rn/cc-mr、実効果 +3〜12p、p 0.117-0.32)。本件は同じ帳簿ゾーン (multi-day MR)。cc-mr の家系 prior 文言をそのまま継承: 「家系前例サイズ (+3-6p) の効果は本設計では構造的に FAIL する — 意図された retail-viability filter」。
3. **E20 診断: USD_JPY carry cell は EV 正 (+13.14p h960、全 fold 正) だが Spearman IC は全ホライズン負 (−0.070/−0.113/−0.077)** = 金利差**レベル**に時系列ランキング力は無かった。本件の残差乖離 estimand は別物だが、rates 情報の弱さの負 prior として正直継承。
4. 外部/新規 family 系統の explore→OOS 生存 **0/16**。
5. **E21: user 実績の timing α 不検出 (p=0.32、収益 = swap 28% + 価格ドリフト 72%)** — 本件はその thesis の機械核を検定するのであって、user が α を持つ証拠は現時点で存在しない。
6. anchor 縮退リスク: 2020-2021 は金利差がほぼ不動 (両国 ZIRP 近傍) — 回帰は ill-conditioned になりうる (§3 縮退 void 規則で処理、件数報告)。イベントが後半窓に立たない可能性は UNDERPOWERED 分岐で正直に処理。
7. **外挿限界の事前記録 (lane-owner 要請 1、[[intervention-history-anatomy-2026-08-18]] dossier)**: E-C の +188p リトレース (PR #189) は**介入型**の帯下人工乖離だが、explore 窓 2014-2021 は**介入ゼロ** — 本 explore が検定するのは**非介入型の帯下乖離**のみ。PASS/FAIL いずれでも「介入 dip への外挿」は本 verdict の claim 範囲外 (介入層との統合は 09-18 裁定の family B/C 統合設計マター)。

**正の差分 prior (§8 の存在理由)**: (i) anchor が価格由来でない (level family 5 corpse と非同型) かつ**日次リプライス** (ppp は月次 CPI + 45 日 staleness)、(ii) USD_JPY↔金利差のレベル追従は 2014-2021 で最も文書化された FX-マクロ関係、(iii) **swap が trade 側 (LONG) に有利** — slow-MR 死型 4 例で初めて摩擦が味方につく、(iv) イベント設計 (連続 IC でなく尾部集中) で per-event 効果量の土俵に乗せる。

## §2 データ凍結と QA (pass-1 で census 確定、凍結コミット時に manifest pin)

| 項目 | 凍結値 / 実測 |
|---|---|
| 金利系列 | **凍結コピー** `knowledge-base/raw/bt-results/family-c/data_freeze/jgb_yields_2026-08-19.csv` + `us_treasury_yields_2026-08-19.csv` (data/external/rate_anchor/ は日次更新される living store のため、凍結コミット時点のコピーを固定 — E22 living-cache 条項の実装形)。実測 (2026-08-18 シード): JGB 2y 2014-2021 = 1,954 行 NaN 0 / DGS2 = 2,088 行 NaN 86 (米祝日、両テナー同時 NaN)。sha256 + 行数を manifest pin |
| 価格系列 | `data/cache/massive/USD_JPY_15m_2014_2026.parquet` (**main checkout、E15/E7 凍結体系の gap-fill 済ファイル**: 310,624 行、2013-12-29→2026-07-02、completeness 99.13%、2019/2020 ベンダー穴補修済み)。--parquet 引数で明示指定 + **sha256 + 行数 assert** (worktree 部分 parquet 罠 / MASSIVE drift 対策)。**bare `USD_JPY_15m.parquet` は使用禁止** (2019/2020 穴が未補修の再 fetch 版) |
| D1 再構築 | **UTC-day バー** (mof_forward_verdict と同規約: date group → weekday<5)。day valid = **n_bars ≥ 24**、未満は void (件数報告)。D1 close = 最終バー close。リターン端点: 連続 valid D1 間のみ、span > 7 暦日 → return void。\|r\| > 5%/日 → assert 停止 (手動検分) |
| 金利⇄価格 join | calendar-date join、**yields は lag 1 営業日** (シグナル日 d は label ≤ d−1 の値を ffill 使用) — JGB (17:30 JST 公表) / DGS (~23:00 UTC 公表) の公表時刻 knife-edge を構造排除。ffill staleness > 5 暦日 → 当該日 anchor void (件数報告)。**日付境界変換は明示コード + test pin** (ベンダー日足 lesson 2026-08-18) |
| swap panel | `knowledge-base/raw/bt-results/e20/e20_carry_level.csv` USD_JPY 列 (policy diff %/yr、2013-01..2022-12 = explore 完全被覆、凍結済みファイル)。sha256 pin |
| 介入ゼロ確認 | `data/external/mof_interventions.csv`: **2014-01-01..2021-12-31 の USD_JPY 介入 = 0 行 (2026-08-19 実測)** — MoF #4 cross-LOCK (介入ラベル非使用 + 価格シグネチャ推定禁止) は explore 窓選択で構造遵守 |
| E12 firewall | parquet ロードは `columns=["Close"]` + **Volume/vwap/High/Low 非読取をコード assert** (gate A は \|fwd21\| ベースで H/L 不要 — MFE/MAE 系 gate なし) |
| sha256 pin | `knowledge-base/raw/bt-results/family-c/data_freeze_manifest_2026-08-19.json`: 上記 4 ファイルの sha256 + 行数。ハーネスはロード時 assert |

## §3 シグナル・サンプリング定義 (全 DoF 凍結 — 単一構成、grid なし)

| 要素 | 凍結値 |
|---|---|
| anchor 入力 | diff2y(d) = DGS2(d) − JGB2y(d) (%pt、lag 1bd 適用後) |
| フェアバリュー | rolling OLS: log C_d = a + b·diff2y over 直近 **W = 252 valid D1** (完全窓必須)。fitted_d = a + b·diff2y_d |
| 乖離 z | z_d = (log C_d − fitted_d) / std(residuals, ddof=1) (同一 252 窓) |
| 縮退 void | 窓内 std(diff2y) < **0.10 %pt** → 当該日 z void (回帰 ill-conditioned、件数・年次分布を pass-1 census 報告)。2020-21 の ZIRP 期に void が集中する見込みを事前記録 — void はイベント不成立であって欠陥ではない |
| onset イベント | z が **−Z_th を上から下へクロス** (直前の valid z 観測 ≥ −Z_th ∧ 当日 z < −Z_th — void 跨ぎのクロスも「直前 valid 観測」基準で判定)。**min separation = 5 valid D1** (直前 onset から 5 日未満のクロスは無視 — 同一エピソード多重計上防止) |
| warmup 事前記録 | 価格 parquet 左端 = 2013-12-29 → W=252 valid D1 warmup により**最初の有効 z ≈ 2014-12 末 = 2014 年はほぼ全日 warmup void → 実効 explore ≈ 2015-01..2021-12 (7 年)**。これは機械的 warmup であって窓選択ではない (pass-1 census で実測値を記録) |
| Z_th 機械選定 | pass-1 (outcome 非接触) で grid **{1.5, 2.0, 2.5}** から explore 窓 onset 数 N_ev ∈ [30, 150] のうち **\|N_ev − 60\| 最小**を選定、tie は大きい方。全 grid で N_ev < 30 → **UNDERPOWERED** (pass-2 非解錠)。全 grid で N_ev > 150 → 2.5 採用。選定は機械的・事前宣言 (MoF #4 §4 rule 校正の同型) |
| サイド | **LONG のみ** (下方 onset)。上方 onset (+Z_th 上抜け) は同一機械定義で列挙・記録するが descriptive (claim 恒久禁止) |
| horizon | **PRIMARY = +21 valid D1** close-to-close (t0 = onset 日 close、entry = onset 当日終値 — シグナルは同日 close + lag-1bd yields で構成されるため lookahead なし)。net move (pips, pip=0.01) = (C_{t0+21} − C_{t0})/0.01。span > 45 暦日 → void。**SECONDARY = +5 valid D1 (診断のみ、gate 判定に不使用)** |
| 窓 | **explore = onset 日 2014-01-01..2021-12-31**。12 月末 onset の outcome 完了が 2022-01 に食い込むのは explore イベントの outcome 完了であって OOS シグナル接触ではない (cc-mr §3 前例)。**OOS = onset 日 2022-01-01..2026-05-31、候補凍結後 1 回のみ・explore 全 gate PASS 時のみ接触** (§4-4 機械ロック)。OOS 窓は介入エピソードを含むが**介入ラベルは一切使用しない** (z 定義に価格 range/co_ret 成分なし = E-A 凍結 rule と非同型、§8) |
| pair | USD_JPY 単独。横展開は新 pre-reg + 新敵対的検証 |

## §4 接触順序 (two-pass、E22/cc-mr §4 パターン)

1. **pass-1**: イベント列挙 (`date|z|diff2y|side`) + Z_th 機械選定 + census (N/年次分布/void 件数 [縮退・staleness・n_bars]) + **無条件 \|fwd21\| 分布 (シグナル非依存、aggregate 分位のみ)** → gate A 判定 + MDE 確定 + z 系列 ACF 実測。**firewall (明文 pin): pass-1 成果物に per-date の forward 値を一切含めない** — 無条件 \|fwd21\| は median/sd/p25/p75 のみ。イベント CSV は signal 列のみ。**コミットしてから pass-2 解錠**。
2. **pass-2**: primary + gates C–G + knife-edge + verdict。stats はハーネス同梱 (seed 20260819)。
3. gate A/B 不通過 → pass-2 非解錠 (ハーネス assert で機械強制)。
4. **OOS pass** (explore 全 binding gate PASS 時のみ、1 回): E22 §4-4 と同一の 4 点機械ロック — (i) `--unlock-oos` flag、(ii) pass-2 verdict JSON の git commit 済み assert、(iii) OOS 成果物の不在 assert (書出後の再走恒久禁止)、(iv) swap 延伸 manifest 追補 (§7) の commit 済み assert。単一接触の意味論 = E22 事前宣言を継承。

## §5 統計 gates (凍結)

- **Gate A (headroom、pass-1)**: 無条件 median \|fwd21 move\| ≥ **10× stressed_RT = 43p**。不通過 → family KILL。
- **Gate B (power、pass-1)**: **N_ev ≥ 30** (選定 Z_th)。未達 → **UNDERPOWERED** (PASS/FAIL ではない。Z_th grid 拡張・窓拡張による救済は禁止 — N 不足は「2014-2021 に大乖離が少ない」という事実の記録)。
- **Gate C (primary)**: onset LONG の **pooled mean net_21 (swap 込み、point 摩擦)** について、**year-matched placebo permutation の片側 p ≤ 0.05** (§6)。placebo が年次 drift を保存するため、**本 gate は「同年の任意日ロング」への超過 = timing の検定** (drift β では通過できない)。
- **Gate D (経済 floor、有意性主張なし)**: pooled mean net_21 > 0 を **adverse 端 (stressed_RT 4.3p + m_adverse 1.65%/yr)** で要求。**RT 3× (6.4p) 感度を非拘束で併記** (E22 条件 8 継承)。
- **Gate E (集中)**: S_y = 暦年 y のイベント net 和。**max_y \|S_y\| / Σ_y \|S_y\| ≤ 0.50**。
- **Gate F (一貫性)**: onset を含む暦年のうち年次 mean net_21 > 0 の年が **≥ 60%** ∧ **LOYO で pooled mean 符号不変**。事前記録: イベント疎年 (N_y < 3) は符号カウント分母から除外し件数報告 (cc-mr 単年 regime-kill 前例の防御と false-kill の均衡)。
- **Gate G (dose-response)**: onset を \|z\| 深さ tercile に分割、**T3 (最深) − T1 の mean net_21 符号 = 正** (深い乖離ほど戻りが大きい)。on-record: tercile 2 分割差分のみの弱い gate (E22 gate G 縮退の on-record と同型)。
- **knife-edge (全 gate PASS 後のみ、選択不使用)**: (i) W ∈ {189, 378}、(ii) Z_th ±0.5 (選定値の隣接、grid 外は生成しない)、(iii) anchor を 10y 差分 (DGS10 − JGB10y) に置換、(iv) fwd を log return で再計算、(v) placebo 代替 null = event-block sign-flip (seed 20260820)。**いずれかで primary mean net 符号反転 → FAIL**。
- verdict: 全 binding gate (A, C–G) 通過 = **explore PASS** → OOS pass。gate B 未達 = **UNDERPOWERED**。他 = **FAIL クローズ** (OOS 非接触)。閾値の事後変更禁止。
- **OOS gates (事前凍結)**: (i) 同一定義の片側 placebo p ≤ 0.05 (seed 20260821)、(ii) OOS pooled mean net_21 adverse 端 > 0、(iii) **OOS N_ev ≥ 15** 未達 = OOS UNDERPOWERED、(iv) 経済 floor: OOS mean net_21 ≥ **+10.0p**。**全通過 = family PASS → stage-2 (執行設計) は別 pre-reg + user 最終承認 — live/shadow/tier/lot 変更ゼロ、autopilot による実装着手も禁止**。
- **BH 分母合流条項**: 本 verdict 前に他 explore family 起動時は BH q=0.10 合流 (cc-mr §5 (c) 継承)。
- **claim 範囲の恒久限定**: family-pooled USD_JPY LONG onset のみ。サブ期間/深さ bin/上方サイド等の per-slice claim は結果如何によらず禁止。**非介入型乖離のみ** (§1 負 prior 7 の外挿限界)。
- **分解報告義務 (lane-owner 要請 4、E21 慣行)**: verdict には gross move / swap / net を**分離して併記** (swap 受取が verdict を作っている場合に識別可能にする)。

## §6 permutation と正直 MDE (完全凍結)

- **primary null = year-matched placebo resampling**: 各 onset を**同一暦年内**の有効非イベント日 (onset 集合の ±5 valid D1 を除外、fwd21 有効日のみ) から一様抽出で再配置。placebo セットにも **min separation 5 valid D1 を強制** (実イベント列と同一の重複構造 — overlap 分散の非対称を排除)。B = **10,000**、numpy `default_rng(20260819)`。**p_one = (1 + #{mean_perm ≥ mean_obs}) / (1 + B)**。year-matched により各年の drift を null に保存 = 検定対象は純粋に「年内のどこで買うか」の timing。
- OOS: 同一構成、seed 20260821。
- knife-edge (v) 代替 null: 21bd block sign-flip (イベント net の符号を 2-ISO-week block 単位で flip、seed 20260820) — 診断併記、選択不使用。
- **正直 MDE (事前記録)**: N_ev = 60 想定・無条件 σ_21 ≈ 250-300p (pass-1 実測で確定) → mean-net MDE ≈ (1.645+0.84) × σ_21/√N_ev × 重複 inflation (min-sep 5 vs h 21 → 最大 16/21 重複、inflation ~1.2-1.5×) ≈ **90-160p**。**E-C 実測の介入 dip リトレース (+188p/N=3) は届く帳簿、slow-MR 家系の +3-12p 級は構造的に届かない** — 後者なら本設計は意図どおり kill する (retail-viability filter)。pass-1 が σ_21 実測から MDE を確定し report 記載 (gate 閾値は変えない)。
- 検出力の帳簿: 真効果 +100p なら power ≈ 0.5-0.7 / +50p なら ≈ 0.15-0.3 (σ=275p、N=60、inflation 1.35 仮定)。**FAIL ≠ falsified の power caveat は §9 で凍結**。

## §7 摩擦・swap (凍結)

- **RT friction (USD_JPY)**: point = 2.14p (friction-analysis 表)、**stressed = 4.3p (2.0×)**。gate C は point、gate D binding は stressed + m_adverse。**RT 6.4p (3×) 感度は非拘束報告**。**honesty 条項**: 歴史 mid 測定であり執行可能性を主張しない — 実装経路は実スプレッド実測必須 (E22 §7 同型)。
- **swap (per-event、LONG 固定)**: swap_pips = (rate_used/100) × (H_cal/365) × S_entry/0.01。rate_used = d_USD_JPY(t0) − m (d = e20 列 %/yr、USD_JPY LONG は **earn 側**)。**m_adverse = 1.65%/yr (gate D binding) / m_point = 1.0%/yr (gate C・感度併記)**。H_cal = t0→t0+21 の実暦日数。
- **規模の事前記録**: e20 panel 実測で d_USD_JPY は 2014-2015 ≈ +0.1〜0.4 / 2018-2019 ≈ +2.2〜2.5 / 2020-2021 ≈ +0.1〜0.25 %/yr → 21bd (≈30 暦日) の swap は **−4p〜+20p/event** (m 控除後、S≈105-115)。earn 側とはいえ ZIRP 期はほぼゼロ = swap が verdict を作ることはない見込み (支配的なら分解報告)。
- **E20 隣接の構造分離**: rates はシグナル (anchor) に入る — これは E20 ban (sign ランキング) との **estimand 分離**であってソース分離ではない (§8 で明示差分)。swap 減算は outcome join 後のみ (コード上 builder 分離、敵対的検証で実査)。
- **OOS swap 延伸 (事前宣言)**: e20_carry_level.csv は 2022-12 終端。OOS pass 実行前に `e20_carry_level_ext` 延伸 (E22 §7 条件 4 と同一仕様: フル被覆 + 重複等値 assert + manifest 追補別コミット)。E22 が延伸済みならそのファイルを共用 (等値 assert は同一)。

## §8 ban 隣接差分節 (必須)

- **ppp #14 (ban = 5y rolling z × 月次サンプリング × 21-63bd の CPI-PPP 回帰)**: 差分 = ① anchor が CPI 価格水準でなく**金利観測** (日次リプライス、staleness 61 日 → 1 日)、② 月次 IC サンプリングでなく **onset イベント設計**、③ 7 ペア pooled でなく USD_JPY 単独 + 片側。ppp の承認済み再挑戦経路 (a)「実質金利差込みモデル等の**推定量変更** + 明示差分節」に該当する正規の隣接新 family。**負 prior (ppp の USD_JPY per-pair IC 負) は §1 に正直転記済み**。
- **E20 (凍結 = sign(政策金利差)/sign(Δ63bd 2y 差) × 日足バイアス × テクニカル entry、保有 1-10d の同型再提案禁止)**: 差分 = ① E20 は金利差の**符号/変化をそのままシグナル**にするランキング (クロスペア)、本件は**スポットの残差乖離** (金利差は説明変数であってシグナルではない — z は spot が動かねば動かない)、② 保有 21bd ≠ 1-10d、③ 単一ペア片側イベント ≠ 13 ペア日次バイアス。E20 診断の「将来 rates 系の新 S1 は Q2 中抜けと fold 3 集中を機構で説明できる仮説に限る」への応答: 本件の機構は「金利差→方向」でなく「乖離→回帰」であり、E20 の quintile 中抜けは金利差レベルの非単調性の話で本 estimand には転移しない (ただし §1 負 prior 3 に正直記載)。
- **cc-mr (クローズ = slow location-anchor [mean/percentile/**regression**] band fade × multi-day × AUD_NZD/AUD_CAD/NZD_CAD 全着せ替え)**: **ペア scope 外 (USD_JPY)** が一次差分。二次差分 = cc-mr の regression anchor は**価格自身の時間回帰** (location)、本件は**外生金利系列への回帰** (価格外情報)。家系 resemblance (slow band fade) は §1 負 prior 2 に正直継承 — ban 違反ではないが同帳簿ゾーンであることを隠さない。
- **level family (h4/channel/sweep/rn/zz、価格由来ライン全滅)**: anchor が価格幾何でない — 非該当。
- **MoF #4 cross-LOCK**: ① explore 窓 2014-2021 = **介入ゼロ実測** (§2)、② z 定義に day range / co_ret 成分なし (E-A 凍結 rule (X,Y) と非同型 — 敵対的検証で機械確認)、③ 介入ラベル・介入日推定は全工程で不使用、④ OOS (2022+) でも label-free (z-onset のみ)。mof-next-episode-reverdict (将来エピソード) には非接触。
- **E12 P-10 (volume×価格)**: columns=["Close"] assert で遮断。**E1/#22 ECG/E21 口座データ**: 非接触。
- **E23 (中銀声明テキスト)**: 本件は数値金利のみ (テキスト特徴量ゼロ) — 非重複。BH 分母合流条項 (§5) が両建て時を governs。

## §9 分岐 (凍結) と事前コミット節

- **PASS の意味の事前凍結 (E22 §2.1 様式)**: explore PASS → OOS pass (単一接触、同 wave)。**family PASS = 「stage-2 (執行設計 pre-reg + user 最終承認) の起草権」のみ** — live 実装・shadow 化・lot・tier 変更は一切伴わない。PASS しても月利ミッションへの寄与は stage-2 の執行設計と摩擦実測を通過してから。
- **FAIL 時クローズ範囲 (事前凍結)**: 「**日次国債金利差アンカー (rolling 回帰帯、2y/10y テナー・W/Z_th 摂動を含む) × USD_JPY × 帯下 onset LONG × 5-63bd 固定ホライズン の全変種**」をクローズ。**user 水平線理論の機械核 v2 死亡** = 裁量スタックの残る未検証は執行層 (15m/1m) と exit 層のみ ([[../analyses/family-c-anchor-automation-2026-08-18|automation doc]] §4 の系譜完結)。**power caveat (クローズ文言に義務付け)**: FAIL は効果不在の証明ではない (MDE 90-160p、slow-MR 家系級 +3-12p への検出力 ≈ 5-10%)。クローズ根拠は『この設計での retail-viability 不成立』であり、「rate anchor は falsified」型引用は estimand 監査なしに禁止 (user 恒久指示 2026-08-05)。復活経路 = 新 anchor 構成 (例: OIS/先物 implied 政策 path、有償) + 新 family + 事前差分節 + 新敵対的検証のみ。
- **UNDERPOWERED (explore N_ev < 30)**: family PARK。イベント定義は保存、**Z_th 緩和・窓拡張による救済再試行は禁止**。再開 = OOS 窓が将来 explore 化できる split 再設計 (ppp 再挑戦経路 (b) 同型) の新 pre-reg のみ。
- **接触規律**: 測定は凍結コミット後のみ。pass-1 → コミット → pass-2。OOS はシグナル日 2022+ にexplore pass 中非接触 (ハーネスの explore モードは 2022+ onset 行を生成しない)。
- 動機記録 (R1 手続き): user 明示指示 (2026-08-19「進めて」— BT 実施の直接承認) + 改訂 WIP 原則 (能動枠 0 本解消) + データ駆動 (自動化パケットで材料完備)。感情的動機なし。
- registry: 凍結コミットと同時に `family-c-explore-verdict-deadline` (deadline_info、凍結 +10 日 = **2026-08-29**、到達経路 = 本セッションが two-pass を同日実行予定 + Tier-A cron 表示) を登録。

## §10 敵対的検証 条件 → 解決マッピング (検証 report が SSOT)

(敵対的検証実行後に記入 — DRAFT 状態の本節は placeholder)

**コミット規律**: 本文書 + `tools/family_c_anchor_explore.py` + data_freeze コピー + manifest + 検証 report + 台帳 #26 行 + registry 追記を**同一コミットで凍結 (rule:R1 手続き)**。測定はコミット後開始。
