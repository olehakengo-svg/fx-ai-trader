# HMM Regime Filter

## Overview
- **Entry Type**: `hmm_regime_filter` (防御オーバーレイ — トレードシグナル生成なし)
- **Status**: SENTINEL (v8.5)
- **Module**: `modules/hmm_regime.py` (HMMRegime, HMMRegimeDetector)
- **Wrapper**: `strategies/daytrade/hmm_regime_filter.py` (evaluate() → None)

## v9.0 Phase 1: Auto-Fit + Data Accumulation

### 変更点
1. **Auto-Fit on Startup**: サーバー起動15秒後にバックグラウンドで全6ペアを120日1hデータでBaum-Welch学習
   - これにより `predict()` が heuristic fallback → 真のHMM forward algorithm に昇格
   - fit結果は `system_kv` に永続化（デプロイ再起動でもウォームスタート可能）
2. **Trade Record付与**: エントリー時のHMM regime/proba をトレードの `regime` JSON に記録
   - `hmm_regime`: "trending" | "ranging"
   - `hmm_proba`: {"trending": 0.xx, "ranging": 0.xx}
   - `hmm_agree`: true/false (ルールベースとの一致)
3. **Agreement永続化**: 100tick毎にDB (`system_kv`) にagreement累積データを保存
   - デプロイ再起動でもN数がリセットされない
4. **ログ改善**: fitted状態を `[HMM]` vs `[HMM-heuristic]` で区別表示

### Phase 2 分析プラン (N=500到達後)
- HMMとルールベースが不一致のトレードの勝率差を分析
- HMM=trending + Rule=RANGE → 勝率は？
- HMM=ranging + Rule=TREND → 勝率は？
- 有意差があればPhase 3 (取引判断への統合) に進む

## Academic Backing
| Paper | Finding | Confidence |
|-------|---------|-----------|
| Hamilton (1989) | Markov-switching model for financial markets | ★★★★ |
| Nystrup et al (2024, JAM) | Statistical Jump ModelがHMM超え。MaxDD大幅削減 | ★★★★ |
| Ang & Bekaert (2002) | Regime-dependent risk premia | ★★★ |

## Key Design Decisions
- **状態数 = 2固定**: 3以上はオーバーフィット (Nystrup 2024)
- **numpy only**: hmmlearn依存なし（Render deploy互換）
- **フェイルセーフ**: fit失敗時は heuristic fallback に自動退行、取引ループに影響なし

## Related
- [[index]] — Tier classification
- [[hmm-regime-overlay]] — 詳細設計
- [[roadmap-v2.1]] — Portfolio strategy
