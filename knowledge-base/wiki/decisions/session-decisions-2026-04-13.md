# Session Decisions: 2026-04-13

**Session**: [[sessions/2026-04-13-session]]
**Context**: v8.9 EV Decomposition + Alpha Scan + N蓄積ボトルネック解消
**Total decisions**: 8

---

## Decision 1: bb_rsi x USD_JPY PAIR_DEMOTED

**What was decided**: bb_rsi戦略のUSD_JPYペアをPAIR_PROMOTED → PAIR_DEMOTEDに降格。USD_JPYでのbb_rsi実弾トレードを停止し、shadow記録のみ継続。

**Quantitative evidence**:
| Metric | Value |
|--------|-------|
| N | 76 |
| WR | 38.2% |
| EV | -0.28 pip/trade |
| Kelly | -5.5% |
| BT時EV (USD_JPY) | -0.522 |

**Source**: Phase 19 EV分解 (Post-cutoff, FX-only, N=294全体分析)。損失ワースト8戦略xペアが全損失の83%を生産しており、bb_rsi x USD_JPYはその一角。

**Rationale**: N=76は統計的に十分なサンプルサイズ。Kelly=-5.5%はベットすべきでないことを明確に示す。BT時点で既にEV=-0.522と負であり、本番データがBTの予測を追認。独立監査(2026-04-10)では「bb_rsi保護最優先」だったが、それはUSD_JPYが唯一の正EVだった時点の判断。N=76でEV負が確定した以上、保護する根拠が消失。

**Reversible**: Yes。PAIR_DEMOTEDはshadow記録を継続するため、将来的にEVが反転すれば復帰可能。EUR_USD(EV=+0.943)への焦点移行が未解決事項として残存。

**Success criteria**:
- 短期: USD_JPYでの実弾損失がゼロになる
- 中期: bb_rsi x EUR_USDがN=30到達時にEV>0を維持すればfocus shiftが正当化される
- 判定時期: 2-3週間後(EUR_USD N=30到達時)

---

## Decision 2: stoch_trend_pullback FORCE_DEMOTED

**What was decided**: stoch_trend_pullbackをUNIVERSAL_SENTINEL → FORCE_DEMOTEDに降格。全ペアで実弾停止、shadowのみ。

**Quantitative evidence**:
| Metric | Value |
|--------|-------|
| N | 19 |
| WR | 31.6% |
| EV | -0.97 pip/trade |

**Source**: Phase 19 EV分解。損失ワースト8戦略のうちの1つとして特定。

**Rationale**: N=19はFORCE_DEMOTION判断には十分(閾値N>=10)。WR=31.6%はBEV_WR(break-even win rate)を大きく下回り、EV=-0.97は1トレードあたり約1pip喪失を意味する。UNIVERSAL_SENTINELのまま放置すると、N蓄積のために実弾損失が継続する。

**Reversible**: Yes。FORCE_DEMOTEDはshadow記録を継続。N=50到達時にEVが正に転じれば復帰可能。

**Success criteria**:
- 実弾損失の即時停止(0 pip/trade)
- Shadow N=50到達時にEV再評価 → 負のままなら判断正当化

---

## Decision 3: dt_bb_rsi_mr FORCE_DEMOTED

**What was decided**: dt_bb_rsi_mrをUNIVERSAL_SENTINEL → FORCE_DEMOTEDに降格。全ペアで実弾停止、shadowのみ。

**Quantitative evidence**:
| Metric | Value |
|--------|-------|
| N | 7 |
| WR | 14.3% |
| EV | -4.09 pip/trade |

**Source**: Phase 19 EV分解。

**Rationale**: N=7は通常の判断基準(N>=30)には不足だが、WR=14.3%(7回中6回LOSS)とEV=-4.09(1トレードあたり4pip以上喪失)は極端に悪い。N不足での判断リスクより、4pip/tradeの出血を止める緊急性が上回る。Alpha Scanでも dt_bb_rsi_mr x USD_JPYは N=5でEV=+3.08だったが、これは外れ値1件に依存しており、全体N=7と合わせると信頼性なし。

**Reversible**: Yes。Shadow継続。N=30到達時に再評価。

**Success criteria**:
- 実弾損失の即時停止
- Shadow N=30到達で再評価 → WR>BEV_WRかつEV>0なら復帰検討

---

## Decision 4: Shadow slot bypass (全戦略がshadowで発火可能に)

**What was decided**: スロット制限(max_per_mode_pair, hedge_block, max_open)を超過した場合でも、全戦略がshadow tradeとして発火できるようにバイパスを実装。Shadow tradesはスロットカウントから除外。max_openにshadow用別上限(+8)を追加。

