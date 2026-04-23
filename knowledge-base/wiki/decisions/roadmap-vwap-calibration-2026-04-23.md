# Roadmap: Signal Calibration Rescue (VWAP → Multi-Enhancer)

**Date**: 2026-04-23
**Owner**: クオンツ analyst
**Goal**: 月利100% (¥454,816/月) への EV 改善経路を calibration 修正で確保

## 背景サマリ

2026-04-23 に commit `b37ee8b` で VWAP conf_adj を中立化したが、その後の TF root-cause
分析 (N=568) で **「方向一致」「機関フロー」「HVN」** など他の enhancer ラベルも
逆校正されていることが判明。単一 VWAP 修正では不十分。

参照:
- [[vwap-calibration-baseline-2026-04-23]] (N=2039 baseline)
- [[tf-inverse-rootcause-2026-04-23]] (TF root-cause)
- [[lesson-vwap-inverse-calibration-2026-04-23]]

## Phase 分類

### Phase 1 ✅ COMPLETED (2026-04-23)

- [x] VWAP conf_adj 中立化 (`massive_signals.py:_vwap_zone_analysis`)
- [x] Baseline snapshot 固定 (N=2039)
- [x] 監視ツール `tools/vwap_calibration_monitor.py` 作成
- [x] KB lesson + TF root-cause 分析
- [x] 戦略カテゴリレジストリ `modules/strategy_category.py` 作成 (注入未)

### Phase 2a 🔥 URGENT — 追加 enhancer 中立化 (次セッション候補)

TF root-cause で発見した逆校正因子を順次中立化:

| # | Target | File | Expected EV lift |
|---|---|---|---|
| 1 | MTF alignment `aligned` 加点中立化 | `massive_signals.py:_mtf_gate` or 類似 | +3-5p/TF |
| 2 | 「機関フロー」ラベル conf_adj 中立化 | `massive_signals.py:_institutional_flow` | +2-4p/TF |
| 3 | HVN 加点中立化 | `massive_signals.py:_volume_profile` | +1-2p/TF |
| 4 | 「方向一致」断定文言削除 | 全 enhancer の reasons 生成 | 間接 (解釈バイアス除去) |

**判定ゲート**: 各修正ごとに `vwap_calibration_monitor.py` で TF Delta WR が
改善したか確認 (目標: -9.0pp → -3pp 以上)

### Phase 2b 📊 A2 FOLLOW-UP (計測タスク, N 蓄積待ち)

| # | アクション | トリガ | 備考 |
|---|---|---|---|
| A2.1 | commit `b37ee8b` deploy 確認 | Render auto-deploy log | 即時 |
| A2.2 | Shadow post-fix N≥200 蓄積 | ~1週間 | 毎日 `tools/vwap_calibration_monitor.py --since 2026-04-24` |
| A2.3 | Phase 2 GO/NOGO gate 判定 | A2.2 完了時 | Pooled Delta WR が +3pp に反転なら GO |
| A2.4 | 判定結果を KB `timeseries` page に追記 | A2.3 完了時 | タイムシリーズで trend 可視化 |

**GO/NOGO 分岐ルール** (A2.3):

| Pooled Delta WR 変化 | 判定 | 次アクション |
|---|---|---|
| -6.1pp → ≥ +3pp (反転) | GO ✅ | カテゴリ別 conf_adj 復活 (Phase 3a) |
| -6.1pp → -3〜+3pp (flat) | 部分GO | 他 enhancer 逆校正特定 → Phase 2a 実施 |
| -6.1pp → -3pp 以下 (変化なし) | NOGO | 根本対策 (Phase 3b: 全中立化 + calibrated gate) |

### Phase 2c 🎯 Shadow 昇格候補 (N 蓄積待ち)

| # | Strategy | Current N | Target N | Status |
|---|---|---|---|---|
| B2 | engulfing_bb_lvn_london_ny | 0 (routing deploy後) | 30 | 待機 (retrospective N=27 で 2/3 gate pass) |
| B1 | sr_fib_confluence_tight_sl (未実装) | — | — | VWAP修正後 baseline 再計測で GO判定 |

### Phase 3a 🛠️ カテゴリ別 conf_adj 復活 (2-3週間先)

Phase 2a + 2b が条件付きで GO 判定の場合:

- `strategy_category.py` の `apply_policy()` を enhancer に注入
- TF は VWAP+2 維持 / MR は -2 反転 / BR は中立
- Shadow A/B で 2週間計測、Delta WR を monotonic 化

### Phase 3b 🧪 Calibrated Gate (最終形)

Phase 2 で逆校正が解消しない場合の根本対策:

- 過去 shadow データで sklearn `CalibratedClassifierCV` (isotonic) fit
- confidence score → calibrated probability 変換
- Gate を `p_win > 0.50` で一元化
- 既存 conf_adj は全廃

## 優先順位 (月利100%目標への寄与度)

| Priority | Phase | Item | Risk | Reward | Window |
|---|---|---|---|---|---|
| 🥇 | 2a.1 | MTF aligned 中立化 | 低 | 高 (+3-5p) | 即 |
| 🥇 | 2a.2 | 機関フロー 中立化 | 低 | 中 (+2-4p) | 即 |
| 🥈 | 2a.3 | HVN 中立化 | 低 | 低-中 (+1-2p) | 即 |
| 🥈 | 2b | A2 follow-up | 0 (計測) | データ価値 | 1週後 |
| 🥉 | 2c.B2 | engulfing_bb_lvn_london_ny 昇格 | 低 | 中 | 1-2週後 |
| 🥉 | 2c.B1 | sr_fib_confluence_tight_sl 実装 | 中 | 高 (+6p/trade) | 2-3週後 |
| 🏅 | 3a | カテゴリ別 conf_adj | 中 | 高 | 3-4週後 |
| 🏅 | 3b | Calibrated gate | 高 | 超高 | 4-8週後 |

## 測定ディシプリン (全 Phase 共通)

1. **施策実装前に baseline 固定** (既に vwap-calibration-baseline-2026-04-23 で実施済)
2. **Shadow N≥200 蓄積待ってから判定** (pre/post 比較可能な同一週次 window)
3. **Bootstrap 95% CI + Top1-drop 必須** (過去の Lever-B 失敗の教訓)
4. **Monotonicity check** (confidence → WR が単調増加しているか)
5. **各 Phase 完了時に KB timeseries page に追記**
