# E15 phase-0 execution status — ✅ 完了: OOS verdict ❌ FAIL 0/6 (2026-07-22、期日 9 日前倒し)

**日付**: 2026-07-20 machinery / 2026-07-21 price-data run (autopilot) / **2026-07-21 calendar run (本セッション)**
**pre-reg SSOT**: [[e15-e7-event-modality-prereg-2026-07-18]] (🔓 DESIGN self-LOCK + §3.2b AMENDMENT 2026-07-21)
**タスク票**: `.ai/tasks/queue/20260718-e15-e7-event-phase0.md`
**期日**: 凍結 2026-07-24 / OOS verdict 2026-07-31 (registry `e15-e7-event-prereg-phase0-verdict`)

## 🔄 2026-07-21 更新 (calendar run) — カレンダー凍結完了、sanity >5% 発火 → §8 DEFERRED、discovery は user 裁定待ち

**FRED ブロッカーは §3.2b AMENDMENT (結果観測前 data-availability、round-3 前例) で解消**:
NFP 行に pre-registered 済みの fallback「BLS 公式ページ」を発動 (CPI は「同上」の明確化)、
アクセスは Wayback Machine snapshot 経由 (BLS 直接 403)。発表日は客観的事実でソース非依存。

- **カレンダー構築完了** (`tools/event_calendar_build.py build`、politeness 2s/req):
  **FOMC 99 / NFP 149 / CPI 149 件** (2014-01-01〜2026-06-30、ET→UTC per-date DST)。
  - NFP/CPI = BLS News Release Archive の**アーカイブ発表ファイル名 = actual release date** (一次記録)。
    snapshot: empsit 2026-07-13 / cpi 2026-06-12 (sha256 は JSON source ledger に凍結)。
  - FOMC = federalreserve.gov 直接。fomccalendars.htm (2021-2026) + fomchistorical{2014-2020}。
    **scheduled のみ**: unscheduled 4 (2014-03-04, 2019-10-04, 2020-03-02, 2020-03-15) /
    cancelled 1 (2020-03-17,18) / notation vote 4 件を除外・記録 (計 9、JSON exclusion ledger)。
    monetary20250822a (枠組み改定、非会合) は行内突合で構造排除。scheduled = 8/年 (2020 のみ 7+1 cancelled)、2026H1 = 4。
  - **整合性検証 green (explore 窓)**: NFP 非金曜ゼロ (7月4日木曜 3 件のみ) / 12件/年 / 欠月ゼロ。
    OOS 窓の 2025 shutdown 異常 (NFP 11/20 木曜・12/16 火曜、Oct 2025 欠月等) は**フラグ記録のみ・除外せず** (§10-3)。
  - パーサ回帰 pin: `tests/test_event_calendar_build.py` (15 tests、オフライン fixture)。
- **価格 re-fetch 再現**: 13/13 ペアの explore coverage が凍結台帳と**完全一致** (例: USD_JPY 0.9786、
  EUR_AUD 1.0000) — 台帳の再現可能性を実証。
- **⚠️ §3.2 sanity 検出器が発火**: フラグ率 **CPI 43.6% / NFP 6.8% / FOMC 2.5%** (>5%)
  → §3.2 処方どおり **discovery 停止・カレンダー再検証を実施**:
  - **verify-times (オフセットピーク検査、range のみ・explore 窓のみ)**: 全 3 イベント種で
    range 比が **offset +0 で正確にピーク** (NFP 3.94× / CPI 2.92× / FOMC 7.95×) = **時刻は正しい**。
  - フラグ年次分布: CPI は 2014-2020 に 49/51 集中 (2023 ゼロ) = **低インフレ期の低インパクト由来**。
    NFP/FOMC フラグは COVID 期 (高ベースライン) 集中。**時刻破損行ゼロ → §3.2 後付け修正は不実施**。
  - → 検出器は「時刻誤り」と「低インパクトイベント」を弁別できない仕様だが、
    **pre-reg §8 は明文で「カレンダー sanity >5% — user 裁定 (勝手に解釈しない)」** →
    **DEFERRED 分岐発動。discovery は user 裁定まで実行しない** (R1 規律、勝手な解釈で
    LOCK を汚さない)。裁定材料は `e15_e7_event_calendar_build.md` に凍結済み。
