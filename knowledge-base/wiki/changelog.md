# Changelog — バージョン別変更と評価基準日

## なぜこのページが重要か
定量評価は「いつからのデータを使うか」で結論が180度変わる。
各バージョンの変更が**どのトレードに影響するか**をここで追跡する。

## 2026-07-06 — order 層 per-bar dedup — engine 再構築で無効化された strategy 内 guard の構造代替 (rule:R3)

- T8 forensic #2 帰結: DaytradeEngine/HourlyEngine が poll 毎に再構築され strategy instance の per-bar dedup/cooldown が live デッドコードだった問題に対し、order 層 (demo_trader) に `(entry_type, instrument, signal, closed_bar_ts)` の per-bar dedup を追加。
- primary `_tick_entry` と shadow emit DB insert が同一 key 空間を共有 (SHADOW_ALWAYS も bypass 不可)。recent_emit は第2防御として併存。block は `order_bar_dedup` counter で観測可能。
- 影響トレード: 同一バー内の重複 emit (live/shadow とも) が DB insert 前に遮断される。1バー1シグナルの BT 前提に live を整合させる方向の変更。multi-bar cooldown の代替は forensic #3 (BT 突合) 後に判断。
- 回帰: tests/test_dedup_gate_all_paths.py (12 cases)。詳細: [[t8-week1-gate-breach-2026-07-06]]
## 2026-07-06 — T9: Kalman D7 qualifying-bar telemetry + pre-reg 分母付き基準へ追補 (rule:R3)

- roadmap v2.2 T9 (最後の未完了項目)。kalman_d7 に QUALBAR print telemetry を追加 — PO-UP transition バー毎に DIST/GAP/ATR-Q/RSI/session の pass/fail と emit 判定を 1 行出力。0-fire の原因 (dormant / filter落ち / 経路ブロック) が production ログで判別可能に。
- class 属性 dedup により engine 毎tick再構築でも同一バー 1 行 (3 variant 共有)。
- pre-reg 2026-05-28 に追補: 判定を「QUALBAR 数 (分母) vs 発火数 (分子)」の表に書換え。emit=True で発火ゼロなら R3 即時 forensic。
- prereg-trigger-registry に `t9-kalman-d7-fire-info` 追加 (prefix マッチ対応を watch tool に実装、BT 期待 3.9/週)。
- 影響トレード: なし (観測性のみ、シグナル判定・lot 不変更)。回帰: tests/test_kalman_d7_qualbar_logging.py (5) + prefix マッチ 1 件。

## 2026-07-06 — pre-reg トリガー監視の自動化 + env gate 宣言整合チェック (rule:R3)

- **tools/prereg_trigger_watch.py** (新規): 機械判定可能な pre-reg トリガー/決定点を registry (decisions/prereg-trigger-registry.json) で管理し毎日評価。Tier A daily cron (quant_gate_status.py) の Discord レポートに統合。初期登録 3 件: T5 復帰条件 (D1<159.50) / sweep P-S1(a) DEFER 決定点 (N≥10 or 09-30 N<5) / hull 頻度 band
- **scripts/check.py チェック8** (新規): demo_trader.py が読む `*_LIVE_ENABLE` env が render.yaml 未宣言なら WARN — decision-without-provisioning クラス (watchdog token / carry dip gate / T5 未執行の 3 例) の構造防止
- **render.yaml**: `KALMAN_D7_LIVE_ENABLE` / `USDJPY_CARRY_DIP_LIVE_ENABLE` を sync:false で宣言 (dashboard 値は不変更)
- 影響トレード: なし (監視・観測性のみ)。背景: T5 トリガーが監視主体不在で 18 日間未執行だった事故
## 2026-07-06 — T5 pre-reg 発動執行: JPYキャップ撤退 SIZE lever 0.5x (rule:R2)

- [[jpy-cap-exit-prereg-2026-06-12]] トリガー1「USD_JPY D1 close > 160.80」が **2026-06-18 に成立済み** (161.295、以降14営業日連続、max 162.631) と本日検出。18日の執行ギャップ (監視機構不在) — pre-reg 文書に発動記録+教訓を追記。
- 執行: `_resolve_jpy_cap_exit_size_lever` — 対象4戦略 (vsg_jpy_reversal / dt_sr_channel_reversal / vix_carry_unwind / ema200_trend_reversal) の **LIVE lot 0.5x** (SIZE lever、lot チェーン最後段)。Shadow 無変更 (原則3)。code pin (`JPY_CAP_EXIT_SIZE_LEVER_ACTIVE`、env/KV 経路なし) + 回帰テスト 5 件。
- **Floor 1000u**: vix Overlap pilot の 1000u 固定検証ロット契約 ([[vix-carry-grail-removal-overlap-1000u-2026-06-15]], agg-Kelly bypass の正当性根拠) と衝突するため `max(1000, 0.5x)` で適用 — 1000u 検証ロットは no-op、1000u 超のみ半減。
- 影響トレード: 以後の対象4戦略 LIVE 送信 lot が半減 (`(JPYCAP0.5x)` lot tag + trade_reason で識別可)。Shadow/BT 系列は不変。
- 復帰 = 復帰条件 (D1<159.50 回帰+介入再確認 / BOJ 後 clean N≥10 EV>0) の KB 記録 + テスト変更を伴う PR のみ。

## 2026-07-06 — T8 初週 R2 STOP: hull/sweep LIVE 転送を code pin で停止 (rule:R2)

- pre-reg [[sweep-hull-live-week1-prereg-2026-06-12]] 拘束ゲート抵触 (sweep=ゲート① 24日 fill 0 / hull=ゲート④ 同一バー再emit) → 裁量禁止条項に従い LIVE 転送停止。
- env フラグでなく `_*_LIVE_ENABLE = False` の code pin (lesson: KV disable は pin にならない)。Shadow は原則3で継続。
- 影響トレード: なし (両戦略とも live fill 実績 0)。復帰 = forensic 完了 + 再 LOCK PR のみ。
- 詳細: [[t8-week1-gate-breach-2026-07-06]]

## 2026-07-06 — rnb WAIT entry=0 恒常汚染の根絶 + QUALBAR print 化 (観測性 R3 バッチ)

