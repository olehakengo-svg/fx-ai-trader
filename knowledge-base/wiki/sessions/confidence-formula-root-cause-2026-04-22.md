# Confidence Formula — Root Cause Audit (病因の特定)

**Registered**: 2026-04-22 (UTC ~12:00)
**Status**: **Root-cause 特定完了 / Option C (formula 再設計) のための Binding 前提**
**Supersedes partial scope of**: [[confidence-q4-full-quant-2026-04-22]] (症状の数学的証明)
**Adds**: コードレベル根本原因、formula 分類、戦略×formula ミスマッチ表

**User requirement (2026-04-22)**: 「Q4 だけでなくそもそものロジックがどうなっているのか、なぜ間違っているのか」
→ 本 audit は症状 (Q4 paradox) でなく **病因 (confidence 計算ロジック本体)** を定量・定性的に解剖.

---

## 0. 要旨 (Executive summary)

問題戦略 4 つは異なる **3 種類の confidence 公式** を使っているが、すべて以下の同一の構造的欠陥を持つ:

```
conf = f(feature_magnitude, direction_alignment)
     ← strategy_type (trend / MR / pullback) に依存しない
     ← edge_sign (features が EV+ か EV- か) に依存しない
```

**核心的誤り**: *confidence は "feature alignment の強さ" を測っている. これは trend-follow 戦略では EV proxy として正しいが, MR/pullback 戦略では **逆エッジ指標** (alignment 強 ⇒ reversion 失敗確率 高).*

全 4 戦略で Q4 が PF/EV/Kelly 最悪になる ([[confidence-q4-full-quant-2026-04-22]] §2) のは、この formula-strategy ミスマッチの **数学的必然**.

## 1. Confidence 公式の解剖 — 4 戦略の formula を逐条分析

### 1.1 bb_rsi_reversion (scalp/MR) — `strategies/scalp/bb_rsi.py:L209`

```python
conf = int(min(85, 50 + score * 4))
```

`score` の内訳 (BUY 側):

| 構成要素 | 加算 | 方向性 | MR エッジとの整合 |
|---|---:|:-:|:-:|
| base (tier1 / tier2) | 3.0 / 4.5 | neutral | ✓ |
| `(38 - rsi5) * 0.06` | +0〜1.1 | 過売り深さ | ✓ (MR 順向き) |
| Stoch gap | +0.3〜0.6 | 反転開始 | ✓ |
| 前バー陰線 | +0.3 | MR setup 整合 | ✓ |
| MACD > 0 | +0.5 | **momentum 方向** | **✗ MR 逆エッジ** |
| MACD-H 反転上昇 | +0.6 | momentum 消耗 | ✓ |
| **USD/JPY × ADX≥30** | **+0.6** | **強トレンド** | **✗ MR 逆エッジ** |
| Gold Hours | +0.8 | 時間統計 | ✓ (独立) |

**逆エッジ要素: `MACD>0` + `ADX≥30` = 最大 +1.1 score ≈ +4.4 conf**.
USD/JPY の tier1 BUY trade で、Gold Hour + MACD+ + ADX≥30 + MACD-H 反転が全て揃うと:
```
score = 4.5 + 0.8 + 0.6 + 0.5 + 0.6 = 7.0 → conf = min(85, 50 + 28) = 78 (Q4)
```
このうち **+4.4 conf (1.1 score) が trend-follow features**. MR strategy なのに conf が trend 強度で決まる.

### 1.2 fib_reversal (scalp/pullback-MR hybrid) — `strategies/scalp/fib.py:L201`

```python
conf = int(min(85, 45 + score * 5))  # ← 最大勾配 5pt/unit
```

| 構成要素 | 加算 | 方向性 | fib エッジとの整合 |
|---|---:|:-:|:-:|
| base | 3.5 | neutral | ✓ |
| Fib 61.8% bonus | +0.8 | **"最強ゾーン"** | △ (BT WR 高だが Q4 で逆転) |
| Fib 50% | +0.5 | 中間 | ✓ |
| RSI 過熱 | +0.5 | MR 順向き | ✓ |
| 陽線 + body≥60% | +0.3 | 反転確認 | ✓ |
| **MACD-H 反転** | **+0.4 (+ 必須化 v8.3)** | **momentum 変化** | **△ trend continuation 前兆も該当** |

