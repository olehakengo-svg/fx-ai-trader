# Cell Deepdive Audit — 7 Strategies (Weekly) — 2026-07-26

**Tool note**: `tools/cell_deepdive_audit.py` は repo に存在しないため、前週までと同一の ad-hoc 再実装 (`_run_deepdive_2026_07_26.py`, `cell_edge_audit.py` v2/v3 methodology) を Render PROD API に対して実行。`--regime-source` オプションは非対応 (regime / hour_bin / mode 軸なし、cell = entry_type × pair × direction [v2] / + session [v3])。task 記載の regime×hour_bin×mode 分解は本ツールの対象外。

- **Data source**: `https://fx-ai-trader.onrender.com/api/demo/trades?limit=50000` (PROD, HTTP 200 / 42MB)。ローカル demo_trades.db は STALE (memory rule 準拠)。`?limit` 明示必須 (無指定だと 50 件のみ返る)
- **Window**: 365d 指定、実データ span 2026-04-02 → 2026-07-26 (約 17 週)
- **Filters**: XAU 除外 / dedup_violation=1 除外 / outcome ∈ {WIN, LOSS}
- **Meta**: fetched 14,127 / target raw 612 / dedup 除外 353 / non-WL 除外 20 / **clean N = 239** / m_global v2 = 4, v3 = 1

## PAIR_PROMOTED Candidates

**1 件** (前週と同一セル、2 週連続)。Gate = N≥20 ∧ Wilson_lo>0.50 ∧ p_bonf<0.05。

| # | strategy | pair | session | hour_bin | regime | mode | direction | N | WR | Wilson_lo | EV_net | PF | p_bonf | kelly | wf_stable |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | sr_anti_hunt_bounce | EUR_JPY | (集約) | (集約) | (集約) | (集約) | BUY | 38 | 71.1% | **0.552** | +4.29 | 2.35 | **0.0378** | 0.409 | ✅ |

session/hour_bin/regime/mode は本ツール未分解のため集約値。

### 🔴 昇格クロスの品質監査 — 前週の persistence 条件は「未充足」

前週 (07-20) にこのセルが初の 3 ゲート通過。その際 Live 移行前の保留条件 (b)「追加 N がクラスタ外に分散し WR が持続するか」を課した。**今週データで検証した結果、条件 (b) は満たされず、むしろエッジは弱化した。**

- **全体は依然 3 ゲート通過だが弱化**: N 35→38 (+3)、WR 74.3%→71.1%、Wilson_lo 0.579→**0.552**、EV +5.01→+4.29、PF 2.66→2.35、p_bonf 0.0081→**0.0378** (m_global v2 が 2→4 に増え Bonferroni が厳格化、まだ <0.05 だが余裕が急減)
- **de-clustering で gate FAIL**: 07-17 の単日 6W/0L クラスタを除くと **N=32 / WR 65.6% / Wilson_lo = 0.483 < 0.50** → 昇格ゲート未通過。**この候補は依然として単日 hot-streak が load-bearing**。前週から構造は不変どころか、クラスタ寄与への依存が確定
- **新規 3 trade は 1W/2L で持続を否定**: 07-22 (+2.8p WIN) / 07-23 (−7.8p LOSS) / 07-24 (−7.1p LOSS)。勝ちは micro (+2.8p)、負けはその ~2.7 倍 (−7.8/−7.1p)。**bounce-scalp の非対称ペイオフ (tight TP / wide SL) が実データで顕在化** = friction 感応度の懸念 (前週指摘) が新規サンプルで実証
- **依然ほぼ全て shadow (35/38)**、直近 5 本は全て is_shadow=1。spread/slippage 未検証は不変

## Eligible cells (N≥20, v2)

| cell | N | WR | Wilson_lo | EV_net | PF | p_bonf | kelly | wf_stable |
|---|---|---|---|---|---|---|---|---|
| sr_anti_hunt_bounce \| EUR_JPY \| BUY | 38 | 71.1% | **0.552** | +4.29 | 2.35 | 0.0378 | 0.409 | ✅ |
| sr_anti_hunt_bounce \| EUR_USD \| SELL | 24 | 62.5% | 0.427 | −5.92 | 0.26 | 0.883 | 0 | ❌ |
| sr_anti_hunt_bounce \| GBP_JPY \| BUY | 28 | 50.0% | 0.326 | −5.02 | 0.40 | 1.0 | 0 | ❌ |
| sr_anti_hunt_bounce \| USD_JPY \| BUY | 22 | 59.1% | 0.387 | −1.19 | 0.52 | 1.0 | 0 | ❌ |

