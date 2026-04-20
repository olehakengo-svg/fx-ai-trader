# ema_trend_scalp / trend_rebound — Live Pair-Level Breakdown (2026-04-20)

**Data source**: `GET /api/demo/trades?limit=5000&status=closed` (Render prod) @ 2026-04-20
**Sample scope**: `is_shadow=0` (Live), XAU excluded, closed trades only
**Trigger**: Post-P2-merge Kelly 分析で ema_trend_scalp edge=-0.353 / trend_rebound edge=-0.455 が aggregate edge=-0.1348 の主因と判明 ([[shadow-baseline-2026-04-20]] Phase 2 追記)

## なぜこのページ (Purpose)

[[shadow-baseline-2026-04-20]] で shadow 側の pair-level 内訳は判明しているが、**Live (is_shadow=0) の pair 別内訳が未取得**だった。
PAIR_DEMOTED 追加判定には Live データが必須 (lesson-reactive-changes: 1日データで反射判断禁止、複数日の Live 実測が必要)。
本ページはその Live 内訳を計測し、Gate 判定 → PAIR_DEMOTED 追加 (必要なら) までを記録する。

## Live Aggregation (All time, closed, is_shadow=0)

### ema_trend_scalp — Live

| Pair | N | W | L | BE | WR% | decided WR% | PnL (pip) | EV (pip/trade) |
|---|---|---|---|---|---|---|---|---|
| USD_JPY | 19 | 5 | 13 | 1 | 26.3 | 27.8 | −17.50 | **−0.921** |
| EUR_USD | 16 | 4 | 11 | 1 | 25.0 | 26.7 | −19.50 | **−1.219** |
| GBP_USD | 4 | 0 | 2 | 2 | 0.0 | 0.0 | −6.60 | −1.650 |
| **合計** | **39** | **9** | **26** | **4** | **23.1** | **25.7** | **−43.60** | **−1.118** |

### trend_rebound — Live

| Pair | N | W | L | BE | WR% | decided WR% | PnL (pip) | EV (pip/trade) |
|---|---|---|---|---|---|---|---|---|
| USD_JPY | 10 | 3 | 5 | 2 | 30.0 | 37.5 | −7.80 | **−0.780** |
| EUR_USD | 7 | 2 | 5 | 0 | 28.6 | 28.6 | −10.00 | −1.429 |
| GBP_USD | 1 | 0 | 1 | 0 | 0.0 | 0.0 | −7.10 | −7.100 |
| **合計** | **18** | **5** | **11** | **2** | **27.8** | **31.3** | **−24.90** | **−1.383** |

### Date distribution (combined, 57 Live trades)

```
2026-04-03:  1
2026-04-09:  7
2026-04-10:  7
2026-04-13: 21
2026-04-14: 14
2026-04-15:  6
2026-04-16:  1  ← Fidelity Cutoff day
```

Post-Fidelity Cutoff (>= 2026-04-16): **N=1 のみ** (trend_rebound × USD_JPY, BE)
→ 99% の Live トレードは Fidelity Cutoff 前。v9.2 (2026-04-17) の FORCE_DEMOTE 以降は新規 Live が蓄積されていない (想定通り、strategy-level 遮断が効いている)。

## Shadow との対照 (BT-Live divergence 推定)

Shadow baseline ([[shadow-baseline-2026-04-20]]) と Live を並べる:

### ema_trend_scalp
| Pair | Shadow N | Shadow WR | Shadow EV | Live N | Live WR | Live EV | Shadow→Live Δ |
|---|---|---|---|---|---|---|---|
| USD_JPY | 83 | 25.3 | −0.94 | 19 | 26.3 | **−0.92** | +0.02 (均質) |
| EUR_USD | 73 | 24.7 | −1.02 | 16 | 25.0 | **−1.22** | −0.20 (やや悪化) |
| GBP_USD | 36 | **8.3** | **−3.64** | 4 | 0.0 | −1.65 | +1.99 (小 N) |

**所見**: Shadow ≈ Live (USD_JPY) / Shadow ≈ Live (EUR_USD)。**構造的に負EV で規模差はあれど符号・規模が一致**。
GBP_USD は Live N=4 で統計的に判断不能だが shadow N=36 が壊滅的。