**最大勾配 5pt/unit が致命的**: score 5.0 → conf 70 (Q4 境界). Fib 61.8% + MACD反転 + RSI過熱 + 陽線 + base 3.5 = 5.5 → conf 72.5. **Q4 に入るのが構造的に容易**.

さらに app.py L8173 で fib_reversal は **`_mean_reversion_types` に含まれていない** → HTF trend 逆行で `conf *= 0.85` 減衰が適用される. これは **MR の最強エッジ (HTF 逆張り反発) を逆ペナルティ** する構造.

### 1.3 ema_trend_scalp (scalp/pullback) — `strategies/scalp/ema_trend_scalp.py:L242`

```python
conf = int(min(85, 50 + score * 4))
```

score は base 3.0 + **10 以上の加算項** (+0.3〜+0.5 each, L201-233):

| 代表的な加算項 | 加算 | 方向性 |
|---|---:|:-:|
| base | 3.0 | neutral |
| EMA 整合 × N | +0.5 ×3 | **trend 方向** |
| ADX 強度 | +0.4 ×2 | **強トレンド** |
| HTF 整合 | +0.3 | trend-follow |
| 複数 EMA 傾き | +0.3 ×3 | trend continuation |

**加算項の 70% 以上が "trend-follow 強化" 要素**. Pullback strategy の定義上、必要なのは "軽度 trend + 深い pullback" だが、formula は "**強い trend + 順方向**" を高スコアにする. これは pullback 戦略の **逆エッジ** (強トレンド中は pullback が発生しない / 浅い再押し上げ後に trend 継続).

score 6+ で conf > 74 (Q4 深部) に容易に到達.

### 1.4 ema_cross (daytrade) — 二重の問題

Strategy 自体の conf (`strategies/daytrade/ema_cross.py:L242`):
```python
conf = int(min(80, 45 + score * 4))  # score = 3.5 + adx_bonus(max 0.8)
# → strategy 単体で max conf = 45 + 4.3*4 = 62.2
```

**しかし**: `compute_daytrade_signal` (app.py:L2497-2772) で **DTE の conf は破棄される**:
```python
# L2497
if _dt_best:
    signal = _dt_best.signal
    _dt_entry_type = _dt_best.entry_type
    score += _dt_best.score * 0.5  # ← score のみ継承, confidence は使わない
# L2729-2772
if signal != "WAIT":
    base_conf = 50
    base_conf += int(sr_strength * 15)        # SR bonus max +20
    ema_boost = int(np.clip(ema_score * 8, -15, 15))  # ema 整合 max +15
    if signal=="BUY" and ema9>ema21>ema50:  ema_boost += 5  # trend 順向き
    if signal=="BUY" and macdh>0 and rising: ema_boost += 3  # momentum
    if signal=="BUY" and vwap_dev>0:         ema_boost += 3  # VWAP 乖離
    conf = int(np.clip(base_conf + ema_boost, 25, 92))
```

**構造問題** (ema_cross 特有):
1. Strategy のバランスされた conf (max 62) が **daytrade 層で上書き** される
2. Daytrade 層 formula は 純粋 trend-follow: EMA 整合 + MACD + VWAP 全て一致で conf=85+
3. TREND_BULL + BUY で全要素が同方向 → **asymmetric BUY bias** ([[confidence-q4-full-quant-2026-04-22]] §6 で Fisher p<0.0001 で確認済み)
4. SELL 側は `ema9<ema21<ema50` が TREND_BULL で発生せず → SELL が Q4 に入らない → Q4 の 100% が BUY に

## 2. 戦略 × Formula × Edge 整合性マトリクス

| 戦略 | Formula 層 | Formula slope | score feature のうち trend-follow 寄与率 | 戦略タイプ | 整合? |
|---|---|---:|---:|---|:-:|
| bb_rsi_reversion | scalp (own) | 4/unit | **~25%** (MACD+, ADX≥30) | MR | **✗** |
| fib_reversal | scalp (own) | **5/unit** | **~30%** (MACD反転, Fib61.8) | MR/pullback | **✗** |
| ema_trend_scalp | scalp (own) | 4/unit | **~70%** (EMA, ADX, HTF) | pullback | **✗** (加算過多) |
| ema_cross | daytrade (override) | 8/unit* | **~80%** (ema_score, EMA, MACD, VWAP) | trend-follow | △ (trend には整合だが BUY asymm) |

*ema_cross は `base_conf + ema_boost` の複合で実効勾配が 8pt/score-unit に達する.

