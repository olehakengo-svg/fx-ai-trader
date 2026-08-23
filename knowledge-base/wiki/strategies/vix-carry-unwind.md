# VIX Carry Unwind — VIX急騰キャリー巻き戻し

## Stage: PAIR_DEMOTED (2026-08-03 Overlap pilot 早期 demote — 下記参照。shadow 蓄積は継続)

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
| vix_carry_unwind | all | **26** | **53.8%** | **−46.9 pip** |

Data source: /api/demo/stats?date_from=2026-04-08 (**refreshed 2026-08-20**; supersedes the 2026-04-20 N=2 row).

**2026-08-20 状況**: 08-03 の PAIR_DEMOTED 執行以降、**新規 live fill なし**。累計は N=26 / −46.9 pip で 07-31 quant-eval 時点から不変 — 直近 30d 窓に 1 本 (07-30 の −30.1 pip SL_HIT) が残っているだけで、これは demote 前のトレード。**demote は意図通り効いている** (live 発火停止、shadow emit は継続)。再昇格条件は下記 08-03 節の R1 のまま。

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

## 2026-07-31 証拠更新 (quant-eval 全数監査) — 早期 demote 推奨、user 決裁待ち
checkpoint (live SELL N≥20) は未達 (N≈14) だが、07-07 継続裁定の根拠 2 点が悪化:
1. **live**: 累計 N=26 PnL=−46.9p PF=0.66、月次 3/4 負 (04:−21.3 / 05:+27.7 / 06:−19.0 / 07:−34.3)。
   07-30 に −30.1p (SL_HIT) を追加
2. **shadow エッジの減衰** (07-07 裁定の根拠 3「shadow 正 EV」が崩壊): 04 月 +537p (n=40) →
   05 月 −98p (n=35) → 06 月 +5p (n=20) → 07 月 **−123p (n=84)**。05〜07 累計 −216p/n=139 =
   post-April の shadow は一貫して負。全期間集計 +320p は April regime の遺産
3. 7 月 live 出血 −84.4p のうち vix 単独で −34.3p (最大の現役出血源、[[quant-eval-2026-07-31]] §1)

**推奨**: checkpoint を待たず demote (Overlap pilot 撤去 + PAIR_DEMOTED 復帰)。07-07 裁定
「demote する場合は user 決裁」に従い執行は保留 — user 承認で即実装可。

## 2026-08-03 早期 demote 執行 (rule:R2, user 決裁「進めて」)
上記推奨を user 承認 → **PAIR_DEMOTED 復帰を執行**。`_PAIR_PROMOTED` 除外 /
`_PAIR_SESSION_FILTER`・`_PAIR_LOT_BOOST` 撤去 / MIN-lot 1000u 契約 code は再昇格時のため残置 /
shadow emit 不変更 (原則3)。registry `vix-sell-pilot-recheck` は resolved 化 (checkpoint 消化)。
追加証拠: 08-01〜03 shadow n=7 −17p (減衰継続)。
再昇格 = R1 (直近 90d shadow N≥30 EV>0 ∧ Wilson_lo>34.4% ∧ Bonferroni ∧ 365d cell BT ∧ pre-reg + user 承認)。
pin: `tests/test_vix_pilot_demote_pin.py` / 詳細: [[vix-pilot-early-demote-2026-08-03]]
