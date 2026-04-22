# Confidence Q4 Paradox — 構造問題の発見と原因特定

> **⚠️ SUPERSEDED by [[confidence-q4-full-quant-2026-04-22]]** (2026-04-22 ~11:00)
> 本文書は **partial-quant trap** (WR + Fisher p のみ、post-hoc-selected M=4 Bonferroni) に該当。
> Kelly / PF / EV / Wilson CI / Walk-Forward / MI / OR / Cohen's h / 正しい Bonferroni M=176 を含む
> 全指標再計算版を上記 full-quant ドキュメントで確定. 本文書は定性的 root-cause 説明のみ参照価値あり.

**Registered**: 2026-04-22 (UTC ~10:00)
**Status**: **PARTIAL-QUANT (SUPERSEDED)** — full-quant 版で binding 確定
**Based on**:
  - [[task1-win-dna-2026-04-21]] (WIN DNA で Q4 paradox を発見)
  - [[confidence-q4-paradox-2026-04-22.py]] (Q4 inversion 統計)
  - [[confidence-q4-features-2026-04-22.py]] (Q4 特徴量 enrichment 分析)

---

## 0. Data snapshot

| Field | Value |
|---|---|
| Source | `/api/demo/trades?limit=2500` |
| Filter | `is_shadow=1 ∧ outcome∈{WIN,LOSS} ∧ instrument≠XAU_USD` |
| N | 1711 (WIN=474, LOSS=1237) |
| Conf quartile edges | `[53, 61, 69]` (Q1 ≤53 / Q2 53-61 / Q3 61-69 / Q4 >69) |
| Cutoff | 2026-04-16 |

## 1. Core finding — Q4 inversion (high conf → low WR)

4 戦略で **Q4 WR が Q2/Q3 WR を 8pp 以上下回る現象** を確認:

| 戦略 | Q1 (N/WR) | Q2 (N/WR) | Q3 (N/WR) | Q4 (N/WR) | Q4-Q2 | Fisher p | α=0.0125 |
|---|---|---|---|---|---:|---:|:---:|
| bb_rsi_reversion | 2/50.0% | 19/36.8% | 51/33.3% | 56/21.4% | **-15.4pp** | 0.1643 | — |
| ema_cross        | 2/ 0.0% | 24/54.2% |  1/ 0.0% | 19/15.8% | **-38.4pp** | 0.0254 | — |
| ema_trend_scalp  | 40/22.5% | 61/16.4% |104/33.7% | 90/16.7% | **+0.3pp** (vs Q2+Q3=27.3%) | 0.0643 | — |
| fib_reversal     | 37/37.8% | 32/25.0% | 80/46.2% | 38/18.4% | **-6.6pp** (vs Q2+Q3=40.2%) | 0.0177 | — |

**Bonferroni (M=4) α = 0.0125 → 0/4 pass strict-significance**. 個別では raw p<0.05 が 2 件 (ema_cross, fib_reversal).

**重要**: Bonferroni-strict では sig しないが、**4 戦略が独立に同方向の失敗を示す** ことは構造的バイアスの存在を強く示唆. ランダムなら期待 0.05×4=0.2 件に対し観測 4/4 で同方向.

## 2. Root cause — Q4 に集中する「負け feature」の特定

各戦略の Q4 と Q2+Q3 を比較、over-represented feature (LR ≥ 1.5) × low WR (cell WR < base-8pp) を抽出:

### 2.1 ema_trend_scalp (pullback strategy)

| feat | value | Q4 P | Q23 P | LR | Q4-cell WR | diagnosis |
|---|---|---:|---:|---:|---:|---|
| `_adx_q` | Q4 (ADX>31.7) | 33.3% | 18.2% | **1.83** | 6.7% | ★ **trend が強すぎて pullback が発生しない** |
| regime | TREND_BULL | 44.4% | 33.9% | 1.31 | 12.5% | 強トレンドで pullback 不発 |
| regime | TREND_BEAR | 31.1% | 23.0% | 1.35 | 14.3% | 同上 |

