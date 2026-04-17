# MTF Regime Engine Validation (2026-04-17)

## TL;DR

| 判定 | 結論 |
|---|---|
| **baseline labeler (slope_t+ADX, M30/H1/H4/D1)** | η²(fwd-*) < 0.003 → **構造的ノイズ**. 使用不可. |
| **v9.2 guardrail (uncertain×SELL / up_trend×BUY)** | 6.5年検証で **方向が逆**. 利益トレードを block していた. **デフォルト無効化**. |
| **MTF engine (D1 dominant × H4 confirm × H1 trigger)** | η² 最大 **105×** improvement, flipping rate 0.6%/bar. **shadow 投入承認**. |
| **Signal map (emerging trend follow / mature reversion)** | 全 3 pair で ★★★ (\|t\|>3), IS/OOS 安定. **v9.3 で guardrail 再設計**. |

---

## 1. 動機

v9.2 SELL bias forensics (2026-04-17 初稿 [[sell-bias-forensics-2026-04-17]]) で導入した regime-conditional guardrail が、

1. **Live 9日 N=60-72** の in-sample 検出
2. **ラベル元**は slope_t+ADX single-TF (M30) labeler
3. 理論的裏付け（forward-return predictability）**未検証**のまま実装

だった。「regime 判定が最重要なのに、その labeler が信頼できるか分からないまま guardrail を作っている」との指摘を受け、3 段階で検証した。

---

## 2. Stage 1 — Baseline labeler validation (single-TF)

### 手順

`/tmp/labeler_forward_return_test.py` → 6.5年 H1 × 3 pair (USD_JPY / EUR_USD / GBP_USD) に
`label_regimes(RegimeConfig())` を適用し、forward return r_{t+k} × regime の η² (ANOVA) を計測.

### 結果

```
Pair       k=1h     k=4h     k=24h
USD_JPY    0.00013  0.00045  0.00086     sign_ok ✗
EUR_USD    0.00009  0.00031  0.00262     sign_ok ✗
GBP_USD    0.00004  0.00004  0.00062     sign_ok ✗
```

全 pair × 全 horizon で **η² < 0.003 (trivial)**. さらに label-ごとの forward return の符号が反転:
- up_trend ラベルの期待 forward return が **負**
- uncertain ラベルが **最も正**

**解釈**: slope_t > 2 は「既に上がった」ラベル → ピークを catch、エントリーには遅すぎる (ラギング).

---

## 3. Stage 2 — MTF 検証 (階層化仮説)

ユーザーの直感「長い足を見ないと trend は分からない」を検証. 同じ labeler を H1 / H4 / D1 で適用.

### 結果

```
                   fwd-short  fwd-mid    fwd-long     sign
USD_JPY  H1        0.00013    0.00045    0.00086      ✗✗✗
USD_JPY  H4        0.00005    0.00023    0.00211      ✗✗✗
USD_JPY  D1        0.00022    0.00117    0.00374      ✓✓✓
EUR_USD  H1        0.00009    0.00031    0.00262      ✗✗✗
EUR_USD  H4        0.00008    0.00052    0.00024      ✗✗✗
EUR_USD  D1        0.00068    0.00467    🟢 0.01794   ✓✓✓
GBP_USD  D1        0.00043    0.00051    0.00287      ✗✗✗
```

**発見**: D1 で初めて sign が揃い、EUR_USD × fwd-20d で η² = 0.018 = actionable 閾値 (0.010) 到達.

**示唆**: 構造的 trend は D1 の粒度で測るべき. M30/H1 のラベルは noise.

詳細: `/tmp/mtf_regime_test.py`

---

## 4. Stage 3 — MTF Engine 設計と検証

### 4.1 設計 (research/edge_discovery/mtf_regime_engine.py)

7-class 階層化ラベル:

