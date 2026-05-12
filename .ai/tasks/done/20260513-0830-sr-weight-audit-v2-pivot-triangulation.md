---
id: 20260513-0830-sr-weight-audit-v2-pivot-triangulation
title: "[SR-Redesign] Weight-Gate Audit v2 Pivot Triangulation — find_sr_levels_weighted で検出器を切替、Phase 2 BT N=594 と triangulation"
owner: codex
status: queued
priority: P1
created_at: 2026-05-13T08:30:00+0900
roadmap_gate: "2026-05-12 v2 fixed audit (commit 28a1114) で 5/5 DEAD 維持だが sr_anti_hunt_bounce N=335 が Phase 2 BT N=594 の triangulation band (416-772) 外。KDE detector (sr_detector.detect_sr_levels) vs 本番 demo trader が使う pivot detector (indicators.find_sr_levels_weighted) の divergence が verdict の主因仮説。本タスクは pivot detector path を実装し再走、Phase 2 BT との N triangulation + 3-way verdict 比較を出す。"
rule: pre-reg
related:
  - tools/sr_weight_gate_audit_v2.py
  - modules/indicators.py
  - modules/sr_detector.py
  - reports/sr_weight_gate_audit_v2_2026-05-12.md
  - raw/audits/sr_weight_gate_v2_2026-05-12.parquet
---

# 0. 背景

## 0.1 直近 audit 結果 (commit 28a1114, 2026-05-12)

methodology bug 4 件修正後の v2 fixed audit:

| Strategy | v2 fixed N | v2 WR_heavy | v2 EV_heavy | Verdict |
|---|---:|---:|---:|---|
| sr_anti_hunt_bounce | 335 | 44.98% | -2.93 | DEAD |
| sr_break_retest | 294 | 29.45% | -0.86 | DEAD |
| sr_fib_confluence | 2037 | 37.26% | -0.88 | DEAD |
| sr_liquidity_grab | 2 | 50.00% | +25.75 | DEAD (N too small) |
| sr_channel_reversal | 1249 | 25.16% | -0.33 | DEAD |

## 0.2 Phase 2 BT との triangulation 失敗

- Phase 2 BT (commit 別): `sr_anti_hunt_bounce` BH FDR survivor (trend p=0.0034, **N=594**)
- v2 fixed audit: **N=335** → triangulation band (416-772) の **外**
- 同じ戦略・同じ期間・同じ MASSIVE データなので N divergence は **detector の違い** が主因仮説
  - v2 audit: `modules.sr_detector.detect_sr_levels` (KDE-based clustering on price density)
  - 本番 demo trader / Phase 2 BT: `modules.indicators.find_sr_levels_weighted` (pivot-based, Williams Fractal + tolerance clustering)
- v2 audit report も明示: "detector mismatch remains a candidate explanation"

## 0.3 quintile が edge を全く discriminate しなかった追加発見

v2 fixed (commit 28a1114) で composite_weight quintile (mean weight 36 → 154) を見ても WR は 43-49% で平坦。「heavy walls = エッジ」仮説が **KDE detector** で支持されない。pivot detector でも同じパターンが再現すれば仮説真の falsification、異なれば detector が真因。

# 1. 目的

1. `tools/sr_weight_gate_audit_v2.py` に `--detector {kde,pivot}` フラグを追加
2. `pivot` モードでは `modules.indicators.find_sr_levels_weighted` を own-TF / HTF detector として使用
3. HTF projection / composite weight / post-hoc dedup / stride / pre-reg 統計プロトコルは **全て v2 fixed と完全同一**
4. pivot 再走し以下を出力:
   - `reports/sr_weight_gate_audit_v2_pivot_<date>.md` (独立レポート、3-way 比較表入り)
   - `raw/audits/sr_weight_gate_v2_pivot_<date>.parquet`
5. sr_anti_hunt_bounce N が triangulation band (416-772) に入るかを明示判定

# 2. 修正仕様 (絶対遵守 — 既存 v2 fixed のロジックは触らない)

## 2.1 CLI フラグ追加

**修正対象**: `tools/sr_weight_gate_audit_v2.py` の `def main()` (現 line ~1180)。

