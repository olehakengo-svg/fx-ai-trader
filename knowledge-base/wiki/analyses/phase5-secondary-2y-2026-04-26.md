# Pre-Registration: Phase 5 副次仮説 2 年 BT (3 SURVIVOR 兆候 cluster) — 2026-04-26 LOCK

> **Pre-reg LOCK 確定 (2026-04-26)** — data look 前. [[phase5-9d-edge-matrix-2026-04-25]]
> + [[lesson-pure-edge-5m-structural-failure-2026-04-25]] の本日 BT で観察された
> 3 SURVIVOR 兆候を **N≥20-30 確保 + 関連 PAIR 1個追加**で本検定 SURVIVOR 化
> できるか判定する追試 pre-reg.

## 0. HARKing 回避の規律

[[lesson-asymmetric-agility-2026-04-25]] Rule 1 完全準拠:
- **拡張軸は 2 つのみ** (期間: 365日→2年, PAIR: Top2→+1関連 PAIR)
- **個別パラメータ (vol_spike_ratio, gap_min_atr 等) は本日値で固定**
- 本日 BT 結果見て調整した仮説変更は **HARKing 違反として明示禁止**

## 1. 3 SURVIVOR 兆候 cluster と本検定仮説

### Cluster 1: S7 ORB (Opening Range Breakout)
- 本日 BT (365日): 12 cells, 合計 N=10 件で WR 90% 級, EV +23〜+82pip
- 物理仮説: GBP系 × London/NY open × Asia range break + vol×2.5 (固定)
- 拡張: + EUR/JPY (London open で macro flow 受ける cross)
- **検定 PAIR (3)**: GBP/USD, GBP/JPY, EUR/JPY
- **個別パラメータ (固定)**: vol_spike_ratio=2.5, asia_range_hours=6, sl_atr=0.8
- **検定軸 (3)**: session ∈ {London_open, NY_open, both}

### Cluster 2: S9 VSA C09 (USD/JPY × vol×3.0 × body<0.3)
- 本日 BT (365日): N=26 WR 57.7% EV +4.00 PF 1.61
- 物理仮説: 大口 absorption (vol spike + body 縮小)
- 拡張: + GBP/JPY (高ボラ cross で absorption pattern 検出可能)
- **検定 PAIR (3)**: USD/JPY, GBP/JPY, EUR/JPY
- **個別パラメータ (固定)**: vol_spike=3.0, body_max=0.3, sl_atr=0.6
- **検定軸 (3)**: lookback ∈ {30, 50, 100}

### Cluster 3: S5 VWAP C03 (EUR/USD × VWAP+EMA50_HTF BOTH touch)
- 本日 BT (365日): N=5 WR 60% EV +4.69 PF 2.39
- 物理仮説: 大口機関の二重防衛線 (VWAP + 上位足 EMA50)
- 拡張: + GBP/USD (Cable 系大口機関 trend follow)
- **検定 PAIR (3)**: EUR/USD, GBP/USD, EUR/JPY
- **個別パラメータ (固定)**: pullback_min_atr=1.5, defense_touch_atr=0.2, sl_atr=0.8, defense_line=BOTH (本日 SURVIVOR 兆候の cell 限定)
- **検定軸 (3)**: trend_filter ∈ {ema9>21>50, ema21>50, ema21>50 + adx>20}

## 2. データセット

- 期間: **2 年 (2024-04-26 〜 2026-04-25)** で N 倍増
- PAIR: 各 cluster 3 PAIR (上記)
- bar TF: 5m (3 cluster 共通)
- 摩擦モデル: v2 (本日 BT と同)

## 3. 検定グリッド (各 cluster)

各 cluster: **3 PAIR × 3 検定軸 = 9 cells**.

合計 **3 cluster × 9 cells = 27 cells**.

Bonferroni: outer 3 cluster 独立検定 → 各 cluster 内 α_cell = 0.05 / 9 = **0.00556**
(各仮説の H1 は独立物理仮説で交差なし).

## 4. SURVIVOR Gate (LOCKED, AND)

### 共通条件 (全 cluster):
1. **EV > +1.5p / trade** (摩擦+slippage マージン)
2. **PF > 1.5**
3. **N ≥ 20** (本検定の N 確保要件)
4. **Wilson_lo (WR) > 観測 WR の 70%** (overfit防止)
5. **Welch p < 0.00556 vs random baseline**
6. **WF 4/4 same-sign** (90日 × 4 期間で全 EV>0 同符号)
7. **MAE_BREAKER < 30%** (FLOOR_INFEASIBLE 回避)

### Cluster 別 追加条件:
- S7 ORB: 実 RR ≥ 2.0 (高 RR 設計強制)
- S9 VSA: 実 RR ≥ 2.0
- S5 VWAP BOTH: 実 RR ≥ 2.5

