---
id: 20260603-2022-sr-fib-confluence-v3-usdjpy-bt
priority: P1
gate: R3
rule: R3
status: queued
created: 2026-06-03
owner: claude
depends_on: 20260603-1635-sr-fib-confluence-v3-redesign-bt
---

# sr_fib_confluence V3 — USD_JPY BT (multi-pair extension)

**Rule classification**: R3 (shadow-first redesign extension、catastrophic check のみ)
**Depends on**: `20260603-1635-sr-fib-confluence-v3-redesign-bt` (V3 ロジック実装と BT script
を提供する先行タスク)。先行タスクが PASS で merge 済みであることを前提。

## Background — なぜこれを追加するか

先行タスク `20260603-1635-sr-fib-confluence-v3-redesign-bt` で sr_fib_confluence V3
(Classical MR+Follow combined) を EUR_USD M15 365d で BT 実施。Claude session で
TradingView Pine v6 を使った 6-pair multi-pair check の結果、**USD_JPY が最強の edge**
を示した:

| Pair | N | WR | PF | PnL | Verdict |
|---|---:|---:|---:|---:|---|
| **USD_JPY M15** | 467 | **40.69%** | **1.29** | **+6.26** | ✅ **🥇 Strong** |
| EUR_USD M15 | 529 | 37.62% | 1.194 | +4.12 | ✅ Good |
| GBP_USD M15 | 470 | 34.89% | 1.097 | +2.12 | ✅ Decent |
| GBP_JPY M15 | 506 | 36.17% | 1.051 | +1.26 | ⚠️ Marginal |
| EUR_JPY M15 | 512 | 33.79% | 1.001 | +0.03 | ⚠️ Breakeven |
| AUD_JPY M15 | 519 | 33.33% | 0.985 | -0.47 | ❌ FAIL |

USD_JPY の per-trade EV は EUR_USD の +72%、PnL は +51% 高い。**USD_JPY を Live promote
候補の主戦場にする方が EUR_USD より合理的**。Codex 側でも prod V3 BT を USD_JPY で再確認
して、TV と Codex 両方で edge が確認できれば Live promote の根拠になる。

なお EUR_JPY (PF 1.001) と AUD_JPY (PF 0.985) は edge 無し / 負で、Live promote 対象外。
これは別タスクで universe filter 化する。

## V3 設計仕様

先行タスクで実装される `_evaluate_redesign_v3` をそのまま流用。新たに strategy file の
修正は不要。詳細は `20260603-1635-sr-fib-confluence-v3-redesign-bt.md` を参照。

要点 (先行タスクの実装):
- Impulse direction detection (high_age vs low_age)
- Fib levels: 38.2 と 61.8 only (50% mid 除外)
- ADX ∈ [20, 30]
- Entry: LONG=up-impulse+fib, SHORT=down-impulse+fib
- TP/SL: ±2×ATR7 / ∓1×ATR7
- env flag `SR_FIB_CONFLUENCE_REDESIGN_V3=1`

## BT 実行

### Option A: 既存 BT script 環境変数で USD_JPY 指定 (推奨)

先行タスクで `tools/sr_fib_confluence_redesign_v3_bt.py` が `SR_FIB_CONFLUENCE_BT_TARGETS`
env を尊重する実装になっていれば、以下で USD_JPY のみ BT:

```bash
cd /Users/jg-n-012/test/fx-ai-trader
SR_FIB_CONFLUENCE_BT_TARGETS=USD_JPY python3 tools/sr_fib_confluence_redesign_v3_bt.py
```

### Option B: 新規 BT script (Option A が不可なら)

`tools/sr_fib_confluence_redesign_v3_bt_usdjpy.py` を新規作成:
- 先行タスクの `tools/sr_fib_confluence_redesign_v3_bt.py` のコピーを base
- TARGETS = [("USD_JPY", "USDJPY=X")] に変更
- OUTFILE = bt-results/sr_fib_confluence-redesign-v3-usdjpy-2026-06-03.json

### データ要件

