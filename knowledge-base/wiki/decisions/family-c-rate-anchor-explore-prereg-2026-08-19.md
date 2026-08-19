# family_c_rate_anchor_deviation (台帳 #26) explore pre-reg — 観測前プロトコル凍結 (2026-08-19)

**状態**: 🔒 **FROZEN (2026-08-19、本コミットが凍結点 — 以後の定義・閾値変更禁止、逸脱は verdict 無効)**。敵対的検証 GO-WITH-CONDITIONS (blocking 10 条) を全反映済み (§10)
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
| 金利⇄価格 join | calendar-date join、**yields は lag 1 暦日** (シグナル日 d は label ≤ d−1 の値を ffill 使用) — JGB (17:30 JST 公表) / DGS (~23:00 UTC 公表) の公表時刻 knife-edge を構造排除。**ffill staleness > 12 暦日 → 当該日 anchor void** (件数報告。敵対的検証 blocking C1: JGB の実測最大 gap = 11 暦日 [2019 Golden Week、他に 2014-01/2019-01/2020-01 に 7 日 gap] — 旧値 5 日では GW ごとに完全窓規則が 252 日 blackout を連鎖させ 2019-2021 が実質全滅していた。12 日は実測 gap 全被覆の最小整数 + DGS は >5 日 gap ゼロ)。staleness は **lag date d−1 で計測** (使用時の値 age ≤ 13 暦日)。**日付境界変換は明示コード + test pin** (ベンダー日足 lesson 2026-08-18)。yields は 2026-08-19 時点の改定済み値 (first print 復元は 252d rolling z には非本質 — on-record) |
| swap panel | `knowledge-base/raw/bt-results/e20/e20_carry_level.csv` USD_JPY 列 (policy diff %/yr、2013-01..2022-12 = explore 完全被覆、凍結済みファイル)。sha256 pin |
| 介入ゼロ確認 | `data/external/mof_interventions.csv`: **2014-01-01..2021-12-31 の USD_JPY 介入 = 0 行 (2026-08-19 実測)** — MoF #4 cross-LOCK (介入ラベル非使用 + 価格シグネチャ推定禁止) は explore 窓選択で構造遵守 |
| E12 firewall | parquet ロードは `columns=["Close"]` + **Volume/vwap/High/Low 非読取をコード assert** (gate A は \|fwd21\| ベースで H/L 不要 — MFE/MAE 系 gate なし) |
| sha256 pin | `knowledge-base/raw/bt-results/family-c/data_freeze_manifest_2026-08-19.json`: 上記 4 ファイルの sha256 + **行数** assert。**実ロード対象 (--parquet 引数) の sha256 を manifest pin と直接照合** (bare/部分 parquet の差し替えを構造遮断 — 敵対的検証 C2) |
| parquet living-cache 条項 | parquet は main checkout の絶対 path (E22 条件 16 同型): 凍結・pass-1/pass-2・OOS は同一実体を sha256 で毎回 assert、**drift 検出時は manifest 編集でなく再凍結コミット**。再現は「sha256 で同定されるファイル実体」に host-pin (on-record) |

## §3 シグナル・サンプリング定義 (全 DoF 凍結 — 単一構成、grid なし)

