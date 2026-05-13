---
id: 20260513-1030-sr-weight-phase2-vs-audit-v2-divergence-forensic
title: "[SR-Redesign] Phase 2 BT vs Audit v2 Methodology Divergence Forensic — N=594 vs N=140/335 の原因を pure-audit で特定"
owner: codex
status: queued
priority: P1
created_at: 2026-05-13T10:30:00+0900
roadmap_gate: "v2 fixed audit (KDE N=335 / PIVOT N=140) と Phase 2 BT (N=594) が両 detector で triangulate しない。3 way 監査で原因を特定し、どちらの methodology が真かを decision に落とす。本タスクは pure-audit (コード未変更) で divergence を完全マップ化することが目的。"
rule: pre-reg
related:
  - tools/sr_weight_phase2_bin_bhfdr.py
  - tools/sr_weight_gate_audit_v2.py
  - app.py
  - strategies/daytrade/sr_anti_hunt_bounce.py
  - modules/indicators.py
  - modules/sr_detector.py
  - bt-results/sr-weight-phase2-bin-bhfdr-2026-05-11.json
  - reports/sr_weight_gate_audit_v2_2026-05-12.md
  - reports/sr_weight_gate_audit_v2_pivot_2026-05-12.md
---

# 0. 背景

## 0.1 N mismatch (sr_anti_hunt_bounce, 365d MASSIVE, 5 majors)

| Methodology | N | EV pip | 出典 |
|---|---:|---:|---|
| Phase 2 BT (`tools/sr_weight_phase2_bin_bhfdr.py`) | **594** | (BH FDR survivor, p=0.0034) | commit `1eabe84` |
| v2 fixed audit KDE detector | 335 | -2.91 | commit `28a1114` |
| v2 fixed audit PIVOT detector | **140** | +1.06 | commit `512f773` |

同期間 (365d)、同データ (MASSIVE parquet)、同戦略 (`sr_anti_hunt_bounce`)、同 5 majors にもかかわらず **N が 4.2 倍** ずれる。pivot detector に揃えても band 外。

## 0.2 観察された主要 methodology 差

`tools/sr_weight_phase2_bin_bhfdr.py` は **`app.run_daytrade_backtest`** を呼んで戦略を実行 (production-style BT runner)。`compute_daytrade_signal` を monkey-patch して per-bar に `SrAntiHuntBounce().evaluate(ctx)` を呼ぶ。

`tools/sr_weight_gate_audit_v2.py` は **独自 bar loop** で `_simulate_exit` / `_build_ctx` / `_prefilter_strategy_bar` を実装し、`evaluate()` のみを共通使用。

→ 同じ `evaluate()` を呼んでいるが、**呼び出し前後の bar 選別 / sr_levels populate / exit 計算 / dedup** が完全に違う pipeline。

# 1. 目的 (pure-audit, コード一切変更しない)

1. Phase 2 BT (`sr_weight_phase2_bin_bhfdr.py` → `app.run_daytrade_backtest` → `compute_daytrade_signal` → `evaluate`) の **完全 call graph** を mapping
2. v2 audit (`sr_weight_gate_audit_v2.py` の `run_strategy_bt`) の **完全 call graph** を mapping
3. 両 pipeline の **divergence point を全 列挙** (bar iteration cadence / sr_levels source / ctx population / SL-TP exit / dedup / pair filtering / regime gate / 各種 indicator 計算等)
4. divergence 1 つずつについて **「N=594 vs 335/140」のどちらに寄与しうるか定量的見積もり**
5. 最終 verdict: どの divergence が **N=594 の正体** か (single dominant か多要因か)
6. decision recommendation: 今後の SR audit は (a) Phase 2 BT pipeline に統一 / (b) v2 audit pipeline に統一 / (c) 両方併走 のどれが正解か

# 2. 監査スコープ (pure-audit 限定)

## 2.1 静的コード解析

以下 3 ファイルを完全に読み、関数間 call graph を生成:
- `tools/sr_weight_phase2_bin_bhfdr.py` (Phase 2 BT runner)
- `app.py` の `run_daytrade_backtest`, `compute_daytrade_signal`, `add_indicators` 周辺
- `tools/sr_weight_gate_audit_v2.py` (v2 audit runner)

