# Pre-registration DRAFT: weekend_gap 短ホライズン fade の OOS confirm (rule:R1 stage-1)

> **DRAFT — LOCK 未執行、レビュー待ち。OOS (2022-01-01 以降のデータ) 未接触。**
> 本文書はレビュー通過 + LOCK PR マージまで一切の拘束力を持たない。LOCK 前の条項変更はレビューコメント経由で可、LOCK 後は禁止。

**起案日**: 2026-07-24 (explore 完了同日 — OOS 接触ゼロの状態で設計固定するため)
**Status**: 📝 **DRAFT** (LOCK 後に 🔒 LOCKED へ更新)
**起点**: W0-3 explore `reports/weekend_gap_fill_multiday-2026-07-24.md` / [[hypothesis-catalog-2026-07-24]] 台帳 family **#3** (weekend_gap)
**承認系統**: user ミッション委任 (2026-07-08) + 探索最大化指示 (2026-07-24)。純研究 — **live パラメータ変更ゼロ**。PASS でも live 実装は別途 R1 手続き + user 最終承認 (§9)
**様式**: [[ws3-asymmetry-oos-prereg-2026-07-09]] 踏襲

---

## 1. 仮説 (H1 / H0)

**H1**: 週末ギャップ (|gap| ≥ 10× 通常 RT) の **短ホライズン (≤12h) toward-fill fade** は、explore 窓 (2014–2021) で観測された正の順方向移動 (EUR_USD 4h/12h Bonferroni 生存、pooled 4h weekend-block 生存) が選択バイアスではなく実在の非効率であり、**未接触の OOS 窓 (2022-01-01〜2026-06-30) でも再現する**。

**H0**: explore の生存は 20 検定 (4 ペア × 5 ホライズン) の事後選択 + 2014–2021 特有の news-weekend 構成 (Brexit / ギリシャ危機 / COVID) の産物であり、OOS では net toward-fill mean ≤ 0。

**explore verdict の要約 (凍結された前提)**:
- 「multiday fill」は**棄却済み** — 24h 以降は MAE が MFE より速く積み上がり、72h/120h の見かけの正値は Bonferroni 不生存 (drift/noise 裁定済み)
- Bonferroni (α = 0.05/20 = 0.0025) 生存: **EUR_USD 4h (p<1e-4) / EUR_USD 12h (p<1e-4)** のみ。pooled 4h weekend-block (p=0.0002) も生存 (pooled family m=5, α=0.01)
- GBP_USD は逆符号 (continuation、N=18、gap 大→fill 率低下の単調悪化)
- gap サイズ tercile のモノトニシティは**全ペアなし** — 「大ギャップほど埋まる」型の主張はしない (期待形状 = flat/hump、§7 検査で使用)

## 2. 凍結候補セット (explore から変更禁止、m = 2 arms)

| arm | 定義 | primary horizon | explore 根拠 (2014–2021) |
|---|---|---|---|
| **A** | **EUR_USD 単独** toward-fill fade | **4h AND 12h** (co-primary、両方必須) | N=57、net mean +12.3p (p<1e-4) @4h / +15.6p (p<1e-4) @12h — Bonferroni 唯一の per-pair 生存 |
| **B** | **pooled {EUR_USD, USD_JPY, AUD_USD}** toward-fill fade | **4h** (単一) | N=169 (GBP 除外後)、pooled net mean +8.3p (weekend-block p=0.0002) |