| 要素 | 凍結値 |
|---|---|
| anchor 入力 | diff2y(d) = DGS2(d) − JGB2y(d) (%pt、lag 1bd 適用後) |
| フェアバリュー | rolling OLS: log C_d = a + b·diff2y over 直近 **W = 252 valid D1** (完全窓必須)。fitted_d = a + b·diff2y_d |
| 乖離 z | z_d = (log C_d − fitted_d) / std(residuals, ddof=1) (同一 252 窓) |
| 縮退 void | 窓内 std(diff2y) < **0.10 %pt** → 当該日 z void (回帰 ill-conditioned、件数・年次分布を pass-1 census 報告)。2020-21 の ZIRP 期に void が集中する見込みを事前記録 — void はイベント不成立であって欠陥ではない |
| onset イベント | z が **−Z_th を上から下へクロス** (直前の valid z 観測 ≥ −Z_th ∧ 当日 z < −Z_th — void 跨ぎのクロスも「直前 valid 観測」基準で判定)。**min separation = 5 valid D1** (直前 onset から 5 日未満のクロスは無視 — 同一エピソード多重計上防止) |
| warmup 事前記録 | 価格 parquet 左端 = 2013-12-29 → W=252 valid D1 warmup により**最初の有効 z ≈ 2014-12 末 = 2014 年はほぼ全日 warmup void → 実効 explore ≈ 2015-01..2021-12 (7 年)**。これは機械的 warmup であって窓選択ではない (pass-1 census で実測値を記録) |
| Z_th 機械選定 | pass-1 (outcome 非接触) で grid **{1.5, 2.0, 2.5}** から explore 窓 onset 数 N_ev ∈ [30, 150] のうち **\|N_ev − 60\| 最小**を選定、tie は大きい方。全 grid で N_ev < 30 → **UNDERPOWERED** (pass-2 非解錠)。全 grid で N_ev > 150 → 2.5 採用。**混在で range 内ゼロ (一部 <30 ∧ 一部 >150) → UNDERPOWERED** (敵対的検証 C3/C5: 反保守側の多イベント採用を禁止する完全列挙)。選定は機械的・事前宣言 (MoF #4 §4 rule 校正の同型) |
| min-sep の単位 | onset の min-sep 5 は **frame (valid D1) position で計測** (z-void 圧縮 index ではない — placebo/null と同一単位、敵対的検証 C3。test pin あり) |
| サイド | **LONG のみ** (下方 onset)。上方 onset (+Z_th 上抜け) は同一機械定義で列挙・記録するが descriptive (claim 恒久禁止) |
| horizon | **PRIMARY = +21 valid D1** close-to-close (t0 = onset 日 close、entry = onset 当日終値 — シグナルは同日 close + lag-1bd yields で構成されるため lookahead なし)。net move (pips, pip=0.01) = (C_{t0+21} − C_{t0})/0.01。span > 45 暦日 → void。**SECONDARY = +5 valid D1 (診断のみ、gate 判定に不使用)** |
| 窓 | **explore = onset 日 2014-01-01..2021-12-31**。12 月末 onset の outcome 完了が 2022-01 に食い込むのは explore イベントの outcome 完了であって OOS シグナル接触ではない (cc-mr §3 前例)。**OOS = onset 日 2022-01-01..2026-05-31、候補凍結後 1 回のみ・explore 全 gate PASS 時のみ接触** (§4-4 機械ロック)。OOS 窓は介入エピソードを含むが**介入ラベルは一切使用しない** (z 定義に価格 range/co_ret 成分なし = E-A 凍結 rule と非同型、§8) |
| pair | USD_JPY 単独。横展開は新 pre-reg + 新敵対的検証 |

## §4 接触順序 (two-pass、E22/cc-mr §4 パターン)

1. **pass-1**: イベント列挙 (`date|z|diff2y|side`) + Z_th 機械選定 + census (N/年次分布/void 件数 [warmup/stale_anchor/degenerate/n_bars/ret を分離報告] + **anchor 寄与 share 分位** [敵対的検証 L2-7/C4 — rates-content 識別の材料]) + **無条件 fwd21 分布 (シグナル非依存、aggregate のみ: \|move\| median/p25/p75 [gate A 用] + signed sd [MDE 用 — sd(\|X\|) は MDE を ~1.6x 過小報告する、敵対的検証 C2])** + z 系列 ACF 実測。**firewall (明文 pin): pass-1 成果物に per-date の forward 値を一切含めない**。**コミットしてから pass-2 解錠**。
2. **pass-2**: primary + gates C–G + ablation 対照 + knife-edge + verdict。stats はハーネス同梱 (seed 20260819)。解錠 assert = pass-1 JSON + イベント CSV + **ハーネス自身**の commit 済み (敵対的検証 C12/C14)。
3. gate A/B 不通過 → pass-2 非解錠 (ハーネス assert で機械強制)。**pass-2 で fwd 無効 drop 後の測定 N < 30 → verdict = UNDERPOWERED** (drop 件数は報告義務 — 敵対的検証 C8/C11)。
4. **OOS pass** (explore 全 binding gate PASS 時のみ、1 回): 4 点機械ロック**実装済み** (敵対的検証 blocking C5/C6 — 凍結ハーネスに `oos` モード同梱) — (i) `--unlock-oos` flag、(ii) pass-2 verdict JSON の git commit 済み assert、(iii) OOS 成果物の不在 assert (書出後の再走恒久禁止)、(iv) swap 延伸 manifest 追補 (§7) の commit 済み assert。単一接触の意味論 = E22 事前宣言を継承。

## §5 統計 gates (凍結)

- **Gate A (headroom、pass-1)**: 無条件 median \|fwd21 move\| ≥ **10× stressed_RT = 43p**。不通過 → family KILL。
- **Gate B (power、pass-1)**: **N_ev ≥ 30** (選定 Z_th)。未達 → **UNDERPOWERED** (PASS/FAIL ではない。Z_th grid 拡張・窓拡張による救済は禁止 — N 不足は「2014-2021 に大乖離が少ない」という事実の記録)。
- **Gate C (primary — 敵対的検証 blocking C1 で null 差し替え済み)**: 統計量 = **mean over events of (net_21 − μ_year)** (μ_year = 同暦年の**全 valid 日無条件 net_21 平均** — 同一 swap/RT 会計。年次 drift を統計量側で除去)。null = **episode-block sign-flip** (イベントを frame-position gap < 21 valid D1 で episode に連結し、block 和の符号を等確率 flip、B=10,000、seed 20260819 — イベント間相関を保存)。**片側 p ≤ 0.02**。旧 null (year-matched placebo mean) は合成 probe で **type-I 20.6-29.0% @ 名目 5%** (イベント clustering + vol conditioning の二重反保守) と実証され棄却。差し替え null の probe 実測 size ≈ 8.7-9.2% @ 名目 5% (drift-only では 4.3% = timing 検定性を保持) → **名目 0.02 ≈ 実効 ~5% として閾値を較正** (on-record: 残余 ~1.8x inflation を閾値側で吸収)。
- **Gate D (経済 floor、有意性主張なし)**: pooled mean net_21 > 0 を **adverse 端 (stressed_RT 4.3p + m_adverse 1.65%/yr)** で要求。**RT 3× (6.4p、m_adverse 併用) 感度を非拘束で併記** (E22 条件 8 継承)。
- **Gate E (集中)**: S_y = 暦年 y のイベント net 和。**max_y \|S_y\| / Σ_y \|S_y\| ≤ 0.50**。
- **Gate F (一貫性)**: onset を含む暦年のうち年次 mean net_21 > 0 の年が **≥ 60%** ∧ **LOYO で pooled mean 符号不変**。イベント疎年 (N_y < 3) は符号カウント分母から除外し件数報告。**全年が疎の場合は全年符号 share に fallback** (敵対的検証 C10 — 未定義分岐の凍結)。
- **Gate G (dose-response)**: onset を \|z\| 深さ tercile に分割、**T3 (最深) − T1 の mean net_21 符号 = 正**。on-record: 実質 T3−T1 符号チェックの弱い gate。**false-kill 定量 (敵対的検証 C9): flat dose-response の真効果下で ~40-50%** — cc-mr gate F 前例と同じく anti-gate-shopping として意図的に binding 維持 (今緩めるのは gate-shopping)。
- **ablation 対照 (診断・選択不使用 — 敵対的検証 blocking C4)**: b≡0 対照 (z = rolling mean/std of log C のみ、同 W・同 Z_th) の onset 集合と Jaccard 重複 + 対照 mean net を pass-2 で報告。**解釈規則 (凍結): Jaccard ≥ 0.5 ∧ 対照 mean net ≥ 0.8× primary → PASS でも claim 文に「rates-content unidentified」caveat を義務付け、rates 系 family 拡張は対照分離を再現できるまで禁止** (価格のみ dip-buy と識別できない PASS を rates 機構に誤帰属させない — user 恒久指示 2026-08-05 の estimand 監査対応)。
- **knife-edge (全 gate PASS 後のみ、選択不使用)**: (i) W ∈ {189, 378}、(ii) Z_th ±0.5 (選定値の隣接、**grid 内のみ**)、(iii) anchor を 10y 差分 (DGS10 − JGB10y) に置換、(iv) **entry を t0+1 valid D1 close に遅延** (窓 t0+1→t0+22 — 極値 print 進入への感度、敵対的検証 C6。log-return 変種は pip 差分と 2 次まで等価で無歯のため差し替え済み)。**(i)-(iv) いずれかで primary mean net 符号反転 → FAIL**。(v) 代替 null 診断 = year-matched placebo (旧 primary、seed 20260820) — **診断併記のみ・判定不使用** (反保守側の参考値)。
- verdict: 全 binding gate (A, C–G) 通過 = **explore PASS** → OOS pass。gate B 未達 (pass-1 onset 数 or pass-2 測定 N < 30) = **UNDERPOWERED**。他 = **FAIL クローズ** (OOS 非接触)。閾値の事後変更禁止。
- **OOS gates (事前凍結)**: **介入隣接 partition を先行適用** (敵対的検証 blocking L2-1): MoF 開示介入日の +21 valid D1 以内に立つ onset は binding 集合から除外し記述併記 (with-adjacent pooled は非拘束感度)。開示ラベルは **signal には一切入らず、OOS verdict 時に本 partition のためだけに 1 回読む** (§8 ④)。binding 集合に対し (i) gate C と同一の demean + episode-block null、**片側 p ≤ 0.02** (seed 20260821)、(ii) OOS mean net_21 adverse 端 > 0、(iii) **binding N_ev ≥ 15** 未達 = OOS UNDERPOWERED、(iv) 経済 floor: OOS mean net_21 ≥ **+10.0p**。**全通過 = family PASS → stage-2 (執行設計) は別 pre-reg + user 最終承認 — live/shadow/tier/lot 変更ゼロ、autopilot による実装着手も禁止**。
- **BH 分母合流条項**: 本 verdict 前に他 explore family が**起動** (= 敵対的検証済み pre-reg の凍結コミット = 測定解錠。DRAFT/起草中は分母に入らない — 敵対的検証 L2-5 で定義凍結) した場合は BH q=0.10 合流 (cc-mr §5 (c) 継承)。family A は 2026-08-19 現在 DRAFT 未測定 = 分母外。
- **claim 範囲の恒久限定**: family-pooled USD_JPY LONG onset のみ。サブ期間/深さ bin/上方サイド等の per-slice claim は結果如何によらず禁止。**非介入型乖離のみ** (§1 負 prior 7 の外挿限界)。
- **分解報告義務 (lane-owner 要請 4、E21 慣行)**: verdict には gross move / swap / net を**分離して併記** (swap 受取が verdict を作っている場合に識別可能にする)。

## §6 permutation と正直 MDE (完全凍結 — 敵対的検証 C1 で null 差し替え)

- **primary null = 年内 demean + episode-block sign-flip**: 統計量 = mean(net_21 − μ_year) (μ_year = 同暦年の全 valid 日無条件 net_21 平均、同一会計)。イベントを frame-position gap < 21 valid D1 で episode block に連結し、demeaned block 和の符号を等確率 flip (B = 10,000、numpy `default_rng(20260819)`)。**p_one = (1 + #{stat_perm ≥ stat_obs}) / (1 + B)、閾値 0.02**。
- **null 差し替えの経緯 (on-record、probe = 敵対的検証 report §lens-1)**: 旧 primary (year-matched placebo mean resampling) は合成 RW probe で **type-I 20.6% (const vol) / 29.0% (vol-clustered) @ 名目 5%** — (i) min-sep 5 << h 21 によるイベント净の正相関を placebo が持たない、(ii) onset の vol-conditioning、の二重反保守。差し替え null は同 probe で size 8.7-9.2% (drift-only 4.3% = timing 検定性保持) → **名目 0.02 ≈ 実効 ~5%** に較正。旧 null は knife-edge (v) 診断に降格 (判定不使用)。
- OOS: 同一構成 (OOS 年の μ_year は OOS valid 日から計算)、seed 20260821、片側 p ≤ 0.02。
- **正直 MDE (事前記録、敵対的検証 C2 で σ 定義修正)**: σ_21 は **signed fwd21 の sd** (pass-1 実測、aggregate のみ — sd(\|fwd21\|) は ~0.6× に過小で MDE を誤報告する)。mean-net MDE ≈ **2.485 × σ_21(signed)/√N_ev × 1.35** (重複 inflation 事前固定) — N_ev=60・σ≈275p で ≈ **120p 前後** (pass-1 実測で確定値を report、gate 閾値は変えない)。**E-C 実測の介入 dip リトレース (+188p/N=3) は届く帳簿、slow-MR 家系の +3-12p 級は構造的に届かない** — 後者なら本設計は意図どおり kill する (retail-viability filter)。
- 検出力の帳簿: 真効果 +100p なら power ≈ 0.4-0.6 / +50p なら ≈ 0.1-0.25 (σ=275p、N=60、inflation 1.35、α=0.02)。**FAIL ≠ falsified の power caveat は §9 で凍結**。

## §7 摩擦・swap (凍結)

- **RT friction (USD_JPY)**: point = 2.14p (friction-analysis 表)、**stressed = 4.3p (2.0×)**。gate C は point、gate D binding は stressed + m_adverse。**RT 6.4p (3×) 感度は非拘束報告**。**honesty 条項**: 歴史 mid 測定であり執行可能性を主張しない — 実装経路は実スプレッド実測必須 (E22 §7 同型)。
- **swap (per-event、LONG 固定)**: swap_pips = (rate_used/100) × (H_cal/365) × S_entry/0.01。rate_used = d_USD_JPY(t0) − m (d = e20 列 %/yr、USD_JPY LONG は **earn 側**)。**m_adverse = 1.65%/yr (gate D binding) / m_point = 1.0%/yr (gate C・感度併記)**。H_cal = t0→t0+21 の実暦日数。
- **規模の事前記録**: e20 panel 実測で d_USD_JPY は 2014-2015 ≈ +0.1〜0.4 / 2018-2019 ≈ +2.2〜2.5 / 2020-2021 ≈ +0.1〜0.25 %/yr → 21bd (≈30 暦日) の swap は **−4p〜+20p/event** (m 控除後、S≈105-115)。earn 側とはいえ ZIRP 期はほぼゼロ = swap が verdict を作ることはない見込み (支配的なら分解報告)。
- **E20 隣接の構造分離**: rates はシグナル (anchor) に入る — これは E20 ban (sign ランキング) との **estimand 分離**であってソース分離ではない (§8 で明示差分)。swap 減算は outcome join 後のみ (コード上 builder 分離、敵対的検証で実査)。
- **OOS swap 延伸 (事前宣言)**: e20_carry_level.csv は 2022-12 終端。OOS pass 実行前に `e20_carry_level_ext` 延伸 (E22 §7 条件 4 と同一仕様: フル被覆 + 重複等値 assert + manifest 追補別コミット)。E22 が延伸済みならそのファイルを共用 (等値 assert は同一)。

## §8 ban 隣接差分節 (必須)

- **ppp #14 (台帳原文 verbatim: 「同型再試行禁止 (5y-z 月次×21-63bd)、再挑戦は実質金利差込みモデル等 + 明示差分 or 2022+ 込み split 再設計のみ」)**: **一次論拠 = ban の連言 scope 外** (anchor が CPI 価格水準でなく金利観測 [日次リプライス、staleness 61 日 → 1 日] / 月次 IC サンプリングでなく onset イベント設計 / 7 ペア pooled でなく USD_JPY 単独片側 — horizon 21bd の重複単独では連言 ban は発動しない)。二次論拠 = 再挑戦経路の「実質金利差込みモデル**等**」クラスに名目金利差 anchor として該当 (nominal vs 実質の差は on-record — 敵対的検証 L2-4 で paraphrase を原文引用に訂正済み)。**負 prior (ppp の USD_JPY per-pair IC 負) は §1 に正直転記済み**。
- **E20 (凍結 = sign(政策金利差)/sign(Δ63bd 2y 差) × 日足バイアス × テクニカル entry、保有 1-10d の同型再提案禁止)**: 差分 = ① E20 は金利差の**符号/変化をそのままシグナル**にするランキング (クロスペア)、本件は**スポットの残差乖離** — z は各窓内で diff2y と OLS 直交する残差から作られるため、**構造的に金利差レベル/変化の情報を含まない** (シグナルは「価格が金利含意からどれだけ外れたか」のみ)。これが E20 診断の「Q2 中抜けと fold 3 集中を機構で説明できる仮説に限る」条項への機構的応答である: E20 の病理は金利差**そのもの**の方向情報の欠如 (quintile 非単調) であり、残差乖離 estimand はその情報を最初から使わない (敵対的検証 L2-3)。② 保有 21bd ≠ 1-10d (SECONDARY h=5 は banned 保有帯と重なるが非拘束・診断のみ)、③ 単一ペア片側イベント ≠ 13 ペア日次バイアス。負 prior は §1-3 に正直記載。
- **cc-mr (クローズ = slow location-anchor [mean/percentile/**regression**] band fade × multi-day × AUD_NZD/AUD_CAD/NZD_CAD 全着せ替え)**: **ペア scope 外 (USD_JPY)** が一次差分。二次差分 = cc-mr の regression anchor は**価格自身の時間回帰** (location)、本件は**外生金利系列への回帰** (価格外情報)。家系 resemblance (slow band fade) は §1 負 prior 2 に正直継承 — ban 違反ではないが同帳簿ゾーンであることを隠さない。
- **level family (h4/channel/sweep/rn/zz、価格由来ライン全滅)**: anchor が価格幾何でない — 非該当。
- **MoF #4 cross-LOCK**: ① explore 窓 2014-2021 = **介入ゼロ実測** (§2)、② z 定義に day range / co_ret 成分なし (E-A 凍結 rule (X,Y) と非同型)、③ 介入ラベル・介入日推定は**シグナル構築の全工程で不使用**、④ **OOS では開示済みラベルを「介入隣接 partition (§5)」のためだけに verdict 時 1 回読む** — signal には入らず、binding 集合から隣接 onset を外す用途のみ (E-C の既公表 outcome [+188p 等] が §1 prior に入っている以上、介入隣接 onset を binding に含めると「観測済み結果の再判定」になる — 敵対的検証 blocking L2-1 の処置)。mof-next-episode-reverdict (将来エピソード) には非接触。
- **E12 P-10 (volume×価格)**: columns=["Close"] assert で遮断。**E1/#22 ECG/E21 口座データ**: 非接触。
- **E23 (中銀声明テキスト)**: 本件は数値金利のみ (テキスト特徴量ゼロ) — 非重複。BH 分母合流条項 (§5) が両建て時を governs。

## §9 分岐 (凍結) と事前コミット節

- **PASS の意味の事前凍結 (E22 §2.1 様式)**: explore PASS → OOS pass (単一接触、同 wave)。**family PASS = 「stage-2 (執行設計 pre-reg + user 最終承認) の起草権」のみ** — live 実装・shadow 化・lot・tier 変更は一切伴わない。PASS しても月利ミッションへの寄与は stage-2 の執行設計と摩擦実測を通過してから。
- **FAIL 時クローズ範囲 (事前凍結)**: 「**日次国債金利差アンカー (rolling 回帰帯、2y/10y テナー・W/Z_th 摂動を含む) × USD_JPY × 帯下 onset LONG × 5-63bd 固定ホライズン の全変種**」をクローズ。**user 水平線理論の機械核 v2 死亡** = 裁量スタックの残る未検証は執行層 (15m/1m) と exit 層のみ ([[../analyses/family-c-anchor-automation-2026-08-18|automation doc]] §4 の系譜完結)。**power caveat (クローズ文言に義務付け)**: FAIL は効果不在の証明ではない (MDE 90-160p、slow-MR 家系級 +3-12p への検出力 ≈ 5-10%)。クローズ根拠は『この設計での retail-viability 不成立』であり、「rate anchor は falsified」型引用は estimand 監査なしに禁止 (user 恒久指示 2026-08-05)。復活経路 = 新 anchor 構成 (例: OIS/先物 implied 政策 path、有償) + 新 family + 事前差分節 + 新敵対的検証のみ。
- **UNDERPOWERED (explore N_ev < 30)**: family PARK。イベント定義は保存、**Z_th 緩和・窓拡張による救済再試行は禁止**。再開 = OOS 窓が将来 explore 化できる split 再設計 (ppp 再挑戦経路 (b) 同型) の新 pre-reg のみ。
- **接触規律**: 測定は凍結コミット後のみ。pass-1 → コミット → pass-2。OOS 窓のシグナル×outcome には explore pass 中非接触 (2022+ の onset 日付は列挙後に窓 filter で破棄され、**出力・保存されない** — 敵対的検証 C5 で wording を実装に一致)。
- 動機記録 (R1 手続き): user 明示指示 (2026-08-19「進めて」— BT 実施の直接承認) + 改訂 WIP 原則 (能動枠 0 本解消) + データ駆動 (自動化パケットで材料完備)。感情的動機なし。
- registry: 凍結コミットと同時に `family-c-explore-verdict-deadline` (deadline_info、凍結 +10 日 = **2026-08-29**、到達経路 = 本セッションが two-pass を同日実行予定 + Tier-A cron 表示) を登録。

## §10 敵対的検証 条件 → 解決マッピング ([[family-c-adversarial-verification-2026-08-19]] が SSOT)

4 レンズ (統計/leakage、ban 隣接/cross-LOCK、ハーネス⇄spec 整合、完全性) 全て **GO-WITH-CONDITIONS**。blocking 10 条 (dedup 後) は全て凍結前に反映済み:

| 条件 | [B] | 解決 |
|---|---|---|
| C1 gate C null 反保守 (probe type-I 20-29%) | B | §5/§6 (年内 demean + episode-block sign-flip、p≤0.02 較正、旧 null は knife-edge (v) 診断へ降格) |
| C2 MDE σ 定義 (sd(\|X\|) は ~1.6x 過小) | B | §6/ハーネス (signed sd を aggregate 出力し MDE に使用、係数 2.485) |
| C3/C5 select_zth 未定義分岐 | B | §3 (混在 range 内ゼロ → UNDERPOWERED を完全列挙、test pin) |
| C4 rates-content 識別不能 | B | §5 (b≡0 ablation 対照 + Jaccard/net 比の解釈規則凍結 + pass-1 anchor 寄与 census) |
| C5/C6/L2-2 OOS 機械ロック未実装 | B | ハーネス (`oos` モード + 4 点 assert + seed 20260821 を凍結前実装、test pin) |
| L2-1 OOS 介入隣接の再判定汚染 | B | §5/§8 ④ (開示介入日 +21d 以内の onset を binding から除外する partition を事前凍結) |
| C1-critic 金利 staleness 5d が 2019-2021 を blackout (JGB GW 実測 gap 11d) | B | §2 (staleness 12 暦日へ + gap census on-record + test pin) |
| C2-critic --parquet 実体未照合 | B | §2/ハーネス (実ロード対象の sha256 を manifest と直接照合) |
| C3-critic min-sep 単位不一致 (valid-z index vs frame position) | B | §3/ハーネス (frame position に統一、void 跨ぎ test pin) |
| C4-critic placebo pool に z-void 日混入 | B | §6 診断 null (pool を valid-z 日に限定) |

non-blocking (全て反映/on-record): C6 entry-lag knife-edge 追加 (旧 log-fwd 変種は無歯で差替)、C8/C11 測定 N 再チェック + drop 件数報告、C9 staleness 計測基準 wording、C10 inf-z guard (RESID_STD_MIN)、C12 RNG 順序決定化 + version 記録、C13 gross/swap/net 分解報告、C14 ロック網羅 (イベント CSV/ハーネス自己 commit assert + manifest 行数 assert)、L2-3 E20 機構的 discharge、L2-4 ppp 原文引用、L2-5 BH「起動」定義、L2-6 parquet living-cache 条項、L2-7 anchor 寄与 census、C9-critic gate G false-kill 定量、C10-critic gate F 全疎 fallback、C13-critic yields 改定値 on-record、C5-conform §9 wording 一致、C8-conform knife-edge (v) 診断化の明文化、C11-critic host-pin on-record、runtime 実測 ~1 分 (問題なし)。

**コミット規律**: 本文書 + `tools/family_c_anchor_explore.py` + tests + data_freeze コピー + manifest + 検証 report + 台帳 #26 行 + registry 追記 + **changelog 行**を**同一コミットで凍結 (rule:R1 手続き)**。測定はコミット後開始。