**結論**: **Trend-follow 戦略 1 本のための formula が 3 つの異なる戦略型に適用されている**. MR / pullback には構造的に逆エッジ.

## 3. 公式の数学的定式化 — なぜ Q4 paradox が必然か

### 3.1 現行 formula (4 戦略共通構造)

```
conf(x) = a + b · S(x)
S(x)   = Σᵢ wᵢ · fᵢ(x)     where fᵢ ∈ {EMA整合, ADX, MACD方向, VWAP, Fib, RSI極端, ...}
```

ここで `wᵢ > 0` すべて、`fᵢ` は「feature alignment の度合い」.

### 3.2 戦略タイプ別の真の EV 関数

Trend-follow 戦略:
```
EV_trend(x) ≈ α_T + β_T · (EMA整合) + γ_T · ADX - δ_T · |EMA200乖離|
             (全係数 > 0)
→ ∂EV_trend/∂S > 0  ⇒  conf ↑ と EV ↑ が共起 (正しい)
```

MR 戦略:
```
EV_MR(x) ≈ α_M - β_M · (EMA整合) - γ_M · ADX + δ_M · |EMA乖離|·(EMA乖離が極端な時のみ)
          (β_M, γ_M > 0 = 逆エッジ係数)
→ ∂EV_MR/∂(EMA整合) < 0,  ∂EV_MR/∂ADX < 0
→ conf ↑ と EV ↓ が共起 (Q4 paradox の数学的正体)
```

Pullback 戦略:
```
EV_pb(x) ≈ α_P + β_P · (軽度 trend) - γ_P · (強度 trend)²
          (非単調: 中程度 trend で極大)
→ conf は単調増、EV は非単調 → 強トレンドで divergence (同 Q4 paradox)
```

### 3.3 必然的結論

**同じ増加関数 conf = a + b·S(x) を 3 種類の異なる EV 関数に適用している**. MR と pullback では conf と EV の相関が部分的に **負** になるのは数学的必然であり、Q4 paradox は formula のバグでなく **設計の根本的誤り** (model misspecification).

## 4. 歴史的経緯 — なぜこの設計になったか

コードコメント・commit 履歴から推定 (根拠):
- `compute_daytrade_signal` (L1992-) は元々 **trend-follow 単一戦略** として設計 (2025Q4)
- DaytradeEngine (L2438) で **複数戦略 plug-in** 化 (2026-02-03, `strategies/daytrade/` 分離)
- しかし conf 計算 (L2727-2772) は trend-follow 前提のまま残存 → DTE 戦略の Candidate.confidence が **無視される回路** になった
- Scalp 側 (L7928-) も同様: 複数戦略の中で個別 formula を持たせたが、MR と pullback で **同じ additive score→conf 写像** を使い続けた
- `_mean_reversion_types` リスト (L8135) は MR 戦略への HTF/EMA200 ペナルティ免除を実装しているが、**conf 計算自体は変更されない**. しかも fib_reversal, ema_trend_scalp はこのリストに入っていない.

## 5. 修正設計 — Option C (formula 再設計) の具体化

### 5.1 Design principle

**"Feature score" と "Strategy-specific confidence" を 2 層化**:

```python
# Layer 1: 純粋な signal strength (direction-agnostic, strategy-agnostic)
raw_score = Σ wᵢ · fᵢ(x)                     # 従来どおり

# Layer 2: 戦略タイプ依存の conf mapping
conf = g_τ(raw_score, context)                # τ ∈ {trend, MR, pullback}
```

`g_τ` は戦略タイプごとに分離:

```python
def conf_trend(s, ctx):      return clip(50 + s*4, 25, 92)
def conf_MR(s, ctx):
    # raw_score が大き過ぎる (= trend 機能) なら減点
    anti_trend = max(0, ctx.adx - 25) * 2     # ADX>25 でペナルティ
    return clip(50 + s*4 - anti_trend, 25, 85)
def conf_pullback(s, ctx):
    # 強トレンドだけ減点 (中程度は許容)
    over_trend = max(0, ctx.adx - 31) * 3     # ADX>31 で急ペナルティ
    return clip(50 + s*4 - over_trend, 25, 85)
```

### 5.2 設計の根拠 (full-quant 結果から)

