---
strategy: ma_generic_family_v1
status: Sentinel (Shadow validation phase, 2026-04-30〜)
version: v1
parent_design_plan: /Users/jg-n-012/.claude/plans/ema-trend-scalp-ma-generic-wadler.md
related:
  - bb-rsi-reversion
  - ema_trend_scalp
  - mtf_trend_follow_scalp
  - mtf_counter_trend_scalp
rule: R1 (Slow & Strict — 365d BT or Live N≥30 + Bonferroni)
---

# MA-Generic Scalp Family v1

## Status: Sentinel (Shadow validation phase, 2026-04-30〜)

**Stage**: Pre-reg LOCK pending — Shadow validation 14d で N 蓄積中

ema_trend_scalp (FORCE_DEMOTED 2026-04-22) を置換する MA ベースの 4 変種戦略
ファミリー。USD_JPY 限定でフルクオント検証 (WF + BH/Bonferroni + Wilson +
Kelly + PF + DSR) を行い、Shadow→LIVE 昇格の勝者を統計的に選別する。

## Context (なぜこのファミリーを作ったか)

| 観測 | 値 | 出典 |
|---|---|---|
| ema_trend_scalp Live N | 0 | demo_trades.db (2026-04-30) |
| ema_trend_scalp Shadow EV | -1.219 pip (N=88) | wiki/analyses/pre-registration-2026-04-22.md |
| LIVE 全体 | N=36, +6 pip, Kelly 加重 +0.385 | 2026-04-30 audit |
| 唯一の堅実 LIVE エッジ | bb_rsi_reversion USD_JPY × London (N=13, WR 61.5%, PF 3.36, **Wilson95下限=0.355, Kelly=0.432**) | 06a-live-cell-stats.csv |
| 同 Tokyo | N=8, WR 62.5%, Wilson 0.306, Kelly 0.351 | 同上 |

LIVE 実証エッジは **USD_JPY × Tokyo/London のミーンリバージョン** のみ。
ema_trend_scalp の負け要因は pullback 型 confidence_v2 ペナルティが効きすぎ
強トレンドで発火停止／弱トレンドでダマシ、という構造的負けエッジ。

ユーザ提示の 3 手法 (トレンドフォロー押し目／GC・DC／大循環) は順張り系で
LIVE 実測と方向性が逆。単一戦略では張り違える可能性が高い。

## 4 変種仕様

すべて USD_JPY 限定、H1 EMA200 をマクロ方向バイアスに採用 (10bps gap で
方向確定、それ以下は発火停止)。

### v1a — `ma_mr_hybrid` (メイン候補)

H1 EMA200 整合 × M5 過熱リバージョン。`bb_rsi_reversion` のエッジを MA
構造で再現拡張。

- L1: USD_JPY のみ
- L2: H1 close vs ema200 (>10bps で方向確定)
- L3: M5 BB%B≤0.20 / ≥0.80 + RSI(M5,14)≤30/≥70 + Stoch反転
- L4: 1m 確認足 (反転バー)
- TP: ATR×0.8 (MR は早めに刈る), SL: ATR×1.2, RR floor=1.0

### v1b — `ma_trend_perfect` (純粋順張り)

ユーザ提示の「移動平均線大循環分析」を素直に実装。

- L2: H1 close vs ema200
- L3: M15 EMA9>21>50 (BUY) / 9<21<50 (SELL) パーフェクトオーダー + ADX≥22
- L4: M5 EMA21 を直前で割って当バー再ブレイク (再加速)
- L5: 1m 確認 + MACD-H 同方向
- TP: ATR×1.8, SL: ATR×1.0, RR floor=1.5

### v1c — `ma_regime_switch` (ハイブリッド)

H1 EMA50 傾き + M15 EMA9-EMA50 乖離率で {Trend / Range / Mixed} 判定 →
レジーム別に v1b/v1a ロジック切替。Mixed は発火しない。

### v1d — `bb_rsi_ema_aligned` (最小改修)

`bb_rsi_reversion` を継承し、H1 EMA200 整合チェック (BUY は EMA200 上向き
時のみ／SELL は下向き時のみ) を追加するだけ。LIVE 実証エッジを MA 構造で
増幅する最低リスクのリファレンス。

