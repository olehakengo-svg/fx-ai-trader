---
id: 20260604-1513-sr-fib-confluence-v3-resume-bt
priority: P1
gate: R3
rule: R3
status: completed_by_claude
created: 2026-06-04
closed: 2026-06-07
owner: claude
supersedes: 20260603-1635-sr-fib-confluence-v3-redesign-bt
closure_reason: 2026-06-05 新方針 (Codex=review/rescue 層) 下で Claude が一次実装として完走。BT 再実行成功 (elapsed 368.4s)、TV vs Codex ±20% gate FAIL (PF -36/-41%, PnL sign flip)。catastrophic check 機械的 PASS だが PF<1 / PnL負 / Wilson_lo Bonferroni 未達で analyst override REJECT。final.md = .ai/runs/20260607-141500-sr-fib-confluence-v3-resume-bt-claude/final.md
result_verdict: REJECT_BY_ANALYST_OVERRIDE
---

# sr_fib_confluence V3 — RESUME (carry-over from stalled task)

**Rule classification**: R3 (shadow-first redesign、catastrophic check only、stalled task の続行)
**Supersedes**: `20260603-1635-sr-fib-confluence-v3-redesign-bt` (22h stall、V3 strategy 実装まで終了、BT runner 仕上げ未了)

## ⚠️ 前タスクの状況 (重要)

前 Codex companion job `task-mpxr8a35-yhuhti` は 2026-06-03 16:38 JST に起動し、22h 経過時点で log 停止 (2026-06-03 07:40 UTC 以降進捗なし)。すでに companion store からも消えており、auto-expired した模様。

**working tree に残っている成果物** (`git status` で確認可):
- ✅ `strategies/daytrade/sr_fib_confluence.py` — V3 実装 (`_evaluate_redesign_v3`, `_v3_seen_signal_keys`, `_redesign_v3_enabled`, `reset_dedup_state` 更新) 完了
- ✅ `tests/test_sr_fib_confluence_shadow_redesign_v2.py` — V3 回帰テスト追加 (前回 10 passed まで確認済)
- ⚠️ `tools/sr_fib_confluence_redesign_v3_bt.py` — **template copy のみ、diff 未適用** (現状は v2 BT のコピー)
- ❌ BT 実行: 未
- ❌ `bt-results/sr_fib_confluence-redesign-v3-*.json`: 未生成
- ❌ `final.md`: 未生成
- ❌ git commit / push: 未実行

memory `[feedback_codex_stash_leak]` の典型的な stall パターン。working tree から拾って続行する。

## このタスクで Codex がやること

### 1. 既存実装の検証 (read-only)

```bash
cd /Users/jg-n-012/test/fx-ai-trader

# V3 実装が working tree に残っていることを確認
git status --short | grep -E "(sr_fib_confluence|test_sr_fib_confluence)"
git diff strategies/daytrade/sr_fib_confluence.py | head -50

# V3 回帰テスト再実行 (前回 10 passed のはず)
python3 -m pytest -q tests/test_sr_fib_confluence_shadow_redesign_v2.py
```

期待: テスト 10 passed (前回再現)。落ちていたら strategy 側の修正不足を発見した可能性 → 該当箇所修正してから次へ。

### 2. BT runner 仕上げ

`tools/sr_fib_confluence_redesign_v3_bt.py` は現在 v2 BT の単純コピー。以下を差分適用:

```python
# 先頭付近
FLAG = "SR_FIB_CONFLUENCE_REDESIGN_V3"
SHADOW_PROMOTE_FLAG = "SR_FIB_CONFLUENCE_REDESIGN_V3_SHADOW_PROMOTE"
OUTFILE = ROOT / "bt-results" / "sr_fib_confluence-redesign-v3-2026-06-04.json"

# TARGETS は env override 尊重、デフォルトを EUR_USD + USD_JPY に拡張
TARGETS = [
    ("EUR_USD", "EURUSD=X"),
    ("USD_JPY", "USDJPY=X"),
]
# 既存の _TARGET_FILTER ロジックはそのまま (env override 可)

# variant
"variant": "classical_mr_follow_v3"

# _criteria は v2.1 catastrophic check のみ (sanity floor REMOVED)
def _criteria(current, proposed):
    if proposed["N"] < 20:
        return {"verdict": "INSUFFICIENT_BT_EVIDENCE",
                "reason": "proposed BT trades < 20",
                "catastrophic_check": "SKIPPED",
                "shadow_promote_recommendation": "RECOMMEND_SHADOW"}
    err = current.get("bt_error") or proposed.get("bt_error")
    if err:
        return {"verdict": "REJECT", "reason": "bt_error", "bt_error": err,
                "catastrophic_check": False,
                "shadow_promote_recommendation": "REJECT"}
    pnl_sign_preserved = not (current["PnL"] > 0 and proposed["PnL"] < 0)
    pf_change = _num(proposed["PF"]) - _num(current["PF"])
    wilson_change = proposed["wilson_lo"] - current["wilson_lo"]
    n_change_pct = _change_pct(proposed["N"], current["N"])
    verdict = "PASS" if pnl_sign_preserved else "REJECT"
    return {
        "pf_change_warn_only": round(pf_change, 4) if math.isfinite(pf_change) else str(pf_change),
        "wilson_lo_change_warn_only": round(wilson_change, 4),
        "n_change_pct_warn_only": round(n_change_pct, 4) if math.isfinite(n_change_pct) else str(n_change_pct),
        "pnl_sign_preserved": pnl_sign_preserved,
        "catastrophic_check": pnl_sign_preserved,
        "sanity_floor": "REMOVED_IN_V2_1",
        "verdict": verdict,
        "shadow_promote_recommendation": "RECOMMEND_SHADOW" if verdict == "PASS" else "REJECT",
    }

# `_run` 内の env 設定
os.environ[FLAG] = "1" if proposed else "0"
# 念のため V2 も明示的に OFF (V3 が優先されるが、評価順を保証)
os.environ["SR_FIB_CONFLUENCE_REDESIGN_V2"] = "0"
```

ALT_ENTRY_TYPES は legacy 同じく `{"sr_fib_confluence", "ob_retest"}` でよい (V3 path も entry_type="sr_fib_confluence" を返すため)。

その他 helper (`_pnl_r`, `_wilson_lower`, `_pf`, `_stats`, `_change_pct`, `_pnl_sign_preserved`, `_num`, `_compute_sr_fib_only_signal`) は v2 BT と同等で OK。

### 3. BT 実行

```bash
cd /Users/jg-n-012/test/fx-ai-trader
python3 tools/sr_fib_confluence_redesign_v3_bt.py
```

期待出力:
- `bt-results/sr_fib_confluence-redesign-v3-2026-06-04.json` 生成
- stdout に `Overall: PASS|INSUFFICIENT_BT_EVIDENCE|REJECT|BLOCKED_DATA`
- 経過時間 ~10-30 分 (2 pair で BT_MODE で MASSIVE cache 365d)

### 4. 結果検証 (TV 数値との一致確認)

TV (TradingView Pine v6) で得た期待値:

| Pair | TV PF | TV WR | TV N | TV PnL ($) |
|---|---:|---:|---:|---:|
| EUR_USD M15 | 1.194 | 37.62% | 529 | +4.12 |
| USD_JPY M15 | 1.29  | 40.69% | 467 | +6.26 |

Codex BT 結果が TV と **±20% 以内** なら成功と判定 (data source 差・signal pricing 差で完全一致不能、近似一致で OK)。

### 5. final.md 作成

`.ai/runs/<run-dir>/final.md` に以下を含める:

```markdown
# sr_fib_confluence V3 — Resume task BT result

## Background
Stalled task `task-mpxr8a35-yhuhti` の続行。V3 実装は working tree に完了済、BT runner 仕上げから再開。

## Implementation summary
- V3 method: `_evaluate_redesign_v3` (impulse-aware, ADX [20,30], Fib 38.2/61.8 only, EMA filter なし)
- env flag: SR_FIB_CONFLUENCE_REDESIGN_V3=1
- Tests: 10 passed (incl. V3 dedup / regression / flag priority)

## BT result vs TV expectation

| Pair | TV PF | Codex PF | TV WR | Codex WR | TV N | Codex N | Verdict |
|---|---:|---:|---:|---:|---:|---:|---|
| EUR_USD | 1.194 | ... | 37.62% | ... | 529 | ... | PASS/FAIL |
| USD_JPY | 1.29  | ... | 40.69% | ... | 467 | ... | PASS/FAIL |

## Catastrophic check (v2.1)
- pnl_sign_preserved: ...
- proposed.N >= 20: ...
- overall verdict: ...

## Shadow ramp plan
- (recommend) EUR_USD shadow 30d N>=30 蓄積 → Wilson_lo + Bonferroni 検査 → Live promote 検討
- (recommend) USD_JPY 同様、PF 1.29 想定で Live ramp 主戦場化候補

## Self-review checklist
- [x] impulse-aware classical fib
- [x] EMA filter なし
- [x] ADX [20,30] 両端含む
- [x] Fib 38.2/61.8 のみ、50% mid 除外
- [x] MASSIVE cache 強制
- [x] v2.1 catastrophic check のみ
- [x] V2 flag と V3 flag の優先順位 (V3 > V2 > legacy)
- [x] reset_dedup_state で V2 と V3 両方 clear
- [x] git commit + push 完了

## Files committed
- strategies/daytrade/sr_fib_confluence.py
- tests/test_sr_fib_confluence_shadow_redesign_v2.py
- tools/sr_fib_confluence_redesign_v3_bt.py
- bt-results/sr_fib_confluence-redesign-v3-2026-06-04.json
```