- **rnb_usdjpy**: `compute_rnb_signal` WAIT dict の `entry: 0` (2026-04-05 起源) が PRICE_HISTORY_GUARD 発火 ~2,880件/日 の唯一の発生源と特定 → WAIT に実 Close を埋める 1 行修正。ガードの残発火が真の fetch 障害シグナルに戻る。
- **usdjpy_carry_dip QUALBAR**: `logger.info` は本番 handler 未設定で破棄されており T7 E2E 検証が構造的に不可能だった → `print(flush=True)` 化。
- 回帰: tests/test_rnb_wait_entry_price.py (3 cases)。影響トレードなし (シグナル判定・tier/lot 不変更、観測性のみ)。
- 詳細: [[rnb-wait-entry-zero-forensic-2026-07-06]]

## 2026-07-04 — Fable5 監査 Phase A バッチ: edge-cell DD mult / 孤児クローズ年齢ガード / strategy Kelly 汚染除去 (rule:R2+R3)

- **P0-1 (user 決裁)**: edge cell force-live の固定 lot に `max(1000, int(lot × _dd_lot_mult))` を適用。DD defensive 0.2x 下で stage3=10000u フル送信だったバイパスを封鎖、1000u floor でクリーン N 蓄積は継続。
- **P0-2**: `_sync_demo_to_oanda` 孤児クローズに `_ORPHAN_MIN_AGE_SEC=600` の openTime 年齢ガード (parse 不能も fail-safe skip)。再起動直後の正規 live ポジション誤クローズ競合窓を封鎖。
- **P1-1**: `_get_strategy_kelly` を `_get_strategy_kelly_clean` へ委譲 — 実弾サイジング 2 経路 (dynamic boost / half-Kelly cap) + shadow promotion の all-time 汚染 (pre-cutoff/XAU/shadow 混入) を除去。
- **影響トレード**: DD defensive 継続中の E2/E9 マッチが縮小サイズ (5000→1000u 等) で送信される。per-cell EV 評価は pips ベースのため非影響。Kelly boost/cap はクリーン N<10 戦略で不発化 (誤 boost の停止)。
- 回帰テスト 16 本を同コミットで追加。
- 詳細: [[fable5-phase-a-p0-fixes-2026-07-03]] / 監査 SSOT: [[fable5-system-audit-2026-07-02]]

## 2026-07-03 — _price_history 0価格ガード (spike/velocity gate 誤発火修正, rule:R3)

- P1 データ整合性バグ修正: fetch 全滅時の `current_price=0/None` が `_price_history`
  に混入し、spike gate が range=価格そのもの (07-02 12:31 UTC 実例: 16153.1pip/60s =
  USDJPY 161.53) で誤発火 → 当該 instrument **全戦略**の live 送信を 60s〜30min 封鎖
  (shadow-eligible は shadow 化、それ以外は drop) していた。
- 3層ガード: L1 append 前 `price>0` 検証 + `[PRICE_HISTORY_GUARD]` 検出ログ /
  L2 spike 計算側 `p>0` フィルタ / L3 velocity 計算側 `p>0` + current_price 有効時のみ評価。
- **影響トレード**: データソース障害と同期した spike/velocity の shadow 化・drop が本デプロイ
  以降消滅。07-02 12:31-13:42 の vix_carry_unwind 窓内 14/14 shadow はこのバグ起因
  (清浄データでの窓内 live 実証は依然 N=1)。正常 tick での spike/velocity 発火は不変。
  tier/lot 変更なし。
- TDD 8 cases: `tests/test_price_history_zero_price_guard.py`。
  詳細: [[zero-fire-diagnosis-carrydip-vix-2026-07-02]] §2.6

## 2026-07-03 — Watchdog CODE_PIN_SYNC: code pin と KV stage の自動同期

- watchdog に `CODE_PINNED_CELLS` (modules/edge_cell_promote.DISABLED_CELLS のミラー、CI equality テストで乖離固定) を追加。pin cell の KV stage!=0 を検出したら new_stage=0 を発行して同期 (rule:R3 整合性修正)。
- 動機: 2026-07-02 zombie incident で E4 KV が 1 に残置 (DECREMENT stage>=2 ガードのため自然回復しない)。「eligible と effective を区別する」教訓の恒久対応。
- **影響トレード**: なし。lot 決定は従来どおり code pin (`DISABLED_CELLS`) が支配し、本変更は KV 表示状態のみ同期する。
- 詳細: [[edge-cell-e1-e4-code-disable-2026-07-02]] 追記 2026-07-03

## 2026-07-02 — Edge cell E1/E4 code-level DISABLE + watchdog DECREMENT 床バグ修正

- `DISABLED_CELLS` に E1 (dt_bb_rsi_mr ASN SELL) / E4 (bb_rsi_reversion NY SELL) を追加 (rule:R2)。T10 KILL ([[bb-rsi-t10-kill-2026-07-02]]) 拘束事項3 の実施。
- **影響トレード**: E4 経由の bb_rsi_reversion live 発火 (2026-07-02 13:08-19:55 UTC の 11 件が最後) は本デプロイ以降ゼロ。E1 は LOCK 以降 live N=0 で実挙動不変。dt_bb_rsi_mr の通常 PAIR_PROMOTED 経路は不変。
- watchdog `max(1, stage-1)` 床バグ修正 (rule:R3) — stage=0 セルの 0→1 再武装 (zombie) を根絶。**2026-07-02 10:18Z〜デプロイまでの間、E4 の KV disable は 15 分毎に無効化されていた**点に注意 (該当 live 4 件は分析時に E4 force-live として扱う)。
- 詳細: [[edge-cell-e1-e4-code-disable-2026-07-02]]

## 2026-07-02 — Aggregate Kelly Gate raw-fix + 1000u 契約 min-lot bypass (rule:R3+R2)

- P1 死にゲート修正: `kelly_criterion` の `max(0,·)` クリップにより v9.0 SHIELD
  Aggregate Kelly Gate (`< 0` 判定) が構造的に発火不能だった。`full_kelly_raw`
  (非クリップ) を追加し `_get_aggregate_kelly` を raw 化。
