# TP-hit Deep Mining — Grail Sentinel 投入 + bb_rsi 緊急トリップ (2026-04-25)

## 背景

2026-04-25 セッションで TP-hit 全件 (Live + Shadow + FORCE_DEMOTED 含む) の
4 次元クロス集計 (戦略 × ペア × セッション × Regime) を実施.

母集合: 3271 closed trades (XAU除外, 23日, post-cutoff Apr-02〜Apr-24),
TP-hit 712 件 (TP_HIT 600 + OANDA_SL_TP+ 112).

Live OANDA 送信は 126 件のみ (17.7%) で、内訳:
- bb_rsi_reversion: 76 件 (60.3%) → **単一戦略集中リスク**
- vwap_mean_reversion: trip 済 (4/24)
- vol_surge_detector: 20 件
- trend_rebound: 4 件

## Step 1 主要発見

### 1.1 真アルファ (Wilson_lo ≥ 30%, EV>0): 4 cluster のみ

| # | Strategy × Pair × Session × Regime | N/All | Wlo% | EV | PF | L/S |
|---|---|---|---|---|---|---|
| 1 | vol_surge_detector × USD_JPY × NY × TREND_BEAR | 5/7 | 35.9 | +1.10 | 2.13 | 5/0 |
| 2 | vol_surge_detector × USD_JPY × London × TREND_BEAR | 8/14 | 32.6 | +5.79 | 4.62 | 4/4 |
| 3 | ema200_trend_reversal × USD_JPY × NY × RANGE | 6/10 | 31.3 | +5.83 | 3.79 | **0/6** |
| 4 | ny_close_reversal × USD_JPY × NY × RANGE | 4/4 | 51.0 | +2.15 | 4.58 | **0/4** |

### 1.2 EV負の主役: bb_rsi_reversion × USD_JPY × RANGE

- N=217 closed (TP=70 / SL=111 / Other=36)
- TP-rate **32.3%** (Wilson_lo 26.4%)
- EV **-0.58p**, PF **0.75**
- AvgWin **+4.24p** / AvgLoss **-3.94p** (W:L 1.08)
- TP距離 4.92p, SL距離 4.27p (RR **1.17**)
- **Break-even WR 必要値 48.1%** ← 実測 32.3% で構造的 EV 負

## Step 2 Edge Attribution

### 2A. vol_surge_detector × USD_JPY × TREND_BEAR (London+NY) アルファ正体

| 指標 | TP組 (n=13) | SL組 (n=8) |
|---|---|---|
| MAFE_fav (順行最大) | 9.84p (med 6.20) | 0.76p (med 0.30) |
| MAFE_adv (逆行最大) | 2.36p (med 2.30) | 3.65p (med 3.30) |
| Hold (min) | 6.4 (med 4.0) | 3.85 (med 1.36) |
| **即時順行率** | **13/13 = 100%** | **0/8 = 0%** |

エッジ正体: **エントリー直後の即時順行が完全二値分離変数**.
SL 組は 100% が最初に逆行して中央値 1.4分で即SL, TP 組は 100% が最初から順行.
摩擦コスト (spread 0.8p) を MAFE_fav 9.84p で 12.3 倍カバー.

### 2B. bb_rsi_reversion × USD_JPY × RANGE — 構造病理

- 平均回帰仮説は機能 (TP-rate 32% > random 25%) だが RR 1.17 設定が WR を救えない
- スリッページ: SL 約定率 92% (深く約定) > TP 約定率 86% (届かず時間切れ撤退)
- TIME_DECAY_EXIT 36件 (16.6%) = TP 届かず撤退
- 「利＝損」構造: AvgWin (+4.24) ≈ |AvgLoss| (-3.94)

処方箋: **RR 1.5 拡張** で TP-rate 32% でも EV+ 化を BT 365日で検証 (別 pre-reg).

## Step 3 Shadow Grails (41 cluster, EV>0 Wlo>10%)

### 共通シグニチャ

上位 5 grail のうち **4 つが mtf_regime=range_tight + mtf_vol_state=squeeze**.
MTF gate の `conflict` 降格が、本来は squeeze→expansion ブレイク予兆だった
可能性を示唆 (= 未発掘の "Squeeze Paradox").

### 投入対象 4 grail