### 6. git commit + push (必須)

```bash
cd /Users/jg-n-012/test/fx-ai-trader

# 関係 file だけ stage (他の dirty file は触らない)
git add strategies/daytrade/sr_fib_confluence.py
git add tests/test_sr_fib_confluence_shadow_redesign_v2.py
git add tools/sr_fib_confluence_redesign_v3_bt.py
git add bt-results/sr_fib_confluence-redesign-v3-2026-06-04.json

git status --short  # 確認
git commit -m "feat(strategies): sr_fib_confluence V3 redesign — Classical MR+Follow impulse-aware

V3 implementation:
- impulse direction detection (high_age vs low_age) replaces EMA-based direction
- Fib 38.2 / 61.8 only (50% mid excluded — TV BT confirms 50% mid is noise source)
- ADX [20, 30] chop band (avoid super-strong trend overshoot)
- env flag SR_FIB_CONFLUENCE_REDESIGN_V3 (default off, V2 と排他、V3 優先)

BT result (EUR_USD + USD_JPY M15 365d, MASSIVE cache):
- EUR_USD: PF=..., WR=..., N=..., PnL=...
- USD_JPY: PF=..., WR=..., N=..., PnL=...
- TV reference: EUR_USD PF 1.194, USD_JPY PF 1.29
- v2.1 catastrophic check: PASS

Carry-over from stalled task 20260603-1635-sr-fib-confluence-v3-redesign-bt
(prev Codex job task-mpxr8a35-yhuhti, 22h stall before BT runner finalization)

Tests: 10 passed
Shadow ramp: TBD per pair (recommend EUR_USD + USD_JPY for Live promote)

[rule:R3] [gate:catastrophic-only]
"

git push origin main
```

## Accept gate (v2.1 catastrophic check only)

- proposed N >= 20 per pair
- pnl_sign_preserved = NOT (current.PnL > 0 AND proposed.PnL < 0)
- final verdict per pair: PASS / INSUFFICIENT_BT_EVIDENCE / REJECT
- overall_verdict: PASS (全 pair PASS) / INSUFFICIENT_BT_EVIDENCE (一部 N不足) / REJECT (一部 REJECT)

## Self-review checklist

- [ ] V3 method 既に存在することを確認 (working tree から)
- [ ] V3 回帰 tests 10 passed
- [ ] BT runner 差分適用 (FLAG/OUTFILE/TARGETS/_criteria/variant)
- [ ] TARGETS は `[EUR_USD, USD_JPY]` (env override 可)
- [ ] BT 実行成功 (bt-results JSON 生成)
- [ ] Codex BT が TV ±20% 以内一致
- [ ] final.md 作成 (TV vs Codex 比較テーブル + shadow ramp plan)
- [ ] git commit + **push 到達** (`git push origin main` の exit code 0)
- [ ] 他の dirty file (data/cache/.../*.parquet, AGENTS.md 等) は触らない

## Out of scope

- multi-pair BT 拡張 (今回 EUR_USD + USD_JPY のみ、GBP_USD 等は別タスクで)
- Live promotion / OANDA bridge 設定
- SHORT only / hybrid variant の prod 実装 (今回 combined のみ)

## References

- 前 stalled task: `.ai/tasks/queue/20260603-1635-sr-fib-confluence-v3-redesign-bt.md`
- 前 run dir: `.ai/runs/20260603-163807-20260603-1635-sr-fib-confluence-v3-redesign-bt/`
- 前 job log: `/Users/jg-n-012/.claude/plugins/data/codex-inline/state/fx-ai-trader-77445e4e87c6fe70/jobs/task-mpxr8a35-yhuhti.log`
- TV multi-pair screenshots: `/Users/jg-n-012/test/tradingview-mcp/screenshots/tv_strategy_tester_2026-06-03T*.png`
- memory: `[feedback_codex_stash_leak]`, `[feedback_shadow_first_quant_architecture]`, `[feedback_bt_must_use_massive]`
