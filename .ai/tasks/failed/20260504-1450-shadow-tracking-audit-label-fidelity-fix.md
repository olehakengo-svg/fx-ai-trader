---
id: "20260504-1450-shadow-tracking-audit-label-fidelity-fix"
title: "shadow_tracking audit label fidelity fix: 11 sub-conditions に specific block_reason を保存する"
owner: "codex"
status: "queued"
priority: "P1"
created_at: "2026-05-04T14:50:00+0900"
roadmap_gate: "Audit fidelity 改善 — 後続 R3 RCA の効率化"
rule: "R3"
prereq_artifacts:
  - "modules/demo_trader.py (line 5008-5009 が修正対象)"
  - ".ai/runs/20260504-0527-tier1-shadow-tracking-forensic/forensic-report.md (11 sub-conditions の出典)"
related:
  - ".ai/tasks/done/20260504-1410-tier1-shadow-tracking-forensic-relaxation.md (発端 forensic task)"
---

# 0. なぜこのタスクか

`shadow_tracking` ラベルが **11 個の異なる upstream gate** を 1 つに潰している、という構造的な audit log 不忠実問題が forensic (commit 43126ea) で確定した。`modules/demo_trader.py:5008-5009` で audit log の最終出力時に `_is_shadow=True` が specific block_reason を上書きするため、slot bypass / alpha-scan / MTF downgrade / Q4 / pair-demote safety net / Phase0 tier / SHIELD/mode/Kelly/MC escalation など実態的に異なる挙動が、すべて同一の `shadow_tracking` 文字列に collapse される。

この aggregation 問題は、以下のような実害を継続的に発生させている:
- 監査時に「どの gate でこの trade が shadow に落ちたか」をログだけでは特定できず、毎回 source code grep が必要
- 後続 R3 RCA でも同じ aggregation を踏むため、forensic コストが線形に膨らむ
- LIVE/Shadow 分離は別 column (`is_shadow`) で守られているため PnL aggregation には汚染しないが、原因分析のコホート分割が事実上できない

V1 narrow implementation (別 P0 task) が正しい route を推し進めるのに対し、本タスク (P1) は「audit ログに 11 種の reason を素直に書き分ける」最小コミットに絞り、後続 RCA を効率化する観点で寄与する。schema 変更不要 (block_reason column が既存) で実装可能と forensic 段階で確認済み。

# 1. 仮説

- **H1**: `_is_shadow` フラグと `block_reason` を **両方保存** すれば、現在の `shadow_tracking` 表示を残しつつ specific reason も audit query 可能になる。
- **H2**: schema 変更不要 (block_reason column が既存) で実装できる。production audit DB の schema 互換性を維持できる。
- **H3 反証 (要検証)**: 既存の audit consumer (dashboard / Render API / forensic 既存スクリプト) が `shadow_tracking` literal に依存していて、変更で壊れる可能性がある。これに対しては `shadow_tracking` literal を **削除せずに残す** ことで回避する。

# 2. 仕様 (PRE-REGISTERED, LOCK)

修正対象: `modules/demo_trader.py:5008-5009` 周辺の audit logging logic。

11 個の sub-condition それぞれに specific block_reason 文字列を定義し、`_is_shadow=True` セット時に同時に block_reason に書き込む。期待 reason 列 (LOCK、post-hoc 変更で verdict INVALID):

| Order | Source line | block_reason (LOCK) |
|---:|---|---|
| 1 | Slot bypass `:3129-3143` | `slot_full_shadow_overflow` |
| 2 | Max-open bypass `:3159-3163` | `max_open_global_cap_shadow` |
| 3 | Active-hours bypass `:3178-3185` | `out_of_active_hours_shadow_eligible` |
| 4 | Alpha-scan shadow gates `:3642-3737` | `alpha_scan_toxic_segment_shadow` |
| 5 | MTF A/B downgrade `:3749-3802` | `mtf_conflict_downgrade_non_elite` |
| 6 | Optional regime guardrail `:3821-3838` | `regime_guardrail_directional_shadow` |
| 7 | Emergency trips `:4680-4712` | `emergency_kill_switch_shadow` |
| 8 | Q4 gate `:4714-4734` | `q4_paradox_non_elite_shadow` |
| 9 | Not-promoted safety net `:4735-4740` | `not_promoted_safety_net_shadow` |
| 10 | Phase0 tier shadow gate `:4749-4765` | `phase0_three_tier_routing_shadow` |
| 11 | Post-gate SHIELD/mode/Kelly/MC `:4847-4933` | `post_gate_late_oanda_shield_shadow` |

audit log line format (LOCK):

```
is_shadow=true | block_reason=<specific> | tier_state=<...>
```

`shadow_tracking` ラベルは backward compat のため **削除しない** が、新 audit query では `block_reason` を一次キーとして使用する。

