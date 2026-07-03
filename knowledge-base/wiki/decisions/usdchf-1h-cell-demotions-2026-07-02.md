# daytrade_1h_usdchf モード監査 — 残存4セル Shadow demotion (2026-07-02, rule:R2)

**Rule**: R2（損失停止/demotion — 数トレード〜N=10で即断可）
**根拠データ**: 本番 Render API `/api/demo/trades?mode=daytrade_1h_usdchf` 実測 2026-07-02 14:35 UTC（count=444、clean=dedup_violation除外）
**トリガー**: 凍結スナップショット再集計 (clean W/L N=169, WR=16.6%, -416.3p) + R2 alert 2026-07-02T13:55Z の london_breakout×USD_CHF WARN (EV=-1.485, PF=0.30)

## モード全体像（2026-05-18 開始〜2026-07-02、clean W/L）

**N=169, WR=16.6%, sum=-416.3p** — 8 entry_type 全てが負。内訳は2群に分かれる:

### 群1: 2026-06-12 恒久退役済み（対処不要 — 経路閉鎖確認のみ）

| entry_type | N | WR | PnL | 最終トレード | 状態 |
|---|---|---|---|---|---|
| ema_trend_scalp | 37 | 5% | -133.3p | 06-11 | SHADOW_RETIRED で停止確認 ✅ |
| sr_channel_reversal | 37 | 22% | -41.7p | 06-16 | 同上（deploy ラグで06-16まで漏れ）✅ |
| bb_rsi_reversion | 21 | 10% | -57.5p | 06-04 | 同上 ✅ |
| fib_reversal | 15 | 13% | -30.6p | 06-09 | 同上 ✅ |

小計 N=110, -263.1p。**06-12 退役後の新規 emit なし = 退役機構は機能している。**

### 群2: 残存 bleeder（本決定で per-cell demote）

| entry_type × USD_CHF | N | W | WR | Wilson_lo | PnL | mean | 最終トレード |
|---|---|---|---|---|---|---|---|
| london_breakout | 37 | 11 | 29.7% | 17.5% | -88.6p | -2.39p | **07-02（当日も emit 中）** |
| vol_surge_detector | 12 | 3 | 25.0% | 8.9% | -36.0p | -3.00p | **07-02（当日も emit 中）** |
| three_bar_reversal | 4 | 0 | 0.0% | 0.0% | -16.6p | -4.15p | 06-30 |
| engulfing_bb | 6 | 0 | 0.0% | 0.0% | -12.0p | -2.00p | 06-15（休眠中だが emit 可能） |

小計 **N=59, WR=23.7%, Wilson_lo=14.7%, -153.2p**。friction テーブルのどの BEV_WR (33.7〜57.1%) をも下回り、**4セル全て BUY/SELL 両方向で負**（london: BUY -49.1p / SELL -39.5p、vol_surge: BUY -17.8p / SELL -18.2p）。方向反転仮説も不成立。

**vol_surge の注意点**: R2 alert の直近 window は n=4 3W1L +0.9p (PF 2.44) だが、N=4 は Wilson noise（前例: sr_channel USD_CHF BUY +0.35 N=12 → noise 判定）。all-time clean N=12 WR 25% -36.0p を採用。教訓「促進判定も逆校正判定も同じ統計厳格さで」。

## LIVE OANDA 転送 8件の経路特定（live-bleeder-demotions 未解決項目の解消）

[[live-bleeder-demotions-2026-07-02]] で「bb_rsi_reversion 30d n=10 -9.8p — live経路未特定・保留」とされた項目の**答えがこのモード**:

- LIVE 8件は全て **bb_rsi_reversion × USD_CHF、2026-06-02 17:02〜19:37 UTC**（oanda_trade_id 496674〜496722）、net **-11.0p**
- 全モード横断では bb_rsi live 16件 (06-01以降: daytrade_1h_usdchf 8 / scalp系 8、計 -6.1p)
- **全経路とも 2026-06-12 の bb_rsi 戦略退役で構造閉鎖済み**（bb_rsi は ELITE/PAIR_PROMOTED 非所属のため live-tier exempt なし、`is_shadow_demoted` が emit 前にブロック）。06-02 の転送は退役前のイベント
- → 追加の live 停止アクションは不要。live-bleeder doc の残タスクを解消

## 判定: モード停止ではなく per-cell demote

**モード自体（Phase B-1 price_shock_reversion surface slot）は維持**:
- 原則3: Shadow データ蓄積は削らない。モード停止は price_shock_reversion × USD_CHF（tier-master #159: Tier 3 WATCH, Phase B Wave 1 candidate）のセンサーを殺す
- 教訓「無条件 emit 設計は EV<0 で自動的にデータ汚染源化する。SHADOW_ALWAYS には R2 demotion gate を併設」→ per-cell demote が既設の正規機構（SHADOW_DEMOTED_CELLS、block_reason=`r2_shadow_demoted_cell`）
- demote 後のモード残存 emit 源: price_shock_reversion（シグナル未発火、shock イベント待ち）+ 未発火の hourly 戦略。日次 R2 alert loop が新規セルを監視継続

## 実装（同一コミット）

- `modules/shadow_demote_registry.py`: `SHADOW_DEMOTED_CELLS` に4セル追加（london_breakout / vol_surge_detector / three_bar_reversal / engulfing_bb × USD_CHF）
- `tests/test_shadow_demote_registry.py`: expected set 更新 + `test_usdchf_hourly_bleeder_cells_demoted` 追加（他ペア非影響も pin: vol_surge×USD_JPY SCALP_SENTINEL は現役維持）
- KB: 本 doc + [[live-bleeder-demotions-2026-07-02]] 未処理項目更新 + strategy cards 4枚 + CHANGELOG.md

## 再昇格条件

**R1 のみ**（365日BT or Live N≥30 + Bonferroni + Pre-reg LOCK）。本決定は main デプロイで有効化。

## Related

- [[live-bleeder-demotions-2026-07-02]] — 同日の LIVE 側 R2 demotions（本 doc は Shadow 側の補完）
- [[hourly-engine-shadow-ramp-2026-05-18]] — このモードの起動経緯
- [[edge-factor-audit-2026-06-12-ema-trend-scalp]] 他 — 群1の退役根拠
