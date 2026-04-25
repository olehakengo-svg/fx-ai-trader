# Phase 5 9次元エッジマトリクス: 戦場プロファイリング (2026-04-25, **LOCKED**)

> **Pre-reg LOCK 確定 (2026-04-25)** — data look 前. S1-S9 の通貨ペア & 時間帯
> プロファイリング, 検定 PAIR を物理的根拠で限定 (総当たり禁止).
> 詳細ロジック骨子: [[phase5-pure-edge-portfolio-2026-04-25]] (S1-S3) +
> [[phase5-extended-s4-s9-2026-04-25]] (S4-S9).

## 0. 設計原則

- **総当たり禁止**: 各戦略は **物理的に最適な PAIR (Top 2 まで)** で検定.
- **時間帯指定**: そのエッジが機能するセッションを物理的根拠で限定.
- **戦場の選択 = カーブフィッティング防止の主軸**: 全 PAIR × 全戦略の grid search
  はデータマイニングと等価で、Bonferroni 補正があっても n 数膨張で偽陽性が漏れる.

## 1. 9 戦略マトリクス (Logic × Pair × Session)

| # | 戦略 | カテゴリ | 第一原理 | Top1 PAIR | Top2 PAIR | 稼働セッション | 不稼働 |
|---|---|---|---|---|---|---|---|
| **S1** | Session Handover Stop Hunt | レンジ盾 | 流動性入替時の swing 抜きヒゲ reject | **GBP/USD** | **USD/JPY** | London open (06-08), Tokyo close (06-07), NY close (20-21) UTC | NY mid (15-19) |
| **S2** | Volatility Compression Breakout | トレンド剣 | Squeeze→Expansion エネルギー保存則 | **EUR/USD** | **GBP/JPY** | London-NY overlap (12-16 UTC) | Asia (00-05) |
| **S3** | Z-Score Exhaustion (mean revert) | カウンター | (BT REJECT 確定) — 順張り版は別 pre-reg 候補 | (DEAD) | (DEAD) | — | — |
| **S4** | Pure Divergence | カウンター | 価格 new HH/LL × RSI極限値減衰 = trend 終焉 | **GBP/USD** | **USD/JPY** | London-NY (08-20 UTC), trend 終盤 | Asia early |
| **S5** | VWAP / HTF Defense | トレンド剣 | 大口の VWAP/EMA 防衛線で買い支え | **EUR/USD** | **GBP/USD** | London (07-13), NY (13-20 UTC) | Tokyo (機関薄) |
| **S6** | Value Area Reversion | レンジ盾 | TPC 逸脱→POC 引力 (Volume Profile) | **EUR/USD** | **EUR/GBP** | Tokyo + Asia (00-07 UTC) | London open peak |
| **S7** | Opening Range Breakout | トレンド剣 | Macro 資金流入で Asia range 突破 | **GBP/USD** | **GBP/JPY** | London open (07-08), NY open (13-14 UTC) | session 中盤以降 |
| **S8** | Fair Value Gap (FVG) | カウンター | ICT/SMC 流動性 imbalance fill | **EUR/USD** | **GBP/USD** | London (07-13), NY (13-20 UTC) | Tokyo (低流動性で gap fill 機能薄) |
| **S9** | VSA Absorption | カウンター | 大口指値による吸収 (vol×3 + body×0.5) | **GBP/JPY** | **USD/JPY** | London open (07-09), Tokyo fix (00-01 UTC) | NY late (低 vol) |

---

## 2. 通貨ペア選定の第一原理

### EUR/USD (S2/S5/S6/S8 の Top1)
- **世界最深流動性** (日次 1.5T USD): Squeeze→Breakout (S2) のエネルギー保存則が
  クリーンに発動. FVG/VA Reversion (S6/S8) は機関の構造的 fill 動機が最強.
- 摩擦最小 (RT 1.6-2.0p): 低 RR (S6 RR 1.5) でも勝てる
- VWAP/HTF Defense (S5): 機関の長期建玉が VWAP/EMA50 (1H) で物理的 defense

