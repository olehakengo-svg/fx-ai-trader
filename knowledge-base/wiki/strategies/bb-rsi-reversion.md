# bb_rsi_reversion

## Status: SCALP_SENTINEL + PAIR_DEMOTED (全ペア) + OANDA_TRIP (BB_RSI_OANDA_TRIP=1) + 🟠 RETIRED (2026-06-12, rule:R2 — `SHADOW_RETIRED_STRATEGIES` で Shadow 含め全ペア恒久停止)
**現行**: SCALP_SENTINEL (最小ロット shadow)。EUR_JPY / EUR_USD / GBP_USD / USD_JPY の 4 ペアすべて PAIR_DEMOTED — 実弾通過なし。

## ★ 2026-05-14 後継: macd_rsi_pullback
bb_rsi の mean-reversion 哲学を放棄し、trend-following pullback 戦略に再設計。
USDJPY 1H × OANDA friction で +EV 確認 (N=196, WR=39.29%, PF=1.161, Net=+0.36%).
詳細: [[../analyses/macd-rsi-pullback-h1-audit-2026-05-14]].
bb_rsi 系 variant 化は引き続き停止。

## ★ 2026-05-14 TV friction cell audit — 全 cell -EV 確認
USDJPY 5m × 1y, OANDA commission 0.0136% RT 込みで Strategy Tester:
N=2,512, WR=30.65%, PF=0.605, Net=-3.13%, Max DD=3.13%.
Session × Tier × H1 RSI × Direction の 16 cell 全てで NetP<0 → **PAIR_DEMOTED 維持決定**.
詳細: [[../analyses/bb-rsi-tv-friction-cell-audit-2026-05-14]].

## ★ 2026-05-14 1m-MTF variant audit — hypothesis falsified
1m MACD entry filter + 1m RSI exhaustion exit で entry/exit 精度を上げる仮説を Pine v5 で検証 (USDJPY 5m, OANDA friction):

| Config | N | WR% | PF | Net |
|---|---:|---:|---:|---:|
| Parent (no 1m MTF) | 733 | 30.97 | 0.59 | -0.92% |
| MACD hist_dir + 1m RSI exit | 619 | 32.15 | 0.55 | -0.86% |
| MACD hist_cross + 1m RSI exit | 100 | 22.00 | 0.34 | -0.22% |
| MACD hist_dir only | 616 | 30.84 | 0.56 | -0.85% |

→ 全 config -EV、全 cell -EV (例外: SELL H1RSI≥70 N=4 NetP=+1.7 / 統計無意味).
1m RSI 早期 TP は WR +1.3pp 上げるが PF は下がる (利幅縮小と zero-sum).
hist_cross は worst (mean reversion against fresh momentum flip).
**bb_rsi_reversion 系 variant 化を完全停止**. 詳細: [[../analyses/bb-rsi-1m-mtf-variant-audit-2026-05-14]].

## ★ 2026-04-25 v11.1 RR floor 適用 (Asymmetric Agility Rule 3)

### 修正内容
TP 計算式を `max(ATR×tp_mult, SL_dist × RR_floor)` に変更.

| Tier | tp_mult (旧 ATR 倍率) | RR_floor (新, 強制) |
|---|---:|---:|
| Tier1 (極端ゾーン) | 2.2 | **3.0** |
| Tier2 (通常) | 1.5 | **2.5** |

### 数学的根拠
WR=32.3% (Wilson_lo=26.4%) で BEV_WR=48.1% を必要とする構造的負 EV.
旧 RR=1.17 では算数破綻 → RR=2.5 (Tier2) で BEV_WR=28.6% に降下、観測 32.3% に対し +3.7pp マージン確保.

### 規律根拠
[[lesson-asymmetric-agility-2026-04-25]] Rule 3 (Immediate, 算数破綻修正) — 365日 BT スキップ.
撤回された pre-reg: [[bb-rsi-rr15-rescue-2026-04-25]].
詳細修正記録: [[bb-rsi-fix-rr-2.5-2026-04-25]].