### trend_rebound
| Pair | Shadow N | Shadow WR | Shadow EV | Live N | Live WR | Live EV | Shadow→Live Δ |
|---|---|---|---|---|---|---|---|
| USD_JPY | 12 | 33.3 | **+1.43** | 10 | 30.0 | **−0.78** | **−2.21 (符号逆転)** |
| EUR_USD | 7 | 42.9 | +1.16 | 7 | 28.6 | −1.43 | **−2.59 (符号逆転)** |
| GBP_USD | 2 | 0.0 | −7.55 | 1 | 0.0 | −7.10 | — (両方 N<3) |

**所見 — 重要**: Shadow baseline で "marginal +EV" と評価した trend_rebound×USD_JPY / EUR_USD が **Live では両方とも負EV**。
Shadow (N=12/7) での +EV は **truncated sample bias** (shadow-baseline-2026-04-20 節 "既知のバイアスと制限" 項1) に起因する可能性が高い。
→ [[lesson-orb-trap-bt-divergence]] 「短期BT/shadow で WR 高く見える → Live で WR 反転」の再現パターン。

## Gate 判定 (PAIR_DEMOTED 追加候補)

Gate (全て AND):
- Live N ≥ 10
- Live EV ≤ −0.5 pip/trade
- Live WR ≤ 20% **OR** Live PnL ≤ −10 pip

| 組合せ | N | WR% | PnL | EV | N≥10 | EV≤-0.5 | WR≤20 ∨ PnL≤-10 | **PASS** |
|---|---|---|---|---|---|---|---|---|
| ema_trend_scalp × USD_JPY | 19 | 26.3 | −17.50 | −0.92 | ✅ | ✅ | ✅ (PnL) | **✅** |
| ema_trend_scalp × EUR_USD | 16 | 25.0 | −19.50 | −1.22 | ✅ | ✅ | ✅ (PnL) | **✅** |
| ema_trend_scalp × GBP_USD | 4 | 0.0 | −6.60 | −1.65 | ❌ | ✅ | ✅ | ❌ (N不足) |
| trend_rebound × USD_JPY | 10 | 30.0 | −7.80 | −0.78 | ✅ | ✅ | ❌ | ❌ |
| trend_rebound × EUR_USD | 7 | 28.6 | −10.00 | −1.43 | ❌ | ✅ | ✅ (PnL) | ❌ (N不足) |
| trend_rebound × GBP_USD | 1 | 0.0 | −7.10 | −7.10 | ❌ | ✅ | ✅ | ❌ (N不足) |

### Gate 通過組合せ

**2 combos が Gate 通過**:
1. `ema_trend_scalp × USD_JPY` — N=19 WR=26.3% EV=−0.92 PnL=−17.5
2. `ema_trend_scalp × EUR_USD` — N=16 WR=25.0% EV=−1.22 PnL=−19.5

## 実装判断 (何をするか / しないか)

### ema_trend_scalp の扱い

`ema_trend_scalp` は **v9.2 (2026-04-17) で全ペア FORCE_DEMOTED 済み** ([[sell-bias-forensics-2026-04-17]]):
- `demo_trader.py::_FORCE_DEMOTED` に登録済 (L4981)
- つまり **strategy-level で既に全ペア OANDA 遮断**されており、PAIR_DEMOTED 追加は**挙動として冗長**
- ただし `("ema_trend_scalp", "EUR_USD")` は v8.9 (FORCE_DEMOTE 前) に PAIR_DEMOTED に登録されて残留 (documentation marker)
- `("ema_trend_scalp", "USD_JPY")` は v8.9 で「SELL PB境界バグ修正済み → 再蓄積」としてコメントアウト解除された状態

**判断**: `ema_trend_scalp × USD_JPY` を PAIR_DEMOTED に documentation marker として再追加する。
理由:
1. Live N=19 EV=−0.92 PnL=−17.5 で Gate 通過 (データ根拠明確)
2. v8.9 の "再蓄積" コメントは v9.2 FORCE_DEMOTE で無効化されたのに未更新 → 履歴整合性のため記録
3. 将来 FORCE_DEMOTED 解除時にペア別負EV の履歴が残る (lesson-reactive-changes の「動機の記録」原則)

