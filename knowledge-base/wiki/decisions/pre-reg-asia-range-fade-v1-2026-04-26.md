# Pre-Registration LOCK: asia_range_fade_v1

**LOCK Date**: 2026-04-26
**Type**: Phase 3 mechanism-driven 新エッジ pre-registration
**Category**: MR (Mean-Reversion / Range)
**Status**: 🔒 LOCKED — 仮説/閾値を本日付で固定。HARKing 防止のため後付け変更禁止。

## 1. Hypothesis (Mechanism Thesis)

**1 行**: アジア時間 (00-07 UTC) の低 vol 環境で形成された range の high/low touch は、
構造的に流動性吸収後に range 中央へ回帰する傾向が高い。touch + rejection で fade entry。

**メカニズム詳細**:
- アジア時間は institutional flow が低い (London/NY 出席前)
- 低 vol 環境では trend formation 力が弱く、range boundary が strong S/R として機能
- range high/low touch = 過度な短期 directional bias (often retail driven)
- rejection = institutional liquidity が touch 後に逆方向に提供される

**因果方向**: 低 vol session → range 形成 → touch (overshoot) → liquidity 吸収 → 中央回帰

**TAP 含有チェック**:
- TAP-1 (中間帯 AND): ❌ 不含 (range boundary は明示的 level、中間帯ではない)
- TAP-2 (N-bar pattern): ❌ 不含 (rejection は 1 bar 確認 + range duration 構造)
- TAP-3 (直前 candle): ⚠️ rejection candle は直前 1 bar だが、range 形成の構造的前提が必須

→ 構造的に TAP 回避 (range 形成という明示的な構造的前提による)。

## 2. Entry Conditions (LOCKED)

### Required (全て満たす必要)

```
SESSION_CONDITION:
  current UTC hour ∈ [02, 06]   (Tokyo 中盤 - London 直前)
  excluded:
    [00, 01] = Sydney early (流動性 dead zone)
    [07, 09] = London open (vol explosion)

RANGE_FORMATION:
  recent 24 bars (M15 × 24 = 6h) で:
    range_high = max(high) of last 24 bars
    range_low  = min(low) of last 24 bars
    range_size = range_high - range_low
    
  構造的 range 条件:
    range_size_pips ≤ 1.5 × ATR(14)   [range が ATR の 1.5 倍以内]
    range_size_pips ≥ 5 pip            [範囲が極小すぎない]
    bars_in_range_pct ≥ 0.80           [24 bar 中 80% 以上が range 内]

TOUCH_DETECTION:
  BUY (range_low fade):
    current low ≤ range_low * (1 + 0.0005)
  SELL (range_high fade):
    current high ≥ range_high * (1 - 0.0005)

REJECTION_CANDLE:
  BUY: close > open AND
       (low - close) / (high - low) ≥ 0.4   [下髭 40% 以上]
  SELL: close < open AND
        (high - close) / (high - low) ≥ 0.4

EXTRA_CONFIRMATION:
  RSI(14) at touch:
    BUY: RSI ≤ 30  (oversold confirmation)
    SELL: RSI ≥ 70 (overbought confirmation)
```

### Forbidden (除外条件)

```
- 直近 4 bars 内に同 range fade entry → no entry
- ATR(14) > 8 pip → no entry (vol expansion = range invalid)
- Bonus condition: 経済指標 30 min 前後 → no entry (flow disruption)
- 月曜 Asia open (Sydney 周辺) → no entry (gap risk)
```

## 3. Exit Conditions (LOCKED)

```
TP: range の中央 ((range_high + range_low) / 2)
    または entry ± 0.7 × range_size, 近い方
SL: range_low - 0.5 × ATR (BUY 時)
    range_high + 0.5 × ATR (SELL 時)
TIME_STOP: London open (07:00 UTC) で未達なら成行決済
```

## 4. Validation Requirements (LOCKED — 一切緩和不可)