- **user 裁定後は push-button**: `python3 tools/event_modality_explore.py discovery` が
  カレンダー + parquet を読んで §5a/§5b を機械実行 (凍結 artifact `e15_frozen_candidates.json`
  も書き出す)。期日 07-24 まで残り 3 日 — 裁定が下り次第、数分で凍結可能。
- **役割分離 (PR #102)**: 本カレンダー = 歴史 (BLS/Fed 一次、BT 判定用)。PR #102 の
  `tools/ff_calendar_import.py` + `modules/market_data_ingest.py` = go-forward FF capture
  (E7 Actual 補完)。ファイル・役割とも非重複。
- **§10-1 遵守**: 本セッションで計算したのはカレンダー件数・整合性・event bar の **range** のみ。
  イベント×リターンの結合統計 (探索窓含む) は一切未計算 — discovery 自体を実行していない。

## 🔄 2026-07-21 更新 (autopilot) — MASSIVE ブロックは誤り、§3.1 データ準備を完遂

前回 (07-20) は data-run を **MASSIVE_API_KEY + FRED_API_KEY 双方の credential ブロック**と記録したが、
今回 origin/main で再検証したところ **MASSIVE 側のブロックは事実誤認**だった:

- **`MASSIVE_API_KEY` はローカル `.env` に実在 (len 32) し、正常に稼働** — `modules.data.fetch_ohlcv_massive`
  で実データ取得を確認 (EUR_USD daily → USD_JPY 15m 312,458 行)。前回の「env 不在 / sandbox が `.env` 遮断」は
  この環境では成立しない。「MASSIVE MCP は非現実的」という代替経路の議論も、REST 直叩き (parquet に直書き、
  context を経由しない) なら不要。
- **§3.1 データ準備を完遂**: 13 ペア 15m フル歴史 (days=4650、~2013-10-24〜2026-07-21) を MASSIVE から取得し
  `data/cache/massive/{pair}_15m.parquet` に保存、explore 窓 (2014-01-01〜2023-12-31) の market-time coverage を
  `lib.market_time_coverage` で計測し **`raw/bt-results/e15_e7_pair_coverage.json` に凍結**。
  **結果: 13/13 ペア全て coverage ≥ gate 0.90 (実測 0.974〜1.000)、primary 7/7 included。**
  pre-reg が懸念した EUR_AUD の取得不能は**発生せず (coverage 1.000)** → §3.1 の「12 ペアへ縮小」分岐は不発、
  **§8 DEFERRED (primary < 5) リスクは解消** (primary 7/7 確保)。
- **ハーネスを実 parquet でスモーク検証**: `_load_pair` → `build_daily_from_m15` → `event_trade` → `run_combo` が
  本番 parquet 上で完走 (tz=UTC 正、3 primary × 8 date で N=24 / event_blocks=8 / EV 計算成立)。合成 self-test だけでなく
  実データ経路の統合バグがないことを確認 (EV 値自体は合成日付サブセットにつき無意味 = 機械検証のみ)。
- **§10-1 遵守**: 本更新は coverage 件数と日付範囲の計上のみ。OOS 窓 (2024-01-01〜) の**イベント×リターン結合統計は一切未計算**。

### 残る唯一のブロッカー = FRED calendar (NFP/CPI release date)

- `FRED_API_KEY` は依然 **env 不在・self-provision 不能** (FRED API は要キー / FRED 公開ページは WebFetch に 403・
  urllib timeout / firecrawl キーも無し / MASSIVE Economy は series 観測値のみで release-date endpoint なし)。
- **FOMC** は federalreserve.gov から key-free で HTTP 200 だが、**歴史ページ (2014-2020) の HTML が年ごとに書式不統一**
  (2017/2018/2020 は "Month D-D Meeting" パターンに乗らず、unscheduled 会合はインライン注記)。LOCK に供する
  カレンダーを不安定な手パースで作るのは integrity リスク、かつ **discovery は NFP/CPI が無い限り走らせられない**
  (54 combo family の一部だけの freeze は §5b 違反) ため、**FOMC も NFP/CPI と同一の keyed パスで一括構築するのが正**。

→ **item は「両 credential ブロック・データ皆無」から「価格データ + coverage 凍結済 + ハーネス実データ検証済、
残りは FRED を要するカレンダー 1 パスのみ」へ前進。** keyed 環境での再開手順は下記 runbook のとおり (機械層は無改変で push-button)。
価格 parquet は `data/cache/massive/` (gitignore) にローカル保存 = keyed 環境では同じ fetch を再実行 (coverage 台帳が実行可能性を保証)。

## サマリ

phase-0 の **オフラインで完遂可能な機械層を先行実装**した。estimand を 1 箇所に正規化した
SSOT lib + 探索ハーネス + §10-6 契約テストを納品し、合成データで検証済み。**残るは
credential を要するデータ取得と、それに続く discovery→凍結→verdict の実行のみ** で、
キー投入後は push-button で走る状態にした。

pre-reg §10-1 (中間 peeking 禁止) は厳守 — 本 PR は OOS 窓 (2024-01-01〜) のイベント×
リターン結合統計を一切計算していない。ハーネスは探索窓終端 `EXPLORE_END=2023-12-31` を
構造的に強制し、self-test は全 event date ≤ EXPLORE_END を assert する。

## ✅ 納品 (offline 検証済)

| 成果物 | 内容 | 検証 |
|---|---|---|
| `tools/event_modality_lib.py` | §3.5/§4/§5a estimand SSOT | 単体 12 pin green |
| `tests/event_modality_lib` | §10-6 契約 pin (SL 優先/DST/entry=open/censoring/leak canary) | `pytest -q` green |
| `tools/event_modality_explore.py` | §5a discovery ハーネス + §5b select_and_freeze | `self-test` green (54→54 cell、false-edge 0) / `discovery` fail-loud |

**estimand の要点** (round-3 crossasset harness からの意図的逸脱 = pre-reg 忠実性):
- entry = 指定バー **open** (round-3 は close) / 前方リターン終端 = horizon バー **open**。
- first-touch **同一バー TP+SL 両ヒット = SL 優先** (round-3 は TP 優先 = ハウス保守規約違反 → 再利用禁止)。
- σ_h = ATR14d × √(h/24h)、ATR14d = t より厳密に前の 14 daily bar (NY 17:00 roll、M15 構築)。
- horizon = market-time bar count (h4=16 / h12=48 / h24=96)。censoring は terminal>cache 末尾で不算入。

## credential 状態 (2026-07-21 更新)

| 必要 credential | 用途 | 状態 |
|---|---|---|
| `MASSIVE_API_KEY` | 13 ペア 12y 15m OHLCV (§3.1) | ✅ **解消** — `.env` に実在・稼働。§3.1 データ準備 + coverage 凍結 完遂 (13/13 pass gate) |
| `FRED_API_KEY` | NFP/CPI release date (§3.2 release_id 50,10) | ⛔ **残** — env 不在・self-provision 不能。FRED API=要キー / FRED 公開ページ=WebFetch 403・urllib timeout / firecrawl キー無 / MASSIVE Economy=series 観測値のみ |

**key-free で取得可能なもの**: FOMC scheduled meeting dates (federalreserve.gov HTTP 200) — ただし歴史ページ書式が
年ごと不統一のため、FRED パスと同一 keyed 実行で NFP/CPI と一括・検証付き構築が正 (上記 §残ブロッカー参照)。

## ▶ data-run 再開 runbook (キー投入後)

キーがある環境 (Codex companion env / keyed session) で以下を順に実行。機械層は改変不要。

```
# 0. env
export MASSIVE_API_KEY=... FRED_API_KEY=...

# 1. カレンダー (§3.2) — FOMC=federalreserve.gov / NFP+CPI=FRED release_id 50,10
#    ET→UTC は lib.event_time_utc、sanity は §3.2 (event bar range vs 20d 中央値×2)
#    → raw/bt-results/e15_e7_event_calendar.json  ({"events": {"FOMC":[iso...], "NFP":[...], "CPI":[...]}})

# 2. 価格 (§3.1) — ✅ 2026-07-21 完遂済 (13/13 pass gate)。台帳 = raw/bt-results/e15_e7_pair_coverage.json
#    keyed 環境では data/cache/massive/{pair}_15m.parquet が無ければ同じ fetch を再実行:
#    for pair in ALL_PAIRS: fetch_ohlcv_massive(pair, "15m", 4650) → parquet
#    (coverage = lib.market_time_coverage(...) ≥ 0.90、台帳が実行可能性を保証済)

# 3. discovery (§5a、探索窓のみ) + 凍結 (§5b)  ── 期日 2026-07-24
python3 tools/event_modality_explore.py discovery
#    → e15_discovery.json。select_and_freeze で m₀≤8 → pre-reg §5b 追記 🔒 + e15_frozen_candidates.json

# 4. OOS verdict (§5c、LOCK 後に実装) ── 期日 2026-07-31
#    tools/event_modality_oos_verdict.py (--extract/--sim 分離、seed 固定、canary/join tests 先行 pin)
#    レグ A (event-block bootstrap + IM t、BH q=0.05) / レグ B / ナイフエッジ 4 点
#    → pre-reg §12 追記 + registry resolve + changelog
```

## 判断メモ

- 本 PR は **live/shadow/Kelly/tier を一切変更しない純研究** (pre-reg rule)。
- estimand を lib に正規化したことで、後続 verdict 器は同一 SSOT を共有し first-touch/σ_h/DST の
  二重定義リスクを排除 (round-3 で first-touch 定義が harness 内に閉じていた反省)。
- data-run が別環境になっても、機械層 + tests が pin されているため「執行のみ」の pre-reg
  規律 (設計自由度ゼロ) を保てる。

---

## 🟢 2026-07-22 — §8 DEFERRED 裁定: user 承認 → discovery 実行

- **裁定**: user「承認」(2026-07-22、本 session)。問 = 「sanity フラグ率 CPI 43.6% > 5% は時刻誤りではなく低インパクトイベント由来として discovery 続行を承認するか」
- **裁定根拠 (観測前に凍結済みの材料のみ)**: verify-times 検査で全 3 イベント種が offset +0 に正確な変動ピーク (NFP 3.94× / CPI 2.92× / FOMC 7.95×)、破損行ゼロ。フラグは低インフレ期 (2014-2020) CPI の低インパクト由来 (49/51 が同期間、2023 ゼロ)。低インパクトイベントの包含は「正直な EV」側 — 除外する方が選択バイアス
- **実行**: `python3 tools/event_modality_explore.py discovery` — 価格 parquet は coverage 台帳検証済みフルセット (calendar worktree からコピー、13/13)。凍結 artifact = `e15_frozen_candidates.json`、期日 2026-07-24 に対し 2 日前倒し

---

## 🏁 2026-07-22 — phase-0 OOS verdict 執行: ❌ **FAIL (PASS 0/6、全候補 C5)** — phase-0 完了

**手順 (§10-6 遵守 — test pin してから OOS 接触)**:

1. **判定器実装**: `tools/event_modality_oos_verdict.py` (§11 指定名、extract/verdict 分離、seed=20260718 固定、B=10,000)。estimand は lib SSOT を再利用 (重複実装なし)。lib へは加法的拡張のみ — `TradeOutcome.atr` 露出 (レグ A の ATR14d 正規化用) / `entry_delay_bars` (ナイフエッジ#3 遅延レグ) / leak_canary の ATR 経路比較 (§5c-3 明文「R0/ATR 経路」の完全化)。sanity 検出器は `event_calendar_build.py` を window 共有関数化 (`range_sanity_scan`/`offset_peak_scan`) して OOS 窓 (§3.2b-7) に適用。
2. **test pin 26 件** (`tests/test_event_modality_oos_verdict.py`): 判定分岐 C1–C5 排他順 / 全体 PASS·UNDERPOWERED·FAIL / BH-FDR (m=m₀ 固定、None 処理) / event-block bootstrap の seed 決定論・効果弁別 / IM df=blocks−1・退化ケース / p=max(p_boot,p_IM) / ナイフエッジ LOFO·top-block·LOPO·collision / **canary の検出能力** (注入リークを False 検出) / entry+1バー遅延 (R0 不変) / OOS 窓ガード / stress 摩擦式 / gross+摩擦線形適用=lib net の join 契約 — **全 green 確認後に OOS データへ**。
3. **parquet**: calendar worktree の検証済みフルセット 13 本をコピー → **台帳再現 13/13 green** (first 起点・explore coverage 完全一致・台帳 last 時点行数一致。末尾余剰 23–24 本 = 台帳スナップショット後の re-fetch 分、OOS cutoff 2026-06-30 切詰めで判定非接触。sha256 を artifact に凍結)。
4. **OOS sanity (§3.2b-7)**: flag 率 NFP 3.4% / CPI 14.3% / FOMC 10.0%。CPI/FOMC >5% だが offset ピーク**全種 +0** (時刻正常) = explore 窓の user 裁定 (2026-07-22、低インパクト由来) と同一シグネチャ → 同裁定下で続行・記録。canary 実データ sweep 686 件 all clean。
5. **verdict**: 1,005 trades / 6 候補。**レグ A 全滅** (min p_combo=0.214 ≫ BH rank-1 閾値 0.0083、BH-FDR q=0.05 m=6 通過ゼロ) → 全候補 **C5**。C3 ゼロ (blocks 20–28 ≥ 15 で B(d) 充足 — §9 modal 予想 C3 は不成立、§8 字義執行)。**§8 固定分岐 = phase-1 予定どおり実行**。
6. **成果物**: `e15_phase0_oos_verdict.json` (全統計+trade/event list、~500KB) + `e15_phase0_oos_trades.json` (抽出中間) + pre-reg §5b 凍結表転記 (手続き補完)・§8 発動分岐・§12 判定表 + registry `e15-e7-event-prereg-phase0-verdict` resolve + changelog + pipeline 状態表。

**§10 遵守**: OOS 結合統計の観測は verdict 実行が初回。観測後の再分析・再解釈なし (§12 は事前列挙の切り口のみ)。**残タスク = phase-1 (E7) のみ** (FF gap scrape + データ付録凍結 08-14 → discovery 08-21 → verdict 08-28、registry `e15-e7-event-prereg-phase1-verdict` が監視)。

---

## 🏁 2026-07-24 — phase-1 データ基盤執行: FF カレンダー歴史+gap import 完了 (期日 08-14 の 21 日前倒し)

**§3.3b データ付録 (同日凍結) の執行記録。イベント×リターン結合統計は一切未計算 (§10-1 遵守)。**

1. **ソース確定**: EPSOFT 延長なし (2023-03 で停止、2026-07-24 確認) → **R4F (`robots4forex.com/news/news.php`) を歴史 (2014-01〜) + gap (2023-04〜2026-07-20) の単一ソースに採用**。値整合 = EPSOFT cross-check 歴史 sample 279/279 完全一致 + 2023 Q1 overlap 114/120 (差分は全て EPSOFT 側 end-of-panel)。
2. **dump 実測特性 2 点を anchor 突合で特定** (E15 canonical NFP 149 + CPI 135): (a) 時刻規約が 2023-08-07 で Europe/London → UTC に切替 (`tools/ff_gap_prepare_r4f.py` が正規化) (b) actual 列が 2023-08 で充填停止 → 判定系列は BLS first print で補完。
3. **BLS first print 抽出** (`tools/ff_gap_bls_first_prints.py`、Wayback id_ 経由 §3.2b 経路): 75 件抽出 / **較正 9/9 完全一致** (R4F actual 残存区間)。抽出器は「出現位置最早」選択 — kind 順先勝ちの 2 バグ (NFP 後方改定括弧 2 件・CPI 後方 y/y 4 件) を **R4F previous 連鎖との系統突合で検出して修正** (regression test pin 済み)。CPI 2025-12-18 は shutdown 合算値 (「over the 2 months」) のため機械検出で除外。
4. **本番 import (Render SSH、dry-run → 実行)**: `r4f-2014-2026` = 58,713 insert / 13 kept (go-forward seam) / 0 invalid。`bls-first-print` = 66 actual 補完 / 9 kept / 0 invalid。
5. **完備性検証 (export API)**: ff_calendar_events = **58,789 行 / actual 35,861**。**判定系列 canonical 突合 = 297/298 完備 (actual+forecast)** — 唯一の欠落 = CPI 2025-12-18 (§3.3b-6 で事前宣言済みの除外、forecast も FF に不存在)。
6. 成果物: `raw/bt-results/e7/` (import CSV ×2 + manifest + BLS ledger + 意味論検証 json)。生 snapshot (R4F dump 5.5MB + BLS 76 ページ) は data/cache/rates/raw/ (sha256 は manifest/ledger に凍結)。

**残 = phase-1 本体のみ**: discovery+候補凍結 2026-08-21 → OOS verdict 2026-08-28 (registry `e15-e7-event-prereg-phase1-verdict` 監視継続)。データ側の前提は本日で完結。

---

## 🔧 2026-07-29 — phase-1 データ前提修理: plain 15m parquet の台帳再現復元 (rule:R3)

**発見**: MASSIVE ベンダー欠損 backfill (PR #131) の影響調査中に、coverage 台帳 (`e15_e7_pair_coverage.json`) が参照する plain `{pair}_15m.parquet` が **11/13 ペアで台帳再現不能**と判明 (USD_JPY は 2024-05 開始に短縮、NZD_USD/USD_CAD/NZD_JPY は 2025-04 開始、EUR_AUD は消失など。再現 OK は EUR_JPY / EUR_GBP のみ)。原因 = 各種 explore の短い `--days` フル取得が plain path を無条件上書き (WS3 round-2 prep 2026-07-09 等、複数回)。このままでは phase-1 discovery (08-21) / OOS verdict (08-28) が `load_and_verify_bars` で **BLOCKED** になる。

**復元 (byte-exact)**:
1. phase-0 実行 worktree **`e15-oos-20260722`** に原本 13 本が現存し、**phase-0 verdict `data_ledger` の sha256 と 13/13 完全一致**を確認。
2. `tools/e15_e7_data_refreeze.py --restore-from <worktree>/data/cache/massive` で sha256 照合付き復元 → 13/13 `RESTORED_BYTE_EXACT` (旧ファイルは `.bak-pre-refreeze-2026-07-29` 退避)。
3. 判定器の実コード `load_and_verify_bars` で **13/13 GREEN** を実証 (errors=[])。

**凍結コピー (clobber 再発保険)**: `data/cache/massive/e15_e7_frozen/` に 13 本コピー + sha256 manifest = `raw/bt-results/e15_e7_frozen_manifest_2026-07-29.json` (**verdict data_ledger と同一 sha256** = provenance 連鎖が閉じる)。

**ベンダー不安定性の実測 (副産物)**: MASSIVE fresh 再取得 (days=4675) では USD_JPY/EUR_USD/GBP_USD が 3 点一致した一方、**AUD_USD は台帳比 −25 行の drift** (07-21 に存在したバーがベンダーから消えた)。→ **MASSIVE 歴史バー集合は不変ではない**。凍結が必要な pre-reg データは「plain cache 参照 + 行数 pin」ではなく**ファイル実体の凍結コピー + sha256** で守ること (本件の教訓)。

**phase-1 実行手順への追加 (08-21 / 08-28 の pre-flight)**:
```
python3 tools/e15_e7_data_refreeze.py --verify-only            # 13/13 OK を確認してから discovery/verdict
python3 tools/e15_e7_data_refreeze.py --restore-from-frozen data/cache/massive/e15_e7_frozen   # clobber 時
```

**再発防止**: `tools/fetch_massive_data.py` に never-shorten merge ガード (既存行優先・head 保持・tail 延長のみ、`--overwrite` で明示解除) + `tests/test_massive_cache_never_shorten.py` 8 tests。

**§10-1 遵守**: 本修理は価格ファイルの復元・検証のみ (first/coverage/行数/sha256)。イベント×リターン結合統計は一切未計算。live/shadow/Kelly/tier 不変更。
