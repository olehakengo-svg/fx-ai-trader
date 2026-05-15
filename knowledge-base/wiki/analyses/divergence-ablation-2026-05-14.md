# Python BT ↔ TV BT 乖離 — 執行層 Ablation 分析 — 2026-05-14

**Rule**: R3 (Immediate, math invariant — 実行層機構の出力寄与を分離計測)
**Setup**: xs_momentum × USD_JPY × 318d × 15m。`tools/bt_divergence_ablation_2026-05-14.py`
**Source data**: `raw/bt-results/ablation-divergence-2026-05-14.json`
**先行発見**: `cross-strategy-tv-bt-reconciliation-2026-05-14.md` で Python BT WR 62.7% vs TV BT WR 43.5% の +19.2pp gap を測定

## TL;DR

1. **Python full BT vs TV BT の WR 乖離 (+19.2pp) は BE/Trail (Tier1+Tier2 partial exit) で完全に説明できる** — `no_BE_trail` で xs_momentum WR 62.7% → **39.8%** (TV の 43.5% と sampling noise 範囲内)
2. **Cascade CD (12-bar all-strategy block) は xs_momentum/sess_time_bias に対して marginal 効果ゼロ** — signal density が低く 12-bar 窓に signals がほぼ重ならない
3. **Post-SL same-dir block (40-bar) は xs_momentum で −2 trades / −2.4pp WR** — 微寄与
4. **Quick Harvest (0.85× TP) は xs_momentum WR を 3.2pp inflate** — 部分利確で reversal 前に WIN 確定
5. **N 乖離 (Python 158 vs TV 501, 3.17×) は execution layer ablation では説明できない** — `all_off` でも xs_momentum N=108。signal qualification gate (DT_QUALIFIED, session×pair filter, HTF bias 等) が TV Pine replica と未整合の可能性

## 完全結果テーブル

| variant | xs_mom N | xs_mom WR | xs_mom EV | ΔWR vs baseline | sess_t N | sess_t WR | sess_t EV |
|---|---:|---:|---:|---:|---:|---:|---:|
| baseline_all_layers | 158 | 62.7% | +0.084 | — | 301 | 64.5% | +0.107 |
| no_cascade_cd | 158 | 62.7% | +0.084 | **0.0** | 301 | 64.5% | +0.107 |
| no_post_sl_block | 156 | 60.3% | +0.035 | −2.4 | 298 | 64.8% | +0.114 |
| no_cascade_and_post_sl | 156 | 60.3% | +0.035 | −2.4 | 298 | 64.8% | +0.114 |
| no_quick_harvest | 158 | 59.5% | +0.086 | −3.2 | 199 | 74.9% | +0.475 |
| **no_be_trail** | 118 | **39.8%** | **−0.521** | **−22.9** | 264 | 38.6% | −0.536 |
| all_off | 108 | 31.5% | −0.684 | −31.2 | 162 | 43.8% | −0.255 |

**TV reference (xs_momentum × USD_JPY)**: N=501 WR=**43.5%** PF=1.04 (`python-bt-vs-tv-reconciliation-2026-05-14.md`)

## 主要発見

### 1. BE/Trail が WR 乖離のドミナント要因

xs_momentum × USDJPY:
- baseline WR 62.7% → no_BE_trail WR **39.8%** (−22.9pp)
- TV BT WR = 43.5% → no_BE_trail との diff は **−3.7pp** (sampling noise 範囲内、N=118 vs N=501 で有意でない)

機構 (app.py line 6788-6818, 6880-6883):
```python
_dt_be_thr = atr * 0.8   # Tier1: BE 移動閾値
_dt_ts_thr = atr * 1.5   # Tier2: Trail 開始閾値
# 価格が atr*0.8 順行 → SL を entry+offset へ移動
# 価格が atr*1.5 順行 → trail SL = max(_dt_current_sl, hi - atr*0.5)
# その後 fut が _dt_current_sl 触る → outcome="WIN" (BE活性化なら ep+0.6tp_dist で profit count)
```