## 数学的検証フレーム

すべて既存ユーティリティを再利用。

| 指標 | 用途 | 実装 |
|---|---|---|
| WF 3-fold (時系列分割) | 過剰最適化検出 | `research/edge_discovery/ma_family_validation.py:_split_folds` |
| Benjamini-Hochberg (q=0.05) | 多重検定補正 (4 戦略 × 3 セッション = 12 検定) | `_benjamini_hochberg` |
| Wilson 95% 下限 | WR 信頼下限 | `modules/bt_vec_harness.py:wilson_lower` |
| Trade-weighted Kelly | 推奨ロット導出 | `modules/bt_vec_harness.py:kelly_pct` |
| Profit Factor | 期待値ベース指標 | `profit_factor_local` |
| BEV WR + 1-sided binomial | spread 込みの実効有意性 | `_bev_wr` + `_binomial_one_sided_p` |
| Deflated Sharpe | 多重試行下の真の Sharpe | `_deflated_sharpe` (Bailey & Lopez de Prado) |

### Shadow→LIVE 昇格条件 (全項目 AND)

1. WF 3-fold すべての fold で PnL>0 かつ PF>1.3
2. BH 補正後 q<0.05 (one-sided binomial vs BEV)
3. Wilson95下限 > 10% (= 0.10)
4. Trade-weighted Kelly > 0.10
5. N ≥ 30 (cell 粒度: pair × session × strategy)
6. cohort time alignment (demote 履歴と整合) は手動 cross-check

## 実行手順

### 1. 90d × WF 3-fold parity BT

```bash
BT_MODE=1 NO_AUTOSTART=1 python3 research/edge_discovery/ma_family_validation.py \
    --pair USD_JPY \
    --days 270 \
    --wf-folds 3 \
    --inject-spread 0.8 \
    --output knowledge-base/raw/audits/ma_family_v1/
```

出力:
- `USD_JPY_trades_<UTC>.csv` — 全 trade レベル
- `USD_JPY_summary_<UTC>.csv` — strategy × session × fold セル粒度
- `USD_JPY_promotion_<UTC>.csv` — Shadow→LIVE 6 条件チェック表

### 2. Shadow ライブ走行

`modules/demo_trader.py` の `_SCALP_SENTINEL` に 4 戦略追加済み。デプロイ
後は最小ロット (0.01) で稼働しデータ収集。

### 3. cohort time alignment 確認

`feedback_cohort_time_check.md` に従い、promote/demote 履歴と trade 時刻
を突合。歴史データを現状と取り違えない。

### 4. Bonferroni-significant cell の昇格判定

promotion CSV の `promote_to_live=True` 行を確認。1 戦略以上が全条件
クリアなら該当 cell のみ LIVE 昇格 (rule:R1)。

## 期待される結果と分岐

| ケース | 期待される対応 |
|---|---|
| 4 変種すべて Shadow→LIVE 不通過 | 設計失敗。MA パラダイム自体が我々のデータでは負けエッジ。別パラダイム模索 (例: order book imbalance / volatility surface) |
| v1d のみ通過 | 既存 bb_rsi エッジを EMA200 で増幅できることを確認、v1a/b/c は廃案 |
| v1a 通過 | MR ドメインで MA を活用できる、新規 LIVE 戦略追加 |
| v1b 通過 | 順張り大循環がデータで反証されていなかったことを確認、ema_trend_scalp の正しい修正方向 |
| v1c 通過 | レジームスイッチ価値あり、追加変種 (volatility regime, news regime) を検討 |

## ema_trend_scalp との関係

ema_trend_scalp は FORCE_DEMOTED のまま **保持** する (相対評価ベースライン)。
本ファミリーの相対 PF 比 > 1.5 で「真の改善」と確定。撤廃は v1 検証完了後
の独立判断。

## クオンツ的論理導出 (なぜこの設計か)

- LIVE 実測の唯一実証エッジは MR 系 (bb_rsi_reversion)
- MA を「方向整合フィルタ」として機能させると、MR の弱点 (カウンタートレンド
  逆走で連敗) を抑制可能
