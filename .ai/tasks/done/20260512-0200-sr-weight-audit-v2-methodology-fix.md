---
id: 20260512-0200-sr-weight-audit-v2-methodology-fix
title: "[SR-Redesign] Weight-Gate Audit v2 Methodology Fix + Re-run — passthrough composite weight, dedup, stride 修正"
owner: codex
status: queued
priority: P1
created_at: 2026-05-12T02:00:00+0900
roadmap_gate: "2026-05-11 v2 監査が 5/5 DEAD を返したが、司令塔監査で 4 件の methodology バグが verdict を機械的に DEAD に寄せていることを確認。Phase 2 BT survivor (sr_anti_hunt_bounce) との 2.4×サンプル過大、composite weight の W1=0 強制 zero、own_touch の 16-bar 再計算など。本タスクは line-level patch で修正し再走、verdict を再判定する。"
rule: pre-reg
related:
  - tools/sr_weight_gate_audit_v2.py
  - reports/sr_weight_gate_audit_v2_2026-05-11.md
  - raw/audits/sr_weight_gate_v2_2026-05-11.parquet
  - strategies/daytrade/sr_anti_hunt_bounce.py
  - strategies/daytrade/sr_break_retest.py
  - strategies/daytrade/sr_fib_confluence.py
  - strategies/daytrade/sr_liquidity_grab.py
  - strategies/scalp/sr_channel_reversal.py
---

# 0. 背景: 前回 v2 監査の methodology バグ (司令塔 2026-05-12 監査)

前回 task `20260511-1955-sr-weight-gate-empirical-audit-v2` (commit 92f2e85) は完走したが、`tools/sr_weight_gate_audit_v2.py` に以下 4 件の致命的バグがあり、verdict が **構造的に DEAD に寄せられている**。

## バグ一覧

| # | 場所 | 内容 | 影響 |
|---|---|---|---|
| 1 | `tools/sr_weight_gate_audit_v2.py:529-531` | `_nearest_level_meta` 内で `w1_touch = 0` 無条件上書き、`d1_touch` も極厳条件で {0,1} 化 | 🔴 decisive: composite weight の `×5×w1` と `×3×d1` 係数が事実上機能停止。レポート全体で W1 only / D1+W1 bucket が空 |
| 2 | `tools/sr_weight_gate_audit_v2.py:522-528` | `_nearest_level_meta` 内で own_touch / magnitude を 365d global ではなく **直近 16 bar (4 時間)** で再計算 | 🔴 decisive: 「heavy wall」概念を破壊。globally 8 touches の壁でも局所窓に無ければ own_touch=1 に降格 |
| 3 | `_build_ctx` line 482 で `backtest_mode=True`、stride=1 (anti_hunt / liquidity_grab) | 戦略の `_v2_seen_closed_bar_keys` dedup は `not ctx.backtest_mode` でしか作動しないため、連続バーで重複シグナル多発 | 🟠 high: Phase 2 BT (N=594) vs 本監査 (N=1441) の 2.4× サンプル過大、非独立サンプルで Wilson_lo / EV / CI が破綻 |
| 4 | `detect_sr_levels_with_weight` が KDE-based `sr_detector.detect_sr_levels` を使用 | 本番デモトレーダーは pivot-based `indicators.find_sr_levels_weighted` を使用、level 集合が乖離 | 🟡 medium: Phase 2 BT survivor と本監査の verdict 不整合の主因の 1 つ |

## 前回 verdict の信用度

「5/5 DEAD」は **methodology artifact**。weight thesis の検証になっていない。バグ 1-2 だけでも heavy bucket の composite_weight が正しく計算されておらず、quintile 分割の意味自体が崩れている。

# 1. 目的

1. バグ 1-3 を line-level patch で修正
2. 修正版で 365d × 5 majors × 5 戦略の audit を再走
3. 新 verdict を出力し、前回 v2 (バグ入り) との **横並び比較表** を report に明記
4. bug 4 (detector mismatch) は本タスクのオプション拡張: 余裕があれば pivot-based でも parallel 再走

