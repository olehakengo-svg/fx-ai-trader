# Pre-Registration LOCK: ma_trend_perfect (v1b)

**LOCK Date**: 2026-04-30
**Type**: Rule R1 (Slow & Strict) Shadow→LIVE 昇格 pre-registration
**Strategy**: `ma_trend_perfect` (MA-Generic Family v1b)
**Category**: Trend (Pure Trend-Follow with Perfect Order)
**Status**: 🔒 LOCKED — 仮説/閾値/コホートを本日付で固定。HARKing 防止のため後付け変更禁止。

## 1. Hypothesis (Mechanism Thesis)

**1 行**: H1 EMA200 によるマクロ方向 + M15 大循環 (EMA9>21>50) によるメソ
トレンド + M5 EMA21 再ブレイクによるマイクロ加速 → 3 段カスケードでダマシ
を統計的に削った純粋順張りスキャル。

**メカニズム詳細**:
- ema_trend_scalp の負け要因は pullback 型 (ADX>31 で confidence ペナルティ
  が効く構造的弱点)。**純粋順張りは反証されていなかった**。
- USD_JPY は M15/H1 で trend persistency が高い (SDR 流入主因の構造的特性)。
- M5 EMA21 再ブレイク = 過熱 pullback 終了 + トレンド継続シグナル。
- パーフェクトオーダー (EMA9>21>50) は trend strength の純粋な証拠であり、
  ADX 上昇局面で発火が増えるが pullback 戦略と異なり高 ADX が逆風にならない。

**TAP 含有チェック**:
- TAP-1 (中間帯 AND): ❌ 不含 (M5 EMA21 再ブレイクは明示的 level)
- TAP-2 (N-bar pattern): ⚠️ M5 prev_close ≤ ema21 < close という 1 bar 反転
  だが、M15 大循環という構造的前提が必須なので TAP-2 厳密違反ではない
- TAP-3 (直前 candle): ⚠️ MACD-H 上昇/下落確認は直前 1 bar 含むが、M15 +
  H1 の複層構造が dominant signal

→ 構造的に TAP 回避 (M15 大循環 + H1 EMA200 という多層構造的前提による)。

## 2. Entry Conditions (LOCKED — strategies/scalp/ma_trend_perfect.py)

### Pair (LOCKED)
- USD_JPY のみ (LIVE 実証コホート整合、多重検定補正最小化)
- XAU 除外、その他通貨ペアは Phase 2 で別途判断

### Required (全て満たす必要)

```
H1_TREND_GATE:
  h1_close > h1_ema200 * 1.001    → BUY 方向確定
  h1_close < h1_ema200 * 0.999    → SELL 方向確定
  それ以外                         → no entry (10bps gap が方向確定閾値)

M15_PERFECT_ORDER:
  BUY:  m15_ema9 > m15_ema21 > m15_ema50 AND m15_ema_slope > 0
  SELL: m15_ema9 < m15_ema21 < m15_ema50 AND m15_ema_slope < 0
  Common: m15_adx ≥ 22.0

M5_BREAKOUT_REACCEL:
  BUY:  m5_prev_close ≤ m5_ema21 < m5_close
  SELL: m5_prev_close ≥ m5_ema21 > m5_close

M1_CONFIRMATION:
  BUY:  ctx.entry > ctx.open_price (陽線確認) AND ctx.macdh > ctx.macdh_prev
  SELL: ctx.entry < ctx.open_price (陰線確認) AND ctx.macdh < ctx.macdh_prev
```

### Position Sizing & Exits (LOCKED)
```
SL: ctx.atr7 × 1.0
TP: max(ctx.atr7 × 1.8, sl_dist × 1.5)   [RR floor = 1.5]
Spread cost (BT): 0.8 pip round-trip (USD_JPY 想定)
```

## 3. Pre-LOCK BT Evidence (180d × USD_JPY × spread 0.8 pip)

実行: `BT_MODE=1 NO_AUTOSTART=1 python3 research/edge_discovery/ma_family_validation.py --pair USD_JPY --days 180 --wf-folds 3 --inject-spread 0.8 --strategies ma_trend_perfect` (2026-04-30 06:42 UTC)

