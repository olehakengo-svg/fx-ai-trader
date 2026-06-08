---
id: 20260608-2040-d1-tsmom-basket-pre-reg-bt
priority: P1
gate: R1
rule: R1
status: queued
created: 2026-06-08
owner: claude
---

# D1 Time-Series Momentum バスケット — pre-reg BT (risk-premia 収穫)

**Rule classification**: R1 (Slow & Strict — 新規 risk-premia 戦略の pre-reg BT)
**Purpose**: 高 TF (D1) でグロスエッジが構造的に立つ脈として、**分散通貨バスケットの time-series momentum** を新規 pre-reg する。チャートパターンの grid 総当たり (Bonferroni m=100+ で全滅する従来型) ではなく、**経済的根拠のある少数仮説 (m=4)** を事前登録して検定文化を変える。

## なぜこれか (司令塔の判断)

- 既存 "trend" 戦略は全て M15 単一ペアのチャートパターン (jpy_basket_trend ですら cross-pair data 制約で単一ペア PO を「バスケットのプロキシ」と自白)。**真の D1 分散バスケット TSMOM は未実装** = 脈の空白。
- TSMOM は documented risk-premium (下記文献)。当てに行くのではなく「過去リターンの符号を持ち越して分散で稼ぐ」ため、グロスが構造的にプラスになりやすく、D1 で friction が極小 ([[feedback_spread_basis_for_mafe]])。
- 仮説が少数・事前登録なので Bonferroni を生き残れる (従来の grid 全滅は self-inflicted な多重検定死)。

### 学術的根拠

- Moskowitz, Ooi & Pedersen (2012, JFE) — "Time Series Momentum" (12ヶ月 lookback が canonical)
- Menkhoff, Sarno, Schmeling & Schrimpf (2012, RFS) — FX momentum の40年普遍性
- Lustig, Roussanov & Verdelhan (2011, RFS) — 通貨バスケット factor

## Pre-registration (m=4、LOCK)

**Primary 仮説 (1本)**: 12ヶ月 lookback TSMOM。各ペアの過去252営業日 excess return の符号で long/short、vol-target でサイズ正規化、月次リバランス。
**Secondary (報告のみ、selection しない)**: lookback ∈ {1, 3, 6} ヶ月。これら3本は **探索的に併記するが promote 判断には使わない** ([[project_w3_3_s4_connors_raschke_queued]] の post-hoc selection 罠回避)。
- Bonferroni m=4 (lookback 4種)、α=0.05。**primary (12m) が単独で生き残るかが本丸**。

### バスケット (G10 majors、固定)

`EUR_USD, USD_JPY, GBP_USD, AUD_USD, USD_CAD, USD_CHF, NZD_USD, EUR_JPY` (8 pair 固定、後から足さない)。

### 設計詳細 (LOCK)

- Signal: `sign(close[t] / close[t-252] - 1)` per pair, D1。
- Position: vol-target。各ペア重み = (target_vol / realized_vol_60d) を equal-risk 正規化 ([[project_tp_hit_12cell_portfolio_2026_06_05]] の inv-vol equal-risk と整合)。
- Rebalance: 月次 (月初)。
- No stop / no TP — risk-premia harvest はシグナル反転で exit (持ち切り)。これが「予測しない」設計の核。

## Required scope

### Phase 0: D1 データ backfill (前提作業、blocker)

**MASSIVE キャッシュに D1 が存在しない** (現状 1m/5m/15m/1h/4h のみ、`ls data/cache/massive/` で確認済)。
- `tools/price_shock_backfill_data.py` のパターンを流用し、8 pair の D1 bars を `data/cache/massive/{PAIR}_1d.parquet` に backfill。
- MASSIVE Market Data API の daily aggregate endpoint を使う ([[feedback_bt_must_use_massive]]: Yahoo 不可)。期間: 最低 10 年 (TSMOM は long-horizon、WF に十分な fold が要る)。
- backfill 後、bar 数・欠損率・最古/最新日を report。欠損 >2% のペアは BLOCKED_DATA として明記 ([[project_w3_4_c1_london_blocked_data]])。

### Phase 1: BT

- 10年 D1 で portfolio equity curve を構築。
- 出力 8軸: Sharpe, annualized return, max DD, Calmar, t-stat (return≠0), Wilson は WR ベースなので **月次リターン勝率の Wilson_lo** も併記, PF, Kelly。
- **Walk-Forward**: 3+ folds (各 fold で in-sample パラメータ無し = TSMOM はパラメータフリーなので、fold は単に OOS 期間分割。lookback は固定 252)。各 fold の Sharpe を report。
- Bonferroni: 4 lookback の t-stat に m=4, α=0.05 適用。

### Phase 2: 判定

- `knowledge-base/wiki/decisions/d1-tsmom-basket-pre-reg-2026-06-08.md`:
  - primary (12m) が Bonferroni 後 t-stat 有意 ∧ WF 3/3 同符号 → SHADOW_CANDIDATE。
  - 失格なら NULL として明記 (思想は documented でも本データで edge 無しなら正直に棄却、[[project_w3_5_s3_pair_pool_fdr_queued]] と同様)。
- **本タスクでは Live/Shadow 投入しない**。shadow 投入は司令塔の別判断。

## Codex 注意

- BT は本番 signal 関数を `backtest_mode=True` で呼ぶ設計が原則だが、本戦略は新規。**新規戦略本体 `strategies/daytrade/tsmom_basket.py` を実装し、同じ signal ロジックを BT harness から呼ぶ** こと (BT 専用ロジックを別実装して乖離させない)。
- self-mock テストで PASS しても無意味、実 D1 parquet での E2E 必須 ([[feedback_codex_mock_test_trap]])。
- DB 書き込みがあるなら CREATE TABLE 文を本 spec に追記要求 ([[feedback_codex_schema_hallucination]])。
- 成果物 git 反映を実 verify、final.md 非信用 ([[feedback_codex_stash_leak]])。
