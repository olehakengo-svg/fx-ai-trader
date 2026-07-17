# Changelog — バージョン別変更と評価基準日

## なぜこのページが重要か
定量評価は「いつからのデータを使うか」で結論が180度変わる。
各バージョンの変更が**どのトレードに影響するか**をここで追跡する。

## 2026-07-17 — fix(research): E1 ハーネス敵対的レビュー修正 — fatal 2 系統 (look-2 着地 / health 時系列) + major 6 + minor (rule:R3)

- **[[e1-positioning-contrarian-prereg-2026-07-16]] 判定器への敵対的レビュー (spec/leak/stats 3 レンズ、fatal 3 [実質 2 系統] / major 6 / minor 10) を全件処置**。pre-reg 本文は不変更 (LOCK 遵守)
- **F1 (look-2 着地違反)**: `overall_verdict()` が look を知らず second look で C3 → 禁止された `UNDERPOWERED` (= 第 3 look 示唆) を返していた → look=2 では **PASS / REJECT-F / REJECT のみ** に写像 (C3/C2/C5→REJECT、C4→REJECT-F、UNDERPOWERED 到達不能化 = α 会計 q₁+q₂≤0.10 の保証回復)。look=2 × C3 → REJECT / 着地集合の pin テスト追加
- **F2 (health 時系列インフラ、§6-7「estimand を宣言どおりにする運用修理」)**: §2.2 stale cap 主モードが要求する per-instrument verified **時系列**が、本番 `positioning_health` の 1 行 upsert から構造的に得られなかった → (1) `positioning_health_log` append テーブル新設 + `record_health()` が**同一トランザクション**で追記 (~940 行/日)、(2) `/api/positioning/export?table=health_log` read-only export 経路、(3) ハーネス `--verdict-run` は verified 系列欠落で fail-loud 拒否 (明示 `--fallback-mode` でのみ続行)、結果 JSON に `stale_cap_mode: primary|fallback` を必ず記録、fallback 時は §2.2 必須診断 (2h-cap NA の NY 時間帯分布) を併記し**閑散帯集中 → DEFERRED を機械接続** (事前固定分岐、閑散帯 = NY 17:00–03:00 / 総数≥50 / 集中倍率 2.0 を観測前固定)
- **major**: (a) gate2 点推定を全 6 combo 常時計算 — look=2 でナイフエッジ #2(ii) 隣接 combo 参照が機械 FAIL する偽 REJECT バイアスを修復 (`gate2_all_combos` で透明化)、(b) C1/PASS 経路の end-to-end pin — 埋め込み強 contrarian シグナル合成世界で **verdict=PASS/C1 に実到達**する統合テスト (knife 4 点 / confirmatory / Stage B / Gate1+2) + confirmatory 4 分岐・partial IC・S2 lag・S3 pain 式の単体 pin、(c) canary に rank 窓 (strictly trailing / t 非包含) + mid 経路 (確定 bar 限定) の注入点と rank→IC 貫通の検出感度チェックを追加 (リーク rank 実装が fail することを pin — §6-4 委譲の空洞化を修復)、(d) primary parquet 欠落の無言 family 縮小を封鎖 (`--verdict-run` で 13 ペア完備必須、欠落リスト表示で拒否)
- **minor**: verified key の book 成分検査 (outlook 限定) / im_test se=0 の符号盲目 p=0 修正 (逆符号→p=1) / CONFIRMATORY_UNTESTED フラグを C1 限定化 (C2〜C5 汚染除去) / 量子化粒度をペア×統計毎 (S1/S2/S3) に記録 / Stage B 実行条件を c1_candidate (Gate1+2 通過) に拡張 / parquet cutoff 切詰めの機械クリップ + 件数記録 (切詰め規約非依存) / LOCF resampler の DST 跨ぎ週 (2026-11-01) unit test / MBB 全ペア同時 day-draw の pin / **day-block「観測日 index」規約の宣言** (Gate 2 の疎 trade 日で暦 5 営業日と乖離 — LOCK 字義の解釈変更を避け、実装ノートとして verdict JSON (`block_basis`) と本 changelog に宣言。変更でなく宣言で処置した唯一の項目)
- tests 118→160 (E1 96 + ingest 64、全 offline/合成)。**評価への影響: なし** — 判定器 + read-only export 経路 + append テーブルのみ。live 発注経路・戦略・Kelly・shadow 一切不変。verdict 期日 (2026-10-15) の実データ初適用前に修正完了

## 2026-07-17 — feat(research): E1 pre-reg 判定ハーネス実装 — LOCK 後成果物 (rule:R3)

- **[[e1-positioning-contrarian-prereg-2026-07-16]] §7 成果物規定の実装**: 判定器 `tools/e1_positioning_prereg_eval.py` (2,250 行、LOCK 後実装・seed 固定 `SEED_DEFAULT=20261015`)。§7 の規定どおり **LOCF resampler / rank タイ規約 (mid-rank §3.1) / DST 跨ぎ週 (2026-11-01) / ATR (NY17 roll 完結 bar) / OHLCV join 契約 / canary leak test を `tests/test_e1_prereg_eval.py` (58 tests) に pin してから verdict データに触れる**体制を確立
- 実装範囲 = §2.2 市場時間 (America/New_York DST 追随) + LOCF/stale cap (verified 基準)/cycle 証跡、§2.3 join/前方リターン/ATR14d/censoring、§2.5 品質 gate (coverage/stale gap/family postpone/sanity/jump detector 前方+24h)、§3 シグナル 3 本 × rank/hysteresis/金曜窓/年末窓、§4.1 Gate1 (営業日 MBB L=5 B=10k 全ペア同時 + Ibragimov–Müller df=7、p=max、BH q=0.05 m=6)、§4.2 Gate2 (day-block bootstrap、N<60 は点推定分類)、§4.4 C1〜C5 排他分類 + SIGN-FLIP/CONFOUNDED (partial IC)、§4.5 ナイフエッジ 4 点、§2.4 confirmatory 複製検査、§4.3 Stage B、§4.6 Secondary
- **構造的強制 (§6-1/6-2)**: 入力 = 凍結 export artifact + parquet のみ (本番 API/DB 経路をコードに含めない)。synthetic 宣言のない artifact は `--verdict-run` フラグなしで拒否。family gate postpone 時は統計段を一切実行しない (look 非消費の機械化)。canary suite green が verdict 実行の前提条件
- **実データ接触なし — テスト・dry-run は 100% 合成データ** (§6-2「実データへの初適用は verdict 期日 2026-10-15」遵守)。tests 60→118 (58 追加、全 offline/deterministic)。**評価への影響: なし** — 研究ツール + テストのみ、live 発注経路・戦略・Kelly・shadow 一切不変