**Quantitative evidence**:
| Metric | Value | 問題 |
|--------|-------|------|
| session_time_bias発火数 | 0回 | ポジションブロック(max_per_mode_pair=1)が原因 |
| 既存ポジション占有率 | 高 | 新戦略がスロット確保不能 |

**Source**: Phase 19 分析。session_time_bias(学術★★★★★、BT WR=69-77%)が一度もlive発火していない根本原因がスロット枯渇と判明。

**Rationale**: 新戦略のN蓄積は月利100%目標達成の前提条件。スロット制限は実弾リスク管理のために存在するが、shadow tradesはエクイティに影響しないため、スロット制限を適用する必要がない。Shadow用の別上限(+8)でDB肥大化を防止しつつ、データ蓄積を最大化。

**Reversible**: Yes。config変更のみ。`_is_slot_shadow_eligible` フラグで制御。

**Success criteria**:
- session_time_bias / london_fix_reversalのshadow発火確認(deploy後)
- Shadow N蓄積速度が改善(現在0 → 期待値: 数件/日)
- 実弾トレードのスロット管理が引き続き正常に機能

---

## Decision 5: Equity Reset v89b (shadow exclusion付き再リセット)

**What was decided**: v8.9 Equity Resetを再実行(v89b)。今回はis_shadow=0バグで汚染されたshadow tradesを除外してeq_peak/eq_currentを再計算。

**Quantitative evidence**:
| Metric | Before v89b | After v89b |
|--------|-------------|------------|
| DD | 12.39% (is_shadow=0バグ汚染込み) | クリーンデータで再計算 |
| lot_mult | 0.2x (防御モード) | 1.0x (フルロット) → 目標 |

- **is_shadow=0バグ**: FORCE_DEMOTED戦略がis_shadow=0でDB記録されていた → shadow損失がeq計算に混入 → DDが実態より大幅に悪化
- 初回v89: DD 2,899pip(289.9%) → 8.4pip(0.8%) → lot_mult=1.0x
- バグ汚染後: DD=12.39% → lot_mult=0.2x (実弾ロットが1/5に制限)

**Source**: Phase 19 DD防御0.4x原因調査 + Phase 20 is_shadow=0バグ発見(commit ab0489d)。

**Rationale**: is_shadow=0バグにより、本来shadow(非実弾)であるべきトレードがeq計算に混入し、DDが不当に悪化。lot_mult=0.2xは月利目標の達成を不可能にする。バグ修正(is_shadow強制True化) + Equity Re-resetにより、クリーンデータのみでDD/lot_multを再計算。

**Reversible**: Yes。eq_reset_v89bフラグで1回のみ実行。必要なら再度リセットフラグを設定可能。

**Success criteria**:
- lot_mult=1.0x復帰(deploy後に確認)
- DD防御の自動安全弁(2%→0.8x等)が正常機能を維持
- 以降のeq計算にshadow tradeが混入しない(is_shadow=True強制が機能)

---

## Decision 6: session_time_bias / london_fix_reversal スコア 4.0 → 5.5

**What was decided**: session_time_biasとlondon_fix_reversalのbase scoreを4.0から5.5に引き上げ。同時にSENTINEL矛盾(UNIVERSAL_SENTINELがscore要件を満たさず発火不能だった問題)を修正。

**Quantitative evidence**:
| Metric | Value |
|--------|-------|
| BT WR (session_time_bias) | 69-77% |
| 学術根拠 | ★★★★★ |
| Live発火数 | 0回 (スコア不足 + SENTINEL矛盾) |

**Source**: Phase 20 N蓄積ボトルネック解消 (commit 4011b94)。

**Rationale**: score=4.0ではUNIVERSAL_SENTINELの閾値要件を満たせず、戦略が一度もlive発火しない矛盾状態が発生していた。学術根拠★★★★★(学術研究で強く支持)かつBT WR=69-77%の戦略がN=0のまま放置されるのは、N蓄積フェーズの目標に反する。score=5.5はSENTINEL閾値を超え、かつ他のTier1戦略と同等のスコア水準。

**Reversible**: Yes。config変更のみ。score値を戻すだけで元に戻せる。

**Success criteria**:
- session_time_bias x EUR/JPYの初回live発火確認
- london_fix_reversal x GBP_USDの初回live発火確認(UTC 15:45-17:00)
- N蓄積開始(目標: 1-2週間でN>=10)

---

## Decision 7: EUR_USD SELL ブロック

**What was decided**: EUR_USDペアでのSELL方向トレードを全面ブロック。BUYのみ許可し、SELLはshadow化。