### 監視 (Rule 2 警報閾値)
- N=10 で Wilson_lo (WR) < 20% → 即停止
- N=20 で PF < 0.7 → 即停止
- N=30 で EV < -1.0p → 即停止
- N=30 で Wilson_lo > 28.6% AND PF > 1.1 → Rule 1 経路で OANDA TRIP 解除 pre-reg 起案

## 2026-05-07 post-Cutoff 観測 (wiki-daily-update)

| Bucket | N | WR | PnL | 備考 |
|---|---|---|---|---|
| Total post-cutoff (2026-04-08+) | 187 | **38.0%** | **-52.7pip** | SCALP_SENTINEL shadow のみ |

⚠️ N=187 at WR=38.0% (BEV_WR≈34.4%)。N=126 (2026-04-24) から +61 trades, -37.9pip 追加損失。止血条件: N≥150 EV<-0.5 → FORCE_DEMOTED 起動検討。現在 EV≈-0.28/trade、Wilson_lo 確認推奨。

## 2026-04-21 post-Cutoff 観測

| Bucket | N | EV | 備考 |
|---|---|---|---|
| Shadow post-cutoff (全ペア) | 117 | **-1.76** | 全ペアで強負 |
| LIVE post-cutoff (USD_JPY) | 4 | +1.52 | PAIR_DEMOTED 展開前の timing lag |

**止血条件**: 詳細は [[negative-strategy-stop-conditions-2026-04-21]]
- Shadow N≥150 かつ 7日間 EV < -0.5 → **FORCE_DEMOTED**
- LIVE 新規ペア N≥15 かつ 7日間 mean_pnl < -0.5 → **PAIR_DEMOTED 追加**

**履歴**: Previously PAIR_PROMOTED x USD_JPY (v6.3-v8.8, "The only strategy with PF > 1 in 556t production audit")。v8.9 で Post-cut N=76 WR=38.2% EV=-0.28 Kelly=-5.5% → Tier1 剥奪、USD_JPY も PAIR_DEMOTED に降格。

## Performance History
| Period | N | WR | PnL | PF | Notes |
|--------|---|-----|-----|-----|-------|
| Pre-cutoff (all) | 212 | 44.3% | -274.2 | <1 | All pairs mixed |
| Pre-cutoff (USD_JPY) | 123 | 54.7% | +54.8 | 1.13 | **Only PF>1** |
| Post-cutoff (shadow-excluded) | 77 | 36.4% | -42.2 | - | v8.4 shadow filter applied |
| BT (v3.2, 7d) | 181 | 61.3% | - | - | EV=+0.173 ATR |

## v8.3 Changes (2026-04-10)
- Added confirmation candle: `ctx.entry > ctx.open_price` (BUY) / `< open` (SELL)
- Counter-trend filter: TREND_BULL blocks SELL, TREND_BEAR blocks BUY
- ADX floor: JPY ADX < 15 -> return None
- **Expected**: instant death 77.6% -> 20-25%, WR -> 58-62%
- **Status**: OOS verification pending (data accumulating)

## MAFE Profile
- WIN: avg MAE=1.1pip, avg MFE=3.7pip (entry precision ratio=3.36)
- LOSS: avg MAE=3.2pip (=SL), avg MFE=0.3pip (instant death)
- 77.6% of losses have MFE=0 (never favorable)

## Friction
- USD_JPY: spread 0.7 + slip 0.5 = 2.14pip RT
- BEV_WR = 34.4%
- Edge = 0.45pip/trade (extremely thin)

## Key Risk
- Post-cutoff WR=36.4% is only 2pp above BEV_WR=34.4%
- Independent audit warning: "edge could vanish with slight spread increase"
- v8.3 confirmation candle effect is UNVERIFIED

## v9.3 P2: REGIME_ADAPTIVE Family (2026-04-17)

本戦略は **regime 方向で family 挙動が反転** する非対称性を持つため、
`research/edge_discovery/strategy_family_map.py::REGIME_ADAPTIVE_FAMILY` で
regime 別に family をオーバーライドする。

### 観測された非対称性 (Phase C N=324, P0 forensics)

