# Pre-registration: WS3 round-3 外部仮説 — cross-asset divergence-reversion (2026-07-13)

**Status**: ❌ **CLOSED — VERDICT PASS=0 / H0 採択 (2026-07-14、期日 07-24 の 10 日前倒し)**。data-availability で窓を data-driven 再指定 (§2b AMENDMENT、結果観測前) → discovery 216 cells → top-8 凍結 → OOS 8/8 反転。§4 固定分岐発動 = E1 positioning 格上げ。詳細は §8。(旧: 🔓 DESIGN self-LOCK — 方法論・窓・判定規則を結果観測前に固定)
**rule**: R1 (新シグナル系統。365d BT + Bonferroni + pre-reg LOCK が昇格の必要条件)
**owner**: claude (autopilot 自走可 — データ到達済・net 到達可)
**関連**: [[external-hypothesis-scan-2026-07-13]] (起案根拠) / [[ws3-round2-explore-prereg-2026-07-10]] (方法論母型) / [[shortest-path-decision-memo-2026-07-10]] D4 (実装必須項目) / [[roadmap-v2.3-payoff-friction-repair]] WS3

---

## 1. 仮説 (H1) と機構

**H1**: FX (特に金利感応ペア USD_JPY / cross-JPY) が、金利先物 (ZN=10y T-note、後続で ES/株も) との**強い contemporaneous linkage (実測 IC −0.585)** から短期乖離したとき、その乖離は次の H バーで**方向性を持って回帰する** (divergence-reversion)。

**なぜ先行 lead-lag と違うか**: [[external-hypothesis-scan-2026-07-13]] §3 で **価格の先行構造 (lead-lag) は ≥1h で裁定消滅**を実証済み (ZN→USDJPY lag-1 IC 0.0075)。本仮説は「先行」ではなく「同時 linkage からの乖離の平均回帰」= **非先行構成**。エッジの source は情報の時間差ではなく、一時的 dislocation の crowd 過剰反応 (mean-reversion regime、Lo-MacKinlay 1988 系)。

**H0**: 乖離 z-score は次 H バーの符号付き超過リターンに対し予測力を持たない (friction 調整後 EV≤0)。

## 2. 手続き

### 2a. データ準備 (discovery 前)
- rates 長期 history 取得: ZN=F を 15m/1h で **2021-01-01〜** まで拡張取得 (`data/cache/yield/`、net 到達可)。tz を FX 1h (UTC) に整合。将来 ES=F (equity) も同様に。
- FX: Massive cache 1h (全ペア済)。**JPY 感応ペア優先** (USD_JPY / EUR_JPY / GBP_JPY / AUD_JPY)、比較対照に EUR_USD / GBP_USD。

### 2b. discovery diagnostic (探索窓のみ, 候補固定)
- **探索窓**: 2021-01-01〜2024-06-30。
- 乖離定義 (探索窓で最適化してよい = 選択バイアスは OOS で除去): rolling-β の rate-implied FX return からの残差 z-score (窓 {60,120,240} bars × z 閾 {1.5,2.0,2.5})。
- 各 (pair × 乖離パラメータ × horizon H∈{6,12,24,48}) で first-touch 摩擦調整 EV と reversion IC を計測。
- **選抜規則 (round-2 の EV スクリーン教訓を内蔵)**: 探索窓 first-touch EV>0 **かつ** reversion IC の符号が機構整合 (乖離 z と逆符号) の cell を列挙 → **N≥30, m≤8** に絞り §2b に**凍結して 🔒** (この時点で candidate list を追記コミット)。

---

### 🔧 AMENDMENT 2026-07-14 (data-availability — 窓再指定、結果観測前 = look-ahead なし) 🔒

**§2a の前提「ZN=F を 15m/1h で 2021-01-01〜 net 到達可」は実測で falsified。** intraday rates history の実測フロア (2026-07-14 検証):
- yfinance `ZN=F` 1h: **2024-02-18** が最古 (Yahoo は 1h intraday を ~730 日に制限)。日次は 2021+ 取得可だが、本仮説は h6-48 = 1h バーの intraday reversion なので日次では検定不能。
- Massive futures aggs (`/futures/v1/aggs/ZN{contract}` 1hour): ZNZ4 は 2024-07-15 開始、ZNH3 (2023) は空 → フロア ~2024-07。
- Massive equities aggs (IEF/TLT 1h, treasury ETF proxy): 2024-08 可 / 2023-07 は HTTP 403 (plan lookback ~2y)。