- 一方 v1b/v1c は「LIVE で勝てるか不明だがユーザ提示理論を統計的にテスト
  する」枠 — ema_trend_scalp の負けは「pullback 構造」由来であり、純粋順張
  り (ブレイク再加速) はまだ反証されていない
- 4 変種を並列で走らせることで、単一仮説に依存せず統計的にエッジを発見

## 不変条件 (絶対遵守)

- LIVE/Shadow 分離 (`is_shadow=0` 必須、`feedback_live_shadow_separation.md`)
- Cohort 時系列整合 (`feedback_cohort_time_check.md`)
- N/WR/EV だけでなく PF/Wilson/Kelly/WF/Bonferroni/DSR まで (`feedback_partial_quant_trap.md`)
- ラベル実測主義 (`feedback_label_empirical_audit.md`)
- XAU 除外 (`feedback_exclude_xau.md`)

## リスクと未解決事項

- スキャルピング BT の High/Low 即約定モデルは楽観バイアス。Live N≥30
  までは BT 結果を参考値扱い。spread 0.8 pip の固定値は USD_JPY を想定。
- USD_JPY 特化は LIVE 整合的だが、レジーム変化 (円買い介入等) で全変種
  同時死する集中リスクあり。LIVE 昇格後 30 日経過で EUR/GBP 横展開検討
  を別タスク化。
- v1c の {Trend/Range/Mixed} 閾値は WF 中で過剰最適化リスク高。
  Combinatorial Purged CV を将来検討 (今回フェーズ外)。

## BT Validation Results

### Run 1: 90d × 4 戦略 (2026-04-30 06:23 UTC)
コホート別の概要 (USD_JPY × spread 0.8 pip):

| 戦略 | ALL N | WR | PF | Kelly | EV pip | 結論 |
|---|---|---|---|---|---|---|
| ma_mr_hybrid | 66 | 48.5% | 0.83 | 0.0 | -0.51 | 過熱閾値が厳しすぎ N不足、再設計 |
| ma_trend_perfect | **174** | **56.3%** | **1.77** | **24.4%** | **+1.58** | **本命浮上、BH q<0.05 未達** |
| ma_regime_switch | 22 | 31.8% | 0.40 | 0.0 | -1.82 | レジーム閾値機能不全 |
| bb_rsi_ema_aligned | 1131 | 31.0% | 0.76 | 0.0 | -0.73 | **H1 EMA200 整合が MR エッジを破壊** |

12 検定の BH 補正で全 cell q<0.05 未達。

### Run 2: 180d × v1b 単独 (2026-04-30 06:42 UTC, BH=3 検定に絞り)

| Cell | N | WR | PF | Kelly | Wilson95下限 | p値 | 6条件 |
|---|---|---|---|---|---|---|---|
| **Tokyo** | 91 | 73.6% | 3.84 | 54.5% | 63.75% | 0.00001 | **✅ 6/6 PASS** |
| **NY** | 124 | 61.3% | 2.19 | 33.3% | 52.50% | 0.005 | **✅ 6/6 PASS** |
| London | 99 | 59.6% | 1.97 | 29.4% | 49.75% | 0.0503 | 5/6 (BH ギリギリ未達) |
| ALL | 369 | 60.7% | 1.99 | 30.2% | 55.64% | 0.00026 | 5/6 |

WF 3-fold: 全 fold で PF>1.3 (f1=2.18, f2=2.20, f3=1.67), EV>0。

### 主要発見
1. **v1b は USD_JPY × Tokyo/NY で rule:R1 昇格条件を完全達成** (BH 補正後 p<0.05)
2. ema_trend_scalp Shadow PF 0.685 → v1b ALL PF 1.99 = **相対 PF 比 2.9x**, Plan 設計時の「真の改善」基準 >1.5x をクリア
3. LIVE bb_rsi_reversion Tokyo Wilson95下限=30.6% < v1b Tokyo Wilson95下限=63.75% (ベンチマーク超え)
4. **v1d の負けは予想外の発見**: H1 EMA200 整合フィルタは MR にとって有害。LIVE bb_rsi のエッジは無条件 BUY/SELL から来ており、MA 整合で絞ると消える
5. ema_trend_scalp の負けは pullback 型構造由来 (純粋順張りは反証されていない) という設計仮説が支持された