## 2026-07-16 — feat(research): E1 positioning contrarian pre-reg DRAFT + positioning_health 永続化 + D4 テンプレート (rule:R3)

- **[[e1-positioning-contrarian-prereg-2026-07-16]] (DRAFT)**: 文献駆動・**データ観測前** pre-reg — discovery 2 段階を省き、first look verdict を **2026-10-15** (cutoff = t0+12週) に固定。従来計画 (2-3ヶ月蓄積 → discovery → 凍結 → OOS) 比で **verdict を 1〜2 ヶ月前倒し**。設計 = 8-agent workflow (独立3案 → 統合 → 敵対的レビュー major 11 反映)。階層ゲートキーパー (pooled IC 二重検定 → 摩擦調整 EV conjunction、look 毎 BH q=0.05)、UNDERPOWERED second look (2027-01-06) 事前固定。LOCK 決裁期限 2026-07-17 (registry `e1-prereg-lock-decision-stale`)
- **positioning_health テーブル (pre-reg §2.2 必須インフラ)**: per-instrument `verified:` 時刻 + `last_cycle_at` heartbeat を DB 永続化 — dedup skip (行を書かない) と fetch 失敗の識別を可能にし、LOCF stale cap の活動条件付けバイアスを排除。status API に `health` 露出。詳細: [[e1-positioning-ingest-2026-07-14]] §13
- **[[d4-implementation-prereg-template-2026-07-16]]**: survivor 到達時に即起案できる D4 実装 pre-reg 雛形 (carve-out 2 択 / R2 自動降格 / セル単位判定 / parity / 防御解除ラダー) — 直列待ちの前倒し削減
- tests 56→60。**評価への影響: なし** — read-only 計測基盤 + 文書のみ。live 発注経路・戦略・Kelly・shadow 一切不変

## 2026-07-16 — feat(data): E1 instrument 拡張 6→13 — 将来セル候補の蓄積 clock を前倒し開始 (rule:R3)

- **動機 (最短経路)**: history は今から蓄積する以外に入手不可 (§8c 確定) → 将来ペアの clock は今日始めた分だけ discovery が早まる。outlook は全 symbol 一括 1 リクエスト (probe: n_symbols=186) のため **API 予算コストゼロ**、増分は DB ~940 rows/日のみ
- **追加 7 ペア**: AUD_USD / NZD_USD / USD_CAD / USD_CHF / NZD_JPY / EUR_AUD / EUR_GBP (engine モード/Phase B-1 slot 既存の取引可能ペア)。ペア別 t0 が異なる点を pre-reg 窓設計の必須参照事項として記録。詳細: [[e1-positioning-ingest-2026-07-14]] §12
- **評価への影響: なし** — read-only データ収集の対象拡張のみ。live 発注経路・戦略・Kelly・shadow 一切不変

## 2026-07-16 — fix(data): E1 defer_thread — import 時 network thread 起動の廃止 (第2修正, rule:R3)

- **背景**: §10 修正後も serving プロセスの healed thread がハング (master の cycle は成功 = t0 蓄積開始済み)。帰属 = fork 瞬間に master thread が HTTP 実行中 → socket/ssl 内部 lock が locked のまま複製 (Session 再生成では直らない)
- **根治**: `start_positioning_ingest(defer_thread=True)` — master では thread を起動せず、serving プロセスの初回 heal (§8b) を唯一の起動経路に一本化。status に `current_phase`/`phase_since` 追加 (ハング位置の直接観測)。詳細: [[e1-positioning-ingest-2026-07-14]] §11
- tests 54→56。**評価への影響: なし**

## 2026-07-16 — fix(data): E1 Myfxbook client 2バグ修正 — session 二重エンコード + fork-unsafe HTTP Session (rule:R3)

- **背景**: user が credentials 投入 (05:54Z) → 初回稼働で "Invalid session." + healed thread ハングを実証
- **(a)**: Myfxbook session は発行時点で URL-encoded 済み — params= 再エンコードが二重化。`_get` を組立済み query 方式へ (session は raw 付加)。**(b)**: fork 継承 requests.Session の pool lock が locked のまま複製されハング — pid 変化検知で lazy 再生成。詳細: [[e1-positioning-ingest-2026-07-14]] §10
- 修正版で実 API 検証済み (186 symbols / 対象 6 ペア全取得)。tests 51→54 (回帰 pin 3)
- **評価への影響: なし** — read-only データ収集の修正のみ

## 2026-07-15 — feat(data): E1 ソース転換 — Myfxbook Community Outlook aggregate 版 (オプション A 採択, rule:R3)

