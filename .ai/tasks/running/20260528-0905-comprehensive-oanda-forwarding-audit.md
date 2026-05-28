---
id: 20260528-0905-comprehensive-oanda-forwarding-audit
priority: P1
gate: R3
rule: R3
status: queued
created: 2026-05-28
owner: claude
---

# Comprehensive OANDA forwarding audit — `_block()` / `_is_shadow=True` 全経路の徹底監査

## 背景

A1+A2 hot-fix (`20260528-0900-edge-cell-pre-block-bypass-fix`) で 2 つの block 経路を fix するが、**`modules/demo_trader.py` には 25+ 箇所の `_block()` 呼び出し と 30+ 箇所の `_is_shadow=True` 代入箇所がある**。

これらの中で、まだ未発見の「edge cell strategy の signal を edge cell match に到達させずに殺している経路」がある可能性がある。**1 箇所ずつ A 系統 patch を当てるのは loose-end-game**。

本タスクは **網羅的 audit**:
1. 全 `_block()` call site を列挙
2. 全 `_is_shadow=True` 代入箇所を列挙
3. 各々が edge cell strategy (7 戦略) の signal を intercept しうるか実測 (recent 7-day production log + demo_trades 統計から)
4. それぞれの fix pattern を提案 (shadow bypass / edge cell bypass / leave as is)
5. 優先順序付き fix queue を出力

## Scope

`modules/demo_trader.py` の関数:
- `_tick_entry()` (line ~3340-5600)
- `_should_audit_shadow_emit()` / `_open_shadow_emit_trade()` (line ~817-859)
- `shadow_emit_signals()` (line ~3149-3210)

その他関連:
- `_block()` の定義と副作用
- `is_shadow_demoted()` の判定ロジック
- score gate / cooldown / sentinel bypass の判定箇所

## 監査タスク (5 phase)

### Phase A: 全 _block() / _is_shadow=True 列挙 + 静的分析

```bash
# Codex は read-only でこれを実行
grep -nE "_block\(|_is_shadow = True|_is_shadow=True" modules/demo_trader.py | sort -k1,1n
```

各 call site について以下を抽出:
- line number
- block reason 文字列 (e.g., "same_price_0pip", "r2_shadow_demoted_cell")
- 上流 context (どの guard 条件下で発火するか)
- 上流の変数依存 (entry_type, instrument, signal, _entry_time, _v2_regime, _mtf_gate_action が定義済か)
- `return` / `continue` / fall-through どれか

Output: マトリクス table (35+ row) を done/ markdown に貼る

### Phase B: 各 block site が edge cell strategy の signal を intercept しうるか実測

edge cell strategy 7 個:
- dt_bb_rsi_mr (PAIR_PROMOTED, 5 cell)
- session_time_bias (PAIR_PROMOTED, 2 cell)
- bb_rsi_reversion (PAIR_DEMOTED, 1 cell)
- rsk_gbpjpy_reversion (PHASE0_SHADOW, 1 cell)
- orb_trap (FORCE_DEMOTED, 1 cell)
- wick_imbalance_reversion (PAIR_PROMOTED, 1 cell)
- sr_anti_hunt_bounce (PHASE0_SHADOW, 1 cell)

**実測 method**:
1. Render production log `srv-d6va1of5r7bs73en10vg` の `[SENTINEL_BLOCK_DIAG]` を 直近 24h (2026-05-27 09:00 〜 2026-05-28 09:00 UTC) 全件取得
2. block reason 別 × strategy 別の count を集計
3. edge cell strategy が引っかかった block reason TOP 10 をリスト化

```bash
# Render log MCP 経由 (Codex は mcp__render__list_logs を呼ぶ)
# text filter: "SENTINEL_BLOCK_DIAG"
# Aggregate by parsing: strategy_name -> block_reason -> count
```

Output: `block reason × strategy × 24h count` matrix。fix 優先度の根拠データ。

### Phase C: 各 _is_shadow=True 代入箇所の context 分析

30+ 箇所の `_is_shadow = True` について:
- どの guard 条件で発火するか
- shadow 化のあと return するか continue するか
- edge cell match (line 5011) に到達できるか

注意: line 5269 の override は `_edge_cell_force_live AND _is_shadow` で flip するため、**shadow 化のあと続行するパスは override で救える**。**return するパスは救えない**。

Output: 「return 後で殺される shadow path」リスト

### Phase D: oanda_audit table の bridge_status 分布実測

`/api/oanda/audit?limit=1000` を fetch して直近 24h を解析:
- bridge_status 分布 (skipped / sent / filled / pending / error 等)
- block_reason 分布
- is_live=True で oanda_trade_id が空 (sent 失敗) の件数
- entry_type × bridge_status の cross-tab

特に注目:
- `bridge_status='sent'` で `oanda_trade_id=""` (= OANDA 送信したが ack 来ず?) の件数
- edge cell strategy で bridge_status が `skipped` 以外の件数
- `block_reason` 別の `is_live=True` 件数

Output: 24h forwarding 健全性レポート。

### Phase E: fix pattern 別の優先順序付き提案

各 block site について以下 4 つから選択:

1. **EDGE_CELL_BYPASS**: edge cell match pre-check で bypass (今回 A1+A2 と同パターン)
2. **SHADOW_BYPASS**: `_is_shadow=True; continue` で常に shadow に降格 (recent_emit 等で既採用パターン)
3. **LEAVE_AS_IS**: block 維持 (cell demote / pair demote / risk state 等の安全弁)
4. **DEEPER_REFACTOR**: edge cell match を guard 群より手前に移動 (spec doc 厳密準拠)

各候補に対し:
- 影響戦略数 (edge cell strategy 何個が救われるか)
- side effect risk (false-live promotion / DB 容量 / 重複 fill 等)
- 実装工数 (lines changed, test 範囲)

Output: 優先順位付き fix table (各 fix が「次の 24h で edge cell live N を何件増やすか」の推定込み)

## Output (done/ markdown に追記)

```markdown
## Result: comprehensive OANDA forwarding audit

### Section 1: _block() / _is_shadow=True 全列挙 (静的 + Phase A)

| line | call type | reason | guard context | upstream vars defined? | exit type |
|---|---|---|---|---|---|
| 3551 | _block | r2_shadow_demoted_cell | is_shadow_demoted + !live_tier_exempt | yes | return |
| 3837 | _block | same_price_{Npip} | abs(t.entry_price - current) < dist | yes | return |
| ... | ... | ... | ... | ... | ... |

### Section 2: 直近 24h 実測 block 分布 (Phase B)

| block_reason | total count | edge cell strategies impacted |
|---|---:|---|
| recent_emit_bypass→shadow | 200+ | session_time_bias / dt_bb_rsi_mr |
| same_price_0pip | 100+ | session_time_bias |
| r2_shadow_demoted_cell | 50+ | bb_rsi_reversion |
| spread_gate | 30+ | ma_regime_switch (not edge) |
| ... | ... | ... |

### Section 3: shadow_eligible_full bypass pattern を持つ既存 guard (Phase C)

GBP Asia (line 3753) / RANGE SELL (4097) / DT RANGE (4119) / + 29ec95cb で追加した 5 個 = 8 個既存。

### Section 4: oanda_audit 24h 健全性 (Phase D)

| metric | value |
|---|---:|
| total audit rows 24h | ? |
| bridge=filled count | ? |
| bridge=skipped count | ? |
| bridge=sent count | ? |
| oanda_trade_id empty/sent ratio | ? % |
| edge cell strategy with bridge != skipped | ? |

### Section 5: 優先順序付き fix proposal (Phase E)

| priority | block site | fix pattern | impact (edge cells) | risk | est lines |
|---|---|---|---|---|---:|
| P0 | r2_shadow_demoted_cell (3551) | EDGE_CELL_BYPASS | bb_rsi_reversion (E4) | low | ~15 |
| P0 | same_price_0pip (3837) | EDGE_CELL_BYPASS | session_time_bias (E2,E8) | low | ~10 |
| P1 | (新発見の block site) | ? | ? | ? | ? |
| P2 | ... | ... | ... | ... | ... |

### Section 6: Conclusion

- 全 ?? 箇所の block site のうち、edge cell strategy を intercept する箇所は ?? 個
- A1+A2 fix で救われるのは ?? 個 / ?? 個
- 残り ?? 個を追加 fix するか、深い refactor (Option B) に進むかの user 判断データ
- 24-72h 観測の Pre-reg LOCK 提案 (具体的閾値)
```

## 禁止事項

- 本番 demo_trades.db への書き込み (read-only)
- `.env` / OANDA secret アクセス
- LIVE 戦略 tier の変更
- `EDGE_CELLS` リストの追加 / 削除
- `_block()` 関数自体のシグネチャ変更
- 本タスクは **監査のみ**、修正コードは出さない (修正は A1+A2 task `20260528-0900` で別途)
- 監査の途中で新たな修正を `git commit / push` する **禁止**

## クオンツチェック

- [x] R3 (correctness audit, BT skip 許容)
- [x] read-only (修正なし)
- [x] 実測ベース (静的 + 24h Render production log)
- [x] 全 block site 網羅
- [x] edge cell strategy 7 個全てカバー
- [x] fix pattern 別優先順序付与
- [x] Pre-reg LOCK 提案

## Acceptance

Codex completes if:
1. Phase A-E 全 Section が埋まる
2. 静的列挙 + Render log 実測 (24h 分) が両方含まれる
3. 修正コードは含まれない (監査のみ)
4. fix 優先順序付き table が出力される
5. P0/P1/P2 別の est lines + risk assessment あり

## 関連 memory

- 前回 P0-3 fix: commit 29ec95cb (shadow-eligible bypass for 5 gates)
- 前回 P0-R3 fix: commit 5594a7a5 (line 5269 AND condition removal)
- 今回 P0 hot-fix: queue 20260528-0900 (A1+A2)
- [edge-cells-stage3-live-promote-2026-05-26.md](../../knowledge-base/wiki/decisions/edge-cells-stage3-live-promote-2026-05-26.md) — spec doc
- [feedback_codex_schema_hallucination](feedback_codex_schema_hallucination.md) — schema は直貼り
- [監査=設計の正誤、N不足は別問題](feedback_audit_purpose_design_not_n.md) — 監査の本質
