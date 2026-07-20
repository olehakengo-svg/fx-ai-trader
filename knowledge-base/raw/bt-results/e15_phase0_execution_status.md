# E15 phase-0 execution status — machinery delivered, data-run credential-blocked

**日付**: 2026-07-20 (autopilot)
**pre-reg SSOT**: [[e15-e7-event-modality-prereg-2026-07-18]] (🔓 DESIGN self-LOCK)
**タスク票**: `.ai/tasks/queue/20260718-e15-e7-event-phase0.md`
**期日**: 凍結 2026-07-24 / OOS verdict 2026-07-31 (registry `e15-e7-event-prereg-phase0-verdict`)

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

## ⛔ credential ブロック (self-provision 不能、CLAUDE.md 自走原則の例外)

| 必要 credential | 用途 | 状態 | 確認した代替経路 (全滅) |
|---|---|---|---|
| `MASSIVE_API_KEY` | 13 ペア 12y 15m OHLCV (§3.1) | env 不在 / sandbox が `.env` 遮断 | MASSIVE MCP = 12y×15m×13 で不現実 (limit 50k/call、~117 call、context 破綻)。ローカル 15m cache は cross 2 本のみ (primary 7 = ゼロ) |
| `FRED_API_KEY` | NFP/CPI release date (§3.2 release_id 50,10) | env 不在 | BLS schedule = 403 bot-block / MASSIVE Economy = series のみ (release-date endpoint なし) |

**key-free で取得可能なもの**: FOMC scheduled meeting dates (federalreserve.gov、HTTP 200 確認)。

## ▶ data-run 再開 runbook (キー投入後)

キーがある環境 (Codex companion env / keyed session) で以下を順に実行。機械層は改変不要。

```
# 0. env
export MASSIVE_API_KEY=... FRED_API_KEY=...

# 1. カレンダー (§3.2) — FOMC=federalreserve.gov / NFP+CPI=FRED release_id 50,10
#    ET→UTC は lib.event_time_utc、sanity は §3.2 (event bar range vs 20d 中央値×2)
#    → raw/bt-results/e15_e7_event_calendar.json  ({"events": {"FOMC":[iso...], "NFP":[...], "CPI":[...]}})

# 2. 価格 (§3.1) — 13 ペア 15m フル歴史 + coverage freeze
#    for pair: fetch_ohlcv_massive(pair, "15m", days) → data/cache/massive/{pair}_15m.parquet
#    coverage = lib.market_time_coverage(...) ≥ 0.90、未達は機械除外 (fail-loud)
#    → raw/bt-results/e15_e7_pair_coverage.json

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