- **決裁**: user 全面委任 (2026-07-15「最短がオーダーなので、やり方は任せる」) の下で §8c オプション A 採択。B (practice) は期待値低で保留、C (有償) はコスト非対称、D (閉鎖) は唯一の主戦線を閉じる理由なし。詳細: [[e1-positioning-ingest-2026-07-14]] §9
- **何を**: `modules/myfxbook_client.py` (新規、login/session/re-login、secrets 非開示 pin) + `positioning_ingest.py` ソース抽象 (`POSITIONING_SOURCE` 明示 > MYFXBOOK_EMAIL/PASSWORD 自動検出 > oanda default)。book_type=`outlook`、near_imbalance=NULL (bucket 級放棄の明示)、raw payload を buckets_json に JSON object で温存、content-hash dedup (sha256、snapshot_time は fetch 時刻 μs 精度)、poll ≥900s clamp (rate limit 100 req/24h)
- **受け入れ確認**: `/api/positioning/probe?run=1&source=myfxbook` (login+outlook 1回)。export API は book=outlook を受理
- **user アクション (E1 稼働の唯一の依存点)**: Myfxbook 無料 account 作成 → Render env に `MYFXBOOK_EMAIL`/`MYFXBOOK_PASSWORD` 投入 (§9 手順)
- **評価への影響: なし** — live 発注経路・戦略・Kelly・shadow 一切不変。read-only データ収集のソース交換のみ。tests: test_positioning_ingest.py 34→51

## 2026-07-15 — fix(routing): trendline_sweep 全セル shadow-first demote — ELITE_LIVE all-pairs bypass 除去 (pre-reg 2026-07-13 執行, rule:R2)

