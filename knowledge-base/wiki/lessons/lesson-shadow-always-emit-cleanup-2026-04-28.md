---
title: SHADOW_ALWAYS_STRATEGIES の無条件 emit がデータ蓄積汚染源になる構造的リスク
date: 2026-04-28
type: lesson
severity: HIGH
related: [[lesson-shadow-vs-live-confusion-2026-04-28]], [[../decisions/sr-strategies-signal-track-2026-04-28]], [[../strategies/sr-anti-hunt-bounce]], [[../strategies/sr-liquidity-grab]]
---

# SHADOW_ALWAYS の無条件 emit が EV<0 戦略を「自動的にデータ蓄積汚染源」にする (2026-04-28)

## 何が起きたか

`strategies/daytrade/__init__.py:179` の `SHADOW_ALWAYS_STRATEGIES` set に登録された戦略は、`select_best()` の max-score 競争で primary slot を取れなくても `split_shadow_always()` で抽出され、`demo_trader.py:2700-2734` の SHADOW_EMIT 経路で `is_shadow=1` として無条件 DB 永続化される。

設計意図: 低スコア戦略 (sr_anti_hunt_bounce score=3.0) でも N 蓄積路を確保する。

実害 (2026-04-28 本番実測, 4 日, 5 majors):
- sr_anti_hunt_bounce: N=300 closed, EV=-1.19p, sum=**-355.7p**
- sr_liquidity_grab: N=300 closed, EV=-0.65p, sum=**-390.8p**
- 両戦略とも GBP_USD のみ EV>0 (+0.31p, marginal)、ほか全 majors で EV<0
- OANDA forwarding: sr_anti 2 件、sr_liquid 4 件 (`is_shadow=0` の primary 経路でのみ流入)
- Phase 2 audit (sim) との乖離: 全 majors で 1.69-6.14p 楽観評価

## 根本原因

**SHADOW_ALWAYS は「N 蓄積」を主張するが、N の質を保証する gate を持たない**

1. EV<0 戦略でも emit が止まらない → trade DB に負エッジ data が連続流入
2. 流入 data は将来の `cell_edge_audit` / `Wilson_BF lower bound` / `Bonferroni n_test_eff` / `Kelly fraction` 計算に**直接 N として乗る**
3. 同一バーで複数候補が出れば全件 emit される (per-bar dedup なし)
4. これは **R2 (Fast & Reactive) の警報閾値 EV<0 が R2 自身で発動できない構造** = R2 違反

## クオンツ規律違反

- **CLAUDE.md L107 KB参照**: SHADOW_ALWAYS 導入時 (decision sr-strategies-signal-track-2026-04-28.md) に **EV<0 検出時の自動停止 gate** を設計しなかった
- **R2 警報閾値の不在**: N>=30 で EV<0 が確定したらその戦略を SHADOW_ALWAYS から自動除外する仕組みが必要だった
- **partial quant trap (memory: feedback_partial_quant_trap)**: 「N 蓄積」だけ見て「N の質」を見ていなかった

## 修正 (本コミット rule:R2)

```python
# strategies/daytrade/__init__.py
SHADOW_ALWAYS_STRATEGIES = frozenset()  # 一旦 empty
```

戦略本体の `enabled=True` は維持 → primary 競争で勝てば trade 化。SHADOW_EMIT 経路のみ完全停止。
これで本日以降の `is_shadow=1` × `entry_type IN ('sr_anti_hunt_bounce','sr_liquidity_grab')` の流入が止まる。

## 構造的対策 (次セッションで実装すべき P2)

```python
class ShadowAlwaysGate:
    MIN_N = 30
    R2_TRIGGER_EV_PIP = -0.5

    def should_emit(self, strategy_name: str, instrument: str) -> bool:
        n, ev_pip = fetch_recent_stats(strategy_name, instrument, days=7)
        if n < self.MIN_N:
            return True  # データ蓄積中
        return ev_pip > self.R2_TRIGGER_EV_PIP
```

`split_shadow_always()` 内で per-instrument 自動 gate。EV<0 になったペアだけ emit 停止。

## scalp loop の DT engine best 採用問題 (次タスクで対応)

調査中に判明: `app.py:signal_for_pair_tf()` は mode 引数なし、scalp loop でも DT engine を評価し、`signal=='WAIT'` のとき `_dt_best` を primary として流用 (L2547)。これにより `is_shadow=0` × `mode=scalp*` で 25 件の sr_anti_hunt_bounce が記録され、うち 1 件が OANDA forwarded。

本コミットの SHADOW_ALWAYS=empty では止まらない。**signal_for_pair_tf に mode/tf gate 追加** が必要だが影響範囲が広いため別タスクで R3 (構造バグ修正) として扱う。

## 再発防止チェックリスト

新戦略 / 新 SHADOW_ALWAYS エントリを追加する場合:
1. 自動 demotion gate (EV<0 で除外) があるか
2. per-bar dedup があるか
3. Pre-reg LOCK で MIN_N と R2 閾値を明記したか
4. 本番データ取得で 7 日後に再評価する schedule があるか
5. cell_edge_audit が Shadow data を **戦略別にフラグ可能**な構造か (汚染除外しやすい)