各 pipeline の以下を関数 + 行番号付きで mapping:
| 軸 | Phase 2 BT (path / line) | v2 audit (path / line) | 一致/相違 |
|---|---|---|---|
| Bar iteration cadence (stride / 全 bar / dedup) | … | … | … |
| `sr_levels` 取得方法 | … | … | … |
| `ctx` (SignalContext) populate (各 field の source) | … | … | … |
| Pair filter (5 majors 等) | … | … | … |
| Regime / ADX gate | … | … | … |
| `evaluate()` の前の prefilter | … | … | … |
| SL/TP exit simulation | … | … | … |
| Friction / spread 計算 | … | … | … |
| `pnl_pips` の正規化 (atr-multiple → pip 換算) | … | … | … |
| Dedup (per-bar / per-key) | … | … | … |

## 2.2 動的 instrumentation 実行 (オプション)

可能であれば各 pipeline を `--limit-symbols 1 --limit-bars 1000` で短時間実行し、生 trade log を比較:
- Phase 2 BT: 出力済 `bt-results/sr-weight-phase2-bin-bhfdr-2026-05-11.json` の `trades` 配列 (sr_anti_hunt_bounce のみ抽出)
- v2 audit: `raw/audits/sr_weight_gate_v2_2026-05-12.parquet` (KDE) と `raw/audits/sr_weight_gate_v2_pivot_2026-05-12.parquet` (PIVOT)

5 majors × USD_JPY のような単一 pair で:
- Phase 2 BT trade timestamps (entry_time) 集合
- v2 audit KDE/PIVOT trade timestamps 集合
- Jaccard 一致率 を計算
- 不一致 trade を 10 件サンプル、各 trade について「なぜ片方では出て片方では出ないか」を 1 行 explanation

実行コマンド例 (Codex がやれそうなら):
```bash
.venv/bin/python tools/sr_weight_gate_audit_v2.py --all --limit-symbols 1 --limit-bars 4000
# Phase 2 BT 再走は時間 1h43m なのでスキップ可、既存 bt-results の trade_log を再利用
```

**動的実行はオプション**。静的解析だけでも本タスクは完了可能。

## 2.3 divergence の定量的影響評価

各 divergence point について 4 段階で寄与度評価:

| Severity | 定義 |
|---|---|
| **🔴 dominant** | この 1 点で N が 2 倍以上動きうる |
| **🟠 material** | 1.3-2 倍動きうる |
| **🟡 minor** | 1.1-1.3 倍 |
| **🟢 negligible** | < 1.1 倍 |

# 3. 重点的に検証する 5 つの仮説

司令塔監査で挙げた仮説。Codex は **これら 5 つを必ず明示的に hit/miss 判定** すること。

## 仮説 H1: bar iteration cadence
- Phase 2 BT は `app.run_daytrade_backtest` で完全 per-bar (stride=1) iteration
- v2 audit は `RUN_STRIDES = {"sr_anti_hunt_bounce": 4, ...}` で stride=4
- 365d × 5 majors × 96 bars/day = ~175k bars
- もし全 setup が独立なら v2 audit は 1/4 = 25% に減るはず
- Phase 2 BT 594 vs v2 audit 335 → 比 56% → stride だけでは説明不十分
- **検証**: v2 audit を `RUN_STRIDES = {"sr_anti_hunt_bounce": 1, ...}` に変えて N がどう変わるかを推定 (実行不要、静的見積もり)

## 仮説 H2: sr_levels の populate 方法
- Phase 2 BT: `_compute_sr_anti_hunt_only_signal` 関数の `sr_levels` 引数の流入経路を完全特定。`app.run_daytrade_backtest` 内で **production と同じ** SR detection (pivot-based `find_sr_levels_weighted`) が動いているか?
- v2 audit: globally pre-computed levels を全 bar に同一 set として渡す
- **検証**: `app.py` 内の bar loop で sr_levels がどう生成・更新されるか line 番号付きで明示。Phase 2 BT が **bar 毎に sr_levels を再生成** している場合、設定の鮮度差が原因の最有力候補