### trend_rebound の扱い

- `trend_rebound × USD_JPY` は Gate 微妙に不通過 (WR=30%, PnL=−7.8)。**PAIR_DEMOTED 追加は見送り**。
  - ただし shadow で +EV と評価されたが Live で −EV 符号逆転 → **監視優先度 High**
- `trend_rebound × EUR_USD` は Live N=7 で Gate 不通過だが**既に PAIR_DEMOTED に登録済み** (v8.9, N=6 根拠)。維持。
- `trend_rebound × GBP_USD` は Live N=1。Shadow も N=2。データ不足で判定保留。

### 付帯発見: demo_db.py ↔ demo_trader.py の SSOT drift

調査中に `demo_db.py` `SHADOW_MIGRATION` の `_force_demoted` set が `demo_trader.py::_FORCE_DEMOTED` と drift していることを発見:

```
demo_trader.py._FORCE_DEMOTED (18 strategies)
  └── ema_trend_scalp, intraday_seasonality, atr_regime_break が含まれる (v9.1, v9.2 追加)

demo_db.py._force_demoted (15 strategies, migration 用)
  └── 上記 3 戦略が欠落
```

**帰結**: v9.2 後に蓄積された ema_trend_scalp の is_shadow=0 trades (本分析対象の 39 件) が、
起動時 migration で is_shadow=1 に変換されないまま残留していた。**本分析の Live 39 件は本来 shadow 扱いであるべき**。

**修正**: `demo_db.py::_force_demoted` を `demo_trader.py::_FORCE_DEMOTED` と同期する (3 戦略追加)。
これにより次回デプロイ起動時の migration で stale Live trades が shadow 化 → Kelly pool から除外される。

### 保留した組合せと理由

| 組合せ | 保留理由 |
|---|---|
| ema_trend_scalp × GBP_USD | Live N=4 < 10 (N不足) |
| trend_rebound × USD_JPY | Gate 不通過 (WR 30%, PnL −7.8)。監視継続 |
| trend_rebound × EUR_USD | Live N=7 < 10、既 PAIR_DEMOTED |
| trend_rebound × GBP_USD | Live N=1 (N不足) |

## 実装する変更

1. **`modules/demo_trader.py::_PAIR_DEMOTED`**: `("ema_trend_scalp", "USD_JPY")` 追加 (コメントアウト解除 + 最新 Live 数値)
2. **`modules/demo_db.py::_force_demoted`** (migration set): `ema_trend_scalp`, `intraday_seasonality`, `atr_regime_break` を追加 (SSOT drift 修正)
3. **`wiki/tier-master.md` / `tier-master.json`** — 自動再生成
4. **`wiki/strategies/ema-trend-scalp.md` / `trend-rebound.md`** に判断履歴追記
5. **`wiki/changelog.md`** v9.5 エントリ

## 監視計画

- **trend_rebound × USD_JPY** (Gate 微不通過): 次の Live N≥20 到達時に再判定。現 WR 30% を維持なら +EV 復帰判定の根拠になる。Live N≤10 時点で反射的降格はしない (lesson-reactive-changes)。
- **trend_rebound 全体 edge=−0.455 問題**: FORCE_DEMOTE は pair-level breakdown が全ペアで決着しない限り保留 (現状 USD_JPY=−0.78, EUR_USD=−1.43, GBP_USD=N=1 で判定不能)。
- 次回 post-P1 shadow 蓄積と合わせて **2026-04-27** (P1 デプロイから 1週間) に再精査。

## Related

- [[shadow-baseline-2026-04-20]] — shadow 側 pair-level (対照元)
- [[lesson-reactive-changes]] — 1日データ反射禁止 (本分析は複数日 Live データに基づく)
- [[lesson-orb-trap-bt-divergence]] — shadow +EV が Live で逆転するパターン (trend_rebound で再現)
- [[sell-bias-forensics-2026-04-17]] — ema_trend_scalp v9.2 FORCE_DEMOTE の根拠
- [[pair-promoted-candidates-2026-04-20]] — 対称な PAIR_PROMOTED Gate 分析
- [[tier-master]] — 現行 Tier (本変更後に再生成)