- **GBP_USD は両 arm から除外** — 除外理由: explore で逆符号 (12h 以降 net 負、tercile 単調 continuation)。**GBP_USD の OOS データは本 confirm でロードすらしない** — 将来「GBP continuation」を別 family として起こす場合の OOS を汚染しないため
- **qualify (凍結)**: |gap| ≥ **10× 通常セッション RT** — 閾値ピップ数も凍結: EUR_USD 20.0p / USD_JPY 21.4p / AUD_USD 25.0p。**2022+ の実測スプレッドで RT を再計算しない** (定義ドリフト = リーク経路)。AUD_USD の RT 2.5p は KB friction table 外の理論仮置きである旨を verdict に再掲
- **entry**: Monday open 直後バー — 基準価格 = Sunday/Monday open (Sun 21:00 UTC 以降の最初の 15m バーの Open、≤24h guard)、forward 窓はイベントバーを除外して開始 (explore と同一、lookahead なしを assert)
- **測定**: **exit-free** 固定ホライズン (BE/Trail/TP/SL なし — MEMORY `project_be_trail_inflates_python_bt_wr` 準拠)。全ホライズン {4,12,24,72,120}h を透明性のため出力するが、**判定は凍結 endpoint (arm A: 4h+12h、arm B: 4h) のみ**
- **swap**: 保有 ≤12h のため無視可 (multi-week 条項は非該当) — 1 行明記のみ

### 2.1 週末境界の定義 (レビュー指摘① への対応 — 凍結 + 正当化)

**凍結定義 (explore と同一)**: Friday close = Fri **21:00 UTC** 固定境界前の最終 15m バーの Close (≤6h guard) / Monday open = Sun **21:00 UTC** 以降の最初の 15m バーの Open (≤24h guard)。

**既知の歪み**: US DST 冬時間 (11月上旬〜3月中旬、年間 ~4.3 ヶ月) は実クローズが 22:00 UTC のため、冬の Friday close は実クローズの約 1h 前のバーを参照する。

**固定 21:00 UTC を維持する正当化 (a priori)**:
1. **estimand の同一性が最優先** — explore と confirm で定義を変えること自体が forking-paths/リーク経路。confirm は「explore が測ったものが OOS で再現するか」を問う
2. 歪みは explore 窓・OOS 窓の双方に同率で存在 (冬期比率ほぼ同一) — 系統差を生まない
3. 1h 早い close 参照は gap 測定に**ノイズを加える方向** (attenuation、null 側バイアス) であり、偽陽性側に働かない

**感度分析の宣言 (非ゲート、§7 検査③に組込)**: NY 17:00 anchor (`America/New_York` tz-aware、DST 追随) で境界を再定義した再計算を **verdict と同一の単一実行内**で行う。PASS arm の点推定符号が DST-aware 定義で反転した場合、当該 arm verdict を **FAIL (knife-edge)** に格下げする (事前規定)。

## 3. OOS 窓と接触規律

- **OOS 窓**: **2022-01-01〜2026-06-30** (explore 窓 2014–2021 と重複ゼロ。explore スクリプトは hard date filter + assert で 2022+ を一度もロードしていない)
- **一発判定**: OOS データへの接触は **verdict 実行の 1 回のみ**。primary・感度分析 (§2.1 DST / §7 閾値摂動)・診断 (§5) の**全てを単一スクリプト実行**で計算し、出力を `raw/bt-results/` に保存。結果閲覧後の再実行・再集計・条件変更は一切禁止
- **実行スクリプト (予約)**: `tools/weekend_gap_fill_oos_confirm.py` — `tools/weekend_gap_fill_explore.py` 派生、date filter を OOS 窓へ、§4 ゲートを実装。**LOCK 後に作成** (本 DRAFT 段階ではコード変更なし)。explore スクリプトは不変更
- **bootstrap**: one-sided、B=10,000、**seed 20260724 凍結** (explore と同一)。p の床は 1/(B+1) — 「p<1e-4」表記に統一 (横断規律メモ準拠)

### 3.1 データ品質の事前宣言 (レビュー指摘② への対応)