## 仮説 H3: ctx fields の divergence
- 特に怪しい field: `atr` / `ema9-200` / `adx` / `bbpb` / `htf` / `regime`
- v2 audit は `_build_ctx` で row.get() default を多用 (例 `adx=float(row.get("adx", 25.0))`)
- Phase 2 BT は `app.add_indicators(df)` 後の生 row 値を使用
- **検証**: 5 majors × 1000 bar で `df.adx` の min/max/median を `app.add_indicators` 経由 vs v2 audit `load_data` 経由で比較。差があれば「ADX < 30 gate の trigger 数」が変わる

## 仮説 H4: SL/TP exit simulation
- v2 audit `_simulate_exit` は 12-bar 制限 + `sl_first_ambiguous` で同一 bar SL+TP hit を SL 扱い
- Phase 2 BT は `app.run_daytrade_backtest` 内の native exit (たぶん同様だが要確認)
- **検証**: Phase 2 BT の exit logic を `app.py` で特定し、`max_hold_bars` / friction / spread 適用順を v2 audit と比較

## 仮説 H5: `evaluate()` 呼び出し時の context.backtest_mode 影響
- v2 audit は `backtest_mode=True` を明示 setting
- Phase 2 BT は `backtest_mode=True` を `app.run_daytrade_backtest` 経由で渡す
- `sr_anti_hunt_bounce.evaluate()` 内 line 62 で `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2` env を確認し v2 / legacy 分岐
- **検証**: Phase 2 BT 走行時 (commit `1eabe84`) の env で `SR_ANTI_HUNT_BOUNCE_REDESIGN_V2` が "1" だったか確認 → 違う path を通っていれば dedup や signal_bar 選定が完全違う

# 4. 出力

## 4.1 報告書 `reports/sr_phase2_vs_audit_v2_forensic_<date>.md`

```markdown
# Phase 2 BT vs Audit v2 Methodology Divergence Forensic

## 1. Call Graph Mapping
### Phase 2 BT (sr_anti_hunt_bounce path)
- tools/sr_weight_phase2_bin_bhfdr.py:<line> → main() → run_target()
- ... 完全 call chain (関数名 + 行番号)
### Audit v2 (sr_anti_hunt_bounce path)
- ... 同様の完全 call chain

## 2. Divergence Matrix
| 軸 | Phase 2 BT | Audit v2 | 一致? | Severity | N への影響推定 |
|---|---|---|---|---|---|
| Bar iteration cadence | <line>: stride=1, ... | <line>: stride=4 | 相違 | 🔴/🟠/🟡/🟢 | +/- X% |
| sr_levels source | ... | ... | ... | ... | ... |
| ctx.adx populate | ... | ... | ... | ... | ... |
| SL/TP exit logic | ... | ... | ... | ... | ... |
| friction / spread | ... | ... | ... | ... | ... |
| dedup | ... | ... | ... | ... | ... |
| backtest_mode env (v2_redesign branch) | ... | ... | ... | ... | ... |
| (他、見つかった全 divergence) | ... | ... | ... | ... | ... |

## 3. Hypothesis Test
- H1 (bar cadence): <PASS/FAIL/PARTIAL>, 寄与 ≈ <%>
- H2 (sr_levels populate): <PASS/FAIL/PARTIAL>, 寄与 ≈ <%>
- H3 (ctx fields): <PASS/FAIL/PARTIAL>, 寄与 ≈ <%>
- H4 (SL/TP exit): <PASS/FAIL/PARTIAL>, 寄与 ≈ <%>
- H5 (v2_redesign env): <PASS/FAIL/PARTIAL>, 寄与 ≈ <%>

## 4. Dominant Cause Verdict
- Single dominant divergence: <"None" / "H<x>"> 
- 多要因の場合 ranked list (上から 3 つ寄与度パーセント明記)

## 5. Decision Recommendation
- 今後の SR audit pipeline:
  - (a) Phase 2 BT pipeline 統一 — pros / cons
  - (b) v2 audit pipeline 統一 — pros / cons
  - (c) 両方併走 — pros / cons
- Recommended path (1 つ選択 + 理由 3 行以内)

## 6. Open Questions
- forensic で answer 出来なかった 残懸念 (司令塔フォロー必要)
```

## 4.2 trade-level diff CSV (オプション、動的実行した場合)

