# Shadow Baseline Analysis — 2026-04-20

**Data source**: `GET /api/sentinel/stats` (Render prod) @ 2026-04-20T23:xx (post P1/P3/P4 deploy)
**Sample**: `is_shadow=1`, XAU excluded, all-time shadow trades
**N**: 1,475 (P3 で発見: 旧 UI 表示 N=1 は 3桁過小計測バグ)

## Purpose (なぜこのページ)

Priority 2 (PAIR_PROMOTED 候補抽出) を **post-P1 データ蓄積を待ってから再実行**する方針のため、
現時点 (P1 デプロイ直後) の shadow 実測を**監視ベースライン**として記録する。

- このページの数値は**昇格判定の根拠には使わない** (truncated sample bias: score_gate 通過分のみ)
- post-P1 新規 shadow (score_gate バイパス対象) と比較する**基準点**として保存
- 1〜2 週間後に P2 を再実行する際、分布シフトの有無を判定する対照データ

参照: [[lesson-bt-live-divergence]] の "6つの構造的楽観バイアス"、[[lesson-orb-trap-bt-divergence]] (サンプル窓バイアス)

## Aggregate (全体)

| 指標 | 値 | 備考 |
|---|---|---|
| N | 1,475 | XAU除外、is_shadow=1 |
| WR | 25.1% | BEV_WR(USD_JPY)=34.4% → **9pp下回る** |
| EV | **-1.55 pip/trade** | 構造的負エッジ (aggregate Kelly=0 と整合) |

→ Shadow 全体はここから昇格できるエッジが無い。個別セグメントで +EV を探す。

## By Instrument

| Pair | N | WR% | EV |
|---|---|---|---|
| USD_JPY | 830 | 26.1 | -1.28 |
| EUR_USD | 365 | 25.2 | -1.07 |
| GBP_USD | 217 | 24.9 | -1.66 |
| EUR_JPY | 42 | 9.5 | **-8.05** |
| GBP_JPY | 12 | 16.7 | **-8.30** |
| EUR_GBP | 9 | 11.1 | -3.32 |

**所見**:
- 主要3ペア (USD/EUR/GBP × USD) はほぼ均質 (WR≈25%, EV≈-1.3pip)
- JPY クロス (EUR_JPY, GBP_JPY) と EUR_GBP は**壊滅的負EV** → Sentinel 対象から外すか、特定戦略に限定すべき
- N は USD_JPY 偏重 (56%)。他ペアは統計的に弱い

## Top Strategies by N

| Strategy | N | WR% | EV |
|---|---|---|---|
| ema_trend_scalp | 192 | 21.9 | -1.48 |
| stoch_trend_pullback | 144 | 27.8 | -0.79 |
| fib_reversal | 139 | 30.2 | -0.71 |
| macdh_reversal | 120 | 25.0 | -1.27 |
| bb_rsi_reversion | 113 | 25.7 | -1.60 |
| sr_channel_reversal | 106 | 19.8 | -1.67 |
| sr_fib_confluence | 102 | 23.5 | **-4.63** |
| engulfing_bb | 89 | 29.2 | -0.17 |
| bb_squeeze_breakout | 69 | 20.3 | -0.26 |
| ema_cross | 47 | 34.0 | -1.94 |

**所見**: 全戦略で aggregate shadow EV が負。高 N 戦略ほど分散が小さいが全て負EV。→ 戦略レベルでは昇格候補なし、**戦略×ペア** 粒度で探す必要。

## +EV 候補 (N ≥ 10, EV > 0)

⚠️ **重要**: このリストは**昇格根拠ではない** — pre-P1 truncated sample。post-P1 データで再検証必須。

| 戦略×ペア | N | WR% | EV | 現 Tier (tier-master) | コメント |
|---|---|---|---|---|---|
| **trend_rebound × USD_JPY** | 12 | 33.3 | +1.43 | ? | N<30、要観測 |
| **dt_sr_channel_reversal × USD_JPY** | 11 | 45.5 | +1.41 | DT戦略 | WR高だが N<30 |
| **dt_bb_rsi_mr × GBP_USD** | 12 | 50.0 | +1.34 | DT戦略 | WR高だが N<30 |
| **vol_surge_detector × USD_JPY** | 22 | 31.8 | +1.27 | SCALP_SENTINEL + PAIR_DEMOTED 全4ペア | 意外 |
| **engulfing_bb × EUR_USD** | 23 | 34.8 | +1.13 | FORCE_DEMOTED | 要再検証 |
| **bb_squeeze_breakout × USD_JPY** | **42** | 28.6 | +0.80 | PAIR_PROMOTED_OVERRIDE (現 Live) | 既存 override、Live実測=+0.41 と整合 |
| dt_bb_rsi_mr × USD_JPY | 14 | 42.9 | +0.21 | DT戦略 | 小 N |

