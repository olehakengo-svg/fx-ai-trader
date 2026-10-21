# Lesson: needs_orchestrator に返した根本修理は期日付き registry entry なしで 29 日放置された (2026-10-21)

**分類**: プロセス欠陥 (防御を先に入れると「根は後で」が既定化する)
**関連**: [[storm-guard-design-2026-09-22]] §6-2 / §8、[[usdjpy_carry_dip_accumulator]]、[[daily-observations-2026-10]] O-2026-10-13-1 / O-2026-10-20-1

## 何が起きたか

- 2026-09-22 PR #287 (storm guard 4 点、bridge 層) の設計書 §1 と §6-2 は、**family A の根 = LIVE 経路が `modify_sl_sync` 成功後に DB `sl` を更新しない**ことを code reading で特定し、「別 PR (R3) 候補」として needs_orchestrator に返した。
- その後 29 日間、この根は registry の期日付き entry を持たず (`storm-guard-enforce-decision` / `-execution-window` は guard の有効化だけを追跡)、session log の「未解決」欄に文として残り続けた。
- その間に storm 3 波 — #1022861 14,676 (10-05) / #1062664 57,311 (10-13、史上最大) / #1254773 46,091 (10-19) — 合計 ≈120k の `REPLACEMENT` tx が broker に送られ、guard は検知のみ (`enforce: false`) のため 1 件も止めなかった。guard の enforce 執行自体も env 設定の permission 問題で 10-21 時点未達。
- 10-21 に Workflow (読み 5 面 → 統合 → 反証 → 設計) で根を再導出したところ、**family B (trail⇄BE 往復) も同じ根**で、2 writer は同一 if/else の排他 2 分岐だった。修正は送信口に 6 行 + 保険 + 兄弟 1 箇所 (§8.2)。1 日で PR 可能な規模だった。

## 何が間違っていたか

1. **「防御層を先に、根は後で」が既定化した**: guard が入ると storm の「被害」は tx 数だけで PnL は ¥0 なので、優先度が自然に下がる。しかし guard は enforce されるまで 0 件も止めず、enforce は別の障壁 (permission) で止まっていた。
2. **期日を持たない未解決項目は読み手がいない**: session log の未解決欄は毎日 copy され、registry の TRIGGERED にも daily report にも出ない。registry に載せる規律 (「文書に期日を書いたら同 PR で registry」[[2026-10-07-session]] (autopilot 10-07 の規律)) が「候補」止まりの項目には適用されなかった。
3. **「正しい層は bridge」という設計判断が根の所在を曖昧にした**: §1 の「修理の正しい層は bridge 入口」は guard としては正しいが、根 (caller の簿記欠陥) を直す層の判断と混同され、caller 側は「非接触」のまま 29 日経った。

## どう直すか (規律)

- **needs_orchestrator に返す根本修理は、返す PR と同じ PR で registry に期日付き entry (`deadline_info`) を作る** — 候補・別 PR・後日、のいずれの言葉でも同じ。期日は「次の storm 1 波分」を上限に (本件なら 1 週間)。
- 防御層 PR の §6 (既知の限界) に「根」が書かれている場合、その項目は registry entry の id を併記する。id が無い項目は lint 対象 (将来: `tools/prereg_trigger_watch.py --lint` で `needs_orchestrator` 節の根項目に registry id が無ければ WARN — 本 lesson 時点では未実装、候補)。
- 「guard が全数捕捉した」という観測 (O-2026-10-15-1 / 10-16-1 / 10-20-1) は **根の修理の緊急度を下げる材料ではなく、根の所在 (caller 側) を確定する材料**として読む。

## 本件の処置

- 修復 PR (2026-10-21、rule:R3): [[storm-guard-design-2026-09-22]] §8、pin `tests/test_sltp_live_sl_persist_storm_root.py`
- 回帰アラーム: registry `sl-persist-root-fix-first-live-trail-readout` (期日 11-04)