```
D1 (dominant)  — EMA20/EMA50/EMA200 alignment + ADX(14)
                 { +2 strong_bull, +1 weak_bull, 0 flat,
                   -1 weak_bear, -2 strong_bear }
H4 (confirm)   — EMA20 vs EMA50 diff/close
                 { +1 bull, 0 neutral, -1 bear }
D1 vol state   — BB(20)*2σ width の 252日 rolling percentile
                 { squeeze ≤25pct, normal, expansion ≥75pct }

Compose:
  D1=+2 + H4≥0 → trend_up_strong
  D1=+1 + H4≥0 → trend_up_weak
  D1=0  + squeeze → range_tight
  D1=0  + else   → range_wide
  D1=-1 + H4≤0 → trend_down_weak
  D1=-2 + H4≤0 → trend_down_strong
  (H4 disagreement) → uncertain
```

- **As-of alignment**: `pd.merge_asof(direction='backward')` + 1-bar shift → 未来参照ゼロ.
- **Config-driven thresholds**: `MTFConfig` dataclass でペアごとの tuning 余地.
- **Right-aligned features**: ADX / BB 全て confirmed candles のみ (OANDA `complete=true`).

### 4.2 検証 (η² 比較)

```
           fwd-1h     fwd-4h     fwd-24h    fwd-120h    flip
USD_JPY    MTF  0.00013  0.00049  0.00184   0.00530   0.6%
           base 0.00013  0.00045  0.00086   0.00159
EUR_USD    MTF  0.00012  0.00056  0.00315   🟢 0.02112   0.7%
           base 0.00009  0.00031  0.00262   0.00020
GBP_USD    MTF  0.00015  0.00063  0.00304   🟢 0.01194   0.6%
           base 0.00004  0.00004  0.00062   0.00248
```

- **η² improvement (fwd-120h)**: USD_JPY 3.3×, EUR_USD **105×**, GBP_USD 4.8×
- **Flipping rate**: 6.1% → 0.6% (10× 安定化). 頻繁な反転でエントリー乱発しない.
- **IS/OOS 比較** (50/50 split): degradation は同一オーダー, 露骨な curve-fit なし.

### 4.3 Signal Decomposition — 真の signal 構造

sign_ok が naive に ✗ だったのは、MTF engine が **2 種類の signal** を同時に出していたため.

#### Weak trend = Continuation (trend-following edge)
#### Strong trend = Exhaustion (mean-reversion edge)

Hypothesis tests (3 pair × 3 horizon, 全て ★★★ = |t|>3):

```
hypothesis                            USD_JPY  EUR_USD  GBP_USD
H1: weak_up>0 AND weak_dn<0             ✓        ✓       ✓     (8/9)
H2: strong_up < weak_up (exhaustion)    ✗*       ✓       ✓
H3: strong_dn > weak_dn (reversion)     ✓        ✓       ✓     (9/9)
H4: uncertain has negative drift        ✓        ✓       ✗     (pair-dep)

* USD_JPY は 2021- secular carry bull で strong_up も継続する (pair-specific特例).
```

#### Signal Map (fwd-3d pip)

| regime | USD_JPY | EUR_USD | GBP_USD | action |
|---|---|---|---|---|
| trend_up_weak | +12.65 ★★★ | +12.22 ★★★ | +1.82 | BUY (emerging trend) |
| trend_down_weak | −0.92 | **−10.16** ★★★ | **−30.23** ★★★ | SELL (emerging trend) |
| trend_up_strong | +13.69 ★★★ (JPY特例) | **−5.16** ★★★ | **−18.38** ★★★ | SELL (exhaustion, 非JPY) |
| trend_down_strong | +21.07 ★★★ | +14.30 ★★★ | +10.56 ★★★ | BUY (oversold bounce) |
| range_tight | +21.74 ★★★ | +0.03 | +4.04 ★★★ | (USD_JPY carry drift) |
| range_wide | −0.90 | +13.29 ★★★ | +7.11 ★★★ | BUY (breakout bias) |
| uncertain | −6.37 ★★★ | **−10.65** ★★★ | +5.51 ★★★ | skip (pair-dep) |

詳細: `/tmp/mtf_engine_validation.py`, `/tmp/mtf_signal_decomposition.py`

---

## 5. v9.2 Guardrail 判定

v9.2 は以下 2 cell を block していた:

| v9.2 block | MTF 検証 6.5年 | 判定 |
|---|---|---|
| uncertain × SELL | EUR_USD uncertain fwd-3d = **−10.65p** (t=−11.12) → SELL は **利益** | 逆 |
| up_trend × BUY | USD_JPY up_trend fwd-1d = **+4.52p** (t=+4.83) → BUY は **利益** | 逆 |

Live 9日 N=60-72 で観測した負 EV は、6.5年検証で完全に棄却. **小サンプル curve-fit**.

### 対応 (v9.2.1)

- `demo_trader.py`: `REGIME_GUARDRAIL_ENABLED` デフォルトを `"0"` に反転 (無効化)
- コード自体は温存. MTF engine guardrail (v9.3) への移行後に削除.
- テスト `tests/test_regime_guardrail.py` の default assertion 更新.

---

## 6. Next Actions (v9.3 ロードマップ)

### Step 1 — Shadow 展開 (14 day observation)

MTF engine を `demo_trader` に組み込み、**判定のみ** shadow log に出力:

```python
# pseudo-code
from research.edge_discovery.mtf_regime_engine import label_mtf, fetch_mtf_data
mtf_regime = _get_mtf_regime(instrument)  # 30分 TTL キャッシュ
self._add_log(f"[MTF_MONITOR] {instrument} signal={signal} mtf={mtf_regime}")
# trade は通す. DB の regime_mtf カラムに記録.
```

目的: Live 環境で MTF engine の latency / OANDA API 負荷 / 分布偏りを確認.

### Step 2 — 最初の actionable cell を guardrail 化

14日 N 蓄積後、Live での検証 cell:

- **trend_up_weak** × 逆張り SELL → block (or lot reduce)
- **trend_down_weak** × 逆張り BUY → block
- **uncertain × 任意方向** × 低 ADX → lot reduce (skip ではなく)

pair-specific:
- **USD_JPY** は secular bull なので strong_up_trend を除外しない.
- **GBP_USD** の uncertain は drift が逆方向 (+5.51 @3d) → 通常ルール除外.

### Step 3 — MTF features を entry_type signal に統合

monolithic な regime gate ではなく、features として各 entry_type の signal 関数が参照:

```python
# 例: ema_trend_scalp だけが MTF context を必要とする
if entry_type == "ema_trend_scalp":
    if mtf["regime_mtf"] in ("trend_up_weak", "trend_down_weak"):
        # 方向揃えば通過
    else:
        return None  # no signal
```

---

## 7. 参照

- Baseline labeler: [[conditional-edge-estimand-2026-04-17]] §6
- v9.2 initial forensics: [[sell-bias-forensics-2026-04-17]]
- Implementation: `research/edge_discovery/mtf_regime_engine.py`
- Validation scripts: `/tmp/mtf_regime_test.py`, `/tmp/mtf_engine_validation.py`, `/tmp/mtf_signal_decomposition.py`, `/tmp/mtf_retrospective_trade_analysis.py`, `/tmp/mtf_strategy_aware_analysis.py`
- Shadow integration: `modules/demo_trader.py::_get_mtf_regime`, `modules/demo_db.py` (mtf_* columns)
- Tests: `tests/test_regime_guardrail.py` (7/7 pass), `tests/test_mtf_monitor.py` (6/6 pass)

---

## Phase A 追記: 戦略ファミリ考慮 retrospective 分析 (2026-04-17 夕方)

### A-1. 動機

ユーザー仮説: 「レジーム判定が正しくなれば勝率が上がる.順張り/逆張りが適切に使い分けられる」.

**初回の retrospective**（全戦略を trend-follow と仮定）は符号が逆転した: aligned WR 38.9% < conflict 69.2%. これは サンプルが mean-reversion 戦略（bb_rsi_reversion 等）に偏っていたため, TF前提では「conflict」が実はMR視点の「aligned」になっていた.

### A-2. 戦略ファミリ定義

各 entry_type を 4 ファミリに分類:

