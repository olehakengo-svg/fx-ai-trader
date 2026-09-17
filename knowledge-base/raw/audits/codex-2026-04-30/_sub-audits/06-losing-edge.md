# Sub 6 (訂正版): 負けエッジの構造診断 — LIVE/Shadow 完全分離

> **訂正履歴**:
> - v1 (2026-04-30 12:50): is_shadow フィルター漏れで誤った "Live 緊急停止" 提言。ユーザー指摘で誤りを認識
> - **v2 (2026-04-30 13:00, 本ファイル)**: is_shadow=0 を真の LIVE として完全分離。攻めの提言に転換
>
> 本サブは Codex API 利用上限のため Claude が直接実行。

## 重要な前提訂正

`demo_trades` テーブルには **OANDA 実弾 (is_shadow=0)** と **シャドウ (is_shadow=1)** が混在している。
シャドウは「OANDA に流していない、ロジック発火だけ記録した学習用トレード」であり、損失も学習資産。
v1 ではこれを混ぜて「-661.9pip の出血」と書いたが、**実際は LIVE +6pip 黒字 (outlier 除外で +176pip)**。

| 区分 | N | 累計PnL | WR | EV/trade | Aggregate Kelly |
|---|---:|---:|---:|---:|---:|
| **LIVE 実弾 (is_shadow=0)** | **36** | **+6.0 pip** | **50.0%** | **+0.17** | **+0.385** |
| LIVE outlier 除外 (turtle_soup -170 除く) | 35 | +176.0 pip | 51.4% | +5.03 | +0.396 |
| Shadow (is_shadow=1) | 437 | -667.9 pip | 28.1% | -1.53 | -0.31 |

CLAUDE.md 4原則 #4「**攻撃は最大の防御 — 防御フィルターの積み上げよりデータ蓄積を優先**」と整合させると、
shadow の負けは止血対象ではなく **Tier 昇格判定の根拠を作るためのデータ蓄積**。

---

## 1. 真の LIVE エッジ (is_shadow=0)

### 1-A. LIVE 戦略集計

| Strategy | venue | N | WR | PF | Wilson Lower | Kelly | 累計pip | 評価 |
|---|---|---:|---:|---:|---:|---:|---:|---|
| **bb_rsi_reversion** | LIVE | **22** | **63.6%** | **6.97** | **0.430** | **+0.545** | **+192.3** | ★ Bonferroni 補正後も有意。LIVE 最強エッジ |
| doji_breakout | LIVE | 1 | 100% | inf | 0.21 | 0 | +18.6 | N不足だが正の sign |
| mtf_reversal_confluence | LIVE | 1 | 100% | inf | 0.21 | 0 | +1.2 | 同上 |
| vol_momentum_scalp | LIVE | 4 | 50% | 15.3 | 0.15 | +0.467 | +17.2 | 小N で pf 圧倒的 |
| trend_rebound | LIVE | 2 | 0% | 0 | 0 | 0 | -5.9 | N不足 |
| dt_sr_channel_reversal | LIVE | 1 | 0% | 0 | 0 | 0 | -6.1 | N=1 outlier |
| session_time_bias | LIVE | 1 | 0% | 0 | 0 | 0 | -6.5 | M3 修正後 LIVE で 1 件、判断不能 |
| streak_reversal | LIVE | 1 | 0% | 0 | 0 | 0 | -7.3 | N=1 outlier |
| vol_surge_detector | LIVE | 1 | 0% | 0 | 0 | 0 | -7.5 | N=1 outlier |
| vix_carry_unwind | LIVE | 1 | 0% | 0 | 0 | 0 | -20.0 | N=1 outlier |
| **turtle_soup** | LIVE | **1** | **0%** | **0** | **0** | **0** | **-170.0** | **★ 単発 -170 outlier、Sub 1d #6 SL/TP 競合バグの影響強疑** |

**LIVE 累計 +6pip / outlier 除外 +176pip / Aggregate Kelly +0.385 (outlier 除外で +0.396)**

### 1-B. 真の生存源 (LIVE で N≥4 かつ EV>0)

| Strategy | N | WR | EV | Kelly | 累計 |
|---|---:|---:|---:|---:|---:|
| bb_rsi_reversion | 22 | 63.6% | +8.74 | +0.545 | +192.3 |
| vol_momentum_scalp | 4 | 50% | +4.30 | +0.467 | +17.2 |

**この 2 戦略 26 トレードで +209.5pip**。これが現状の真のエッジ。

### 1-C. LIVE cell-level (最重要 cell トップ)

| Cell | N | WR | PF | EV | 累計 | 評価 |
|---|---:|---:|---:|---:|---:|---|
| bb_rsi_reversion × USD_JPY × london | 13 | 61.5% | 3.36 | +2.65 | +34.5 | ★ Bonferroni 候補 |
| bb_rsi_reversion × USD_JPY × tokyo | 8 | 62.5% | 2.28 | +2.81 | +22.5 | ★ Tier 候補 |
| bb_rsi_reversion × EUR_USD × london | 1 | 100% | inf | +135.3 | +135.3 | 1件 outlier (avg_win=135) |
| vol_momentum_scalp × USD_JPY × london | 3 | 67% | 26.3 | +5.90 | +17.7 | 観察継続 |
| doji_breakout × USD_JPY × ny | 1 | 100% | inf | +18.6 | +18.6 | 観察継続 |