| # | Strategy | Pair | Session | Regime | N | Wlo% | EV | PF | NLive |
|---|---|---|---|---|---|---|---|---|---|
| #5 | ema200_trend_reversal | USD_JPY | NY | RANGE | 8 | **40.9** | **+9.40** | **19.80** | 2 |
| #4 | vol_surge_detector | USD_JPY | London | TREND_BEAR | 7 | 25.0 | +9.51 | 6.05 | 7 |
| #2 | vix_carry_unwind | USD_JPY | London | TREND_BEAR | 4 | 15.0 | +11.12 | 2.99 | 1 |
| #19 | ny_close_reversal | USD_JPY | NY | RANGE | 4 | 51.0 | +2.15 | 4.58 | 0 |

## 適用パッチ

### Patch A — bb_rsi_reversion 緊急トリップ

```python
# modules/demo_trader.py:4296+
_BB_RSI_OANDA_TRIP = _os.environ.get("BB_RSI_OANDA_TRIP", "1") == "1"
if _BB_RSI_OANDA_TRIP and entry_type == "bb_rsi_reversion":
    if not _is_shadow:
        _is_shadow = True
        _is_promoted = False
        _shadow_at_open = True
        self._add_log("[EMERGENCY_TRIP] bb_rsi_reversion OANDA 送信停止 ...")
```

- Shadow 経路は継続 (DB 記録/統計蓄積)
- Kill-switch: `BB_RSI_OANDA_TRIP=0` で即解除
- 解除条件: RR 1.5 拡張版 BT 365日で EV+ 実証

### Patch B — `_GRAIL_CANDIDATES` 機構

```python
# modules/demo_trader.py:5403+
_GRAIL_CANDIDATES = {
    "ema200_trend_reversal", "vol_surge_detector",
    "vix_carry_unwind", "ny_close_reversal",
}
```

### Patch C — `_check_grail_filter()` (新メソッド)

`USD_JPY` 専用、hour-bounded、`mtf_regime=range_tight + mtf_vol_state=squeeze`
の保守的境界. 詳細は demo_trader.py 参照.

### Patch D — Phase0 gate 直後の Grail bypass

合致時のみ `is_shadow=False`, `is_promoted=True`, `_adjusted_units=1000` 強制.
`GRAIL_SENTINEL_ENABLED=0` で全停止可能 (env var kill-switch).

## 期待効果 (事前宣言)

### bb_rsi trip
- Live OANDA 送信から 60% 占有戦略を除外 → 単一戦略集中解消
- ポートフォリオ EV 改善: 推定 +0.58p × 月間 N (76件→0件)
- Shadow N 蓄積で RR 拡張版 BT 検証へのデータ供給継続

### Grail Sentinel
- 4 grail × Sentinel 0.01lot で投入
- 期待 N: ema200(月 ~10), vol_surge(月 ~10), vix_carry(月 ~5), ny_close(月 ~5) = 月 30 前後
- 期待 EV: ema200=+9.4p, vol_surge=+9.5p, vix_carry=+11p, ny_close=+2p

## 観測ポイント (デプロイ後)

```bash
# Grail bypass log 確認
curl -s https://fx-ai-trader.onrender.com/api/demo/logs | jq '.logs[] | select(.message | contains("[GRAIL]"))'

# bb_rsi emergency trip log
curl -s https://fx-ai-trader.onrender.com/api/demo/logs | jq '.logs[] | select(.message | contains("bb_rsi_reversion OANDA"))'

# 1週後の grail Live 発生確認
curl -s 'https://fx-ai-trader.onrender.com/api/demo/trades?limit=200' | \
  jq '[.[] | select(.entry_type|test("ema200|vol_surge|vix_carry|ny_close")) | select(.is_shadow==0)] | length'
```

## 安全弁

1. **3 段階 kill-switch**: `BB_RSI_OANDA_TRIP=0`, `VWAP_MR_OANDA_TRIP=0`, `GRAIL_SENTINEL_ENABLED=0`
2. **Sentinel 0.01lot 固定** で最大損失制御
3. **既存 SL/TP/spread gate は通過** (grail bypass は shadow gate のみ)
4. **MC ruin gate / Aggregate Kelly gate は引き続き機能**

## 解除/降格判定 (事前宣言)

各 grail について **N≥20 到達時点**:
- Wilson_lo ≥ 観測値の 70% かつ累積 EV>0 → 維持
- いずれか未達 → SHADOW 戻し (env var で個別停止)
- 累積 EV<0 が連続 5 trade → 即時 SHADOW 戻し

## 参照
- [[external-audit-2026-04-24]] (構造的Catch-22 警告と整合)
- [[elite-freeing-patch-2026-04-24]] (前日 ELITE 解放 + vwap_mr trip)
- [[bb-rsi-rr15-rescue-2026-04-25]] (bb_rsi RR 1.5 救済 BT 起案)