| Regime | BUY WR | SELL WR | 差 | 実挙動 |
|---|---|---|---|---|
| `trend_up_weak`/`_strong` | **55%** | 50% | +5pp | **TF** (順張り BUY が aligned) |
| `trend_down_weak`/`_strong` | **44%** | 23% | +21pp | **MR** (逆張り BUY = fade 下落が aligned) |
| `range_tight`/`_wide` | — | — | — | default **MR** (両方向 BUY aligned) |

`trend_down` における BUY WR > SELL WR (差 +21pp) は特に強いシグナル.
「下落中に拾う」MR 挙動が顕著で、単一 family 分類では取りこぼすエッジ。

### 現行マッピング

```python
REGIME_ADAPTIVE_FAMILY["bb_rsi_reversion"] = {
    "trend_up_weak": "TF",
    "trend_up_strong": "TF",
    "trend_down_weak": "MR",
    "trend_down_strong": "MR",
    # range_* は override せず default MR
}
```

### 効果 (Phase C OOS データ再実行)

- LIVE ΔWR (aligned vs conflict): +2.4pp → **+9.3pp (4×)**
- IS aligned − conflict WR gap: **+12.0pp**
- IS/OOS 全 family 符号一致維持 (curve-fit 耐性保持)

### 運用

v9.3 Phase D hash-based A/B routing (`gate_group = mtf_gated`) 下で、
本戦略の conflict alignment トレードは LIVE→SHADOW downgrade される。
Group B (`label_only`) では従来通り LIVE 実行 → 並走で gate 効果を直接測定。

## Related
- [[friction-analysis]]
- [[mfe-zero-analysis]]
- [[independent-audit-2026-04-10]]
- [[mtf-regime-validation-2026-04-17]] §C (P0 forensics) / §E (REGIME_ADAPTIVE)

## 2026-06-08 Pair Whitelist Redesign

**Status**: implemented per `docs/superpowers/specs/2026-06-08-session-time-bias-bb-rsi-edge-cell-redesign-design.md`

**Filter**:
- ON pairs: USD_JPY only
- KILL pairs (absolute block): USD_CHF, GBP_USD
- Other pairs: skip (insufficient evidence)

**SIZE lever**:
- USD_JPY × LDN/NY (UTC 07-21): 1.0x
- USD_JPY × ASN (UTC 00-07): 0.5x defensive

**Empirical baseline (40-day shadow data, N=239)**:
- baseline (no filter): WR 30.1%, mean -0.77p, sum -184p
- proposed (USD_JPY only): in-sample N=96, WR 43.8%, mean +0.10p, sum +9p
- killing USD_CHF removes -120p single-strategy bleed; GBP_USD removes -60p

**Rollback**: `BB_RSI_REVERSION_PAIR_WHITELIST_V1=0`.

## 2026-06-12 Edge Factor Audit #2 — 🟠 統合退役 (恒久退役、思想は dt_bb_rsi_mr が継承)

clean N=780 の要因解析で確定。詳細: [[edge-factor-audit-2026-06-12-bb-rsi-reversion]]

- gross EV +0.50〜+0.61 で**思想は生きている**が、friction 1.2-1.5p が TP 5.2p の 24.7% を占め算数で詰み (BE-WR 40.9% vs 実測 35.4%)
- 同思想 DT 版 [[dt-bb-rsi-mr]] は friction 10.8%/TP で net +1.72 / PF 1.61 — 修理形が既存のため scalp 版の存続理由なし
- 12y MASSIVE BT REJECT (2026-06-11, USD_JPY PF 0.66) と整合
- E4 disable → USD_CHF hourly 漏れ (22件) → env バイパス可能な whitelist、と封じ込め 3 段が漏れ続けたため registry で不可逆化
- 既存防御 (whitelist / per-cell registry / OANDA_TRIP) は残置

## 2026-07-02 T10 判定: KILL (redesign不能)
清浄shadow N=495 の因子分解 + 敵対検証で生存セルゼロ。構造的死因 = friction>edge (楽観上限マスクでも BE 天井)。**再試行禁止** (セル分割/フィルタ追加での再生禁止)。Shadow 収集は継続、LIVE 候補・redesign 工数はゼロ固定。詳細: [[bb-rsi-t10-kill-2026-07-02]]