| Cell | N | WR | PF | Kelly | Wilson95下限 | p値 (1-sided binomial vs BEV) | 6条件 |
|---|---|---|---|---|---|---|---|
| **🏆 Tokyo** | 91 | 73.6% | 3.84 | 54.5% | 63.75% | 0.00001 | **✅ 6/6 PASS** |
| **🏆 NY** | 124 | 61.3% | 2.19 | 33.3% | 52.50% | 0.005 | **✅ 6/6 PASS** |
| London | 99 | 59.6% | 1.97 | 29.4% | 49.75% | 0.0503 | 5/6 (BH ギリギリ未達) |
| ALL | 369 | 60.7% | 1.99 | 30.2% | 55.64% | 0.00026 | 5/6 |

**WF 3-fold 内訳:**
- f1: N=123, WR 64.2%, PF 2.18, Kelly 34.7%, p=0.012
- f2: N=123, WR 61.8%, PF 2.20, Kelly 33.7%, p=0.005
- f3: N=123, WR 56.1%, PF 1.67, Kelly 22.4%, p=0.146

→ 全 fold で PF>1.3 ✅

**BH 補正 (q=0.05, 3 cells):** Tokyo (p=10⁻⁵) と NY (p=0.005) が有意。

## 4. Promotion Path (rule:R1)

### Phase A: Shadow Sentinel (現状, 2026-04-30〜)
- `_SCALP_SENTINEL` で 0.01 lot 稼働。データ蓄積。

### Phase B: Shadow→LIVE 昇格判定 (2026-05-30, **+30 日後**)
**Phase B 期間は当初 14d → 30d に延長** (Tier 1.5 forensic で f3 期待 N が
14d で不足、Wilson 信頼区間広すぎることが判明したため)。

30 日 LOCK 期間後、以下を確認:
1. Shadow Live N (USD_JPY × Tokyo+NY 合算) ≥ 30
2. Shadow Live は **本 LOCK と同一閾値** で稼働 (HARKing なし)
3. Shadow Live cell-level metrics と本 BT の **f3 cell-level metrics** の
   差分が許容内 (BT 全 180d ではなく直近 f3 が baseline、decay を考慮)
   - Tokyo Wilson95下限 > **30%** MUST
   - NY Wilson95下限 > **25%** MUST
4. Cohort time alignment: 2026-04 H1 急落 (WR 33%) の構造原因が特定
   されているか確認。原因不明のままなら昇格中止

### Phase C: LIVE Promotion (full strategy 2026-05-14 以降)
上記すべて満たせば、`_SCALP_SENTINEL` から外して通常戦略リストへ。
初期 lot = **Quarter Kelly** (実 Kelly 30-54% × 0.25 = 7-13.5% に相当する
ロット係数). Forensic Report (2026-04-30) の f3 期間 WR 劣化 (64→56%) と
12/4-cell BH 未通過事実を反映した保守化。Half Kelly への引き上げは Phase
C 開始後 30d で Wilson95下限>40% 維持時に再評価。

## 5. Forbidden Modifications (HARKing 防止)

LOCK 期間中 (2026-04-30 ～ 2026-05-14) に以下は **絶対禁止**:
- ❌ 閾値変更 (m15_adx_min, m15_adx_strong, h1_bias_gap_pct, RR floor, TP/SL mult)
- ❌ ペア追加/削除
- ❌ セッション境界変更
- ❌ Bonferroni/BH を「BH 通過しなかったから」と緩めること
- ❌ "都合の良い fold" だけ採用すること

許可される修正:
- ✅ ロット計算 (Phase C 前の Kelly 再計測による)
- ✅ Shadow→LIVE 昇格判定の延長 (London cell が p=0.05 ボーダーゆえ追加 N≥30 待機)
- ✅ 致命的バグ修正 (signal direction 反転等。判定後やり直し)

## 6. Failure Conditions (本仮説の反証条件)

LOCK 終了時 (2026-05-14) に以下のいずれかが発生したら **昇格中止**:
1. Shadow LIVE Tokyo Wilson95下限 < **30%** (Forensic で確認した f3 decay
   prior + BT optimistic bias を考慮、LIVE で 30% を下回ると真のエッジ無し
   と判定)
2. Shadow LIVE NY Wilson95下限 < 25% (BT 52.5% の 50%)
3. fold f3 (2026-02-09 〜 2026-04-13) と Phase B Shadow 期間で WR 連続 12 d
   下落トレンドが続けば構造的 decay 確定 → 昇格中止
4. spread 実測 > 0.8 pip × 1.5 = 1.2 pip (USD_JPY 構造的悪化)
5. ema_trend_scalp 同期間 Shadow と比較して相対 PF 比 < 1.5x に劣化 (Plan
   設計時の改善基準割れ)