- interplay (user 決裁): 1000u 固定契約 3 戦略 (vix_carry_unwind /
  usdjpy_carry_dip_accumulator / sweep_reversion_eurgbp_late) は
  allowlist AND 実効 units<=1000 AND 非XAU の二重ガードで gate bypass。
  hull_donchian_fade (5000u) は対象外。
- 影響: aggregate raw Kelly<0 (2026-07-02 時点 edge=-0.3617) の間、promoted
  非 sentinel/非 edge-cell/非 1000u契約 の OANDA 転送が初めて実ブロックされる。
  tier/lot 変更なし。TDD 10 cases。
- Decision: `decisions/agg-kelly-gate-raw-fix-minlot-bypass-2026-07-02.md`

## 2026-05-21 — SR-family shadow_emit OANDA audit restoration

- `shadow_emit_signals` が `_tick_entry` を経由せず `demo_trades` に直接 Shadow row を書くため、SR-family の OANDA audit skip row が欠落していた問題を修正。
- `sr_*` shadow emit は `demo_trades` 記録後に `oanda_audit` へ `bridge_status=skipped` / `block_reason=shadow_tracking` を永続化する。
- 対象は監視可視性の復旧のみ。OANDA 発注、Live/Shadow 判定、lot sizing は変更しない。

## 2026-05-18 — /api/oanda/stats range window 修正

- OANDA stats endpoint が frontend の `range=today|7d|30d|all` を無視して全期間集計していた問題を修正。
- 既定 window を demo stats と同じ 30d + `2026-04-08T00:00:00` floor にし、`range=all` も fidelity cutoff 以降のみ集計。
- `_filters` / `_db_path` を返し、stats 系 endpoint の表示条件を監査可能にした。

## 2026-05-18 — trend_rebound THESIS_INVALID FORCE_DEMOTED

- C audit verdict により `trend_rebound` を FORCE_DEMOTED に固定。
- 21d shadow N=60 WR=33.3% EV=-1.29p PF=0.66 Kelly=0.000 WF=0/3。
- `trend_rebound` x USD_JPY の PAIR_PROMOTED と EUR_USD の PAIR_DEMOTED を撤去し、
  FORCE_DEMOTED 一括管理へ統合。
- Decision: `decisions/trend-rebound-thesis-invalid-2026-05-18.md`。

## 2026-05-18 — HourlyEngine Shadow Ramp Activation

- 全 10 `daytrade_1h*` modes を `auto_start=True` に変更し、HourlyEngine dormant 状態を解除。
- `_shadow_always` に KSB+DMB+5 PriceShockRev を frozenset 固定し、H1 alpha source を一括 Shadow-only にした。
- XAU modes と 15m/scalp Live 経路は変更なし。Decision: `decisions/hourly-engine-shadow-ramp-2026-05-18.md`。

## 2026-05-18 — Price-Shock Rev Live Activation v2 MIN Lot (rule:R1)

- 5 Price-Shock Rev H1 戦略を Tier 2 Live MIN lot に移行。
- `_shadow_always` から Price-Shock Rev を削除し、KSB/DMB は Shadow-only 維持。
- Live lot は 1000u 固定。lot ramp は N>=30 pre-reg evaluator の提案のみで自動変更しない。
- N>=10 watchdog は EV<0 または Wilson_lower<0.40 で auto-demote state を記録。Decision: `decisions/price-shock-rev-live-activation-2026-05-18.md`。

## 2026-05-18 — Price-Shock Reversion Tier 1 Phase B-1 Shadow

- H1 negative shock LONG 5 戦略を `strategies/hourly/` に追加。
- BT runner と `shift(1)` / rolling 252 / vol quintile を bar-by-bar 一致。
- `demo_trader` で Shadow-only 強制、EUR_GBP/EUR_AUD shared lock を追加。
- Live promote は `decisions/price-shock-rev-promote-criteria-2026-05-18.md` で別判定。

## 2026-05-18 — PRIME v2 Apply

- PRIME v2 apply: 5 entries demoted to Tier C per P1 re-eval verdicts.
- EDGES replaced with the 2026-05-18 Render shadow non-XAU recomputation.
- All current PRIME matches remain Shadow-only; A/B live-lock structure preserved for future candidates.

## 2026-05-18 — PRIME B' Micro LIVE Forward-Fix

- Corrected the grade mismatch between LIVE promotion and Micro LIVE exploration.
- Revived `fib_reversal_PRIME` and `sr_fib_confluence_GBP_ADXQ2` as Tier B `0.05x` measurement cells.
- Kept the other 4 PRIME entries at Tier C `0.0`; no Tier A entries active.
- Existing watchdog safety net remains unchanged: auto-demote at Live `N>=10` and `EV<0`.

## Fidelity Cutoff Timeline

