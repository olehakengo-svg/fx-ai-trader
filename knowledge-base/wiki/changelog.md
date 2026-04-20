# Changelog — バージョン別変更と評価基準日

## なぜこのページが重要か
定量評価は「いつからのデータを使うか」で結論が180度変わる。
各バージョンの変更が**どのトレードに影響するか**をここで追跡する。

## Fidelity Cutoff Timeline

```
2026-04-02  システム稼働開始
     |
2026-04-08  ★ Fidelity Cutoff (v6.3 SLTP修正後)
     |       ├── この日以降のデータ = "クリーンデータ"
     |       └── 以前のデータ = "バグ汚染データ"（SLTPチェッカーバグ含む）
     |
2026-04-09  v7.3-v7.6: XAU修正チェーン
     |       └── XAUデータ: v7.5以前は MAX_SL_DIST=$0.20バグで汚染
     |
2026-04-10  ★★ v8.0-v8.3: 戦略大改革
     |       ├── v8.0: vol_momentum 2.0x, engulfing_bb停止, TREND_BULL遮断
     |       ├── v8.1: TREND_BULL MR免除
     |       ├── v8.2: orb_trap PAIR_PROMOTED, vol_momentum 1.0x
     |       ├── v8.3: 確認足フィルター（bb_rsi/fib/ema_pullback）
     |       └── v8.3以降のデータ = "確認足効果測定用"
     |
2026-04-10  ★★★ v8.4: XAU停止 + Shadow汚染除去
     |       ├── XAUモード停止: scalp_xau, daytrade_xau auto_start=False
     |       ├── get_stats() is_shadow=0 フィルター追加
     |       └── v8.4以降 = "FX-only クリーンデータ"
     |
2026-04-12  Knowledge Base構築
     |       └── 評価基盤の確立
     |
2026-04-12  ★ v8.5: 学術文献6新エッジ戦略 (全Sentinel)
     |       ├── session_time_bias, gotobi_fix, london_fix_reversal
     |       ├── vix_carry_unwind, xs_momentum, hmm_regime_filter
     |       └── 25論文ベース、DaytradeEngine 32戦略化
     |
2026-04-12  ★★ v8.6: 本番昇格 + モード再編
     |       ├── session_time_bias × 3ペア PAIR_PROMOTED (BT WR=69-77%)
     |       ├── london_fix_reversal × GBP_USD PAIR_PROMOTED (BT WR=75%)
     |       ├── london_fix_reversal × USD_JPY PAIR_DEMOTED (BT WR=28.6%)
     |       ├── xs_momentum × USD_JPY PAIR_DEMOTED (BT EV=-0.129)
     |       ├── scalp_eurjpy auto_start=False (friction/ATR=43.6%, 構造的不可能)
     |       ├── scalp_5m_eur + scalp_5m_gbp 新規モード追加 (5m摩擦改善)
     |       ├── 金曜/月曜ブロック全撤去 — 原則#1「攻める」準拠
     |       ├── GBPアジアセッション除外フィルター実装
     |       ├── DSR (Deflated Sharpe Ratio) 実装 — Bailey & Lopez de Prado (2014)
     |       └── BT/Live乖離分析: bb_rsi 25pp乖離の原因分解完了
     |
2026-04-12  v8.7: BT基盤強化
     |       ├── BT Friction Model v3 (Spread/SL Gate + RANGE TP + Quick-Harvest反映)
     |       ├── backtest-long DT/1H対応 (120-365日チャンクBT)
     |       └── BT/Live乖離: Scalp 14-27pp→5-10pp, DT 5.5-10pp→2-4pp (期待)
     |
2026-04-12  v8.8: 生データアルファマイニング
     |       ├── vol_spike_mr: 3x range spike fade (BT JPY PF=1.92, 全戦略最高)
     |       ├── doji_breakout: 3連続doji breakout follow
     |       ├── post_news_vol × USD_JPY PAIR_DEMOTED (120d WR=0%)
     |       └── ema200_trend_reversal × USD_JPY PAIR_DEMOTED (120d WR=0%)
     |
2026-04-13  ★★★ v8.9: Equity Reset — クリーンデータ起点
     |       ├── 旧DD: 2,899pip (289.9%) ← XAU(-2,280pip) + pre-cutoffバグ汚染
     |       ├── リセット: v8.4(2026-04-10T12:00)以降FX-only非Shadowで再計算
     |       ├── 新DD: 8.4pip (0.8%) → lot_mult=1.0x (フルロット)
     |       └── ワンショットマイグレーション (eq_reset_v89フラグで1回のみ実行)
     |
2026-04-17  ★ v9.2.1: MTF Regime Engine + v9.2 guardrail 無効化
     |       ├── D1×H4×H1 階層 regime labeler (7-class)
     |       ├── EUR_USD η² 105× improvement, flip rate 6.1%→0.6%
     |       ├── v9.2 guardrail デフォルト無効化 (6.5年検証で符号逆)
     |       └── shadow_monitor + DB mtf_* カラム追加
     |
2026-04-17  ★★ v9.3 Phase A-C: Strategy-aware MTF + P0 Family Map Forensics
     |       ├── Phase A: 戦略ファミリ考慮 retrospective (LIVE aligned WR +22.9pp)
     |       ├── Phase B: 本番OOS反実仮想 (+508p 改善) — TF sign flip 検出
     |       ├── Phase C P0: 3戦略 mislabel 修正 (macdh_reversal/engulfing_bb → TF, ema_cross → MR)
     |       ├── CORRECTED map で ALL Δ PnL +306p→+1129p (3.7×), 全family符号一致
     |       └── research/edge_discovery/strategy_family_map.py (production module)
     |
2026-04-17  ★★★ v9.3 Phase D+E: A/B Gate Routing + REGIME_ADAPTIVE
             ├── **Phase D**: Hash-based A/B routing (MD5 mod 2 → mtf_gated / label_only)
             │   ├── DB: gate_group / mtf_alignment / mtf_gate_action 追加
             │   ├── Group A conflict → LIVE→SHADOW downgrade (soft gate)
             │   └── 50/50 分布確認 (N=1000 ±50)
             ├── **Phase E**: REGIME_ADAPTIVE_FAMILY (regime別 family override)
             │   ├── bb_rsi_reversion: trend_up=TF / trend_down=MR
             │   ├── fib_reversal: trend_up=MR / trend_down=TF
             │   └── LIVE ΔWR +2.4pp→+9.3pp (4×), IS aligned gap +12.0pp
             └── Tests: 234 passed (new: test_ab_gate.py 7 + TestRegimeAdaptive 7)

2026-04-20  v9.3 Phase F: FAMILY MAP 拡張 — ELITE_LIVE/PAIR_PROMOTED 6戦略追加分類
             ├── **TF追加**: gbp_deep_pullback, trendline_sweep (wiki Category根拠)
             ├── **MR追加**: vwap_mean_reversion, wick_imbalance_reversion (wiki MR根拠)
             ├── **SE追加**: london_fix_reversal (Krohn 2024), vix_carry_unwind (Brunnermeier 2009)
             ├── 未分類→"unknown"から"conflict/neutral"へ: A/B gate が ELITE_LIVEにも機能するように
             ├── RANGINGレジーム下: gbp_deep_pullback/trendline_sweep → conflict → shadow降格（正常）
             ├── RANGINGレジーム下: vwap_mean_reversion/wick_imbalance_reversion → aligned（正常）
             ├── pending (BT forensics必要): doji_breakout, post_news_vol, squeeze_release_momentum
             └── Tests: 234 passed (既存テスト全pass、新分類はwiki根拠で実装)

2026-04-20  ★ v9.4: wiki/strategies KB ドリフト一掃 + 検出ツール導入
             ├── 13 ページの Status 行を tier-master.json と整合
             │   ├── bb-rsi-reversion.md: "Tier 1 PP×USD_JPY" → SCALP_SENTINEL + PAIR_DEMOTED(全4ペア)
             │   ├── orb-trap.md: "Tier 1 PP×3ペア" → FORCE_DEMOTED (v9.1 負EV確定)
             │   ├── trendline-sweep.md: "ELITE+FD+PP" → ELITE_LIVE のみ (v9.0 整理)
             │   ├── bb-squeeze-breakout / engulfing-bb / sr-channel-reversal / ema-pullback:
             │   │   FD下のPP死コード記述を削除 (v9.1 cleanup 反映)
             │   ├── london-fix-reversal: "PP×GBP" → Phase0 Shadow (v9.1 GBP PP削除)
             │   ├── vol-momentum-scalp: "SHADOW" → PAIR_PROMOTED×EUR_JPY
             │   ├── three-bar-reversal: "UNI_SENTINEL" → Phase0 Shadow
             │   ├── stoch-trend-pullback: "Sentinel" → FORCE_DEMOTED (v8.9 剥奪)
             │   ├── vol-surge-detector: "Sentinel" → SCALP_SENTINEL + PAIR_DEMOTED
             │   ├── doji-breakout: Status追加 (UNI_SENTINEL + PP×GBP/USDJPY)
             │   ├── fib-reversal: "Tier 2" → FORCE_DEMOTED (Recovery Path active)
             │   ├── liquidity-sweep: "Tier 2 Sentinel" → UNIVERSAL_SENTINEL 明示
             │   ├── post-news-vol: Status 行の USD_JPY をPP→PAIR_DEMOTED に訂正
             │   └── dual-sr-bounce: "FORCE_DEMOTED" → REMOVED (v9.1 死コード削除)
             ├── 旧 Status は「履歴」/「Previously ...」で保持 (削除禁止ルール遵守)
             ├── **新ツール**: tools/strategies_drift_check.py
             │   ├── tier-master.json を truth source として読み込み、md の Status 行を検証
             │   ├── 否定コンテキスト / 履歴マーカーはスキップ
             │   ├── PAIR_PROMOTED scope 内のペアのみ truth と突合
             │   └── exit 1 で pre-commit / CI 組み込み可能
             ├── **テスト**: tests/test_strategies_drift_check.py (11 cases, all pass)
             │   └── 実 KB 回帰テスト込み (test_live_kb_passes_drift_check)
             ├── **lesson**: wiki/lessons/lesson-strategies-page-drift.md
             │   └── lesson-kb-drift-on-context-limit の strategies/ 特化版
             └── 独立ツール設計: tier_integrity_check.py (code 整合) と分離
                 pre-commit 実行順: tier_integrity_check --write → strategies_drift_check

2026-04-20  ★ v9.x Priority 3: Sentinel N 測定バグ修正
             ├── **症状**: UI で 62 戦略中 bb_squeeze_breakout のみ N=1、他 61 戦略 N=0
             │   └── 実測: 本番 DB に closed Shadow trades が 1,466 件存在
             ├── **原因**: `get_trades_for_learning` は is_shadow=0 固定フィルタ
             │   └── `_strategy_n_cache` → `_build_strategy_status_map` の n が Live のみに
             ├── **修正**: `get_shadow_trades_for_evaluation()` 新関数 (is_shadow=1 固定)
             │   ├── `_build_strategy_status_map` に shadow_n/wr/ev 付与
             │   ├── `/api/sentinel/stats` 新設 (entry_type/instrument/after_date フィルタ)
             │   └── `get_trades_for_learning` は**変更なし** (lesson-shadow-contamination 維持)
             └── Tests: 244 passed (new: test_shadow_stats.py 10 = 正例4+負例3+空3)
             参照: [[lesson-sentinel-n-measurement-bug]]
```

