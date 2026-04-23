# Cell-level Survivor Scan (2026-04-23)

**Pre-registration**: [[pre-registration-phase2-cell-level-2026-04-23]]
**Script**: `/tmp/cell_level_scan.py`
**Raw**: `/tmp/cell_level_scan_output.txt`
**Scope**: shadow post-cutoff 2026-04-08 / XAU除外 / N=2075 / 5 pairs × 4 sessions × 17 strategies

## Result: ✅ Scenario A — 全面 regime mismatch 確定

| Metric | Value |
|--------|-------|
| Active cells (N≥10) | **50** |
| Cells with N≥30 | 19 |
| Cells with Wilson lower > BEV | **0** |
| Cells with Fisher p < 2.5e-4 | **0** |
| Cells with Kelly > 0 | 3 (小-N、N=20/10/20) |
| Cells with Kelly > 0.05 | 2 |
| **GO (all 5 criteria)** | **0** |
| **CANDIDATE (N≥20, 3+/5)** | **0** |

Pooled shadow WR (raw, no cost): 23.8% (493/2075)

## Binding criteria (locked before scan)

5 条件全てを満たす cell のみ GO。実測結果:

| Condition | Count / 240 | Example best-hit |
|-----------|-------------|------------------|
| N ≥ 30 | 19 | ema_trend_scalp\|USD_JPY\|ny N=118 |
| Wilson 95% lower > BEV+3pp | **0** | best: bb_squeeze_breakout\|USD_JPY\|ny (wlo=21.9%, bev=26.6%) |
| Fisher p < 2.5e-4 | **0** | min p=0.11 (bb_squeeze_breakout\|USD_JPY\|ny, bb_rsi_reversion\|USD_JPY\|ny) |
| Kelly > 0.05 | 2 | bb_squeeze_breakout\|USD_JPY\|ny K=+0.212 (N=20) |
| WF 2-bucket same sign | 1 | bb_squeeze_breakout\|USD_JPY\|ny |

**交点 = 0**. 全 240 cells のうち 1 つも 5 条件を満たさず、holdout 候補化も不可。

## Top-5 cells by conditions met

| Cell | N | WR% | wlo% | bev% | PF | Kelly | p | flags |
|------|---|-----|------|------|----|----|---|-------|
| bb_squeeze_breakout\|USD_JPY\|ny | 20 | 40.0 | 21.9 | 26.6 | 2.12 | +0.212 | 0.11 | ---KF |
| trend_rebound\|USD_JPY\|ny | 10 | 30.0 | 10.8 | 39.4 | 1.41 | +0.088 | 0.71 | ---K- |
| sr_channel_reversal\|USD_JPY\|ny | 42 | 31.0 | 19.1 | 38.4 | 0.62 | -0.188 | 0.15 | N---- |
| fib_reversal\|USD_JPY\|asia | 41 | 24.4 | 13.8 | 38.6 | 0.56 | -0.195 | 0.86 | N---- |
| engulfing_bb\|USD_JPY\|asia | 34 | 32.4 | 19.1 | 36.9 | 0.61 | -0.207 | 0.23 | N---- |

**flags**: N=N≥30 / W=wlo>bev+3pp / P=p<2.5e-4 / K=Kelly>0.05 / F=WF同符号

注目:
- **bb_squeeze_breakout|USD_JPY|ny** は Kelly+0.212 かつ WF 同符号だが N=20 (基準未達)
  かつ Fisher p=0.11 (非有意)。既存 PAIR_PROMOTED strategy ([[quant-validation-label-audit-2026-04-23]]
  の promotion 時 BT) の現 live 観察だが、holdout 候補化には N不足。
- 他の全 cell は Kelly 負または wlo < bev、何らかの形で dead。

## Bonferroni 補正の確認

α_family = 0.05 / M = 340 → α_cell ≈ 1.47e-4 (厳密) / 2.5e-4 (pre-reg 保守寄り)
実測最小 p = 0.11 (bb_squeeze_breakout|USD_JPY|ny)
→ Bonferroni 未補正 α=0.05 でも **全 cell 棄却不可**。
過去 promotion を正当化したと思われるエッジは current 市場で shadow 消失。

## Scenario A interpretation

Pre-registration の binding rule:
> Scenario A (GO 0 + CANDIDATE 0): **全面 regime mismatch** 確定。
> - 現 shadow システム全体が current 市場で dead
> - [[pre-registration-label-holdout-2026-05-07]] H3 (category 降格) の確実性が極めて高い
> - 新戦略設計 (Phase 4) を即時着手判断材料

### 意味

1. **label / MTF / regime レベルの fine-tuning では救えない**
   - [[quant-validation-label-audit-2026-04-23]]: 方向一致 以外の候補 6 件 Bonferroni 棄却
   - 本 scan: どの cell slice でも Kelly>0 の統計的生存者なし
   - → 「どこかに生き残りがあるはず」という期待を data が否定

2. **Kelly 全体: -5,554 pips/month 推定は安定**
   - [[quant-validation-label-audit-2026-04-23]] の category-level Kelly ≤ 0
   - 本 scan で cell-level でも同様 → 集計バイアスではない

3. **ただし (current 市場で broken) ≠ (永続的に broken)**
   - regime が戻れば cell レベルで edge が再発する可能性
   - Phase 1 holdout は「今後 14d の market が同じか」の確認
   - 2 連続 holdout で Kelly<0 確定 → H3 GO で live-weight zero

## Implication for action

### DO

1. **[[pre-registration-label-holdout-2026-05-07]] を予定通り実行** (2026-05-07)
   - Phase 1 holdout: 方向一致 confirmatory test
   - H3: category Kelly Wilson 95% upper < 0 判定 (1st of 2)
2. **Phase 4 新戦略設計を着手** (regime-native strategies)
   - 現 17 strategies の何れも current regime で生存しないという data が
     逆に「current regime に合う別 entry 条件」の探索を正当化する
   - ただし開発方針は別 pre-registration doc で lock
3. **live-weight 現状維持** (既存 PAIR_PROMOTED / ELITE_LIVE は shadow 継続)
   - 本 scan は observational only、action trigger ではない
   - 降格 action は holdout 2 連続で初めて trigger

### DO NOT

- 本 scan の Kelly+0.212 cell (bb_squeeze_breakout|USD_JPY|ny N=20) を
  "見込みあり" として live 昇格させる — **post-hoc selection**, N 不足, p=0.11
- label 削除 / code 変更を先行させる — Phase 1 holdout を待つ
- "もう少しで" (p=0.11 など) の cell を別基準で救わない — pre-reg lock 違反

## Limitations

1. **N=2075 は 16 日分** (2026-04-08 → 2026-04-23)。短期 regime snapshot。
2. **BT_COST_cell** は spread p50 固定 (phase0 data)。時間変動 spread は考慮外。
3. **session 分割** UTC hour 単位、市場遷移帯 (11-13 UTC など) は粗い。
4. **WF 2-bucket** 16 日 → 8 日ずつ。regime 安定性の厳密検定ではない。

これら limitation は次の pre-registration で考慮。本 scan の binding rule は lock。

## References

- [[pre-registration-phase2-cell-level-2026-04-23]] (binding criteria)
- [[phase0-data-integrity-2026-04-23]] (データ健全性確認)
- [[quant-validation-label-audit-2026-04-23]] (label Bonferroni)
- [[pre-registration-label-holdout-2026-05-07]] (next step)
- [feedback_partial_quant_trap](/Users/jg-n-012/.claude/projects/-Users-jg-n-012-test/memory/feedback_partial_quant_trap.md)