| 項目 | 閾値 | 検証手段 |
|---|---|---|
| Sample size | N ≥ 200 | Wilson lower bound 計算可能性 |
| Win Rate | Wilson lower bound > 50% | `tools.empirical_validator.wilson_ci` |
| Profit Factor | PF > 1.40 (MR は WR 高めを想定) | (sum win) / (sum loss) |
| EV per trade | EV > 0 (after Friction Model v2 cost) | `friction_for(pair, mode="DT", session="Tokyo")` |
| Walk-Forward | 5-fold WF, 各 fold で WR > 50% AND PF > 1.0 | 365日 BT を 5 等分 |
| Bonferroni 補正 | α=0.05 / m=10 → α=0.005 | `bonferroni_correct` |
| Top-1-drop | drop_pct < 30% | `top_k_drop_test` |
| Bootstrap CI | 95% CI low > 0 (EV) | `bootstrap_ci` |
| Monte Carlo DD | DD ≤ Kelly Half 許容範囲 | `modules.risk_analytics` |

## 5. Test Plan

### Phase 3.A: 365日 BT

- Pair set: USD_JPY, EUR_USD (アジア時間に主要動く 2 ペア)
- Period: 2025-04-26 〜 2026-04-26 (365日)
- Cost: `friction_for(pair, mode="DT", session="Tokyo")` 適用
  → アジア時間 friction multiplier 1.45× が反映される
- ATR: 過去 14 bars (M15)

合格基準: 上記 9 項目全 PASS

### Phase 3.B: Walk-Forward

- Period を 5 fold (each ~73日)
- 各 fold で個別 WR/EV/PF
- レジーム別: 高 vol vs 低 vol 期で結果が一貫しているか追加チェック

### Phase 3.C: Shadow forward test

- 1 ヶ月 shadow forward
- N ≥ 30 で Wilson lower bound > 50%
- アジア時間限定 fire frequency が現実的か確認

### Phase 3.D: Live promotion

- 0.01 lot で live 投入
- N ≥ 30 で再検証
- Kelly Half ルールで lot 増設

## 6. Anti-pattern 警告

- ❌ **時間帯緩和**: アジア時間限定で fail → 「London 直前まで延長」→ HARKing、戦略破棄
- ❌ **range 定義変更**: 24 bars で fail → 「48 bars」→ data dredging、戦略破棄
- ❌ **RSI 閾値緩和**: 30/70 で fire 少ない → 「35/65 に緩和」→ HARKing、戦略破棄
- ❌ **Pair 追加**: USD_JPY/EUR_USD で fail → 「AUD/USD 追加で平均化」→ cherry-pick、戦略破棄

## 7. Expected Effect Size (Pre-Registration)

- Estimated WR: 60% (range fade with rejection の理論値、低 vol 環境)
- Estimated PF: 1.55
- Estimated EV: +0.6 pip / trade (after Friction Model v2 Tokyo session cost)
- Required N (sample size planner): `sample_size_for_proportion_diff(0.50, 0.60) ≈ 380`
  → 検出には N≥380、365日 BT で fire 400+ 回が前提
- Asia 時間限定なので fire frequency 低い可能性 → fire ≤200 なら判定保留

## 8. Strategic Rationale (なぜ low vol session を選ぶか)

クオンツ的に MR 戦略は **trend が弱い時間帯** で edge が出やすい:
- High vol session (London/NY) は trend formation 力強 → MR は不利
- Low vol session (Asia 中盤) は range 形成 dominance → MR 構造的優位
- session × strategy interaction を `bt-live-divergence.md` の 6 因子で実証済 (Asia 摩擦は高いがこれは別問題)

→ Pure mechanism と session 整合性の二重根拠。

## 9. References

- [[strategy-mechanism-audit-2026-04-26]] — thesis 評価枠組み
- [[edge-reset-direction-2026-04-26]] — Phase 0 方向転換
- [[pre-reg-pullback-to-liquidity-v1-2026-04-26]] — TF candidate 兄弟 pre-reg
- [[friction-analysis]] — Friction Model v2 ベース数値
- [[bt-live-divergence]] — session × strategy interaction
- `modules/friction_model_v2.py` — friction lookup
- `tools/empirical_validator.py` — 統計関数
- Lo & MacKinlay (1988) "Stock Market Prices Do Not Follow Random Walks" — 短期 MR 学術根拠