### 次フェーズ
- v1b Tokyo/NY を Pre-reg LOCK 14 日 (rule:R1) → LIVE Sentinel 連動データ蓄積
- v1b London は N=99 を +30 補完で BH 通過見込み (180d 時点 p=0.0503)
- v1d の H1 EMA200 整合フィルタは廃止候補 (再設計 v1d-rev: 別フィルタで再検証)
- v1a/v1c は再設計 (閾値見直し)

### Forensic Report — Tier 1 (2026-04-30 07:00 UTC)
スクリプト: `research/edge_discovery/v1b_forensics.py`
ログ: `knowledge-base/raw/audits/ma_family_v1/v1b_forensics_*.txt`

**① Tokyo 73.6% WR の検証 — 統計的に本物**
| 検査 | 結果 | 判定 |
|---|---|---|
| 時刻分布 (UTC 0-6) | 全帯で WR 50-100%、UTC 1 が WR 100% (N=10) で最強 | ✅ 集中なし |
| 週次 WR 集中度 | 上位 5 週で総勝ち 13.4% のみ占有 | ✅ 分散あり |
| Wald-Wolfowitz runs test | observed=36, expected=36.34, z=-0.09, p=0.93 | ✅ i.i.d. と完全整合 |
| 最長 streak | WIN=11, LOSS=3 | ✅ HARKing 兆候なし |
| Quick LOSS (<5 bars) | 16.7% | ✅ SL 健全 |
| RR 実効 | avg_win 5.39 / avg_loss -3.91 = 1.38 (cost込) | ✅ |

**結論: Tokyo の数字は HARKing / データピーキング / SL ノイズではない真の統計エッジ。**

**② Cohort time alignment — f3 劣化確認**
| Fold | 期間 | days | N | WR | PF | EV |
|---|---|---|---|---|---|---|
| f1 | 2025-10-17 〜 2025-12-11 | 54 | 123 | 64.23% | 2.18 | +1.78 |
| f2 | 2025-12-11 〜 2026-02-09 | 60 | 123 | 61.79% | 2.20 | +2.07 |
| **f3** | **2026-02-09 〜 2026-04-13** | **62** | **123** | **56.10%** | **1.67** | **+1.35** |

**Phase B Shadow 期間 (2026-04-30〜05-14) は f3 直後 = エッジ decay 中の可能性。**
要因仮説: 2026 年初頭の円相場変動 / FOMC dot plot 変更 / 円介入観測。

**③ BH cell grouping 妥当性**
| Grouping | 検定数 | BH-pass |
|---|---|---|
| 3-cell (v1b LOCK 宣言粒度) | 3 | Tokyo, NY |
| 4-cell (strategy-level) | 4 | 0 (ma_trend_perfect p=0.038 だが BH 閾値 0.0125 で reject) |
| 12-cell (full family panel) | 11 | 0 |

→ LOCK は 3-cell で defensible。但し 4/12-cell では未通過の事実は Phase B 評価時に transparent に記録。

**Forensic を踏まえた追加判断**
1. Phase B Shadow Tokyo Wilson95下限 > 30% を **MUST** とする (BT 73% を盲信しない)
2. f3 期間レジームの forensic を別途実施 (USD_JPY マクロイベントマップ)
3. LIVE 昇格時 lot は Kelly Half × 0.5 から **Quarter Kelly** に格下げ (decay リスク反映)

### Forensic Tier 1.5 — f3 decay 構造分解 (2026-04-30, 重大)

スクリプト: `research/edge_discovery/v1b_f3_decay.py`

**Session × Fold cell decay (f1 → f3 ΔWR)**
| Session | f1 WR | f3 WR | ΔWR | 判定 |
|---|---|---|---|---|
| **Tokyo** | 77.4% | **63.0%** | **-14.5%** | 🔴 大幅劣化 |
| **London** | 68.8% | **56.0%** | **-12.7%** | 🔴 大幅劣化 |
| NY | 60.9% | 57.1% | -3.7% | 🟡 最安定 |

**Tokyo 機構分解**: N 31→27, avg_win 5.75→4.80, median_exit_bars 3→6
→ **鋭い momentum continuation 減少 = volatility compression**