# 2. 修正仕様 (絶対遵守 — Codex が独自判断で他箇所を改ざんしないこと)

## 2.1 Bug 1+2 修正: `_nearest_level_meta` を passthrough に簡素化

**修正対象**: `tools/sr_weight_gate_audit_v2.py` の `def _nearest_level_meta(...)` 関数 (現 line 502-551)。

**修正後の完全な関数**:

```python
def _nearest_level_meta(
    levels: list[dict],
    price: float | None,
    entry: float,
    df_window=None,
    symbol: str = "USDJPY=X",
) -> dict:
    """Return global-level metadata passthrough.

    Previously this function re-computed own_touch / magnitude on the last
    16 bars and forced w1_touch=0 / d1_touch={0,1}. That destroyed the
    composite_weight semantics computed globally in
    detect_sr_levels_with_weight. We now just return the global metadata
    as-is. df_window / symbol params kept for ABI compat but unused.
    """
    if not levels:
        return {
            "level_price": None,
            "own_touch": 0,
            "d1_touch": 0,
            "w1_touch": 0,
            "round_score": 0.0,
            "magnitude_score": 0.0,
            "composite_weight": 0.0,
            "distinct_touch": 0,
        }
    ref = entry if price is None else price
    lv = min(levels, key=lambda x: abs(float(x["price"]) - float(ref)))
    return {
        "level_price": float(lv["price"]),
        "own_touch": int(lv["own_touch"]),
        "d1_touch": int(lv["d1_touch"]),
        "w1_touch": int(lv["w1_touch"]),
        "round_score": float(lv["round_score"]),
        "magnitude_score": float(lv["magnitude_score"]),
        "composite_weight": float(lv["composite_weight"]),
        "distinct_touch": int(lv["own_touch"]),
    }
```

→ globally 計算された `detect_sr_levels_with_weight` の出力を信用して passthrough する。

## 2.2 Bug 3 修正: stride 引き上げ + post-hoc dedup

### 2.2.1 stride 引き上げ

**修正対象**: `tools/sr_weight_gate_audit_v2.py` の `RUN_STRIDES` 定数 (現 line 50-56)。

**修正後**:

```python
RUN_STRIDES = {
    "sr_anti_hunt_bounce": 4,   # 1→4: 戦略 MAX_HOLD_BARS=12 の 1/3、setup の同一性カバレッジ確保
    "sr_break_retest": 8,        # 維持
    "sr_fib_confluence": 4,      # 2→4: 同上
    "sr_liquidity_grab": 4,     # 1→4
    "sr_channel_reversal": 4,    # 2→4
}
```

### 2.2.2 post-hoc dedup を `run_strategy_bt` に追加

**修正対象**: `tools/sr_weight_gate_audit_v2.py` の `def run_strategy_bt(...)` 関数本体ループ (現 line 621-695)。

**仕様**: signal 記録 (`rows.append(...)`) の直前に **dedup フィルタ** を入れる。

**dedup キー**:
```python
dedup_key = (
    strategy_name,
    symbol.replace("=X", ""),
    cand.signal,                                  # BUY / SELL
    round(meta["level_price"] or 0.0, 5),         # level 同定
    int(df.index[i].value // 10**9 // (15*60*8))  # 2 時間バケット (8 × 15m)
)
```

→ 同一 (戦略, シンボル, 方向, level, 2hr bucket) で **最初の 1 件のみ採用**。後続の同一キーはスキップ。

