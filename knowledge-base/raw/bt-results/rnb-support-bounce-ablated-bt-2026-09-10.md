# rnb_support_bounce × USD_JPY × BUY — BE/Trail-ablated closed-bar BT (2026-09-10)

**rule**: R3 (R1 パケット [[../../wiki/decisions/rnb-support-bounce-r1-packet-2026-09-10]] の evidence)
**ハーネス**: `knowledge-base/raw/session-scripts/rnb-support-bounce-ablated-bt-2026-09-10.py`
**データ**: `data/cache/massive/USD_JPY_15m.parquet` (MASSIVE、315,994 bars、2013-10-24 → 2026-09-10 01:00 UTC)
**signal fn**: 本番 `app.compute_rnb_signal` (backtest_mode=True、確定足評価)

## Estimand

- 固定 TP=20p / SL=15p (RR 1.33)、MAX_HOLD 8×15m bars (=MODE_CONFIG MAX_HOLD_SEC 7200s)
- **BE/Trail なし** (ablated — MEMORY `project_be_trail_inflates_python_bt_wr`: BE/Trail は Python BT WR を +20pp 水増し)
- 同時 1 ポジション (live `_mode_limits` daytrade-class=1 と同一)
- 同一バー SL/TP 両接触 → **SL 扱い (悲観側)** — 365d で 1 件のみ
- friction: USD_JPY RT **2.14p** ([[../../wiki/analyses/friction-analysis]])
- ATR: live 慣行と同一 (`ta` AverageTrueRange(14)、`modules/indicators.py`)
- ⚠️ closed-bar estimand。live は forming-bar 30s 評価 (MEMORY `project_ps_capture_estimand_disjoint_2026_09_09`) — **本 BT の EV を live 期待値として引用しない**

## 結果

| 窓 | bars | raw setups | /週 | N (非重複) | WR | Wilson_lo95 | gross EV | **net EV (f2.14)** | net 合計 | PF(gross) | TP/SL/AMBIG/TIMEOUT |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| **365d** | 24,721 | 156 | **2.99** | 126 | 55.6% | 46.8% | +2.18p | **+0.04p** | +5.5p | 1.429 | 35/37/1/53 |
| 730d | 49,404 | 352 | 3.38 | 295 | 44.8% | 39.2% | −0.06p | **−2.20p** | −649.9p | 0.991 | 83/121/2/89 |
| 90d | 6,143 | 28 | 2.18 | 23 | 52.2% | 33.0% | −1.81p | **−3.95p** | −90.8p | 0.667 | 1/6/1/15 |

- setup 頻度 2.99/週 は [[../../wiki/analyses/rnb-dead-mode-and-block-estimand-2026-09-05]] §1.2 の 157/365d (3.0/週) と一致 (再現確認、parquet 5 日分更新差で 156)
- friction 込み BEV_WR = (15+2.14)/35 = **49.0%**。365d WR 55.6% の二項片側 p = **0.082** (単一 pre-specified cell、m=1 でも NS)。Wilson_lo 46.8% < BEV 49.0% → **lot ladder テンプレの昇格 gate (Wilson_lo > BEV) 不成立**
- 月次分解 (365d net): **2026-03 単月 +160.9p が net 合計 +5.5p を単独で説明** (他 12 ヶ月合計 −155.4p)。2026-09 (部分月 N=6) は −102.8p
- TIMEOUT 53/126 (42%)、timeout 平均 +2.7p — exit 構造は timeout 依存が大きい

## verdict (evidence としての読み)

**live 昇格根拠なし** (net EV≈0・NS・単月依存・730d/90d 負)。頻度 (2.99/週 ≥ registry 閾値 1.0/週) は成立。
→ 登録の価値は「shadow N 源 (現行最速 live セル 2.10/週 超)」+「forming-bar live estimand の実測取得」に限定される。
判断は packet 本文 [[../../wiki/decisions/rnb-support-bounce-r1-packet-2026-09-10]] を参照。