- **何を**: `_ELITE_LIVE` から trendline_sweep を除去 (最後の member → 空集合化) + `_PAIR_DEMOTED` に EUR_USD / GBP_USD / EUR_GBP の 3 セルを追加 (gbp_deep_pullback 2026-05-04 と同型)。`TRENDLINE_SWEEP_REDESIGN_V2=1` env の live 復活パスも PAIR_DEMOTED 先勝ちで無効化。`HTF_MIXED_LIVE_STOP_CELLS` の GBP_USD mixed cell stop は部分集合として残置
- **なぜ**: pre-reg `trendline_sweep_gbpusd_pairscope_2026-07-13` (resolved / reviewer=SATISFIED) の terminal action 執行。12y MASSIVE per-cell WF (本番 trigger 無変更) で**全 3 セル FAIL** — netEV: EUR_USD −0.483 (N=3036, WF 1/4) / GBP_USD −3.121 (N=4884, grossEV=−0.095 = 摩擦以前に負) / EUR_GBP −1.449 (N=2829)。BH-FDR (q=0.10, m_eff=4) 生存ゼロ。ELITE_LIVE 根拠の 365d favorable BT (WR 73-81%) は WR 41-44% に崩壊し反証。forward LIVE GBP_USD netEV=−2.35p RR=0.15 が corroborate
- **shadow 継続**: 3 セルとも emit は止めない — is_shadow=1 で記録継続 (4原則#3)。再LIVE化条件 (R1, cell 単位) = forward shadow N≥20 ∧ Wilson_lo≥0.40 (FDR) ∧ WR≥BE-WR@realized-payoff
- **評価への影響**: あり — trendline_sweep の live 発火が全ペアで停止 (ELITE_LIVE 便乗 live はこれで消滅、`_ELITE_LIVE` は空集合)。clean live 集計から trendline_sweep の新規 live row が消える。shadow 統計は不変
- 詳細: [[trendline-sweep]] 判断履歴 / BT: `bt-results/trendline_sweep-12y-pairscope-2026-07-13.json`

## 2026-07-14 — fix(data): E1 positioning worker self-heal + 401 帰属確定 (OANDA book 提供終了) (rule:R3)

- **本番実証 2 問題** ([[e1-positioning-ingest-2026-07-14]] §8): ①全 12 book が HTTP 401 ②worker thread が process ライフサイクルで死ぬ (started_at ありなのに running:false / poll_cycles:0)
- **401 帰属確定 (§8a)**: 当初仮説「OANDA Japan 区分制限」を**棄却** — OANDA は **2024-09-14 に retail API での book 提供を終了** (公式告知 oanda.jp/info/1193 原文確認 + no-token でも同一 generic 401 の実測 + 非日本ユーザー同時遮断の傍証)。fxlabs `/labs/v1/orderbook_data` は 2020 年廃止 (403 HTML 実測)。**auth 修理では直らない → 代替ソース比較 §8c を user 決裁用に整備 (推奨 = Myfxbook aggregate 版転換)**
- **self-heal (§8b)**: demo_trader StatusHeal パターン準拠 — `ensure_running()` (started_at あり × thread 死のみ heal、stop 後は復活せず) + `status()` 冒頭 heal + app.py `before_request` heartbeat (60s throttle、Render health check を恒常 heal 経路化)。status に `restarts`/`last_restart_at` 追加
- **probe API**: `GET /api/positioning/probe?run=1` — v3/accounts 統制付き可用性 probe (read-only ×4)。token/口座 ID 非開示をテストで pin。instrument は whitelist 検証 (path injection 防止)
- **registry**: `e1-positioning-ingest-freshness` → conditional_info 化 — 蓄積ゼロは既知状態、user 決裁まで stale 調査不要
- **評価への影響: なし** — live 発注経路・戦略・Kelly・shadow 一切不変。tests: test_positioning_ingest.py 17→34

## 2026-07-14 — feat(data): E1 positioning ingest — OANDA 建玉/注文比率の snapshot 蓄積基盤 (user GO 2026-07-14, rule:R3)

- **何を**: OANDA v20 positionBook/orderBook (read-only) を 20 分毎 + jitter で snapshot し、既存 SQLite に `positioning_snapshots` (UNIQUE(instrument, book_type, snapshot_time)) として蓄積。buckets は mid ±3% trim + 集計列 (pct_long/short_total, near_imbalance)。対象 6 instruments (USD_JPY/EUR_USD/GBP_USD/EUR_JPY/GBP_JPY/AUD_JPY、env override 可)。dedup 3 層 (book.time メモリ / 再起動 DB seed / UNIQUE)
- **なぜ**: WS3 price-modality 計 3 周 FAIL ([[ws3-round3-crossasset-divergence-prereg-2026-07-13]] §8) → E1 retail-positioning contrarian が主戦線。positioning history は今から蓄積する以外に入手不可 = 稼働開始が最優先。設計: [[e1-positioning-ingest-2026-07-14]]
- **可観測性 (fail-loud)**: `/api/positioning/status` (行数/最新 snapshot_time/連続失敗/可用性マップ) + `/api/positioning/export` (研究用 JSON)。非対応 instrument は初回 4xx 記録→以後 skip。silent except ゼロ
- **監視 (T5 教訓)**: registry `e1-positioning-ingest-freshness` (最終 snapshot 2h 超 stale = 要調査)。`prereg_trigger_watch.py` に info/conditional_info type 追加 (UNAVAILABLE ノイズ→watching)
- **評価への影響: なし** — live 発注経路・戦略・Kelly・shadow 一切不変。read-only データ収集 thread の追加のみ。env `POSITIONING_INGEST_ENABLE=0` で無効化可
- tests: `tests/test_positioning_ingest.py` (17) + prereg watch (+2)。本番検証手順は KB ページ §5 (ローカル token 失効のためデプロイ後検証)

## 2026-07-10 — data(bt): WS3 探索2周目 OOS verdict — ❌ FAIL 0/5、外部仮説探索へ転進 (rule:R1)

- **OOS 窓**: 2024-07-07〜2025-07-07 (再利用 2 回目)。切詰め parquet (末尾 2025-07-07T23:45Z) + **N 凍結→判定の順序執行** (`ws3_round2_oos_entries.json`)。GBP_JPY 15m は Massive 遡及取得で充足、EUR_USD/USD_JPY は stage-1 凍結資産再利用、ep 復元不一致 0/428
- **判定** ([[ws3-round2-explore-prereg-2026-07-10]] §8): 2 レグ (ratio BH-FDR m=5 / §2b 凍結 grid first-touch EV) + ナイフエッジ (LOFO) — **全 5 セル FAIL**。vol_spike×USD_JPY N=27<30 機械 FAIL + ratio 崩壊 0.56 / vsg×GBP_JPY 0.88・dt_sr×GBP_JPY 0.90 崩壊 / sr_fib×GBP_USD 1.21 (p=0.13 n.s.) + EV 孤立格子点 / 最接近 sr_fib×EUR_USD 1.25 (p=0.19) + EV 隣接過半 fail
- **一貫した結論**: round-1→stage-2→round-2 の 2 周で「現行エンジン母集団に OOS 再現の方向性非対称 × 固定 barrier EV の組は無い」。探索窓 EV スクリーン通過 5 セル中 4 セルが OOS で崩壊 = 探索窓 EV は選択バイアスの別表現
- **分岐 (§3 事前固定)**: shadow 母集団内の軸は枯渇 → **外部仮説 (新シグナル系統 — 学術/TV 由来、falsified 6 系統除外) の探索へ転進** (v2.3 WS3 反映)。registry `ws3-round2-oos-verdict-deadline` resolved
- **評価への影響**: なし (純研究、live/shadow 変更なし)

## 2026-07-10 — docs(kb): WS3 探索2周目 pre-reg LOCK — 候補 m=5 凍結 (rule:R1 stage-1 型、純研究)

- **診断** (`raw/bt-results/ws3_round2_scan_2026_07`): 方向分割 196 セル + EUR_GBP (entries=0 構造的) + h96 → 1次候補 8 セル。round-1 checkpoint 窓同一性 0 mismatch
- **§2(ii) 探索窓 first-touch EV スクリーン** (`ws3_round2_ev_screen_2026_07`): **5/8 通過**。脱落 = turtle_soup×GBP_USD / dt_sr_channel×GBP_USD×SELL (孤立格子点) / sr_fib×AUD_JPY×SELL (EV<0)。stage-2 verdict の教訓「非対称 ≠ 固定 barrier で EV 化可能」をスクリーン結果観測前に pre-reg へ反映した a priori 改訂が機能
- **LOCK**: [[ws3-round2-explore-prereg-2026-07-10]] §2b に m=5 + 凍結 grid + 摩擦判定値を固定。registry `ws3-round2-oos-verdict-deadline` (2026-07-17) 追加
- **評価への影響**: なし (純研究、live/shadow 変更なし)

## 2026-07-10 — feat(mode): 15m AUD_JPY shadow-only モード `daytrade_audjpy` 新設 (user 承認 D2)

- **目的**: WS3 stage-2 対象セル htf_false_breakout×AUD_JPY の estimand は **15m** だが、本番 AUD_JPY は 1h モード (`daytrade_1h_audjpy`) のみで 15m shadow 発火ゼロだった。stage-2 PASS 時に shadow parity 検証を即開始できる状態 + AUD_JPY 実測摩擦 (spread/slippage) の取得。決裁メモ: [[shortest-path-decision-memo-2026-07-10]] / pre-reg: [[ws3-stage2-barrier-ev-prereg-2026-07-09]]
- **MODE_CONFIG**: interval 30s / 15m / 60d / compute_daytrade_signal / AUD_JPY / auto_start=True / base_sl_pips=15 (JPY クロス既存値 eurjpy=15 準拠) / **`shadow_only: True`**
- **shadow-only 構造保証 (新機構 `_mode_is_shadow_only`)**: 既存機構では塞げないことを確認の上で追加 — htf_false_breakout は `_SHIELD_EUR_DT_WHITELIST` 登録済みのため `_OANDA_MODE_BLOCKED` 方式は bypass され、N<10 sentinel は agg-Kelly gate も bypass して live minlot 発注される (テストの control ケースで実証: 同一入力×mode=daytrade は 1000u send に到達)。ガードは 3 経路: ①送信ガード最終段 (PRIME/GRAIL/C1/Kalman/edge-cell force-live の後・OANDA 判定の前で shadow 強制、以降 promote 復帰経路なし) ②`_resend_promote_gate_block_reason` に `SHADOW_ONLY_MODE_GATE` (補完送信) ③`_resolve_is_shadow_for_write` (write-path fail-closed)
- **htf_false_breakout 発火経路**: `HTF_FALSE_BREAKOUT_REDESIGN_V2` OFF の legacy 経路のまま (コード変更なし、stage-1 と同一母集団)。v6.1 JPY 追加ゲート (RSI div / OB 接触) は本番仕様どおり適用。QUALIFIED_TYPES は既にグローバル登録済みで per-pair 追加不要、live 転送資格の付与は一切なし
- **テスト**: `tests/test_daytrade_audjpy_shadow_only_mode.py` (9 tests) — 構造 pin / 最悪ケース (N<10 sentinel × strategy_mode=live × bridge active × SHADOW_MODE off) の send ゼロ / control 帰属証明 / resend・write-path gate
- **影響トレード: なし** (live パラメータ不変・OANDA 発注ゼロ。AUD_JPY 15m shadow 行の新規蓄積が開始される)

## 2026-07-09 — fix(tier): FORCE_DEMOTED > PAIR_PROMOTED precedence 全経路統一 (rule:R3)
## 2026-07-10 — docs(kb): 最短経路決裁 (user 承認「進めて」) + 月利目標の段階化 (rule:R3 導出)

- **決裁メモ**: [[shortest-path-decision-memo-2026-07-10]] — 8-agent workflow + 敵対的レビュー3レンズによるゼロベース再検討。**agg-Kelly gate 恒久閉鎖の確定** (固定 cutoff 2026-04-16 累積 −0.2758 → per-cell carve-out なしで正セルも live 発火不能)、D3 決裁 SLA 48h、D4 実装 pre-reg 必須項目 (carve-out + R2 自動降格 + セル単位判定 + parity)
- **目標段階化 (D5)**: [[monthly-target-rederivation-2026-07-10]] — 21.6% の導出考古学 (12-cell 母体 1〜2/12 残存、二重楽観バイアス、pips→%変換消失)。現行制約下天井 = 2セルで +0.15〜2.4%/月。**段階目標 M1 (月次符号転換) → M2 (+0.5%/月) → M3 (+2〜3%/月) へ移行、21.6% は aspirational anchor** — CLAUDE.md / index / roadmap v2.3 反映
- **トラックB 起動**: [[ws3-round2-explore-prereg-2026-07-10]] DRAFT (探索2周目: 方向分割×未走査ペア×h96、判定済み8セル+falsified 6系統除外、queue `20260710-ws3-round2-explore` 排他 claim)
- **評価への影響**: なし (live パラメータ変更なし。D2 15m AUD_JPY shadow-only モードは別 PR)
## 2026-07-09 — fix(tier): FORCE_DEMOTED > PAIR_PROMOTED precedence 全経路統一 (rule:R3)
## 2026-07-10 — WS3 stage-2 verdict: ❌ PASS ゼロ / UNDERPOWERED — barrier EV 化は不成立 (rule:R1)

- pre-reg LOCK ([[ws3-stage2-barrier-ev-prereg-2026-07-09]]) の機械的実行 (期日 07-19 の 9 日前倒し)。OOS-2 = 2022-07-07〜2024-07-06 (第3窓、切詰め worktree)。§3 執行順序遵守 (エントリー抽出 → N 凍結 59/46 → sim)。独立実装の再計算で符号一致検証
- **lfr×EUR_USD: 全 9 構成負 (best −6.51 p/t) → セルクローズ**。SL 先着率 44-75% — stage-1 の中央値非対称は first-touch sequencing で反転
- **htf_fb×AUD_JPY: 1/9 構成のみ +1.15、p_cell 0.594** — fold 集中 (2022 円介入期 +10.8 / 直近 −10.9)・孤立格子点。UNDERPOWERED 分岐 = shadow N≥100 で同一 grid 1 回限り再判定 (registry `ws3-stage2-underpowered-recheck`)
- **帰結: v2.3 WS3 は新シグナル系統 (外部仮説) の探索へ**。TV canon は PASS 候補不在で未評価 (moot)
- **監視配線 (R3)**: `prereg_trigger_watch.py` の shadow_count_decision に instrument フィルタを追加 (無指定だと全ペア合算でセル判定を過大計上) + 回帰テスト。`test_session_time_bias_in_bt_metrics` をパーサ実装 (all-pairs/full-audit 優先) に整合 — 旧実装は辞書順最後の .md を盲目的に見ており研究成果物の追加で誤 red になっていた (テストバグ)
- **影響トレード: なし** (純研究。live/tier 変更ゼロ)
## 2026-07-09 — fix(tier): FORCE_DEMOTED > PAIR_PROMOTED precedence 全経路統一 (rule:R3)
- **latent 疑義の確定**: `_is_promoted_ex` のみ PP 先勝ちで、シグナル経路
  `_is_live_tier_exempt` (9b16ebb5 fail-closed) / `_apply_force_demoted_final_gate` /
  再送 gate と逆。final gate が PP 例外なしに shadow 強制するため live 漏れは構造的に
  不可能 = **実害ゼロ (latent)**。実害候補は「PP でペア復活」の silent 死コード化
  (ema_pullback×JPY 前例) と audit block_cause 誤帰属のみ
- **修正**: `_is_promoted_ex` を FD 先勝ちに統一 + docstring 正準化。FD∩PP=∅
  (tier_integrity_check check#1) のため到達可能入力で挙動不変 (no-op 証明、BT 不要 R3)
- **CI 固定**: `tests/test_pair_promoted_force_demoted_precedence.py` (5 tests) で
  FD∩PP=∅ / PP∩PD=∅ 不変量 + precedence pin。正準文書 = [[system-reference]] Tier
  Precedence セクション (経路別 derivation 表)
- **副次発見の相互裏付け**: post-commit-verify.sh check#3 の `pp_sentinel` premise
  stale (PP∩UNIVERSAL_SENTINEL = {vix_carry_unwind, doji_breakout,
  squeeze_release_momentum} は設計上合法) を本調査でも独立に確認 — 並行セッションの
  check#3 修正 (下記 f292ccb1、マージで合流) と同一結論
- **影響トレード: なし**

## 2026-07-09 — WS3 stage-2 pre-reg LOCKED — user 承認 (rule:R1)

- [[ws3-stage2-barrier-ev-prereg-2026-07-09]] を user 承認「進めて」で 📝 DRAFT → 🔒 LOCKED (決裁期日 07-16 の 7 日前倒し)。verdict 期日 2026-07-19 (LOCK+10d、registry `ws3-stage2-verdict-deadline` 監視)
- **影響トレード: なし** (live パラメータ不変。grid BT / TV 検証の実行解禁のみ)
## 2026-07-09 — post-commit-verify check#3 silent 不発修正 + assertion 現行設計へ張替え (rule:R3 構造バグ)

- **不発の実証と修正** ([[lesson-post-commit-verify-silent-misfire-2026-07-09]]): check #3 (demo_trader tier set 整合検証) は bash double-quoted `python3 -c "..."` 内の f-string `"` によるコード截断で導入 (2026-04-14) 以来一度も実行完了せず、SyntaxError が `|| echo "SKIP"` に吸収される silent 検証ギャップだった。quoted heredoc 化 (check #1 も予防的に同化、check #2 は inline python 非使用で対象外) + 空出力/import 失敗の FAIL 可視化 + `POST_COMMIT_VERIFY_CHANGED` テストシームで red→green 実証
- **stale assertion 発見**: 修復後の初実行が検出した 4 overlap (FD∩SENT=post_news_vol / PP-strat∩SENT=doji_breakout, squeeze_release_momentum, vix_carry_unwind) は全て現行設計の意図的共存 (demote = live 遮断 + shadow 蓄積継続、PAIR_PROMOTED は `_is_promoted_ex`/`_resolve_tier` 両 gate で SENTINEL より先勝ち)。assertion を現行 invariant (`PAIR_PROMOTED∩PAIR_DEMOTED` 同一セル / `ELITE_LIVE∩FORCE_DEMOTED`) へ張替え — 両者とも現状空集合 = 本番 tier 状態は健全
- **影響トレード: なし** (ローカル post-commit hook のみ、live シグナル判定・サイジング不変)

## 2026-07-09 — WS3 stage-2 pre-reg DRAFT 起案 + KB stale 棚卸し (rule:R1 起案 / R3 doc-sync)

- **stage-2 barrier/EV pre-reg DRAFT** ([[ws3-stage2-barrier-ev-prereg-2026-07-09]]): PASS 2 セル限定 h24 barrier grid (m=18)。評価 = 第3窓 OOS-2 (2022-07〜2024-07、2年) で winner's curse 遮断、Westfall–Young max-T セル検定 (FWER 0.10)、TV Pine canon trade-level 突合ゲート、3 分岐 verdict (PASS/UNDERPOWERED/REJECT)。敵対的レビュー 3 レンズ 18 findings 反映 (tie-break 帰属訂正 = SL 優先は swing 規約で fut_close pin より保守側、検定力分析による 2 年窓化、timeout ドリフト PASS の排除等)。**DRAFT — user 決裁期日 2026-07-16 (registry `ws3-stage2-lock-decision-stale` 監視)、LOCK 前の grid BT 実行禁止**
- **KB stale 訂正 (R3 doc-sync、tier 実状態の変更なし)**: london_fix_reversal×GBP の PROMOTED/PAIR_PROMOTED 残存 2 箇所 (`wiki/edge-pipeline.md` / `wiki/strategies/edge-pipeline.md` Stage 6 表) を v9.1 実状態 (Phase0 Shadow + PAIR_DEMOTED×USD_JPY、365d BT GBP EV=−0.239 で demote 済み) に同期 — check.py Edge Stage warn の解消
- **影響トレード: なし** (DRAFT 起案 + doc 同期のみ)

## 2026-07-09 — WS3 stage-1 verdict: ✅ PASS 2/8 — 方向性非対称の OOS 再現 (rule:R1 stage-1)

- pre-reg LOCK ([[ws3-asymmetry-oos-prereg-2026-07-09]]) の機械的実行 (claude 直接、期日 07-16 の7日前倒し)。OOS 窓 2024-07-07〜2025-07-07 (切詰め parquet worktree で look-ahead 遮断、USD_JPY/AUD_JPY は Massive 15m を 2024-05 まで遡及取得)、N=4,980 entries。
- **PASS**: london_fix_reversal×EUR_USD (OOS ratio 1.43 vs 探索 1.51、p=0.0115、CI5% 1.14) / htf_false_breakout×AUD_JPY (1.82 vs 1.39、p=0.0118、CI5% 1.20)。BH-FDR q=0.10 (m=8) + ratio≥1.2 + N≥30 + ナイフエッジ3点全通過。
- 選択バイアス組の崩壊 (htf_fb×EUR_JPY 1.81→0.99 / dt_sr_channel×EUR_USD 1.55→0.62) を確認 = 2段スクリーン設計が機能。持続型 2 セル (lin_reg_channel / dt_fib) は不再現でクローズ。
- **影響トレード: なし (純研究 stage-1)**。次 = stage-2 (PASS 2セル限定 barrier/EV pre-reg + TV Pine canon + user 最終承認)。判定器 `tools/ws3_oos_verdict.py` / スキャン `tools/ws3_mfe_scan.py` (--pairs/--out-suffix 追加)。
## 2026-07-09 — WS4 T15: CI paths filter 撤廃 + QUALIFIED_TYPES drift 検査 + 再送ガード共通化 (rule:R3, audit P1-6/7/8)

- **P1-7 (CI 品質ゲート穴)**: ① `ci.yml` push trigger の paths filter を撤廃 — 旧 filter (`*.py`/`strategies/`/`modules/` のみ) は tests/tools/agents/knowledge-base/scripts 変更の直接 push で CI が一切走らない盲点だった。② hip1-holdout-manifest ガードを CI job 化 (`hip1-holdout-guard`) — .git/hooks/pre-commit はカスタムスクリプト symlink のため pre-commit フレームワークの hook はローカルで一度も実行されていなかった。event diff に対して実行、正規編集は commit message の `HOLDOUT-APPROVED` / `HOLDOUT-VALIDATION-APPROVED` マーカーで通過。③ `agents/cma/dev.agent.yaml` の `--no-verify` 根拠誤記 (「hip1 が full pytest を走らせる」→ 実際はカスタム hook 側) を訂正。actions は full SHA pin 化 (supply-chain)。
- **P1-8 (scalp BT QUALIFIED_TYPES drift)**: `run_scalp_backtest` の inline set を `SCALP_BT_QUALIFIED` に改名 (挙動不変) + 意図的除外 `SCALP_BT_EXCLUDED_TYPES` (mtf_trend_follow / mtf_counter_trend / mtf_regime_trend_cascade = vec harness 専用) を文書化。`scripts/check.py` step 5b が「enabled scalp ⊆ QUALIFIED ∪ EXCLUDED」を機械検査 (drift = ERROR、矛盾登録 = ERROR、stale 除外 = WARN)。意図的 drift で red になることを確認後 green 化。
- **P1-6 (再送ガード共通化)**: `_resend_pending_oanda_trades` は FORCE/PAIR demotion しか再チェックせず Q4/aggregate Kelly/MC-ruin/SHIELD mode を素通しだった (is_shadow 反転バグ 1 つで gate 迂回の直通経路)。共通 helper `_resend_promote_gate_block_reason` が主経路の v9.x SHIELD 群と同判定を resend 直前に再実行。ELITE Q4 免除 / SHIELD whitelist / 1000u min-lot bypass / SENTINEL 免除は主経路と同じに保ち、PRIME lock・edge-cell bypass は per-signal コンテキスト不在のため fail-closed 側へ (5分窓の補完送信のみに影響)。`get_open_trades_without_oanda` に confidence 追加 (Q4 再チェック用)。
- **影響トレード: なし** (live シグナル判定・サイジング不変。resend の fail-closed 化と BT/CI/検査系のみ)。回帰: `tests/test_t15_quality_gates.py` (20 cases)。詳細: [[fable5-system-audit-2026-07-02]]。

## 2026-07-09 — P1-2b 検証クローズ: fut_close tie-break は4エンジン既装 + 回帰 pin 移植 (rule:R3, T14 補完)

- **二重実装レース記録**: T14 (P1-2) は autopilot が PR #65 で実装・マージ、並行セッションの PR #64 (同一実装 + 追加テスト 20 cases) と衝突 → #64 close で解決 (07-07 handoff インシデントと同型)。両実装の意味的差分ゼロを精査確認: (a) 3エンジン cache 無効化 (b) 1H系 BE/Trail guard (block-wrap ⇔ 閾値inf は等価) (c) flag semantics 完全一致。
- **P1-2b (fut_close tie-break) 検証結果: 追加実装不要** — 同一バー TP+SL 同時ヒットの fut_close tie-break は 4 エンジン (run_backtest/scalp/daytrade/1h) 全てに既装、swing はより厳格な保守的 SL 優先 (両ヒット=LOSS)。fut_close→SL 優先への厳格化は BT 全体再較正を伴うため監査どおり P2 据置。
- **#64 由来のテスト delta を移植**: `tests/test_bt_tie_break_regression_pins.py` (13 cases) — ① inline flag 式の canonical AST pin (真偽逆転・env typo 検出、main の既存 pin は参照有無のみ) ② cache key/フラグ照合 pin (stale cache = A/B 汚染防止) ③ P1-2b tie-break pin (TP優先への退行封鎖 + swing SL優先維持)。
- 影響トレード: なし (テスト + KB のみ、app.py 不変更)。

## 2026-07-09 — P1-2: BE/Trail ablation を全 BT エンジンへ展開 (rule:R3, WS4 T14)

- MEMORY 確定事実 `project_be_trail_inflates_python_bt_wr` の水増し源が daytrade 以外の 3 エンジン (`run_backtest` 1H / `run_scalp_backtest` / `run_1h_backtest`) に残存していた (Fable5 監査 P1-2)。daytrade と同じ `_BT_ABLATE_BE_TRAIL` (default ablated、`BT_OPTIMISTIC=1` で旧挙動復元) guard を展開。
- **行動証拠** (scalp fixture `_df_override`): ablated(default) N=84 WR=46.4% vs optimistic N=102 WR=56.9% → **+10.5pp inflation を default で排除**。
- BT cache key を flag-aware 化 (A/B で stale 防止)。AST 構造回帰テスト `tests/test_be_trail_ablation_all_engines.py` 同梱 (4 エンジン guard を pin)。
- **影響トレード: なし** (BT 評価ロジックのみ、live signal/OANDA 転送は不変)。過去 scalp/1H verdict は水増し込みのため再解釈対象。詳細: [[be-trail-ablation-all-engines-2026-07-09]]。残 = P1-2b (fut_close tie-break、副次)。

## 2026-07-09 — WS3 MFE 分布診断: 選抜基準を「MFE 絶対量」→「MFE/MAE 方向性非対称」へ改訂 (rule:R3)

- T2 FAIL 後の WS3 初手 ([[ws3-mfe-distribution-2026-07-08]])。365d baseline 6 pair、N=6,995 entries / 104 cells の forward MFE/MAE (H∈{6..96} bars) を exit 非依存で計測 (`tools/ws3_mfe_scan.py`)。
- **発見1**: MFE 絶対量は豊富 (h24 p50 15-30p) — live 診断の「winners MFE 5.18p」は exit 打ち切りアーティファクトと確定。
- **発見2**: MFE/MAE 比の母集団中央値 0.88 = **価格は走るがシグナル方向に走らない**。希少資源は方向性非対称 (ratio≥1.3 = 7/79 cells)。horizon 持続型 2 cells (lin_reg_channel×EUR_USD 1.38→1.94 / dt_fib_reversal×USD_JPY 1.29→2.05) を次期 pre-reg の検証対象に固定。
- 影響トレード: なし (R3 純診断)。roadmap WS3 節の選抜基準を改訂。事後選択セルの promote 禁止を明記。

## 2026-07-08 — T2 exit-repair grid BT verdict: ❌ FAIL / H0 採択 → WS3 全振り (rule:R1)

- pre-reg LOCK ([[exit-repair-tp-sl-prereg-2026-07-07]]) の機械的実行。executor は Codex queue → claude 直接実行に変更 (user 運用委任、期日 07-21 の 13 日前倒し)。
- **結果: 全 9 構成 FAIL** — BH-FDR q=0.10 全構成 p=1.0 (日次ブロックブートストラップ B=10,000、208 取引日) / WF 3-fold 全構成 0/3 / 摩擦調整 EV 全構成負 (最良 tp0.4×sl0.6 で −2.96 p/t、baseline −6.64 から +3.67 改善もレバー不足)。
- ナイフエッジ3点検査: メカニズムは診断通り作動 (TP-hit 0.215→0.44、EV 両軸厳密単調) した上での**構造的 FAIL**。lag-1 ρ ≈ ±0.06 で自己相関影響なし。感度 run (pre-#58 code、mixed 込み) も同結論 FAIL 0/9。
- 実装: `tools/exit_repair_tp_sl_grid_bt.py` (spawn 分離 grid runner) + `app.py` BT 専用 env hook (`BT_TP_MULT`/`BT_SL_MULT`、env 未設定で完全 no-op)。EUR_JPY 15m parquet の 2ヶ月 stale (silent window 罠) を差分修復。
- **影響トレード: なし (純研究、live パラメータ不変更)**。変わるのは roadmap の主戦線 — §4 固定分岐により **WS3 シグナル張り替え (MFE 分布ベースの entry 再設計) が v2.3 の主戦線**に。exit 側レバーの再試行は禁止。
- 成果物: `raw/bt-results/exit_repair_tp_sl_grid_2026_07.{json,md}` + 感度版。registry `exit-repair-bt-deadline` inactive。verdict 詳細: [[exit-repair-tp-sl-prereg-2026-07-07]] §8

## 2026-07-07 — WS4 Phase B follow-up: shadow 修復層の oscillation 封鎖 + 停止可視化 (PR #59 敵対的レビュー起点, rule:R3)

- PR #59 (P1-3 stale SHADOW_MIGRATION 削除 + P1-9 Kelly raw 化) / PR #60 (T4 摩擦調整 EV マップ) のマージ後、10-agent 敵対的検証 workflow が confirmed した欠陥への追修:
- **oscillation 封鎖**: SHADOW_DRIFT_BACKFILL (2026-05-03) が leak backfill の shadow 分類 (pre-RULE_TS の OANDA-filled リーク行) を次 restart で無条件に live へ巻き戻し、冪等マーカーが再修復を恒久ブロックしていた (空 DB 4-init で再現)。drift rollback の WHERE に `force_demoted_live_leak=0` 除外を追加。
- **修復層停止の可視化 (P2-3 部分)**: leak/flag_drift backfill の unsafe/exception 停止を `[SHADOW_REPAIR_PAUSED]` WARN で毎 restart 表面化。**本番は現在 leak 側 status=unsafe で停止中と実測** (P2-10 新設、修復 chip 化済)。
- **P1-9 スコープ訂正**: `_evaluate_shadow_promotions` は production call site ゼロの dead code — P1-9 で武装されるのは live promotion loop の `_kelly_block` のみ (P2-11 新設)。ゼロ境界は `< 0` が仕様と裁定 (`<= 0` 化は正エッジ誤 block の対称害で不採用)、mirror テストを production 述語に整合。
- 影響トレード: なし (シグナル判定・lot 不変更)。変わるのは修復層の分類安定性と観測性のみ。
- 回帰: tests/test_ws4_phase_b_followup.py (5 cases、oscillation は main で red 確認済み) + test_kelly_promotion_gate.py 整合。詳細: [[fable5-system-audit-2026-07-02]] P1-3 follow-up / P2-3 / P2-10 / P2-11

## 2026-07-07 — HTF mixed cell stop: trendline_sweep×GBP_USD live 転送停止 + mixed 診断タグ是正 (rule:R2/R3)

- T1 forensic §7 の異常 (30d 大負け4発 −53.6p 全てに「⚖️ 4H+1D 不一致 → シグナル抑制中」タグ付き LIVE 発注) の根本原因を特定: **タグは診断のみで、v9.1 HTF Hard Block は bull/bear 限定 — mixed は DTE 候補フィルタ no-op**。trendline_sweep は self-contained HTF guard も持たず、demo_trader v9.3 regime gate も ELITE_LIVE 免除で第2層不在。
- R2 執行: `DaytradeEngine.HTF_MIXED_LIVE_STOP_CELLS = {(trendline_sweep, GBP_USD)}` — mixed 時に候補除外 + shadow 退避 (`[HTF_MIXED_LIVE_STOP]` タグ、is_shadow=1)。根拠 = clean live (06-03..07-03) mixed N=15 EV=−3.38p/−50.7p vs aligned N=4 +1.5p、shadow mixed N=7 EV=−7.20p corroborate。
- R3 執行: reasons の mixed 文言を実状態記述へ是正 (「4H+1D 不一致」substring は query 互換維持)。
- 影響トレード: trendline_sweep×GBP_USD の HTF mixed 状態エントリーが以後 live に乗らない (shadow は継続)。aligned (bull/bear) 状態は不変。BT は `compute_daytrade_signal` 内適用のため自動同期。
- 回帰: tests/test_htf_mixed_live_stop.py (6 cases)。再 live 化は R1 のみ。詳細: [[mtf-mixed-gate-noop-forensic-2026-07-07]]

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