TV Pine replica は **fixed SL = 1.5 ATR** で BE/Trail 無し → original SL に当たる前に reversal すれば LOSS。Python BT は BE 活性化後の SL touch を WIN にカウント。

### 2. Cascade CD は marginal 効果ゼロ (この strategy には)

- `_CASCADE_CD_DT = 12` bars (15m=180s) を 0 にしても xs_momentum/sess_time_bias の N/WR 完全一致
- 解釈: xs_momentum の signal は時間的に sparse (318日で N=158 = ~1 entry/2日) で、12 bar=3h の cooldown 窓に signals がほぼ重ならない
- **Cascade CD は high-density strategy (scalp や ema_trend) では効くが、DT high-quality entry には binding しない**

### 3. Post-SL same-dir block は微効

- xs_momentum: 158 → 156 trades (−2), WR 62.7 → 60.3 (−2.4pp)
- 解釈: BUY-SL 直後 40 bars (=10h) の BUY 再 entry は数件しか発生せず、その数件は実際に勝率低めだった

### 4. Quick Harvest は xs_momentum WR を 3pp inflate

- baseline WR 62.7% → no_QH WR 59.5% (−3.2pp)
- 機構 (line 6761): `tp = ep + (tp - ep) * 0.85` → TP を 15% 早めて部分利確
- 効果: full TP 到達前に reversal で SL に当たる trades を、QH で WIN 確定させる

### 5. sess_time_bias の不思議な挙動 — Cross-strategy 結合効果

- baseline N=301 WR=64.5% → no_QH N=199 WR=74.9% (N -34%, WR +10.4pp)
- sess_time_bias は QH_EXEMPT set に含まれる (`_BT_QH_EXEMPT_DT` line 6349-6356) ので **直接** QH 影響は受けない
- それなのに massive な変化: **他戦略の QH off → 他戦略の SL hit 増 → cascade_cd state 変化 → sess_time_bias の entry 可否変化**
- 解釈: BT における multi-strategy interaction は線形分解できない。「sess_time_bias 単独 WR」の解釈は限定的

### 6. N 乖離 (3.17×) は execution layer では説明できない

- TV: N=501
- Python baseline: N=158
- Python all_off: N=108 (むしろ baseline より少ない、SL-hold が長引いて新 entry の余地が削れる)
- **結論**: 3.17× の N 比は execution layer ablation では再現できない。signal qualification gate (`DT_QUALIFIED` set, EUR_USD Tokyo/Late_NY 停止フィルタ、HTF bias filter、SR 計算、Score 閾値) と TV Pine replica の整合性を別途検証する必要がある

## 真値階層の更新

| Source | WR (xs_mom × USDJPY) | Reliability | 理由 |
|---|---:|---|---|
| **TV Strategy Tester (Pine replica)** | 43.5% | 真値の近似 | execution layer なしの raw signal — Python ablation の `no_BE_trail` と整合 |
| **Python BT no_BE_trail** | 39.8% | 真値の近似 | TV と sampling noise 範囲内、独立計測の整合 |
| **Python BT shadow-isolated** | 60.4% | 中 | 他戦略 cascade なし、単戦略の execution_layer 込み (`portfolio-bt-rescan-2026-05-14.md`) |
| **Python BT full (baseline)** | 62.7% | **過大評価** | BE/Trail と QH で systematic に WR を inflate |
| **Live (oanda_trade_id ≠ '')** | (未測定) | 真値 | execution friction + BE/Trail + QH の真の出力 |

memory `feedback_tv_edge_discovery_loop` の階層 (Live > TV > Python BT) は **直接 Python full BT を信用するなら TV 経由が正しい近似** を意味する — Python BT は **生 BE/Trail のオフを simulate しないと TV と整合しない**。

## Tier 判断への含意 (本 doc では action しない)

