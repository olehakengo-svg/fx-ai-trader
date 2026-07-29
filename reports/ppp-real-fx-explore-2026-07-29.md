# ppp_real_fx_gap_reversion explore verdict — ❌ FAIL / healthy kill (2026-07-29)

**結論: 凍結 5 条件のうち (i) primary 有意性と (ii) quintile 単調性が不成立 → family クローズ。
OOS 2022+ 未接触保存。台帳 #14 verdict 追記。**

- Protocol (観測前凍結 b037102c): [[ppp-real-fx-explore-prereg-2026-07-29]]
- データ: FRED H.10 + CPI 8 系列 (`data/external/ppp/`、コミット済み・再現可能)
- 測定: `tools/ppp_real_fx_explore.py` (seed 20260729、半期ブロック×同時ペア bootstrap 10,000×、
  lookahead/完全窓/explore 窓 assert 全通過)。Raw: `knowledge-base/raw/bt-results/ppp-real-fx-explore-2026-07-29.json`
- N = 96 月末 × 7 ペア = 672 obs (explore 2014-01〜2021-12)

## 凍結 5 条件の機械適用

| 条件 | 実測 | verdict |
|---|---|---|
| (i) primary IC 42bd p<0.05 | IC **+0.1130**、**p=0.1292** (符号 ✓) | ❌ |
| (ii) quintile 単調 (違反≤1) | 隣接違反 **3** (Q1→Q5: −0.67/−1.20/+0.25/+0.13/−0.36 %)、Q5−Q1 = +0.30% | ❌ |
| (iii) キャリー中立化 ≥50% | 残差 IC +0.1157 = **102.4%** 保持 (z~金利差 r²=0.008) | ✅ |
| (iv) headroom ≥10×RT | Q5 115× / Q1 79× (per-pair 全通過、haircut25 感度不変) | ✅ |
| (v) 単一年集中 <50% | LOYO 最大 2018 の 29.3% | ✅ |

supporting: IC 21bd +0.081 (p=0.158) / 63bd +0.132 (p=0.127) / 非重複 confirmatory +0.126 (p=0.192)。
per-pair: NZD +0.26 / CHF +0.29 / GBP +0.10 / AUD +0.10 / EUR +0.09 / CAD +0.09 / **JPY −0.03**。
年次 IC: 2014 −0.14、2015-2021 は全て正 (+0.07〜+0.44)。

## 解釈 (記録のみ、新規主張なし)

1. **「方向は合うが弱い」型の FAIL** — IC 符号は 8 年中 7 年で回帰方向、キャリー直交・摩擦非拘束。
   しかし効果量が 672 obs (実効独立 ~16 半期ブロック × dollar factor) の検定力で確認できる水準にない。
   文献既知の 2011-2020 value 低迷 + 公表後減衰と整合 — 凍結時の事前宣言どおりの結果
2. **窓の構造的不利**: z>2 が 96 obs に対し z<−2 が 5 obs — explore 窓は USD が自身の 5y 窓に対し
   ほぼ一貫して実質割高 (2014 後半以降の USD 高 regime)。quintile 構成が時期と強く相関し、
   (ii) の非単調はこの偏りと不可分。**「割安側の回帰」は本窓ではほぼ観測不能だった** —
   ただしこれを理由に窓を動かす/条件を緩めることはしない (事後調整の禁止)
3. **スペック解釈の透明性**: 凍結式の記号向きに内部不整合が 1 点あり (S の向き)、測定 agent は
   凍結 doc の意図 (回帰方向・−z 適用) と数値同一の内部整合構成を primary に採用。字面 mix 構成は
   診断併記で **IC +0.084 とさらに弱い** — どちらの解釈でも verdict は FAIL (頑健)

## 再試行スコープ (台帳記録)

- **同型再試行禁止**: 5y rolling z × 月次サンプリング × 21-63bd ホライズンの CPI-PPP 回帰
- 再挑戦経路: (a) **実質金利差込み real FX モデル**等の推定量変更 + 明示差分節、
  (b) 2022+ (USD 割高の解消局面を含む) を explore に含められる将来の split 再設計。
  いずれも観測前 pre-reg 必須

## 台帳への影響

#14 クローズ → アクティブ枠 0/3。残る能動候補 = holiday 縮約版 (背景線、カレンダー検証済み・
凍結待ち)。受動: E7 (08-28) / E1 (10-15) / MoF (Q2+10d) / P-S1(a) (N=8/10)。