**実装スケッチ** (関数冒頭付近):
```python
def run_strategy_bt(...):
    ...
    seen_keys: set[tuple] = set()    # post-hoc dedup
    rows = []
    pip = pip_size(symbol)
    for i in range(spec.min_bars, len(df) - 13, max(1, int(stride))):
        ...
        cand = strategy.evaluate(ctx)
        if cand is None or cand.signal not in {"BUY", "SELL"}:
            continue
        ...
        level_price = _extract_level_price(cand, entry, levels)
        meta = _nearest_level_meta(levels, level_price, entry, df_window=df_window, symbol=symbol)

        # ===== post-hoc dedup (bug 3 fix) =====
        dedup_key = (
            strategy_name,
            symbol.replace("=X", ""),
            cand.signal,
            round(meta["level_price"] or 0.0, 5),
            int(df.index[i].value // 10**9 // (15 * 60 * 8)),
        )
        if dedup_key in seen_keys:
            continue
        seen_keys.add(dedup_key)
        # ======================================

        exit_meta = _simulate_exit(...)
        ...
        rows.append({...})
    return pd.DataFrame(rows)
```

## 2.3 Bug 4 オプション拡張 (時間に余裕があれば)

`tools/sr_weight_gate_audit_v2.py` に `--detector pivot` フラグを追加し、`indicators.find_sr_levels_weighted` で level を生成する path を併走可能にする。

**仕様** (実装するなら):
```python
parser.add_argument("--detector", choices=["kde", "pivot"], default="kde",
                    help="kde = sr_detector.detect_sr_levels (default), pivot = indicators.find_sr_levels_weighted")
```

`detect_sr_levels_with_weight` 内で detector を切り替え:
- `kde`: 現状通り
- `pivot`: `find_sr_levels_weighted(df_15m, window=5, tolerance_pct=0.003, min_touches=2)` を呼び、返り値の `(price, strength, touches, days_span, is_strong)` から audit 用 meta dict を組み立てる

pivot path で report に `sr_weight_gate_audit_v2_pivot_<date>.md` を別ファイルで出力。

**本タスクの完了条件としては kde (現状) パスで十分。pivot は時間余裕がなければスキップ可、ただし report に「pivot triangulation skipped due to time budget」と明記**。

# 3. 再走 + 比較表

## 3.1 実行

```bash
.venv/bin/python tools/sr_weight_gate_audit_v2.py --unit-tests
.venv/bin/python tools/sr_weight_gate_audit_v2.py --integration-tests
.venv/bin/python tools/sr_weight_gate_audit_v2.py --all
# (optional, bug 4) .venv/bin/python tools/sr_weight_gate_audit_v2.py --all --detector pivot
```

## 3.2 出力ファイル

- `reports/sr_weight_gate_audit_v2_<date>.md` (kde path, 修正版)
- `raw/audits/sr_weight_gate_v2_<date>.parquet` (kde path 修正版)
- (任意) `reports/sr_weight_gate_audit_v2_pivot_<date>.md`

## 3.3 報告書追加セクション (絶対遵守)

`reports/sr_weight_gate_audit_v2_<date>.md` の Summary の **直前** に以下セクションを挿入:

```markdown
## Methodology Fix Compared to v2 (2026-05-11 buggy run)

| Bug fixed | Location | Before behavior | After behavior |
|---|---|---|---|
| W1 forced zero | _nearest_level_meta | w1_touch=0 unconditional | passthrough from detect_sr_levels_with_weight |
| D1 collapsed to {0,1} | _nearest_level_meta | d1_touch = 1 if (d1>=10 AND w1>=3 AND rscore>0.5) else 0 | passthrough |
| own_touch 16-bar recompute | _nearest_level_meta | recomputed on last 16 bars | passthrough (365d global) |
| stride too small | RUN_STRIDES | 1 for anti_hunt/liq_grab | 4 |
| Adjacent-bar duplicate signals | run_strategy_bt | no dedup (backtest_mode disables strategy dedup) | post-hoc (strategy, symbol, signal, level, 2hr-bucket) dedup |

## v1 (buggy) vs v2 (fixed) Verdict Comparison

| Strategy | v1 verdict | v1 N total | v1 N heavy | v1 WR heavy | v1 EV heavy | v2 verdict | v2 N total | v2 N heavy | v2 WR heavy | v2 EV heavy | Wilson_lo (v2 Bonf) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| sr_anti_hunt_bounce | DEAD | 1441 | 68 | 0.3676 | -4.1755 | <verdict> | ... | ... | ... | ... | ... |
| sr_break_retest | DEAD | 294 | 54 | 0.3148 | -1.7896 | <verdict> | ... | ... | ... | ... | ... |
| sr_fib_confluence | DEAD | 4748 | 708 | 0.3955 | -0.6166 | <verdict> | ... | ... | ... | ... | ... |
| sr_liquidity_grab | DEAD | 6 | 0 | 0.0 | 0.0 | <verdict> | ... | ... | ... | ... | ... |
| sr_channel_reversal | DEAD | 2612 | 876 | 0.2671 | -0.0001 | <verdict> | ... | ... | ... | ... | ... |

## sr_anti_hunt_bounce Triangulation vs SR-weight Phase 2 BT

SR-weight Phase 2 BT (commit 別) では `sr_anti_hunt_bounce` が BH FDR survivor
(trend p=0.0034, N=594)。本監査修正版が N=594 ± 30% (= 416–772) の範囲か、
重要 deviation あれば必ず報告書に明記すること。
```