- ADX≥31.7 (_adx_q=Q4) で MR / pullback 4 戦略すべて WR<25% ([[confidence-q4-full-quant-2026-04-22]] §1)
- bb_rsi_reversion の USD/JPY ADX≥30 bonus (+0.6) は既存 BT で WR=60% を根拠としているが、これは ADX 25-35 の帯域データ. ADX>35 では機能しない (Q4 Kelly=-46.9% が裏付け)
- Wilson 95% 上限 < BEV が **4 戦略すべての Q4 cell で成立** → Kelly-negative が統計的に確定

### 5.3 実装方針

2 段階:
- **Phase 1 (即時可能)**: `modules/confidence_q4_gate.py` (Option A) で gate 層フィルター
  - 根本修正でないが reversible・安全・effect size 既知 (+572 pip/month)
- **Phase 2 (中期)**: `strategies/base.py` に `strategy_type` 属性追加, conf 計算を `g_τ` 分離
  - `StrategyBase.strategy_type: Literal["trend", "MR", "pullback"]`
  - 各 strategy module で `conf = self._conf_mapper(score, ctx)` (default = trend)
  - MR/pullback strategies は override

### 5.4 検証プロトコル (Phase 2 実装時)

Pre-merge criteria:
1. **Shadow backtest (WF split)**: pre-Cutoff データで formula 再設計、post-Cutoff で検証
2. **Per-strategy Kelly 改善**: 4 戦略すべての Q4 cell で Kelly_full → ≥ 0 (または N 半減)
3. **Bonferroni-176 有意性**: 少なくとも ema_cross (raw p=0.0127) が strict pass
4. **Regression**: 他の 40 戦略の Q1-Q3 PF/EV が悪化しない (±5% 以内)

## 6. リスクと制約

### 6.1 Phase 1 (Q4 gate) のリスク
- **Shadow 観測期間 ~1ヶ月** — WF で 3/4 が両期間再現だが ema_cross は post-Cutoff N=1 で判定不能
- **誤排除**: Shadow Q4 の実 Kelly が意外にも ≥0 になる可能性 — 2026-05-15 検証で rollback 判定

### 6.2 Phase 2 (formula 再設計) のリスク
- 既存戦略の conf 分布変化 → PRIME gate (prereg-6-prime) の conf 閾値 (53/61/69) が **再チューニング必要**
- BT-Live 乖離が再発する可能性 (本番データ分布の前提変化)
- 回帰リスク: 40 戦略への副作用

## 7. 推奨

**Path 1 (推奨)**: Phase 1 即時 + Phase 2 は 2 週間の Phase 1 観測後に再評価
- Phase 1: `confidence_q4_gate.py` 実装 (30分) → Shadow 化 → +572 pip/month 救済
- 2026-05-06 Phase 1 中間レビュー: 誤排除率確認
- 2026-05-15 Phase 1 正式評価 → Phase 2 GO/NOGO 決定

**Path 2 (保守)**: Phase 1 のみ実装し、Phase 2 は見送り (formula 欠陥を許容、gate でマスク)

**Path 3 (攻め)**: Phase 2 を先に実装 (Phase 1 をスキップ)
- リスク: 40 戦略の conf 分布変化を一度に評価するのは困難
- 非推奨

## 8. Changelog from partial-quant → full-quant → root-cause

| 版 | 日時 | スコープ | 主要欠陥 |
|---|---|---|---|
| v1: [[confidence-q4-paradox-2026-04-22]] | 2026-04-22 10:00 | WR + Fisher p | post-hoc M=4 Bonferroni (不正) |
| v2: [[confidence-q4-full-quant-2026-04-22]] | 2026-04-22 11:00 | Kelly/PF/EV/WF/MI/OR (症状の完全統計化) | formula 本体未読解 |
| **v3: 本文書** | 2026-04-22 12:00 | **code-level 病因 + formula 分類 + Option C 設計** | **(現在)** |

---

**Status**: ROOT CAUSE IDENTIFIED.
- § 1 Formula 逐条分析: ✓ (4 戦略、3 実装層)
- § 2 戦略×Formula マトリクス: ✓
- § 3 数学的定式化 (∂EV/∂S の符号): ✓
- § 5 Option C 2-phase 設計: ✓

**Note**: v3 ドキュメントは Option C (formula 再設計) の binding 前提. 数学的 EV モデル (§3.2) は各戦略タイプの真の EV 関数を示しており、この符号に基づいて `g_τ` が設計される. ユーザー承認後 Phase 1 `confidence_q4_gate.py` 実装に移行可.
