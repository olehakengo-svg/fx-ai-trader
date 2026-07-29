# fx_quote_spread_state (W3-2) explore — ❌ FAIL (2026-07-30)

**凍結プロトコル**: `knowledge-base/wiki/analyses/fx-quote-spread-state-explore-prereg-2026-07-30.md`
(凍結コミット 8618409e → 測定はコミット後。凍結ルールの機械適用、事後変更ゼロ。
注: 凍結コミットは並行セッションの auto KB save と race し、メッセージが混線したが
内容 (ハーネス 2 本 + パネル 42 parquet + prereg doc + 台帳) は完全で測定前に commit 済み)
**Raw**: `knowledge-base/raw/bt-results/fx-quote-spread-state-explore-2026-07-30.json`
**台帳**: #17 (単独 wave m=1、wave-3 敵対的検証 GO-WITH-CONDITIONS の 6 条件解決済み)

## TL;DR

**❌ family FAIL — クローズ、OOS (2022+) 未接触保存。**

| gate | 結果 | 値 |
|---|---|---|
| (i) primary p<0.05 | ❌ | pooled mean 標準化 fwd24h = **−0.237σ** (−9.5p raw)、両側 p=**0.3228** (全ペア同時営業日 circular shift 10k) |
| (ii) magnitude tercile 同符号 | ✅ | [−0.333, −0.369, −0.031] 全て負 |
| (iii) LOYO + 集中 | ✅ | 6 年 (2016-2021) 全符号安定、max year share 0.352、top event 除外 −0.314、SNB 除外 −0.237 |
| (iv) cross-pair coherence | ✅ | 3 ペア全て負 (EUR −0.23 / GBP −0.28 / JPY −0.13)、LOPO 全符号不変 |
| (v) 実現 headroom ≥10x | ✅ | median \|move\| 32.4p / median RT_event 2.14p = **15.1x** (事前ゲート 13.5x の実現側確認) |
| (vi) 年末薄商い ≤50% | ✅ | share 0.308 |

N=65 (検出 69、正常化不能 drop 4)。p=0.323 は knife-edge 帯 (0.025-0.10) 外 →
3 点検査不要の明快な FAIL。**「方向は全ペア・全年で一貫するが、大きさがクラスタ補正 null と
区別できない」— ppp (#14) と同じ弱効果死型。**

## 学習事項 (KB)

1. **デスゾーン防御の定量的正当化 (本 wave の主産物)**: イベント条件付き実測摩擦で、
   onset 即 entry の反実仮想 RT = **EUR 7.25p / GBP 9.47p / JPY 5.87p** vs スプレッド正常化後
   entry の RT ≈ KB baseline (2.0-5.2p)。**スプレッド異常中の執行は摩擦が 2-3 倍** — live の
   デスゾーン gate (動的スプレッド防御) の設計判断を初めて実測で裏付けた
2. **点推定は risk-ON 方向**: 流動性退出の正常化後 24h はペア上昇 (=USD 安/リスク回復) 方向に
   −0.24σ、48h 診断で −0.46σ と伸びるが有意でない。「flight-to-quality 継続」prior は逆 —
   スプレッド正常化はストレス解消の遅行指標である可能性 (診断的解釈、新規主張ではない)
3. **イベント分布の構造**: 2014-2015 はゼロ件 (固定スプレッド様式 feed でイベント定義が構造的に
   不発)、2020-2021 に 42/65 集中 (COVID + tight-feed 期)。BBO feed の regime 構造
   (2014 ~2.3p 固定 → 2019+ sub-pip + crossed 43%) は本パネルの恒久 caveat
4. **MASSIVE /v3/quotes パネルはインフラとして残置**: 3 ペア × 8 スロット/日 × 2013-10〜2026-07
   (78,000 サンプル、valid 98%、`data/external/quote_spread/`)。将来の摩擦研究・execution 分析に
   流用可 (エッジ再マイニングは ban スコープ)

## 同型再試行禁止 (凍結 kill rule どおり)

**スコープ = 「実測 BBO スプレッド状態 (異常オンセット/レベル/正常化) × 時間固定ホライズン fwd
方向」全変種** (閾値・持続定義・ホライズン・ペア・feed の別を問わない)。
デスゾーン防御 (live gate) は本 verdict の影響を受けない (防御用途の正当性はむしろ強化)。

## 判定の完全性

- 凍結→測定の順序保持 (8618409e が測定前)。事後の閾値変更・再解釈なし
- **headroom 事前ゲートは forward return 非接触で執行** (stage 分離コードパス、条件 1 遵守):
  ゲート通過 (13.5x) 後に初めて return grid を構築
- OOS 2022+ はイベント×fwd return ジョイント未接触のまま保存 (パネル自体は取得済み、
  explore 測定は cutoff 2022-01-31 でスライス)
- coverage assert 全通過 (3 ペア × 8 年、最低 0.888 ≥ 0.80)、skip 年ゼロ、事後緩和なし
- swap: 1 晩 rollover 上限 ~1.3p は RT 中央値 2.14p・実現 move 32.4p に対し無視可能水準 (開示のみ)
- 診断 (判定外): fwd 48h −0.457σ / 正常化待ち中央値 9.0h (p90 67.8h wall-clock、週末跨ぎ含む) /
  peak ratio 中央値 7.6x (max 37.9x)
