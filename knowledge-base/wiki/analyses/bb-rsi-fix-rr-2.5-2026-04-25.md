# [[bb-rsi-fix-rr-2.5-2026-04-25]] — Rule 3 即時修正: bb_rsi_reversion RR floor 2.5/3.0

**適用日**: 2026-04-25
**ルール**: [[lesson-asymmetric-agility-2026-04-25]] Rule 3 (Immediate, 算数破綻修正)
**ステータス**: ★ 即時適用 (365日 BT スキップ)
**撤回した pre-reg**: [[bb-rsi-rr15-rescue-2026-04-25]]
**対象コード**: `strategies/scalp/bb_rsi.py` (BBRsiReversion)

---

## 1. 算数破綻の数学的証明

### 観測データ ([[tp-hit-deep-mining-grail-2026-04-25]] より)

| 項目 | 値 |
|---|---:|
| `bb_rsi_reversion × USD_JPY × RANGE` Closed N | 217 |
| Win rate (TP-hit rate) | 32.3% |
| Wilson 95% CI lower | 26.4% |
| Avg TP distance | 4.92p |
| Avg SL distance | 4.27p |
| **Realized RR** | **1.17** |
| Per-trade EV | **-0.58p** |
| Profit Factor | 0.75 |

### Break-even 数学

期待値ゼロ条件:

```
EV = WR × (RR × |loss|) − (1 − WR) × |loss| = 0
⇔ WR × RR = 1 − WR
⇔ RR_BEV = (1 − WR) / WR
⇔ WR_BEV = 1 / (1 + RR)
```

### 現状 (RR=1.17) の必要 WR

```
WR_BEV = 1 / (1 + 1.17) = 1 / 2.17 = 0.461 = 46.1%
```

しかし観測 WR = 32.3% (Wilson_lo = 26.4%) << 46.1%
→ **Wilson 信頼区間の上限ですら BEV に到達しない**.
→ **統計的検定は不要**. これは標本誤差ではなく構造誤差.

### WR=32.3% で BEV を満たす最低 RR

```
RR_min = (1 − 0.323) / 0.323 = 2.097
```

→ Wilson_lo=26.4% で BEV を確実にする RR:

```
RR_safe = (1 − 0.264) / 0.264 = 2.788
```

### TP 拡張による WR drop の補正

TP 距離を拡げると、過去 TP に到達していた一部 trade が反転 → SL 到達に変わる.
保守的に WR drop = 5pp を仮定:

```
WR_post_extension ≈ 0.323 − 0.05 = 0.273
RR_min (post) = (1 − 0.273) / 0.273 = 2.66
```

### 採用値

| Tier | RR Floor | BEV_WR (理論) | WR margin (vs 観測 32.3%) |
|---|---:|---:|---:|
| Tier2 (通常) | **2.5** | 28.6% | +3.7pp |
| Tier1 (極端ゾーン) | **3.0** | 25.0% | +7.3pp (Wilson_lo 26.4% との margin +1.4pp) |

**RR=1.5 を選ばなかった理由**: BEV_WR=40% で観測 32.3% に対し −7.7pp 不足.
本セッション pre-reg 表 ([[bb-rsi-rr15-rescue-2026-04-25]] §2 H1 詳細閾値) でも
「RR 1.50 → +9.8 pt 不足」と既証明済. RR=1.5 では算数破綻が解消されない.

---

## 2. コード差分 (本適用)

`strategies/scalp/bb_rsi.py`:

```python
# (定数追加)
rr_floor_tier1 = 3.0  # Tier1 (極端ゾーン): RR≥3.0 強制
rr_floor_tier2 = 2.5  # Tier2 (通常): RR≥2.5 強制 (BEV margin vs WR=32.3%)

# BUY (旧)
tp_mult = self.tp_mult_tier1 if tier1 else self.tp_mult_tier2
tp = ctx.entry + ctx.atr7 * tp_mult
sl_dist = max(abs(ctx.entry - ctx.bb_lower) + ctx.atr7 * 0.3, _min_sl)
sl = ctx.entry - sl_dist

# BUY (新)
sl_dist = max(abs(ctx.entry - ctx.bb_lower) + ctx.atr7 * 0.3, _min_sl)
sl = ctx.entry - sl_dist
tp_mult = self.tp_mult_tier1 if tier1 else self.tp_mult_tier2
rr_floor = self.rr_floor_tier1 if tier1 else self.rr_floor_tier2
tp_dist = max(ctx.atr7 * tp_mult, sl_dist * rr_floor)
tp = ctx.entry + tp_dist

# SELL は対称構造
```

### 設計上の決定事項