```
2026-04-02  システム稼働開始
     |
2026-04-08  ★ Fidelity Cutoff (v6.3 SLTP修正後)
     |       ├── この日以降のデータ = "クリーンデータ"
     |       └── 以前のデータ = "バグ汚染データ"（SLTPチェッカーバグ含む）
     |
2026-04-09  v7.3-v7.6: XAU修正チェーン
     |       └── XAUデータ: v7.5以前は MAX_SL_DIST=$0.20バグで汚染
     |
2026-04-10  ★★ v8.0-v8.3: 戦略大改革
     |       ├── v8.0: vol_momentum 2.0x, engulfing_bb停止, TREND_BULL遮断
     |       ├── v8.1: TREND_BULL MR免除
     |       ├── v8.2: orb_trap PAIR_PROMOTED, vol_momentum 1.0x
     |       ├── v8.3: 確認足フィルター（bb_rsi/fib/ema_pullback）
     |       └── v8.3以降のデータ = "確認足効果測定用"
     |
2026-04-10  ★★★ v8.4: XAU停止 + Shadow汚染除去
     |       ├── XAUモード停止: scalp_xau, daytrade_xau auto_start=False
     |       ├── get_stats() is_shadow=0 フィルター追加
     |       └── v8.4以降 = "FX-only クリーンデータ"
     |
2026-04-12  Knowledge Base構築
     |       └── 評価基盤の確立
     |
2026-04-12  ★ v8.5: 学術文献6新エッジ戦略 (全Sentinel)
     |       ├── session_time_bias, gotobi_fix, london_fix_reversal
     |       ├── vix_carry_unwind, xs_momentum, hmm_regime_filter
     |       └── 25論文ベース、DaytradeEngine 32戦略化
     |
2026-04-12  ★★ v8.6: 本番昇格 + モード再編
     |       ├── session_time_bias × 3ペア PAIR_PROMOTED (BT WR=69-77%)
     |       ├── london_fix_reversal × GBP_USD PAIR_PROMOTED (BT WR=75%)
     |       ├── london_fix_reversal × USD_JPY PAIR_DEMOTED (BT WR=28.6%)
     |       ├── xs_momentum × USD_JPY PAIR_DEMOTED (BT EV=-0.129)
     |       ├── scalp_eurjpy auto_start=False (friction/ATR=43.6%, 構造的不可能)
     |       ├── scalp_5m_eur + scalp_5m_gbp 新規モード追加 (5m摩擦改善)
     |       ├── 金曜/月曜ブロック全撤去 — 原則#1「攻める」準拠
     |       ├── GBPアジアセッション除外フィルター実装
     |       ├── DSR (Deflated Sharpe Ratio) 実装 — Bailey & Lopez de Prado (2014)
     |       └── BT/Live乖離分析: bb_rsi 25pp乖離の原因分解完了
     |
2026-04-12  v8.7: BT基盤強化
     |       ├── BT Friction Model v3 (Spread/SL Gate + RANGE TP + Quick-Harvest反映)
     |       ├── backtest-long DT/1H対応 (120-365日チャンクBT)
     |       └── BT/Live乖離: Scalp 14-27pp→5-10pp, DT 5.5-10pp→2-4pp (期待)
     |
2026-04-12  v8.8: 生データアルファマイニング
     |       ├── vol_spike_mr: 3x range spike fade (BT JPY PF=1.92, 全戦略最高)
     |       ├── doji_breakout: 3連続doji breakout follow
     |       ├── post_news_vol × USD_JPY PAIR_DEMOTED (120d WR=0%)
     |       └── ema200_trend_reversal × USD_JPY PAIR_DEMOTED (120d WR=0%)
     |
2026-04-13  ★★★ v8.9: Equity Reset — クリーンデータ起点
     |       ├── 旧DD: 2,899pip (289.9%) ← XAU(-2,280pip) + pre-cutoffバグ汚染
     |       ├── リセット: v8.4(2026-04-10T12:00)以降FX-only非Shadowで再計算
     |       ├── 新DD: 8.4pip (0.8%) → lot_mult=1.0x (フルロット)
     |       └── ワンショットマイグレーション (eq_reset_v89フラグで1回のみ実行)
     |
2026-04-17  ★ v9.2.1: MTF Regime Engine + v9.2 guardrail 無効化
     |       ├── D1×H4×H1 階層 regime labeler (7-class)
     |       ├── EUR_USD η² 105× improvement, flip rate 6.1%→0.6%
     |       ├── v9.2 guardrail デフォルト無効化 (6.5年検証で符号逆)
     |       └── shadow_monitor + DB mtf_* カラム追加
     |
2026-04-17  ★★ v9.3 Phase A-C: Strategy-aware MTF + P0 Family Map Forensics
     |       ├── Phase A: 戦略ファミリ考慮 retrospective (LIVE aligned WR +22.9pp)
     |       ├── Phase B: 本番OOS反実仮想 (+508p 改善) — TF sign flip 検出
     |       ├── Phase C P0: 3戦略 mislabel 修正 (macdh_reversal/engulfing_bb → TF, ema_cross → MR)
     |       ├── CORRECTED map で ALL Δ PnL +306p→+1129p (3.7×), 全family符号一致
     |       └── research/edge_discovery/strategy_family_map.py (production module)
     |
2026-04-17  ★★★ v9.3 Phase D+E: A/B Gate Routing + REGIME_ADAPTIVE
             ├── **Phase D**: Hash-based A/B routing (MD5 mod 2 → mtf_gated / label_only)
             │   ├── DB: gate_group / mtf_alignment / mtf_gate_action 追加
             │   ├── Group A conflict → LIVE→SHADOW downgrade (soft gate)
             │   └── 50/50 分布確認 (N=1000 ±50)
             ├── **Phase E**: REGIME_ADAPTIVE_FAMILY (regime別 family override)
             │   ├── bb_rsi_reversion: trend_up=TF / trend_down=MR
             │   ├── fib_reversal: trend_up=MR / trend_down=TF
             │   └── LIVE ΔWR +2.4pp→+9.3pp (4×), IS aligned gap +12.0pp
             └── Tests: 234 passed (new: test_ab_gate.py 7 + TestRegimeAdaptive 7)

2026-04-20  v9.3 Phase F: FAMILY MAP 拡張 — ELITE_LIVE/PAIR_PROMOTED 6戦略追加分類
             ├── **TF追加**: gbp_deep_pullback, trendline_sweep (wiki Category根拠)
             ├── **MR追加**: vwap_mean_reversion, wick_imbalance_reversion (wiki MR根拠)
             ├── **SE追加**: london_fix_reversal (Krohn 2024), vix_carry_unwind (Brunnermeier 2009)
             ├── 未分類→"unknown"から"conflict/neutral"へ: A/B gate が ELITE_LIVEにも機能するように
             ├── RANGINGレジーム下: gbp_deep_pullback/trendline_sweep → conflict → shadow降格（正常）
             ├── RANGINGレジーム下: vwap_mean_reversion/wick_imbalance_reversion → aligned（正常）
             ├── pending (BT forensics必要): doji_breakout, post_news_vol, squeeze_release_momentum
             └── Tests: 234 passed (既存テスト全pass、新分類はwiki根拠で実装)

2026-04-20  ★ v9.x Quant Readiness: 2D v2 Pre-Registration + Dashboard (parallel A+B)
             ├── **Task A — Regime 2D v2 Pre-Registration (data snooping 防止)**:
             │   ├── knowledge-base/wiki/analyses/regime-2d-v2-preregister-2026-04-20.md
             │   ├── 43戦略の family/regime×direction 仮説を backfill 前に pre-commit
             │   ├── Gate 閾値確定: N≥50/cell, |ΔWR|≥10pp, Bonferroni α=0.05/K, IS/OOS 符号一致
             │   ├── Pass/Fail 判定を機械化可能な形で記述 (§3.7)
             │   ├── 禁止事項 (§5): 閾値/仮説の事後調整, cell 除外の事後正当化, 1日データ実装
             │   ├── Bailey & Lopez de Prado (2014) *Backtest Overfitting* 流儀の pre-register
             │   └── Post-execution 記録枠を空のまま commit → data snooping 抑止
             ├── **Task A — Rescan script**: scripts/regime_2d_v2_rescan.py (~470行)
             │   ├── --trades-json input / --output-dir / --dry-run
             │   ├── Fisher's exact (two-sided, SciPy 非依存) + Bonferroni strict
             │   ├── matrix_all / asymmetry_strict / hypothesis_check / gate_candidates / sanity_check
             │   ├── 既存 REGIME_ADAPTIVE_FAMILY (bb_rsi/fib) の sanity check も同時実行
             │   └── Dry-run smoke test pass (synthetic 600 trades, k_eff=1)
             ├── **Task B — Quant Readiness Dashboard**: tools/quant_readiness.py (~340行)
             │   ├── --api / --json / default https://fx-ai-trader.onrender.com
             │   ├── Data accumulation (Live/Shadow N, Kelly progress)
             │   ├── Gate thresholds (Kelly N≥20, DSR N≥50, PP review N≥30+EV>0, FD-risk EV<-0.5)
             │   ├── mtf_regime coverage (labeled/total, regime diversity, missing list)
             │   ├── Alerts (Kelly/coverage/trend_down zero/FD-risk triggers)
             │   ├── セキュリティ: URL scheme allowlist + custom opener (HTTP/HTTPS のみ) →
             │   │   file:// / ftp:// 攻撃面遮断 (CWE-939), verified SSL context (CWE-295)
             │   └── 本番 smoke test: Live=14/20 (70% Kelly), Shadow=849, coverage=30.1% (target 80%)
             │       → trend_down_* 0件警告, backfill 前提の blocker 検出
             ├── **Tests**: tests/test_quant_readiness.py 13 cases
             │   └── URL validation (file/ftp reject), build_accumulation/gate/coverage, alerts, render
             ├── tier_integrity_check --check: PASS (ERROR=0)
             ├── strategies_drift_check: PASS (65 pages clean, exit 0)
             └── 判定プロトコル: **実装提案なし**. 本 commit は "infrastructure 整備" であり
                 backfill 後の 2D v2 rescan / daily readiness snapshot のための pre-commit.
                 実際の strategy 昇格・降格は backfill + N 蓄積後の human review を要求.

2026-04-20  ☆ v9.x Diagnostic: Regime × Strategy 2D Kelly Asymmetry Scan (NO-OP)
             ├── **目的**: 43戦略 × 7 regime × 2 direction の非対称性マトリクスを全探索
             │   └── Phase E (bb_rsi_reversion / fib_reversal) 同等候補があれば REGIME_ADAPTIVE 追加
             ├── **データ**: 本番 API N=786 (Cutoff 2026-04-16以降 / XAU除外 / closed)
             │   └── mtf_regime 本番 DB populate 率 24.5% → research/edge_discovery/mtf_regime_engine で
             │       retrospective labeling (Phase B 済み pipeline 再利用) で 100% カバー
             ├── **結果**: Gate 通過候補 = **0件**
             │   ├── 観測期間 4.6日 → lesson-reactive-changes "1日データ禁止" に抵触
             │   ├── Regime coverage 欠損 (trend_down_* / uncertain が 0 件)
             │   ├── 43戦略中 N≥50/cell を 1つ以上持つのは ema_trend_scalp のみ
             │   ├── Bonferroni α=0.0125 で有意 cell ゼロ (最小 p=0.277)
             │   └── 観測された方向非対称性は全て既存 strategy_aware_alignment で処理済
             ├── **実装**: なし (判断プロトコル #1 違反回避)
             ├── **別 task 提案**: scripts/backfill_mtf_regime.py 作成 → 過去トレードに mtf_regime 注入 → N ≈ 1500+ 規模で再評価
             └── Artifacts: knowledge-base/wiki/analyses/regime-strategy-2d-2026-04-20.md
                 + /tmp/fx-regime-2d-analysis/{matrix_all,asymmetry,asymmetry_strict}.csv

2026-04-20  ★ v9.4: wiki/strategies KB ドリフト一掃 + 検出ツール導入
             ├── 13 ページの Status 行を tier-master.json と整合
             │   ├── bb-rsi-reversion.md: "Tier 1 PP×USD_JPY" → SCALP_SENTINEL + PAIR_DEMOTED(全4ペア)
             │   ├── orb-trap.md: "Tier 1 PP×3ペア" → FORCE_DEMOTED (v9.1 負EV確定)
             │   ├── trendline-sweep.md: "ELITE+FD+PP" → ELITE_LIVE のみ (v9.0 整理)
             │   ├── bb-squeeze-breakout / engulfing-bb / sr-channel-reversal / ema-pullback:
             │   │   FD下のPP死コード記述を削除 (v9.1 cleanup 反映)
             │   ├── london-fix-reversal: "PP×GBP" → Phase0 Shadow (v9.1 GBP PP削除)
             │   ├── vol-momentum-scalp: "SHADOW" → PAIR_PROMOTED×EUR_JPY
             │   ├── three-bar-reversal: "UNI_SENTINEL" → Phase0 Shadow
             │   ├── stoch-trend-pullback: "Sentinel" → FORCE_DEMOTED (v8.9 剥奪)
             │   ├── vol-surge-detector: "Sentinel" → SCALP_SENTINEL + PAIR_DEMOTED
             │   ├── doji-breakout: Status追加 (UNI_SENTINEL + PP×GBP/USDJPY)
             │   ├── fib-reversal: "Tier 2" → FORCE_DEMOTED (Recovery Path active)
             │   ├── liquidity-sweep: "Tier 2 Sentinel" → UNIVERSAL_SENTINEL 明示
             │   ├── post-news-vol: Status 行の USD_JPY をPP→PAIR_DEMOTED に訂正
             │   └── dual-sr-bounce: "FORCE_DEMOTED" → REMOVED (v9.1 死コード削除)
             ├── 旧 Status は「履歴」/「Previously ...」で保持 (削除禁止ルール遵守)
             ├── **新ツール**: tools/strategies_drift_check.py
             │   ├── tier-master.json を truth source として読み込み、md の Status 行を検証
             │   ├── 否定コンテキスト / 履歴マーカーはスキップ
             │   ├── PAIR_PROMOTED scope 内のペアのみ truth と突合
             │   └── exit 1 で pre-commit / CI 組み込み可能
             ├── **テスト**: tests/test_strategies_drift_check.py (11 cases, all pass)
             │   └── 実 KB 回帰テスト込み (test_live_kb_passes_drift_check)
             ├── **lesson**: wiki/lessons/lesson-strategies-page-drift.md
             │   └── lesson-kb-drift-on-context-limit の strategies/ 特化版
             └── 独立ツール設計: tier_integrity_check.py (code 整合) と分離
                 pre-commit 実行順: tier_integrity_check --write → strategies_drift_check

2026-04-20  ★ v9.x Priority 3: Sentinel N 測定バグ修正
             ├── **症状**: UI で 62 戦略中 bb_squeeze_breakout のみ N=1、他 61 戦略 N=0
             │   └── 実測: 本番 DB に closed Shadow trades が 1,466 件存在
             ├── **原因**: `get_trades_for_learning` は is_shadow=0 固定フィルタ
             │   └── `_strategy_n_cache` → `_build_strategy_status_map` の n が Live のみに
             ├── **修正**: `get_shadow_trades_for_evaluation()` 新関数 (is_shadow=1 固定)
             │   ├── `_build_strategy_status_map` に shadow_n/wr/ev 付与
             │   ├── `/api/sentinel/stats` 新設 (entry_type/instrument/after_date フィルタ)
             │   └── `get_trades_for_learning` は**変更なし** (lesson-shadow-contamination 維持)
             └── Tests: 244 passed (new: test_shadow_stats.py 10 = 正例4+負例3+空3)
             参照: [[lesson-sentinel-n-measurement-bug]]

2026-04-20  ★ v9.x Priority 1: Sentinel score_gate バイパス (Clean Slate 窒息対策)
             ├── **背景**: Clean Slate(2026-04-16)以降 Live N=0 / Sentinel N=1(bb_squeeze_breakout only, 62戦略中)
             │   └── score_gate(score<0) が 1日396件ブロック → Sentinel shadow も蓄積不能
             ├── **修正**: demo_trader.py L2761 score_gate に `_sentinel_score_bypass` 追加
             │   ├── SCALP_SENTINEL ∪ UNIVERSAL_SENTINEL のみバイパス (Live 挙動不変)
             │   ├── FORCE_DEMOTED / _ELITE_LIVE / _PAIR_PROMOTED は従来通り score_gate 適用
             │   └── L4179 safety net で is_shadow=True 強制 → 学習汚染リスクゼロ
             ├── **観測性**: Sentinel バイパス時 `[SCORE_GATE] Sentinel bypass:` ログ発行
             ├── **対称性**: spread_wide(L3483) / spike(L3522) と同形パターン
             └── Tests: 234 passed (no new tests — 既存挙動 guard のみ)
             注記: P3 実測で Sentinel N=1,466 判明 → 「N=1」は測定バグ由来。本 bypass は純粋な上振れ策として残存有効。

2026-04-20  ★ v9.x Priority 2: PAIR_PROMOTED SSOT drift 修正 (accounting cleanup)
             ├── demo_db.py `_pair_promoted_overrides` 5 組合せを削除
             │   ├── (ema_pullback, USD_JPY), (fib_reversal, EUR_USD)
             │   ├── (bb_squeeze_breakout, USD_JPY/EUR_USD), (sr_channel_reversal, EUR_USD)
             │   └── 全て v9.1 で demo_trader._PAIR_PROMOTED から既に削除済み → SSOT 二重化解消
             ├── Live 監査 (Render DB, 2046 trades):
             │   ├── fib_reversal×EUR_USD: Live N=51 WR=39% EV=-0.298 PnL=-15p (post 4/7)
             │   ├── bb_squeeze×EUR_USD: Live N=26 WR=11.5% EV=-2.32 (**壊滅**)
             │   ├── sr_channel×EUR_USD: Live N=26 WR=19% EV=-1.20 (**壊滅**)
             │   └── 他 2 組は Live N<20 & Shadow 主体 → 昇格根拠不足
             ├── 365d BT 再検証 Gate: 全 5 組合せが EV≥+0.2 ATR & N≥100 を満たさず
             ├── 60d→180d 符号反転: fib_reversal×EUR_USD (+0.271 → -0.147) — lesson-orb-trap 再現
             ├── 新規 PAIR_PROMOTED 追加: **なし** (Gate 通過候補ゼロ)
             ├── **Retroactive effect**: 起動時 SHADOW_MIGRATION で 66件が is_shadow=0→1 化
             │   └── Kelly プールから stale 負EV trades 除去 → aggregate EV 改善見込み
             ├── **Behavioral change**: なし (5 組合せは既に Live 未送信、shadow 扱い)
             └── 詳細: wiki/analyses/pair-promoted-candidates-2026-04-20.md

2026-04-20  🚨 v9.x Hotfix: resend-shadow-leak — FORCE_DEMOTED が OANDA 実弾送信されるバグ修正
             ├── **症状**: is_shadow=1 の open trade に oanda_trade_id が設定されている
             │   ├── sr_channel_reversal USD_JPY (FORCE_DEMOTED) → oanda_trade_id=320787
             │   ├── orb_trap GBP_USD (FORCE_DEMOTED) → oanda_trade_id=318111
             │   ├── bb_rsi_reversion EUR_USD (PAIR_DEMOTED) → oanda_trade_id=325370
             │   └── vwap_mean_reversion GBP_USD (MTF gate shadow降格) → oanda_trade_id=325362
             ├── **原因**: `_resend_pending_oanda_trades()` (起動時実行) が
             │   `get_open_trades_without_oanda()` を呼ぶ際に `is_shadow` を未フィルタ
             │   → 起動/OANDA再接続時に is_shadow=1 trades も OANDA に送信されていた
             ├── **修正**: `demo_db.py` `get_open_trades_without_oanda()` のSQL に
             │   `AND is_shadow=0` 追加 (1行) → shadow trades は resend 対象外
             └── **lesson**: [[lesson-resend-shadow-leak]]

2026-04-20  ★ v9.5: ema_trend_scalp / trend_rebound Live pair-level breakdown + PAIR_DEMOTED 拡充
             ├── **背景**: Post-P2 Kelly 分析で ema_trend_scalp edge=-0.353 / trend_rebound edge=-0.455
             │   が aggregate edge=-0.1348 の主因と判明 ([[shadow-baseline-2026-04-20]] Phase 2)
             ├── **Live pair-level 実測** (Render prod, is_shadow=0, closed):
             │   ├── ema_trend_scalp: USD_JPY N=19 EV=-0.92 / EUR_USD N=16 EV=-1.22 / GBP_USD N=4 EV=-1.65
             │   ├── trend_rebound:   USD_JPY N=10 EV=-0.78 / EUR_USD N=7 EV=-1.43 / GBP_USD N=1
             │   └── 99% は Fidelity Cutoff (2026-04-16) 以前、v9.2 FORCE_DEMOTE 以降は新規発生なし
             ├── **Shadow↔Live 対照で符号逆転検出** — lesson-orb-trap-bt-divergence 再現:
             │   ├── trend_rebound×USD_JPY: Shadow EV=+1.43 (N=12) → Live EV=-0.78 (N=10)
             │   └── trend_rebound×EUR_USD: Shadow EV=+1.16 (N=7) → Live EV=-1.43 (N=7)
             ├── **Gate (N≥10 ∧ EV≤-0.5 ∧ (WR≤20 ∨ PnL≤-10)) 通過**: 2 combos
             │   ├── ema_trend_scalp×USD_JPY (PnL=-17.5 で PnL criterion 通過)
             │   └── ema_trend_scalp×EUR_USD (既に PAIR_DEMOTED)
             ├── **修正 1**: demo_trader._PAIR_DEMOTED に `(ema_trend_scalp, USD_JPY)` 追加
             │   ├── v8.9 で "SELL PB境界バグ修正済み → 再蓄積" として解除されていたが
             │   │   v9.2 FORCE_DEMOTE で "再蓄積" 方針は無効化。documentation marker として記録
             │   └── 挙動変化なし (strategy が既に FORCE_DEMOTED で OANDA 遮断済)
             ├── **修正 2**: demo_db._force_demoted (shadow migration set) の SSOT drift 修正
             │   ├── demo_trader._FORCE_DEMOTED (18) と demo_db._force_demoted (15) が drift
             │   ├── 欠落: ema_trend_scalp, intraday_seasonality, atr_regime_break
             │   ├── → 起動時 migration で is_shadow=0 残留 trades (ema_trend_scalp Live N=39 等)
             │   │   が shadow pool 化されず Kelly を汚していた bug
             │   └── 修正後、次回起動時 migration で stale Live trades が shadow 化
             ├── **保留**: trend_rebound×USD_JPY (WR=30% PnL=-7.8 で Gate 微不通過、監視継続)
             │   └── 次 Live N≥20 到達時に再判定。lesson-reactive-changes 遵守で反射降格なし
             ├── Validations: tier_integrity_check ERROR=0, strategies_drift_check pass
             └── 詳細: wiki/analyses/ema-tr-live-breakdown-2026-04-20.md
```

