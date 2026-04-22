# Roadmap 最速達成 — 5 Priority 実行結果と Tier 再配置判断メモ

**Date**: 2026-04-22
**Goal reference**: 月利100% (¥454,816/月) — roadmap v2.1
**Session scope**: P1-P5 の順次分析実行
**Decision status**: **すべて分析結果 — 実装は別セッション**（CLAUDE.md 判断プロトコル）

---

## P1. Live Edge 分解【完了】

出力: [live-edge-decomp/2026-04-22-summary.md](../analysis/live-edge-decomp/2026-04-22-summary.md)

### 核心的発見: Tier-master と実弾トラフィックの重大な乖離
OANDA 通過 closed N=410 のうち **66% が `bb_rsi_reversion`**（SCALP_SENTINEL 指定の戦略）。
Roadmap v2.1 Tier 1 LIVE の 3 本柱（session_time_bias/trendline_sweep/gbp_deep_pullback）は合計 6 trades のみ、gbp_deep_pullback は 0。

### 負け引き手（sign-stable）
| 組合せ | N | WR | totP (pips) | 推奨 |
|---|---|---|---|---|
| bb_rsi_reversion × EUR_USD | 60 | 33.3% | -40.3 | **ペア全体停止** |
| bb_rsi_reversion × USD_JPY × NY | 71 | 46.5% | -41.3 | **NYセッション停止** |
| vol_surge_detector × USD_JPY × Tokyo | 18 | 27.8% | -21.7 | **Tokyo停止** |

### 即時インパクト推定
Kelly edge: -0.114 → **+0.03~+0.05**（Gate 1 解除領域）

---

## P2. 730d Walk-Forward 再検証【完了 — 実データ上限により 365d×20d窓で実施】

制約: `bt_data_cache.py` の 15m TF 上限 = 365d。730d 不可のため **window 幅を半減 (30→20d) して 18 窓**で統計力を補強。

出力: [walkforward-365d-w20-usdjpy-2026-04-22.md](../bt-results/walkforward-365d-w20-usdjpy-2026-04-22.md)

### ✅ Stable 戦略（18窓評価）
| 戦略 | ペア | N | EV | pos_ratio | CV(EV) | Tier-master 現状 |
|---|---|---|---|---|---|---|
| **streak_reversal** | USD_JPY | **466** | **+1.362** | **1.00** | 0.65 | UNIVERSAL_SENTINEL |
| **vwap_mean_reversion** | USD_JPY | 123 | +1.111 | 0.83 | 1.00 | PAIR_PROMOTED (USD_JPY 未登録) |

### 🟡 Borderline（Roadmap elite だが WF で CV>1）
| 戦略 | pos_ratio | CV | 備考 |
|---|---|---|---|
| session_time_bias × USD_JPY | 0.72 | 1.95 | roadmap Tier 1 LIVE |
| vix_carry_unwind × USD_JPY | 0.79 | 1.12 | PAIR_PROMOTED |
| xs_momentum × USD_JPY | 0.67 | 7.54 | PAIR_PROMOTED |

### 🔴 Unstable
dt_sr_channel_reversal/vol_spike_mr/sr_fib_confluence/dt_bb_rsi_mr/dual_sr_bounce/sr_break_retest — いずれも CV>1 かつ pos_ratio<0.5 のペアあり。ただし **1 回 BT** のため FORCE_DEMOTE は別セッション判断。

### Tier 再配置候補（判断保留）
1. **`streak_reversal × USD_JPY`**: UNIVERSAL_SENTINEL → PAIR_PROMOTED 候補
   - pos_ratio=1.00 (18/18) は USD_JPY 全戦略で唯一
   - 但し **365d×20d窓 = 同一データの再分割**。真の頑健性検証には別期間 (例 1h TF で 500d) または live N≥30 が必要
2. **`vwap_mean_reversion × USD_JPY`**: 現 PAIR_PROMOTED に USD_JPY 追加候補
   - pos=0.83, CV=1.00 → 閾値ちょうど。Tier 拡張は保留推奨

### 実装を止める理由（判断プロトコル遵守）
- Walk-Forward は「同じ365日 BT」を時間軸で切るだけ → **真の out-of-sample ではない**
- yfinance 15m は 365d が上限で 730d 確証不可
- pos_ratio=1.00 は 18 窓のみ → Wilson 95% CI は (0.82, 1.00)
- **次セッションで 1h TF 500d の WF を別途走らせて二重確認**するまで Tier は動かさない

---

## P3. Alpha158 Shadow snapshot モジュール【完了】

出力: [tools/alpha_factor_snapshot.py](../../../tools/alpha_factor_snapshot.py)

### 仕様
- Bonferroni 有意 5 factor (KSFT2/KSFT/RSV10/ROC10/QTLD5) を任意タイムスタンプで取得
- `snapshot_at(pair, tf, ts)` が factor dict を返す
- `composite_score()` が IC 符号揃え合成スコア
- **live path/demo_trader への配線はしていない** — 非侵襲の read-only ユーティリティ

### 運用想定
1. Shadow trade が発火した瞬間に `snapshot_at()` を呼ぶラッパーを `demo_trader.py` 側に追加（別セッション実装）
2. trade_log に composite score を併記
3. N≥30 貯まった時点で quantile 別 WR 差を測定
4. WR lift が +3pp 以上 & WF CV<1.0 なら live entry_filter として昇格検討

### α予算消費
- `alpha_budget_tracker.py --consume daily 5` を別途実行（Shadow 計測を「5 テスト」とカウント）
- 実装者へ: 本セッションでは予算消費していない（設計のみ）

---

