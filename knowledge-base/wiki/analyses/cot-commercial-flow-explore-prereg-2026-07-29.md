# cot_commercial_flow_weekly 凍結探索プロトコル — 単独 wave (2026-07-29)

**性格**: 観測前プロトコル凍結 (explore 段階 + PASS 時 OOS 単一接触ルール込み)。tier action なし、
live 変更なし。台帳 **#16** 登録 (**単独 family、m=1** — wave-1 教訓「強 prior 家系は分母を割らない」
+ 本 wave-3 敵対的検証の実行順序指定どおり W3-1 先行)。
**敵対的検証**: GO-WITH-CONDITIONS (`raw/analysis/wave3-adversarial-verification-2026-07-29.md`
[W3-1]) — **6 条件を本ドキュメントで全て解決してから凍結** (§条件解決)。
**メカニズム**: commercial hedger (輸出入実需) は価格非感応の強制フロー。その 4 週フローの極性は
実体経済ヘッジ圧力の変化を反映し、fwd リターンと相関する (hedging-pressure premium 系、
De Roon+ 1998)。**prior は正直に low〜mid (45-50)** — 兄弟 family (cot_spec_extreme #5) は
incoherence で死亡、Sanders-Irwin 系の null も公知。FAIL が十分あり得る前提で登録する。

---

## 条件解決 (敵対的検証 6 条件)

1. **primary 1 本凍結** ✅ — **pooled Spearman IC (continuous、週次全観測)** を採択、tercile onset は
   不採用 (閾値 DoF ゼロ化 + 検定力最大化)。ホライズン = **fwd 10 営業日 (2w) の 1 本のみ**
   (1w は公表直後ノイズ支配、4w は Δ窓と重複過多 — 機構スケール中央)。**attestation: 本設計は
   COT×価格ジョイント計算に一切接触せず決定** (パネル rebuild はシグナル側列の追加 + spot-check のみ、
   リターン結合ゼロ)。m=1、α=0.05 両側
2. **Δ窓 = 4 レポート (4w) 単一設計点** ✅ — 変種試行 (2w/8w/12w 等) は本 family 内で禁止。
   kill 後の窓変種再試行も禁止 (cot_spec の単一設計点規律を継承)
3. **cot_spec 死因の機械 kill rule 化** ✅ — 診断でなく必須合格条件に昇格 (§gates (ii)-(iv))
4. **鏡像恒等性の開示** ✅ — 会計恒等 comm_net ≈ −(noncomm_net + nonreportable) により Δcomm は
   −Δnoncomm とほぼ鏡像 (rebuild spot-check でも JPY 2024-04 に可視)。**「別 counterparty」による
   独立性主張は減額し、本 family の新規性は『Δ (flow) 変換 × 週次連続 IC』が主、母集団差は従**と
   正直に位置づける。診断で corr(Δcomm_pct_oi, −Δnoncomm_pct_oi) を必須併記
5. **multi-week swap 純額込み** ✅ — headroom gate (v) は swap 純額込み net move で判定。
   swap_pips = rd_fc/100 × 10/252 × price/pip (FC ロングの受払、ショートは符号反転)。
   rd_fc = BIS CBPOL 政策金利差 (`knowledge-base/raw/bt-results/e20/e20_carry_level.csv`、
   列 = base−quote なので FC_USD ペアは +値 / USD_FC ペアは −値)。パネルは 2022-12-30 まで —
   **explore は完全カバー。OOS 執行時は e20_rates_ingest で 2026-06 まで更新してから接触**
   (更新不能時は最終値 ffill + 開示、これは保守側でない旨も開示)。earn 側 25% haircut は診断
6. **継承 assert 群** ✅ — commercial 実列名 assert (`build_cot_panel.py` COL_C_LONG/SHORT、
   rebuild 済み 5178 行・行数/日付レンジは旧パネルと一致)、JPY/CAD/CHF クオート反転マップ、
   release-lag +3 営業日、lookahead assert (entry > publish ∧ entry − report ≥ 6d) を
   cot_spec 凍結規約から無変更継承

## 凍結事項

- **データ**: `data/external/cot_fx_panel.parquet` (rebuild 2026-07-29、comm 列追加) +
  spot 1d = `data/cache/massive/{PAIR}_1d_2014_2026.parquet` 6 ペア (EUR_USD, GBP_USD, AUD_USD,
  USD_JPY, USD_CAD, USD_CHF)。**QA (凍結)**: 週末日付 (土日 UTC) バーを bar 系列から除外
  (price_shock 監査の土曜 artifact 前科 + bar-index 演算の正確性。実測 sat 66-124 / sun ~643)
- **シグナル (単一凍結構成、grid なし)**: flow_t(ccy) = comm_net_pct_oi_t − comm_net_pct_oi_{t−4}
  (4 レポート = 4w、OI 正規化済み Δ)
- **タイミング**: report_date (火曜 as-of) → publish = +3 営業日 (金曜) → entry = publish より後の
  最初の 1d バー (月曜想定、guard: entry − report ∈ [6, 10] 日)。fwd return = Open_entry →
  Open_{entry+10 営業バー} を pips で、**FC 増価方向に統一** (FC_USD ペア +raw / USD_FC ペア −raw)
- **窓**: explore = report_date **2014-01-01〜2021-12-31** (パネルは 2010+ だが in-repo spot 1d が
  2013-12-30 開始のため — ex-ante 明記)。**OOS = 2022-01-01〜2026-06-30、PASS 時のみ単一接触**
- **primary test (m=1、α=0.05 両側)**: pooled Spearman IC(flow, fwd_fc_ret)、
  p は **26 週移動ブロック × 全通貨同時 (週行単位) の独立リサンプル帰無分布** (シグナル側と
  リターン側の週行ブロック列を独立に復元抽出して alignment を破壊、10,000 回、seed 20260729)。
  ppp #14 の「時間ブロック × 全ペア同時・独立リサンプル」設計を週次パネルへ一般化したもの
  (ppp 実装は均一グリッド前提のため、guard スキップでラグドになり得る週次パネルには移動ブロック形で
  適用する — USD 共通因子・自己相関は行単位リサンプルで保存)
- **必須合格条件 (すべて、機械適用)**:
  - (i) primary IC の両側 p < 0.05
  - (ii) quintile 単調性: pooled quintile 平均が IC 符号方向に単調 (隣接違反 ≤1 ∧ Q5−Q1 符号一致)
  - (iii) 集中ガード: LOYO (8 年) 全てで IC 符号不変 ∧ 単一年の寄与 share ≤50% ∧ SNB 窓
    (2015-01 月) 除外で符号不変
  - (iv) サイド split: flow>0 サブパネルと flow<0 サブパネルの IC が両方 pooled と同符号
  - (v) headroom: 上位/下位 quintile の |fwd 10bd net move (swap 純額込み)| 中央値 ≥ 10 × per-pair RT
    (RT 凍結値 = EUR_USD 2.00 / USD_JPY 2.14 / GBP_USD 4.53 / AUD_USD 3.00 / USD_CAD 3.50 /
    USD_CHF 3.50。floor 1.30p 感度は診断)
  - (vi) **レベル中立化 (ban 隣接ガード、ハード条件)**: flow を net_pct_oi レベルに回帰した残差の
    IC が原 IC の 50% 以上を保持し符号不変 (per-currency OLS。banned『レベル極値』効果の
    着せ替えでないことの強制)
- **kill rule**: いずれか不成立 → **family FAIL クローズ、OOS 未接触保存**、台帳 verdict 記録。
  **同型再試行禁止スコープ = 「COT ポジショニングの Δ/flow 変換 × 週次固定ホライズン」全変種**
  (Δ窓・ホライズン・母集団 (comm/noncomm/nonreportable)・閾値化の別を問わない)。COT 残余空間
  (trader counts / concentration 等) は新 family + 強差分節でのみ
- **knife-edge**: p が α の 0.5〜2 倍域 (0.025-0.10) なら 3 点検査 (LOYO 済み / block 6mo→3mo /
  seed 変更) 全通過で初めて PASS
- **OOS (PASS 時のみ)**: 同一定義・同一統計、explore 符号に固定した**片側** α=0.05、
  gates (ii)-(vi) 同一適用 (LOYO は 2022-2026)。**OOS PASS → R1 パケット起案で停止**
  (live 実装なし、user 最終承認まで)
- **診断 (選択に使わない)**: per-currency IC / 年次 IC / fwd 1w・4w (参考のみ、判定外) /
  corr(Δcomm, −Δnoncomm) / swap haircut 25% / quintile 表 / nonreportable share /
  RT floor 感度 / 土曜行除外件数

## 隣接差分 (必須節)

- **cot_spec_extreme (#5 FAIL)**: ban 原文「ban 範囲は『net_pct_oi レベル極値×週次』限定 —
  Δnet/flow・commercial 側は新 family として可」。差分 = (i) Δflow 変換 (レベルでなく変化)、
  (ii) percentile 極値 onset 不使用 (連続 IC)、(iii) 母集団 commercial (ただし §条件解決 4 の
  鏡像恒等により従属的差分と正直に開示)。gate (vi) で着せ替えを構造的に排除
- **E20 carry (kill)**: 金利はスワップ会計のみに使用、シグナル・フィルタ入力ゼロ (ppp と同じ分離)
- **ppp (#14 FAIL)**: 月次レベル z 回帰 vs 週次フローの推定量直交。ハーネス (block bootstrap IC) は流用
- **E1 positioning (LOCKED 走行中)**: E1 はリテール aggregate (Myfxbook)、本 family は CFTC 先物
  報告義務者。**E1 ロック窓 (10-15 first look) のデータには一切触れない**

## 事前宣言 — 期待の較正

兄弟 family の死型 (点推定 incoherent) が commercial 側にも出る公算は相応にある。gates (ii)-(iv) は
それを早期に機械 kill するための装置であり、**FAIL = healthy kill として記録する**。composite score は
生成時 62 → 検証指摘に従い prior 45-50 相当へ減額して解釈する。

## 成果物

`tools/cot_commercial_flow_explore.py` / `tools/build_cot_panel.py` (comm 列拡張) /
`knowledge-base/raw/bt-results/cot-commercial-flow-explore-2026-07-29.json` /
`reports/cot-commercial-flow-explore-2026-07-29.md` / 台帳 #16 verdict 追記