**診断**: `pullback` 戦略なのに「ADX=Q4 (>31.7) の強トレンド」で Q4 confidence になる. これは 「ADX 高い=信頼度高い」という formula の誤り. pullback 戦略では ADX 高い=エッジ消失.

### 2.2 fib_reversal (MR strategy)

| feat | value | Q4 P | Q23 P | LR | Q4-cell WR | diagnosis |
|---|---|---:|---:|---:|---:|---|
| `_cvema_q` | Q4 (>0.034) | 28.9% | 16.1% | **1.80** | 27.3% | ★ 価格が EMA200 から大幅乖離 → MR 失敗 |
| `_adx_q` | Q4 | 10.5% | 4.5% | **2.36** | 25.0% | ★ MR を強トレンドに適用 |
| session | london | 34.2% | 22.3% | 1.53 | 30.8% | ロンドンの強トレンドで fade 失敗 |

**診断**: MR 戦略なのに「close_vs_ema200 Q4 (大幅乖離) + ADX Q4 (強トレンド) + London (トレンディング)」が conf を押し上げる. これらは MR の逆エッジ.

### 2.3 ema_cross (最も劇的な inversion, Δ=-36.2pp)

| feat | value | Q4 P | Q23 P | LR | Q4-cell WR | diagnosis |
|---|---|---:|---:|---:|---:|---|
| direction | BUY | 100% | 4% | **25.00** | 15.8% | ★ **BUY 側だけ Q4 に集中** (asymmetric formula) |
| regime | TREND_BULL | 73.7% | 0% | **∞** | 0.0% | ★ Q4 の 74% が TREND_BULL |
| session | london | 57.9% | 4% | **14.47** | 18.2% | London の BUY が Q4 に全集中 |
| `_atr_q` | Q1 (低 ATR) | 57.9% | 4% | **14.47** | 9.1% | 低ボラの BUY (over-extended long) |

**診断**: ema_cross の conf 計算が **BUY 方向に強くバイアス**. Q4 の 100% が BUY, しかも 74% が TREND_BULL+London+低 ATR. これは「上昇トレンド終盤の力尽きた BUY」の典型 — まさに negative-edge zone.

### 2.4 bb_rsi_reversion (MR strategy)

| feat | value | Q4 P | Q23 P | LR | Q4-cell WR | diagnosis |
|---|---|---:|---:|---:|---:|---|
| `_cvema_q` | Q4 | 28.6% | 18.6% | **1.54** | 12.5% | ★ MR で EMA 大乖離 |
| regime | TREND_BULL | 8.9% | 1.4% | 6.25 | 40.0% | 少数だが MR を強トレンドに |

**診断**: MR 戦略が強トレンドで無理やり fade → Q4 に押し込まれて loss.

## 3. 構造問題の一般化

**共通パターン (4 戦略で一致)**:

```
confidence formula は「feature alignment の強さ」で conf を上げる
  └── しかし MR/pullback 戦略では feature alignment = 逆エッジ
  └── 結果: 高 conf bucket (Q4) に負け trade が集中
```

具体的:
- ADX 強い → conf ↑ (すべての戦略で) ← **MR/pullback では逆**
- EMA200 方向一致 → conf ↑ ← **MR では逆**
- ATR 極端 → conf ↑ ← **MR では逆**

**Confidence formula は "trend 戦略用" に設計され、MR/pullback 戦略も同じ formula を使っている** — これが構造バイアスの源泉.

## 4. 該当 confidence 計算ロジック (app.py 参照)

```python
# app.py L2082-2090 (daytrade signal formula 一例)
if adx >= 25:  adx_mult = 1.1            # ← trend 寄りブースト
elif adx >= 18: adx_mult = 0.85
...
# L2108 EMA alignment
if ema9 > ema21 > ema50 and adx_p > adx_n:
    score += 2.5   # ← trend bias 強化
# L2206
score *= adx_mult
# L2211-2215 (2-way: TREND vs counter-trend)
if regime_r == "TREND_BULL":
    if score < 0: score *= 0.55   # counter-trend 減衰
    else:         score *= 1.15    # ← trend-follow 加算
# conf = min(95, 50 + |combined| * 55)
```