### GBP/USD (S1/S4/S5/S7/S8 の Top1 or Top2)
- 中流動性 + 中ボラ: trend 形成と divergence (S4) が明確
- Cable 系で London 主導 = London open ORB (S7) が爆発的に動く
- Stop hunt (S1) が London open で頻発 (流動性入替で Asia レンジが壊される)

### GBP/JPY (S2/S7/S9 の Top1 or Top2)
- **高ボラ cross**: 大きく動くため Squeeze 後 expansion (S2) で高 RR 達成
- VSA absorption (S9): vol spike + 値幅縮小の異常検出ペアとして data 豊富
- ORB (S7): London/NY open で macro flow に最も rectimagrespond

### USD/JPY (S1/S4/S9 の Top2)
- Tokyo session 主軸: Tokyo close (S1), Tokyo fix (S9) のセッション特異性
- 中流動性: trend follow + divergence (S4) が機能

### EUR/GBP (S6 の Top2)
- 極狭 range + low vol: VA Reversion (S6) で偏在が頻繁発生
- ただし流動性薄で他戦略は不適

---

## 3. 時間帯選定の第一原理

| Session | UTC | 主要戦略 | 物理特性 |
|---|---|---|---|
| **Tokyo** | 00-06 | S6 (VA), S9 (Tokyo fix) | low vol, range 構造強 |
| **Tokyo close** | 06-07 | **S1** | 流動性入替で stop hunt |
| **London open** | 07-08 | **S1, S7, S9** | macro flow 注入, vol 急増 |
| **London** | 08-13 | S2, S5, S8 | trend 形成, defense, FVG |
| **London-NY overlap** | 12-16 | **S2, S5** | 最高流動性, expansion |
| **NY** | 13-20 | S5, S8, S4, S7 | trend 継続 / 終焉 |
| **NY close** | 20-21 | **S1** | 流動性枯渇 stop hunt |

## 4. 検定 PAIR グリッド (総当たり禁止)

各戦略の **Top 1 + Top 2 のみ**を BT 対象とする. それ以外の PAIR は data look 前に
**除外を pre-reg LOCK**.

| 戦略 | 検定 PAIR | 検定セッションフィルタ |
|---|---|---|
| S1 | GBP/USD, USD/JPY | UTC ∈ {6.0-7.5, 12.5-13.5, 20.5-21.5} |
| S2 | EUR/USD, GBP/JPY | UTC ∈ {12-16} |
| S4 | GBP/USD, USD/JPY | UTC ∈ {8-20} (Asia 除外) |
| **S5** | EUR/USD, GBP/USD | UTC ∈ {7-20} (Tokyo 除外) |
| S6 | EUR/USD, EUR/GBP | UTC ∈ {0-7} |
| **S7** | GBP/USD, GBP/JPY | UTC ∈ {7-9, 13-15} |
| **S8** | EUR/USD, GBP/USD | UTC ∈ {7-20} (Tokyo 除外) |
| S9 | GBP/JPY, USD/JPY | UTC ∈ {0-2, 7-9} |

→ 全 PAIR × 全 hour grid search (= 6 × 24 = 144 cell) ではなく、**最大 2 PAIR × 2-3 session = 4-6 cell** で検定.
   N 数稼ぎ目的の総当たりを防止.

---

## 5. 9 戦略の無相関性証明 (要約)

3 軸での直交性:

### 軸 1: Volatility Regime
| 局面 | 該当戦略 |
|---|---|
| **Squeeze (低 vol)** | S2 |
| **Range (中 vol)** | S1, S6 |
| **Expansion (高 vol)** | S5, S7 |
| **Extreme deviation** | S4 |
| **Discontinuity** | S8 (gap), S9 (absorption) |

→ **vol regime 5 つに完全分配** = 同時刻発火不可能.

### 軸 2: Time
| Session | 戦略 |
|---|---|
| Tokyo | S6, S9(Tokyo fix) |
| Tokyo close | S1 |
| London open | S1, S7, S9 |
| London-NY overlap | S2, S5 |
| NY | S4, S5, S8 |
| NY close | S1 |

→ S1 (handover) のみ複数 session 跨ぐが、各 session 内では他戦略と排他. 時刻条件
で event-level 直交.