## バージョン別データ切り口

| 目的 | date_from | 除外条件 | 理由 |
|------|----------|---------|------|
| 全体傾向 | 2026-04-08 | is_shadow=0 | Fidelity Cutoff後クリーンデータ |
| **v8.3確認足効果** | **2026-04-10** | is_shadow=0 | v8.3デプロイ後のみ |
| **XAU停止効果** | **2026-04-10 夕方〜** | is_shadow=0, XAU除外 | v8.4デプロイ後 |
| **FX純粋評価** | 2026-04-08 | is_shadow=0, XAU除外 | FXのみの真のパフォーマンス |
| BT/ライブ比較 | 全期間 | なし | BT乖離幅の把握 |

## 各バージョンの影響範囲

### v7.x (2026-04-09): XAU修正チェーン
| Version | Change | Affected Strategies | Affected Data |
|---------|--------|-------------------|---------------|
| v7.3 | gold PBルーズ化+bbσバグ修正 | gold_trend_momentum | XAU DT |
| v7.4/b/c | extreme_momentum: ADX≥25, MACD-H/EMA9免除 | gold_trend_momentum | XAU DT |
| v7.5 | MAX_SL_DIST: XAU $0.20→$100 | **全XAU戦略** | ★ v7.5前のXAU SLデータは全て汚染 |
| v7.6 | Sentinel units: XAU 1000u→1u | XAU OANDA連携 | XAU audit |