- **USD_JPY parquet のデータ穴**: explore 窓に 2019-09 / 2020-10 の穴が存在 (guard で skip 済み: no_friday_close 13 / no_sunday_open 5)。**confirm run では OOS 窓の完全性監査を verdict 計算前に同一実行内で行い、以下を verdict に明記する**: (a) ペア別 weekends measured vs 暦上の週末数 (期待 ~234)、(b) skip 内訳 (no_friday_close / no_sunday_open / incomplete)、(c) 1 週間超の欠損区間の一覧。arm B 対象ペアが OOS 週末の >10% を欠く場合は verdict に低下 N を明記するが、**ゲート自体は変更しない** (データ可用性は結果非依存のため)
- **MASSIVE feed の土曜行/不良プリント** (price_shock 監査 2026-07-24 で発見): 週末境界定義は構造上、土曜行を Friday close/Monday open のどちらにも選択しない (Fri 21:00〜Sun 21:00 の行は両 guard から除外) — 影響なしを設計で担保。ただし Sunday open の不良プリントが |gap| を偽装しうるため、**診断 (非ゲート)** として「qualifying イベントのうち初バー内で gap の 80% 超が即時逆転するもの」(spike-revert プリント徴候) の件数を verdict に記録
- **AUD_JPY 12y parquet 不在**のため AUD_USD 代替 (explore と同一構成)

## 4. 判定ゲート (実行前凍結 — arm ごとに全充足で PASS)

| # | ゲート | 内容 |
|---|---|---|
| (a) | **方向性** | net toward-fill mean > 0、one-sided event-block bootstrap。arm A = 4h と 12h の**両方** (arm p 値 = max(p_4h, p_12h) — intersection-union、保守的)。arm B = 4h、weekend-block bootstrap (同一週末クロスペア相関をブロック化) |
| (b) | **多重性** | **BH-FDR q=0.10、m=2 arms** (arm-level p で: p(1) ≤ 0.05 かつ p(2) ≤ 0.10 なら両通過) |
| (c) | **stressed friction net EV (主ゲート)** — レビュー指摘③ | **通常 RT の 3 倍**を stressed RT とし (EUR_USD 6.0p / USD_JPY 6.42p / AUD_USD 7.5p)、イベント毎に `net_i − 3×RT_pair(i)` を控除した**平均 > 0** (点推定)。日曜 open の実スプレッドは通常の数倍であり、理論 RT での EV 主張を禁止する趣旨。arm A は等価的に「gross mean > 6.0p」 |
| (d) | **headroom** | MFE p50 ≥ **10× stressed RT** (= 30× 通常 RT) を primary horizon で充足 (arm A は 4h/12h 両方、arm B は 4h)。⚠️ §10-1 のレビュー論点参照 — explore 水準では算術的に未達 |
| (e) | **N floor** | arm A: **N ≥ 25** / arm B: **N ≥ 60**。導出: explore 発生率 (EUR_USD 7.1 件/年、pooled 21.1 件/年) × OOS 4.49 年 = 期待 N ≈ 32 / 95。Poisson で P(N<25\|λ=32) ≈ 9% に設定 (repo 慣行 N≥30 だと期待値比 94% が床になり、イベント希少性だけで verdict が壊れる確率 ~35% — §10-2 のレビュー論点)。**floor 未達の arm は PASS/FAIL ではなく UNDERPOWERED** と裁定 |

### 4.1 効果量 shrinkage の事前予測 (凍結記録 — verdict との突合用)

explore 比 **50% 減衰**を事前予測として記録する (事後選択された点推定は OOS で縮む — 選択バイアスの機械的帰結):

| endpoint | explore gross mean | 50% shrinkage 予測 | stressed RT | 予測 stressed-net |
|---|---|---|---|---|
| arm A 4h | +12.3p | **+6.2p** | 6.0p | **+0.2p (限界的)** |
| arm A 12h | +15.6p | **+7.8p** | 6.0p | **+1.8p** |
| arm B 4h | +8.3p | **+4.2p** | 6.56p (N 加重) | **−2.4p (負)** |

**正直な事前記述**: 50% 減衰が実現した場合、arm B はゲート (c) を落とし、arm A 4h は限界的、arm A 12h のみ通過圏。つまり本 confirm の現実的な PASS 経路は「arm A の効果が explore 水準に近く保存されること」であり、それ以外は設計上 FAIL する。これは意図された保守性である (FP を作らないことが M1 への寄与)。

