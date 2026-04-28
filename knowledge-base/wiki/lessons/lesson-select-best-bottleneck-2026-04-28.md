# Lesson: select_best() bottleneck — 30/54 戦略が永遠に DB に現れない構造

**Date**: 2026-04-28
**Trigger**: Phase 10 G0a production routing audit
**Plan**: /Users/jg-n-012/.claude/plans/memoized-snuggling-eclipse.md

## 観測

`raw/audits/production_routing_audit_2026-04-28.md`:

- DT_QUALIFIED 54 戦略のうち **30 が DB に一度も登場しない** (Apr 2-28)
- そのうち 3 戦略 (vsg_jpy_reversal, rsk_gbpjpy_reversion, mqe_gbpusd_fix) は
  `tools/never_logged_diagnosis.py` で 365d × 5 majers BT replay すると計
  533 signals を BT で出している
- 18 戦略は Shadow-only (Live=0)
- Live-active は 6 / 54 (11%)

## 根本原因

`strategies/daytrade/__init__.py` の `DaytradeEngine`:

1. `evaluate_all(ctx)` で全戦略の候補を集める (≤54 candidates)
2. `select_best(candidates)` が **max score 1 つだけ** を返す
3. `split_shadow_always(candidates, best)` は best 以外の候補のうち
   `SHADOW_ALWAYS_STRATEGIES` に含まれるものだけを Shadow 経路で
   並行記録 — **しかし `SHADOW_ALWAYS_STRATEGIES = frozenset()` (empty)**

つまり 1 bar で複数戦略が候補を出しても、**勝者 1 つ以外は完全に
記録されない**。常に他に負け続ける戦略は永遠に DB に現れない。

`SHADOW_ALWAYS_STRATEGIES` は 2026-04-28 R2 demotion で意図的に空に
された (sr_anti_hunt_bounce / sr_liquidity_grab が EV<0 で audit data を
汚染するため、`lesson-shadow-always-emit-cleanup-2026-04-28.md` 参照)。
副作用として **その後デプロイした全ての新戦略の audit data も同時に
失われる構造**になった。

## Phase 1-8 結論への影響

過去の audit で「○○戦略は edge 無し」と結論したものは **全て**
以下を区別していなかった:

- (a) 真の edge 無し — strategy.evaluate() が常に None を返す
- (b) **edge ありで strategy.evaluate() は Candidate を返すが、
  DaytradeEngine の score 競争で常に負けて記録されない**
- (c) signal が出る前段で SignalContext などの上流データが届いていない

例: Phase 7 の唯一 survivor `london_close_reversal_v2` は本 audit で
**NEVER in DB**。しかし LCR-v2 は production の主要 edge と見なされて
いる戦略。実際は LCR-v2 が UTC 20:30-21:00 に Candidate を出していても、
同窓で他戦略 (post_news_vol / dt_bb_rsi_mr 等) が score 4.0+ を出して
いれば LCR-v2 (score 3.5) は永遠に sub-leading で記録されない。

## 構造的含意

- 戦略を 47→48 に増やしても **競争に勝てない限り Live trade は出ない**
- 「Sentinel として 0.01 lot 蓄積」も SHADOW_ALWAYS_STRATEGIES に
  入れていなければ全く蓄積しない
- Phase 8 の `pd_eurjpy_h20_bbpb3_sell` も既に NEVER in DB を確認 —
  override で deploy したのに観測不能
- BT replay で signal 出るのに Live で出ない 3 戦略は、
  「pipeline pre-insert で消える」例外的失敗ではなく
  「DaytradeEngine の score 競争で常に負ける」**通常動作**

## アクション (このセッションで commit する範囲外)

1. **観測性の回復**: 全候補を per-bar 記録する audit table 追加
   (Live trade として実行はしない、観測のみ)
2. **DaytradeEngine 競争の見直し**: per-strategy quota, score
   normalization, または並行 emission への architectural pivot
3. **Phase 1-8 結論の再評価**: 観測性回復後、過去の "edge 無し" 結論を
   "競争で負けただけ" のものと区別して再 audit

## 自分への教訓

- "0 trade" を見たら **3 つの仮説** ((a)(b)(c)) を毎回区別する
- 既存の audit infra が「全候補を見ているか / 勝者だけを見ているか」を
  確認してから結論を出す
- KB-defer trap (lesson 4) と同様、**既存の集約 layer を盲信しない**

## 関連

- raw/audits/production_routing_audit_2026-04-28.md (G0a 結果)
- raw/audits/never_logged_diagnosis_2026-04-28.md (G1 BT replay)
- knowledge-base/wiki/lessons/lesson-shadow-always-emit-cleanup-2026-04-28.md
- knowledge-base/wiki/decisions/sr-strategies-signal-track-2026-04-28.md
- knowledge-base/wiki/lessons/lesson-shadow-vs-live-confusion-2026-04-28.md