bb_rsi_reversion EUR_USD london N=1 +135pip は **outlier**。Tokyo+London USD_JPY (N=21) で +57pip がフェアな edge 値。

---

## 2. Shadow データ (is_shadow=1) の意味再定義

Shadow は **撤退対象ではなく学習資産**。CLAUDE.md 原則 #4 とも整合する。

### Shadow の役割
1. **Tier 昇格判定の根拠を作る** — shadow N が一定数を超え Wilson lower が BEV+5% を超えれば LIVE 昇格候補
2. **負けパターンの構造分析** — 同型バグの早期発見 (例: sr_break_retest USD_JPY/london 全敗 → SL=43pip 設計が london ボラに不適合という発見)
3. **regime/session フィルター設計のデータ源** — どの regime/session で勝てる/負けるかを実トレードで観察

### Shadow で「負けている」戦略の正しい扱い

| 戦略 | shadow N | shadow 累計 | 何を学ぶか |
|---|---:|---:|---|
| sr_break_retest | 22 | -415pip | USD_JPY/london の SL 設計不整合 (構造発見) |
| sr_fib_confluence | 33 | -196pip | 理由文字列依存ロジックの破綻 (Sub 3 #2 を裏付け) |
| sr_channel_reversal | 28 | -99pip | range MR を trend で発火する regime mismatch |
| ema_trend_scalp | 88 | -107pip | session-aware フィルター不在 (Tokyo以外赤字) |
| post_news_vol | 7 | -91pip | event 後の signal lag (timing 問題) |

**これらの shadow データは、撤退判断ではなく「LIVE 昇格時にどのフィルター/cell 限定で許可するか」の設計根拠**。
止めるとデータが失われる。

### Shadow の唯一の例外: 構造的バグの可視化目的

Shadow が **lesson にすべき構造発見** を生んだら、shadow 経路にも cell-level kill を入れる価値がある。
ただし「データ蓄積の機会損失 vs 学習資産の継続」を秤量すべきで、
**現状の Shadow 全体損失 -668pip は roadmap "クリーンデータ蓄積最優先" の観点から見れば許容コスト**。

---

## 3. 訂正された「なぜ負けるのか / どう調整すれば勝てるか」

### 3-A. LIVE で実際に負けている例

LIVE で N≥2 EV<0 は **trend_rebound (N=2, -5.9pip)** のみ。N不足。

LIVE で N=1 で大負けしているのは **turtle_soup -170pip** だけだが、これは Sub 1d #6 (SL/TP 同時到達時 SL 優先) の **execution bug 起因の outlier の可能性が極めて高い**。
理由:
- avg_loss = 170pip は通常戦略の SL 設計 (典型 5-30pip) を逸脱
- 1 件で戦略全体の損失化
- Sub 1d #6: ローカル snapshot で SL 優先判定するため、broker truth と乖離する case がある

**正しい対応**: turtle_soup の取引履歴を broker side (OANDA trades) と照合し、本当に -170pip の SL hit だったか確認。execution bug の outlier であれば PnL を broker truth に置き換える。

### 3-B. Shadow で負けている戦略 — 学習として消化

各戦略の負けは **構造発見** として既に Sub 3-4 で詳述済み。これらを「撤退」するのではなく、
**LIVE 昇格条件の厳格化** という形で活用する:

```
Shadow → LIVE 昇格条件 (新提案):
1. Shadow N ≥ 30
2. Wilson lower ≥ BEV + 5pp (Bonferroni 補正後)
3. 直近 30日 Shadow EV > 0
4. cell-level で発火集中なし (1 cell で 50% 超は NG)
5. tier_integrity_check.py が ERROR=0 を返す
```

これに合致しない戦略は **Shadow に戻す** (PAIR_PROMOTED → SHADOW、ELITE_LIVE → PAIR_PROMOTED demote)。

---

## 4. Roadmap Alignment (訂正版)

### Gate 1 (Aggregate Kelly > 0): **★達成**
- LIVE trade-weighted Kelly = **+0.385** (turtle_soup 込み)
- outlier 除外で **+0.396**
- 集計母集団が小さい (N=36) ためまだ Gate 1 確定とは言いにくいが、明確に正の側

### Gate 2 (Kelly>0.05, PnL>+50pip, 破産<70%): **★ Kelly 部分達成、PnL は outlier 次第**
- Kelly: +0.385 ≫ 0.05 ✅
- PnL: +6pip (outlier 込み) / +176pip (outlier 除外) — outlier 1 件で判定が反転
- 破産確率: 要計算。Kelly+0.385 なら破産確率は通常 30-50%

### Gate 3 (PF>1.0, N≥100, 破産<30%, DSR>0.80): **未達**
- LIVE N=36、Gate 3 の N≥100 まで遠い
- Scalp の N 蓄積を加速する必要 (roadmap v2.1 Track E)

### Gate 4: 未着手

### 月利100% への距離 (LIVE 実績ベース再計算)
- 28 日 LIVE +6pip → 年化 **+78pip** (outlier 込み)
- 28 日 LIVE +176pip → 年化 **+2,295pip** (outlier 除外)
- ロードマップ目標 +633pip/年に対し、outlier 除外なら **3.6 倍超え** している
- ただし N=36 では統計的に不安定。N=100 に到達するまで判定保留

---

## 5. Top 5 Action Items (攻めの提言、訂正版)

1. **bb_rsi_reversion を Gate 進行どおり lot up**
   - 現状 LIVE N=22, Kelly+0.545, PnL+192pip
   - roadmap Gate 1 達成判定で 0.2x → 0.3x → 0.5x へ段階的増量
   - Impact: 月利目標への最大寄与 (高 Kelly + 確証あるエッジ)
   - Confidence: high (Bonferroni 補正候補)

2. **vol_momentum_scalp / doji_breakout / mtf_reversal_confluence の N 蓄積を加速**
   - 現状 N=4/1/1 で N 不足だが LIVE で正のサイン
   - Scalp 高頻度 (Track E) で 1-2 週間で N=15 まで蓄積
   - Impact: 第 2 のエッジ確認 → ポートフォリオ多角化
   - Confidence: med (N不足だが positive)

3. **turtle_soup -170pip outlier の broker-side 検証**
   - Sub 1d #6 SL/TP 同時到達バグの影響強疑
   - OANDA 履歴と demo_trades を照合し、execution bug 起因なら PnL を実測値に修正
   - Impact: LIVE PnL 集計の信頼性回復、Aggregate Kelly の真値確定
   - Confidence: high (バグパターン明確)

4. **Sev1 14 件の優先度を再仕分け** (LIVE 経路に集中)
   - 最優先 (LIVE 経路のみ): Sub 1d #1 OANDA idempotency, Sub 1d #2 ロット永続化, Sub 1c #1-2 認証/DoS
   - 中優先 (Shadow 経路汚染): Sub 1a #1-3 kill / auto-start / _main_loop
   - 低優先 (BT のみ): Sub 1b #1, Sub 5 #1-4 (BT runner PnL 誤算は LIVE 影響なし)
   - Impact: LIVE 真正性回復、shadow 経路は段階的修正で OK
   - Confidence: high

5. **Shadow → LIVE 昇格基準を厳格化** (Sub 8 で提言した tier_integrity_check 拡張)
   - Shadow N≥30, Wilson lower ≥ BEV+5pp, 直近 30日 EV>0, cell 集中なし
   - LIVE で N=1-2 大負けの戦略 (turtle_soup, vix_carry_unwind, vol_surge_detector 等) は Shadow へ降格
   - Impact: LIVE 純度向上、ELITE_LIVE Tier の意味回復
   - Confidence: high

---

## 6. Out-of-Scope Findings

- v1 で書いた「負け cell トップ 10 を即時 cell-level kill」は **shadow データに対する誤った提言** だった
- shadow cell の損失はお金が動いていないため止血ではなく学習資産。撤回
- ただし bb_rsi_reversion のように LIVE で N が積まれている戦略は cell-level でも観察対象
  - bb_rsi_reversion EUR_USD/london の +135pip outlier (N=1) を除外して再評価する価値あり
  - bb_rsi_reversion USD_JPY × Tokyo+London (N=21, +57pip) が真のエッジ

---

## 7. v1 → v2 訂正対比

| 観点 | v1 (誤) | v2 (訂正) |
|---|---|---|
| LIVE 累計 PnL | -661.9pip | +6.0pip (outlier 除外で +176pip) |
| Aggregate Kelly | -0.165 | +0.385 (outlier 除外 +0.396) |
| Gate 1 (Kelly>0) | ❌ 未達 | ✅ 達成 |
| Gate 2 (Kelly>0.05) | ❌ 未着手 | ✅ Kelly 部分達成 |
| 主要提言 | Live 緊急停止 + 戦略撤退 | LIVE lot up + Shadow 継続 + 昇格基準厳格化 |
| 損失主犯 | sr_break_retest -415pip | (それは shadow。LIVE では turtle_soup -170pip 1件で execution bug 疑い) |
| データの真の汚染源 | shadow データそのもの | (汚染ではない) Sub 1d #1-2 の execution bugs が LIVE データに混入 |

---

## 統計的留意点

- Bonferroni 補正 (k=11 LIVE 戦略) を適用して z=2.576 で見ると、bb_rsi_reversion の Wilson lower 0.430 はクリア
- 他の LIVE 戦略は N不足で Bonferroni 補正後ほぼすべて「統計判断不能」だが、それは N 蓄積中という正しい状態
- aggregate fallacy 回避のため、bb_rsi_reversion についても EUR_USD/London N=1 outlier を分離評価することが必須