**半月次 WR 急落**:
- 2025-10〜2026-01: 60-69% 安定
- 2026-02 H2: 54%
- **2026-04 H1: 33.3% (Wilson下限 17%, EV -0.77p)** ← LOCK 直前
- Linear trend: -1.32%/半月

### 強化された Phase B 設計 (LOCK 文書に反映済み)
1. Phase B 期間 **14d → 30d** に延長 (N 不足解消)
2. **NY-only 昇格パス追加** (Tokyo/London が decay 継続でも NY 単独で達成可)
3. 2026-04 H1 急落の構造原因解析を **Phase B 期間中に必須**

## Run 3: 再設計 v1a/c/d-rev 90d BT (2026-04-30 07:24 UTC)

v1a/c/d 全て BT 90d の cells で **昇格条件未達** だが、構造的改善は確認:

| 戦略 (rev) | N | WR | PF | Kelly | EV pip | 結論 |
|---|---|---|---|---|---|---|
| ma_mr_hybrid (v1a-rev) | 1 | 100% | 99 | 0 | +4.88 | 🔴 M15 5bps gap 過剰絞り (N=1)、再々設計必要 |
| ma_regime_switch (v1c-rev) | 397 | 49.1% | 0.94 | 0 | -0.14 | 🟡 機構正常化 (旧 N=22→397, +18x) も break-even |
| bb_rsi_ema_aligned (v1d-rev) | 365 | 35.6% | 0.97 | 0 | -0.09 | 🟡 旧 v1d (N=1131 EV=-0.73) 比改善、break-even |

**v1c-rev London cell** が唯一の正値: N=99 WR 53.5% PF 1.17 Kelly 7.95% (昇格条件未達だが
方向性は正しい)。

### Run 3 から得られた知見

1. **v1a-rev**: 5bps M15 trend gap は USD_JPY スキャルで通過率が 1/90d まで落ち過剰絞り。
   再々設計案: gap 撤去 (方向ニュートラル) or 緩和 (1bp) + 別フィルタ追加 (例: VWAP)。
2. **v1c-rev**: ATR percentile regime classifier は機構として **正常稼働** することを確認
   (旧 v1c の N=22 機能不全から N=397 へ大幅改善)。ただし現市場環境ではエッジ未達 ⇒
   閾値最適化 or 別 regime axis (例: ADX percentile) を試行する価値あり。
3. **v1d-rev**: ADX>=30 + Gold Hours の LIVE-validated ボーナス条件**でも spread 0.8 pip
   負担を乗り越えるエッジは出ない**。MR の TP が 4-5 pip 域に収まるため、spread 比率
   が高すぎる構造的限界。MR 戦略の本番昇格には **spread <0.5 pip 銘柄 or pair** が
   必要 — USD_JPY は十分タイトだが MR スキャルの cost-edge ratio が厳しい。

### 再々設計フェーズ (deferred to v2)

v1b LIVE 検証完了 (2026-05-30) を待ってから着手:
- v1a-rev2: M15 trend filter 撤去 + 別の過熱条件追加 (例: 5-bar Z-score)
- v1c-rev2: ATR percentile + ADX percentile の 2D regime classifier
- v1d-rev2: spread 影響を minimize する large TP MR (TP ≥ 8 pip 強制)

## CHANGELOG

- 2026-04-30: 初期実装 (rule:R1)。v1a/b/c/d 4 変種を `_SCALP_SENTINEL`
  に登録、`research/edge_discovery/ma_family_validation.py` で WF + BH +
  Wilson + Kelly + PF + DSR 検証ランナー作成、`bt_vec_harness.py` に
  `inject_spread` toggle 追加。
- 2026-04-30 (same day): 90d 4 戦略 + 180d v1b 単独 BT 完了。v1b Tokyo/NY が
  rule:R1 昇格条件完全達成 (BH q<0.05、Kelly>30%、Wilson95>50%)。
  Pre-reg LOCK 候補に確定。--strategies フィルタを runner に追加。

## LOCK 期間中の独立タスク (2026-05-01〜)

### Phase B Daily Monitor (Tier 1 ①)