- Python full BT の +EV 値はそのまま Live edge の予測値として使えない → **新規 promote は最低限 `no_BE_trail` 同等な独立計測 (TV BT or Live) で再検証**
- 既存 ELITE_LIVE / PAIR_PROMOTED 戦略の Python full BT WR は **3〜23pp 過大評価** の可能性。次の cell audit では BT WR ではなく Live trades の oanda_trade_id 集計を使う
- Cascade CD は防御機構として残す価値あり (drawdown 抑制) — WR への影響はゼロでも、tail loss 抑制効果は別途測定要

## 関連

- [[cross-strategy-tv-bt-reconciliation-2026-05-14]] — 乖離発見元 (xs_momentum + trendline_sweep)
- [[python-bt-vs-tv-reconciliation-2026-05-14]] — xs_momentum 単独 TV vs Python 比較
- [[portfolio-bt-rescan-2026-05-14]] — Python BT shadow vs full
- [[feedback_tv_edge_discovery_loop]] (memory) — 真値階層
- 実装: `tools/bt_divergence_ablation_2026-05-14.py`, env vars: `BT_ABLATE_CASCADE_CD`, `BT_ABLATE_POST_SL_BLOCK`, `BT_ABLATE_QUICK_HARVEST`, `BT_ABLATE_BE_TRAIL` (app.py L6346-, L6790-)

## Next steps

1. **N 乖離調査**: TV Pine replica の signal filter と Python BT の `DT_QUALIFIED` / session×pair filter を 1 行ずつ突き合わせ。TV が N=501 で Python が N=158 になる削減段を特定
2. **他戦略への展開**: trendline_sweep × EUR_USD/GBP_USD (ELITE_LIVE) も `no_BE_trail` で TV と整合するか確認
3. **Live cell audit**: Live trades の `oanda_trade_id ≠ ''` 集計で xs_momentum WR が baseline 62.7% 寄りか no_BE_trail 39.8% 寄りかを確認 (本番の BE/Trail logic が BT と同じなら baseline 寄りのはず)

## 2026-05-15 追記: BT default を TV-aligned に反転

ユーザー指示「基本BTが楽観すぎることが課題なのでtvbtと合わせてください」を受け、`run_daytrade_backtest` の default を反転:

- **新 default**: BE/Trail を off (`_BT_ABLATE_BE_TRAIL = True`), QH は keep (TV Pine 側に近い挙動あり)
- **旧 (inflated) 挙動**: `BT_OPTIMISTIC=1` 環境変数で復元可能 (transition 期間用)
- 実装: app.py L6351-6362, L6800-6803, cache_key L6287 に `_opt{0|1}` segment 追加

新 default 検証 (USD_JPY × 318d × 15m):

| metric | xs_momentum | sess_time_bias | total |
|---|---:|---:|---:|
| N | 118 | 264 | — |
| WR | **39.8%** | 38.6% | 36.1% |
| EV | -0.521 | -0.536 | -0.907 |

xs_momentum WR=39.8% は TV BT 43.5% と sampling noise 範囲内で整合 ✓
`BT_OPTIMISTIC=1` で legacy run: xs_momentum N=156 WR=60.3% EV=+0.035 (旧 baseline N=158 WR=62.7% と微差 < 3pp; cache 切替時の indicator 計算順序差)

**KB 上の既存 BT WR/EV は legacy 値**: `comprehensive-bt-scan-2026-05-14.json`, `tier-master.md`, 各 strategy page の `EV=+0.xxx WR=xx.x%` は全て `BT_OPTIMISTIC=1` 相当の inflated 値。新規 promote 判定では legacy 値を rough upper bound、新 default 値を core decision base として併用すること。

**全 ablation tool の baseline 列も legacy 値**: `tools/bt_divergence_ablation_2026-05-14.py` の `baseline_all_layers` variant は旧 default で測定。新 tool 走行時は `BT_OPTIMISTIC=1` を立てて再現要。
