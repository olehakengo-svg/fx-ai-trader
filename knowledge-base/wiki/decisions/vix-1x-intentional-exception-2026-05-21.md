# Pre-reg: vix_carry_unwind × USD_JPY 1.0x intentional exception (2026-05-21)

**Rule classification**: R1-EXCEPTION (intentional, Kalman D7 型 precedent)
**Author**: goto (user judgment) + Claude (audit + implementation)
**Effective**: 2026-05-21 (commit pending)
**Supersedes**: [vix-overlap-pilot-prereg-2026-05-13.md](./vix-overlap-pilot-prereg-2026-05-13.md) (0.05x R2 pilot)

---

## Decision

`_PAIR_LOT_BOOST[("vix_carry_unwind", "USD_JPY")]` を **0.05 → 1.0 (20倍)** に引き上げ。Tier 維持 (PAIR_PROMOTED)、session_filter (Overlap UTC 12-16) 維持。

## Rule 1 violation 認識

CLAUDE.md Rule 1 (lot↑) は以下を要求するが、本変更時点で **3 項目すべて未充足**:

| Rule 1 要件 | 現状 (2026-05-21) | Gap |
|---|---|---|
| Live N ≥ 30 | N=12 (90d rolling) | -18 trades |
| Bonferroni 有意 (BF_lo ≥ 0.40 相当) | BF_lo=0.165 (direction cell, N=84 live+shadow統合) | gap ~0.235 |
| Pre-reg LOCK (lot↑用) | 0.05x 用は存在、1.0x 用は本 doc で新規作成 | この doc で充足 |

これは [Kalman D7 LIVE 2026-05-20](../../../../.claude/projects/-Users-jg-n-012-test/memory/project_kalman_d7_regime_bound_live_2026_05_20.md) と同じ **discretionary edge / user judgment 例外** に該当。memory に動機を記録 (`project_vix_carry_1x_intentional_exception_2026_05_21`)。

## 動機 (データ駆動 vs 感情 の自己宣言)

主にデータ駆動:

- ✅ **PAIR_PROMOTED で実エッジ判定済み** (USD_JPY/SELL 単独 cell, concentration_top_pct=100%)
- ✅ **Shadow 30d N=66, WR=24.2%, avg_net=+7.00pip, PnL=+461.8** — pip EV は明確にプラス
- ✅ **Live 30d N=10, WR=70%, PnL=+37.3** (90d N=12 PnL=+6.4) — 過去 60d 前の損失 2 件を吸収して直近 30d は回復
- ✅ **WF h1=+15.56** — 前半は強い
- ✅ **設計仮説 (Brunnermeier 2009 VIX carry unwind) と整合**

副次的に conviction:

- ⚠️ Wilson_lo gate (0.40) は WR≈30% の low-WR / high-R 戦略では **数学的に永久に到達不能** — Gate 設計と戦略タイプのミスマッチを user が認識
- ⚠️ WF h2=-2.58 の degradation は存在するが、unique_days=13 で 1 日 5.9 件発火の集中度ゆえ統計ノイズの可能性も
- ⚠️ 過去 demote 履歴 (Live N=7 EV=-6.04 Wilson_lo=8.22%) は 0.05x R2 pilot 復活で回復した実績

## 監視 (safety net)

- **既存 watchdog**: `tools/volume_live_promotion_watchdog.py` の WATCHED_CELLS に `vix_carry_unwind × USD_JPY` 登録済み (Live N≥10 EV<0 で自動 demote)。1.0x 化後も同一 cell に対して継続発動。
- **Pre-reg trigger conditions** (本 doc 固有):
  - Live N≥15 で EV<0 → 即時 demote (watchdog 10 件閾値より厳しい個別ルール)
  - Live N≥20 で Wilson_lo<0.20 → 0.25x に降格
  - Live N≥30 で Bonferroni 有意化失敗 (BF_lo<0.25) → 0.50x に降格、再評価
- **Manual review schedule**: Live +10 trade 経過時点 (推定 2-3 週後) に再監査

## 期待値 (pre-reg)

30d 期待 PnL: **+746pip 相当** (現状 30d Live +37.3pip × 20倍。session_filter で trade 回数同一前提)
30d 最悪 DD 推定: **-60pip** (連続 3 連敗想定、SL 20pip × 1.0x lot)
ロット倍率: 0.05x (R2 pilot) → 1.0x (Standard)

これらの数字は **本 doc 作成時点での予測**。N+15 trade 後に実測と比較してドリフト評価。

## 撤退条件 (post-mortem trigger)

以下のいずれかで本 1.0x exception を 0.25x or 0.05x に降格 + post-mortem 作成:

1. Live N+15 (累計 N≥27) 時点で cumulative PnL<0
2. Live N+5 (累計 N≥17) で連続 3 連敗かつ DD ≥ -100pip
3. WF h2 が h1 の 50% を下回り続ける (現状 h1=+15.56 / h2=-2.58 ratio -17%)
4. session_filter Overlap 外で発火が観測される (filter leak)

## 関連

- 上位 strategy default: `_STRATEGY_LOT_BOOST["vix_carry_unwind"] = 1.5` (180日BT N=103 EV=+0.521)
- session filter: `_PAIR_SESSION_FILTER[("vix_carry_unwind", "USD_JPY")] = {"Overlap"}` (UTC 12-16)
- watchdog: `tools/volume_live_promotion_watchdog.py` (Render cron 経由で定期実行)
- 監査経緯: 2026-05-21 audit conversation (Q1-Q3 audit, Post-London 2026-05-20 report 検証)