### 4.2 固定分岐 (verdict 後のアクション)

- **≥1 arm PASS (全ゲート)** → family #3 = PASS 候補。次段 = §9 の R1 手続き (即 live 禁止)
- **全 arm FAIL** → family #3 **CLOSE (再試行禁止)**。news-type 条件付き変種は「新 family + 新 explore (pre-2022 のみ) + 台帳新行」としてのみ許可 — 本 OOS の事後サブセット化による救済は禁止 (§6)
- **UNDERPOWERED (N floor 未達)** → family CLOSE (UNDERPOWERED)。再開はデータソース自体の更新時のみ

## 5. 診断出力 (非ゲート、単一実行内で同時計算)

- 全ペア×全ホライズン {4,12,24,72,120}h の MFE/MAE/net 分布 (explore 表と同形式)
- fill timing (t-half / t-full 分位、120h fill 率) — §7 検査①の入力
- OOS qualifying イベントの年次件数と |gap| p50/p90 — news-weekend 構成シフトの検出 (§6)
- tercile 別 net@24h — 期待形状 = flat/hump (explore 同型)。モノトニック化していたら構成シフトの徴候として記録
- spike-revert プリント件数 (§3.1)

## 6. 予想される反対仮説の事前宣言 — news-weekend 構成比の regime 差

**宣言**: explore の qualifying set は 2014–2021 特有の政治・危機週末 (Brexit 系、ギリシャ資本規制、COVID/oil、米仏選挙) に支配されている。OOS 窓 (2022+) の構成は異なる (ウクライナ侵攻、利上げサイクル、円介入週末、2024-08 キャリー巻き戻し)。**FAIL の場合の最有力の良性説明は「メカニズムの反証」ではなく「構成シフト (効果が news タイプ条件付き)」である**ことを事前に認める。

**ただし拘束**: この反対仮説は FAIL の**解釈**にのみ使用し、**OOS イベントの事後サブセット化 (news タイプ別の再集計・救済) は禁止**。条件付き仮説を追うなら §4.2 のとおり新 family として pre-2022 で explore からやり直す。§5 の年次件数・|gap| 分布診断は構成シフトの有無を記述するためのものであり、判定には使わない。

## 7. ナイフエッジ 3 点検査 (verdict 時必須 — T11 教訓 [[t11-ldn-morning-counter-usd-mr-12y-2026-07-06]] 準拠)

1. **メカニズム整合**: PASS arm の fill dynamics が explore と同型か — t-half 中央値 1–2h / full-fill 中央値 ~9–15h / 効果の構成が MFE 優位 (MAE 崩壊による見かけの正値でない) こと。tercile は flat/hump 型 (モノトニシティを新たに主張しない)
2. **擬似反復**: arm B は weekend-block bootstrap 内蔵 (同一週末のクロスペア相関)。同一週末の複数ペア qualifying 重複件数と、週末レベル net の lag-1 ρ を記録。arm A はイベント (週末) 非重複を assert (4h/12h は次週末と重ならない)
3. **境界・閾値ナイフエッジ**: (i) **DST 感度** — NY17:00 anchor 再計算 (§2.1) で PASS arm の点推定符号が維持されるか、(ii) **qualify 閾値摂動** — 8× / 12× RT (±20%) で点推定符号が維持されるか。**(i)(ii) いずれかで符号反転 → 当該 arm を FAIL (knife-edge) に格下げ** (事前規定)。全て単一実行内で計算

## 8. 執行と監視 (T5 教訓: 監視主体を必ず併設)