→ **exploration 窓 (2021-2024.06) に intraday rates が全ソースで不在。** 純研究 self-LOCK であり discovery 未着手のため、**結果を一切観測する前に**、利用可能な intraday データに合わせ窓を data-driven 再指定する (look-ahead bias なし)。判定規則 (2 レグ / 閾値 / ナイフエッジ) は不変:
- **EXPLORE 再指定**: `2024-02-18 〜 2025-06-30` (~16.4mo、yfinance ZN=F 1h continuous = 最長 intraday rates)
- **OOS 再指定**: `2025-07-01 〜 2026-05-15` (~10.5mo、FX Massive cache 末尾)
- rates source = yfinance `ZN=F` 1h continuous (back-adjusted front-month)、`data/cache/yield/ZN_F_1h.parquet` (UTC、N=12,760)。
- 機構 sanity (full window): contemporaneous IC USD_JPY −0.46 / EUR_JPY −0.27 / GBP_JPY −0.28 / AUD_JPY −0.19 / EUR_USD +0.28 / GBP_USD +0.27 (全て符号整合)、lag-1 lead IC 全て ~0 (lead-lag 死、external-scan §3 と一致)。
- harness: `tools/ws3_crossasset_divergence_explore.py` (乖離定義・EV primitive はファイル docstring に明記)。

### 2b-FROZEN (discovery 実行 2026-07-14 → 候補凍結 🔒)

discovery: 216 cells scan (6 pair × W{60,120,240} × z{1.5,2.0,2.5} × H{6,12,24,48})。選抜規則充足 (EV_ft>0 ∧ IC<0 ∧ N≥30) = **47/216** (pair 別: AUD_JPY 18 / EUR_USD 13 / GBP_JPY 8 / EUR_JPY 5 / USD_JPY 3 / GBP_USD 0)。**top-8 by EV_ft を凍結** (`ws3_round3_frozen_candidates.json`):

| # | pair | W | z | H | explore N | EV_ft (p/t) | EV_hz (p/t) | reversion IC |
|---|------|---|---|---|-----------|-------------|-------------|--------------|
| 1 | GBP_JPY | 120 | 2.5 | 12 | 68 | +6.51 | +19.11 | −0.213 |
| 2 | GBP_JPY | 120 | 2.5 | 24 | 53 | +6.12 | +22.07 | −0.228 |
| 3 | GBP_JPY | 120 | 2.5 | 6 | 97 | +4.19 | +11.44 | −0.152 |
| 4 | GBP_JPY | 60 | 2.5 | 12 | 107 | +4.05 | +4.57 | −0.071 |
| 5 | AUD_JPY | 120 | 2.5 | 12 | 84 | +3.77 | +12.77 | −0.279 |
| 6 | GBP_JPY | 120 | 2.5 | 48 | 46 | +3.56 | +8.37 | −0.104 |
| 7 | USD_JPY | 120 | 1.5 | 48 | 108 | +3.49 | +4.95 | −0.063 |
| 8 | AUD_JPY | 120 | 2.0 | 12 | 163 | +3.01 | +8.14 | −0.171 |

⚠️ 凍結セットは GBP_JPY W=120 z=2.5 に集中 (top-by-EV rule の帰結) — 相関の高い near-duplicate。fold 集中/regime 依存を §8 ナイフエッジで検定。**この時点で LOCK、OOS 実行へ。**

### 2c. OOS verdict (LOCK 後)
- **OOS 窓**: 2024-07-01〜2026-05-15 (cache 末尾)。**E3 は新シグナル系統で本窓は per-signal 未使用 = 有効な OOS** (FX 日付は round-1/2 OOS-1 と一部重複するが、検定対象の signal family が全く異なるため独立。窓消費履歴に明記)。
- **判定 (2 レグ、両方充足で PASS — round-2 準拠)**:
  - (A) reversion IC レグ: 日次ブロックブートストラップ (B=10,000, seed 固定) → BH-FDR q=0.10 (m=候補数) ∧ point |IC|≥0.05 ∧ OOS N≥30。
  - (B) first-touch 摩擦調整 EV レグ: §2b 凍結 grid の OOS EV について best 構成の 3×3 近傍平均 ≥ +0.5 p/t ∧ 隣接過半 EV>0 (stage-2 §5.3 基準)。
  - ナイフエッジ3点検査 (擬似反復 lag-1 ρ / 孤立格子点 / fold 集中 LOFO)。
