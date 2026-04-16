# Quick Harvest (QH) — Quant分析 2026-04-16 (更新: 全戦略マッピング追加)

## 概要
OANDA送信時に TP距離を ×0.85 に短縮する含み益保護メカニズム。
実装: `modules/demo_trader.py:3997-4005, 4934-4943`

**設計意図**: DT WIN 7件の19.2pip利益漏出修復（v6.8で0.70→0.85に緩和）

**適用条件**:
1. `is_promoted=True` かつ Bridge active (OANDA実行パス)
2. `(entry_type, instrument)` が EXEMPT に含まれない
3. RANGE_MR ではない（BB_mid TPで既に短縮済み）
4. `_signal_price > 0` かつ `abs(tp - _signal_price) > 0`

## EXEMPT List (v8.9)
| Strategy | Pair | 理由 |
|---|---|---|
| gbp_deep_pullback | GBP_USD | 高WR戦略 (BT WR=72.6%) |
| session_time_bias | USD_JPY | BT WR=79.0% (4-6h保有、TP到達率高い) |
| session_time_bias | EUR_USD | BT WR=69.0% (N=526) |
| session_time_bias | GBP_USD | BT WR=67.1% |
| london_fix_reversal | GBP_USD | BT WR=75.0% |
| vix_carry_unwind | USD_JPY | BT WR=69.9%, イベント戦略 |

---

## 定量分析結果 (2026-04-16)

### 理論: QH のブレークイーブンWR
```
R (Reward/Risk) = 0.85/1.0 = 0.85
BEV = 1 / (1 + R) = 54.05%
```
QH適用で **BEVは 50% → 54.1% に +4.05pp 上昇**。WR<54.1%では QH が損失拡大する。

### Live data (alpha-scan-2026-04-15): QH適用群のWR
| Strategy × Pair | N | WR% | EV | BEV 54.1% 比 |
|---|---|---|---|---|
| ema_pullback USD_JPY | 15 | **46.7%** | **+1.66** | -7.4pp |
| vol_momentum_scalp USD_JPY | 14 | **57.1%** | +0.62 | +3.0pp ✅ |
| fib_reversal USD_JPY | 29 | 31.0% | +0.21 | -23.1pp |
| vol_surge_detector USD_JPY | 32 | 46.9% | -0.10 | -7.2pp |
| bb_rsi_reversion USD_JPY | 90 | 36.7% | -0.31 | -17.4pp |
| sr_channel_reversal USD_JPY | 33 | 15.2% | -1.88 | -38.9pp |
| ... | ... | ... | ... | ... |

**加重平均 (14セル, N=342): WR=34.5% << BEV 54.1% (乖離 -19.5pp)**

→ QH適用群の **95.9% (N=328/342) が BEV 以下** で QH が構造的に損失を拡大している。

### Counterfactual: QH除去時の推定EV
保守的近似モデル: TP×1.0 で TP到達率 0.92倍, 勝ち利益 ×1.176

| Strategy × Pair | N | EV_qh (実測) | EV_noQH (推定) | 判定 |
|---|---|---|---|---|
| ema_pullback USD_JPY | 15 | +1.66 | **+1.80** (+0.14) | QH除去推奨 |
| vol_momentum_scalp USD_JPY | 14 | +0.62 | +0.66 | QH除去推奨 |
| fib_reversal USD_JPY | 29 | +0.21 | +0.26 | QH除去推奨 |
| stoch_trend_pullback USD_JPY | 28 | -0.14 | -0.12 | QH除去で損失緩和 |
| bb_rsi_reversion USD_JPY | 90 | -0.31 | -0.31 | QH維持でも同程度 |
| sr_channel_reversal USD_JPY | 33 | -1.88 | -1.98 | **QH維持で損失緩和(-0.10)** |

**結論**:
- **正EV戦略 (ema_pullback, vol_momentum_scalp, fib_reversal)**: QH除去で EV 向上 (+0.04〜+0.14/trade)
- **深い負EV戦略 (sr_channel_reversal 等)**: QHで微かに損失緩和（-0.10/trade 程度）
- しかし深い負EV戦略は本来 FORCE_DEMOTED すべき対象。QHは「応急処置」に過ぎない

### EXEMPT 戦略: BT vs Live 検証
| Strategy × Pair | BT N | BT WR | BT EV | Live N (post-cutoff) |
|---|---|---|---|---|
| gbp_deep_pullback GBP_USD | 84 | 72.6% | +1.10 | <5 (不明) |
| session_time_bias EUR_USD | 526 | 69.0% | +0.30 | <5 (不明) |
| session_time_bias USD_JPY | 103 | 79.0% | +0.58 | <5 (不明) |
| london_fix_reversal GBP_USD | 60 | 75.0% | +0.72 | <5 (不明) |
| vix_carry_unwind USD_JPY | 103 | 69.9% | +0.52 | <5 (不明) |