**注目ポイント**:
1. **bb_squeeze_breakout × USD_JPY** が唯一 N≥30 の +EV 候補 (N=42, EV=+0.80)。現在 PAIR_PROMOTED_OVERRIDE として Live 実行中。P2 分析の Live 実測 EV=+0.41 とほぼ整合。→ **維持妥当**
2. vol_surge_detector × USD_JPY (N=22, EV=+1.27) が PAIR_DEMOTED 下で +EV。tier-master は 4ペア全てを PAIR_DEMOTED にしているが USD_JPY だけは再検討候補 (post-P1 N≥30 で再判定)
3. engulfing_bb × EUR_USD (N=23, EV=+1.13) が FORCE_DEMOTED だが +EV。lesson-orb-trap-bt-divergence に照らして 365d BT 符号確認が必要

## High-N Combos (N ≥ 30)

| Combo | N | WR% | EV | 所見 |
|---|---|---|---|---|
| bb_squeeze_breakout × USD_JPY | 42 | 28.6 | **+0.80** | 唯一の +EV 高N |
| engulfing_bb × USD_JPY | 56 | 28.6 | -0.34 | marginal |
| fib_reversal × USD_JPY | 113 | 30.1 | -0.68 | marginal |
| macdh_reversal × EUR_USD | 55 | 29.1 | -0.81 | marginal |
| ema_trend_scalp × USD_JPY | 83 | 25.3 | -0.94 | marginal |
| stoch_trend_pullback × USD_JPY | 103 | 28.2 | -0.96 | marginal |
| ema_trend_scalp × EUR_USD | 73 | 24.7 | -1.02 | marginal |
| ema_cross × USD_JPY | 43 | 34.9 | -1.27 | WR34.9% は BEV 近辺 |
| macdh_reversal × USD_JPY | 61 | 21.3 | -1.66 | 負EV |
| bb_rsi_reversion × USD_JPY | 77 | 23.4 | -1.83 | **[[bb-rsi-reversion]] の Pre-cutoff PF=1.13 から明確に悪化** |
| sr_channel_reversal × USD_JPY | 75 | 18.7 | -1.86 | 負EV |
| ema_trend_scalp × GBP_USD | 36 | **8.3** | **-3.64** | 壊滅、除外候補 |

## Catastrophic Combos (N ≥ 20, EV < -2)

| Combo | N | WR% | EV | 推奨アクション |
|---|---|---|---|---|
| sr_fib_confluence × USD_JPY | 26 | 15.4 | **-7.47** | FORCE_DEMOTED 再確認、現状既にそう |
| sr_fib_confluence × EUR_JPY | 20 | 15.0 | **-7.01** | 同上 |
| ema_trend_scalp × GBP_USD | 36 | 8.3 | **-3.64** | PAIR_DEMOTED×GBP_USD 追加検討 |
| bb_squeeze_breakout × EUR_USD | 22 | **0.0** | **-3.17** | PAIR_DEMOTED 済 (tier-master 確認要) |

## 既知のバイアスと制限

### 1. Truncated Sample Bias (最重要)
- 現行 1,475件は全て `score_gate(score<0)` 通過分のみ
- P1 (score_gate バイパス) デプロイ後は低スコア Sentinel も流れる → **EV はさらに下がる可能性高**
- Kelly 推定に使うには **post-P1 only** フィルタが必須 (例: `entry_time > 2026-04-20T23:00:00`)

### 2. Regime Mixing
- `_FIDELITY_CUTOFF=2026-04-16` 前のトレードも含まれている可能性
- Fidelity Cutoff 後に絞った再分析が必要

### 3. score_gate ブロック率が戦略別に不明
- 「どの戦略が score_gate で最も弾かれていたか」は本分析では計測不可
- 本番ログ `/api/demo/logs` 経由で集計するか、`_sentinel_score_bypass` 発火ログが貯まるのを待つ必要
- **後日追記**: post-P1 の Sentinel bypass ログを集計して bias 補正係数を推定

### 4. N 不足
- +EV 候補 7件中 6件が N<30 → Kelly 評価不能
- N≥30 の +EV は `bb_squeeze_breakout × USD_JPY` 1件のみ (既に Live)