```python
def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true", help="run full 5 strategy x 5 pair audit")
    parser.add_argument("--unit-tests", action="store_true")
    parser.add_argument("--integration-tests", action="store_true")
    parser.add_argument("--limit-symbols", type=int, default=None, help="debug only")
    parser.add_argument("--limit-bars", type=int, default=None, help="debug only")
    parser.add_argument(
        "--detector",
        choices=["kde", "pivot"],
        default="kde",
        help="kde = sr_detector.detect_sr_levels (default), pivot = indicators.find_sr_levels_weighted (Williams Fractal + tolerance clustering, matches production demo_trader)",
    )
    args = parser.parse_args()
    if args.unit_tests:
        unit_tests()
        return 0
    if args.integration_tests:
        integration_tests(detector=args.detector)
        return 0
    if args.all:
        run_all(limit_symbols=args.limit_symbols, limit_bars=args.limit_bars,
                detector=args.detector)
        return 0
    parser.print_help()
    return 2
```

## 2.2 `detect_sr_levels_with_weight` を detector で分岐

**修正対象**: `tools/sr_weight_gate_audit_v2.py:287` `def detect_sr_levels_with_weight(...)`.

**修正後の完全な関数** (既存 KDE path は保持しつつ pivot path を分岐):

```python
def detect_sr_levels_with_weight(
    df,
    htf_df_d1,
    htf_df_w1,
    tolerance_pip: float,
    min_touches: int,
    symbol: str = "USDJPY=X",
    detector: str = "kde",
) -> list[dict]:
    """Detect levels with composite weight metadata.

    detector="kde"   : sr_detector.detect_sr_levels (existing v2 fixed behavior)
    detector="pivot" : indicators.find_sr_levels_weighted (Williams Fractal,
                       matches production demo_trader / Phase 2 BT methodology)

    All downstream metadata (own_touch / d1_touch / w1_touch / round_score /
    magnitude_score / composite_weight) is computed identically regardless of
    detector — only the candidate level set differs.
    """
    pip = pip_size(symbol)
    tolerance = tolerance_pip * pip
    atr_own = _atr_series(df)
    atr_d1 = _atr_series(htf_df_d1) if len(htf_df_d1) else atr_own
    atr_w1 = _atr_series(htf_df_w1) if len(htf_df_w1) else atr_own
    d1_tol_pip = max(float(atr_d1.median()) * 0.3 / pip, tolerance_pip)
    w1_tol_pip = max(float(atr_w1.median()) * 0.3 / pip, tolerance_pip)
    d1_match = max(float(atr_d1.median()) * 0.5, tolerance)

    if detector == "pivot":
        own_raw, d1_raw, w1_raw = _pivot_levels(
            df, htf_df_d1, htf_df_w1,
            tolerance_pip=tolerance_pip,
            d1_tol_pip=d1_tol_pip,
            w1_tol_pip=w1_tol_pip,
            min_touches=min_touches,
        )
    elif detector == "kde":
        from modules.sr_detector import detect_sr_levels
        own_raw = detect_sr_levels(
            df, symbol,
            bandwidth_pips=max(5.0, tolerance_pip * 1.5),
            touch_tolerance_pips=tolerance_pip,
            min_touches=min_touches, max_levels=30,
        )
        d1_raw = detect_sr_levels(
            htf_df_d1, symbol,
            bandwidth_pips=max(5.0, d1_tol_pip * 1.5),
            touch_tolerance_pips=d1_tol_pip,
            min_touches=2, max_levels=20,
        ) if len(htf_df_d1) >= 5 else []
        w1_raw = detect_sr_levels(
            htf_df_w1, symbol,
            bandwidth_pips=max(5.0, w1_tol_pip * 1.5),
            touch_tolerance_pips=w1_tol_pip,
            min_touches=2, max_levels=20,
        ) if len(htf_df_w1) >= 5 else []
    else:
        raise ValueError(f"unknown detector: {detector}")

    levels = []
    for lv in own_raw:
        price = _srlevel_price(lv)
        own_touch = count_distinct_touches(df, price, tolerance, min_gap_bars=5)
        if own_touch < min_touches:
            continue
        d1_hits = [x for x in d1_raw if abs(_srlevel_price(x) - price) <= d1_match]
        w1_hits = [x for x in w1_raw if abs(_srlevel_price(x) - price) <= d1_match]
        d1_touch = (
            count_distinct_touches(htf_df_d1, price, d1_tol_pip * pip, min_gap_bars=2)
            if d1_hits else 0
        )
        w1_touch = (
            count_distinct_touches(htf_df_w1, price, w1_tol_pip * pip, min_gap_bars=1)
            if w1_hits else 0
        )
        mag_raw = median_rejection_size(df, price, tolerance, atr_own)
        meta = {
            "price": float(price),
            "touch_count": int(_srlevel_touch(lv)),
            "own_touch": int(own_touch),
            "d1_touch": int(d1_touch),
            "w1_touch": int(w1_touch),
            "round_score": round_score(price, pip),
            "magnitude_score": float(min(1.0, mag_raw)),
            "magnitude_raw": float(mag_raw),
            "distinct_touch_events": int(own_touch),
            "strength": float(_srlevel_strength(lv)),
            "obviousness": float(getattr(lv, "obviousness", lv.get("strength", 0.0) if isinstance(lv, dict) else 0.0)),
        }
        meta["composite_weight"] = float(composite_weight(meta))
        meta["touches"] = meta["own_touch"]
        meta["is_strong"] = bool(meta["composite_weight"] >= PRIMARY_HEAVY_THRESHOLD)
        levels.append(meta)
    levels.sort(key=lambda x: (-x["composite_weight"], x["price"]))
    return levels
```

