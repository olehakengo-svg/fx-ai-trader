# Decisions Index — 重要判断の記録

## 目的
トレーディングシステムに影響を与える重要判断を構造化して記録する。
「なぜその判断をしたか」を振り返り可能にし、同じ議論の繰り返しを防ぐ。

## 記録基準（いつ decision を作るか）
1. **戦略のTier変更**: PROMOTED, DEMOTED, FORCE_DEMOTED, 停止/復活
2. **パラメータ変更**: SL/TP/スコア閾値の変更（カーブフィッティング禁止ルール関連）
3. **アーキテクチャ変更**: 新モジュール追加、モード追加/削除
4. **監査・レビュー結果**: 外部/独立監査の勧告とその受諾/却下
5. **リスクポリシー変更**: DD防御、ロットサイズ、Kelly導入

## セッションログでの Decision タグ
セッション中の重要判断を `[DECISION: ...]` タグで記録する:
```
[DECISION: bb_rsi×EUR_JPYをDEMOTE — N=15でWR=26.7%, BEV未達]
[DECISION: v8.9 Equity Reset実施 — XAU損失+pre-cutoffデータがDD計算を汚染]
```
PreCompact hookがこのタグを検出し、decision ページ作成を提案する。

## Decision Pages — Categorized (84 docs as of 2026-05-26)

### 🔍 Independent / External Audits (10)
- [[independent-audit-2026-04-10]] — 独立監査（macdh吸収REJECT, bb_rsi保護最優先）
- [[academic-audit-2026-04-12]] — 学術研究サーベイ結果（25論文→6新エッジ）
- [[external-audit-2026-04-24]]
- [[shadow-audit-2026-04-30]]
- [[contamination-event-2026-04-30]]
- [[gate-progression-audit-2026-05-03]]
- [[tier1-live-edge-audit-2026-05-03]]
- [[tier1-routing-rca-2026-05-04]]
- [[fx-nexus-step1-audit-2026-05-04]]
- [[r2-postmerge-audit-prereg-2026-05-11]]
- [[prime-v2-n30d-reaudit-schedule]]

### 🔒 Pre-Registration LOCK (16)
- [[pre-reg-asia-range-fade-v1-2026-04-26]]
- [[pre-reg-bb-rsi-revival-2026-04-27]]
- [[pre-reg-bbrsi-eurusd-2026-04-27]]
- [[pre-reg-cell-promotion-2026-04-27]]
- [[pre-reg-overlap-cells-2026-04-28]]
- [[pre-reg-pattern-discovery-2026-04-28]]
- [[pre-reg-phase8-track-a-2026-04-28]]
- [[pre-reg-phase8-track-b-2026-04-28]]
- [[pre-reg-phase8-track-c-2026-04-28]]
- [[pre-reg-phase8-track-d-2026-04-28]]
- [[pre-reg-phase8-track-e-2026-04-28]]
- [[wave-2-prereg-bypass-2026-04-27]]
- [[streak-reversal-htf-soft-penalty-pre-reg]]
- [[vix-overlap-pilot-prereg-2026-05-13]]
- [[pre-reg-promotion-rewire-2026-04-28]]
- [[pre-reg-ma-trend-perfect-2026-04-30]]
- [[fx-nexus-step1-prereg-2026-05-04]]
- [[ema10-8pattern-pullback-pre-reg-2026-05-05]]
- [[cell-promotion-prereg-2026-05-13]]
- [[pre-reg-ob-retest-h1-2026-05-18]]
- [[pre-reg-ob-retest-h1-1095d-2026-05-18]]
- [[pre-reg-kalman-d7-shadow-fire-recovery-2026-05-28]] — silent-block fix (29ec95cb) が Kalman D7 に効くかの 24h post-deploy 判定

### 🔄 W4 EDA Shadow Redesign (9, all 2026-05-05)
Background: [[lessons]] 配下の W4-EDA 監査由来。MEMORY `project_w4_eda_complete_2026_05_05`, `project_w4_shadow_redesign_v2_1_paradigm_fix` 参照。
- [[w4-redesign-lock-criteria-v2-2026-05-05]] — v2.1 paradigm fix LOCK
- [[alpha_intraday_seasonality-shadow-redesign-2026-05-05]]
- [[asia_range_fade_v1-shadow-redesign-2026-05-05]]
- [[confluence_scalp-shadow-redesign-2026-05-05]]
- [[doji_breakout-redesign-2026-05-05]]
- [[squeeze_release_momentum-shadow-redesign-2026-05-05]]
- [[vol_momentum_scalp-shadow-redesign-2026-05-05]]
- [[xs_momentum-shadow-redesign-2026-05-05]]
- [[regime-cascade-empirical-redesign-2026-04-30]]