# 4. 統計プロトコル (pre-registered, v1 から不変)

- Primary heavy threshold: `composite_weight >= 5.0` (HTF source 付きを REBORN_HEAVY 必須条件)
- Exploratory thresholds: [3.0, 4.0, 6.0, 8.0]
- Bonferroni m=5, α=0.01
- Bootstrap CI: 10000 resamples
- Wilson_lo: 95% LB, α=0.01 適用済
- 単一年集中 flag: WR>=0.90 AND N>=10 AND share>=0.5

# 5. テスト要件 (Codex mock-only 罠回避)

## 5.1 Unit tests (修正版で必ず追加)

`tools/sr_weight_gate_audit_v2.py` の `unit_tests()` に以下を追加:

```python
def unit_tests():
    # ... 既存 tests ...

    # ===== Bug 1+2 regression test: _nearest_level_meta must passthrough =====
    fake_levels = [{
        "price": 110.50,
        "own_touch": 5,
        "d1_touch": 3,
        "w1_touch": 2,                 # ← 非ゼロ
        "round_score": 0.7,
        "magnitude_score": 0.6,
        "composite_weight": 1.0*5 + 3.0*3 + 5.0*2 + 2.0*0.7 + 1.5*0.6,  # = 25.3
    }]
    meta = _nearest_level_meta(fake_levels, price=None, entry=110.55,
                               df_window=None, symbol="USD_JPY")
    assert meta["w1_touch"] == 2, f"w1_touch should passthrough, got {meta['w1_touch']}"
    assert meta["d1_touch"] == 3, f"d1_touch should passthrough, got {meta['d1_touch']}"
    assert meta["own_touch"] == 5, f"own_touch should passthrough, got {meta['own_touch']}"
    assert abs(meta["composite_weight"] - 25.3) < 1e-6
    print("[unit] PASS (incl. bug 1+2 regression)", flush=True)
```

## 5.2 Integration tests

既存の `integration_tests()` に以下 assertion を追加:

```python
def integration_tests():
    # ... 既存 ...
    # Bug 1 fix: at least 1 signal must carry w1_touch >= 1 OR d1_touch >= 2
    htf_ok = ((all_rows["w1_touch"] >= 1) | (all_rows["d1_touch"] >= 2)).sum()
    assert htf_ok >= 1, f"Bug 1 regression: no signal had non-trivial HTF touch (htf_ok={htf_ok})"
    # Bug 3 fix: dedup must reduce signal count meaningfully
    # (simple sanity: distinct (strategy, symbol, signal, level, 2hr bucket) ratio >= 0.95)
    ...
```

# 6. 不変条件 (絶対遵守)

- ✋ 戦略の `evaluate()` コードを変更しない
- ✋ `_nearest_level_meta` 以外の audit ロジックは触らない (Codex の自由判断で他箇所を「改善」しないこと)
- ✋ `composite_weight` 計算式 (line 258-265) は変更しない
- ✋ `RUN_STRIDES` 以外の stride 計算は触らない
- ✋ Yahoo データ禁止、`data/cache/massive/*.parquet` のみ
- ✋ post-hoc threshold selection 禁止 — primary は `composite_weight >= 5.0` で pre-reg 不変
- ✋ stash leak 禁止 — final.md は `git log/diff/stash list` で必ず実 verify

