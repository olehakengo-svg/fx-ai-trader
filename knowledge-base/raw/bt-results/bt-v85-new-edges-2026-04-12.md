# BT Results: v8.5 New Edge Strategies (2026-04-12)
**BT Mode**: DT (daytrade), USD_JPY, 55 days, 15m, friction model v2
**Total**: 274 trades, WR=60.2%, PF=1.02, Sharpe=0.151, EV=+0.018 ATR

## New Strategies (v8.5) Results

| Strategy | WR | EV(ATR) | PnL(ATR) | Verdict |
|----------|-----|---------|----------|---------|
| **vix_carry_unwind** | **100%** | **+2.222** | **+13.33** | **★★★★★ BT最高EV** |
| **session_time_bias** | **66.7%** | **+0.143** | **+2.14** | **★★★ 正EV確認** |
| xs_momentum | 58.3% | -0.133 | -12.74 | ★★ 負EV（パラメータ調整要） |
| london_fix_reversal | 33.3% | -0.569 | -1.71 | ★ 負EV（要調査） |
| gotobi_fix | 0.0% | -2.692 | -2.69 | ✗ 負EV（USD_JPY BT期間にgotobi少ない？） |
| hmm_regime_filter | N/A | N/A | N/A | 防御オーバーレイ（トレード生成なし） |

## Comparison with Existing Strategies (same BT)

| Strategy | WR | EV(ATR) | Status |
|----------|-----|---------|--------|
| tokyo_nakane_momentum | 100% | +1.719 | Existing (N小) |
| orb_trap | 100% | +1.443 | PAIR_PROMOTED |
| dual_sr_bounce | 76.0% | +0.703 | FORCE_DEMOTED |
| sr_break_retest | 80.0% | +0.512 | FORCE_DEMOTED |
| htf_false_breakout | 60.0% | +0.317 | Sentinel |
| dt_bb_rsi_mr | 64.2% | +0.156 | Sentinel |
| **session_time_bias** | **66.7%** | **+0.143** | **NEW — EV positive** |
| dt_sr_channel_reversal | 60.0% | +0.115 | Sentinel |

## Key Findings

1. **vix_carry_unwind**: BT EV=+2.222は全戦略中最高だが100% WR（N小）は過学習のリスク。
   低頻度イベント(55日で数回)のため統計的確信は低い。

2. **session_time_bias**: EV=+0.143は控えめだが安定的な正のエッジ。WR=66.7%は
   BEV_WR=34.4%を大幅に上回る。摩擦耐性は十分。**最も堅実な新エッジ。**

3. **xs_momentum**: EV=-0.133は負。USD_JPY単体ではモメンタムが機能しにくい可能性。
   クロスセクション（複数ペア比較）が本来の設計意図だが、単一ペアBTでは限界。

4. **london_fix_reversal**: WR=33.3%は低い。Fix効果がUSD_JPYで弱い可能性（EUR/USDの方が顕著）。
   EUR_USD BTが必要だがRenderのBTが単一ペア制約。

5. **gotobi_fix**: WR=0%は55日BTに五十日が少なすぎることが原因の可能性。
   カレンダーイベントなので長期BT（120日+）が必要。

## BT Limitations
- USD_JPY単体のみ（EUR/USD, GBP/USDのBTはRenderタイムアウトで実行不可）
- 55日間（約2.5ヶ月）のデータ
- gotobi_fix: 55日間に五十日は約10回のみ、さらに月金除外
- vix_carry_unwind: 低頻度イベントは55日では統計的に不十分

## Related
- [[edge-pipeline]] — 評価パイプライン
- [[session-time-bias]] / [[london-fix-reversal]] / [[gotobi-fix]] — テスト対象エッジ
- [[vix-carry-unwind]] / [[xs-momentum-dispersion]] / [[hmm-regime-overlay]]
- [[friction-analysis]] — 摩擦モデル