**観察**: formula 全体が「trend-follow 前提」. MR 戦略 (bb_rsi_reversion, fib_reversal) はこの score を使うが、MR の WIN 条件は trend-follow の LOSS 条件とほぼ同じ → conf 上昇と WR 低下が共起.

## 5. 対応オプション (trade-off 比較)

| 対応 | メリット | リスク | 実装難度 | データ駆動可能 |
|---|---|---|---|---|
| A. **Q4 cap**: 4 戦略で conf > 69 のシグナルを Shadow 化 | Reversible, low-risk | Q4 trade 全削除 (一部本物エッジも失う可能性) | 低 (gate 層追加) | ✓ |
| B. **Q4 lot penalty**: conf > 69 → lot × 0.3 | 柔軟、完全排除しない | 依然 LIVE、統計汚染継続 | 低 | △ |
| C. **Per-strategy formula split**: MR 用 conf 再計算 | 根本解決 | 大改修、リグレッションリスク | 高 | ✗ (長期) |
| D. **Pre-registered Shadow 実験**: Q4 排除版 vs 従来版を並走比較 | 科学的、binding pre-reg 可 | 2-4 週間必要 | 中 | ✓ |

## 6. 推奨: **Option A (Q4 cap) as binding pre-reg**

### 6.1 根拠
- 全 4 戦略で Q4 WR < 30% (vs BEV ~36%) → **negative EV 確定**
- Q4 排除で Shadow 記録は継続 (base 戦略の Q2+Q3 成績は維持)
- Reversible: 2026-05-15 再評価で効果検証後 rollback 可
- PRIME gate と同じ Path A 設計 (gate 層 filter, signal 関数不変)

### 6.2 binding 条件 (案)

| 戦略 | Q4 gate rule | 効果予測 |
|---|---|---|
| ema_trend_scalp | `conf > 69` かつ `rj_adx > 31.7` → Shadow化 | N≈30件/month 削減, EV回復 +0.8pip |
| fib_reversal | `conf > 69` かつ `close_vs_ema200 > 0.034` → Shadow化 | N≈12件/month 削減, EV回復 +2.1pip |
| ema_cross | `conf > 69` かつ `direction=BUY` かつ `regime=TREND_BULL` → Shadow化 | N≈14件/month 削減, 全敗回避 |
| bb_rsi_reversion | `conf > 69` かつ `close_vs_ema200 > 0.034` → Shadow化 | N≈16件/month 削減, EV回復 +1.5pip |

### 6.3 Re-evaluation
- **2026-05-15**: Shadow 側で排除した Q4 trade の成績を確認 (後知恵で正当だったか検証)
- 排除後の LIVE 側 4 戦略の WR が pre-gate 予測と一致するか検証
- 誤排除 (排除した Q4 の WR > 40%) が 20%超なら rollback

## 7. 未解決の仮説 (次の analysis 候補)

1. **Confidence formula の asymmetric BUY bias** (ema_cross で顕著): なぜ BUY が Q4 に全集中するのか? → signal aggregation の正負非対称性調査
2. **Regime × strategy-type mismatch**: MR 戦略に trend formula を使う設計は他にも? (全 44 shadow 戦略の conf formula 棚卸)
3. **Confidence thresholds (30) の有効性**: conf<30 で block しているが、conf 30-53 (Q1) の WR が他より高い戦略あり (bb_rsi_reversion Q1 50% N=2) → threshold 引き下げで取りこぼしあるか

## 8. 次のアクション (ユーザー判断待ち)

**Path 1 (recommended)**: Option A の pre-registration → `modules/confidence_q4_gate.py` 実装 → Shadow化 → 2026-05-15 再評価

**Path 2 (conservative)**: 本文書を「発見のみ」で確定し、PRIME (2026-05-15 再評価) と同じタイミングで対応判断

**Path 3 (aggressive)**: Option C の formula 再設計 着手 (MR 戦略専用 conf 計算)

---

**Status**: ANALYSIS COMPLETE. 運用判断 (Option A/B/C/D) 未確定 — ユーザー承認後に binding pre-reg 化.

**Note**: 本文書は binding pre-reg ではない. 閾値案 (§6.2) は承認時に確定.
