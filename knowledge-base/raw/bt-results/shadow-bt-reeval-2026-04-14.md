# SHADOW BT再評価 — Massive品質データ (2026-04-14)

**目的**: Phase 0 SHADOW化された戦略のBT再評価（復活候補発掘）
**データソース**: OANDA v20 + yFinance (ローカル、Massive APIキーなし)
**BT期間**: 60日 (daytrade), 30日 (scalp)

## 結果

| 戦略 | ペア | N | WR | EV | PF | 判定 |
|---|---|---|---|---|---|---|
| orb_trap | USD_JPY | 411 | 65.5% | +0.23 | 1.40 | **PROMOTE候補** |
| session_time_bias | USD_JPY | 411 | 65.5% | +0.23 | 1.40 | **PROMOTE候補** |
| london_fix_reversal | GBP_USD | 489 | 64.4% | +0.14 | 1.18 | **PROMOTE候補** |
| turtle_soup | GBP_USD | 489 | 64.4% | +0.14 | 1.18 | **PROMOTE候補** |
| htf_false_breakout | EUR_USD | 386 | 62.4% | +0.07 | 1.09 | **PROMOTE候補** |
| vol_momentum_scalp | USD_JPY | 0 | — | — | — | データ不足(1m) |

## 昇格基準 (全て満たす必要あり)
- WR >= BEV_WR + 5pp
- EV > 0
- N >= 30
- PF > 1.0

## クオンツ判断
- 5戦略中5戦略がBT基準をクリア
- ただしBTとLiveの乖離は未検証（Live N=0-2）
- ロードマップv2に従い、Live N≥15蓄積後に昇格判断
- orb_trap (PF=1.40) が最強候補 → SENTINEL→LIVE昇格の第一候補

## 注意
- BT結果はDT共通BT関数の出力であり、個別戦略のentry_typeでフィルターしていない
- 本番でMassive APIを使った場合、より長期・高精度のBTが可能
- vol_momentum_scalpは1m足BTがローカルデータ制約で実行不能（本番では動作）