## P2 再実行の判断基準 (post-P1 data)

以下を満たしたら P2 を再実行可:

1. **Post-P1 shadow N ≥ 300** (現状 1,475 → post-P1 only で ~300〜500 想定)
2. **目標戦略×ペアの post-P1 N ≥ 20** (pre-P1 と比較して分布シフトが計測可能)
3. **Fidelity cutoff (2026-04-16) 以降のみ**をフィルタ
4. **BT 側は 365d かつ 60d/180d との符号一致** (lesson-orb-trap-bt-divergence)

推定 timeline: **2026-04-27〜2026-05-03** (P1 デプロイから 1〜2週間)

## Phase 2 追記: Post-P2 merge verification (2026-04-20 later)

P2 (SSOT drift fix) merge + deploy 後の実測 (commit `6438d02`):

### Pool 変動
| Pool | Pre-P2 | Post-P2 | Delta |
|---|---|---|---|
| Live (is_shadow=0) | 559 | 448 | **-111** |
| Shadow (is_shadow=1) | 1,466 | 1,593 | **+127** |
| 期待 migration 数 | - | - | +66 (5 override × historical) |

→ migration 66件 + 新規 shadow (post-P1 bypass) ~50件 が合算

### Aggregate Kelly (新測定)
- edge: **-0.1348**
- full_kelly / half_kelly / quarter_kelly: 全て **0.0**
- 推奨 lot fraction: **0%** (負エッジのため)
- WR 41.07%, odds ratio 1.1065

### 🚨 Strategy-level Kelly 重大発見

| Strategy | Kelly | Edge | 備考 |
|---|---|---|---|
| **vol_momentum_scalp** | 0.0712 | +0.083 | 希少な +EV |
| **mtf_reversal_confluence** | 0.0664 | +0.0766 | 希少な +EV |
| bb_rsi_reversion | 0.0 | -0.022 | marginal 負 |
| dt_sr_channel_reversal | 0.0 | -0.007 | 近break-even |
| vol_surge_detector | 0.0 | -0.042 | marginal 負 |
| ema_trend_scalp | 0.0 | **-0.353** | **深刻な負** |
| trend_rebound | 0.0 | **-0.455** | **最も深刻** |

**全戦略中 Kelly>0 は 2戦略のみ**。aggregate edge=-0.13 の主要因:
- `ema_trend_scalp`: edge -0.353 (N=192 で shadow baseline から観測、大きな影響)
- `trend_rebound`: edge -0.455 (N=21、高インパクト per trade)

### DSR 状態 (Deflated Sharpe Ratio)
- sharpe_observed: -0.087
- is_significant: **false**
- haircut: **100%** (24 trials 補正後、有意エッジ無し)

### Risk state
- DD: 25.9%, lot_multiplier: 0.2 (defensive mode 継続)
- eq_current: -242.1 pip, eq_peak: 16.9 pip

### 含意 — 次の優先課題

1. **ema_trend_scalp と trend_rebound の精査**: 365d BT 再検証 → PAIR_DEMOTED ペア拡張 or FORCE_DEMOTED
2. **vol_momentum_scalp / mtf_reversal_confluence の保護**: 現在の PAIR_PROMOTED 登録状態を確認
3. **aggregate edge -0.13 → 0 到達**: 負edge戦略の剪定 + clean N 蓄積が最短ルート
4. **月利100%目標達成性**: Kelly=0 のままだと position sizing エッジなし → 構造的に目標到達不能。戦略剪定が必須

### 監視サイクル (post-P1 observation)
- 2026-04-22 (2日後): Sentinel N 増分、Strategy Kelly 変動を記録
- 2026-04-27 (1週間後): post-P1 shadow N≥300 蓄積確認 → P2 再実行判断
- 2026-05-01 (1.5週間後): ema_trend_scalp / trend_rebound の剪定判断 (365d BT 必須)

## Related

- [[lesson-sentinel-n-measurement-bug]] — 今回の baseline を取るためのツール (P3)
- [[lesson-sentinel-score-gate-gap]] — P1、shadow 蓄積加速策
- [[lesson-bt-live-divergence]] — 6つの構造的楽観バイアス
- [[lesson-orb-trap-bt-divergence]] — 短期BT符号反転事例
- [[pair-promoted-candidates-2026-04-20]] — P2 初回分析 (復活候補ゼロ判定、本ベースラインで再検証予定)
- [[tier-master]] — 現行 Tier 分類 (Source of Truth)