# 7. 完了条件

1. `_nearest_level_meta` が §2.1 の passthrough 版に置換 (diff で確認可能)
2. `RUN_STRIDES` が §2.2.1 の値に更新
3. `run_strategy_bt` に §2.2.2 の post-hoc dedup 追加
4. unit_tests + integration_tests に regression test 追加、全 PASS
5. `python3 tools/sr_weight_gate_audit_v2.py --all` 完走
6. `reports/sr_weight_gate_audit_v2_<date>.md` 生成、§3.3 の比較表 3 種を含む
7. `raw/audits/sr_weight_gate_v2_<date>.parquet` 生成
8. PR タイトル: `fix(sr-redesign): weight-gate audit v2 methodology repair + re-run`
9. PR description に v1 vs v2 比較表 + 各バグ修正の commit-by-commit diff 要約
10. final.md に `git log --oneline -5` / `git stash list` (空) / `git status` clean を実 verify した証跡

# 8. 後続タスクとの接続

修正版 verdict 別 next action:
- 任意の戦略が **REBORN_HEAVY** → 個別 redesign 実装タスク (司令塔判断)
- **ALL DEAD でも sr_anti_hunt_bounce が Phase 2 BT N=594 と triangulate しない** → bug 4 (detector mismatch) を確認するため `--detector pivot` 再走を別タスクで投入
- 全 DEAD かつ triangulate OK → weight thesis 棄却、思想再検討フェーズに移行


## Result (2026-05-12T10:22:37Z)

exit=0 · 1195s

```
Implemented and committed.

Commit: `28a1114 fix(sr-redesign): weight-gate audit v2 methodology repair + re-run`

Changed:
- [tools/sr_weight_gate_audit_v2.py](/data/repo/fx-ai-trader/tools/sr_weight_gate_audit_v2.py): `_nearest_level_meta` passthrough, updated `RUN_STRIDES`, post-hoc dedup, regression tests, report comparison sections.
- [reports/sr_weight_gate_audit_v2_2026-05-12.md](/data/repo/fx-ai-trader/reports/sr_weight_gate_audit_v2_2026-05-12.md): fixed KDE audit report with required comparison tables.
- [raw/audits/sr_weight_gate_v2_2026-05-12.parquet](/data/repo/fx-ai-trader/raw/audits/sr_weight_gate_v2_2026-05-12.parquet): rerun raw output.
- [final.md](/data/repo/fx-ai-trader/final.md): PR title/description, v1 vs v2 table, verification summary.

Verification:
- `.venv/bin/python tools/sr_weight_gate_audit_v2.py --unit-tests` passed.
- `.venv/bin/python tools/sr_weight_gate_audit_v2.py --integration-tests` passed.
- `.venv/bin/python tools/sr_weight_gate_audit_v2.py --all` completed and wrote both required outputs.

Final verdict: all five strategies remain `DEAD`. `sr_anti_hunt_bounce` fixed N is `335`, outside Phase 2 BT triangulation band `416-772`, so detector mismatch remains a material follow-up candidate. Pivot triangulation was skipped and explicitly noted in the report.

Final git verification:
```text
git log --oneline -5
28a1114 fix(sr-redesign): weight-gate audit v2 methodology repair + re-run
39fdb43 chore(codex): claim 20260512-0200-sr-weight-audit-v2-methodology-fix
8b7042b task(codex): queue SR weight-gate audit v2 methodology fix [rule:R1]
c558add feat(cfd-trader): MT5経由 OANDA CFD 発注経路 (Section 5.D 3-bucket 分離) (#20)
58b0541 docs(KB): daily report 2026-05-12

git stash list
# empty

git status --short
# clean
```
```
