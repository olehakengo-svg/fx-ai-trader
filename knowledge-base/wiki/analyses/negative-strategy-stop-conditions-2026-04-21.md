# Negative Strategy 止血条件 — 2026-04-21

**目的**: post-Cutoff 観察期間における negative 戦略の明示的停止基準。感情的な再昇格判断を防ぐ。

---

## 対象戦略と現状 (2026-04-21 snapshot)

| 戦略 | Tier | Shadow post-cut | Live post-cut | リスク |
|---|---|---|---|---|
| bb_rsi_reversion | SCALP_SENTINEL + PAIR_DEMOTED (EUR_JPY/EUR_USD/GBP_USD/USD_JPY) | N=117 EV=-1.76 | N=4 EV=+1.52 (USD_JPY, timing lag) | 中 — 一部 LIVE 継続 |
| fib_reversal | FORCE_DEMOTED | N=62 EV=-1.37 | N=0 | 低 — 全 shadow |
| macdh_reversal | FORCE_DEMOTED | N=23 EV=-3.59 | N=0 | 低 — 全 shadow |
| sr_fib_confluence | FORCE_DEMOTED | N=43 EV=-6.37 | N=0 | 低 — 全 shadow |

---

## 明示的停止基準

### bb_rsi_reversion (最優先監視)

**現状判断**: SCALP_SENTINEL 継続。Shadow が全ペアで強負だが FORCE_DEMOTED 未適用。

**FORCE_DEMOTED 移行条件 (いずれか充足で即時)**:

| 条件 | 判断 |
|---|---|
| Shadow 累計 N≥150 AND 7日間 EV < -0.5 pip/trade | FORCE_DEMOTED |
| LIVE (新規ペア) N≥15 AND 7日間 mean_pnl < -0.5 pip | PAIR_DEMOTED 追加 |
| LIVE 累計 N≥30 AND WR < 40% | SCALP_SENTINEL → FORCE_DEMOTED |

**再昇格禁止条件 (以下が全て揃うまで昇格不可)**:
- Shadow 7日間 EV ≥ +0.3 (連続14日以上)
- 365d BT 対象ペア EV ≥ +0.3
- 市場レジームが trending dominant (range_tight > 50% の期間は見送り)

### fib_reversal

**現状**: FORCE_DEMOTED。Shadow post-cut EV=-1.37 (N=62)。

**再昇格解禁条件 (全条件必要)**:
- Shadow 連続14日間 EV ≥ +0.5 (N≥20 per 14d)
- 365d BT 対象ペアで EV > +0.3
- Phase 5 優先度リスト (wiki/sessions) で P1 以上に昇格したとき

**再昇格手順**: SCALP_SENTINEL 試用 → Live N≥30 確認 → PAIR_PROMOTED 審査

### macdh_reversal

**現状**: FORCE_DEMOTED。Shadow EV=-3.59 (N=23) — 全期間で強負。

**再昇格禁止**: 365d BT で複数ペア EV > 0 が出るまで凍結。BT 実施すら不要。

### sr_fib_confluence

**現状**: FORCE_DEMOTED。Shadow EV=-6.37 (N=43) — 壊滅的。

**再昇格禁止**: shadow N≥100 かつ連続30日 EV > 0 になるまで凍結。事実上永久凍結。

---

## 自動監視のプロトコル (手動チェック)

セッション開始時に以下を確認:
```
curl <RENDER_URL>/api/demo/trades?limit=500 | python3 - <<'EOF'
# bb_rsi_reversion の LIVE trades (is_shadow=0) を7日分集計
# mean_pnl < -0.5 → 即座に PAIR_DEMOTED 追加
EOF
```

---

## 根拠 (Phase 3 教訓の適用)

前セッション Phase 3 で「shadow を live と誤認して production に harm を加えようとした」ことを教訓に、本文書は:
1. shadow の負けを live の問題と混同しない
2. 実際の live が正 EV であっても shadow の構造負 EV を無視しない
3. 停止条件を事前宣言することで観察バイアスを排除する

参照: [[lesson-shadow-contamination]], [[lesson-backfill-task-pivot-2026-04-21]]
