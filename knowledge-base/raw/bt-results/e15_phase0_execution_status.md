# E15 phase-0 execution status — price data + coverage FROZEN (MASSIVE unblocked), residual = FRED calendar only

**日付**: 2026-07-20 machinery / **2026-07-21 price-data run (autopilot)**
**pre-reg SSOT**: [[e15-e7-event-modality-prereg-2026-07-18]] (🔓 DESIGN self-LOCK)
**タスク票**: `.ai/tasks/queue/20260718-e15-e7-event-phase0.md`
**期日**: 凍結 2026-07-24 / OOS verdict 2026-07-31 (registry `e15-e7-event-prereg-phase0-verdict`)

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
