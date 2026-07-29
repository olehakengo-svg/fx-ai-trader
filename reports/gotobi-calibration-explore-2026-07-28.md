# gotobi_tokyo_fix_usdjpy explore verdict — ✅ 較正成功 / ❌ 昇格 kill (2026-07-28)

**結論: 測定ハーネスは公表実在効果を回収できることを実証 (較正目的達成)。エッジ自体は
sub-friction (+1.9p < RT 2.14p) で、昇格テール cell は凍結 kill rule どおり死亡。family クローズ、
OOS 未接触。台帳 #13 verdict 追記。**

- Protocol (観測前凍結、コミット 7bb17f2 系): [[gotobi-calibration-explore-prereg-2026-07-28]]
- 測定器: main checkout `USD_JPY_5m_2014_2026.parquet` (フル被覆 2014-01-02〜) + structural_events.parquet
- Stats: `tools/gotobi_calibration_explore.py` (seed 20260728、month-block permutation 10,000×)
- Raw: `knowledge-base/raw/bt-results/gotobi-calibration-explore-2026-07-28.json`
- explore 2014-2021: JP 営業日 1,927 (FX bar あり)、gotobi A/B 559/557、EOM 94
  (導出 EOM は calendar `month_end_jp` 列と mismatch ゼロ)

## 結果

| レグ | diff (pips) | p | verdict |
|---|---|---|---|
| C1 fix 窓 規約 A (翌営業日繰り、primary 凍結) | +0.33 | 0.595 | ✗ 効果なし |
| **C1 fix 窓 規約 B (前営業日繰り、較正診断)** | **+1.92** | **0.0032** | ✅ **公表効果を gross 回収** |
| C2 fix 後反転 (規約 A) | +0.87 | 0.505 | ✗ 反転検出なし |
| **P1 昇格テール cell (EOM D1、m=1)** | **+1.38** | **0.430** | ❌ **kill rule 発動 (< 13p ∧ p≥0.05)** |

診断: DOW-matched C1 (A) +1.06p (組成バイアス小)。年次 (A 規約下) は 2015-2020 正・2014/2021 負の
混合 — 公表 (2017) 後の減衰と整合的なレンジ。

## 較正の成果 (この explore の主目的 — 達成)

1. **測定ハーネスの正当性を実証**: 我々の exit-free 測定器は ~2p の実在公表効果を p=0.003 で
   検出できる。過去の null 群 (H4 レベル、チャネル、月末系等) が「測定器が壊れていて見えなかった」
   のではないことの直接証拠 — postmortem §4f (測定器故障史) への解毒剤として機能した
2. **gotobi 繰り越し規約の解決**: in-repo 3 文書矛盾 (catalog #0 "rolled forward" / #78 "prior
   business day" / strategy card) は **規約 B (前営業日繰り) が正** — 決済日までにドル手当てが
   必要な輸入実需の性質と整合。今後 gotobi に触れる全ドキュメントは B に統一すること
3. **効果は実在するが sub-friction**: +1.92p vs USD_JPY RT 2.14p (実測フロア 1.30p でも headroom
   1.5x < 10x)。postmortem §2「friction > edge」死因クラスの教科書例 — 「アノマリーが本物であること」
   と「リテール摩擦で収益化できること」は別問題、の直接実証

## 昇格判定 (凍結ルールの機械的適用)

- P1 = +1.38p < 13.0p (kill 閾値、実測フロア×10) かつ p=0.43 ≥ 0.05 → **family クローズ**
- 誓約どおり: 規約 B の有意性 (+1.92p) を根拠に fix-window cell を「有望」と再解釈しない
  (sub-friction であり、かつ B は較正診断として宣言済み — 昇格に使えば宣言違反)
- OOS 2022+ は未接触のまま保存
- 再試行禁止スコープ: **gotobi/仲値系の USD_JPY 昇格提案は「摩擦 < 効果」を成立させる新条件
  (執行コスト構造の変化 or fix 参加経路) なしには不可**。tokyo_nakane_momentum (shadow) も
  本 verdict の同 family — 独立 family として再登録しない

## 台帳への影響

m=13 verdict 追記 (クローズ)。アクティブ枠 1/3 → 0/3。次の能動線 = ppp (条件解消後、単独 wave) /
holiday 縮約版 (背景)。受動: E7 (08-28) / E1 (10-15) / MoF (Q2+10d) / P-S1(a) (N=8/10、8 月上-中旬)。

## 追記 (2026-07-29): データ欠損の robustness 注記

holiday カレンダー検証で MASSIVE キャッシュに欠損 2 区間 (2019-09-14〜10-05, 2020-10-13〜11-14、
5m/1d とも 0 行) が発見された。本 explore への影響評価: 欠損は explore 8 年の ~2% であり、
gotobi 日と非 gotobi 日の両群を等しく欠くため diff-in-means は不偏 — **C1/P1 の verdict は不変**。
キャッシュ再取得は chip task_146ae96b で別線化。
