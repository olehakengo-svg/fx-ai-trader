# OSS 転用分析: FX 自動売買ツールの横断調査 (2026-04-22)

## 目的
GitHub 上の FX/量化 OSS を英語圏・中国圏・日本圏で横断調査し、FX AI Trader への転用可能性を評価。実装は lesson-reactive-changes 遵守で **観測専用ツールの追加のみ** とし、live/BT ロジックは一切変更しない。

## 調査結果サマリー

### 圏別 TOP 候補
| 圏 | リポジトリ | Stars | FX 対応 | 転用価値 |
|---|---|---:|:---:|:---|
| 国際 | freqtrade/freqtrade | 49.1k | ✗ | Hyperopt 概念のみ (CLAUDE.md 違反で不採用) |
| 国際 | polakowo/vectorbt | 7.3k | △ | Vectorized BT (diagnostic only で限定採用候補) |
| 英語 | kieran-mackle/AutoTrader | 1.2k | ◎ | OANDA v20 endpoint 参考 (archived) |
| 英語 | edtechre/pybroker | 3.3k | - | Walk-forward 概念 → **実装済み** |
| 英語 | mhallsmoore/qsforex | 842 | ◎ | Event-driven 命名規約 |
| 中国 | microsoft/qlib | 41k | ✗ | **Alpha158 factor library → 実装済み** |
| 中国 | vnpy/vnpy | 39.7k | △ | EventEngine パターン (将来のリファクタ候補) |
| 日本 | 10mohi6/oanda-bot-python | 35 | ◎ | 参考価値薄 (停滞) |

### 最重要所見
**英語圏・中国圏・日本圏いずれにおいても、FX 特化で「勝てている」実証可能な OSS は存在しなかった**。Live verified record を公開している OSS はゼロ、検証可能な収益実績を持つのは商用 MT4/5 EA のみ。これは FX AI Trader が OSS FX bot の空白地帯にあることを示唆する。

## 採用した転用 (2 件)

### 1. Alpha Factor Zoo (qlib Alpha158 サブセット)
**Source**: microsoft/qlib `Alpha158` feature loader
**実装**: `tools/alpha_factor_zoo.py` (新規、live/BT 無影響)
**機能**:
- kbar 9 feature (KMID, KLEN, KUP, KLOW, KSFT 等)
- rolling windows [5, 10, 20, 30, 60] × [MA, STD, ROC, QTLU, QTLD, RSV] = 30 features
- 各 (pair × TF × factor × horizon) の IC = Spearman corr(factor_t, return_{t+h})
- Bootstrap 100 回で p 値、Bonferroni 補正

**初回走行結果** (USD_JPY × 15m × 90d):
- 78 cells scanned
- Bonferroni-significant (p < 1.28e-4): **5 cells**
  - KSFT2 (h=1): IC=-0.0429
  - KSFT (h=1): IC=-0.0420
  - RSV10 (h=1): IC=-0.0360
  - ROC10 (h=1): IC=-0.0339
  - QTLD5 (h=1): IC=+0.0307

KSFT (= (2·C − H − L) / O) の負 IC は短期の mean-reversion 傾向と整合 (bar 終値が H/L の中央から上にズレるほど次 bar で下げる)。

**次ステップ** (CLAUDE.md 遵守):
- 1 日スキャンで判断停止 (lesson-reactive-changes)
- Bonferroni 有意 factor は 365d walk-forward で再検証 (別セッション)
- 既存 entry_filter との合成実装は Live N≥30 まで Shadow のみ

### 2. Walk-Forward Stability Scanner (pybroker 概念)
**Source**: edtechre/pybroker `WalkforwardWindow`
**実装**: `tools/bt_walkforward.py` (新規、live/BT 無影響)
**機能**:
- 既存 `app.run_daytrade_backtest` を 1 回実行 (BT ロジック無変更)
- trade_log の entry_time を 30 日 rolling window で bin
- 戦略 × ペア別に per-window (N, WR, EV, PF) を集計
- Stability metric: CV(EV), positive_ratio, verdict (stable / borderline / unstable)

**判定基準**:
- `stable`: positive_ratio ≥ 0.67 AND CV(EV) < 1.0
- `borderline`: positive_ratio ≥ 0.5
- `unstable`: 上記どちらも未達

**目的**: 既存の「365 日 BT 一発 EV 判定」では見えない**時間窓間の分散**を可視化し、unstable 戦略の FORCE_DEMOTE 候補 flag を立てる。

**判断プロトコル**:
- 不安定判定だけでは FORCE_DEMOTE しない (観測のみ)
- 別 BT 期間 (例 730d) または Live N≥30 で再検証してから判断

## 不採用 (理由明記)

| 対象 | 理由 |
|------|------|
| **freqtrade Hyperopt** | 「カーブフィッティング禁止、パラメータ調整完了」(CLAUDE.md) と正面衝突 |
| **vectorbt replace BT** | 「BT/本番ロジック統一」原則違反 (event-driven → vectorized への置換不可) |
| **vnpy EventEngine 即導入** | live 実行パス書き換えで 365d 再 BT 必須、リスク高 |
| **modules/oanda_client.py 拡張** | 本番コード変更は別セッションで N≥30 監視後に判断 |
| **AutoTrader コード取り込み** | archived (2025-05)、API 網羅度参考のみ |

## 保留 (将来の候補)

### vnpy EventEngine を「観測 shadow」で導入
- `modules/event_bus.py` として 50 行版 EventEngine を追加
- 既存 demo_trader.py 分岐は残し、TICK/SIGNAL/ORDER/FILL event を publish のみ
- handler 側は log/KB 記録のみ
- N≥30 の並走データ取得後に既存ループ置換を検討

### vectorbt を diagnostic-only で導入
- `tools/bt_vectorbt_sweep.py` として既存 BT 確定戦略の ±10% grid sweep
- パラメータ感度分析のみ、本番 BT は別パス

### OANDA client read-only endpoint 拡張
- `list_pending_orders()`, `list_closed_trades_since(dt)`, `get_position_breakdown()` を追記
- 本番コード変更のため、別セッションで独立に実装・レビュー

## CLAUDE.md 原則との整合確認

| 原則 | 本転用での遵守状況 |
|------|:---:|
| 「365d BT or Live N≥30 を経ない実装変更は保留」 | ✅ 観測・分析ツールのみ追加 |
| 「カーブフィッティング禁止、データ蓄積フェーズ」 | ✅ パラメータ調整なし、新 α 候補の発見のみ |
| 「BT/本番ロジック統一」 | ✅ 既存 signal 関数を `backtest_mode=True` で流用 |
| 「月利 100% 目標への寄与」 | ✅ walk-forward で Kelly Half 到達前のクリーンデータ品質を数値化 |

## 関連文書
- [[lessons/lesson-reactive-changes]] — 1 日データでの実装禁止
- [[lessons/lesson-silent-except-hides-nameerror]] — silent except の罠
- [[analyses/bt-live-divergence]] — 6 つの構造的楽観バイアス
- [[roadmap-v2.1]] — ポートフォリオ戦略

## Source 一覧
- microsoft/qlib Alpha158: https://github.com/microsoft/qlib/blob/main/qlib/contrib/data/loader.py
- edtechre/pybroker: https://github.com/edtechre/pybroker
- kieran-mackle/AutoTrader: https://github.com/kieran-mackle/AutoTrader (archived 2025-05)
- polakowo/vectorbt: https://github.com/polakowo/vectorbt
- vnpy/vnpy EventEngine: https://github.com/vnpy/vnpy/blob/master/vnpy/event/engine.py