- `data/cache/massive/USD_JPY_15m.parquet` 必須 (MASSIVE cache、Yahoo fallback 禁止)
- cache 無ければ verdict=BLOCKED_DATA で early return (既存 v2 BT と同じ挙動)
- BT_MODE=1, BT_REQUIRE_MASSIVE_CACHE=1 強制

## A/B 構造

- current: legacy (`SR_FIB_CONFLUENCE_REDESIGN_V2=0`, `SR_FIB_CONFLUENCE_REDESIGN_V3=0`)
- proposed: V3 (`SR_FIB_CONFLUENCE_REDESIGN_V3=1`)
- 出力: `bt-results/sr_fib_confluence-redesign-v3-usdjpy-2026-06-03.json` (Option B)
  または `bt-results/sr_fib_confluence-redesign-v3-2026-06-03.json` の cells["USD_JPY"]
  に上書き追記 (Option A、要マージロジック注意)

## Accept gate (v2.1 catastrophic check のみ)

```python
def _criteria(current, proposed):
    if proposed["N"] < 20:
        return {"verdict": "INSUFFICIENT_BT_EVIDENCE",
                "shadow_promote_recommendation": "RECOMMEND_SHADOW"}
    pnl_sign_preserved = not (current["PnL"] > 0 and proposed["PnL"] < 0)
    verdict = "PASS" if pnl_sign_preserved else "REJECT"
    return {"pnl_sign_preserved": pnl_sign_preserved,
            "catastrophic_check": pnl_sign_preserved,
            "sanity_floor": "REMOVED_IN_V2_1",
            "verdict": verdict,
            "shadow_promote_recommendation": "RECOMMEND_SHADOW" if verdict == "PASS" else "REJECT"}
```

## 期待値 (TV から)

USD_JPY M15 365d:
- proposed (V3): PF ~ 1.25-1.35, WR ~ 38-43%, N ~ 400-500, PnL > 0 (TV: PF 1.29 / WR 40.69% / N 467 / PnL +6.26)
- current (legacy): PF ~ 0.95-1.05, WR ~ 33-35%, N ~ 500-700

Codex BT が TV と ±20% 以内一致なら成功と判定。

## Deliverables

1. (Option A) 既存 BT script 環境変数対応のみ修正 + USD_JPY BT 実行
2. (Option B) 新規 BT script + USD_JPY BT 実行
3. `bt-results/sr_fib_confluence-redesign-v3-usdjpy-2026-06-03.json` 生成
4. `final.md` (run dir 直下):
   - TV 数値 vs Codex BT 数値の差分テーブル (N / WR / PF / PnL)
   - verdict と shadow ramp plan
   - **EUR_USD vs USD_JPY 比較表** (どちらを Live promote 主戦場にすべきかの根拠)
5. git commit + push 必須 ([feedback_codex_stash_leak])

## Self-review checklist

- [ ] V3 ロジック呼び出し (`SR_FIB_CONFLUENCE_REDESIGN_V3=1` で `_evaluate_redesign_v3` が動く)
- [ ] MASSIVE cache USD_JPY parquet 確認
- [ ] BT_REQUIRE_MASSIVE_CACHE=1 で Yahoo fallback 禁止
- [ ] v2.1 catastrophic check のみ (sanity floor / PF 閾値要求しない)
- [ ] git commit + push

## Out of scope

- multi-pair BT 拡張 (今回は USD_JPY のみ、6 pair 全部の Codex BT は別タスク)
- universe filter (EUR_JPY/AUD_JPY exclude) — 別タスクで roadmap 化
- Live promotion / shadow worker への USD_JPY V3 配備 (BT 確認まで)

## References

- TV multi-pair check screenshots: `/Users/jg-n-012/test/tradingview-mcp/screenshots/tv_strategy_tester_2026-06-03T11-*.png`
- 先行タスク: `.ai/tasks/queue/20260603-1635-sr-fib-confluence-v3-redesign-bt.md`
- 先行タスク run dir: `.ai/runs/20260603-163807-20260603-1635-sr-fib-confluence-v3-redesign-bt/`
- memory: `[feedback_shadow_first_quant_architecture]`, `[feedback_bt_must_use_massive]`,
  `[feedback_codex_stash_leak]`
