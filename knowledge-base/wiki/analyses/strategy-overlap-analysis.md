# 戦略重複・固有性分析 (2026-04-15)

## 結論: 「同じ仮説の後継」と片付けた戦略は、実はそれぞれ固有のエッジメカニズムを持つ

---

## Group 1: トレンドプルバック（4戦略）

### 完全重複ペア: なし

| 戦略 | 固有メカニズム | 他にない要素 |
|---|---|---|
| ema_ribbon_ride | 時間帯セッション重み付け(12-17UTC) + BB幅パーセンタイル + DI gap | ロンドン/NY重複窓の明示的な有利時間帯ブースト |
| adx_trend_continuation | 2本バー時系列分離（過去にPBを確認→現在バウンスを確認） | 唯一の「PBとバウンスを別バーで検出」する時間構造 |
| ema_pullback | 3重必須確認ゲート（MACD-H AND Stoch AND body ratio） | 最高選択性。全条件必須でフィルター品質最大 |
| stoch_trend_pullback | Stochastic中心。EMA近接距離制約なし | 深いプルバック（EMA9を大きく超えて戻った場合）を捕捉 |

### 同時発火の可能性
- ema_ribbon_ride × stoch_trend_pullback: **高い**（同じバーで発火可能）
- ema_pullback × stoch_trend_pullback: **ema_pullbackはstoch_trendの部分集合**
- adx_trend_continuation: **他と分離**（DTモード + EUR限定 + 時間構造が異なる）

### 「後継があるから不要」の修正

```
旧判断: ema_ribbon_ride は adx_trend_continuation の後継 → 不要
修正:   ema_ribbon_ride のセッション重み付けとBB幅フィルターは
        adx_trend_continuation にはない。
        ただし1m TFでの摩擦死亡は事実（TP=2-4pip vs 摩擦=2-4pip）。
        → 15m DTで再実装すればセッション重み付きプルバックとして固有の価値
```

---

## Group 2: 平均回帰（6戦略）

### 完全重複ペア: bb_rsi_reversion ≈ dt_bb_rsi_mr（最も近い）

| 戦略 | 「エクストリーム」の定義 | 固有メカニズム |
|---|---|---|
| bb_rsi_reversion | BB%B ≤ 0.30 + RSI5 | **JPYレジーム分離**（JPY: ADX上限なし、EUR: ADX<25） |
| dt_bb_rsi_mr | BB%B ≤ 0.30 + RSI14 + ADX<25 | **BBスクイーズペナルティ**（幅<15%で減点） |
| fib_reversal | Fib 38.2/50/61.8%水準 | **スイング構造由来のレベル**（統計バンドではない） |
| macdh_reversal | BB%B < 0.30 + MACD-Hピーク反転 | **モメンタム枯渇の2バーパターン**（他より1バー早い検出） |
| vwap_mean_reversion | VWAP-2σ偏差 | **セッション内フェアバリュー**（Massive API固有） |
| engulfing_bb | BB%B < 0.30 + 包み足パターン | **プライスアクションパターン確認**（唯一のローソク足構造依存） |

### 「数学的に同じオブジェクト」を使う戦略
- bb_rsi / dt_bb_rsi_mr / macdh_reversal / engulfing_bb: **全てBB%B < 0.30が主条件**
- しかし確認メカニズムが全て異なる（RSI vs MACD-H peak vs engulfing candle）
- **fib_reversal**: 完全に独立（Fibonacci retracement level）
- **vwap_mean_reversion**: 完全に独立（VWAP偏差）

### 重要発見: macdh_reversalは「他より1バー早く検出」
```
bb_rsi_reversion: RSI5が反転確認 → 反転後1-2バーで検出
macdh_reversal: MACD-Hのピーク反転 → 反転の瞬間に検出（prev2>=prev1<current）
→ macdh_reversalは理論上、bb_rsi_reversionより1-2バー早いエントリー
→ 1mではこの1-2バー（1-2分）がスプレッドに食われて意味がない
→ 5m/15mでは1-2バー（5-30分）の差が有意になる可能性
```

---

## Group 3: SR/ブレイクアウト（5戦略）

### SR検出方法が完全に異なる

| 戦略 | SR検出方法 | エントリー方向 |
|---|---|---|
| sr_fib_confluence | layer3パイプラインの文字列パース | バウンス（MR） |
| dt_fib_reversal | 80本スイングからFib水準を独自計算 | バウンス（MR） |
| sr_break_retest | Williams Fractalクラスタリング | **ブレイク後リテスト（TF）** |
| sr_channel_reversal | 外部sr_levels + 平行チャネル | バウンス（MR） |
| bb_squeeze_breakout | BB幅パーセンタイル（SR不使用） | **ブレイクアウト（Momentum）** |

### sr_fib_confluenceとdt_fib_reversalの関係
```
sr_fib_confluence: dt_fib_reversalの出力を読んで再確認する「メタ戦略」
  → layer3["dt_reasons"]に"Fib"文字列があるか？
  → dt_fib_reversalが出力した理由を再チェック + EMAスコアゲート追加

つまり: sr_fib_confluence ⊂ dt_fib_reversal の発火条件
  dt_fib_reversalが発火 → sr_fib_confluenceも発火可能
  sr_fib_confluenceのEMAスコアゲートが追加フィルター

結論: sr_fib_confluenceはdt_fib_reversalの「品質フィルター版」
      ただし文字列パース依存は構造的欠陥
      → dt_fib_reversalにEMAスコアゲートを直接追加すれば統合可能
```

---

## 復活可能性の修正版

### ema_ribbon_ride: 「不要」→「15m DTでセッション重みを活かせば固有価値」

```
旧: adx_trend_continuationが後継 → 不要
新: adx_trend_continuationにはセッション重みもBB幅フィルターもない
    15m DTで再実装すれば、London/NYセッション重み付きプルバックとして
    adx_trend_continuationと共存可能
    
提案: ema_ribbon_rideの時間帯ブーストロジック(12-17UTC +1.0)を
     adx_trend_continuationに移植するのが最も効率的
     → 新戦略ではなく既存戦略の強化
```

### macdh_reversal: 「理論正しいがTF間違い」→「5mで早期検出の固有価値」

```
旧: bb_rsi_reversionと同じBB%B条件 → 冗長
新: macdh_reversalは他より1-2バー早くモメンタム枯渇を検出
    1mでは1-2分の差がスプレッドに食われて無意味
    5m/15mでは5-30分の差が有意
    
提案: 5m EUR_JPY/GBP_JPYでTier1(BB%B<0.15)限定テスト
     180日BTデータ: EUR_JPY 5m N=5 EV=+0.452, GBP_JPY 5m N=9 EV=+0.219
     → N不足だがSHADOWでデータ蓄積開始
```

### sr_fib_confluence: 「再設計必要」→「dt_fib_reversalにEMAスコアゲート移植」

```
旧: 文字列パースの構造的欠陥 → 復活不可能
新: sr_fib_confluenceの「固有価値」はEMAスコアゲート(0.28閾値)
    このゲートをdt_fib_reversalに直接追加すれば、
    文字列パースなしで同等の品質フィルターが実現
    
提案: dt_fib_reversalのエントリー条件に
     EMAスコア >= 0.28 を追加オプションとしてBTテスト
     → sr_fib_confluenceは削除、dt_fib_reversalが統合版になる
```

## Related
- [[force-demoted-decomposition]] — 12戦略因数分解
- [[eur-scalp-regime-analysis]] — rawエッジと実装の分離
- [[bt-live-divergence]] — 6つのBTバイアス
