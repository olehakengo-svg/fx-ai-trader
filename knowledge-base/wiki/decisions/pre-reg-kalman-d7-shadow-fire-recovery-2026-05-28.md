# Pre-Registration: Kalman D7 Shadow-Fire Recovery (post 29ec95cb)

**LOCK Date**: 2026-05-28
**Type**: Post-deploy fix verification pre-reg
**Category**: Observability / Silent-block recovery
**Status**: 🔒 LOCKED — silent-block-fix が Kalman D7 にも効くかの単独判定基準。HARKing 防止のため事後改定禁止。

## 1. Context

- Kalman D7 v17/v18f/v18e は 2026-05-20 (commit `1972bd8b`) deploy 以降 **8 日間で 0 fire** だった ([project_kalman_d7_regime_bound_live_2026_05_20](../../../memory/project_kalman_d7_regime_bound_live_2026_05_20.md))
- 2026-05-28 セッションで end-to-end pipeline probe (ssh から `compute_daytrade_signal` 手動呼び出し @ bar 2026-05-27 05:00 UTC) → 3 candidate (`po_dn_flip` / `ema75_break` / `trail_atr`) が `live_promote_emit_signals` payload に正常に乗ることを確認
- 直後に並行 session が commit **`29ec95cb`** (`fix(gates): shadow-eligible bypass for recent_emit/spread_guard/session_pair/velocity/spike`) を投入 — SENTINEL/PHASE0_SHADOW 戦略が 5 gate で silent drop されていた構造バグを修正
- Render deploy 2026-05-28 04:59 UTC live
- 親 pre-reg は `eurgbp_daily_mr` と "Cluster A SENTINEL 合計" のみで、**Kalman D7 単独の判定基準が無い** → 本書で補完

## 2. Hypothesis

`29ec95cb` の 5 gate bypass (recent_emit / spread_guard / session_pair / velocity_up / velocity_down / spike) は `_UNIVERSAL_SENTINEL` 全体に対する均一修正なので、Kalman D7 もこの fix の対象 (Cluster A SENTINEL に含まれる)。

→ deploy から 24h 以内に Kalman D7 (3 variant 合算) が **shadow trade として複数回 fire** するはず。fire しなかった場合、Kalman 固有の別ブロッカー (例: PO regime ガード本体 / `_kalman_d7_indicators` early return / `_open_shadow_emit_trade` 経路) が残存。

## 3. Threshold (LOCKED)

### 追記 2026-05-28 17:46 JST (option B 採択):
本 pre-reg 設置直後、user 判断で **Render env `KALMAN_D7_LIVE_ENABLE=1`** を MCP 経由で投入 (deploy `dep-d8c01ocm0tmc73etpof0` @ 2026-05-28 08:46 UTC = 17:46 JST)。Shadow ramp は飛ばして即 LIVE 化。

→ judgement bar も `oanda_audit` 内 `is_live=1 AND bridge_status='filled'` を見る必要がある。

### 追記 2026-05-28 18:xx JST (lot sizing 0.1× → 0.5×):
user 判断で `_PAIR_LOT_BOOST` に 3 entry 追加:
- `("kalman_d7_po_dn_flip",  "USD_JPY"): 0.5`
- `("kalman_d7_ema75_break", "USD_JPY"): 0.5`
- `("kalman_d7_trail_atr",   "USD_JPY"): 0.5`

3 variant 同時発火 → 合計 **1.5× base lot exposure / signal**。BT 期待 PF が PF=3.866/2.087/1.181 のため 0.5× は user 判断で妥当 (vix_carry 1.0× の半分)。Live N=0 のままなので Rule 1 (Live N≥30) 未充足、`R1-EXCEPTION` 扱い。

退避条件 pre-reg (追加):
- Live N≥10 達成時点 EV<0 → 0.1× へ自動降格 (watchdog 既存 `tools/volume_live_promotion_watchdog.py` のしきい値に従う)
- 連続 3 trade SL (3 variant 同時 SL = 3 件 SL カウント) → user 手動 review、即時 env=0 で Shadow 戻し検討

### Primary (judgement at 2026-05-29 17:46 JST = LIVE-env deploy + 24h)

```
SUCCESS (LIVE fire 経路まで通った):
  oanda_audit table で
    entry_type LIKE 'kalman_d7%'
    AND is_live = 1
    AND bridge_status = 'filled'
    AND created_at >= '2026-05-28 08:46:00+00:00'  -- LIVE env deploy
    COUNT(*) >= 1

PARTIAL (29ec95cb の shadow fix は効いた、LIVE 経路だけ別ブロッカー):
  上記 LIVE COUNT == 0
  AND
  oanda_audit kalman_d7* shadow (is_live=0) COUNT >= 3
  → KALMAN_D7_LIVE override path (_kalman_d7_live_eligible / [KALMAN_D7_LIVE] log) の問題
  → Render log で `[KALMAN_D7_LIVE]` 文字列の有無確認、無ければ env が反映されてない

FAIL (Shadow も LIVE も 0):
  shadow COUNT == 0 AND LIVE COUNT == 0
  → 29ec95cb fix 自体が Kalman 経路に効いていない (Cluster A SENTINEL 想定外)
  → P0-5: `KalmanD7Base.evaluate` debug print PR 復活
```