**加重BT平均: WR=70.6% (N=976) >> BEV 54.1% → EXEMPT妥当 (BT基準)**

ただし **post-cutoff Live では全て発火数不足 (N<5)** で EXEMPT決定を Live で検証できていない。

---

## 批判的考察

### Paradox: QH が最も必要な戦略には適用されていない
QH は「含み益保護」と銘打たれているが、実態は「**低WR戦略に適用され、高WR戦略を除外**」している。
- 低WR戦略: QH適用 → BEV +4pp 上昇 → 更に不利益
- 高WR戦略: EXEMPT → QHなし → フル利益確保

これは設計としては合理的（高WR=TP届く確率高い=短縮不要）だが、
**「QHが実際に助けている戦略は存在しない」** という現状を示している。

### 真の問題: MFE を収穫するなら Trailing Stop が優位
QH は「エントリー時点で TP を静的に短縮」する手法。より動的な代替:

- **MFE > 50% で BE+ シフト** (Breakeven Plus)
- **Chandelier Exit** (ATR-based trailing)
- **Dynamic TP by regime** (TREND: 1.0x, RANGE: 0.7x, SQUEEZE: block)

現在の QH ×0.85 は RR を一律削るだけで、相場環境を見ていない。

---

## 推奨アクション (優先度順)

### P0: データ蓄積継続 (根拠ベース判断まで)
- EXEMPT戦略の Live N≥30 蓄積を待つ (推定 2-3週間)
- 現時点で EXEMPT変更は **保留** (CLAUDE.md 判断プロトコル準拠)

### P1: 情報フラグ追加 (非破壊)
- demo_trader.py で `quick_harvest_applied: bool` フラグを trade record に追加
- これにより将来の QH vs non-QH A/B 比較が可能に
- **リスク: 低** (記録追加のみ、挙動変更なし)

### P2: 要再検証 (N≥30到達後)
- **ema_pullback USD_JPY** を EXEMPT 追加候補（BT N=10→30到達後）
  - 現在 Live WR=46.7% EV=+1.66 → QH除去で +1.80 推定
- **fib_reversal USD_JPY** を EXEMPT 追加候補（Live N=29→30近い）
  - BT WR=40.6% だが Live で EV+0.21 → TP到達率は悪くない

### P3: 設計改良 (将来検討)
- **QH比率のWR依存動的化**:
  - BT WR≥65%: QH=0.95 (ほぼ無効)
  - BT WR 55-65%: QH=0.90
  - BT WR 45-55%: QH=0.85 (現状維持)
  - BT WR <45%: QH なし (FORCE_DEMOTED 候補)
- **Trailing Stop への移行検討**: MFE≥50%で BE+2pip シフト

### P4: 文書整備 (このファイル)
- [x] wiki/strategies/quick-harvest.md 作成
- [ ] roadmap-v2.1 に QH 改良項目を追記

---

## 全戦略マッピング分析 (2026-04-16 追記)

### 発見: EXEMPT漏れが大量存在

QH BEV = **54.1%**。BT WR > 54.1% でQH適用 = TP利益を不当に削っている。

| Strategy | Pair | Tier | BT WR | QH状態 | BEV超過 | EV損失推定 |
|---|---|---|---|---|---|---|
| post_news_vol | GBP_USD | PAIR_P | **88.5%** | ✅ QH適用 | +34.4pp | **~-0.310/trade** |
| orb_trap | USD_JPY | PAIR_P | **84.2%** | ✅ QH適用 | +30.1pp | **~-0.152/trade** |
| trendline_sweep | EUR_USD | **ELITE** | **80.8%** | ✅ QH適用 | +26.7pp | **~-0.163/trade** |
| dt_fib_reversal | EUR_USD | PAIR_P | **80.0%** | ✅ QH適用 | +25.9pp | ~-0.072/trade |
| doji_breakout | GBP_USD | PAIR_P | **78.3%** | ✅ QH適用 | +24.2pp | ~-0.127/trade |
| session_time_bias | USD_JPY | ELITE | 79.0% | ❌ EXEMPT | — | — |
| gbp_deep_pullback | GBP_USD | ELITE | 75.3% | ❌ EXEMPT | — | — |
| dt_fib_reversal | GBP_USD | PAIR_P | **76.2%** | ✅ QH適用 | +22.1pp | ~-0.066/trade |
| squeeze_release_momentum | EUR_USD | PAIR_P | **73.3%** | ✅ QH適用 | +19.2pp | ~-0.115/trade |
| trendline_sweep | GBP_USD | ELITE | **73.1%** | ✅ QH適用 | +19.0pp | ~-0.105/trade |
| orb_trap | EUR_USD | PAIR_P | **71.4%** | ✅ QH適用 | +17.3pp | ~-0.085/trade |
| post_news_vol | EUR_USD | PAIR_P | **71.4%** | ✅ QH適用 | +17.3pp | ~-0.144/trade |
| session_time_bias | EUR_USD | ELITE | 69.6% | ❌ EXEMPT | — | — |
| vix_carry_unwind | USD_JPY | PAIR_P | 69.9% | ❌ EXEMPT | — | — |
| xs_momentum | EUR_USD | PAIR_P | **68.0%** | ✅ QH適用 | +13.9pp | ~-0.040/trade |
| session_time_bias | GBP_USD | ELITE | 67.1% | ❌ EXEMPT | — | — |
| london_fix_reversal | EUR_USD | PAIR_P | **66.7%** | ✅ QH適用 | +12.6pp | ~-0.028/trade |
| london_fix_reversal | GBP_USD | PAIR_P | 56.8% | ❌ EXEMPT | — | ← 56.8%なのにEXEMPT (不整合) |
| orb_trap | GBP_USD | PAIR_P | **64.3%** | ✅ QH適用 | +10.2pp | ~-0.043/trade |
| doji_breakout | USD_JPY | PAIR_P | **61.9%** | ✅ QH適用 | +7.8pp | ~-0.059/trade |
| vwap_mean_reversion | EUR_JPY | PAIR_P | 56.5% | ✅ QH適用 | +2.4pp | ~-0.143/trade |
| vwap_mean_reversion | GBP_JPY | PAIR_P | 53.6% | ✅ QH適用 | -0.5pp | QH微効果あり |
| dt_fib_reversal | EUR_JPY | PAIR_P | 54.3% | ✅ QH適用 | +0.2pp | ほぼ中立 |