`raw/audits/sr_phase2_vs_audit_v2_trade_diff_<date>.csv`

| pair | timestamp | phase2_present | audit_kde_present | audit_pivot_present | divergence_reason |
|---|---|---|---|---|---|

USD_JPY を pivot として 100 件サンプル。

# 5. 不変条件 (絶対遵守)

- ✋ **コード一切変更しない (pure-audit only)**
- ✋ 既存 BT result `bt-results/sr-weight-phase2-bin-bhfdr-2026-05-11.json` / `reports/sr_weight_gate_audit_v2_2026-05-12.md` / `reports/sr_weight_gate_audit_v2_pivot_2026-05-12.md` を絶対に変更しない
- ✋ Yahoo データ参照禁止
- ✋ stash leak 禁止 — final.md で `git log` / `git stash list` (空) / `git status` (新規 report .md のみ) 実 verify
- ✋ Phase 2 BT を再走しない (時間 1h43m + 不要)

# 6. 完了条件

1. `reports/sr_phase2_vs_audit_v2_forensic_<date>.md` 生成 (§4.1 の 6 セクション全部)
2. divergence matrix が **最低 8 軸** 埋まっている (上記表の例 7 軸 + 必ず 1 つ以上 新発見の divergence)
3. 5 仮説全部 (H1-H5) に明示判定 (PASS/FAIL/PARTIAL + 寄与度パーセント)
4. Dominant cause verdict が **明示** (`None` か `H<x>` か `multi-factor with H<x>+H<y> dominant`)
5. Decision recommendation が **3 候補から 1 つ選択**
6. (オプション) trade-level diff CSV
7. PR タイトル: `audit(sr-redesign): Phase 2 BT vs audit v2 methodology divergence forensic`
8. PR description に Dominant Cause Verdict + Decision Recommendation を貼る
9. final.md に `git log --oneline -5` / `git stash list` (空) / `git status` (新規 report のみ) 実 verify 証跡

# 7. 後続タスクとの接続

forensic verdict 別 next action:
- **Dominant H1 (bar cadence)**: v2 audit を stride=1 で再走するか、Phase 2 BT に揃えるか決断
- **Dominant H2 (sr_levels populate)**: production demo_trader が使う SR detector に audit を揃える redesign
- **Dominant H3/H4/H5**: 該当ロジックを audit v2 に移植 or 逆
- **Multi-factor**: Phase 2 BT を canonical とし v2 audit を廃止、または逆
- **None (説明不能)**: Phase 2 BT 自体に bug 仮説、再走 task で N reproducibility 確認


## Result (2026-05-13T03:13:29Z)

exit=0 · 426s

```
完了しました。pure-audit のみで、新規レポートを作成しています。

Report:
[reports/sr_phase2_vs_audit_v2_forensic_2026-05-13.md](/data/repo/fx-ai-trader/reports/sr_phase2_vs_audit_v2_forensic_2026-05-13.md)

結論:
- Dominant Cause Verdict: **single dominant なし。H1 + H2 dominant、H4 material の multi-factor**
- Recommendation: **(c) 両方併走**
- Phase 2 BT を canonical production-count verdict、v2 audit を exploratory SR-weight metadata として扱うべき、という判定です。
- optional trade-level CSV は未生成です。既存 Phase 2 JSON に `trades` / `trade_log` 配列がなく、Phase 2 再走は禁止条件だったためです。

補助計測中に生成された hunt event JSONL は削除済みで、作業ツリーは新規 report のみです。

Verification:
```text
git log --oneline -5
8c6da54 chore(codex): claim 20260513-1030-sr-weight-phase2-vs-audit-v2-divergence-forensic
2dda137 task(codex): queue Phase 2 BT vs audit v2 methodology divergence forensic [rule:R1]
cbe8735 docs(KB): R2 alert 2026-05-13T02:54Z
2bf3bdf docs(KB): daily report 2026-05-13
c9f7a0f docs(KB): monitor alert 2026-05-13
```

```text
git stash list
<empty>
```

```text
git status --short
?? reports/sr_phase2_vs_audit_v2_forensic_2026-05-13.md
```

PR title:
`audit(sr-redesign): Phase 2 BT vs audit v2 methodology divergence forensic`

PR description excerpt is included in the report.
```
