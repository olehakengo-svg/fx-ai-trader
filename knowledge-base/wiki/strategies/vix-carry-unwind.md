# VIX Carry Unwind — VIX急騰キャリー巻き戻し

## Stage: SENTINEL (v8.5, 低頻度 年2-5回)

> ⚠️ **2026-07-02 zero-fire 診断 (Overlap pilot)**: 06-18 GRAIL 撤去以降 Overlap live fill 0 の原因は **Overlap 窓にシグナル自体が来ていない**こと (05-13〜07-02 で Overlap 4/54 件 = 7.4%、シグナルは London 63% / NY 26% にクラスタ)。session filter は `_is_promoted` 内で実行時評価され正常動作 (窓外→shadow を本番実証済み)。ただし「窓内→live」の現行コード実証は N=0 (旧コードで 05-20 の 1 件のみ)。期待レート月 ~2 件 → demote gate (N≥10) 到達に ~5 ヶ月。副次発見: Aggregate Kelly Gate は max(0,·) クリップで死にゲート (P1)。
> 詳細: [[zero-fire-diagnosis-carrydip-vix-2026-07-02]]

## Hypothesis
VIX急騰（90pctile超）時にキャリートレード巻き戻しが加速し、JPY急騰が発生。初動1週間が最も急速（Brunnermeier 2009, IMF 2019）。

## Academic Backing
| Paper | Finding | Confidence |
|-------|---------|-----------|
| [[brunnermeier-2009]] | キャリー通貨リターンは負のスキュー。巻き戻しは自己強化的スパイラル | ★★★★★ |
| [[menkhoff-2012]] | グローバルFXボラリスクが通貨リターンの90%を説明 | ★★★★★ |
| IMF WP/19/136 | VIX 90pctile超で巻き戻し速度3倍。初動1週間が最急速 | ★★★★ |

## Quantitative Definition
```python
# Trigger: VIX daily close > VIX 90-day 90th percentile
# AND VIX daily change > +20%
# Entry: USD/JPY SELL (JPY long) at next day open
# Exit: 5 trading days後 or TP到達
# SL: ATR(1D) × 2.0 (~200pip)
# TP: ATR(1D) × 3.0 (~300pip)
# 対象: USD/JPY, AUD/JPY
```

## Key Characteristic
**低頻度・高インパクト**: 年2-5回のイベント。1回で100-500pipの動き。

## Friction Viability
日次→週次保有のため摩擦は無視可能。

## Integration
vol_momentumの「VIXブーストモード」として統合が最適。独立戦略の価値は頻度から見て低い。

## Live Performance (post-cutoff, 2026-04-08〜)
| Strategy | Pairs | N | WR | PnL |
|---|---|---|---|---|
| vix_carry_unwind | all | 2 | 0.0% | -30.9 pip |

N=2 is below judgment threshold (min N=10). Low-frequency strategy — observe over full VIX cycle.
Data source: /api/demo/stats?date_from=2026-04-08 (2026-04-20)

## Related
- [[research/index]]
- [[vol-momentum-scalp]]
- [[agg-kelly-gate-raw-fix-minlot-bypass-2026-07-02]] — Overlap pilot (1000u 固定) は Aggregate Kelly Gate の min-lot bypass 対象 (2026-07-02 user 決裁)。lot が 1000u を超えたら bypass 自動失効

## 2026-07-07 USD_JPY SELL セルの R2 基準抵触 → pilot 継続裁定 (user 承認)
30d clean live SELL: N=10 WR=60% EV=−1.90 −19.0p、Wilson_lo 31.3% < BEV 34.4% = **R2 demote 基準に形式的に該当**。しかし以下の理由で **demote せず Overlap pilot 継続** (user「進めていいよ」2026-07-07):
1. pilot は user 承認済み R1 例外 (live N 蓄積が目的) — 薄い R2 統計 (Wilson 差 3.1pp、N=10 最小値) で user の R1 決裁を覆さない
2. T3 診断 ([[payoff-asymmetry-diagnosis-2026-07-07]]) により負 EV の主因は **exit 執行 (capture ~14% = 全戦略最悪、未捕獲 MFE 41.8p)** であり entry thesis の死ではない — exit-repair ([[exit-repair-tp-sl-prereg-2026-07-07]]) の対象セル
3. shadow 集計は +0.96 (N=60) で全戦略中の正 EV 3本の一角 (M6 母集団の初期候補)
4. 1000u floor でのコストは −19p/30d ≈ 実損軽微、live N 蓄積の情報価値が上回る

**再評価 checkpoint**: live SELL N≥20 or 2026-08-31 (registry `vix-sell-pilot-recheck`、live_count_decision で毎日監視)。再評価時に EV/Wilson_lo/BEV を再判定し、demote する場合は user 決裁。