### 🚀 Promote / Demote / Live Activation / Exception (13)
- [[r2-cell-demotion-lock-2026-05-03]]
- [[t3-tokyo-range-breakout-shadow-proposal-2026-04-23]]
- [[ema-trend-scalp-retire-recommendation-2026-04-30]]
- [[hourly-engine-shadow-ramp-2026-05-18]]
- [[price-shock-rev-promote-criteria-2026-05-18]]
- [[price-shock-rev-live-activation-2026-05-18]]
- [[live-promote-losers-side-channel-2026-05-19]]
- [[xs-momentum-rsi-live-promote-override-2026-05-13]]
- [[prime-gate-promotion-path-bug-2026-05-18]]
- [[edge-cells-stage3-live-promote-2026-05-26]]
- [[vix-1x-intentional-exception-2026-05-21]] — MEMORY: `project_vix_carry_1x_intentional_exception_2026_05_21`
- [[pivot_detector_v2_5_live_exception_2026_05_26]]
- [[live-thaw-gate-2026-04-27]]

### 📊 Strategy-Specific Verdicts (8)
- [[mtf-alignment-gate-2026-04-21]] — 保留判断（BT/Shadow効果も ACTIVE戦略 Live N 不足）
- [[vwap-mr-jpy-reconfirmation-2026-04-22]] — vwap_mr × {EUR_JPY, GBP_JPY} PAIR_PROMOTED 維持
- [[sr-strategies-signal-track-2026-04-28]]
- [[ema10-8pattern-pullback-stage0-reject-2026-05-05]] — MEMORY: `project_ema10_8pattern_2026_05_05`
- [[s3-cot-dealer-rejection-2026-05-03]] — MEMORY: `project_w3_5_s3_pair_pool_fdr_queued`
- [[s6-w1p0-detector-2026-05-03]]
- [[trend-rebound-thesis-invalid-2026-05-18]]
- [[score-gate-direction-aware-2026-04-28]]

### 🏗️ System / Policy / Architecture (12)
- [[xau-stop-rationale]]
- [[defensive-mode-unwind-rule]]
- [[memory-system-claude-mem-2026-04-24]]
- [[bt-massive-default-2026-05-05]] — MEMORY: [BT は MASSIVE 必須](feedback_bt_must_use_massive)
- [[aggressive-edge-deployment-2026-04-28]]
- [[complex-gate-edge-destruction-pattern-2026-05-03]] — MEMORY: `feedback_ma_filter_breaks_mr` / `feedback_hmm_gate_same_trap`
- [[neighborhood-stability-gate-2026-05-04]]
- [[per-cell-shadow-cap-2026-04-30]]
- [[regime-gate-phase-b25-2026-05-13]]
- [[regime-gate-phase-e-2026-05-13]]
- [[live-shadow-divergence-2026-04-27]]
- [[edge-reset-direction-2026-04-26]]

### 🧮 Quant / Math (3)
- [[aggregate-kelly-decomposition-2026-05-03]]
- [[aggregate-kelly-decomposition-2026-05-03-corrigendum]]
- [[r2-strategy-instrument-counterfactual-2026-05-03]]

### 🗺️ Roadmap / Phase Plans (5)
- [[phase8-master-2026-04-28]]
- [[phase10-g2-investigation-2026-04-29]]
- [[m4-scenario-c-design-2026-04-28]]
- [[roadmap-vwap-calibration-2026-04-23]]
- [[session-decisions-2026-04-13]] — 8件束: bb_rsi USD_JPY降格, 負EV戦略3件停止, Shadow bypass, Equity Reset v89b 等

## Related
- [[index]] — KB top hub
- [[audit-index]] — `learning/` audit ↔ MEMORY 双方向ハブ（数値根拠側）
- [[lessons/index]] — 間違いから学んだ教訓
- [[changelog]] — バージョン別変更タイムライン
- [[edge-pipeline]] — 戦略のStage管理

---

## 整合性 audit (本 index の保守)

新規 decision を追加したら本 index にも 1行追加すること。漏れチェック:
```bash
cd fx-ai-trader/knowledge-base/wiki
# index に未掲載の decisions/ ファイル抽出
comm -23 <(ls decisions/*.md | xargs -n1 basename | sed 's/\.md$//' | sort) \
         <(grep -oE '\[\[[^]]+\]\]' decisions/index.md | sed 's/\[\[\(.*\)\]\]/\1/' | sort)
```