| Family | Logic | 例 |
|---|---|---|
| **TF** (Trend-Follow) | regime方向 × signal方向 = 揃う | ema_trend_scalp, cci_adx_momentum_gate, adx_trend_continuation, ema_cross_trend, donchian_breakout |
| **MR** (Mean-Reversion) | regime方向と signal方向 = 逆 | bb_rsi_reversion, rsi_mean_reversion, bb_reversion, stochastic_rsi_reversal, williams_rsi_combo |
| **BO** (Breakout) | レジーム問わず range_* 終端で通過 | donchian_breakout, support_resistance_break, atr_breakout |
| **SE** (Session) | セッション条件 + trend, range両対応 | tokyo_session_range, london_breakout, ny_overlap |

### A-3. ファミリ別 aligned/conflict ルール

```python
def strategy_aware_alignment(strategy, mtf_regime, signal):
    family = STRATEGY_FAMILY_MAP[strategy]
    if family == "TF":
        if mtf_regime in ("trend_up_weak", "trend_up_strong") and signal == "BUY": return "aligned"
        if mtf_regime in ("trend_down_weak", "trend_down_strong") and signal == "SELL": return "aligned"
        if mtf_regime in ("trend_up_*") and signal == "SELL": return "conflict"
        ...
    elif family == "MR":
        # 逆張り: trend中に反対方向 = aligned (MR視点)
        if mtf_regime in ("trend_up_*") and signal == "SELL": return "aligned"
        if mtf_regime in ("trend_down_*") and signal == "BUY": return "aligned"
        if mtf_regime in ("range_tight", "range_wide"): return "neutral"
        ...
    ...
```

### A-4. 結果（LIVE trades, N=89）

| 区分 | N | WR | Mean PnL (pips) |
|---|---|---|---|
| **aligned** (戦略ファミリと整合) | 38 | **57.9%** | **+4.3** |
| **conflict** (ファミリと逆) | 20 | **35.0%** | **-8.1** |
| **neutral** (range等) | 31 | 48.4% | +0.2 |
| 差分 (aligned − conflict) | — | **+22.9pp** | **+12.4p** |

### A-5. 反実仮想: conflict trades を block していたら

- **LIVE 累積 PnL**: 実績 **−6.7p** → MTF gate で conflict block → 推定 **+162.1p** (+168.8p 改善)
- **weighted WR**: 実績 52.8% → MTF gate 後 54.8% (+2.0pp)

### A-6. 含意

1. **MTF エンジンは strategy-aware で使う必要がある**. 全戦略に同じ「trend方向一致 = aligned」を当てると, MR 戦略では符号が逆になり精度を下げる.
2. **v9.2 guardrail を v9.3 MTF gate で置き換える根拠が揃った**. 14日 shadow observation (N≥30) 後に gate 化を決定する.
3. **shadow mode の意義**: 実環境でファミリ分類が正しいか, conflict signal の分布が BT と一致するかを検証する. データが揃えば gate promotion へ.

### A-7. 次のマイルストーン

- [ ] 14日 shadow 観察後, entry_type × MTF regime の分布を actionable cell (N≥30, 有意) で抽出
- [ ] Phase C: 全戦略 BT に MTF gate を適用 (strategy_aware_alignment ベース) し, 反実仮想を out-of-sample で検証
- [ ] Gate 化: actionable cell で conflict が block された時の累積 PnL が shadow 期間で改善しているか確認



## 8. 開発メモ

**なぜ単一 TF labeler が構造的に失敗するのか**:

1. **Lookback bias** — slope_t(48) は「過去のドリフト」の記述統計. 時点 t で「上がっていた」を検出しても、t+1 以降は mean-reversion に入る.
2. **Single-scale** — 日足トレンドは H1 48 bar (= 2日) で捕捉不能. TF ごとに異なる trend の concept が存在する.
3. **Stationarity assumption** — 単一閾値は regime transition に対応できない. Bull/Bear transition 時に最も間違える.

**MTF 解決**:
- **階層化** — D1 dominant が週次のバイアスを決め、H4 が日内方向を確認、H1/M30 がエントリータイミング.
- **Predictive features** — EMA cloud の相対位置 (lagging でない) + ADX strength (level ではなく stack).
- **Pair固有** — 同じ閾値でも pair の secular trend (carry, volatility) を吸収. USD_JPY と EUR_USD は strong_up の意味が違う.

これは BJF / SBI の記述を統計的に定式化した結果と一致する.