**Quantitative evidence**:
| Metric | Value |
|--------|-------|
| N | 43 |
| WR | 11.6% |
| EV | -2.714 pip/trade |
| PnL合計 | -116.7 pip |

Alpha Scan毒性テーブルより:
- EUR_USD SELLは2番目に大きな毒性源(1位はRANGE SELL: -145.6pip)
- 43トレード中わずか5勝(WR=11.6%)
- 止めるだけで+116.7pip回復見込み

**Source**: Phase 21 Alpha Scan (commit b296d19) + /api/demo/factors 多次元ファクター分解。

**Rationale**: N=43は十分なサンプルサイズ。WR=11.6%は異常に低く(ランダムの50%を大幅に下回る)、構造的な問題を示唆。EV=-2.714は全因子セル中で最悪クラス。BT検証不要の「止めるだけで効く」即時アクション。SELLをshadow化することでデータ蓄積は継続。

**Reversible**: Yes。ブロック解除はconfig変更のみ。Shadow記録が継続するため、将来EVが改善すれば復帰可能。

**Success criteria**:
- EUR_USD SELLの実弾損失がゼロになる(即時効果)
- 全体PnLの改善: -116.7pipの出血が止まる
- Shadow N蓄積で構造変化の有無を監視(3ヶ月後にEV再評価)

---

## Decision 8: RANGE SELL 制限 (conf >= 65)

**What was decided**: レジームがRANGEの時のSELL方向トレードを制限。confidence >= 65の高信頼シグナルのみ通過させ、低confidenceのRANGE SELLをブロック。

**Quantitative evidence**:
| Metric | Value |
|--------|-------|
| N | 89 |
| WR | 27.0% |
| EV | -1.636 pip/trade |
| PnL合計 | -145.6 pip |

対比: SELL x TREND_BULL は N=44 EV=+0.595 PnL=+26.2(正EV) → SELLが一律に悪いのではなく、RANGE環境でのSELLが特異的に毒性。

**Source**: Phase 21 Alpha Scan + /api/demo/factors。RANGE x SELLが全因子中の最大毒性源(PnL=-145.6pip)として特定。

**Rationale**: N=89は高い統計的信頼度。全面ブロックではなくconf>=65の閾値フィルタを採用した理由は、高confidence時にはエッジが残存する可能性があるため。Decision 7(EUR_USD SELL全面ブロック)とは異なり、こちらは条件付き許可の設計。Alpha ScanでSELL x TREND_BULLが正EVだったことから、SELL自体の問題ではなくRANGEレジーム+SELLの組合せが毒性であることが明確。

**Reversible**: Yes。conf閾値の変更またはフィルタ解除で即座に元に戻せる。

**Success criteria**:
- RANGE SELL低confの実弾損失停止
- conf>=65のRANGE SELLがEV>0を維持(閾値の妥当性確認)
- 全体PnLの改善: -145.6pipの大部分が回復
- 判定時期: 4週間後(低conf SELL shadow N>=30蓄積時にconf閾値を検証)

---

## Summary Table

| # | Decision | Type | N | EV | 即時効果 | Reversible |
|---|----------|------|---|-----|---------|------------|
| 1 | bb_rsi x USD_JPY PAIR_DEMOTED | 戦略降格 | 76 | -0.28 | 損失停止 | Yes |
| 2 | stoch_trend_pullback FORCE_DEMOTED | 戦略降格 | 19 | -0.97 | 損失停止 | Yes |
| 3 | dt_bb_rsi_mr FORCE_DEMOTED | 戦略降格 | 7 | -4.09 | 損失停止 | Yes |
| 4 | Shadow slot bypass | アーキテクチャ | - | - | N蓄積加速 | Yes |
| 5 | Equity Reset v89b | リスクポリシー | - | - | lot_mult復帰 | Yes |
| 6 | Score 4.0→5.5 | パラメータ | - | - | 発火解禁 | Yes |
| 7 | EUR_USD SELL block | アルファフィルタ | 43 | -2.714 | +116.7pip | Yes |
| 8 | RANGE SELL restriction | アルファフィルタ | 89 | -1.636 | +145.6pip | Yes |

## Related
- [[sessions/2026-04-13-session]] — 本セッション全体ログ
- [[independent-audit-2026-04-10]] — bb_rsi保護最優先の判断(Decision 1で覆された前提)
- [[edge-pipeline]] — 戦略Stage管理
- [[alpha-scan-2026-04-13]] — Decision 7, 8の根拠データ
- [[lessons/index]] — 関連教訓