### v8.x (2026-04-10〜): 戦略大改革
| Version | Change | Impact on Data |
|---------|--------|---------------|
| v8.0 | vol_momentum 2.0x, TREND_BULL全遮断 | DT TREBULLトレード消滅 |
| v8.1 | MR免除 (dt_bb_rsi_mr, dt_sr_channel_reversal通過) | DT MRトレード復活 |
| v8.2 | orb_trap PAIR_PROMOTED, vol_momentum 1.0x, bb_squeeze停止 | orb_trap OANDA送信開始 |
| **v8.3** | **確認足(bb_rsi/fib/ema_pullback)** | **★ 即死率の変化を測定する基準点** |
| **v8.4** | **XAU停止 + Shadow除去** | **★ FX-onlyの真のPnLを測定する基準点** |
| v8.5 | 学術文献6新エッジ戦略 (全Sentinel) | 新戦略のライブデータ蓄積開始 |
| **v8.6** | **session_time_bias/london_fix PROMOTED + 5mモード拡張 + DSR実装** | **★ 学術エッジの本番検証開始** |
| v8.7 | BT Friction Model v3 + backtest-long | BT信頼性向上 (乖離幅縮小) |
| v8.8 | vol_spike_mr + doji_breakout + PAIR_DEMOTED追加 | 新アルファ源 + 出血戦略停止 |

## Related
- [[edge-pipeline]] — エッジ仮説の評価はどのデータ期間を使うべきか
- [[independent-audit-2026-04-10]] — "Shadow除去なしにWR/EVは信頼できない"
- [[bb-rsi-reversion]] — WR 52.2% vs 34% の矛盾はデータ期間の差
- [[friction-analysis]] — avg_friction 7.04 は XAU込み。FX-only≈2.5pip