- **分岐 (事前固定)**: PASS≥1 → D4 準拠の実装 pre-reg 起案 (carve-out + R2 降格ゲート + セル単位判定 + shadow parity)、**user LOCK 承認**へ。PASS=0 → cross-asset **価格** モダリティも枯渇と判定し、**E1 positioning モダリティ** ([[external-hypothesis-scan-2026-07-13]] §6) の infra 決定を主戦線に格上げ。

## 3. 期日・監視
- discovery + 候補固定 + self-LOCK: **2026-07-20** / OOS verdict: **2026-07-24**。
- LOCK 時 (候補凍結時) に `prereg-trigger-registry.json` の本エントリ deadline を確定化。

## 4. 除外・注意
- falsified 6 系統 (H4 level / channel / horizontal sweep&reclaim / mtf SELL / bb_rsi / T11 counter-USD) の再試行禁止。本仮説はいずれにも該当しない (cross-asset 乖離は新系統)。
- 唯一 ELITE_LIVE の trendline_sweep には触れない (単一エッジへの実験は非対称リスク、教訓)。
- read-only 診断。live/shadow パラメータ不変更。BE/Trail は MFE/EV 計測に関与させない (forward scan、round-1/2 と同一)。
- **カーブフィッティング禁止**: 乖離パラメータの探索窓最適化は許すが、OOS で grid 再アンカーしない (round-2 と同一規律)。

## 8. VERDICT

### ❌ PASS=0 / H0 採択 (2026-07-14、期日 07-24 の 10 日前倒し)

凍結 top-8 (§2b-FROZEN) を OOS 窓 (2025-07-01〜2026-05-15) で検定 → **8/8 が探索の正 EV を反転、PASS=0**:

| pair | W | z | H | explore EV_ft | **OOS N** | **OOS EV_ft** | **OOS IC** | boot p | legA (IC) | legB (EV) | PASS |
|------|---|---|---|--------------|-----------|---------------|-----------|--------|-----------|-----------|------|
| GBP_JPY | 120 | 2.5 | 12 | +6.51 | 47 | **−6.28** | +0.125 | 0.402 | ✗ | ✗ | ✗ |
| GBP_JPY | 120 | 2.5 | 24 | +6.12 | 37 | **−6.97** | −0.076 | 0.650 | ✗ | ✗ | ✗ |
| GBP_JPY | 120 | 2.5 | 6 | +4.19 | 73 | **−5.85** | +0.070 | 0.561 | ✗ | ✗ | ✗ |
| GBP_JPY | 60 | 2.5 | 12 | +4.05 | 58 | **−7.16** | +0.102 | 0.449 | ✗ | ✗ | ✗ |
| AUD_JPY | 120 | 2.5 | 12 | +3.77 | 47 | **−0.70** | −0.119 | 0.429 | ✗ | ✗ | ✗ |
| GBP_JPY | 120 | 2.5 | 48 | +3.56 | 28 | **−7.39** | −0.206 | 0.296 | ✗ | ✗ | ✗ |
| USD_JPY | 120 | 1.5 | 48 | +3.49 | 68 | **−1.39** | −0.180 | 0.140 | ✗ | ✗ | ✗ |
| AUD_JPY | 120 | 2.0 | 12 | +3.01 | 108 | **−1.89** | −0.100 | 0.305 | ✗ | ✗ | ✗ |