| 項目 | 選択 | 理由 |
|---|---|---|
| 旧 ATR ベース TP の維持 | YES (max() で並走) | ATR が大きい高ボラ環境では旧 TP の方が広い場合がある. 後方互換性 |
| RR floor の実装位置 | TP 計算側 | SL は反転起点 (BB band) を基準に物理的意味を持つ. SL を縮める方向の調整は危険 |
| dt_bb_rsi_mr への適用 | **見送り** | pre-reg 評価は scalp 版のみ. dt 版は MIN_RR=1.2, RR=1.25 で WR データ不在. 別途 Rule 1 経路で Holdout BT 後判断 |
| OANDA TRIP 解除 | **しない** | RR 修正の効果検証まで `BB_RSI_OANDA_TRIP=1` 維持. Shadow データで N≥30 確認後に Rule 1 経路で解除 pre-reg 起案 |

---

## 3. 影響範囲

### 直接影響
- `bb_rsi_reversion` (scalp 1m) の TP 距離が**少なくとも SL × 2.5 倍** に拡張される
- 現行 ATR=4.27p / SL_dist=4.27p で旧 TP=ATR×1.5=6.4p → 新 TP = max(6.4, 4.27×2.5) = **10.68p**
- TP-hit 率の低下 (推定 5-10pp) と引き換えに、ヒット時のリターンが拡大

### 間接影響
- TIME_DECAY_EXIT (max 8 bars) で TP 未到達の trade が増加する可能性 → 平均保有時間延長
- Demo Sentinel 経由の Live N 蓄積速度は維持 (entry gate は変更なし)
- OANDA TRIP 維持のため、Live PnL への直接影響はゼロ (Shadow のみで効果検証)

### モニタ指標 (Rule 2 警報閾値)
- 修正後 N=10 で WR < 20% (Wilson_lo) → 即停止 (FORCE_DEMOTED)
- N=20 で PF < 0.7 → 即停止
- N=30 で EV < -1.0p → 即停止
- N=30 で Wilson_lo (WR) > 28.6% AND PF > 1.1 → Rule 1 経路で OANDA TRIP 解除 pre-reg 起案

---

## 4. dt_bb_rsi_mr への適用見送り根拠

`strategies/daytrade/dt_bb_rsi_mr.py` も同型 MR 戦略で:
- SL = ATR × 1.2
- TP = ATR × 1.5
- MIN_RR = 1.2 (実効 RR = 1.25)

形式的には類似の RR 構造を持つが:
1. **WR データ不在** — 15m 足での post-cutoff WR は未集計
2. **Sentinel 観察モード** — 0.01 lot で蓄積中、損失寄与は微小
3. **MIN_RR=1.2 が既に底値ガード** — scalp の `1.17 < 1.2` ほど露骨ではない

→ **Rule 1 経路** (Holdout で N=30 蓄積後 BT 検証) で再判断するのが筋.
本 Rule 3 適用範囲には含めない.

---

## 5. KB / Tier 整合性

- `_FORCE_DEMOTED`: bb_rsi_reversion は維持 (OANDA TRIP の代わり)
- `wiki/strategies/bb-rsi-reversion.md`: 本修正を反映
- `wiki/tier-master.md`: Status は変化なし (DEMO_SENTINEL のまま)
- `BB_RSI_OANDA_TRIP=1`: 維持 (`modules/demo_trader.py:4302`)

---

## 6. ロードマップ寄与度

[[roadmap-v2.1]] Gate 1 (Aggregate Kelly > 0) への影響:
- 直接寄与: ゼロ (OANDA TRIP のため Live PnL 不変)
- 間接寄与: Shadow Sentinel の正 EV 復活 → 将来 Rule 1 経路で TRIP 解除 → Live N 蓄積寄与
- 推定タイムライン: 修正後 Shadow N=30 到達 ≈ 1-2 週 → Holdout 通過後 (2026-05-07+) で復活判定

---

## 7. リスク評価

| リスク | 評価 | 対策 |
|---|---|---|
| RR=2.5 でも WR 不足 (現状 32.3% に対し BEV 28.6%) | 中 | Rule 2 警報閾値 N=10/20/30 で即停止 |
| TP 未到達トレード増 → TIME_DECAY_EXIT 集中 | 中 | MAFE Dynamic Exit pre-reg ([[mafe-dynamic-exit-result-2026-04-24]]) と整合性確認 |
| ATR 期間 7 と RR floor の相互作用で過大 TP 発生 | 低 | max() 並走で旧 ATR 上限維持、+ entry gate (BB%B 閾値) で過剰 entry 抑止 |
| dt_bb_rsi_mr 未適用で同型バグ温存 | 低 | Sentinel 観察 + 別 Rule 1 経路で順次対応 |

---

## 8. 関連

- [[lesson-asymmetric-agility-2026-04-25]] (本修正の規律根拠)
- [[bb-rsi-rr15-rescue-2026-04-25]] (撤回 pre-reg, 参考保管)
- [[tp-hit-deep-mining-grail-2026-04-25]] (構造病理発見の根拠データ)
- [[bb-rsi-reversion]] (戦略 KB)
- [[lesson-preregistration-gate-mechanism-mismatch]] (gate 機構整合性)
- [[roadmap-v2.1]] (Gate 進捗との接続)
