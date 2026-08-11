# holiday_liquidity_state_family 縮約版 explore + OOS — ❌ family FAIL (2026-07-29)

**凍結プロトコル**: `knowledge-base/wiki/analyses/holiday-liquidity-explore-prereg-2026-07-29.md`
(凍結コミット 3ad0cb18 → 測定はコミット後。凍結ルールの機械適用、事後変更ゼロ)
**Raw**: `knowledge-base/raw/bt-results/holiday-liquidity-explore-2026-07-29.json`
**台帳**: #15 (背景線、BH 分母 family 内独立)

## TL;DR

| レグ | ステージ | 結果 | 死因 |
|---|---|---|---|
| (c) 米休場翌営業日反転 | explore | ❌ **FAIL (kill)** | **符号が凍結仮説と逆** — 薄場ムーブは反転せず**継続** (pooled −7.61p、片側 p=0.973)。LOYO 7/7 で継続方向に一貫 |
| (a) pre-holiday risk-tilt | explore | ✅ PASS (両側 p=0.0163、+7.89p、headroom 11.24、LOYO 7/7) | — |
| (a) 同上 | **OOS (単一接触)** | ❌ **FAIL** | 効果 74% 崩壊 (+7.89p → +2.06p)、片側 p=0.3145 (閾 0.10)、最小効果 2.06<5.0p、**LOYO 符号不安定** (2025 除外で −0.05) |

**family verdict: ❌ FAIL — クローズ。** 事前宣言 (「FAIL が既定路線」) どおりの healthy kill。
explore の見かけの効果 (p=0.016, 7 年 LOYO 安定) が OOS で消滅 = OOS 規律が設計どおり機能した。

## 詳細 — explore (2014-2020)

### レグ (a) pre-holiday risk-tilt basket (両側)
- N=545 obs / 74 月ブロック (US eve 55×8 ペア + JP eve 76×JPY 2 ペア、overlap 8 除外、EUR_JPY は 2016-04+ 部分参加)
- pooled mean **+7.89p** (+ = safer 通貨高 = リスクオフ方向)、両側 permutation p=**0.0163** (BH 閾 0.05 ✓)
- gates: 最小効果 7.89≥5 ✓ / headroom 11.24≥10 ✓ (floor RT 感度 25.08) / LOYO 7/7 符号安定 ✓ / knife-edge 帯 (0.025-0.10) 外
- 分解 (診断): JP eve +13.2p > US eve +6.3p。per-pair は 6/8 正 (USD_CHF −4.6 = CHF は
  リスクオフに参加せず、実態は「JPY・USD 高 vs 欧州・コモディティ通貨」)。backfill 2 窓除外で +7.75p (頑健)。
  eve 日レンジ比 1.043 = **eve 日は薄くない** (機構前提の「流動性薄化」は range には現れない)

### レグ (c) 米休場翌営業日反転 (片側、dir=−sign(休場日リターン))
- N=397 obs / 50 月ブロック (63 休場日、バー存在 + R_H≠0 条件)
- pooled mean **−7.61p** (反転方向に負 = **継続**)、片側 p=0.973 → BH ✗ → kill
- 記述ノート (新規主張ではない): 継続は LOYO 7/7 で一貫、週末跨ぎ (Good Friday) では −0.68p とほぼ消失、
  非跨ぎで −9.23p。**事後の符号反転による「継続 family」再登録は同型再試行禁止スコープ内**
  (祝日フラグ×日次 exit-free) — この観測はすでに explore データに接触しており、pre-reg 資格を失っている

## 詳細 — OOS (2021-2026、レグ a のみ単一接触、explore 符号 + に固定・片側、m=1)

- N=508 obs / 63 月ブロック (111 イベント、overlap 6 除外)
- pooled mean **+2.06p**、片側 p=**0.3145** (閾 0.10 ✗)
- 最小効果 2.06 < 5.0 ✗ / headroom 13.61 ✓ / **LOYO ✗** (2025 除外 −0.05、2023-24 は負寄与 =
  年次 regime 交替でエッジ不在)

## 判定の完全性

- 凍結→測定の順序保持 (凍結コミット 3ad0cb18 が測定前)
- 事後の閾値変更・ホライズン切替・sub-threshold 再解釈なし。レグ c の逆符号は機械 kill
- OOS はレグ a のみ接触。**レグ c の OOS は未接触のまま保存** (ただし同型再試行は禁止)
- 実装バグ修正 1 件 (permutation block key の numpy 2D 化 → 整数エンコード) — プロトコル定義に変更なし

## 同型再試行禁止 (凍結 kill rule どおり)

**スコープ = 「祝日/休場カレンダーフラグ × 日次 (D1-D2) exit-free ホライズン」全て** —
方向規約 (basket/継続/反転)・集団 (US/JP/eve/翌日) の変種を含む。再挑戦は新モダリティ
(intraday マイクロストラクチャ等) + 明示差分節 + 新 family 登録のみ。

## 学習事項 (KB)

1. **explore 通過品質は OOS 生存を予測しない** (p=0.016 + LOYO 7/7 → OOS p=0.31) —
   postmortem §2 の OOS-fail/winner's curse 系 (12 件目 → 13 件目) と同型
2. **「87 本中唯一の未踏フラグ空間」も無料日次×カレンダー系の期待値較正 (wave-1/2) を覆さなかった** —
   処方箋「非価格モダリティへ」を再確認する追加データ点
3. 休場日の薄場ムーブは「情報含有が低く反転する」のではなく**継続する** (記述所見) —
   thin-market reversion prior は FX 日次では棄却方向
