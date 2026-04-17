# 厳密エッジ分析 — 本番データ (2026-04-17)

**作成日**: 2026-04-17
**データ**: Render API `/api/demo/trades` N=1054 closed trades (2026-04-08 ~ 04-16, 9日間)
**手法**: Binomial test + Bonferroni + Benjamini-Hochberg FDR + Walk-forward stability
**基準**: `tools/bt_scanner.py` の判定流儀に準拠

---

> ## ⚠ CAVEAT: regime-unadjusted, provisional (追記 2026-04-17)
>
> 本文書の全 STRONG/MODERATE 判定は **regime-unadjusted の marginal estimate** に基づいており、本番で得られる期待 PnL を推定していない。
>
> 理論的背景: [[conditional-edge-estimand-2026-04-17]]
>
> - 現行推定量は暗黙に $\pi^{\text{sample}}(\text{regime})$ で重み付けされた期待値
> - サンプル期間 (9日, N=1054) は長期 regime 分布を代表していない可能性が極めて高い
> - 前セッションの SELL bias 発見 ([[sell-bias-root-cause-2026-04-17]]) がこの bias の実例
> - `tools/portfolio_balance.py` 実行結果より: RANGE × BUY のみ +0.86p / 他 5セルは全て負 — 強い regime 依存性を確認
>
> **本文書の判定を production 判断に直接使わないこと**。`regime_labeler` 実装後、conditional + reweighted な推定量で再評価予定。

---

## エグゼクティブ・サマリー

**本番データで厳密に分析した結果**:
1. **STRONG pocket (Bonf有意 + WF安定 + EV>0 + N≥30) = 0件**
2. **MODERATE pocket (FDR有意 + EV>0 + N≥30) = 1件** (tf=1m, Avg +0.08p で実質的に flat)
3. **Bonf有意な構造的敗者 = Live 8件, All 26件**
4. **全通貨ペアが Bonferroni 有意で負** (USD_JPY, EUR_USD, GBP_USD の全て)

**結論**:
**現在の本番ポートフォリオに統計的に検証可能な positive edge は存在しない。**
先の `demo_trades.db` ローカル分析 (N=115) で見つけた "fib_reversal ELITE, Tokyo session 勝ち"は **本番データで再現しなかった** → 誤認として撤回。

---

## REVISION: Regime-Aware Re-evaluation (2026-04-17 後刻追記)

`conditional-edge-estimand-2026-04-17` フレームワークに従い、**independent OANDA regime labeling + π_long_run reweighting** で再分析した結果:

### LIVE (N=326, regime-aware)

```
Total pockets: 31 | STRONG: 0 | MODERATE: 0 | Bonf-neg: 17
```

- **STRONG=0, MODERATE=0** — すべて WEAK に降格
- 主要因: 9日サンプルでは各セルで regime_support=FULL (全 regime で n≥30) を満たすのが極めて困難
- reweighted θ* が負のセルも複数 — marginal が正でも長期期待値は負

### `mode=scalp` 再評価 (主要 at-risk claim)

| 項目 | 値 |
|---|---|
| N | 152 |
| Marginal Avg | +0.24p |
| Marginal WR | 44% (BE-WR 61%) |
| **θ_reweighted** | **+0.47p ± 0.58** |
| regime_support | **INSUFFICIENT** (range n=2) |
| **新判定** | **WEAK** (forced) |

**Regime breakdown**:
| Regime (indep.) | n | avg |
|---|---|---|
| up_trend | 57 | +0.16p |
| down_trend | 36 | **+1.18p** |
| range | **2** | −1.80p |
| uncertain | 57 | −0.21p |

**解釈**:
- marginal +0.24p は主に **down_trend 36トレードの +1.18p** で引っ張られた結果
- up_trend (最もサンプル大) では +0.16p とほぼ flat
- range で n=2 のみ → regime_support INSUFFICIENT → **STRONG/MODERATE は原理的に不可**
- reweighted SE (0.58) > estimate (0.47) → **統計的に 0 と区別できない**
- **production 判断に mode=scalp を使わない**という方針が定量的に裏付けられた

### 構造的敗者 (17件) の regime 分解は別途実施予定

- 負の marginal が regime-specific な可能性 — reweighting で positive になる cell があれば demote 判断を見直す必要
- 現状は `regime-unadjusted` のまま; 戦略demote プロセスは regime 分解完了まで保留推奨

### Framework 検証状況

- ✅ `regime_labeler.py` 実装済み + 20 unit tests passing
- ✅ `RigorousAnalyzer` に regime conditioning 追加 + 10 unit tests passing
- ✅ π_long_run 実測 (H1, 3.2年, 4ペア) — §実測値 表
- ✅ `mode=scalp` STRONG claim を framework で反証

---

## データ詳細

| 項目 | 値 |
|---|---|
| 期間 | 2026-04-08 00:49 ~ 04-16 18:03 UTC (約9日間) |
| Total closed trades | 1054 (FX, XAU除外) |
| Live (OANDA送信) | 326 |
| Shadow | 728 |
| 固有戦略数 | 20+ |
| 通貨ペア | USD_JPY, EUR_USD, GBP_USD, EUR_JPY, GBP_JPY |

---

## Analysis 1: Live only (N=326)

### Positive pockets (エッジ候補)
| pocket | N | WR | BE-WR | Avg | PF | p-val | WF | Rec |
|---|---|---|---|---|---|---|---|---|
| tf=1m | 211 | 42% | 51% | +0.08p | 1.04 | 0.012 | **N** | MODERATE |
| mode=scalp | 152 | 44% | 51% | +0.24p | 1.14 | 0.114 | Y | WEAK |

tf=1m の MODERATE: FDR有意だが WF stable=N (時系列 3fold で不安定) → **実運用信頼不可**

