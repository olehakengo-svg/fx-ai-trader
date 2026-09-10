# wave-6 #21 commodity_cross_range_mr explore pre-reg 敵対的検証 verdict (2026-08-05)

**検証体制**: 独立 5-lens subagent (ban-adjacency / DoF-freeze / statistics / data-friction / honesty-power) +
synthesizer 裁定。payload はファイル渡し: `wave6-cc-mr-explore-candidates-2026-08-05.json`。
一次ソース精読照合: `reports/commodity-cross-rt-g0-2026-08-03.md` / `knowledge-base/wiki/decisions/commodity-cross-g0-rt-freeze-2026-08-03.md` /
`knowledge-base/raw/bt-results/commodity_cross_rt-2026-08-03.json` (by_hour_p75 全表) / freeze commit `981ae119` (git show 実確認) /
`knowledge-base/wiki/research/ea-landscape-sweep-2026-07-31.md` §4.1 逐語 / `knowledge-base/wiki/syntheses/hypothesis-catalog-2026-07-24.md`
(#3/#5/#13/#14/#16/#17/#18/#19/#20/#21/#22 + L-d 行 + 運用ルール) / #19 pre-reg+report / ppp・qs・COT・E20 各 report /
`knowledge-base/raw/bt-results/e20/e20_carry_level.csv` (符号規約を三角恒等式 + 2 金利時代で三重検証) /
`knowledge-base/raw/bt-results/cc-g0-rt/2026-08-03.json`+`2026-08-04.json` / `data/cache/massive/{AUD_NZD,AUD_CAD,NZD_CAD}_1h.parquet`
**実測 (行数・first/last bar・gap census・spike scan、synthesizer が最終状態を再実測)** / audit.json (days_requested) /
`tools/fetch_massive_data.py` 実コード / `massive-vendor-gap-backfill-2026-07-29.md`。
**OOS 2022+ の forward return には一切接触していない。forward return / signal の新規計算はゼロ**
(gap census・spike scan・swap 符号検証は fwd 非接触の QA 算術のみ)。

**サマリ: 最終 verdict = GO-WITH-CONDITIONS (21 条、うち blocking 12 条) — ただし現時点は
data-blocked 状態にある。payload 自身の freeze 前提「first 1h bar ≤ 2014-01-01」が実測で 3/3 ペア不成立
(全ペア 2014-07-16 開始、synthesizer 再実測済み) であり、被覆修復 (条件 1) が完了するまで LOCK は物理的に禁止。
ban 同一性は不検出 (L-d/#3 は明示差分節付きで ADJACENT 裁定、E20 回避はソースコードで検証済み)。
ただし draft には PASS 方向バイアスが 4 系統 (markup 約 2 倍過小 / MDE 約 1.3-1.8 倍過小 / 週 block 反保守 /
金曜イベント無音削除) 実在し、全て条件で中和する。5 lens の verdict は GO-WITH-CONDITIONS ×4 +
DATA-BLOCKED(remediable) ×1 で、後者は前者に収斂する (修復経路が実在し family 起因でないため)。**

---

## 1. grounding facts 照合結果

### 1.1 検証済み (payload 正)

| # | claim | 照合 |
|---|---|---|
| 1 | G0 PASS 3/3: stressed_RT AUD_NZD 3.80 / AUD_CAD 3.70 / NZD_CAD 3.90p、全 ≤5.0p、freeze `981ae119` 測定前コミット | ✅ 5/5 lens が report 表・freeze doc §3・raw JSON・git show で一致確認。gate A の 10× 算術 (38.0/37.0/39.0p) も正確 |
| 2 | rollover 毒窓 p75 11.6-12.7p (21-22 UTC) | ✅ raw JSON 一致。hour-21 単独 p75 = 15.2-18.1p が真の毒時間。hour-23 は p50 2.7-2.9p / **p75 2.9-3.1p** (§1.2-9 参照) |
| 3 | §4.1 凍結制約の継承 (single-entry / pure price / M5-15m ban / explore-OOS split / event-block bootstrap / D1 曜日罠 / kill 規則) | ✅ ea-landscape-sweep §4.1 逐語一致。「3 ペア × 2 サイド Bonferroni」の記載も実在し、payload が申告した内部矛盾 (同 §4.1 に「primary 1 本へ凍結」) は本物 |
| 4 | negative prior 逐語 (slow-MR 死型 3 例家系 / RBA-RBNZ デシンク / 機関 RV デスク定番) | ✅ §4.1 line 58 + catalog #21 行と逐語一致。死型 3 例の実効果量も検証: ppp IC +0.113 p=0.129 / qs −0.237σ p=0.32 / rn +6.34p p=0.117 |
| 5 | explore/OOS 窓 2014-01-01..2021-12-31 / 2022-01-01..2026-06-30 単一接触 | ✅ catalog 凍結探索プロトコル逐語一致。デシンク配置 (2014-15→explore / 2022-24→OOS) も算術正 |
| 6 | variant A = postmortem 生存形状に一致、B = NON-TESTED 宣言 | ✅ edge-dev-postmortem §3 と §4.1 の spec に無音ドリフトなし。B 非測定宣言は #19 の「50-levels non-tested」前例に整合し DoF 最小 |
| 7 | pooled-primary 前例 (#19) と gate A-F 骨格の忠実継承 | ✅ #19 pre-reg §4 (two-pass) / §5 と同型。gate G のみ新規 |
| 8 | e20 csv = base−quote 規約 | ✅ 三重検証: ツールコード実文 + 三角恒等式 (AUD_JPY = AUD_USD + USD_JPY が 2013-01-02 に厳密成立) + 2 金利時代スポット (2013 RBA/Fed/BoC、2022-09)。AUD_USD/NZD_USD/USD_CAD 列は 2014-2021 に **NaN ゼロ**。csv は 2022-12-30 まで (explore 完全被覆、OOS は要拡張) |
| 9 | 0/0 financing 異常は 08-03 スナップショットに実在 | ✅ ただし stale (§1.2-6)。08-04 スナップショットで解消済み、しかも三角整合する markup 実測値を与える |
| 10 | ban 隣接差分節: #3 (15m 幾何) / #14 ppp (月次 5y-z) / E20 (rate=cost のみ) / session-mr-wave1 (BLOCKED_DATA、N=0 未測定) / #20 / #22 非干渉 | ✅ 全件一次ソース支持。E20 は line 149 で rates 配管残置が明文、weekend_gap stressed-net 前例と同型。#22 P-10 は shadow P&L の gate×outcome 限定で #21 (外部価格のみ) と非干渉。**ただし §1.2-8 の L-d 欠落を参照** |
| 11 | ledger slot: G0 は枠非消費、#20 PARK 非消費、#22 forward LOCK は E12 前例 (row 71「BH/wave スロット非消費」) で別枠 → **#21 explore = 1/3 active** | ✅ 3 lens 独立に同結論。payload の「0-1/3、verifier 確認」に回答: **1/3 で確定** |
| 12 | orchestrator honesty 4 項目 (頻度=oracle guess / 0/0 リスク / hard-mode 窓 / Bonferroni 矛盾) | ✅ 全て実在する問題の自己申告であり誠実。§9 参照 |
| 13 | MDE 算術 (1.645+0.842)×45/√150 = 9.14p | ✅ **算術は内部整合** — 誤りは入力 (sd=45p) 側 (§1.2-7) |

### 1.2 訂正 (payload 誤 — 重要度順)

1. **[重大 / 現に data-blocked] 被覆 assert が 3/3 ペアで不成立、かつ assert 自体が過小**。
   synthesizer 再実測 (2026-08-05): `AUD_NZD_1h` 80,824 行 / `AUD_CAD_1h` 75,236 行 / `NZD_CAD_1h` 73,885 行、
   **全ペア first bar = 2014-07-16 00:00 UTC** > 2014-01-01。原因は fetch が `--days 4400` で発行されたこと
   (audit.json `days_requested:4400` ≈ 2014-07-18)。さらに assert「≤2014-01-01」自体が設計と矛盾:
   SMA200 warmup で first signal ≈ +9.5 ヶ月後となり、2014-01-01 開始データでも 2014 年は約 75% 測定不能、
   実データ (2014-07-16) では first signal ≈ **2015-05** — gate F「6/8 年 + LOYO 8/8」は算術的に成立せず、
   **2014-15 デシンク敵対 regime の大半が無音削除される** (payload 自身の「honest hard-mode」宣言と矛盾する
   PASS 方向バイアス)。正しい assert = first bar ≤ **2013-03-01** (200 D1 + マージン)。
2. **[重大] 「same trading day 23:00 UTC」entry は自己矛盾で、金曜イベントを全滅させる**。
   金曜は 21/22:00 UTC で市場が閉まるため 23:00 UTC バーは構造的に存在しない (~99% Mon-Thu vs ~0% Fri、実測)。
   payload の「holiday なら skip」条項が **全 onset の約 1/5 を曜日選択バイアス付きで無音削除**する
   (金曜イベント = weekend-gap 露出組そのもの)。さらに DST 未規定: NY17:00 = 21:00 UTC (夏) / 22:00 UTC (冬)
   であり、**冬は毒窓が ~22:00-23:59 UTC へシフトし、固定 23:00 UTC entry は毒窓内に入る**。
   G0 の 60 営業日証跡 (5-8 月) は **100% 夏時間** — 冬の 23:00 UTC スプレッドは未測定。
3. **[重大] 「merge_never_shorten guard (PR #138)」claim は今回の backfill について虚偽**。
   fetch を実行した main checkout (branch `research/trendline-sweep-12y-pairscope-2026-07-13`) に PR #138 は
   **未着地** (`git merge-base --is-ancestor` 実測)。実行された `tools/fetch_massive_data.py` は素の
   `df.to_parquet` 上書きで、audit.json に `merged_with_existing` キーも無い。今回は fresh fetch で実害なしだが、
   payload が引用したガードは何も守っていない。
4. **[重大] 未記録のベンダー穴が explore 窓内に実在し、既知 2 窓より大きい** (gap census 実測、週末行除外):
   AUD_NZD **1225h ≈ 51 日 (2020-11-13 → 2021-01-03)** / NZD_CAD **1730h ≈ 72 日 (~2020-10-23 → 2021-01-03)** +
   286h ≈ 12 日 (2019-10-06 終端) / AUD_CAD は両窓 clean。既知の 2020 窓 (10-13..11-14) を **2021-01-03 まで**
   延長しないと `tools/massive_gap_backfill.py` の現行 WINDOWS では修復不能。
5. **[重大] D1-close 構築時間帯に集中する spike-print 汚染** (1h OHLC scan、レンジ >12× rolling-49 median):
   AUD_NZD **150 バー** (うち 125 が 20-22 UTC、例: 2024-08-06 21:00 の H/L 差 ≈ 1,150 偽 pips、explore 窓内にも
   2015/2019/2021 事例) / NZD_CAD 23 バー (Volume=2 の 21:00 UTC print、2024-01-01 休場バー含む) / AUD_CAD ほぼ clean。
   未除去のままでは (i) D1 close、(ii) **gate A の MFE p50 (headroom gate に PASS 方向バイアス)**、(iii) MFE/MAE 診断を直撃。
6. **[重大] gate D の markup 0.50%/yr は実測の約半分 — PASS 方向に最大のバイアス**。
   `cc-g0-rt/2026-08-04.json` (payload が stale のまま「anomaly unresolved」と記載した翌日分) は非ゼロ rates を持ち、
   三角恒等が厳密に閉じる (implied 差 AUD−NZD +1.835% / NZD−CAD +0.31% / AUD−CAD +2.145% = 和が一致)。
   implied markup m = −(long+short)/2 ≈ **1.08-1.09%/yr per side (3 ペア全て)** — payload の 0.50%±50% (上限 0.75%)
   の外。fade-SHORT 脚 (AUD_NZD/AUD_CAD) は ≈2.9-3.2%/yr ≈ **5-6p/5td 保有** で、宣伝 MDE (9.1p) と同オーダー。
   また NZD_CAD は**両サイド負 carry** があり得る → pooled「swap_net」スカラーは設計として誤り (per-event × per-side 必須)。
   0/0 スナップショット (08-03) は ingest artifact = **MISSING であってゼロコストの証拠ではない**。
7. **[重大] MDE 9.1p は 1.3-1.8 倍過小 + 推論構造が反保守**。
   (i) sd=45p は無根拠: 実測 robust 日次 vol (median |ΔC|/0.6745) ≈ 34.5/33.2/38.5p → σ_5d ≈ **77/74/86p**
   (statistics lens の理論レンジ 42-70p とも整合、45p は楽観 25 percentile 圏)。正直 MDE (N=150) ≈ **12-17p**。
   (ii) 5 営業日 = 7 暦日なので **全イベントの return 窓が ISO 週境界を必ず跨ぐ** — 週 block sign-flip は
   隣接週の重複 return を独立扱いし p が反保守 (#19 の 3d では成立した近似が 5d では構造的に破綻)。
   (iii) log(AUD_CAD) ≡ log(AUD_NZD) + log(NZD_CAD) の三角恒等で 3 ペアは実質 **2 自由度** — 名目 pooled N=150 の
   実効 block 数は ~60-90 に収縮。floor と MDE は block 単位で言い直す必要がある。
   (iv) onset 頻度 6-15/pair/yr も上振れ気味 (z は非単位分散、excursion は複数週持続) — N<120 は現実的シナリオ。
8. **[中 / 重大な欠落] 最近接の killed neighbor が差分節に無い**: wave-4 **L-d `d1_regression_channel_reversion`**
   (2026-07-31 triage KILL、catalog line 115「再入場経路なし (同構造)」) は D1 slow-MR ±2σ band fade であり、
   ea-sweep GO の 5 日前に殺されている。payload の ban_adjacency_diff_clauses は 06-25 の #3 (15m) しか挙げていない。
   L-d 裁定は「回帰±2σ/swing 平行以外 + IC-first + 明示差分節」を開放しており、#21-A (SMA anchor、回帰勾配なし・
   swing fit なし) は幾何 carve-out 内 — だが 2 義務 (IC-first + 差分節) は **L-d に対して**果たされねばならない。§3 で裁定。
9. **[中] 引用誤り 2 件**: (i)「entry を 21:00-22:59 UTC 外に凍結」の出典は G0 freeze doc §4 ではなく
   **catalog #21 行** (freeze doc §4 は「hourly map を entry 時刻特定に使う」としか言っていない)。
   (ii)「23:00 UTC 以降 2.7-2.9p に正常化」は **p50** の数字 (p75 は 2.9/3.0/3.1p — NZD_CAD は帯の外)。実質影響 ≤0.2p だが freeze doc は実数を引くこと。
10. **[中] §4.1 の選択的継承**: frozen_constraints_inherited は §4.1 共通行から「3 ペア × 2 サイド Bonferroni」
    のみを落として gate C の「arbitrate」に移した。honesty 項で開示済みなので隠蔽ではないが、
    省略方向が pro-proceed (p<0.05 vs p<0.0083) である事実は記録する。裁定は §5.1。
11. **[小] gate D の NZD_CAD 導出式が欠落 + USD_CAD 符号が「?」のまま**。解決 (三重検証済み):
    **AUD_NZD = AUD_USD − NZD_USD / AUD_CAD = AUD_USD + USD_CAD / NZD_CAD = NZD_USD + USD_CAD** (全列 base−quote)。
12. **[小] データ品質の非対称が未申告**: NZD_CAD completeness 97.86% / 799 gaps vs AUD_NZD 100% / 546 (audit.json)。
13. **[小] 出典 doc 側の erratum**: §4.1 line 55「AUD_NZD は 2002 年以降 0.615-0.99」は NZD/AUD の逆数レンジ
    (実際は ~1.00-1.35)。freeze doc が引用する際に一行訂正。

**lens 間の事実コンフリクト 1 件と解決**: honesty-power lens は「NZD_CAD fetch 未着地 (2025-04-08.. のまま)」と報告、
data-friction lens は「3/3 着地済み first bar 2014-07-16」と報告。**synthesizer が最終状態を再実測し後者で確定**
(観測時刻差: backfill が data-friction lens の poll 窓内に完了した)。いずれにせよ 2014-07-16 は訂正後 assert
(≤2013-03-01) を満たさないため verdict への影響はない。

---

## 2. verdict サマリ

### 2.1 lens 別 verdict

| lens | verdict | 主根拠 |
|---|---|---|
| ban-adjacency | GO-WITH-CONDITIONS | ban 同一性なし。L-d 欠落 + markup 2 倍過小が主指摘 |
| DoF-freeze | GO-WITH-CONDITIONS | 23:00 entry の自己矛盾 + 被覆 assert 既落ち + 未凍結 DoF ~17 |
| statistics | GO-WITH-CONDITIONS | pooled 設計は正しいが週 block 反保守 + MDE 過小 |
| data-friction | DATA-BLOCKED (remediable) → GO-WITH-CONDITIONS | 被覆・穴・spike・markup の 4 修復が先行必須 |
| honesty-power | GO-WITH-CONDITIONS | 憲章適合・slot 適法・数値正確、だが PASS 偏向 4 系統要修復 |

### 2.2 争点別裁定 (詳細は §3-§6)

| 争点 | 裁定 | 節 |
|---|---|---|
| Q1 pooled vs 6-cell Bonferroni | **pooled m=1 採択、§4.1 は on-record 修正** (6-cell は per-cell MDE 29-39p の非テスト) + gate G を binding 化 + claim 範囲を family-pooled に恒久限定 | §5.1 |
| Q2 entry proxy | **NY アンカー: 19:00 America/New_York バー close** (= 夏 23:00 / 冬 00:00 UTC)。固定 23:00 UTC は DST で冬に毒窓内 → catalog 字面からの on-record 偏差として記録。D1 close-to-close は診断 | §4.1 |
| Q3 swap 符号/式 | **base−quote 検証済み、3 式凍結** + markup 実測 ~1.1%/yr に再較正 + per-event per-side accrual + 0/0=MISSING | §6.3 |
| Q4 floor/MDE | **正直 MDE 12-17p を公表**、floor = events ≥120 **かつ** blocks ≥50、sd=45p/9.1p は破棄。honesty-power の「MDE>12.6p なら UNDERPOWERED 天井」は**棄却** (§5.3 で理由) | §5.3 |
| Q5 gate G binding 形 | **binding**: per-pair 符号 ≥2/3 + サイド kill = サイド平均<0 ∧ 片側 block-perm p<0.10 (サイド N<30 は発火不能・flag) | §5.4 |
| Q6 データ QA 最低線 | 被覆修復 / 穴修復 / despike / bars/week・曜日・三角残差 assert / sha256 pin / P-10 hygiene / TV 照合順序 | §6.1-6.2 |
| Q7 hold-collision | **skip 禁止 — 全 onset 測定が primary** (skip は事前イベント条件付けでクラスタ stress を間引く PASS 方向バイアス)。skip 版は診断のみ | §4.2 |
| block 構造 (lens 対立) | **固定 2-ISO-週 block・全ペア pool が primary**、1 週版は診断 (#19 からの deviation-strengthening) | §5.2 |
| 被覆修復経路 (lens 対立) | **OANDA H1 backfill (07-29 前例) を主経路**、PR #138 入り checkout から実行。fallback = 測定前の窓再宣言 | §6.1 |
| 最終 | **GO-WITH-CONDITIONS (21 条 / blocking 12 条) — 被覆修復完了まで LOCK 禁止 (現状 data-blocked)** | §10 |

---

## 3. ban 隣接裁定 (on-record)

### 3.1 L-d「着せ替え」争点 — 両論併記の上で ADJACENT 裁定

**FOR re-skin (kill 側)**: 両 estimand とも「±2σ band fade」。レンジ相場ペアでは regression-200 センターラインは
SMA200 に退化する — #21-A はまさに測定される場所 (構造的レンジの commodity cross) で L-d の幾何に収束する。
L-d には「再入場経路なし (同構造)」が記録済み。

**AGAINST (survive 側)**: (i) 06-25 の null は証拠スコープ付き (6 majors × 15m × 50-bar lookback、
自己限定「この特徴量セット・チャネル定義では」、IC≈0) — commodity cross ゼロ・D1 測定ゼロ。
(ii) L-d は **triage kill であって測定 kill ではない** (slot 逼迫 + prior が理由、「power は足りる — kill 理由ではない」
が記録済み)。L-d 裁定自身が 06-25 を ADJACENT-not-identity とし、「回帰±2σ/swing 平行以外」を
IC-first + 差分節付きで開放した。(iii) #21 の load-bearing 仮説は**ペア構造** (commodity-bloc 政策連動・
外部 4 ベンダー収斂・共和分文献) であってチャート幾何ではない — 「ページのライン」系仮説ではない。

**裁定: ADJACENT であって re-skin ではない — この estimand に測定済み null は存在しない。**
ただし条件 18-20 (L-d 差分節・IC-first 字義履行・FAIL 時クローズ範囲の事前凍結) の履行を条件とし、
どれかが freeze doc から落ちた瞬間この裁定は失効する。

### 3.2 その他の隣接照合

- **E20**: ban 範囲は rate-SIGNAL 2 凍結 variant + carry 同型。v1 シグナルは純価格、rates は gate D の
  減算コストのみ (outcome join 後)。`tools/e20_rates_ingest.py` の符号規約もソースで監査済み。
  weekend_gap stressed-net 前例と同型 = **非違反**。ファイアウォール条項を条件 17 で凍結。
- **#14 ppp**: ban 字面 (5y rolling z × 月次 × 21-63bd) の外。family-resemblance は negative prior として
  正しく継承されており ban 違反ではない。
- **session-mr-cross-wave1**: 全 10 cell BLOCKED_DATA / N=0 — verdict 不在、supersession は適法 (別 estimand)。
- **bb_rsi_reversion (T10 KILL)**: intraday BB+RSI で scope 別 — 一行注記を freeze doc に (条件 18)。
- **#22 / #20 / E7 / E1 / E12 / MoF**: 非干渉確認済み (#21 は shadow P&L 非接触・外部価格のみ)。
- **slot**: #21 explore = **1/3 active** で確定 (§1.1-11)。

---

## 4. estimand / 執行裁定

### 4.1 Q2 — entry proxy (lens 対立の裁定)

lens の分布: statistics + honesty-power =「23:00 entry 維持 (遅延を価格に織り込む方が誠実)」/
data-friction =「NY アンカー 19:00 NY (DST 安全形)」/ DoF-freeze =「D1 close-to-close を primary に格上げ」。

**裁定: primary entry = 19:00 America/New_York バー close (= NY17:00 close の 2h 後、夏 23:00 UTC / 冬 00:00 UTC)。**
理由: (i) statistics lens の原則 (「執行遅延を close-to-close + 摩擦補正で隠すのは誤り — entry 価格に織り込む」) を
採り、DoF-freeze の close-to-close primary 案は**棄却** (摩擦誠実性で劣後)。(ii) ただし固定 23:00 UTC は
冬に毒窓 (~22:00-23:59 UTC へシフト) 内に入る (§1.2-2) ため、data-friction の NY アンカー形で DST 問題を解消する。
(iii) catalog #21 行の字面「執行 23:00 UTC 凍結」に対しては、G0 証跡が夏時間 100% であり「23:00 UTC」の実体は
「NY close + 2h」だったと解して **on-record の偏差 + 根拠**として freeze doc に記録する (G0 freeze doc §1 の
「原文からの明示的偏差」パターン)。(iv) D1 close-to-close は診断、固定 23:00 UTC (非金曜) は knife-edge に残す。
(v) 冬窓の 23:00 UTC スプレッドは未測定である旨を honesty 条項として明記し、将来の live 化 (本測定の外) は
冬スプレッド再測定を要すると凍結する。

**金曜規則 (blocking)**: 金曜 D1 close のイベントは entry = **次営業日 19:00 NY バー** (遅延日数を報告)。
skip 案も許容可能だが、weekend-gap 露出組を系統的に落とす選択バイアスと N ~−20% を避けるため繰越を主とする。
「holiday なら skip」の無音条項は**却下** — 金曜削除を holiday と誤ラベルする欠陥だった。

### 4.2 Q7 — hold-collision (全 lens 一致)

**skip 禁止。全 onset イベントを測定する。** skip-during-hold は事前イベントの経路に inclusion を条件付け、
クラスタ stress 期 (MR が死ぬ場所そのもの — デシンク prior) を非対称に間引く PASS 方向バイアス。
これは book ではなく測定 — 依存構造の処理は block permutation (§5.2) と gate E の仕事であって標本削除ではない。
skip 版 (live-feasibility) は診断のみ。one-event-per-excursion は維持。overlap share (同ペア 5d 窓内複発率) と
同週 cross-pair co-fire share を報告義務化。

onset 端点規則も凍結 (条件 10): 系列先頭で z(t−1) 未定義 → onset 非成立 (件数報告) /
excursion 内の符号反転 (+2→−2 が |z|<2 を経ない) は新イベントを作らない (件数報告、期待 ≈0) /
再エントリは |z|<2.0 のバー通過後のみ / std60 < 1e-6 はバー void。

---

## 5. 統計裁定

### 5.1 Q1 — pooled primary m=1 採択、6-cell Bonferroni は on-record 棄却 (全 lens 一致)

power 算術 (statistics lens、synthesizer 検算一致): N=150 均等割で per-cell N=25、α'=0.05/6 → z=2.394 →
per-cell MDE = 3.236×sd/5 = **29.1p (sd45) / 38.8p (sd60)** — slow-MR 家系の実測効果 (+2.9〜+11.9p) の 3-6 倍 =
**保証された UNDERPOWERED 非テスト**。さらに 6 cell は三角恒等 + 共有週で非独立であり /6 自体が誤較正。
§4.1 の Bonferroni 行は同 §内の「pre-reg 起案時に primary 1 本へ凍結」と矛盾する pre-prereg スケッチと認定。

**必須の補償 (これが無ければ本裁定は失効)**: (i) gate G を binding 化 (§5.4)。(ii) claim 範囲 =
family-pooled のみ — per-pair / per-side の claim は結果如何によらず恒久禁止。(iii) verdict 前に他の wave-6
explore family が起動した場合は BH q=0.10 で分母合流 (vix #7 knife-edge の死因の再演防止)。
(iv) freeze doc は §4.1 の該当文言を逐語引用し、本偏差 + 根拠を記録する。

### 5.2 block 構造 — 週 block は棄却、固定 2-ISO-週 block が primary (lens 対立の裁定)

DoF-freeze lens は「ISO 週 primary + fortnight 診断」、statistics + honesty-power は「2 週 or overlap-merge を
binding」。**裁定: statistics 側を採択。** 理由は程度問題ではなく構造問題だから — 5 営業日 = 7 暦日により
**全**イベントの return 窓が ISO 週境界を跨ぐ (#19 の 3d 地平では成立した近似が 5d では常に破綻)。
凍結形: **固定 2-ISO-週 block (週 [2k−1, 2k])、全ペア pool、block 単位 sign-flip** (三角依存のため per-pair
block は禁止 — 1 flip は当該 block の全ペア全イベントに同時適用)。1-ISO-週版 + overlap-merge 版は診断併記
(選択不使用)。#19 前例からの deviation-**strengthening** として記録。

permutation 仕様の完全凍結 (条件 14): numpy `default_rng(20260805)`、B=10,000、p=(1+#{perm≥obs})/(1+B)、
block 割当 = entry バーの日付、gate G サブテストは同一 block 構造 + 派生 seed 20260806(L)/20260807(S)、
knife-edge は seed 再利用。gate E の分母凍結: share = max_w |S_w| / Σ_w |S_w| (S_w = block w の符号付き net5d 和 —
pooled net を分母にすると 0 近傍で発散する)。

### 5.3 Q4 — power/MDE の正直化と「UNDERPOWERED 天井」の棄却 (lens 対立の裁定)

正直な数字 (§1.2-7): 実測 robust σ_5d ≈ 74-86p → **MDE(N=150) ≈ 12-17p**。宣伝の 9.1p は破棄。
凍結: gate B = **events ≥ 120 かつ blocks (§5.2 定義) ≥ 50**、どちらか未達 → UNDERPOWERED verdict
(閾値いじり禁止は payload 宣言どおり維持)。pass-1 staging で無条件 5d 分散 (despike 後、event×outcome 非接触) を
実測し MDE を再計算、freeze doc に MDE 表 (sd {45,60,80} × N {120,150} × blocks {50,90}) を公表する。

**honesty-power lens の条件「再計算 MDE > 2× 家系最大効果 (+6.3p) なら verdict 天井 = UNDERPOWERED」は棄却する。**
理由: 正直 MDE は 12-17p でほぼ確実にこの天井 (12.6p) を超える — 採用すれば観測効果の大きさに関係なく PASS が
不可能になり、explore を非テスト化する (6-cell Bonferroni を棄却したのと同一の論理)。低 power の検定は
「小さい真の効果を高確率で見逃す」だけで無効ではなく、PASS には観測 pooled 効果が ~12p+ であることが必要 —
それは gate A (headroom 10×RT ≈ 38p) と gate D (摩擦+swap 控除後正) が要求する retail 生存サイズと整合する。
freeze doc には statistics lens の文言で明記する: 「家系前例サイズ (+3-6p) の効果は構造的に FAIL する —
これは意図された retail-viability filter であって 9.1p での 80% power 推論ではない」。

### 5.4 Q5 — gate G binding 形 (閾値の lens 対立裁定)

**binding 採択** (全 lens 一致)。形: (i) per-pair pooled mean 符号 ≥2/3 正 = binding。
(ii) サイド kill = 片サイド pooled mean fade net5d < 0 **かつ** 片側 block-perm p(against) < **0.10** → FAIL。
閾値は ban-adjacency lens の 0.05 ではなく **0.10** を採択 (3 lens 多数 + kill 発火しやすい側 = 反 PASS バイアス側)。
(iii) サイド N < 30 では binding 形は発火不能とし、低サイド N を report に flag (単なる負ノイズサイドは
PASS に「one-sided effect」注記を付け、OOS pre-reg に逐語継承)。根拠: #16 gate iv (binding、実際に発火) +
#5 incoherence 前例。「両サイド個別有意」形は裏口 Bonferroni であり棄却。

### 5.5 gate F — 維持 (被覆修復に条件付き)

statistics lens の検算: pooled ~19 events/yr で真の +8p エッジでも P(≥6/8) ≈ **0.47** — gate F 単独で実エッジを
~半分の確率で殺す。これは推論としては未較正だが **OOS-regime filter としては正しく較正**されている
(OOS 2022-24 はデシンク主体 — 2014-15 デシンクで死ぬエッジは単一 OOS touch を浪費するだけ)。
**binding 維持** (#19 は 5/8 で死んだ — 今緩めるのは gate-shopping)。凍結: (i) 被覆修復 option (a) 成立なら
6/8 + LOYO 8/8 のまま。option (b) なら ≥5/6 + LOYO 6/6 に測定前リスケール。(ii) ~50% false-kill 率を freeze doc に
事前記録し、C-PASS/F-FAIL 分岐は「regime-inconsistent の FAIL close」で再審禁止。(iii) warmup 規則:
バー適格 = SMA200/std60/z(t)/z(t−1) 全計算可能。per-pair first-eligible 日を freeze doc に記録し、
gate F の分母は仮定でなく導出。

---

## 6. データ・摩擦裁定

### 6.1 被覆修復 (Q6 の第一項、lens 対立の裁定)

data-friction lens は「`--days ≥4950` の MASSIVE 再フェッチで足りる可能性 (4400 は発行パラメータの artifact)」、
honesty-power + statistics + MEMORY は「MASSIVE 深度 ≈ 12y = 2014 が壁」。**裁定: 主経路 = OANDA H1 backfill
(2026-07-29 の確立済み手法) で 2013-03-01..2014-07-16 を補完** — 2013-03 は今日から 13.4y であり MASSIVE 12y 壁の
外にある公算が高い。MASSIVE 明示 start 指定の再フェッチを先に試すのは安価で可 (成功すれば同等)。
いずれの経路でも: (i) **PR #138 (merge_never_shorten) 入りの checkout から実行** (§1.2-3 — 今回の fetch には
ガードが無かった)、splice-QA (重複 ≥20 日で一致検証)、audit key 確認。(ii) 完了 assert = per pair first 1h bar ≤
2013-03-01。(iii) 不能な場合の fallback = **測定前の窓再宣言** explore = [first-signal 日, 2021-12-31] +
gate F/LOYO リスケール + 「2014-15 デシンク窓の一部が測定不能」の honesty 条項逐語。第三の道
(「あるもので走る」) は W3-2 前例で禁止。**本条件が完了するまで LOCK 禁止 = 現状 data-blocked。**

### 6.2 Q6 — QA 最低線 (blocking)

1. **穴修復**: `tools/massive_gap_backfill.py` WINDOWS を 3 クロス向けに 2019-09-14..2019-10-06 と
   **2020-10-13..2021-01-03** (§1.2-4 の実測に合わせ既知窓を延長) に拡張して OANDA mid で修復 → 再 census で
   「2013-03..2021-12 に週内 gap > 72h なし」を assert。修復不能なら凍結 gap-tolerance: onset は z(t−1)/z(t) が
   >5 営業日 gap を跨ぐ場合 void / SMA200/std60 は実 close ≥190/57 本要求 / 穴 census を freeze doc に公表。
2. **despike 規則 (gate A が PASS 方向に汚染されるため測定前必須)**: (H−L) > 8× rolling-49 median の 1h バーを flag、
   flag バーの H/L は MFE/MAE 極値から除外、D1 close を供給する flag バーは OANDA mid で照合・置換 (来歴ログ)。
   flag 件数 per pair/year を freeze doc に公表 (現行 census: AUD_NZD 150 / NZD_CAD 23 / AUD_CAD ~2 @12×)。
3. **D1 再構築規約の再宣言 (参照でなく本文)**: 1h ラベル語義 (open-time/close-time) を既知セッション境界で
   freeze 前に検証・記録 / trading day T = close-time ∈ (NY17:00_{T−1}, NY17:00_T]、境界は **America/New_York**
   zoneinfo (固定 21/22:00 UTC 禁止) / D1 close = 境界一致バー、なければ ≤境界の最終バー + `degraded_close` flag
   (件数報告、最終バーが境界の 3h 超前なら void) / D1 H/L = 構成バーの max/min / 週末ラベル除外 /
   assert: bars/week median = 5、曜日分布 ≈ 一様 (#18 罠検出器)、D1 構成バー数 ∈ [18,24] (祝日外)。
4. **横断 assert**: タイムスタンプ単調・重複ゼロ / 三角残差 |log AUD_CAD − log AUD_NZD − log NZD_CAD| 日次 p99 が
   スプレッド許容内 (データ整合 + block 設計が仮定する依存構造の実測 pin を兼ねる)。
5. **sha256 pin**: 修復後 3 parquets + audit.json + `e20_carry_level.csv` + cc-g0-rt スナップショット + ハーネス +
   統計ツールを freeze commit に pin (MASSIVE drift 実測 −25 行の教訓)。測定は freeze commit 後のみ。
   フル parquet で実行 (worktree 部分 parquet 罠)。
6. **P-10 hygiene**: ハーネスは `Volume`/`vwap` 列を読まない (E12 volume×価格 joint 計算 ban、2027-02-05 まで) —
   コード内 assert。
7. **TV 照合の順序規律**: pass-1 = イベント件数スポットチェック (≥1 ペア、±10%) のみ可。pooled 符号の TV 照合は
   **pass-2 解錠後のみ** — gate A 前の TV 符号 peek は forward look であり禁止。

### 6.3 Q3 — swap / gate D (blocking)

- **式凍結 (三重検証済み)**: `d_AUD_NZD = col_AUD_USD − col_NZD_USD` / `d_AUD_CAD = col_AUD_USD + col_USD_CAD` /
  `d_NZD_CAD = col_NZD_USD + col_USD_CAD` (全列 base−quote、%/yr)。
  `swap_pips = (dir × d(t_entry) − m)/100 × (H_cal/365) × S(t_entry)/1e-4` — dir=+1 long/−1 short、
  H_cal = 実 entry→exit 暦日数 (per-event)、S = entry 価格、負 = コスト。
- **pooled「swap_net」スカラーは廃止 — per-event × per-side accrual に置換** (NZD_CAD は両サイド負 carry があり得る)。
- **markup 再較正 (最大の PASS バイアス修復)**: m = −(longRate+shortRate)/2 を **per pair ≥10 本の非異常日次
  cc-g0-rt スナップショット**から較正 (現行実測 ≈1.08-1.09%/yr — draft の 0.50% は実測の半分以下で棄却)、
  感度 ±50% [≈0.55, 1.65]、**gate D は感度の adverse 端で PASS を要求**。
- **0/0 規則**: longRate=shortRate=0 のスナップショットは **MISSING (棄却)** — ゼロコストの証拠として使用禁止。
  0/0 が >20% の日で再発するペアは m=1.65% を適用。per pair-side で
  worse-of (e20 導出 + 較正 markup, スナップショット実測 implied cost) を採る。
- **E20 ファイアウォール**: rates の使用は outcome join 後の gate D 減算コストのみ。イベント選択・方向・サイズの
  いかなる rate 条件付けも E20 隣接違反。
- **OOS 地平の事前宣言**: `e20_carry_level.csv` は 2022-12-30 で終端 (explore 完全被覆)。OOS 側 swap ソース
  (`e20_rates_ingest` の BIS 再 ingest 拡張) を**今**宣言し、実行は OOS touch 前 (look 問題なし)。

---

## 7. two-pass 機構 (#19 §4 パターンの明文化)

- **pass-1 export** = `date|pair|side|z|d1_close|mfe5` のみ (MFE5 = fade 方向の対 entry 最大順行、再構築 D1 H/L
  ベース、T+1..T+5)。gate A verdict + pooled N + per-pair **無条件** 5d |Δclose| 分散 (§5.3 の MDE 再計算用、
  event-independent) を裁定・コミットしてから pass-2。
- **pass-2** (生存ペアのみ) = `net5|net10|mae5`。統計ツールは freeze commit に同梱 (seed 20260805)。
- gate A で <2 ペア生存 → family KILL (draft どおり維持)。
- knife-edge (全 gate PASS 後のみ、選択不使用): z {1.75, 2.25} / SMA {160, 240} / std {45, 75} /
  entry {固定 23:00 UTC (非金曜), 00:00 UTC 翌日} / block {1-ISO-週}。primary 符号反転はどれでも FAIL。
  std ddof=1、SMA/std は当該バー除外 (draft 逐語維持)。

---

## 8. LOCK-前必須条件 (統合・重複除去済み 21 条)

**[B] = blocking (未了のまま LOCK した場合、本検証 verdict は失効する)**

**A. データ被覆・品質**
1. **[B] 被覆修復**: per pair first 1h bar ≤ **2013-03-01** を assert (現状 2014-07-16 で 3/3 不成立 = data-blocked)。
   主経路 = OANDA H1 backfill (07-29 手法)、PR #138 入り checkout から、splice-QA 付き。fallback = 測定前の
   窓再宣言 + gate F/LOYO リスケール + デシンク欠損 honesty 条項。「あるもので走る」禁止 (§6.1)。
2. **[B] 穴修復 or 凍結 gap-tolerance**: gap-backfill WINDOWS を 2020-10-13..**2021-01-03** へ延長して 3 クロスを修復
   (AUD_NZD 51 日穴 / NZD_CAD 72 日穴、実測)。修復後 assert: 週内 gap > 72h なし。不能なら §6.2-1 の凍結規則 + census 公表。
3. **[B] despike 規則凍結** (gate A の PASS 汚染防止): 8× rolling median flag / MFE 極値除外 / flag D1 close の
   OANDA 照合置換 / census 公表 (§6.2-2)。
4. **[B] D1 再構築規約の本文再宣言**: America/New_York NY17:00 境界 (zoneinfo)、1h ラベル語義の事前検証、
   degraded_close 規則、bars/week・曜日一様・構成バー数 assert (§6.2-3)。
5. QA 横断 assert: 単調・重複ゼロ・三角残差 p99 (§6.2-4)。
6. **[B] sha256 pin 一式** + 測定は freeze commit 後のみ + フル parquet (§6.2-5)。
7. P-10 hygiene: Volume/vwap 非読取のコード assert (§6.2-6)。
8. TV 照合順序: 件数チェック = pass-1 可 / 符号照合 = pass-2 後のみ (§6.2-7)。

**B. estimand / 執行**
9. **[B] entry = 19:00 America/New_York バー close** を primary に凍結。catalog「23:00 UTC」字面からの偏差 +
   DST 根拠 + G0 夏時間限定証跡の honesty 条項を on-record。D1 close-to-close = 診断、固定 23:00 UTC = knife-edge。
   live 化時の冬スプレッド再測定義務を注記 (§4.1)。
10. **[B] 金曜規則**: 金曜 close イベント → 次営業日 19:00 NY entry (遅延報告)。「holiday skip」無音条項の削除。
    onset 端点規則 (z(t−1) 未定義 / excursion 内符号反転 / 再エントリ / std60 guard) を凍結 (§4.1-4.2)。
11. **[B] Q7**: 全 onset 測定 (hold-collision skip 禁止)、skip 版は診断、overlap/co-fire share 報告義務 (§4.2)。

**C. 統計**
12. **[B] Q1**: pooled primary m=1 片側 p<0.05。§4.1 Bonferroni 行を逐語引用 + on-record 修正 (per-cell MDE
    29-39p の非テスト算術を記載)。補償: gate G binding / claim = family-pooled 恒久限定 / 他 wave-6 explore
    起動時は BH q=0.10 合流 (§5.1)。
13. **[B] block 構造**: 固定 2-ISO-週 block・全ペア pool・block 単位 flip が primary。per-pair block 禁止。
    1 週版・merge 版は診断。#19 からの deviation-strengthening 記録 (§5.2)。
14. permutation 仕様完全凍結: seed/draws/p 式/block 割当/gate G 派生 seed/gate E 分母 (max_w|S_w|/Σ|S_w|) (§5.2)。
15. **[B] power 正直化**: gate B = events ≥120 **かつ** blocks ≥50、pass-1 で無条件 5d 分散から MDE 再計算、
    MDE 表公表、9.1p/sd45 破棄、「家系サイズ効果は構造的に FAIL = 意図された viability filter」を逐語記載。
    UNDERPOWERED 天井案は棄却済み (§5.3)。
16. gate G binding 形: per-pair ≥2/3 + サイド kill (mean<0 ∧ p<0.10)、サイド N<30 は発火不能 flag (§5.4)。
17. gate F: 被覆 option (a) なら 6/8 + LOYO 8/8 維持 / option (b) なら測定前リスケール。false-kill ≈50% の事前記録 +
    C-PASS/F-FAIL 再審禁止。warmup 由来の first-eligible 日と分母を導出で記録 (§5.5)。

**D. 摩擦 / swap**
18. **[B] swap 凍結**: 3 式 (base−quote 検証済み) + per-event per-side accrual + markup 実測較正 (≥10 非異常
    スナップショット、現行 ≈1.1%/yr) + adverse 端 PASS 要求 + 0/0=MISSING + worse-of 規則 + E20 ファイアウォール +
    OOS swap ソースの事前宣言 (§6.3)。

**E. ban 隣接 / クローズ範囲 / 記載修正**
19. **[B] L-d 差分節の追加** (最近接 killed neighbor の欠落修復): catalog L-d 行 + level-family 検証 md を引用、
    anchor = SMA200/std60 (回帰勾配・swing fit なし) = L-d 裁定の許容空間内、universe = 全チャネル測定に不在の
    3 クロス、レンジ相場での regression-200 ≈ SMA200 収束 caveat を on-record。bb_rsi scope 別注記。
    IC-first 字義履行: 非拘束 Spearman IC(z, fwd5d) を explore report に記載し 06-25 条項の discharge と宣言
    (選択不使用) (§3.1)。
20. **[B] FAIL 時クローズ範囲の事前凍結**: 「slow location-anchor (mean/percentile/regression) band fade ×
    multi-day × AUD_NZD/AUD_CAD/NZD_CAD、全 anchor 着せ替え」— **variant B を明示的に含む**。B の復活は
    新 family + 事前差分節 + 新規敵対的検証のみ (L-e 条件付きクローズの鏡像)。
21. 記載修正: 23:00 出典 = catalog #21 行 / hour-23 p50 2.7-2.9p・p75 2.9-3.1p の実数引用 / §4.1 AUD_NZD レンジ
    erratum 一行 / merge_never_shorten claim の訂正 (§1.2-3/-9/-13)。

---

## 9. score honesty 監査

- **誠実だった点**: orchestrator_honesty 4 項目は全て実在する問題の自己申告 (頻度 = oracle guess の明示、
  0/0 の PASS バイアス警告、hard-mode 窓の「gate F が regime で落ちてもそれが規律」宣言、Bonferroni 矛盾の
  明示 + verifier 所有の明言)。一次数値は 5/5 lens の照合で**捏造・盛りゼロ** (G0/毒窓/効果量/窓/slot 全一致)。
  variant B の NON-TESTED 宣言、two-pass staging、UNDERPOWERED 分岐、wave-5 教訓 (実測してから claim) の
  price_source への部分適用 — いずれも検証文化の水準を維持。
- **バイアスが漏れた箇所 (全て PASS 方向、条件で中和済み)**:
  (i) **被覆 assert をベンダー限界ちょうどに置き、しかも warmup を織り込まなかった** — 通れば gate F が壊れ、
  落ちれば data-blocked という、どちらでも設計が成立しない assert だった (§1.2-1)。wave-5 §12 の指摘
  「進めたい方向にデータ実在を仮定する」型の再演であり、W3-2 の probe-first 教訓の再度の不履行。
  (ii) **markup 0.50%/yr** — 自プロジェクトの live スナップショット (08-04、payload 時点で worktree に実在) が
  ~1.08-1.09%/yr を示しているのに未参照 (§1.2-6)。gate D への最大の PASS バイアス。
  (iii) **sd=45p アンカー** — 「verifier に再導出させる」と書きつつ 9.1p を見出しに置いた anchoring (§1.2-7)。
  (iv) **金曜/DST の穴** — 「holiday skip」の一句に ~1/5 のイベント削除と冬毒窓踏み抜きが埋まっていた (§1.2-2)。
  (v) **L-d の欠落** — 差分節リストが最近接の killed neighbor (5 日前の triage KILL) を挙げていない (§1.2-8)。
  隣接リストの選択自体に生存バイアスが乗った形。
  (vi) §4.1 Bonferroni の「frozen_constraints から gate C の arbitrate への移設」は開示済みだが、
  省略方向が pro-proceed であった事実は記録する (§1.2-10)。
- **総合**: 数値誠実性は高いが、**「凍結したつもりの前提条件」の実在検証が 4 系統で不足** — いずれも
  実測すれば payload 時点で発見可能だった (実際、本検証は全て worktree 内の実測のみで発見した)。
  wave-5 と同じ教訓が再発している: **assert は書くだけでなく、payload 提出前に一度走らせること。**

---

## 10. 最終 verdict

**GO-WITH-CONDITIONS (§8 の 21 条、blocking 12 条) — ただし現時点は data-blocked 状態であり、
条件 1 (被覆修復) が物理的な第一ブロッカー。条件 1-4, 6, 9-13, 15, 18-20 が完了・freeze doc に凍結されるまで
LOCK 禁止。LOCK は blocking 条件の消化を照合してから (本 report を freeze doc から参照すること)。**

- **KILL でない理由**: ban 同一性は不検出 (L-d は triage kill で測定 null 不在、06-25 は証拠スコープ外、
  E20 はソースレベルで回避検証済み)。この estimand (D1 z-fade × commodity cross × 5d) に測定済み null は存在しない。
- **無条件 GO でない理由**: draft のまま走れば gate A (spike 汚染) / gate B (MDE 半分) / gate C (反保守 block) /
  gate D (markup 半分) の 4 gate 全てが PASS 方向に歪む — 敵対的検証なしでは「PASS」が出ても信用できなかった。
- **PARK でない理由 (honesty-power lens の戦略裁定を採択)**: 期待科学価値は低い (家系 3/3 死亡 + 機関 RV 混雑 +
  正直 MDE 近傍の swap drag) が、コストはほぼゼロ (内部データ・live 非接触・1/3 slot・E7/E1/E12/#22 と非干渉) で、
  G0 clean PASS 後の憲章既定の次手。E7 (08-28) を待っても本 family には何も届かない。
  **安価で正直にゲートされた kill attempt として進める** — それが本 family の期待値に見合う唯一の走らせ方である。
- 台帳処理: #21 は explore active (1/3) のまま。PASS → OOS pre-reg DRAFT → user 承認 stop (live 変更禁止) は
  draft 宣言どおり。FAIL → 条件 20 のクローズ範囲で即クローズ。
- KB 永続化: 本 report + payload を raw/analysis に。freeze doc 起案時に §8 条件の消化状況を条件番号で照合すること。

**総括**: G0 の摩擦測定と freeze 規律は模範的で、設計骨格 (exit-free / two-pass / pooled primary / 事前 kill 規則)
は #19 品質バーを満たす。しかし draft は「凍結の器」はあるのに「凍結する中身」の実在検証が 4 箇所で欠けており、
その全てが PASS 方向に倒れていた。修復は全て機械的・fwd 非接触で可能であり、家系起因のブロッカーは存在しない。
被覆を直し、markup と MDE を実測値に置き、block を 5d 地平に合わせ、金曜と冬を設計に入れてから凍結せよ —
その freeze doc は、slow-MR 家系 3 連敗の後で「今度こそ測る価値がある形」になっている。