## 2.3 `_pivot_levels` ヘルパ追加

**新規関数** (`detect_sr_levels_with_weight` の直前あたりに挿入):

```python
def _pivot_levels(
    df, htf_df_d1, htf_df_w1,
    tolerance_pip: float,
    d1_tol_pip: float,
    w1_tol_pip: float,
    min_touches: int,
):
    """Pivot-based detector adapter — wraps indicators.find_sr_levels_weighted
    to provide a level set comparable to production demo_trader.

    Returns: (own_levels, d1_levels, w1_levels) — each a list of dicts with
    at minimum 'price' and 'touches' keys, matching the structure expected
    by the downstream level metadata loop.
    """
    from modules.indicators import find_sr_levels_weighted

    # Tolerance conversions: pip → fractional. own TF 15m bars_per_day=96, D1=1, W1=1/7.
    # find_sr_levels_weighted uses tolerance_pct (fractional), so convert via mid price.
    def _frac_tol(df_, tol_pip):
        if len(df_) == 0:
            return 0.003
        mid = float(df_["Close"].iloc[-1])
        pip = 0.01 if mid > 50 else 0.0001  # rough JPY detection by price magnitude
        return max(1e-4, (tol_pip * pip) / mid)

    own_pct = _frac_tol(df, tolerance_pip)
    d1_pct = _frac_tol(htf_df_d1 if len(htf_df_d1) else df, d1_tol_pip)
    w1_pct = _frac_tol(htf_df_w1 if len(htf_df_w1) else df, w1_tol_pip)

    own = find_sr_levels_weighted(
        df, window=5, tolerance_pct=own_pct,
        min_touches=min_touches, max_levels=30, bars_per_day=96,
    )
    d1 = find_sr_levels_weighted(
        htf_df_d1, window=5, tolerance_pct=d1_pct,
        min_touches=2, max_levels=20, bars_per_day=1,
    ) if len(htf_df_d1) >= 12 else []
    w1 = find_sr_levels_weighted(
        htf_df_w1, window=3, tolerance_pct=w1_pct,
        min_touches=2, max_levels=20, bars_per_day=1,
    ) if len(htf_df_w1) >= 8 else []
    return own, d1, w1


def _srlevel_strength(level):
    """Return obviousness/strength score, robust to both KDE objects and pivot dicts."""
    if isinstance(level, dict):
        return float(level.get("strength", level.get("obviousness", 0.0)) or 0.0)
    return float(getattr(level, "obviousness", 0.0) or 0.0)
```

注意:
- `_srlevel_price` / `_srlevel_touch` は既存ヘルパで dict / object 両対応済 (line 270-285)
- pivot dict は `{price, touches, days_span, strength, is_strong, type}` で `touches` key 有り → `_srlevel_touch` の `level.get("touches", 0)` で正しく動作
- `_srlevel_strength` を新規追加して strength と obviousness の両キーを参照

## 2.4 `run_all` を detector 対応に

**修正対象**: `tools/sr_weight_gate_audit_v2.py:1056` `def run_all(...)`.