2026-04-22  v9.x: TP-hit Quant Analysis (research only, no code change)
             ├── **スコープ**: 全 strategy × pair で TP-hit したトレードの再現性を定量化
             ├── **データ**: `/api/demo/trades?limit=5000` → 非XAU closed 2,267 / WIN 698
             ├── **Phase 1**: Strategy×pair, regime, TF, session, MTF alignment で WR セグメント化
             │   └── 最多 TP-hit = bb_rsi_reversion×USD_JPY (N=127、全 WIN の 18.2%)
             ├── **Phase 2**: TP-hit vs LOSS の feature 分布差 (Mann-Whitney U, Bonferroni)
             │   ├── spread_at_entry: WIN=0.763 < LOSS=0.842 (p=1.94e-5, 有意)
             │   ├── confidence: WIN=59.55 < LOSS=61.16 (負相関, p=1e-3)
             │   └── score: p=0.42 (score_gate は TP-hit 予測力ゼロ)
             ├── **Phase 3-4**: 事前予測可能特徴のみ (post-hoc MAFE 除外) で条件マイニング
             │   ├── 候補 m=107、Bonferroni α=4.7e-4 通過 5 件
             │   └── 高 WR だが 4/5 は Kelly<0 (BEV 押し上げ vs friction キャンセル)
             ├── **Phase 5 安定性** (pre/post cutoff × live/shadow 符号一致):
             │   ├── **最 robust**: bb_rsi_reversion×EUR_USD×BUY (WR 64.5%, EV +1.84 pip,
             │   │   Kelly +0.41, 4/4 window 符号一致) — ただし N=31 境界
             │   └── **最 fragile**: bb_rsi_reversion×USD_JPY×RANGE
             │       pre EV +0.16 → post EV -1.56 (1.7 pip 悪化、[[lesson-orb-trap-bt-divergence]] 再現)
             ├── **DSR 警告**: Bonferroni 通過 5 件は帰無仮説下 FP 期待値 5.4 とほぼ同 → 
             │   family-wise シグナルは弱い、個別採択は stability で決定すべき
             ├── **制限**: Post-cutoff Live N=0、shadow は truncated sample bias 残存、
             │   close_reason 6種(TP_HIT/OANDA_SL_TP/SIGNAL_REVERSE/...)を包括
             ├── **実装提案なし** ([[lesson-reactive-changes]] 遵守) — KB 記録のみ
             └── 詳細: wiki/analyses/tp-hit-quant-analysis-2026-04-20.md,
                 raw/analysis/tp-hit-raw-2026-04-20.csv, scripts/analyze_tp_hits.py