6. **ATR 14d 平均 (M15) が f3 baseline 0.1201 の +20% を超える** = 0.1441 以上
   (Tier 2 macro forensic, `research/edge_discovery/v1b_f3_macro.py` で発見:
   ATR vol expansion が SL 接触ノイズを拡大し v1b エッジを希釈する構造的経路。
   f1→f3 で ATR +15.0%、EMA21 cross continuation +18.0% にもかかわらず WR
   劣化したのは vol regime mismatch が原因)

## 6-bis. Forensic Report (Tier 1+1.5, 2026-04-30) 確認事項

実施スクリプト:
- `research/edge_discovery/v1b_forensics.py` (Tier 1: WR 検証 + cohort + BH)
- `research/edge_discovery/v1b_f3_decay.py` (Tier 1.5: f3 decay 構造分解)

### Tier 1: Tokyo 73.6% WR は HARKing なしの真エッジ
- 系列従属 Wald-Wolfowitz p=0.93 (i.i.d. 整合)
- 上位 5 週集中度 13.4% (低)
- Quick LOSS 16.7% (健全)
- 時刻分布 UTC 0-6 で WR 50-100% 全帯エッジあり

### Tier 1: BH cell grouping
- 3-cell (LOCK 宣言): Tokyo (p=10⁻⁵) + NY (p=0.005) BH-pass ✅
- 4-cell (strategy-level): 0 通過
- 12-cell (full family): 0 通過
- → 3-cell defensible だが「保守的視点では未通過」を Phase B 報告で明記

### Tier 1.5: f3 decay 構造分解 — **重大警報あり**

**Session × Fold cell decay マトリクス**
| Session | f1 WR | f3 WR | ΔWR | f3 Wilson | 判定 |
|---|---|---|---|---|---|
| **Tokyo** | 77.4% | **63.0%** | **-14.5%** | 44.2% | 🔴 大幅劣化 |
| **London** | 68.8% | **56.0%** | **-12.7%** | 37.1% | 🔴 大幅劣化 |
| NY | 60.9% | 57.1% | -3.7% | 42.2% | 🟡 軽度劣化、最安定 |

**Tokyo decay の機構分解**:
- N: 31→27 (発火頻度減)
- avg_win: 5.75→4.80 (-1pip 縮小、TP到達前のフェード増)
- median_exit_bars: 3→6 (倍に延伸 = 鋭い順張りブレイクが消失)
- → 「鋭い momentum continuation の減少」= volatility compression / range 化

**半月次 WR 推移 (重大)**:
- 2025-10〜2026-01: WR 60-69% で安定
- 2026-02 H2: WR 53.8%
- 2026-03 H1: WR 62.5% (一時回復)
- **2026-04 H1: WR 33.3% (Wilson下限 17%, EV -0.77 pip)** ← LOCK 直前の急落
- Linear trend: -1.32%/半月、早期 3 半月 60.7% → 直近 3 半月 52.5% (-8.1%)

### 強化された Phase B 判断 (LOCK Failure に反映済み)

1. **Phase B 期間: 14d → 30d に延長** (Tokyo expected N=6/14d で Wilson 信頼区間広すぎ。N≥30 達成には 30d 必要)
2. **NY-only 昇格パス追加**: Tokyo/London が decay 続行でも NY 単独で昇格条件満たせば NY-only LIVE (lot 0.5 × Quarter Kelly) 可
3. **2026-04 H1 急落の構造原因解析を Phase B 中に必ず実施** (FOMC dot plot / 円介入観測 / IV regime)

## 7. Related Documents

- 設計仕様: [[ma_generic_family_v1]]
- 実装計画: `/Users/jg-n-012/.claude/plans/ema-trend-scalp-ma-generic-wadler.md`
- ema_trend_scalp 廃止判断: 別途 (相対 PF 比 2.9x 達成済み)
- LIVE/Shadow 分離規律: user memory `feedback_live_shadow_separation` (~/.claude/.../memory/)
- Cohort time alignment: user memory `feedback_cohort_time_check`

## 8. Reviewer Notes

LOCK 文書のレビュアーは:
- ✅ 閾値が **コードと一致しているか** を確認 (strategies/scalp/ma_trend_perfect.py)
- ✅ BH 補正の cell 数が宣言通り (3 cells = Tokyo/London/NY) であるか
- ✅ Pre-reg LOCK 解除条件が **時刻ベース** で明示されているか (2026-05-14)
- ✅ Failure condition がコホート時系列整合観点 (`feedback_cohort_time_check.md`)
  と整合しているか
