# Raw Price Action Alpha Mining — 生データスキャン結果 (2026-04-12)

**データ**: 3ペア × 60日 × 15m足（yfinance）

---

## 発見されたアルファ #1: Doji Breakout Follow（★★★★★）

### データ統計

| ペア | N | フォローWR | 平均リターン(pip) | ブレイクサイズ(ATR) |
|------|---|----------|-----------------|-------------------|
| **GBP_USD** | **17** | **82.4%** | **+8.51** | 0.96 |
| **USD_JPY** | **29** | **75.9%** | **+7.96** | 0.87 |
| **EUR_USD** | **23** | **65.2%** | **+4.29** | 0.87 |

### ロジック定義
```python
# 条件: 3本連続Doji（body_ratio < 0.20）→ 次足のブレイク方向にフォロー
# 3-bar保持で決済

def doji_breakout_signal(df, i, atr):
    body_ratio = abs(df.Close[i] - df.Open[i]) / max(df.High[i] - df.Low[i], 1e-8)
    body_ratio_1 = abs(df.Close[i-1] - df.Open[i-1]) / max(df.High[i-1] - df.Low[i-1], 1e-8)
    body_ratio_2 = abs(df.Close[i-2] - df.Open[i-2]) / max(df.High[i-2] - df.Low[i-2], 1e-8)
    
    if body_ratio < 0.20 and body_ratio_1 < 0.20 and body_ratio_2 < 0.20:
        # 3連続Doji検出 → 次足のブレイク方向を待つ
        next_bar_direction = df.Close[i+1] - df.Open[i+1]
        break_size = abs(next_bar_direction) / atr
        
        if break_size > 0.5:  # 有意なブレイク(ATR×0.5以上)
            if next_bar_direction > 0:
                return "BUY"   # 陽線ブレイク → BUY
            else:
                return "SELL"  # 陰線ブレイク → SELL
    return None
```

### 摩擦考慮
- GBP_USD: avg_ret=+8.51pip, spread=1.5pip → **ネット+7.01pip** ✓
- USD_JPY: avg_ret=+7.96pip, spread=0.7pip → **ネット+7.26pip** ✓
- EUR_USD: avg_ret=+4.29pip, spread=0.8pip → **ネット+3.49pip** ✓

### 市場心理の裏付け
3連続Dojiは「価格の均衡状態」= 買い圧力と売り圧力が拮抗。この圧縮は
Mandelbrot (1963) のボラティリティクラスタリングの「溜め」フェーズに相当。
均衡が破れた瞬間(ブレイク足)はストップ注文のカスケードトリガーを引き、
3足分(45min)の慣性が発生する。

**WR=75-82%は既存全戦略中最高。BB squeeze breakoutとは異なり、
BBやKCを使わないpure price action検出のため、indicator依存性ゼロ。**

---

## 発見されたアルファ #2: Vol Spike Mean Reversion (USD_JPY限定)（★★★★）

### データ統計

| ペア | N | 3bar反転WR | 反転平均(pip) | フォローWR |
|------|---|----------|-------------|----------|
| **USD_JPY** | **55** | **61.8%** | **+3.84** | 49.1% (慣性なし) |
| EUR_USD | 95 | 52.6% | +0.14 | 35.8% |
| GBP_USD | 89 | 44.9% | -1.73 | 33.7% |

### ロジック定義
```python
# 条件: 直近5本平均レンジの3倍以上の急拡大バー
# → 方向のフォロー(慣性)ではなく、3bar後の反転(平均回帰)にベット
# USD_JPY限定（EUR/GBPでは機能しない）

def vol_spike_reversal(df, i, atr):
    recent_avg_range = np.mean([df.High[j] - df.Low[j] for j in range(i-5, i)])
    current_range = df.High[i] - df.Low[i]
    
    if current_range > recent_avg_range * 3.0:
        spike_direction = "UP" if df.Close[i] > df.Open[i] else "DOWN"
        
        # 反転方向にエントリー（慣性ではなく回帰）
        if spike_direction == "UP":
            return "SELL"  # 大陽線の後に反転SELL
        else:
            return "BUY"   # 大陰線の後に反転BUY
    return None

# SL: spike barの極値 + ATR×0.3
# TP: ATR×1.5 (反転方向)
# Hold: 3 bars (45 min)
```

