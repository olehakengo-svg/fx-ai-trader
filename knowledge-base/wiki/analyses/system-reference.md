# System Reference — 全バージョン詳細・取引ルール・パラメータ

> **このファイルは CLAUDE.md Diet (2026-04-13) で移行された運用リファレンス。**
> CLAUDE.md はスキーマ（150行以内）、本ファイルが詳細を担う。

## BT Performance — Historical Reference (pre-cutoff)
> **注意**: 以下のBTデータはFidelity Cutoff (2026-04-08) 以前の結果です。
> Shadow汚染・XAU歪み・旧SLTPバグを含む可能性があり、現在のシステム性能を示しません。
> v8.4以降のクリーンデータに基づく最新評価は [[changelog]] および [[index]] を参照してください。

### v5.95 統合監査 (2026-04-07)
- **v5.95 統合BT**: 340t/14d (5m scalp + 15m DT), 摩擦モデルv2, SAR=1.57 (v5.5: 0.42, 3.7x改善)
- **月間PnL**: Raw +857pip → **LC適用 +1,831pip/月** (lifecycle uplift +107%)
- Scalp USD/JPY: 76t WR=65.8% EV=+0.211ATR (fib_reversal WR=86.7% → 1.5x boost)
- Scalp EUR/USD: 40t WR=57.5% (bb_rsi DEMOTED: WR=20% EV=-1.5)
- Scalp GBP/USD: 59t WR=50.8% (macdh DEMOTED: WR=40% EV=-0.818, limit-only enforcement)
- Scalp EUR/JPY: 59t WR=54.2% (vol_surge/bb_squeeze positive, bb_rsi negative)
- DT USD/JPY: 34t WR=61.8% (sr_fib_confluence WR=76.9% → 1.3x boost)
- DT EUR/USD: **27t WR=74.1% EV=+0.647ATR** (orb_trap/htf_fbk/london_ny 1.5x boost)
- DT GBP/USD: **45t WR=66.7% EV=+0.634ATR** (gbp_deep_pullback 2.0x, trendline_sweep 1.5x)
- **1H EUR/USD: 70t WR=50% +483pip** (120d, 1h, KSB+DMB)
- **1H USD/JPY: 40t WR=35% +181pip** (120d, 1h, DMB only, SELL非対称フィルター)
- **Scalp EUR/JPY: 250t WR=45.6% +300pip EV=+1.20** (60d, 5m, UTC 12-15限定)
- Swing: 346t WR=36.7% EV=+0.154 WF=2/3 (730d, 1d)

### Scalp v3.2 Strategy Breakdown (7d BT, bb_rsi Option C適用後)
| Strategy | Trades | WR | EV | Description |
|---|---|---|---|---|
| **bb_rsi_reversion** | **181** | **61.3%** | **+0.173** | **Option C: EUR ADX<25 / JPY ADX制限なし+Death Valley/Gold Hours** |
| macdh_reversal | 144 | 63.2% | +0.231 | BB<0.25/>0.75, MACD-H方向転換 |
| fib_reversal | 172 | 57.0% | +0.056 | Fib 38.2%/50%/61.8%反発, multi-lookback |
| bb_squeeze_breakout | 19 | 36.8% | -0.799 | BB squeeze breakout, ADX>=20 |
| mtf_reversal_confluence | 4 | 50.0% | -0.187 | RSI+MACD AND |
| session_vol_expansion | EUR only | — | — | SVE: London open compression breakout |

### DT v4.4 Strategy Breakdown (55d BT)
| Strategy | EUR Trades | EUR WR | EUR EV | JPY Trades | JPY WR | JPY EV | GBP Trades | GBP WR | GBP EV |
|---|---|---|---|---|---|---|---|---|---|
| sr_fib_confluence | 82 | 63.4% | +0.223 | 84 | 64.3% | +0.286 | 80 | 68.8% | +0.414 |
| **orb_trap** | **42** | **71.4%** | **+0.482** | **29** | **79.3%** | **+0.617** | **28** | **64.3%** | **+0.245** |
| sr_break_retest | — | — | — | 63 | 63.5% | +0.236 | 42 | 61.9% | +0.159 |
| htf_false_breakout | 32 | 65.6% | +0.507 | 24 | 70.8% | +0.545 | 40 | 72.5% | +1.011 |
| gbp_deep_pullback | — | — | — | — | — | — | 38 | 73.7% | +0.543 |
| adx_trend_continuation | 14 | 85.7% | +2.045 | — | — | — | — | — | — |
| tokyo_nakane_momentum | — | — | — | 10 | 70.0% | +0.086 | — | — | — |

