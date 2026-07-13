# Pre-registration: WS3 round-3 外部仮説 — cross-asset divergence-reversion (2026-07-13)

**Status**: 🔓 **DESIGN self-LOCK (純研究、stage-1/round-2 前例準拠)** — 方法論・窓・判定規則を結果観測前に固定。候補セルは discovery diagnostic 後に §2b へ**凍結 (追記して 🔒)**、その後 OOS verdict。**live 実装はここでは禁止** (PASS≥1 で D4 準拠の実装 pre-reg を別途起案 → user LOCK)。
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
(未実行 — discovery diagnostic 後に §2b 候補凍結 → OOS verdict をここに追記)