### 集計
| 区分 | 件数 |
|---|---|
| 昇格中の全戦略ペア | 38 |
| QH適用 | 28 |
| EXEMPT | 6 |
| RANGE_MR bypass | 4 |
| **BT WR > 54.1% でQH適用中（EXEMPT漏れ）** | **16** |
| BT WR > 70% でQH適用中 | **10** |

### 重大不整合: EXEMPTの選定基準が一貫していない

| 現状EXEMPT | BT WR | 理由 |
|---|---|---|
| london_fix_reversal GBP_USD | 56.8% | 高WR戦略 |
| session_time_bias GBP_USD | 67.1% | 高WR戦略 |

| EXEMPT漏れ（高WR） | BT WR | 問題 |
|---|---|---|
| **trendline_sweep EUR_USD** | **80.8%** | ELITE_LIVEなのにQH適用！ |
| **post_news_vol GBP_USD** | **88.5%** | 最高WRなのにQH適用！ |
| **orb_trap USD_JPY** | **84.2%** | BT No.1 EVなのにQH適用 |

→ **EXEMPTの実効閾値は存在せず、個別判断の見落とし多数**

### EXEMPT追加候補 (BT WR ≥ 70% 基準)

BT N≥30 かつ WR≥70% で QH適用中の戦略を EXEMPT に追加すべき:

| Strategy | Pair | BT WR | BT EV | 追加理由 |
|---|---|---|---|---|
| post_news_vol | GBP_USD | 88.5% | +1.762 | 最大EV損失、最高WR |
| orb_trap | USD_JPY | 84.2% | +0.866 | EV最優秀戦略 |
| trendline_sweep | EUR_USD | 80.8% | +0.927 | ELITE_LIVEなのに未EXEMPT |
| dt_fib_reversal | EUR_USD | 80.0% | +0.407 | 80%超WR |
| doji_breakout | GBP_USD | 78.3% | +0.724 | 高WR高EV |
| trendline_sweep | GBP_USD | 73.1% | +0.599 | ELITE_LIVEなのに未EXEMPT |
| orb_trap | EUR_USD | 71.4% | +0.482 | orb_trap他ペアと一貫性 |
| post_news_vol | EUR_USD | 71.4% | +0.817 | 高EV |
| squeeze_release_momentum | EUR_USD | 73.3% | +0.656 | 高WR |

注: BT EV はすでにQH反映済み（BT friction v3）→ EXEMPT化すれば実際のLive EVはさらに向上

### 実装判断

**CLAUDE.md 判断プロトコル適用**:
- EXEMPT追加 = パラメータ変更カテゴリ
- ただし BT N≥30 + WR≥70% の数理的根拠あり
- trendline_sweep/ELITE_LIVE が未EXEMPTは設計意図のバグ相当

→ **ユーザー確認後に実装推奨**

---

## Related
- [[system-reference]] — 全パラメータ一覧
- [[friction-analysis]] — BT v3摩擦モデル (QH反映済み)
- [[bt-live-divergence]] — 6つの構造的楽観バイアス
- [[auto-improvement-pipeline]] — Pattern 3: QH効かない戦略の自動検知
- [[changelog]] v6.4, v6.5, v6.8 の QH 関連変更履歴