シグネチャ + 関数本体修正:

```python
def run_all(limit_symbols: int | None = None, limit_bars: int | None = None,
            detector: str = "kde"):
    import pandas as pd

    started = time.time()
    frames = []
    selected_targets = TARGETS[:limit_symbols] if limit_symbols else TARGETS
    for pair, symbol in selected_targets:
        print(f"[audit] loading {pair} (detector={detector})", flush=True)
        df15 = load_data(symbol, "15m")
        if limit_bars:
            df15 = df15.tail(limit_bars).copy()
        df1h = load_data(symbol, "1h")
        df1h = df1h.loc[df1h.index >= df15.index.min()].copy()
        d1 = resample_htf(df1h, "1D")
        w1 = resample_htf(df1h, "1W")
        tol_pip = max(float(df15["atr"].median()) * 0.30 / pip_size(symbol), 3.0)
        levels = detect_sr_levels_with_weight(
            df15, d1, w1, tol_pip, min_touches=2,
            symbol=symbol, detector=detector,
        )
        print(f"[audit] {pair}: weighted levels={len(levels)}", flush=True)
        for strategy in STRATEGIES:
            print(f"[audit] {pair} {strategy}", flush=True)
            rows = run_strategy_bt(
                strategy, df15, levels, symbol=symbol,
                stride=RUN_STRIDES.get(strategy, 1),
            )
            print(f"[audit] {pair} {strategy}: signals={len(rows)}", flush=True)
            frames.append(rows)
    all_rows = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    suffix = f"_{detector}" if detector != "kde" else ""
    raw_path = ROOT / "raw" / "audits" / f"sr_weight_gate_v2{suffix}_{today}.parquet"
    report_path = ROOT / "reports" / f"sr_weight_gate_audit_v2{suffix}_{today}.md"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    all_rows.to_parquet(raw_path, index=False)
    verdicts, summary_rows = write_report(all_rows, report_path, detector=detector)
    write_redesign_drafts(verdicts)
    print(f"[audit] wrote {raw_path.relative_to(ROOT)}", flush=True)
    print(f"[audit] wrote {report_path.relative_to(ROOT)}", flush=True)
    print(f"[audit] elapsed_s={time.time() - started:.1f}", flush=True)
    return all_rows, raw_path, report_path, summary_rows
```

## 2.5 `write_report` に detector 引数 + 3-way 比較セクション

**修正対象**: `def write_report(all_rows, report_path, ...)` シグネチャに `detector: str = "kde"` 追加。

レポートの **Summary の直前** に以下セクション挿入 (pivot mode 時のみ):

```markdown
## 3-Way Detector Comparison (only present when --detector pivot)

| Strategy | v1 (buggy KDE) verdict | v1 N | v2 fixed KDE (28a1114) verdict | v2 fixed KDE N | v2 fixed PIVOT verdict | v2 fixed PIVOT N | sr_anti_hunt triangulation status (band 416-772) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| sr_anti_hunt_bounce | DEAD | 1441 | DEAD | 335 | <verdict> | <N> | <IN_BAND / OUT_OF_BAND> |
| sr_break_retest | DEAD | 294 | DEAD | 294 | <verdict> | <N> | — |
| sr_fib_confluence | DEAD | 4748 | DEAD | 2037 | <verdict> | <N> | — |
| sr_liquidity_grab | DEAD | 6 | DEAD | 2 | <verdict> | <N> | — |
| sr_channel_reversal | DEAD | 2612 | DEAD | 1249 | <verdict> | <N> | — |

## Phase 2 BT Triangulation (sr_anti_hunt_bounce)

- Phase 2 BT reported N=594 (BH FDR survivor, trend p=0.0034)
- v2 fixed KDE: N=335 (OUT_OF_BAND, deviation -43.6%)
- v2 fixed PIVOT: N=<N_pivot> (<IN_BAND/OUT_OF_BAND>, deviation <pct>%)
- Conclusion: <detector divergence is/is not the explanatory variable>
```

KDE モード時は既存通り `Methodology Fix` + `v1 vs v2` 表のみ。

## 2.6 unit_tests / integration_tests 更新

`unit_tests()` に pivot dict 互換性テスト追加:

```python
def unit_tests():
    # ... 既存 tests including passthrough regression ...

    # Pivot dict adapter compatibility
    pivot_lv = {"price": 110.5, "touches": 4, "days_span": 30.0,
                "strength": 0.7, "is_strong": True, "type": "support"}
    assert _srlevel_price(pivot_lv) == 110.5
    assert _srlevel_touch(pivot_lv) == 4
    assert _srlevel_strength(pivot_lv) == 0.7
    print("[unit] PASS (incl. bug 1+2 regression + pivot adapter)", flush=True)
```

`integration_tests()` に detector 引数追加:

```python
def integration_tests(detector: str = "kde"):
    unit_tests()
    samples = []
    for _pair, symbol in TARGETS:
        df15 = load_data(symbol, "15m").tail(5000).copy()
        df1h = load_data(symbol, "1h")
        df1h = df1h.loc[df1h.index >= df15.index.min()].copy()
        levels = detect_sr_levels_with_weight(
            df15, resample_htf(df1h, "1D"), resample_htf(df1h, "1W"),
            tolerance_pip=max(float(df15["atr"].median()) * 0.30 / pip_size(symbol), 3.0),
            min_touches=2, symbol=symbol, detector=detector,
        )
        assert len(levels) >= 1, f"detect_sr_levels_with_weight({detector}) returned no levels"
        samples.append((symbol, df15, levels))
    # ... 既存ロジック維持 ...
```

# 3. 実行 + 出力

## 3.1 実行コマンド

```bash
.venv/bin/python tools/sr_weight_gate_audit_v2.py --unit-tests
.venv/bin/python tools/sr_weight_gate_audit_v2.py --integration-tests --detector pivot
.venv/bin/python tools/sr_weight_gate_audit_v2.py --all --detector pivot
# 既存 KDE 結果は変更せずに残す (今回 KDE 再走は不要)
```

## 3.2 出力ファイル (pivot 専用、KDE の既存出力は触らない)

- `reports/sr_weight_gate_audit_v2_pivot_<date>.md` (3-way 比較表入り)
- `raw/audits/sr_weight_gate_v2_pivot_<date>.parquet`

## 3.3 Triangulation verdict 明示

報告書末尾に明記:

```markdown
## Verdict on Detector Hypothesis

- v2 fixed KDE sr_anti_hunt_bounce N=335 (outside Phase 2 BT band 416-772)
- v2 fixed PIVOT sr_anti_hunt_bounce N=<N_pivot>
- Decision rule:
  - If pivot N in [416, 772]: detector mismatch CONFIRMED → next action: align production
    demo_trader and audit on same detector for consistent edge testing
  - If pivot N still outside band: detector NOT the main cause → next action: investigate
    Phase 2 BT methodology (e.g., different SL/TP geometry, different exit conditions)
- Verdict reproducibility across detectors:
  - If pivot also returns all 5 DEAD: weight thesis truly falsified, pivot to alternative
    SR design axes (rejection magnitude, TP geometry, regime gate)
  - If pivot reborn any strategy: detector-dependent edge — significant
```

# 4. 統計プロトコル (v2 fixed から完全不変)

- Primary heavy threshold: `composite_weight >= 5.0` (HTF source 必須)
- Exploratory thresholds: [3.0, 4.0, 6.0, 8.0]
- Bonferroni m=5, α=0.01
- Bootstrap CI: 10000 resamples
- Wilson_lo: 95% LB, α=0.01 適用済

# 5. 不変条件 (絶対遵守)

- ✋ 戦略の `evaluate()` コードを変更しない
- ✋ KDE path の既存ロジック (line 287-360 内 KDE branch) を変更しない
- ✋ `composite_weight` 計算式を変更しない
- ✋ `RUN_STRIDES` を変更しない
- ✋ post-hoc dedup (run_strategy_bt 内) のロジックを変更しない
- ✋ pre-reg threshold 5.0 を post-hoc に変更しない
- ✋ 既存 KDE 出力 `reports/sr_weight_gate_audit_v2_2026-05-12.md` を **絶対に上書きしない**
- ✋ Yahoo データ禁止、`data/cache/massive/*.parquet` のみ
- ✋ stash leak 禁止 — final.md で `git log/diff/stash list` 実 verify

# 6. 完了条件