## 5. CANDIDATE / REJECT 判定

- **SURVIVOR**: 全条件 AND 通過 → 該当戦略の deploy pre-reg を別途起案
- **CANDIDATE**: EV>+1.0p AND p<0.05 AND WF≥3 same → holdout 5/14 で再判定
- **REJECT**: ≤2 条件通過 → 該当 cluster は **Pure Edge 5m 限定で DEAD 確定**

## 6. メタ判定 (3 cluster 統合)

- **3 cluster すべて SURVIVOR**: Phase 5 副次の完全勝利. v2.2 で 3 戦略実装+ deploy
- **2 SURVIVOR**: 部分的 Edge 確保. 該当 2 戦略のみ実装
- **1 SURVIVOR**: 単独 Edge 候補. portfolio 集中リスク評価必須
- **0 SURVIVOR**: Phase 5 全否定確定. Phase D (1H/4H) に方向転換

## 7. 副次仮説 (Bonferroni 対象外, 観察記録のみ)

実装上の興味深い観察として:
- TF 依存性: 5m → 上位足で Edge 安定化するか ([[Phase D]] に引き継ぎ)
- PAIR 独立性: 関連 PAIR 1個追加で SURVIVOR cell が複数 PAIR で観察されるか

これらは判定軸ではなく **パラメータ感度の参考情報**.

## 8. 実装注記

### 新規 BT harness (3 個)
- `scripts/phase5_orb_2y_bt.py` (S7 拡張版, EUR/JPY 追加)
- `scripts/phase5_vsa_2y_bt.py` (S9 拡張版, GBP/JPY + EUR/JPY 追加)
- `scripts/phase5_vwap_2y_bt.py` (S5 拡張版, GBP/USD + EUR/JPY 追加)

### テンプレ流用元
- `scripts/phase5_orb_bt.py` (本日 push 済)
- `scripts/phase5_vsa_bt.py` (本日 push 済)
- `scripts/phase5_vwap_defense_bt.py` (本日 push 済)

各々 `PAIRS_*` リスト変更 + 期間引数を 2 年に + 個別パラメータ固定で拡張.

### MAE_BREAKER 必須
全 BT で `MAE_CATASTROPHIC_PIPS = 15` を継承 (本日全 BT と同設定).

## 9. 凍結ルール

- 本 pre-reg LOCK 後、**コード変更禁止**まで BT 完走.
- 365日 BT (本日) と 2 年 BT (本 pre-reg) で**同じ判定基準**を適用.
- SURVIVOR 後の deploy pre-reg は別途起案 (本 pre-reg では deploy 計画は含まない).

## 10. タイムライン

| 日付 | アクション |
|---|---|
| 2026-04-26 (本日 LOCK) | 本 pre-reg + 3 harness 実装 + dry-run 検証 |
| 2026-04-28 (月曜) | 3 BT 並走起動 (data look-blind) |
| 2026-04-29〜04-30 | BT 完走 (推定 2-4h × 3) |
| 2026-04-30 | SURVIVOR 判定 + 結果 KB 起案 |
| 2026-05-01〜02 | SURVIVOR 戦略の deploy pre-reg 起案 |
| 2026-05-07 (Phase 1 holdout) | Live 観測結果と統合判定 |

## 11. メモリ整合性

- [部分的クオンツの罠]: PF/Wilson_lo/RR/p_welch/WF/MAE_BREAKER 完備 ✅
- [ラベル実測主義]: BT 2 年実測のみで判定 ✅
- [成功するまでやる]: REJECT でも Phase D (TF grid) 並走で深掘り継続 ✅
- [Asymmetric Agility Rule 1]: 新エッジ主張 = LOCK + Bonferroni 完備 ✅
- 総当たり禁止: 各 cluster PAIR 3 個限定 (関連 PAIR 1 個のみ追加) ✅
- HARKing 回避: 拡張軸は期間 + PAIR のみ. 個別パラメータは本日値で固定 ✅

## 12. 参照

- [[phase5-pure-edge-portfolio-2026-04-25]] (S1-S3 LOCK)
- [[phase5-extended-s4-s9-2026-04-25]] (S4-S9 LOCK)
- [[phase5-9d-edge-matrix-2026-04-25]] (PAIR×Session 統合)
- [[lesson-pure-edge-5m-structural-failure-2026-04-25]] (Phase 5 構造的失敗総括)
- [[lesson-survivor-bias-mae-breaker-2026-04-25]] (MAE_BREAKER 設計根拠)
- [[lesson-asymmetric-agility-2026-04-25]] (Rule 1 適用)
- [[external-audit-2026-04-24]] (新Phase 凍結方針 — 本 pre-reg は副次仮説検定で適用外)