## Key Parameters
- **Spread**: Production=OANDA real bid/ask (entry BUY=ask/SELL=bid, exit BUY=bid/SELL=ask)
- **BT spread v2**: ペア別実測値ベース (461t監査)
- **TP/SL**: TP=ATR-based technical target, SL=RR ratio inverse (MIN_RR=1.2)
- **SL floor**: ATR(14)x1.0 minimum distance (engine-level enforcement)
- **Entry quality gate**: QUALIFIED_TYPES only, at least 1 reason required
- **Strategy auto-promotion**: Demo N>=30 & EV≥1.0 → OANDA promotion / EV<-0.5 → demotion
- **Force-demoted (OANDA停止)**: sr_fib_confluence, ema_cross, inducement_ob, ema_ribbon_ride, h1_fib_reversal, pivot_breakout, ema_pullback, fib_reversal, macdh_reversal
- **Pair-Specific Lifecycle**: `(strategy, instrument)` tuple-based granular control
- **Equity Curve Protector**: DD_LOT_TIERS (DD 2%=0.80x / 4%=0.60x / 6%=0.40x / 8%=0.20x)
- **v8.9 Equity Reset**: v8.4以降FX-only非Shadowデータで再計算済み → DD=0.8%, lot_mult=1.0x

## Active Trading Rules & Constraints

### COOLDOWN (Re-entry Throttle)
- EXIT-based (cooldown starts after trade close)
- Scalp: 60s, Daytrade 15m: 900s, Swing: 14400s
- Cross-strategy cascade CD: SL_HIT → all strategies (scalp:90s, DT:180s)
- Post-SL same-direction block: scalp:120s, DT:600s, swing:7200s

### Position Limits
- Max open trades: 4 (safety cap) + per-pair 1 position limit
- DT same-direction: max 2, distance >=5pip
- Scalp same-direction: max 3, distance >=1.0pip
- bb_rsi/macdh mutual exclusion: correlation 0.65 pair within 3min

### Circuit Breaker
- All-direction: N losses in 30min pauses mode (scalp:4, DT:3)
- Same-direction max: 3 consecutive → pause
- Drawdown: Daily -30pip / Max DD -100pip → auto-stop

### Friday Filters
- Scalp: Score threshold 0.6→3.5
- DT: Friday UTC 0-6 SR-based blocked, UTC 18+ fully blocked

### HTF / EMA Hard Filters
- DT HTF hard filter: htf_agreement=bull blocks SELL
- Scalp EMA200/HTF hard filters
- Mean-reversion exemption: bb_rsi, macdh → soft penalty only

### SL Hunting Countermeasures
- Session SL widening: UTC 0,1,18-21h: SL +ATRx0.2
- Counter-trend buffer: MR against L1: SL +ATRx0.25
- Fast-SL adaptive: Fast SL (<120s) → next SL +ATRx0.3
- Spread filter per-pair: JPY 1.0p, EUR 1.2p, GBP 1.2p
- Spike detection: >0.5ATR in 60s blocks entry
- Round number SL avoidance: .000/.500 shifted 2.5pip

### Breakeven & Trailing Stop
- BE trigger: Tier1 ATR*0.8→BE, Tier2 ATR*1.5→Trail(price-ATR*0.5)
- Price velocity filter: >8pip in 10min blocks counter-direction
- ADX regime block: ADX>=35 blocks counter-trend

### SIGNAL_REVERSE
- Min hold: scalp 180s, DT 600s, swing 3600s
- Score threshold: abs(score) >= 2.0
- ADX filter: ADX > 20 (RANGE禁止)
- DT含み益保護: profit > ATR×0.3 → SR無効化

### OANDA Position Sync
- Demo → OANDA sync: Orphan detection every 5s, auto-closed
- Demo as source of truth

## Lot Sizing: 3-Factor Model (v6.2)
- **Final**: clamp(risk × edge × boost, 0.3, 2.5)
- Risk factor: base_sl_pips / actual_sl (scalp=3.5, DT=15, 1H=30)
- Edge factor: ATR/Spread (≥15→1.5x, ≥10→1.3x, ≥6→1.0x, ≥3→0.7x, <3→0.5x)
- Boost factor: strat_boost × N_cap × (0.5 if defensive)
- N<10 Safety: 自動Sentinel (0.01lot)。PAIR_PROMOTED免除

## SHIELD + 非対称攻撃 (v6.4)
- OANDA Lot Hard Cap: 10000u
- OANDA_MODE_BLOCKED: daytrade_eur, daytrade_1h_eur (SHIELD WHITELISTで例外あり)
- Quick-Harvest: OANDA TP = demo TP × 0.85 (v6.8で0.70→0.85)
- Fidelity Cutoff: 2026-04-08T00:00:00+00:00
- 50% TP Profit Extender: TF戦略でTP50%到達+ADX>30 → TP延伸

## Range Exit Optimization (v6.5)
- BB_mid TP Targeting: RANGE + MR戦略 → TP=min(BB_mid, ATR×1.2)
- Range SL widening: ATR mult 0.8→1.0
- RR floor: 0.8 for RANGE MR
- Quick-Harvest bypass: BB_mid TP already shortened → ×1.0

## Range Sub-classification
| Sub-type | Condition | MR制御 |
|---|---|---|
| SQUEEZE | bb_width_pct < 10 | **ブロック** |
| WIDE_RANGE | bb_width_pct >= 10 & ADX < 20 | **ブースト** (+1.0 score, +5 conf) |
| TRANSITION | ADX >= 20 | パススルー |