### 期待値の根拠

- MASSIVE USDJPY M15 replay @ 2026-05-21〜28 → 27 PO-UP transition、**7 件が全フィルタ通過** ([調査ログ参照](#))
- 24h 期間中の PO-UP transition 期待値 = 7件 × (24/168) ≈ **1.0 件**
- 1 transition 検出 → 3 variant emit → shadow 3 行
- 30s tick × ~13min 検出窓 = ~26 評価機会 (transition bar が "last" でいる間)
- Conservative threshold: **3 行** (= 1 transition × 3 variant、検出率 100% 想定)

### Secondary (sanity check)

```
evaluated_candidates table で
  strategy_name LIKE 'kalman_d7%'
  AND created_at >= '2026-05-28 04:59:00+00:00'
  COUNT(*) >= 30
```

evaluated_candidates は side-channel 通過前に書かれる (compute_daytrade_signal 内 `_log_cands`)。これが 0 のままなら、gate fix 以前の更に上流 (`evaluate()` 自体が None 返し続けている) でブロック。

## 4. Measurement Command

```bash
ssh -o StrictHostKeyChecking=no srv-d6va1of5r7bs73en10vg@ssh.oregon.render.com 'python3 -c "
import sqlite3, json
c = sqlite3.connect(\"/var/data/demo_trades.db\"); c.row_factory = sqlite3.Row
cur = c.cursor()
cutoff = \"2026-05-28 08:46:00\"  # LIVE-env deploy (option B 採択後)

cur.execute(\"\"\"
SELECT entry_type, COUNT(*) n, SUM(CASE WHEN is_live=1 THEN 1 ELSE 0 END) live,
       SUM(CASE WHEN bridge_status=\x27filled\x27 THEN 1 ELSE 0 END) filled,
       MIN(created_at), MAX(created_at)
FROM oanda_audit
WHERE entry_type LIKE \x27kalman_d7%\x27 AND created_at >= ?
GROUP BY entry_type
\"\"\", (cutoff,))
print(\"oanda_audit kalman_d7 post-LIVE-env:\")
for r in cur.fetchall(): print(\" \", dict(r))

cur.execute(\"\"\"
SELECT strategy_name, COUNT(*) n, SUM(selected) sel
FROM evaluated_candidates
WHERE strategy_name LIKE \x27kalman_d7%\x27 AND created_at >= ?
GROUP BY strategy_name
\"\"\", (cutoff,))
print(\"\\nevaluated_candidates kalman_d7 post-29ec95cb:\")
for r in cur.fetchall(): print(\" \", dict(r))
" 2>/dev/null'
```

## 5. Decision Tree (post 2026-05-29 14:00 JST)

| `oanda_audit` Kalman 行 | `evaluated_candidates` Kalman 行 | 判定 | 次手 |
|---|---|---|---|
| ≥ 3 | ≥ 30 | ✅ **SUCCESS** | fix 完了。Kalman を `core-memories.md` に "8日silent drop → 29ec95cb で回復" として記録 |
| 0 | ≥ 30 | 🟡 **PARTIAL** | evaluate() は走ってる、shadow への path で別ブロッカー → P0-5: `_open_shadow_emit_trade` / `_tick_entry` の Kalman 通過点を計装 |
| 0 | 0 | 🔴 **FAIL** | evaluate() 自体が None 返し続け → P0-5: `KalmanD7Base.evaluate` に debug print PR (前回 session で予告した内容) |
| 1〜2 | ≥ 10 | 🟠 **INCONCLUSIVE** | 観測 48h まで延長、明後日 14:00 JST 再判定 |

## 6. Non-goals

本 pre-reg は **fix の効果検証** のみ。Kalman D7 自体の edge 検証 (PF/WR/Wilson 等) は対象外 (deploy 時点で BT 10.5mo の証跡あり、shadow N 蓄積後に別途 Phase 2 で再評価)。

## 7. References

- 親 commit: [`29ec95cb`](../../../) `fix(gates): shadow-eligible bypass for recent_emit/spread_guard/session_pair/velocity/spike [rule:R3]` (2026-05-28 04:55 JST)
- 診断計装: [`57d1570d`](../../../) `feat(diag): expose _block_counts + SENTINEL block-point logging [rule:R3]`
- 親 pre-reg (Cluster A SENTINEL 全体): 29ec95cb commit message 内
- Kalman D7 LIVE 投入経緯: [project_kalman_d7_regime_bound_live_2026_05_20](../../../memory/project_kalman_d7_regime_bound_live_2026_05_20.md)
- 2026-05-28 セッション pipeline probe ログ: チャット履歴 (compute_daytrade_signal manual call @ bar 2026-05-27 05:00 UTC → 3 emit confirmed)