v3 (＋session) eligible: `sr_anti_hunt_bounce | EUR_JPY | Tokyo | BUY` が初の N≥20 到達 (N=20 WR70% Wilson_lo 0.481 EV+9.37 p_bonf 0.074) — **Tokyo session が EUR_JPY BUY エッジの主産地**だが、単独 gate は未通過 (Wilson_lo<0.50)。これも上記クラスタと重複母集団。

## 前週比 (2026-07-20 → 2026-07-26)

| strategy | clean_N | ΔN | WR | EV_net | PF | 前週PF |
|---|---|---|---|---|---|---|
| sr_anti_hunt_bounce | 152 | +15 | 53.3% | −2.24 | 0.60 | 0.62 ↓ |
| sr_liquidity_grab | 1 | 0 | — | — | — | — (死蔵) |
| cpd_divergence | 0 | 0 | — | — | — | — (17週連続0) |
| vdr_jpy | 17 | +1 | 82.4% | +9.45 | 6.05 | 5.32 ↑ |
| vsg_jpy_reversal | 37 | +1 | 67.6% | +1.25 | 1.27 | 1.40 ↓ |
| rsk_gbpjpy_reversion | 27 | +4 | 40.7% | −5.97 | 0.35 | 0.41 ↓ |
| mqe_gbpusd_fix | 5 | 0 | 60.0% | +6.76 | 2.48 | 2.48 (停滞) |

合計 clean N: 218 → 239 (**+21/週**、前週 +25 から減速)。増加の 15/21 は sr_anti_hunt_bounce だが、そのうち EUR_JPY BUY への寄与は +3 のみで残りは負け cell (GBP_JPY/EUR_USD/USD_JPY) の N 増。

## Notable

- **vdr_jpy が最健全** — 戦略集計 N=17 WR82.4% Wilson_lo **0.590** EV+9.45 PF6.05 wf✅。**唯一 Wilson_lo>0.50 かつ pip が厚い (micro-scalp でない)** エッジで、EUR_JPY BUY のような単日クラスタ依存も見えない。ただし cell 単位 (USD_JPY BUY 中心) は N=10 で eligible 未達。発火レート改善で 4-6 週後に候補化見込み — **次の watch 対象筆頭**
- **sr_anti_hunt_bounce aggregate は net-negative 継続** — PF0.60 / EV−2.24。EUR_JPY BUY の黒字を GBP_JPY BUY (PF0.40) / EUR_USD SELL (PF0.26) / USD_JPY BUY (PF0.52) が相殺。相殺構造は不変で今週さらに悪化 (負け cell の N が増加)
- **rsk_gbpjpy_reversion 悪化** — N 23→27、WR 43.5%→40.7%、PF 0.41→0.35 と 4 週連続で下降。net-negative の掘り下げが続いており demote 検討水準 (Rule 2 対象候補)
- **停滞警告 (継続)**: cpd_divergence 17 週連続 0 発火 / mqe_gbpusd_fix clean N=5 で 5 週連続増加ゼロ (raw 87 の 94% が dedup/non-WL 除外) / sr_liquidity_grab raw 2・clean 1 で実質死蔵。**signal 発火経路調査を別タスク化すべき段階 (3 週連続提言)**

## 判定

**候補 1 件は 2 週連続で形式上 gate 通過するが、de-clustering で Wilson_lo 0.483<0.50 に崩れ、新規 3 trade も 1W/2L で persistence を否定。Pre-reg LOCK は継続 (無害) だが、Live 昇格は引き続き保留 — 保留条件 (a)(b) が今週明示的に未充足と確定。**

推奨アクション:
1. **Pre-reg LOCK 継続 / 更新**: `sr_anti_hunt_bounce | EUR_JPY | BUY` は既に LOCK 済なら現状値 (N=38 Wilson_lo0.552 de-clustered 0.483) を追記。未起票なら shadow 監査として起票は可 (実害なし) だが、**「de-clustered gate fail」を昇格ブロッカーとして明記**すること
2. **Live フルロット昇格は非推奨 (据え置き)**: 07-17 クラスタ除外で gate を割る限り Rule 1 全ロット昇格は不可。次週以降、クラスタ外の追加サンプルが黒字方向に蓄積し de-clustered Wilson_lo が 0.50 を回復するかを persistence 条件として継続監視
3. **watch 対象を vdr_jpy に移行**: 単日クラスタ依存のない最健全エッジ。USD_JPY BUY cell の N≥20 到達を次の候補化トリガとして注視
4. **rsk_gbpjpy_reversion の demote 判断** を別途検討 (4 週連続悪化、Rule 2)
5. **発火枯渇 3 戦略 (cpd / mqe / sr_liquidity_grab)** の signal 経路調査を別タスク化 (継続提言)
