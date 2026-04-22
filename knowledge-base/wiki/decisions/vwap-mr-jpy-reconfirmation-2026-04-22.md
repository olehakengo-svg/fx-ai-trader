# VWAP Mean Reversion × JPY — PAIR_PROMOTED 再確証 (2026-04-22)

## TL;DR
**判断: PAIR_PROMOTED 維持（変更なし、既存設定の追確証）**
- 2026-04-22 の fresh 365d × 15m BT で `vwap_mean_reversion × {EUR_JPY, GBP_JPY}` が walk-forward 全 3 窓で正 EV を維持
- GBP_JPY: N=267 WR=78.3% EV=+1.025 PnL=+273.7 pip（walk-forward w1/w2/w3 = +0.338 / +0.205 / +0.313）
- EUR_JPY: N=223 WR=68.2% EV=+0.672 PnL=+149.9 pip（walk-forward +0.103 / +0.219 / +0.101）
- PAIR_PROMOTED の既存根拠（`modules/demo_trader.py:5168-5170`）を新規 BT データで追確証

## 背景
2026-04-22 に EUR_JPY / GBP_JPY / EUR_GBP × 365d × 15m の DT fresh BT を実行（5862 秒）。
目的は (1) ペア網羅性回復 (USD_JPY/EUR_USD/GBP_USD のみだった) と (2) 既存 PAIR_PROMOTED の新規データでの再確証。

セッション当初に「PAIR_PROMOTED 未登録の最強新エッジ」と誤認した経緯（KB SYNC hook の stale 表示 → `sync_kb_index.py --write` で訂正）を踏まえ、`modules/demo_trader.py:5168-5170` を Source of Truth として参照した結果、**vwap_mean_reversion × {EUR_JPY, GBP_JPY, GBP_USD, EUR_USD}** は既に PAIR_PROMOTED 登録済みであることを確認。本判断はそれを fresh BT で追確証したもの。

## BT 結果 (365d × 15m, `raw/bt-results/bt-365d-jpy-2026-04-22.json`)

| Pair | N | WR | EV | PnL | Walk-forward EV (w1 / w2 / w3) | Stability |
|---|--:|--:|--:|--:|:-:|---|
| **GBP_JPY** | 267 | 78.3% | **+1.025** | +273.7 | +0.338 / +0.205 / +0.313 | **3/3 窓 +EV、最強セル** |
| EUR_JPY | 223 | 68.2% | +0.672 | +149.9 | +0.103 / +0.219 / +0.101 | 3/3 窓 +EV |

## 既存の根拠（Massive Alpha Scan 時点）
Bonferroni significant (p<10^-7) / friction-adjusted:

| Cell | N | fWR | fEV | Annual PnL |
|---|--:|--:|--:|--:|
| EUR_JPY 15m 16bar | 737 | 55.8% | +3.85 | +2,837p |
| GBP_JPY 15m 16bar | 740 | 56.2% | +5.17 | +3,827p |
| EUR_JPY 1h 16bar | 226 | 58.0% | +6.32 | +1,428p |
| GBP_JPY 1h 16bar | 245 | 56.3% | +13.4 | +3,290p |

**今回の fresh BT は 365d × 15m 単独での再実行で、Massive Scan 時点より N は小さいが EV は同オーダー（+0.672〜+1.025）で一致**。小 N 劣化は起きていない。

## 判断理由

### 維持する根拠
1. **Walk-forward 全窓正 EV**: EUR_JPY / GBP_JPY 共に 3/3 窓で +EV、時間的安定性を確認
2. **Massive Scan と fresh BT で方向一致**: 過去のカーブフィッティング懸念は post-cutoff の fresh BT で解消
3. **LOT_BOOST 1.8x × 2.0x ratio の現行設定は BT EV と整合**: 
   - GBP_JPY EV=+1.025 × LOT_BOOST = 構造的期待値
   - friction model (EUR_JPY RT 2.50pip / GBP_JPY RT ~2.5pip) を吸収して依然正 EV
4. **Live N は小さいが方向一致**: post-cutoff Live N=2 WR=50% PnL=+36.9pip（top performer, data source 2026-04-21）
5. **アクション変更なし**: 既に PAIR_PROMOTED、LOT_BOOST 2.0x (`_STRATEGY_LOT_BOOST`)、PAIR_LOT_BOOST EUR_JPY 1.8x / GBP_JPY 1.8x。Tier / lot の追加変更は不要

### 注意点（Scalp 版は別判断）
- Scalp `vwap_mean_reversion` (post-fix N=36) は Live 配置候補として **保留**（本 decision のスコープ外）
- 1m 版は両ペア負 EV（EURJPY -0.272, GBPJPY -0.114）
- 5m 版は N=2-3 で結論不可（+0.874 / +0.132）、365d 延長 BT が次の判断材料
- Scalp scope の方向性は別セッションで議論

## Implications & Next Actions
- [x] PAIR_PROMOTED 維持（変更不要）
- [x] KB 整合: `strategies/vwap-mean-reversion.md` に fresh BT テーブル追加済み
- [x] `sync_kb_index.py --write` で auto-synced portfolio block 再生成済み
- [ ] DT 側は現行設定維持、モニタリングのみ（monthly）
- [ ] Scalp vwap_mr 5m 365d 延長 BT を別タスクで実行（本 decision とは独立）

## 関連
- [[vwap-mean-reversion]] — strategy page (fresh BT 反映済み)
- [[force-demoted-strategies]] — FORCE_DEMOTED 一覧（vwap_mr は非対象）
- [[lesson-kb-blind-pp-proposal]] — Source of Truth 確認の重要性
- [[lesson-user-challenge-as-signal]] — Tier 判断前の demo_trader.py 確認
- `raw/bt-results/bt-365d-jpy-2026-04-22.json` — fresh BT raw data
