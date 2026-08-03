# round_number_major_level (台帳 #19) explore report — ❌ FAIL (2026-07-31)

**pre-reg**: [[round-number-level-explore-prereg-2026-07-31]] (🔒 commit 7bc04410 で凍結後に測定)
**データ**: TV OANDA D1 per-event export、6 ペア、explore 2014-01-01〜2021-12-31、**1,088 イベント** (実効 326 週)
**raw**: `knowledge-base/raw/bt-results/round-number-pass{1,2}-2026-07-31.json` / 測定器 `bt-results/tv-overlays/round_number_export.pine` / 統計 `tools/round_number_explore_stats.py`

## verdict: ❌ FAIL クローズ (OOS 2022+ 非接触保存)

| Gate | 結果 | 判定 |
|---|---|---|
| A headroom (per-pair MFE3d p50 ≥ 10×RT) | **6/6 PASS** — p50 62.3〜89.0p (要求の 2.0〜3.1 倍) + MoF explore 窓介入ゼロ assert 通過 | ✅ |
| B power floor (pooled N ≥ 200) | N=1,088 | ✅ |
| C primary (pooled 反転 3d 純移動 > 0, 週 block perm p<0.05) | **+6.34p、p=0.117** — 方向は正しいが n.s. | ❌ |
| D net EV (RT+swap 控除) | **+2.88p** (markup ±50%: +3.20/+2.56、RT floor: +4.45) — 点推定は正 | ✅ |
| E 集中 (単一週寄与 ≤50%) | 31.3% (2016-W25 = Brexit 週) | ✅ |
| F 一貫性 (年次符号 ≥6/8 + LOYO 全正) | **5/8** (LOYO は 8/8 正) | ❌ |

knife-edge 検査は非該当 (C/F 不通過 — p=0.117 は閾値の 2.3 倍で knife-edge 圏外)。

## 診断 (non-binding — 全て事後観察であり新規主張にしない)

- **死型 = 「方向は合うが弱い」**: ppp (IC +0.113 p=0.129) / quote-spread (方向一貫だが p=0.32) に続く 3 例目。
  N=1,088 の大標本で p=0.117 = 効果は実在してもリテール認定閾値未満の弱さ
- horizon 単調増加: net1 +0.87 → net3 +6.34 → net5 +11.94p (減衰しない — #18 と逆の形)
- per-pair: GBPUSD +15.2 / USDJPY +14.3 が牽引、EURJPY −1.6 / AUDUSD −0.4 フラット — ペア間再現性なし
- サイド split: S (下から接近→反転売り) +11.7p vs L +1.4p — Osler の TP クラスタ機構と整合する非対称だが事後
- **⚠️ 事後スライス禁止の明記**: 「S サイド × GBPUSD/USDJPY × 5d」等の勝ち残り組合せの切り出しは
  round-3 winner's curse (OOS 8/8 符号反転) の再演リスクそのもの。再挑戦するなら新 family + 事前差分節 +
  新 pre-reg のみ — 本 explore の数値を選択根拠に使うことを禁止する
- #18 との pair-週重複 13.5% (<30%) — 独立 2 家系として台帳記録可

## 帰結

- **同型再試行禁止**: メジャーラウンドナンバー (00 grid) fresh-approach × D1 反転 × 固定ホライズン exit-free
  全変種 (fresh 窓/grid/ホライズンの摂動、50-levels への拡張を含む)
- Osler 機構の D1 外挿は「弱すぎて認定不能」と実証。rnb_usdjpy shadow トラックには
  「歴史 D1 では反転方向 +6.3p/3d n.s.」を設計参照として供給 (tier action なし)
- **wave-4 (level-family) はこれで全 family 決着**: 平行線側 3 候補 = 敵対的検証 KILL、
  水平線側 2 候補 = explore FAIL ×2。差分空間は正直に「全滅」
