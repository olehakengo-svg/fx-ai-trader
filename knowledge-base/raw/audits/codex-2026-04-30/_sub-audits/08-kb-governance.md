# Sub 8: KB ガバナンス・構造的問題監査

> 注: Codex API 利用上限のため Claude が直接実行 (2026-04-30)。
> CLAUDE.md / 57 lessons / 10 decisions / CHANGELOG.md / hooks を参照。

## Scope
- `CLAUDE.md`
- `knowledge-base/wiki/lessons/*` (57 lesson)
- `knowledge-base/wiki/decisions/*` (10 decision)
- `knowledge-base/wiki/sessions/` (最新参照)
- `CHANGELOG.md`
- `tools/sync_kb_index.py`, `tools/tier_integrity_check.py`
- `.github/workflows/*` (5 workflow)
- `scripts/hooks/*` (10 hook script)

## 1. Bugs Found
| # | Severity | File:Line | Description | Root Cause | Suggested Fix |
|---|----------|-----------|-------------|-----------|--------------|
| 1 | Sev2 | `tier-master.md:1-3` | Tier-Master が 5 日間更新されていない (最終 2026-04-25, 現在 2026-04-30)。Live drift が反映されないため tier 判定が古い | tier_integrity_check.py が手動 trigger 依存。nightly 自動化なし | nightly cron / GitHub Actions schedule で tier_integrity_check.py --write を毎日実行 |
| 2 | Sev2 | `.remember/save-session.sh` (obs 633) | save-session.sh が無効パスで失敗しセッション保存が機能不全 | パス解決ロジック | hook を修正、エラー時は失敗前提でリトライまたはエスカレート |
| 3 | Sev3 | `knowledge-base/wiki/strategies/{name}.md` | tier-master.md で参照される戦略ドキュメントが一部欠損 (Sub 1c #4: h1-breakout-retest.md, h1-fib-reversal.md, h1-ema200-trend-reversal.md) | feat()コミット時に同期書き込みのルールがあるが pre-commit が警告レベル | pre-commit を error レベルに昇格、欠損 wiki があれば commit reject |

## 2. Structural Issues
1. **Lesson が 57 件あるのに同種バグが繰り返されている**
   - lesson-silent-except-hides-nameerror.md: 「sub 1a #8 の except: pass で未定義変数」が再発
   - lesson-shadow-vs-live-confusion / lesson-shadow-contamination: Sub 1d #3 の crash 時 shadow bypass で再発リスク
   - lesson-bt-before-deploy: Sub 5 #1-4 (BT runner PnL 誤算) はまさに「BT before deploy」が機能していない証左
   - lesson-conf-undefined-bug: Sub 1a #8 で再発
   - lesson-orb-trap-bt-divergence: Sub 6 で post_news_vol の BT-Live 乖離が同型再発
   - **Lesson の知識が code に内部化されていない** — lesson は記述のみで、自動チェック (lint/test/CI) に落ちていない

2. **CLAUDE.md「KB は更新するもの、絶対視も無視も禁止」が運用で機能していない**
   - 過去 3 回の振動事例を CLAUDE.md に記録 (Aggregate Fallacy, Q1' C1 撤退, フラットな意見要請後の KB-defer)
   - しかし Claude/AI 側のセッション開始時自動チェックリストが存在しない
   - 仕組みではなく心構えに依存

3. **CHANGELOG が「変更履歴」として機能不全**
   - 最新エントリは技術的変更の長大なリスト (>200行)
   - **影響評価 (どの戦略の Live PnL がどう動いたか) が併記されていない**
   - lesson-changelog-as-evaluation-anchor.md が「changelog を評価アンカーに」と提唱しているが、実装されていない

4. **静的時間ブロック禁止 (CLAUDE.md 4原則 #3) が code で破られている**
   - Sub 2 OOS finding: `modules/demo_trader.py:3457-3544` に静的時間/ペアブロック多数残存
   - Sub 3 #4: `session_time_bias.py`, `tokyo_range_breakout.py`, `xs_momentum.py`, `asia_range_fade_v1.py`, `liquidity_sweep.py` 多数
   - **CHANGELOG にも UTC 00,01,21 blocked, Friday filter 等の静的ブロックが「fix」として記録されている** — 原則違反が「修正」扱い

5. **Tier 判定の Live drift が tier_integrity_check.py で検出できない**
   - tools/tier_integrity_check.py は code と tier-master.md の整合をチェックする設計
   - しかし「Tier に残っているが Live で大負けしている戦略」を検出する logic がない
   - 結果: ELITE_LIVE 3 戦略 (session_time_bias 等) が Live で負け続けても Tier に居座る

6. **decision 文書と実態の乖離**
   - decisions/independent-audit-2026-04-10.md, external-audit-2026-04-24.md などの監査結果がある
   - しかし「監査勧告 → 実装完了」の追跡が code 側に紐付いていない
   - 例: 監査で指摘された OANDA 冪等化 (Sub 1d #1 と同型) が解決済みかどうか即座に判定不能

7. **tools/sync_kb_index.py の trigger 漏れ**
   - CLAUDE.md「Tier 変更後に必ず実行」と記載
   - しかし pre-commit / post-commit に組み込まれていない
   - 実際 CHANGELOG 上で多数の tier 変更が記録されているが index 同期実行ログなし

8. **CI / GitHub Actions の品質ゲート設計**
   - ci.yml, bug-check.yml, alpha-scan.yml, daily-report.yml, weekly-audit.yml は存在
   - **しかし「Sub 1 で発見された Sev1 11 件のうち何件が CI で検出されるか」を考えると、おそらく 0 件**
   - CI が test 通過のみで、structural integrity (idempotency, gate ordering, look-ahead) のチェックなし

9. **dot-safe link 修復後の dead link 再発**
   - obs 605-606 で 152→0 に修復
   - しかし Sub 1c #4 で `h1-breakout-retest.md` 等の dead link を再検出
   - **修復が one-shot で、継続的検査がない**

10. **lesson-asymmetric-agility-2026-04-25 のルールが守られていない**
    - 「Rule 3 (Immediate)」算数破綻時はBT skip して analyses/ に文書化 → 直近の M3 SCORE_GATE 修正 (obs 626) は documented analysis なし
    - Rule 1-3 の commit メッセージ `rule:R[1|2|3]` 明示も不徹底

## 3. Losing Edge Analysis
- 該当しない (governance scope)

## 4. Roadmap Alignment
- **roadmap v2.1 が KB の参照点でしかなく、運用の制約として機能していない**
- 例: Gate 0/1/2/3/4 の数値基準があるが、`api_phase_gate` がそれを部分的にしか実装していない (Sub 1c #2)
- 例: tier_integrity_check は roadmap Gate 基準で Tier を再計算しない
- 結果: roadmap は更新されても Live が roadmap に従って動いていない

## 5. Top 3 Action Items (impact 順)

1. **Lesson → 自動チェック化**: 主要 lesson (silent-except, shadow-bypass, bt-before-deploy, sr-dict-type) を CI/lint rule または pytest として実装
   - Impact: 同種バグの再発率を大幅低減 (Sub 1-5 で発見された 60+ bugs の半数は lesson 既知)
   - Confidence: high

2. **tier_integrity_check.py に Live drift detector を追加** (Live N≥10, Wilson lower<25%, EV<0 → 自動 demote 提案)
   - Impact: ELITE_LIVE/PAIR_PROMOTED の Tier-Live 乖離を自動是正
   - Confidence: high

3. **CHANGELOG → 戦略別 Live PnL 影響表に再構成** (lesson-changelog-as-evaluation-anchor.md の提案を実装)
   - Impact: 個々の変更が Live にどう影響したかを後追い可能に → 同型バグ再発防止の前提条件
   - Confidence: med

## 6. Out-of-Scope Findings
- 本サブはガバナンス scope だが、Sub 1-7 の発見は「ガバナンス欠陥が結果として bug を量産している」ことを示す
  - 60+ bugs の根因の大半は「lesson にあるが内部化されていない」「監査勧告が実装に紐付いていない」「Tier 判定が Live を見ていない」のガバナンス問題

## 7. Lesson Internalization Audit

| Lesson | 該当 code | 内部化済み? | 残存リスク |
|---|---|---|---|
| lesson-silent-except-hides-nameerror | `app.py:3943-4008` (Sub 1a #8) | ❌ | 再発中 |
| lesson-shadow-vs-live-confusion-2026-04-28 | `modules/demo_trader.py:4231` (Sub 1d #3) | ⚠️ 部分的 | crash 時 shadow bypass の構造が残る |
| lesson-bt-before-deploy | `_bt_*.py` 22本 | ⚠️ 形式的 | Sub 5 #1-4 の PnL 誤算で BT 自体が信頼不能 |
| lesson-conf-undefined-bug | `app.py` `compute_signal()` (Sub 1a OOS) | ❌ | 再発 |
| lesson-orb-trap-bt-divergence | post_news_vol N=7 全敗 (Sub 6) | ❌ | BT-Live 乖離が同型再発 |
| lesson-sr-dict-type-error | `app.py:8186-8196` (Sub 1a #7) | ❌ | float/dict 混在 API バイアス |
| lesson-changelog-as-evaluation-anchor | CHANGELOG.md | ❌ | 影響評価併記なし |
| lesson-strategies-page-drift | tier-master.md 5日未更新 | ❌ | drift 続行 |
| lesson-asymmetric-agility-2026-04-25 | M3 修正 (obs 626) | ❌ | Rule 文書化なし |
| lesson-survivor-bias-mae-breaker-2026-04-25 | Sub 1d #5 (MAFE 破損) | ❌ | close path で未対応 |
| lesson-six-dead-strategies-removal-2026-04-26 | Sub 3 #4 (london_session_breakout 死コード) | ⚠️ | 一部残存 |
| lesson-confounding-in-pooled-metrics-2026-04-23 | aggregate fallacy 再発 (Sub 6 #1) | ⚠️ | bb_rsi_reversion 評価で発生 |
| lesson-xau-friction-distortion | XAU 除外 (memory: feedback_exclude_xau) | ✅ | 06a 集計で除外実装済み |
| lesson-shadow-emit-dedup-2026-04-30 | Sub 1d #3 と関連 | ⚠️ | 当日 lesson だが Sub 1 系で再発 |

**内部化評価**: 14 lesson のうち ✅ 1 / ⚠️ 6 / ❌ 7 → **約 50% が code 内部化されていない**

## 8. KB-Code Drift Detection

1. **CLAUDE.md「静的時間ブロック禁止」 vs CHANGELOG「UTC 00,01,21 blocked, Friday filter」**
   - 原則と実装が真逆。CLAUDE.md を更新するか、code を直すか、明示的判断が必要
2. **roadmap v2.1 「Gate 0 の lot-step 進行」 vs `api_phase_gate` 実装欠落** (Sub 1c #2)
3. **tier-master.md「ELITE_LIVE session_time_bias」 vs Live N=3 全敗** (Sub 6)
4. **CLAUDE.md「KB は更新するもの、絶対視も無視も禁止」 vs 自動チェック仕組みなし**
5. **CLAUDE.md「feat()コミット時に同コミットで wiki 更新」 vs pre-commit が警告のみ** (Sub 1c #4 dead link)
6. **lesson-bt-before-deploy 文書 vs BT runner 自体が壊れている** (Sub 5)
7. **decision/independent-audit-2026-04-10 勧告 vs 実装追跡なし**

## 9. Governance Gap Top 3 (最も是正すべき)

1. **Lesson → CI/lint チェック自動化**
   - 現状: 57 lesson が「読み物」として存在
   - 是正: 主要 lesson (10-15 件) を pytest fixtures や custom ruff/mypy plugin として実装
   - 優先 lesson: silent-except, shadow-bypass, bt-before-deploy, conf-undefined, sr-dict-type, idempotent-orders (新規)
   - 成功指標: Sub 1-5 で発見された Sev1 11 件のうち 5 件以上が CI で再検出

2. **Tier 判定への Live drift detector 組み込み**
   - 現状: tier_integrity_check.py は code-tier 整合のみ
   - 是正: Live N≥10 で Wilson lower<bb 線 (BEV+5%) または EV<0 を自動検出して Tier demote 提案を出す
   - 成功指標: ELITE_LIVE 戦略が Live で 5 日連続 EV<0 になったら 24h 以内に降格通知

3. **CHANGELOG を「Live PnL impact ledger」に再構成**
   - 現状: 技術変更のフラットリスト
   - 是正: 各 entry に「変更前後 7d Live N / WR / EV / PF / cumulative pip」を併記
   - 成功指標: ある変更を rollback すべきかを 3 分以内に判断できる