### 軸 3: Trigger Type (binary)
| Trigger | 戦略 |
|---|---|
| 価格 swing 抜きヒゲ | S1 |
| BB width <10%ile | S2 |
| RSI 極限 + price div | S4 |
| EMA/VWAP touch + 反発 | S5 |
| Volume Profile 外縁 | S6 |
| Asia range break + vol×3 | S7 |
| 3-bar gap geometry | S8 |
| vol×3 + body×0.5 | S9 |

→ 8 種の独立 trigger geometry. 同時成立条件は数学的に不可能 (例: S2 BB 内 vs S6
VA 内は独立次元).

### Pair-level 直交補強
**通貨ペア指定**で更に直交性強化:
- S2 (EUR/USD) と S5 (EUR/USD) は時刻分離 (S2: London-NY overlap, S5: London 全体)
- S1 (GBP/USD) と S7 (GBP/USD) は同じ session window 重複ありだが trigger 異
  (S1: stop hunt wick, S7: range break body 大) → body size で排他

---

## 6. TAP 排除証明 (再確認)

| TAP | S1 | S2 | S4 | S5 | S6 | S7 | S8 | S9 |
|---|---|---|---|---|---|---|---|---|
| 1: 中間帯 RSI/BB%B | ❌ | ❌ | RSI ≤20/≥80 のみ | ❌ | ❌ | ❌ | ❌ | ❌ |
| 2: N-bar pattern | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 3-bar geometry のみ (= 定義) | ❌ |
| 3: 反転 candle 単独 | ヒゲ比率 (定量) | ❌ | ❌ | binary touch+reject | binary 内側回帰 | ❌ | gap 定義の一部 | ❌ |
| 4: 摩擦死 | RR≥1.2 | RR≥3.0 | RR≥2.0 | RR≥2.5 | RR≥2.0 | RR≥2.0 | RR≥2.0 | RR≥2.0 |
| 5: Score 膨張 | score=1.0 | score=1.0 | score=1.0 | score=1.0 | score=1.0 | score=1.0 | score=1.0 | score=1.0 |

**TAP-1 / TAP-5 完全排除**. 全戦略 confidence 固定値, ボーナス加算ゼロ.

---

## 7. 優先 Pre-Reg (有望 4 戦略, 通貨ペア限定)

### 7.1 S5 VWAP/HTF Defense (Pre-reg LOCKED)
**最有望理由**: 機関大口の物理仮説. ELITE_LIVE (gbp_deep_pullback) と同類で実証性高.

検定軸 (限定 grid, 12 cells):
- pair: **{EUR/USD, GBP/USD}** (2)
- pullback_min_atr: {1.5, 2.0} (2)
- defense_line: {VWAP, HTF_EMA50} (3)... actually {VWAP-only, EMA50-only, both} (3)

→ 2 × 2 × 3 = **12 cells**. α_cell = 0.05/12 = **0.00417**

SURVIVOR (AND): EV>+1.5p, PF>1.5, WR≥45%, N≥30, p<0.00417, WF 4/4

### 7.2 S7 Opening Range Breakout (Pre-reg LOCKED)
**最有望理由**: 時刻 + range + volume の 3 binary で false positive 極小.

検定軸 (限定 grid, 12 cells):
- pair: **{GBP/USD, GBP/JPY}** (2)
- volume_spike_ratio: {2.5, 3.0, 4.0} (3)
- session: {London_open, NY_open} (2)

→ 2 × 3 × 2 = **12 cells**. α_cell = 0.05/12 = **0.00417**

SURVIVOR (AND): EV>+2.0p, PF>1.5, WR≥40%, N≥20, p<0.00417, WF 4/4

### 7.3 S8 Fair Value Gap (Pre-reg LOCKED)
**最有望理由**: 純粋 geometry, ICT/SMC コミュニティで実証多数, TAP 排除完璧.

検定軸 (限定 grid, 12 cells):
- pair: **{EUR/USD, GBP/USD}** (2)
- gap_min_atr_mult: {0.3, 0.5, 0.7} (3)
- fill_pct: {full_fill, 50%_fill} (2)