1. `tools/sr_weight_gate_audit_v2.py` に `--detector {kde,pivot}` フラグ追加 (diff で確認可能)
2. `detect_sr_levels_with_weight` が `detector="pivot"` で `find_sr_levels_weighted` を呼ぶ
3. `_pivot_levels` / `_srlevel_strength` ヘルパが追加されている
4. `write_report` が detector で出力ファイル名を切替 + 3-way 比較表挿入
5. unit_tests + integration_tests (pivot mode) 全 PASS
6. `python3 tools/sr_weight_gate_audit_v2.py --all --detector pivot` 完走
7. `reports/sr_weight_gate_audit_v2_pivot_<date>.md` 生成 (3-way + triangulation セクション含む)
8. `raw/audits/sr_weight_gate_v2_pivot_<date>.parquet` 生成
9. PR タイトル: `feat(sr-redesign): pivot detector triangulation for weight-gate audit v2`
10. PR description に 3-way verdict table + sr_anti_hunt_bounce triangulation status
11. final.md に `git log --oneline -5` / `git stash list` (空) / `git status` clean を実 verify した証跡
12. 既存 KDE 出力 `reports/sr_weight_gate_audit_v2_2026-05-12.md` が **未変更** であることを diff で確認

# 7. 後続タスクとの接続

triangulation 結果別 next action:
- **pivot で sr_anti_hunt_bounce N が 416-772 内** + 5/5 DEAD → detector は説明変数だが verdict は不変 → weight thesis 棄却。次は SL/TP geometry 軸への pivot
- **pivot で N 整合 + REBORN_HEAVY 発生** → detector 依存の edge 存在 → 本番 demo trader を audit detector に揃える design 検討
- **pivot でも N が band 外** → Phase 2 BT methodology 自体に未把握の divergence → Phase 2 BT スクリプト直接監査タスク


## Result (2026-05-12T15:50:23Z)

exit=0 · 624s

```
実装・実行・commit まで完了しました。

PR title:
`feat(sr-redesign): pivot detector triangulation for weight-gate audit v2`

Commit:
`512f773 feat(sr-redesign): pivot detector triangulation for weight-gate audit v2`

変更:
- [tools/sr_weight_gate_audit_v2.py](/data/repo/fx-ai-trader/tools/sr_weight_gate_audit_v2.py): `--detector {kde,pivot}` 追加、pivot adapter 追加、report の 3-way/triangulation セクション追加
- [reports/sr_weight_gate_audit_v2_pivot_2026-05-12.md](/data/repo/fx-ai-trader/reports/sr_weight_gate_audit_v2_pivot_2026-05-12.md): pivot audit report
- [raw/audits/sr_weight_gate_v2_pivot_2026-05-12.parquet](/data/repo/fx-ai-trader/raw/audits/sr_weight_gate_v2_pivot_2026-05-12.parquet): pivot raw output
- [final.md](/data/repo/fx-ai-trader/final.md): PR description / verdict / verification summary 更新

結果:
- `sr_anti_hunt_bounce` pivot N = `140`
- Phase 2 BT band `[416, 772]` に対して `OUT_OF_BAND`
- 結論: detector mismatch だけでは Phase 2 BT との N divergence を説明できない
- pivot でも 5/5 `DEAD`

検証:
```text
.venv/bin/python -m py_compile tools/sr_weight_gate_audit_v2.py
.venv/bin/python tools/sr_weight_gate_audit_v2.py --unit-tests
.venv/bin/python tools/sr_weight_gate_audit_v2.py --integration-tests --detector pivot
.venv/bin/python tools/sr_weight_gate_audit_v2.py --all --detector pivot
```

最終 git verify:
```text
git log --oneline -5
512f773 feat(sr-redesign): pivot detector triangulation for weight-gate audit v2
d186357 chore(codex): claim 20260513-0830-sr-weight-audit-v2-pivot-triangulation
3020de4 task(codex): queue SR weight-gate audit v2 pivot triangulation [rule:R1]
140c802 docs(KB): R2 alert 2026-05-12T14:21Z
7d81c46 docs(KB): monitor alert 2026-05-12

git stash list
# empty

git status --short
# clean
```

既存 KDE output への diff も空でした:
`reports/sr_weight_gate_audit_v2_2026-05-12.md` / `raw/audits/sr_weight_gate_v2_2026-05-12.parquet` は未変更です。
```