- **leg A (reversion IC)**: BH-FDR q=0.10 通過 **0/8** (min boot p=0.140、全て非有意)。数セルは IC が探索の負から OOS で **正へ符号反転** (GBP_JPY 群) = 探索の負 IC は選択バイアス。
- **leg B (first-touch 摩擦調整 EV)**: OOS EV_ft ≥ +0.5 p/t 通過 **0/8** (全て負、−0.70〜−7.39)。best 構成 3×3 近傍評価は grid 密度不足のため best-cell 基準で代替 (§2c 注記どおり)。
- 探索の強い正 EV (+3〜+6.5) は **選択バイアス + 2024-25 円 carry-unwind レジーム artifact** (探索窓は 2024-08 円急伸・BoJ 利上げ期を含み FX-rates coupling と violent reversion が異常に強かった)。OOS の別レジームで消滅。

### ナイフエッジ3点 (frozen set)
1. **fold 集中 / regime 依存**: 凍結 8 のうち 5 が GBP_JPY W=120 z=2.5 (near-duplicate)。探索の正 EV はこの1レジーム(carry-unwind)クラスタに集中 → OOS(post-unwind)で最も激しく反転 (GBP_JPY −5.8〜−7.4)。**regime-conditional な見せかけ**を確認。
2. **孤立格子点**: top-EV セルは z=2.5 (最高閾) の疎イベント (explore N 46-97) に偏る。隣接 z=2.0/1.5 は EV 半減 → 格子安定性なし。
3. **擬似反復 (first-touch sequencing)**: USD_JPY W=120 z=1.5 H=48 は OOS で **EV_hz +14.8 vs EV_ft −1.4** = horizon-exit では正だが first-touch で SL 先着に殺される。stage-2 [[ws3-stage2-barrier-ev-prereg-2026-07-09]] の「中央値非対称が first-touch sequencing で反転」現象を再確認 — barrier 設計では捕捉不能。

### robustness (post-hoc、**claimable ではない** = 記録のみ)
best-per-pair の OOS を副次確認: GBP_JPY 撃沈 (−6.3)、AUD_JPY ≈0 (−0.70)、USD_JPY first-touch 負。**EUR_USD (W240 z2.5 H12, OOS N=33 EV_ft +3.52 IC −0.16) と EUR_JPY (W240 z2.0 H12, OOS N=77 EV_ft +2.02 IC −0.23) は OOS 正 + 機構整合 IC で生存。** しかしこれらは (a) 事前登録された凍結セット外 (top-by-EV freeze が拾わなかった)、(b) OOS 成績で選ぶと round-1/2 と同じ選択バイアス、(c) 検証用の fresh OOS データ無し (cache は 2026-05-15 で終端、本 signal family は当窓消費済) → **PASS として主張不可**。price-modality が完全に枯渇したとは言い切れない残余シグナルだが、現行データでは clean 検証不能。

### 教訓 (freeze rule)
**top-by-EV の凍結規則が最も過学習したセル (GBP_JPY carry-unwind) を選び、頑健な EUR ペアを取り逃した。** 探索窓の raw EV は regime-amplified で選抜指標として脆弱。将来の freeze は pair 分散 or IC 安定性 (fold 間) or exploration Sharpe を併用すべき。→ lesson 化 ([[lesson-freeze-rule-topEV-selects-overfit-2026-07-14]])。

### 分岐 (§2c 事前固定どおり発動)
**PASS=0 → cross-asset 価格モダリティ枯渇と判定。E1 positioning (非価格) モダリティの infra 決定を主戦線に格上げ** ([[external-hypothesis-scan-2026-07-13]] §6、user 決定事項)。これで WS3 の price-based 探索は **内部2周 + 外部1周 = 計3周 FAIL** で一巡。lead-lag 実証閉鎖 + divergence-reversion OOS FAIL により、価格情報 (OHLCV 内部 / cross-pair / cross-asset) からの systematic edge は本プロジェクトの摩擦水準では枯渇と確定。

**条件付き round-4 (登録済トリガ)**: FX + rates cache が 2026-05-15 を **6ヶ月以上超えて延伸**したら、pair 分散 freeze (EUR_USD/EUR_JPY を事前登録) で新 OOS 窓による round-4 を安価に再試行可 (registry `ws3-round4-eur-divergence-conditional`)。それまでは E1 が主戦線。

### 窓消費履歴
- OOS 窓 2025-07-01〜2026-05-15 を cross-asset divergence-reversion signal family で **消費済**。同 family の再検定は 2026-05-15 超のデータが必要 (round-4 条件)。