実装上の制約:
- `_is_shadow=True` セット箇所と block_reason セット箇所を一致させる (sentinel ではなく enum / 定数 module を切る方が望ましいが、scope 内であれば string literal 直書きでも可)
- 11 sub-conditions 以外で `_is_shadow=True` をセットしている箇所が後で発見された場合は **本タスクで触らず**、別タスク化する (scope creep 禁止)

# 3. データ分離

監査ログのみ修正する。Live/Shadow PnL aggregation は触らない (`feedback_live_shadow_separation` 厳守)。

具体的には:
- `is_shadow` column の意味は変えない (LIVE PnL 集計時は依然 `is_shadow=0` で分離)
- `block_reason` column の値分布は変わるが、aggregation rule (LIVE/Shadow 分離) は不変
- 既存の Live PnL 集計 SQL は `is_shadow` のみで filter している前提のため影響なし。万一 `block_reason='shadow_tracking'` を filter 条件に使う集計 SQL が見つかった場合は本タスクで報告し、別 issue 化する

# 4. 検証コマンド (Codex 必須実行)

Codex は以下をすべて実行し、結果を artifact に貼ること:

1. **修正前後 diff 検証**:
   - 修正前 (HEAD) の audit log 1 日分から `shadow_tracking` 行を抽出
   - 修正後の audit log を同じ synthetic input で生成し、`block_reason` を解釈する query で 11 種の counts を出す
   - 件数合計が修正前の `shadow_tracking` 件数と一致すること

2. **regression test 新規作成**:
   - `tests/test_demo_trader_audit_label.py` に 11 sub-conditions ごとに synthetic trade を流す test を追加
   - 各 test で期待 block_reason が出るか assert
   - 既存テストが green のまま通ること

3. **production audit DB schema 確認**:
   - read-only で `block_reason` column が既存かどうか確認 (DDL DROP/ALTER 禁止)
   - column type が string で長さ十分 (>=64 char) であることを確認

4. **lint / type check**:
   - `mypy modules/demo_trader.py`
   - 既存の linter (black / ruff / 他プロジェクト標準) を pass

5. **dashboard / Render API 互換確認**:
   - `shadow_tracking` literal を grep で残存検索し、関連箇所が変更後も動くこと (backward compat)

# 5. 採用 / 保留 / 棄却基準

- **ACCEPT**:
  - 11 sub-conditions すべて specific reason で audit log に出力される
  - `shadow_tracking` literal も残っており backward compat ある
  - production audit schema 互換 (DDL 変更なし)
  - 既存 dashboard / Render API が壊れない
  - regression test 11 件 green
  - mypy / linter green

- **NEEDS_MORE_EVIDENCE**:
  - 9-10/11 sub-conditions のみ修正済 (1-2 件漏れ)
  - 漏れ理由が特定 sub-condition の coverage 不足で、追加 commit で完了見込みの場合

- **REJECT**:
  - 8 件以下しか specific reason 化されない
  - dashboard / Render API が壊れる
  - schema 互換性が失われる
  - LIVE/Shadow 集計が変わってしまう

# 6. 禁止事項

- `.env` / OANDA / OPENAI key の取扱禁止
- production DB write 禁止 (read-only のみ)
- `block_reason` column の DROP / ALTER 禁止 (既存 column の意味は変えない、書き込み内容のみ追加)
- 既存 `shadow_tracking` literal を削除する変更禁止 (backward compat 必須)
- 11 sub-conditions 以外への scope creep 禁止
- V1 narrow implementation (別 P0 task) と混ぜない (ファイル変更を相互流入させない)
- `git push` / `git commit` / `git checkout` 禁止 (push は親 Claude が一括で行う)

# 7. Rule R3 verification

- pre-registered LOCK 厳守: 上記 11 個の reason 文字列は本 spec で固定済
- post-hoc に reason 文字列を変更した場合は **verdict INVALID**、再 spec 起票が必要
- LOCK 対象: reason 文字列・対象 line range・audit log line format・採用基準
- LOCK 外: 実装内部の helper 関数名や enum/定数 module 配置などは Codex 裁量

# 8. 期待される所要時間

20-30 min (単純な label 拡張、schema 変更なし、テスト 11 件 synthetic 生成)

# 9. 月利 100% ロードマップへの寄与

直接寄与なし (PnL や戦略エッジに変化はない)。
ただし後続 R3 RCA で `block_reason` を一次キーとして cohort 分割できるようになることで、forensic 1 回あたりのコストを大幅に削減する。とくに pair-demote safety net や Phase0 三層 routing の挙動を独立に追える効果が大きく、間接的に W3 / W4 のロードマップ進捗を加速する。


## Error (2026-05-05T00:53:37Z)

```
orphaned: container restarted while task was running
```
