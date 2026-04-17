# 本番データ取得・分析運用計画 (2026-04-17)

**作成日**: 2026-04-17
**目的**: エッジ検証を**観測データで**継続するための系統的取得・分析スケジュール
**背景**:
- 現 9日データ (N=1054) では STRONG edge = 0, regime = 1種類のみ
- CLAUDE.md ルール: 「分析は本番 (Render) データ使用」「365-day BT OR Live N≥30」
- 先行 learning: entry_price で regime を推定するのは selection bias (`sell-bias-root-cause-2026-04-17.md` 参照)

---

## 1. 取得対象

### 1.1 Primary: Render production API

| エンドポイント | 内容 | 用途 |
|---|---|---|
| `/api/demo/trades?state=closed&limit=1000` | 確定トレード (is_shadow, direction, pnl_pips, sl/tp, session, 等) | 全鍵分析 |
| `/api/demo/factors?factor=<name>&...` | 時系列ファクター値 | IC 計算, regime conditioning |
| `/api/demo/stats` | 集計統計 | sanity check |

### 1.2 Secondary: OANDA candles (独立 regime 検証用)

| 取得項目 | granularity | 用途 |
|---|---|---|
| H1 OHLC 主要3ペア (USD_JPY, EUR_USD, GBP_USD) | H1 | regime slope 検定 |
| 同上 | D | 長期 regime (週次レポート用) |

**注**: Render API で取得する entry_price は signal selection bias を含むため regime 判定には使えない。**必ず OANDA 独立データで regime を測る**こと。

---

## 2. 取得頻度とマイルストーン

### 2.1 日次 (Daily)

| 項目 | タイミング | 実装 |
|---|---|---|
| closed_trades の差分取得 | JST 07:00 (NY close 後) | `production_fetcher.py` を cron |
| OANDA H1 candles (直近24h) | 同上 | `oanda_client.get_candles` |
| 累計 N と Bonf 検出可能 WR-delta の更新 | 同上 | ダッシュボード or markdown |

**目的**: N 増加をモニター。次の分析閾値到達 (下記) を検知。

### 2.2 週次 (Weekly) — 毎週日曜日

| 分析 | 閾値 | 出力先 |
|---|---|---|
| `rigorous_analyzer.py` re-run | N >= 前回+100 | `analyses/rigorous-edge-analysis-YYYY-MM-DD.md` |
| SELL-BUY regime counterfactual 更新 | OANDA trend が反転 | `analyses/sell-bias-*.md` に追記 |
| 構造的敗者 (Bonf-sig negative) のリスト更新 | — | `decisions/force-demote-candidates.md` |

### 2.3 マイルストーン駆動

| マイルストーン | トリガー | 実施内容 |
|---|---|---|
| **M30** | Live N >= 30 per 戦略 (CLAUDE.md GO判定閾値) | 戦略単位の promote/demote 判定会議 |
| **M1K-live** | Live cumulative N >= 1000 | Cross-analysis (strategy × session × inst) が統計的に意味を持つ |
| **Regime 反転** | OANDA D slope の符号反転を 3日連続 | Counterfactual test: SELL bias が対称的に消える/増えるか確認 |
| **M30d** | データ期間 30日到達 | Regime conditioning 分析、時間帯別コストモデル精緻化 |
| **M90d** | データ期間 90日到達 | Walk-forward 3-fold 実効 (fold=30d), VIX/DXY regime 分類追加 |

---

## 3. 分析フレームワーク適用ルール

### 3.1 統計的テスト選択

| 判定したいこと | 適正テスト | 不適切テスト |
|---|---|---|
| WR が BE-WR と有意に違うか | binomial two-sided (BE-WR を p0 に) | t-test |
| BUY vs SELL の PnL 差 | Welch t-test + bootstrap CI | binomial (WR差) だけで判断 |
| 多次元 pocket 探索 | Bonferroni (gate) + BH-FDR (list) | 単純な p<0.05 |
| Regime 方向判定 | OANDA 独立 OHLC で OLS slope + drift/σ | entry_price の期初/期末 (NG) |

### 3.2 多重検定補正

- **Bonferroni**: STRONG pocket 候補の gate (α=0.05/n_tests)
- **BH-FDR** (q=0.10): MODERATE pocket 候補のリスト化
- **Two-sided binomial**: WR が BE-WR の**両側**から外れているか (structural loser 検出のため)

### 3.3 Walk-forward 制約

- fold 幅 >= 期待 regime cycle の 1/3 以上
- 9日データでは fold=3日 → regime 変動を捉えられず実質無意味
- **M30d 以降** で初めて fold=10日が意味を持つ

---

## 4. 判断プロトコル

### 4.1 各レベルで許される結論

| データ量 | 許される結論 | 許されない結論 |
|---|---|---|
| N < 30 / 戦略 | "判断保留" のみ | promote / demote |
| N >= 30 かつ Bonf-sig positive かつ WF-stable | MODERATE → promote 検討 | STRONG 断定 |
| N >= 100 かつ Bonf-sig negative かつ WF-stable | demote 候補 | 即日停止 |
| Multi-regime (>=2 regime) で一貫 | STRONG → promote | — |

### 4.2 regime counterfactual test (最重要)

次の downtrend 観測時に:
- SELL bias が消失または反転 → regime drag 仮説確定
- SELL bias が残存 → signal-side 再調査

---

## 5. 実装タスク (pending)

- [ ] `scripts/daily_production_fetch.sh` — cron で回す fetch スクリプト
- [ ] `scripts/weekly_rigorous_scan.sh` — 日曜朝に rigorous_analyzer 自動実行
- [ ] `research/edge_discovery/regime_verifier.py` — OANDA H1 trend 検定の再利用可能モジュール (`/tmp/regime_check.py` をリファクタ)
- [ ] `tools/data_freshness_check.py` — Live vs BT の FIDELITY_CUTOFF 以降比率を監視

---

## 6. KPI (四半期レビュー時に確認)

| KPI | 目標 |
|---|---|
| 累計 Live N | 月次 +500 以上 |
| Bonf-sig positive pocket 数 | ゼロからの脱却 (M90 までに 1 以上) |
| BT-Live PnL 乖離 | <= 15pp (既存 lesson に準拠) |
| Regime 分類の識別度 | 2 以上の regime を定量判別可能 |

---

## 7. リスクと緩和策

| リスク | 影響 | 緩和 |
|---|---|---|
| Render API レート制限 | データ欠損 | 日次全取得 → 差分取得へ移行 |
| Selection bias (signal が regime を歪める) | 結論誤り | OANDA 独立データで必ず cross-check |
| 過剰分析による multiple testing inflation | 偽陽性 | Bonf/FDR 適用、結論は "MODERATE 以上" のみ採用 |
| 待機期間中のコスト悪化 | 累計 PnL 悪化 | Bonf-sig negative 戦略は FORCE_DEMOTE 候補入り (demote は別プロトコル) |

---

## 関連文書

- `analyses/rigorous-edge-analysis-2026-04-17.md` — 基礎分析
- `analyses/sell-bias-root-cause-2026-04-17.md` — regime 検証の実例
- `research/edge_discovery/` — フレームワーク実装
- `CLAUDE.md` — 判定プロトコル原本
