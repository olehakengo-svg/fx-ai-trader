# cot_commercial_flow_weekly (W3-1) explore — ❌ FAIL (2026-07-29)

**凍結プロトコル**: `knowledge-base/wiki/analyses/cot-commercial-flow-explore-prereg-2026-07-29.md`
(凍結コミット bc1a3e0a → 測定はコミット後。凍結ルールの機械適用、事後変更ゼロ)
**Raw**: `knowledge-base/raw/bt-results/cot-commercial-flow-explore-2026-07-29.json`
**台帳**: #16 (単独 wave m=1、#5 cot_spec_extreme の明示 carve-out)

## TL;DR

**❌ family FAIL — クローズ、OOS (2022+) 未接触保存。**

| gate | 結果 | 値 |
|---|---|---|
| (i) primary IC p<0.05 | ❌ | IC **+0.0186**、両側 p=**0.5652** (26 週移動ブロック独立リサンプル 10k) |
| (ii) quintile 単調性 | ✅ (辛勝) | 隣接違反 1/許容 1、Q5−Q1 符号一致。ただし形は非単調 ([−20.9, −4.7, +5.0, −14.8, −10.4]) |
| (iii) LOYO + 集中 | ✅ | 8 年全符号安定、max year share 0.351、SNB 除外頑健 |
| (iv) サイド split 同符号 | ❌ | flow>0 側 IC **−0.013** vs flow<0 側 **+0.076** — 効果が片側にしか存在しない |
| (v) headroom ≥10x | ✅ | 33.1 (floor RT 感度 79.5) — 週次系は headroom 非拘束の再確認 |
| (vi) レベル中立化 ≥50% | ✅ (knife-edge) | retention **0.502** (境界 0.500 を 0.002 差) |

N=2,479 obs / 414 週 (explore 2014-2021、entry guard skip 23、lookahead assert 全通過)。
p=0.565 は knife-edge 帯 (0.025-0.10) 外 → 3 点検査不要の明快な FAIL。

## 学習事項 (KB)

1. **鏡像恒等の実証**: corr(Δcomm_pct_oi, −Δnoncomm_pct_oi) = **+0.93** — 「commercial は別
   counterparty」という独立性 prior は会計恒等でほぼ無効 (敵対的検証の条件 4 減額が正しかった)。
   COT の comm/noncomm/nonreportable は実質 1.1 モダリティであって 3 ではない
2. **兄弟 family と同じ死型**: cot_spec_extreme (#5) の「点推定 incoherent」と同型の
   サイド非対称 (売り側フローのみ +0.076) — COT ポジショニングの週次予測力は
   レベル極値 (#5) でも flow (#16) でも成立しない
3. **COT モダリティの実質クローズ**: #5 ban (レベル極値) + #16 ban (Δ/flow 全変種、母集団問わず)
   で週次 COT 設計空間はほぼ全域が禁止に。残余 (trader counts / concentration) は
   prior が更に弱く、新 family 申請には strong differential が必要
4. 診断のみ (新規主張ではない): flow<0 側 IC +0.076、年次 IC は 2017 以降に正が偏る —
   いずれも ban スコープ内であり再マイニング禁止

## 同型再試行禁止 (凍結 kill rule どおり)

**スコープ = 「COT ポジショニングの Δ/flow 変換 × 週次固定ホライズン」全変種**
(Δ窓・ホライズン・母集団 (comm/noncomm/nonreportable)・閾値化の別を問わない)。

## 判定の完全性

- 凍結→測定の順序保持 (bc1a3e0a が測定前)。事後の閾値変更・再解釈なし
- OOS 2022+ は COT commercial×価格ジョイント未接触のまま保存
- swap 純額込み headroom、rates ffill 発生 0 件 (explore は rates パネル完全カバー)
