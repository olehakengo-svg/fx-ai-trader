# Academic Cross-Audit: All Strategies x All Pairs (2026-04-12)
**3 parallel agents, all-language search (EN/JP/DE/FR/CN/KR), ~50 papers referenced**

## CRITICAL FINDINGS (Action Required)

### 1. bb_rsi_reversionのエッジが消失している可能性
- **EdgeToolsの1,500万パラメータ検証**: RSI overbought/oversold戦略のBonferroni補正後の有意なエッジ = **ゼロ**
- **Fang et al (2014)**: BBの予測力は「2001年以降ほぼ消失」
- **本番データ**: Post-cutoff WR=36.4% → ランダム(50%)との検定 **p=0.417（有意でない）**
- **BT→本番劣化**: WR=61.3% → 54.7% → 36.4% = 時間とともに一貫して劣化 = alpha decay
- **結論**: bb_rsiは世界で最もクラウディングされたリテール戦略。edge=0.45pip/tradeは統計的ノイズの可能性大

### 2. 53戦略/55日間は多重検定で偽陽性だらけ
- **Bailey et al (2014)**: 53戦略×α=0.05 → 期待偽陽性 = 2.65件
- 本番PF>1は**1戦略のみ** — 残り52は全て偽陽性（BT過適合）の可能性
- **Harvey et al (2016)**: t>3.0が必要（現行binomial_test α=0.10は53倍甘い）
- Deflated Sharpe Ratio (DSR) 未実装 → BT結果の信頼性が根本的に担保されていない

### 3. 五十日アノマリーの効果逓減
- **茨城大学鈴木研究室**: 五十日WRが2023-2024年データで**44%に低下**（PF: 2.23→1.27）
- アノマリー認知の普及で効果が逓減中

### 4. GBPフラッシュクラッシュのテールリスク
- 2016年10月: GBP/USDが9%暴落（アジア早朝）
- 2022年9月: GBP/USDが4.5%急落（アジア早朝）
- **全GBP戦略にアジアセッション除外フィルター必須**

## STRATEGY-BY-STRATEGY ACADEMIC VERDICT

### 学術的に最も強固（Journal of Finance / JFE / NBER level）
| Strategy | Paper | Confidence | Issue |
|----------|-------|-----------|-------|
| **session_time_bias (EUR)** | Breedon & Ranaldo 2013, Krohn 2024, Ranaldo 2009 | ★★★★★ | WR=87.5%は過学習リスク（N小） |
| **london_fix_reversal (GBP)** | Krohn 2024, Melvin & Prins 2015 | ★★★★★ | WR=100%は統計的に無意味（N小）。2015改革後も効果継続 |
| **vix_carry_unwind** | Brunnermeier 2009, IMF 2019 | ★★★★★ | 低頻度（年2-5回） |
| **xs_momentum** | Menkhoff 2012 (JFE), Eriksen 2019 | ★★★★ | 取引コスト後のリターン大幅低下 |

### 学術的に問題あり
| Strategy | Issue | Confidence |
|----------|-------|-----------|
| **bb_rsi_reversion** | Fang 2014: BB予測力消失。EdgeTools: RSI有意エッジゼロ。クラウディング最大 | ★★ |
| **fib_reversal** | Fibonacci比率の学術的根拠なし。自己成就預言のみ | ★★ |
| **gotobi_fix** | 効果逓減（WR 2023-24: 44%）。認知普及で逓減中 | ★★★ |
| **macdh_reversal** | arXiv 2022: MACDがB&Hを上回る証拠なし | ★ |
| **orb_trap** | 査読論文による実証研究なし（概念的に合理的だが） | ★★★ |

### session_time_bias GBP_USDで微負の学術的説明
- Ranaldo (2009): 「GBPを除く」通貨が自国セッションで減価 → GBPは例外
- GBPはロンドン市場の「ホーム通貨」→ セッションバイアスが相殺される

## STRUCTURAL RISKS (Cross-Cutting)

| Risk | Severity | Finding |
|------|----------|---------|
| **過適合** | CRITICAL | 53戦略/55日、DSR未実装、WF 3窓のみ |
| **クラウディング** | CRITICAL | bb_rsi=世界最普及リテール戦略、edge≈noise |
| **擬似分散化** | HIGH | 53戦略≒5-8独立エッジ、同時に同方向で負ける |
| **コスト過小** | HIGH | 定数フリクション、edge/friction=21% |
| **レジーム依存** | HIGH | RANGE 43% vs TREND 34%、MR戦略の構造的脆弱性 |
| **ブローカー執行** | MOD-HIGH | SLスリッページ非対称、Last Lookリスク |

## RECOMMENDED ACTIONS

### Immediate (今週)
1. **DSR (Deflated Sharpe Ratio) をstats_utils.pyに実装** — N_trials=53で全BT結果を補正
2. **bb_rsiのalpha decay監視を強化** — WR=36.4%がさらに低下していないか週次チェック
3. **GBP戦略にアジアセッション除外フィルター追加** — フラッシュクラッシュ対策
4. **session_time_biasをGBP_USDから除外** — 学術的にGBPは例外ペア

### Short-term (2週間)
5. **戦略数を53→10以下に削減** — 独立エッジが5-8しかないなら53は管理不能
6. **BT期間を55日→120日以上に延長** — 統計的信頼性の基盤確保
7. **条件付きフリクションモデルの実装** — セッション×ボラ条件でスリッページ可変

### Medium-term (1ヶ月)
8. **マイクロストラクチャー系エッジに注力** — liquidity_sweep, london_fix_reversal, session_time_bias(EUR)
9. **HMMレジームオーバーレイの本格検証** — defensive lot multiplier改善
10. **Combinatorial Purged Cross-Validation (CPCV)の実装** — WFOの強化

## Related
- [[lessons/index]] — 過去の間違いと教訓
- [[edge-pipeline]] — 6段階パイプライン
- [[changelog]] — データ基準日タイムライン
- [[friction-analysis]] — ペア別摩擦
- [[independent-audit-2026-04-10]] — 前回の独立監査