### Structural Losers (Bonferroni有意の負セル、8件)
| pocket | N | WR | Avg | Total | p-val |
|---|---|---|---|---|---|
| GBP_USD | 23 | 13% | -4.02p | **-92.4p** | 3e-5 |
| daytrade_gbpusd | 11 | 0% | -7.27p | -80.0p | 1e-3 |
| NY session | 27 | 22% | -2.93p | -79.0p | 2e-4 |
| Monday (weekday 0) | 94 | 32% | -1.19p | **-112.3p** | 1e-8 |
| tf=5m | 82 | 26% | -1.15p | -94.4p | 4e-4 |
| **SELL direction** | 174 | 33% | -1.05p | **-183.3p** | 8e-8 |
| EUR_USD | 78 | 35% | -0.89p | -69.4p | 1e-3 |
| USD_JPY | 223 | 39% | -0.30p | -66.3p | 6e-4 |

**SELL direction が最大の負け** (-183p with N=174, p=8e-8) — 方向バイアスの可能性

---

## Analysis 2: All trades (Shadow + Live, N=1054)

### Positive pockets = **なし (MODERATE 以上)**

### Structural Losers = 26件
全通貨ペア・全セッション・全tf でBonf.有意な負が出現:

| 特に深刻 | N | Total loss | 解釈 |
|---|---|---|---|
| weekday 3 (木) | 360 | -621.3p | 最大損失曜日 |
| USD_JPY | 606 | -629.8p | 最大ペア |
| tf=15m | 239 | -614.1p | 構造的負け tf |
| SELL | 521 | -771.0p | Shadow含む全SELL |
| BUY | 533 | -562.4p | Shadow含む全BUY |
| sr_channel_reversal | 104 | -191.3p | 戦略単位で最大損失の一つ |

---

## Analysis 3: Cross-tab entry_type × instrument (Live only)

N≥20 の cell が **3件のみ** → サンプル不足で判断不能

---

## クオンツ的所見

### 1. 先の demo_trades.db 分析との乖離
| 前回主張 (demo_trades.db N=115) | 本番データでの検証 |
|---|---|
| fib_reversal は ELITE (WR 82%) | 本番 N 不足で未検証だが、他プロクシは負け |
| Tokyo session 勝ち (WR 67%) | **Shadow含む全体で Bonf有意に負け (-431p)** |
| GBP_USD 敗者 (-228p) | ✅ **再現** (Live N=23, Bonf有意) |
| London-NY overlap 負け | ✅ **再現** (Live N=27, Bonf有意) |
| tf=1m が勝ち | 本番 Live で MODERATE (Avg +0.08p) — ほぼflat |

**2勝3敗**: 私の分析は **半分が偶然の pattern** だった。

### 2. Selection / survivor bias の可能性
- Shadow 含む N=1054 で positive なし → **システム全体が 9日間 net loss**
- Live 326 trades は既にフィルターを通過したもの。それでも flat/負け
- BT では positive EV だった戦略が Live で機能していない可能性
- これは既知の lesson `bt-live-divergence.md` の再確認

### 3. 9日間の regime bias
- 9日 = 実質 1レジーム
- 次の月次 regime shift で結果が逆転する可能性
- 但し current regime で losing している事実は否定できない

### 4. Direction バイアスの警告
- SELL -771p vs BUY -562p (差 -209p)
- BUY/SELL 両方が負けているが、SELL が特に悪い
- レジーム依存か、signal bias か要調査

---

## Actionable Inference (判断プロトコル準拠)

CLAUDE.md 判断プロトコル:
- Live N≥30 データあり ✓
- 9日間 = 1レジームのみ ✗ → **複数レジーム跨ぐ検証が必要**
- Bonferroni有意な既存エッジ = 0

→ **実装判断 = 保留**。ただし、構造的敗者の一部は既に FORCE_DEMOTED 候補として検討に値する。

### 要検討 (アクション前に追加検証)
1. **GBP_USD の Live (N=23) を Shadow 格下げ** — 9日間で -92.4p, Bonf sig
   - 前提: 過去30日で再現するか、他 regime で違うかを確認
2. **SELL bias の原因調査** — signal 生成ロジックに系統的偏りがないか
3. **sr_channel_reversal (N=104 shadow含, -191p) の Force Demote** — 戦略単体で Bonf sig 負

### 実施すべきでない (現状)
- Live の全通貨ペア OANDA送信停止 → 過剰反応、regime 依存の可能性大
- Tokyo session 停止 → サンプル期間バイアスの可能性
- tf=1m 特別扱い → Avg +0.08p は誤差

---

## 次データ取得計画

### 短期 (今週)
- 毎日 `production_fetcher.fetch_closed_trades()` で最新取得
- 週末に再分析、結果安定性確認

### 中期 (1-2ヶ月)
- 30日+ データで regime 2-3種類を跨いだ再分析
- VIX regime / DXY direction 別の conditional analysis
- Walk-forward validation を 6-8 folds (週次) で厳密化

### 長期 (3ヶ月)
- 90日データで Bonferroni 有意な STRONG pocket が出現するか確認
- 出なければ **現戦略群全廃棄 + 新規探索** を検討

---

## 関連ファイル
- 分析スクリプト: `/tmp/run_rigorous.py`
- 結果ログ: `/tmp/rigorous_result.txt`
- フレームワーク: `research/edge_discovery/significance.py`, `rigorous_analyzer.py`
- データ取得: `research/edge_discovery/production_fetcher.py`

## 関連 lessons
- `lesson-bt-live-divergence.md` — BT と Live の乖離
- `lesson-reactive-changes.md` — サンプル不足での判断の危険
- `lesson-confidence-ic-zero.md` — 既存指標の予測力ゼロ問題
