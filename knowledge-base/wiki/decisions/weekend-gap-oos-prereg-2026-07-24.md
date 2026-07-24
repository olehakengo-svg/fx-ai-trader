# 🔒 Pre-registration LOCK: weekend_gap 短ホライズン fade の OOS confirm (rule:R1 stage-1)

> **🔒 LOCKED 2026-07-24 — 以降の条項変更禁止。OOS (2022-01-01 以降のデータ) は verdict 実行まで未接触。**
> LOCK 手続き: 起案 (strategy-dev agent) → §10 全 4 論点の quant 裁定 (main セッション) → **敵対的レビュー 1 本 (verdict: ISSUES — リーク/設計破綻ゼロ、決定境界曖昧性 6 点)** → 必須 6 点 + 推奨 6 点を全て反映 → LOCK。arm B 凍結値の訂正計算 (GBP 除外プール、explore 窓のみ、seed 20260724) を含む。
> executor = claude / verdict 期日 = **2026-07-31** / 成果物は §8 のとおり。

**起案日**: 2026-07-24 (explore 完了同日 — OOS 接触ゼロの状態で設計固定するため)
**Status**: 🔒 **LOCKED** (2026-07-24、敵対的レビュー反映済み)
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
| **B** | **pooled {EUR_USD, USD_JPY, AUD_USD}** toward-fill fade | **4h** (単一) | N=169 / 117 weekends、net mean **+8.92p**、weekend-block p<1e-4、MFE p50 **24.6p** — **GBP 除外セットの直接再計算 (2026-07-24、explore 窓のみ、seed 20260724)**。※起案初版の「+8.3p (p=0.0002)」は GBP 込み 4 ペアプール (N=187) の誤帰属だった (敵対的レビュー指摘 #1 で訂正 — explore report の pooled 統計は GBP 込みであることに注意) |

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
3. 1h 早い close 参照は gap 測定に主としてノイズを加える (⚠️ 敵対的レビュー指摘: 金曜末尾リターンが週明けに平均回帰する場合は fade 側へ正のバイアスになり得るため純粋な attenuation ではない — この残余リスクは下記感度分析が担保)

**感度分析の宣言 (§7 検査③に組込)**: NY 17:00 anchor (`America/New_York` tz-aware、DST 追随) で境界を再定義した再計算を **verdict と同一の単一実行内**で行う。PASS arm の **gross net mean の符号 または stressed-net mean の符号**が DST-aware 定義で反転した場合、当該 arm verdict を **FAIL (knife-edge)** に格下げする (事前規定 — §7-3 の裁定 4 基準と同一。敵対的レビュー指摘 #5 で統一)。

## 3. OOS 窓と接触規律

- **OOS 窓**: **2022-01-01〜2026-06-30** (explore 窓 2014–2021 と重複ゼロ。explore スクリプトは hard date filter + assert で 2022+ を**分析フレームに一切含めていない** — parquet 読込自体は全行後フィルタのため「ロードしていない」ではなく「分析していない」が正確な表現。統計への接触はゼロ)
- **一発判定**: OOS データへの接触は **verdict 実行の 1 回のみ**。primary・感度分析 (§2.1 DST / §7 閾値摂動)・診断 (§5) の**全てを単一スクリプト実行**で計算し、出力を `raw/bt-results/` に保存。結果閲覧後の再実行・再集計・条件変更は一切禁止
- **実行スクリプト (予約)**: `tools/weekend_gap_fill_oos_confirm.py` — `tools/weekend_gap_fill_explore.py` 派生、date filter を OOS 窓へ、§4 ゲートを実装。**LOCK 後に作成** (本 DRAFT 段階ではコード変更なし)。explore スクリプトは不変更
- **dry-run 検証プロトコル (敵対的レビュー推奨の採用、凍結)**: confirm スクリプトは OOS 接触前に **explore 窓 (2014–2021) で dry-run** し、凍結 explore 統計 (arm A 4h +12.3p / 12h +15.6p、arm B 4h +8.92p、N=57/169) を丸め誤差内で再現することを必須とする。再現失敗 = スクリプトのバグであり、**この段階での修正・再実行は自由** (OOS 未接触のため)。dry-run 通過後に OOS を単一実行 — 以降の再実行は禁止
- **イベント適格性の継承**: explore 実装同様、120h 先の forward データを欠くイベントは全ホライズンから除外 (OOS 末端 2026-06 下旬の週末と 2021-12-31/2022-01-02 跨ぎ週末は explore/OOS どちらの窓にも入らない、影響 ~1-2 イベント — 敵対的レビュー指摘の明文化)
- **bootstrap**: one-sided、B=10,000、**seed 20260724 凍結** (explore と同一)。p の床は 1/(B+1) — 「p<1e-4」表記に統一 (横断規律メモ準拠)

### 3.1 データ品質の事前宣言 (レビュー指摘② への対応)

- **USD_JPY parquet のデータ穴**: explore 窓に 2019-09 / 2020-10 の穴が存在 (guard で skip 済み: no_friday_close 13 / no_sunday_open 5)。**confirm run では OOS 窓の完全性監査を verdict 計算前に同一実行内で行い、以下を verdict に明記する**: (a) ペア別 weekends measured vs 暦上の週末数 (期待 ~234)、(b) skip 内訳 (no_friday_close / no_sunday_open / incomplete)、(c) 1 週間超の欠損区間の一覧。arm B 対象ペアが OOS 週末の >10% を欠く場合は verdict に低下 N を明記するが、**ゲート自体は変更しない** (データ可用性は結果非依存のため)
- **MASSIVE feed の土曜行/不良プリント** (price_shock 監査 2026-07-24 で発見): 週末境界定義は構造上、土曜行を Friday close/Monday open のどちらにも選択しない (Fri 21:00〜Sun 21:00 の行は両 guard から除外) — 影響なしを設計で担保。ただし Sunday open の不良プリントは偽ギャップ→即時「フィル」で toward-fill net を**正方向に**膨らませる false-PASS 経路 (敵対的レビュー指摘 #6 で**凍結ゲート補助規則に昇格**): (i) **flag 規則 (凍結)** = qualifying イベントのうち、イベントバー (Sunday open 初バー、forward 窓から除外済み) の Close が Friday close から |gap| の 20% 以内まで即時回帰しているもの (= gap の 80% 超がイベントバー内で逆転 — spike-revert プリント徴候)。(ii) flag 件数と一覧を verdict に記録。(iii) **PASS arm に対しては flag イベント除外で全ゲート再計算し、gross または stressed-net の符号が反転した場合は当該 arm を FAIL (knife-edge) に格下げ** (§7-3 と同一基準)。本規則は explore + feed 構造情報 (price_shock 監査) のみから導出しており OOS 非接触
- **AUD_JPY 12y parquet 不在**のため AUD_USD 代替 (explore と同一構成)

## 4. 判定ゲート (実行前凍結 — arm ごとに全充足で PASS)

| # | ゲート | 内容 |
|---|---|---|
| (a) | **方向性** | net toward-fill mean > 0、one-sided event-block bootstrap。arm A = 4h と 12h の**両方** (arm p 値 = max(p_4h, p_12h) — intersection-union、保守的)。arm B = 4h、weekend-block bootstrap (同一週末クロスペア相関をブロック化) |
| (b) | **多重性** | **BH-FDR q=0.10、正確な step-up 決定表を凍結** (敵対的レビュー指摘 #3): m = **N floor を満たした (=検定された) arm 数**。arm p を昇順 p(1)≤p(2) とし、(i) p(2)≤0.10 → **両 arm 通過**、(ii) そうでなく p(1)≤0.05 → p(1) の arm のみ通過、(iii) それ以外 → 通過なし。片 arm が UNDERPOWERED の場合 m=1 で残 arm は α=0.10 単独判定 (N floor は凍結値のため executor 裁量なし) |
| (c) | **stressed friction net EV (主ゲート)** — レビュー指摘③ | **通常 RT の 3 倍**を stressed RT とし (EUR_USD 6.0p / USD_JPY 6.42p / AUD_USD 7.5p)、イベント毎に `net_i − 3×RT_pair(i)` を控除した**平均 > 0** (点推定)。日曜 open の実スプレッドは通常の数倍であり、理論 RT での EV 主張を禁止する趣旨。**arm A は 4h と 12h の両 endpoint で充足必須** (敵対的レビュー指摘 #2 — (a)(d) と同じ co-primary 構造に統一。等価的に「gross mean > 6.0p が両ホライズン」)。arm B は 4h、stressed RT = **6.56p 固定** (explore N 加重、OOS 構成での再加重禁止) |
| (d) | **headroom** | MFE p50 ≥ **10× 通常 RT** を primary horizon で充足 (arm A: 4h/12h 両方 ≥20.0p、arm B: 4h ≥ **21.9p 固定** — explore N 加重定数、OOS N での再加重禁止)。カタログ凍結入場条件 ([[hypothesis-catalog-2026-07-24]] 運用ルール) と同一。§10-1 裁定 (2026-07-24): 10× stressed 案は棄却 — headroom は「動きの器」の検査であり、friction stress は (c) の EV 検査に一本化 (二重計上を排除)。参考: explore 実測は arm A 4h 23.7p / 12h 34.6p / arm B 26.4p で全て充足水準 |
| (e) | **N floor** | arm A: **N ≥ 25** / arm B: **N ≥ 60**。導出: explore 発生率 (EUR_USD 7.1 件/年、pooled 21.1 件/年) × OOS 4.49 年 = 期待 N ≈ 32 / 95。Poisson で P(N<25\|λ=32) ≈ 9% に設定 (repo 慣行 N≥30 だと期待値比 94% が床になり、イベント希少性だけで verdict が壊れる確率 ~35% — §10-2 のレビュー論点)。**floor 未達の arm は PASS/FAIL ではなく UNDERPOWERED** と裁定 |

### 4.1 効果量 shrinkage の事前予測 (凍結記録 — verdict との突合用)

explore 比 **50% 減衰**を事前予測として記録する (事後選択された点推定は OOS で縮む — 選択バイアスの機械的帰結):

| endpoint | explore gross mean | 50% shrinkage 予測 | stressed RT | 予測 stressed-net |
|---|---|---|---|---|
| arm A 4h | +12.3p | **+6.2p** | 6.0p | **+0.2p (限界的)** |
| arm A 12h | +15.6p | **+7.8p** | 6.0p | **+1.8p** |
| arm B 4h | **+8.92p** (GBP除外・訂正値) | **+4.46p** | 6.56p (固定) | **−2.10p (負)** |

**正直な事前記述**: 50% 減衰が実現した場合、arm B はゲート (c) を落とし、arm A 4h は限界的、arm A 12h のみ通過圏。つまり本 confirm の現実的な PASS 経路は「arm A の効果が explore 水準に近く保存されること」であり、それ以外は設計上 FAIL する。これは意図された保守性である (FP を作らないことが M1 への寄与)。

### 4.2 固定分岐 (verdict 後のアクション)

**family verdict の優先順位規則 (敵対的レビュー指摘 #4 — 混合アウトカムを網羅、凍結)**:
1. **≥1 arm PASS (全ゲート)** → family #3 = PASS 候補 (他 arm の FAIL/UNDERPOWERED は当該 arm のクローズのみ)。次段 = §9 の R1 手続き (即 live 禁止)
2. PASS ゼロ かつ **≥1 arm が検定済み FAIL** → family #3 **永久 CLOSE (再試行禁止)** — 他 arm が UNDERPOWERED でも「検定された FAIL が 1 つでもあれば永久 CLOSE」(再開可能ラベルへの誘導を遮断)。news-type 条件付き変種は「新 family + 新 explore (pre-2022 のみ) + 台帳新行」としてのみ許可 — 本 OOS の事後サブセット化による救済は禁止 (§6)
3. **全 arm UNDERPOWERED** の場合のみ → family CLOSE (UNDERPOWERED)。再開はデータソース自体の更新時のみ

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
3. **境界・閾値ナイフエッジ**: (i) **DST 感度** — NY17:00 anchor 再計算 (§2.1)、(ii) **qualify 閾値摂動** — 8× / 12× RT (±20%)。維持要求は **gross net mean の符号 AND stressed-net mean (ゲート c と同一定義) の符号の両方** (§10-4 裁定 2026-07-24: 厳格側を採用 — T11 教訓「ナイフエッジ pass は kill」)。**(i)(ii) いずれかでどちらかの符号が反転 → 当該 arm を FAIL (knife-edge) に格下げ** (事前規定)。全て単一実行内で計算

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
- **多重性台帳**: 本 confirm は [[hypothesis-catalog-2026-07-24]] **台帳 family #3** の OOS スロットを消費する (m=12 内)。arm 内 m=2 は §4(b) で処理。**階層設計の明示宣言** (敵対的レビュー推奨): 多重性統制は 2 層 — family 内は本 pre-reg の BH-FDR (m=2)、family 間は台帳 (m=12) による**スロット制 + 全 verdict 追記式記録** (family 横断の p 値補正は行わない設計。families は仮説空間・データソースが異質で joint null が定義不能なため、代わりに「全 family の PASS/FAIL を隠さず記録し、PASS 率を帰無期待と突合できる状態を維持する」ことで統制する)
- **禁止**: verdict 後の endpoint/arm/閾値変更、OOS 再接触、GBP_USD ロード、news-type 事後サブセット化、explore 窓での閾値再チューニング

## 10. レビュー論点 — **全 4 点裁定済み (2026-07-24、main セッション quant 裁定。LOCK 後不変)**

1. **ゲート (d)**: 案 (ii) 採用 — headroom = **10× 通常 RT** (§4(d) に反映済み)。理由: headroom は「動きの器」の検査で friction stress は (c) の EV 検査 — 10× stressed (=30× 通常) は同一リスクの二重計上であり、カタログ凍結入場条件 (10× 通常 RT) とも不整合。explore 水準で全 arm 充足 = ゲートとして識別力を保ちつつ算術的不能を排除
2. **N floor**: **25/60 採択** (Poisson 導出 §4(e))。repo 慣行 N≥30 は昇格 (R1) 側の要件であり、本スクリーンの検定力床とは役割が異なる。UNDERPOWERED は family CLOSE (保守側) のため FP リスクは増えない
3. **arm A co-primary**: **AND (IUT max-p) 維持** — 補正不要で最も保守的
4. **DST/閾値格下げ**: **厳格側採用** — gross 符号 + stressed-net 符号の両方の維持を要求 (§7-3 に反映済み)。T11 教訓との整合

---

## 11. ✅ VERDICT (2026-07-24 — 単一 OOS 実行、§8 成果物として追記。§1–10 は不変)

**実行**: `tools/weekend_gap_fill_oos_confirm.py --oos` (2026-07-24)。dry-run 再現 (凍結 explore 統計 10/10 一致) + 敵対的監査 CLEAN 通過後の**単一実行** — 以降の再実行は禁止 (スクリプトが既存出力検知で拒否)。OOS 窓 2022-01-01〜2026-06-30、seed 20260724、B=10,000。GBP_USD は未ロード (assert 済み — 将来 family 用に清浄維持)。

### arm 結果 (frozen decision table の機械的適用)

| arm | N (floor) | gross mean | boot p | stressed-net | MFE p50 (要求) | (a) | (b) BH | (c) | (d) | (e) | knife-edge | **最終** |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **A** 4h | 46 (25) | +13.22p | p<1e-4 | +7.22p | 21.6p (20.0) | ✅ | ❌ | ✅ | ✅ | ✅ | flip 0/4 (記録) | **FAIL** |
| **A** 12h | 46 | +7.38p | **p=0.1189** | +1.38p | 30.3p (20.0) | ↑IUT | ↑ | ↑ | ↑ | ↑ | ↑ | ↑ |
| **B** 4h | 177 / 112wk (60) | **+15.60p** | **p<1e-4** (weekend-block) | **+9.04p** (−6.56 固定) | 24.8p (21.9 固定) | ✅ | ✅ | ✅ | ✅ | ✅ | **flip 0/4** | **PASS** |

- **ゲート (b) walk-through**: m=2 (両 arm N floor 充足)。arm A p = max(p<1e-4, 0.1189) = 0.1189 (IUT)。p 昇順 p(1)=B (p<1e-4)、p(2)=A (0.1189)。(i) p(2)≤0.10? NO → (ii) p(1)≤0.05? YES → **arm B のみ通過**。arm A は 12h endpoint の p 崩壊が IUT を支配して (b) 落ち — co-primary AND は凍結 (§10-3)、4h 単独への事後変更は §9 で禁止
- **knife-edge (§2.1/§3.1/§7-3、arm B に拘束適用)**: (i) DST NY17 anchor: N=197、gross +12.53/stressed +5.97 → flip なし。(ii) 8×RT: N=219、+14.71/+8.15 / 12×RT: N=140、+15.50/+8.94 → flip なし。(iii) spike-revert flag 2 件 (EUR_USD 2022-07-29 gap −24.6p / AUD_USD 2022-03-18 gap −64.7p) 除外再計算: N=175、+15.20/+8.64、p<1e-4、全ゲート再計算 PASS → flip なし。**4/4 維持 → 格下げなし**
- **§4.1 shrinkage 突合**: arm A 4h −7% (増)、arm A 12h **53% 減衰 (予測 50% どおり)**、arm B **−75% (増幅、予測は 50% 減衰で FAIL 圏だった)**。事前予測「PASS 経路は arm A」と逆の結果 — 効果の pair 構成が USD_JPY/AUD_USD 側へシフト (§6 構成シフト宣言の範疇、estimand は凍結どおり)
- **完全性監査 (§3.1)**: 全 3 ペア 232/234 週末 (missing 0.85% ≪ 10%)、skips = no_friday_close 1 / no_sunday_open 0 / incomplete_120h 1 (窓端、事前明文化どおり)、>1 週欠損区間なし。explore の USD_JPY 穴は OOS 窓に不存在
- **再掲義務 (§2)**: AUD_USD RT 2.5p は KB friction table 外の理論仮置き (stressed 7.5p / arm B 固定 6.56p に混入) — R1 手続き 1 の実測で置換必須。swap は保有 ≤12h で無視

### family verdict

**§4.2 優先順位規則 1 適用: ≥1 arm PASS → family #3 = PASS 候補**。arm A (EUR_USD 単独 co-primary) は本 verdict で当該 arm クローズ (救済・再集計禁止)。

### 固定分岐アクション (§4.2 → §9)

1. **即 live 禁止** — 純研究 stage-1 の PASS。live パラメータ変更ゼロを維持
2. **R1 手続き (省略不可、§9)**: (i) OANDA live 日曜 open 実スプレッド ≥8 週末実測 (3× 仮定の検証/置換 + EV 再計算) → (ii) 執行設計 pre-reg stage-2 (entry mechanics / サイジング / time-exit 実装 / 部分 fill) → (iii) user 最終承認
3. **成果物**: `knowledge-base/raw/bt-results/weekend_gap_oos_confirm-2026-07-24.json` (+ `bt-results/` 同名コピー) / `reports/weekend_gap_oos_confirm-2026-07-24.md` (全ゲート値・walk-through・knife-edge・診断・完全性監査) / [[hypothesis-catalog-2026-07-24]] 台帳 row #3 に verdict 追記要
4. **禁止の再確認**: OOS 再接触・再実行、endpoint/arm/閾値変更、news-type 事後サブセット化、GBP_USD ロード

## 参照

- explore: `reports/weekend_gap_fill_multiday-2026-07-24.md` / `bt-results/weekend_gap_fill_multiday-2026-07-24.json` / `tools/weekend_gap_fill_explore.py` (seed 20260724)
- 台帳: [[hypothesis-catalog-2026-07-24]] (family #3、m=12、凍結探索プロトコル)
- 様式: [[ws3-asymmetry-oos-prereg-2026-07-09]] / ナイフエッジ検査: T11 教訓 / BE/Trail 教訓: MEMORY `project_be_trail_inflates_python_bt_wr`
- verdict 実行: `tools/weekend_gap_fill_oos_confirm.py` / OOS JSON: `raw/bt-results/weekend_gap_oos_confirm-2026-07-24.json` / report: `reports/weekend_gap_oos_confirm-2026-07-24.md`