2026-04-22  ★ v9.x: Roadmap-acceleration 二重WF確証による PAIR_PROMOTED 昇格 2件
             ├── **スコープ**: クロスTF walk-forward stability で pos_ratio=1.00 を示した
             │   2セルを Phase0 auto-Shadow / 既存PP未指定 → PAIR_PROMOTED 昇格
             ├── **`streak_reversal × USD_JPY` PAIR_PROMOTED 新規**
             │   ├── P2 15m 365d × 20d window WF (18窓): N=466 EV=+1.362 pos=1.00 CV=0.65 ✅
             │   ├── P4 5m  180d × 30d window WF (7窓):  N=693 EV=+0.948 pos=1.00 CV=0.62 ✅
             │   ├── Bonferroni BT: 5streak BUY N=586 WR=58.7% p=1.3×10⁻⁵
             │   └── 単一TF根拠を超えたクロスTF確証 → 従来 Phase0 inline auto-Shadow を解除
             ├── **`vwap_mean_reversion × USD_JPY` PAIR_PROMOTED 追加**
             │   ├── P4 5m 180d × 30d WF: N=155 EV=+0.925 pos=1.00 CV=0.51 ✅ (最低CV)
             │   ├── 既存PP (EUR_JPY/GBP_JPY/EUR_USD/GBP_USD) に USD_JPY を追加、5ペア化
             │   └── BT 15m 16bar: N=705 WR=55.0% EV=+2.98pip annual +2,099pip
             ├── **根拠プロトコル**: 両セルとも P2(15m)+P4(5m) 二重 WF クロスTF + Bonferroni BT。
             │   lesson-orb-trap-bt-divergence (短期60d BT のカーブフィッティング) を回避するため
             │   365d WF を一次根拠、5m 180d WF を二次確証、単一TF根拠を超える水準を要求した
             ├── **Validations**: tier_integrity_check.py --check ERROR=0 (PP 15→17 entries)、
             │   sync_kb_index.py --write で index.md portfolio セクション更新
             ├── **KB同梱**: wiki/strategies/streak-reversal.md / vwap-mean-reversion.md Status 更新
             │   (lesson-strategies-page-drift / lesson-kb-drift-on-context-limit 遵守)
             └── 詳細: raw/analysis/roadmap-acceleration-synthesis-2026-04-22.md,
                 raw/bt-results/walkforward-365d-w20-usdjpy-2026-04-22.md,
                 raw/bt-results/walkforward-scalp-5m-180d-2026-04-22.md