- **executor**: claude 直接実行 (exit-repair 方式)。レビュー (敵対的 1 本以上) → LOCK PR → verdict 実行の順
- **LOCK 期限**: **2026-07-31** (レビュー + LOCK PR マージ)。期限超過は session-start hook の未解決事項で追跡
- **verdict 期日**: LOCK から **7 日以内** (遅くとも 2026-08-07)。データはローカル parquet のみで完結するため外部依存なし
- **成果物**: verdict 追記 (本文書) + `raw/bt-results/weekend_gap_oos_confirm-<date>.json` + `reports/` + session log + [[hypothesis-catalog-2026-07-24]] 台帳 row #3 更新 (LOCK 時に「LOCKED」、verdict 時に結果追記)

## 9. 除外・注意 (LOCK 時点で拘束)

- **live パラメータを一切変更しない** (純研究 stage-1)。PASS ≠ live
- **PASS 後の R1 手続き (必須、省略不可)**:
  1. **日曜 open 実スプレッドの実測** — OANDA live で ≥8 週末分の Sunday open スプレッド実測 (stressed 3× は仮定であり実測で置換する。実測が 3× を超えるなら EV 再計算)
  2. **執行設計 pre-reg (stage-2 相当)** — entry mechanics (成行 vs 指値、リトライ)、サイジング、time-exit (4h/12h) の実装形、部分 fill 対応。exit-free 測定は EV 主張であって執行主張ではない
  3. **user 最終承認** — Rule 1 (Slow & Strict) の個別手続き
- **多重性台帳**: 本 confirm は [[hypothesis-catalog-2026-07-24]] **台帳 family #3** の OOS スロットを消費する (m=12 内)。arm 内 m=2 は §4(b) で処理
- **禁止**: verdict 後の endpoint/arm/閾値変更、OOS 再接触、GBP_USD ロード、news-type 事後サブセット化、explore 窓での閾値再チューニング

## 10. レビュー論点 (LOCK 前に解決必須 — DRAFT 固有セクション)

1. **ゲート (d) の算術的帰結**: 指示どおり「MFE p50 ≥ 10× stressed RT」を凍結すると、必要水準は EUR_USD で **60.0p** (arm B N 加重 65.6p)。explore の実測 MFE p50 は 4h 23.7p (3.95×) / 12h 34.6p (5.8×) / pooled 4h 26.4p (4.0×) — **explore 水準ですら全 arm 未達であり、shrinkage 前提では確定 FAIL に近い**。レビューで択一すること: (i) このまま維持 (= 本 confirm を実質 kill-test として運用する意図的選択と明記)、(ii) headroom は catalog 凍結条件どおり **10× 通常 RT** とし、stressed はゲート (c) の net EV 控除に一本化する (起案者推奨は (ii) — headroom は「動きの器」の検査、friction は EV の検査で役割が異なるため)。**どちらを選んでも LOCK 後は不変**
2. **N floor 25 vs repo 慣行 30** (arm A): §4(e) の Poisson 導出参照。30 に引き上げる場合、イベント希少性のみで UNDERPOWERED になる確率 ~35% を受容することを明記のこと
3. **arm A の co-primary (IUT max-p)**: 4h/12h の AND 要求は保守的。OR (どちらか一方) に緩める場合は arm 内多重性 m=2 の補正を追加する必要がある — 現行 AND 案は補正不要で単純
4. **DST 感度の格下げ規定 (§2.1/§7-3)**: 符号反転のみを格下げ条件とした (効果量の変動は許容)。より厳しく「stressed-net の符号維持」まで要求するかはレビュー判断

---

## 参照

- explore: `reports/weekend_gap_fill_multiday-2026-07-24.md` / `bt-results/weekend_gap_fill_multiday-2026-07-24.json` / `tools/weekend_gap_fill_explore.py` (seed 20260724)
- 台帳: [[hypothesis-catalog-2026-07-24]] (family #3、m=12、凍結探索プロトコル)
- 様式: [[ws3-asymmetry-oos-prereg-2026-07-09]] / ナイフエッジ検査: T11 教訓 / BE/Trail 教訓: MEMORY `project_be_trail_inflates_python_bt_wr`