## Quant Infrastructure (v6.5)
- **ExposureManager**: Cross-pair currency exposure (20,000u limit, max 3 same-dir)
- **AlertManager**: Discord Webhook (DD threshold, OANDA disconnect, EV drop)
- **stats_utils**: Binomial test, Bayesian WR, Bootstrap EV CI, Sortino/Calmar/PF, Kelly, RoR, MAFE
- **Risk Analytics**: VaR/CVaR, Monte Carlo ruin, Kelly fraction, strategy correlation

## Version History Details

### v6.3 Sentinel対策 (2026-04-08)
- 負EV戦略の根本原因を特定し改善（切除ではなく修正）
- bb_rsi_reversion: PAIR_PROMOTED, Gold Hours +0.8, Tier1 TP=2.2
- Rolling EV Monitor: EV急落(drop≥0.2 & EV<-0.3) → 自動アラート

### v6.6-v6.7 攻めの戦略再構築 (2026-04-08)
- EUR/GBP全停止 (Spread/ATR=98.7%)
- DT RANGE TF戦略ブロック (74%がRANGE, WR=25.7%)
- DaytradeEngine競合モード化 (スコア比較で上書き)
- MAX_SL_DIST: SL距離キャップ (外れ値防止)

### v6.8 Quant Audit三段ロケット (2026-04-08)
- Stage 1: fib/macdh→FORCE_DEMOTED, sr_fib×3ペア→PROMOTED全削除
- Stage 2: DT含み益保護, Quick-Harvest 0.70→0.85
- Stage 3: DT Power Session (UTC 7-8, 13-14のみ)
- Stage 3.5: Scalp 5m Sentinel A/Bテスト

### v7.0 リスク管理基盤 (2026-04-08)
- Shadow Tracking: 観測トレード ~50/日→~90/日
- Spread/SL Gate: 35%超でエントリーブロック
- Emergency Kill Switch: POST /api/emergency/kill
- 段階的DDロット縮小 + Kelly Lot Cap
- 東京セッション拡大, 静的時間ブロック全撤去

### v7.1-v7.2 (2026-04-09)
- OANDA転送改善: dt_bb_rsi_mr SHIELD WHITELIST追加
- XAU/USD: 専用フィルター閾値 + gold_trend_momentum新規戦略
- Sentinel N蓄積状況: bb_rsi N=23, fib N=20 (WR劇的改善)

### v8.0-v8.9 (2026-04-10〜13)
- 詳細は [[changelog]] を参照
- v8.3: 確認足フィルター
- v8.4: XAU停止 + Shadow汚染除去
- v8.5: 学術文献6新エッジ戦略
- v8.6: session_time_bias/london_fix PROMOTED + DSR実装
- v8.7: BT Friction Model v3
- v8.8: vol_spike_mr + doji_breakout
- v8.9: Equity Reset (DD 289.9%→0.8%)

## Strategy Architecture Details

### Confluence Scalp v2 (2026-04-07)
- Session Gate(UTC 12-17) + MFE Guard(ATR/Spread>=10) + HTF Hard Block
- Triple Confluence: EMA + RSI/BB + MACD-H 3族合意
- MSS: CHoCH/MSB構造転換検出 (Wyckoff 1931)
- Profit Extender + Climax Exit + Friction Minimizer

### 1H Breakout Mode v5.0
- KSB (Keltner Squeeze Breakout): EUR/USD専用, BB inside Keltner→release→breakout
- DMB (Donchian Momentum Breakout): 両ペア, 48-bar range breakout + DI momentum
- BE at 50% TP → trailing stop

### EUR/JPY Scalp Mode
- UTC 12-15のみ (London/NY overlap)
- ATR/Spread ~3.3 → vol_mult=0.7

### EUR/GBP Daily Mean-Reversion
- 20日レンジ上下10%到達→反転足エントリー
- Spread/Daily ATR=7.5% → 日足以上のみviable

## Production Monitoring
- Slippage: signal_price vs entry_price diff
- Spread: OANDA real spread at entry/exit
- DB columns: signal_price, spread_at_entry, spread_at_exit, slippage_pips, cooldown_elapsed

## Deploy-Safe State Persistence (v6.2)
- system_kv テーブル: SQLite永続化
- Equity Protector: eq_peak/eq_current/defensive_mode → 決済ごとにDB保存
- OANDA Audit: oanda_audit テーブル

## OANDA Integration Details
- **転送司令部**: `/api/config/oanda_control` で LIVE/SENTINEL/OFF/AUTO 切替
- **実行監査**: `/api/oanda/audit` — トレードごとのOANDA連携成否
- **ヘルスチェック**: `/api/oanda/heartbeat` — 60秒間隔
- **ログラベル**: `🔗 OANDA: [SENT/FILLED/FAILED/BLOCKED/SKIP]`
- **指値ログ**: `🔗 OANDA: [LIMIT_PLACED]` / `🔗 OANDA: [LIMIT_FILL]`

## Related
- [[changelog]] — バージョン別変更タイムライン
- [[index]] — 戦略Tier分類・システム状態
- [[roadmap-to-100pct]] — 月利100%ロードマップ
- [[friction-analysis]] — ペア別摩擦分析