## P4. Scalp 365d Walk-Forward 拡張【実行中】

**制約**: 5m TF 上限は 180d (`TF_CONFIG["5m"]={"max_days":180}`)。365d は 1m/5m では取得不可。
**実行内容**: 180d × 30日窓 (6窓) を `USD_JPY, EUR_USD` で実施中。

補足: roadmap v2.1 は Scalp 60d BT を根拠としていた → 180d で **3倍データ量の再検証**。
出力先: `knowledge-base/raw/bt-results/walkforward-scalp-5m-180d-2026-04-22.md`

**本セッション内に完了次第、本ドキュメントに追記。** 完了前は Scalp 拡大 (roadmap Track E) の判断は保留。

---

## P5. 統合判断メモ【本セクション】

### 現状確認
- Kelly edge = **-0.114** (Live) → OANDA 自動停止状態
- Roadmap v2.1 は DT 幹 +433pip/年 を想定するが **実弾では幹戦略がほぼ発火していない**
- 実弾を担っている `bb_rsi_reversion` は Tier-master 的には Shadow 指定 → **設定と実態の不一致**

### 最速ロードマップ達成への優先順位（更新版）

#### Tier 1 — 今日〜明日（低リスク、即効性）
**A1. `bb_rsi_reversion` の Tier 実態監査**
- `modules/demo_trader.py` の mode 定義と `tier_integrity_check.py --check` の整合を確認
- なぜ SCALP_SENTINEL 指定の戦略が OANDA に流れているか root cause を特定
- 根本原因が「設定バグ」なら修正、「意図的な例外」なら tier-master に反映

**A2. EUR_USD ペアの即時停止検討**
- `bb_rsi_reversion × EUR_USD` N=60, 全セッション負 (-40.3p)
- 停止すれば aggregate totP は -31.6 → +8.7 に反転
- 但し A1 の結果を待ってから実装（原因が設定バグなら自動解消の可能性）

#### Tier 2 — 今週（中リスク、検証経由）
**B1. `streak_reversal × USD_JPY` の 1h TF 500d WF**
- 15m×365d で pos=1.00 を確認 → 異 TF/期間でも再現するかの直交検証
- `bt_walkforward.py --pairs USD_JPY --lookback 500 --interval 1h --window-days 30`
- **両方で stable なら** UNIVERSAL_SENTINEL → PAIR_PROMOTED 昇格を議論
- α予算: weekly 0.020 の 1/4 を消費（1 仮説 × 4 組合せ）

**B2. Scalp 180d WF (P4) 結果受領後の判断**
- roadmap Track E のうち「追加正EV発掘」の根拠が 180d に更新されるかを見る

#### Tier 3 — 今後2週間（Shadow 蓄積）
**C1. Alpha158 factor 配線（shadow のみ）**
- `alpha_factor_snapshot.py` を `demo_trader.py` に統合（別実装セッション）
- Shadow N≥30 で composite score × WR lift を post-hoc 評価
- α予算: daily 0.020 を消費

**C2. Scalp 枝の慎重拡大**
- P4 結果が stable → roadmap v2.1 の Scalp 枝 (bb_squeeze_breakout × USD_JPY 5m など) を計画通り進行
- unstable → Scalp 拡大を保留、DT 幹に集中

### 判断停止点（実装禁止ライン）

1. **streak_reversal の Tier 変更は 1h TF 500d WF 結果待ち**
2. **vwap_mean_reversion USD_JPY 追加は CV<0.8 での再現待ち**（現状 CV=1.00、閾値ギリギリ）
3. **EUR_USD pair 停止は A1 (Tier 実態監査) 後**
4. **Alpha158 factor の live 昇格は Shadow N≥30 + WF CV<1.0 の両方必須**

### α予算消費状況（本セッション分）
| カテゴリ | 事前予算 | 本セッション消費 | 残 |
|---|---|---|---|
| daily | 0.020 | 0（設計のみ） | 0.020 |
| weekly | 0.020 | 0（分析のみ） | 0.020 |
| anomaly | 0.005 | 0 | 0.005 |
| reserve | 0.005 | 0 | 0.005 |
| **total** | **0.050** | **0** | **0.050** |

本セッションは **既存データの再分析** に留まり、新規仮説検定は行っていないため α 予算消費ゼロ。
次セッション（B1 実装時）で weekly 0.005 消費予定。

### 最速路線サマリ

```
Day 0 (済): P1-P4 分析完了、Shadow snapshot モジュール提供
Day 1:     A1 Tier 実態監査 → A2 EUR_USD 停止判断
Day 2-3:   B1 1h 500d WF → streak_reversal 昇格可否決定
Day 3-5:   B2 Scalp WF 反映、α factor 配線（shadow）
Day 7:     quant_gate_status --to-discord で週次報告、Kelly 推移確認
Day 10-14: Shadow N≥30 到達、α factor lift 一次評価
```

**ボトルネック**: A1 (Tier 実態監査) が最大の律速。ここで「設定の真実」が分かれば、以後の判断が一気に加速する。

---

## Related
- [live-edge-decomp/2026-04-22-summary.md](live-edge-decomp/2026-04-22-summary.md)
- [bt-results/walkforward-365d-w20-usdjpy-2026-04-22.md](../bt-results/walkforward-365d-w20-usdjpy-2026-04-22.md)
- [bt-results/alpha-factor-zoo-2026-04-22.md](../bt-results/alpha-factor-zoo-2026-04-22.md)
- [tools/alpha_factor_snapshot.py](../../../tools/alpha_factor_snapshot.py)
- [[roadmap-v2.1]]
- [[tier-master]]