→ 2 × 3 × 2 = **12 cells**. α_cell = 0.05/12 = **0.00417**

SURVIVOR (AND): EV>+1.5p, PF>1.5, WR≥45%, N≥30, p<0.00417, WF 4/4

### 7.4 S6 Value Area Reversion (Pre-reg LOCKED)
**選定理由**: 高勝率レンジ盾、S1 (handover) と排他で portfolio 補完.

検定軸 (限定 grid, 12 cells):
- pair: **{EUR/USD, EUR/GBP}** (2)
- vp_lookback_hours: {4, 6, 8} (3)
- va_percentile: {0.80, 0.85} (2)

→ 2 × 3 × 2 = **12 cells**. α_cell = 0.05/12 = **0.00417**

SURVIVOR (AND): EV>+1.0p, PF>1.5, WR≥55%, N≥40 (高勝率設計), p<0.00417, WF 4/4

### 7.5 第二波 (5/3 以降, 主軸 BT 結果次第)
- S4 Pure Divergence (GBP/USD, USD/JPY)
- S9 VSA Absorption (GBP/JPY, USD/JPY)

S3 mean revert は本日 BT REJECT 確定 → DEAD strategy として fib_reversal/macdh と
同様処理.

---

## 8. ポートフォリオ全体検定 (合計 BT セル数)

| 戦略 | Cells | 既存 BT |
|---|---|---|
| S1 (走行中) | 27 | ✅ 5pair 全 fetch (要 PAIR 限定 update 検討) |
| S2 (走行中) | 18 | 同上 |
| S3 (完了) | 12 | ALL_REJECT |
| **S5 (新)** | **12** | LOCK 済 |
| **S6 (新)** | **12** | LOCK 済 |
| **S7 (新)** | **12** | LOCK 済 |
| **S8 (新)** | **12** | LOCK 済 |
| 合計 | **105 cells** | (Bonferroni outer α=0.05/4 strategies = **0.0125** for 戦略単位採択) |

PAIR 限定により BT 時間も大幅短縮:
- 旧設計: 5 PAIR × 27 cells = 135 fetch (S1)
- 新設計: 2 PAIR × 12 cells = 24 fetch
- **約 5-6 倍短縮** → 12 cells × 4 戦略 = 48 fetch で 1-2h 完走想定

---

## 9. メモリ整合性

- [部分的クオンツの罠]: 全戦略 PF/Wlo/p_welch/WF/MAE_BREAKER 完備 ✅
- [ラベル実測主義]: BT 365日実測のみで判定 ✅
- [成功するまでやる]: REJECT でも secondary 副次仮説継続 ✅
- [XAU除外]: 全 BT で XAU 除外 ✅
- [Asymmetric Agility Rule 1]: 新エッジ主張 = LOCK + Bonferroni 完備 ✅
- **総当たり禁止**: 各戦略 Top 2 PAIR 限定で実装 ✅

## 10. 実装タイムライン (BT-First, PAIR 限定で軽量化)

| 日付 | アクション |
|---|---|
| 2026-04-25 (LOCK) | 9D matrix 確定 + 4 主軸 (S5/S6/S7/S8) Pre-reg LOCK |
| 2026-04-26〜28 | S5/S6/S7/S8 BT harness 実装 (PAIR 限定 grid) + 365日 BT |
| 2026-04-29〜30 | SURVIVOR 判定 |
| 2026-05-01〜 | S4/S9 第二波 Pre-reg + BT (主軸結果見て調整) |
| 2026-05-07 | Phase 1 holdout 並走 |
| 2026-05-14 | MAFE 再集計と統合 |

## 11. 参照
- [[phase5-pure-edge-portfolio-2026-04-25]] (S1-S3 詳細)
- [[phase5-extended-s4-s9-2026-04-25]] (S4-S9 ロジック骨子)
- [[lesson-toxic-anti-patterns-2026-04-25]] (Gate -1)
- [[lesson-asymmetric-agility-2026-04-25]] (Rule 1)
- [[lesson-survivor-bias-mae-breaker-2026-04-25]] (MAE Breaker)