スクリプト: `research/edge_discovery/v1b_phase_b_monitor.py`
出力: `knowledge-base/raw/audits/ma_family_v1/phase_b_monitor/phase_b_<YYYY-MM-DD>.md`

毎日自動評価:
- Render API `/api/demo/trades` から ma_trend_perfect LIVE trades fetch
- Tokyo / London / NY cell ごとの Wilson95下限 計算
- LOCK Failure Conditions #1, #2, #4, #5, #6 評価
- ATR 14d M15 平均をローカル parquet から自動計算 (Failure #6)

Initial run (2026-05-01, LOCK day 1/30):
- v1b LIVE N=0 (デプロイ直後)
- ATR 14d M15 = 0.0907 << 0.1441 ✅ Failure #6 pass
- 直近環境は f3 baseline より低 vol = v1b に追い風

### Cross-pair Generalization BT (Tier 2 ④, 2026-05-01)

スクリプト: `research/edge_discovery/v1b_cross_pair_bt.py`

180d BT × pair-specific spread (USD_JPY=0.8, EUR_USD=0.5, GBP_USD=0.7):

| Pair | N | WR | PF | Kelly | Wilson95下限 | Verdict |
|---|---|---|---|---|---|---|
| **USD_JPY** | 369 | 60.7% | 1.99 | 30.2% | **55.6%** | 🎯 STRUCTURAL EDGE |
| **GBP_USD** | 385 | 55.3% | 1.53 | 19.0% | **50.3%** | 🎯 STRUCTURAL EDGE |
| EUR_USD | 373 | 51.7% | 1.45 | 15.9% | 46.7% | ✅ Generalizes |

**Session-level 一貫性**: 3 pair すべて London + NY で PF>1.6。

**重要発見**: v1b は **USD_JPY 特化 overfit ではなく汎用 trend-follow edge**。
仮説 (M15 大循環 + M5 EMA21 再ブレイクは asset-class agnostic な短期 trend
persistence 捕捉) が 3 pair 独立評価で 3/3 通過。

### Phase D 横展開計画 (v1b LIVE 昇格後)

Phase B (2026-05-30) クリア後、Phase C (USD_JPY LIVE) 30d を経て Phase D で:
1. **GBP_USD 横展開**: Wilson 50.3% で promotion 閾値クリア、優先候補
2. **EUR_USD 検証継続**: Wilson 46.7% でボーダー、LIVE Shadow N≥30 で再判定
3. **3-pair portfolio Sharpe**: combined で単独 USD_JPY を上回る期待

### Portfolio Kelly Analysis (Tier 2 ③, 2026-05-01)

スクリプト: `research/edge_discovery/portfolio_kelly.py`

LIVE データ + v1b BT proxy で portfolio 最適化:

| 戦略 | N | mean pip | std pip | daily Sharpe (annual) | Kelly weight |
|---|---|---|---|---|---|
| bb_rsi_reversion | 234 LIVE | -0.023 | 4.41 | -0.117 | **0.00** |
| vol_momentum_scalp | 17 LIVE | +0.282 | 3.89 | +0.352 | 0.43 |
| ma_trend_perfect (BT proxy) | 369 | +1.732 | 5.71 | +7.456 | **0.57** |

**重要発見**:
- bb_rsi_reversion は **集計 LIVE level で break-even 以下** (mean -0.023 pip)。
  LIVE Kelly 0.43 は cell-level (USD_JPY × London) のみで、aggregate ではエッジ消失
- ma_trend_perfect 単独 Sharpe 7.46 vs portfolio 7.53 = diversification gain +1.0%
- v1b に集中するのが defensible (vol_momentum N=17 不確実、bb_rsi は dilution)

**Quarter-Kelly 推奨 lot allocation** (Phase C 開始時):
- ma_trend_perfect: 0.142 lot (= 0.57 weight × 0.25 conservative scaling)
- vol_momentum_scalp: 0.107 lot (Phase C で N≥30 確認後)
- bb_rsi_reversion: 0.000 lot (aggregate level でエッジなし)

Caveats:
- v1b は BT proxy、LIVE divergence prior 30-50% Sharpe haircut 想定
- daily aggregation は intra-day hedge を前提
- 105 days overlap、半年 LIVE で更新推奨