## バージョン別データ切り口

| 目的 | date_from | 除外条件 | 理由 |
|------|----------|---------|------|
| 全体傾向 | 2026-04-08 | is_shadow=0 | Fidelity Cutoff後クリーンデータ |
| **v8.3確認足効果** | **2026-04-10** | is_shadow=0 | v8.3デプロイ後のみ |
| **XAU停止効果** | **2026-04-10 夕方〜** | is_shadow=0, XAU除外 | v8.4デプロイ後 |
| **FX純粋評価** | 2026-04-08 | is_shadow=0, XAU除外 | FXのみの真のパフォーマンス |
| BT/ライブ比較 | 全期間 | なし | BT乖離幅の把握 |

## 各バージョンの影響範囲

### v7.x (2026-04-09): XAU修正チェーン
| Version | Change | Affected Strategies | Affected Data |
|---------|--------|-------------------|---------------|
| v7.3 | gold PBルーズ化+bbσバグ修正 | gold_trend_momentum | XAU DT |
| v7.4/b/c | extreme_momentum: ADX≥25, MACD-H/EMA9免除 | gold_trend_momentum | XAU DT |
| v7.5 | MAX_SL_DIST: XAU $0.20→$100 | **全XAU戦略** | ★ v7.5前のXAU SLデータは全て汚染 |
| v7.6 | Sentinel units: XAU 1000u→1u | XAU OANDA連携 | XAU audit |