### 摩擦考慮
- USD_JPY: avg_ret=+3.84pip, spread=0.7pip → **ネット+3.14pip** ✓
- EUR/GBP: 機能しない（反転WR<55%）→ **USD_JPY限定**

### 市場心理の裏付け
USD_JPYでのみ機能する理由: BOJ/日銀の介入示唆と機関投資家の
ストップハンティングが大足を作り、SL約定後に急速に回帰する構造。
EUR/GBPでは大足がトレンド継続(本物のブレイク)である確率が高い。

---

## 発見されなかったもの（アンチパターン）

### ❌ ヒゲ拒否シグナル (A2)
- 下ヒゲ拒否(BUY): USD_JPY WR=43.9%, avg=-1.65pip → **摩擦負け**
- 上ヒゲ拒否(SELL): EUR_USD WR=26.3% → **完全機能不全**
- **結論**: 単一足のヒゲ拒否はノイズ。liquidity_sweepの複合条件が必要。

### ❌ 片側ヒゲ連続 (B2)
- 全ペアでWR=42-46% → ランダム以下
- **結論**: ヒゲ方向の連続はトレンド指標としては機能しない。

### ❌ 大足の慣性フォロー (A1)
- 大陽線後の1bar慣性: USD_JPY WR=52.2%（ほぼランダム）
- 大陰線後の1bar慣性: GBP_USD WR=52.3%（SELL方向、ほぼランダム）
- **結論**: 大足の「慣性」は存在しない。「反転」が正しいパターン（#2で確認）。

---

## タイムアノマリー (C1) — 補足的発見

### EUR_USD UTC 16:00 (t=2.07 ★)
```
N=232, avg_ret=+0.81pip (BUY方向), positive_pct=47.0%
```
London Fix (16:00 GMT) 前後の**Fix前USD買い → Fix後USD売り**パターンと整合。
既存のlondon_fix_reversal戦略を裏付ける独立データ。

### GBP_USD UTC 15:00 (t=-2.05 ★)
```
N=235, avg_ret=-1.48pip (SELL方向), positive_pct=41.3%, negative_pct=51.1%
```
London Fix前の**GBP売り圧力**。Krohn (2024)のW字型パターンと完全一致。
london_fix_reversalのGBP_USDでの正EVを裏付ける独立データ。

### USD_JPY UTC 16:00 (t=-1.84)
```
N=232, avg_ret=-1.09pip (SELL方向)
```
NYセッション中盤のUSD売り圧力。session_time_biasとは逆（東京=BUYだが
NY中盤はSELL方向）。**session_time_biasのNYセッション版？**

---

## 月利100%目標への寄与度

| アルファ | 推定EV/trade | 頻度 | 日次寄与 | 既存戦略との相関 |
|---------|------------|------|---------|---------------|
| Doji Breakout | +7pip(net) | 0.3-0.5t/日 | +2-3pip/日 | 低（BB squeeze/ORBとは別検出） |
| Vol Spike MR (JPY) | +3pip(net) | 0.5-1t/日 | +1.5-3pip/日 | 中（bb_rsiと部分重複？） |
| **合計追加** | | | **+3.5-6pip/日** | |
| **現在DT EV** | | | **+32.4pip/日** | |
| **追加後** | | | **+36-38pip/日（+12-19%改善）** | |

→ DD防御0.5x到達を1-2日加速する効果。月利100%目標に対して**補助的だが正の寄与**。

## Related
- [[edge-pipeline]] — Stage 1: DISCOVERED
- [[roadmap-to-100pct]] — 月利100%目標
- [[microstructure-stop-hunting]] — Vol Spike MRの理論的根拠