### v8.x (2026-04-10〜): 戦略大改革
| Version | Change | Impact on Data |
|---------|--------|---------------|
| v8.0 | vol_momentum 2.0x, TREND_BULL全遮断 | DT TREBULLトレード消滅 |
| v8.1 | MR免除 (dt_bb_rsi_mr, dt_sr_channel_reversal通過) | DT MRトレード復活 |
| v8.2 | orb_trap PAIR_PROMOTED, vol_momentum 1.0x, bb_squeeze停止 | orb_trap OANDA送信開始 |
| **v8.3** | **確認足(bb_rsi/fib/ema_pullback)** | **★ 即死率の変化を測定する基準点** |
| **v8.4** | **XAU停止 + Shadow除去** | **★ FX-onlyの真のPnLを測定する基準点** |
| v8.5 | 学術文献6新エッジ戦略 (全Sentinel) | 新戦略のライブデータ蓄積開始 |
| **v8.6** | **session_time_bias/london_fix PROMOTED + 5mモード拡張 + DSR実装** | **★ 学術エッジの本番検証開始** |
| v8.7 | BT Friction Model v3 + backtest-long | BT信頼性向上 (乖離幅縮小) |
| v8.8 | vol_spike_mr + doji_breakout + PAIR_DEMOTED追加 | 新アルファ源 + 出血戦略停止 |

## Related
- [[edge-pipeline]] — エッジ仮説の評価はどのデータ期間を使うべきか
- [[independent-audit-2026-04-10]] — "Shadow除去なしにWR/EVは信頼できない"
- [[bb-rsi-reversion]] — WR 52.2% vs 34% の矛盾はデータ期間の差
- [[friction-analysis]] — avg_friction 7.04 は XAU込み。FX-only≈2.5pip
2026-05-04  FX Nexus Step 1 pre-reg and shadow audit scaffolding
             ├── Added FX graph MLE currency value and triangular alpha residual data-layer functions.
             ├── Added opt-in `exec_lag_jitter` timing audit path for DT backtests; default remains 0.0.
             ├── Added `tools/fx_nexus_shadow_audit.py` to produce H1/H2/H3 verdict markdown.
             └── Locked Step 1 criteria in `wiki/decisions/fx-nexus-step1-prereg-2026-05-04.md`.
