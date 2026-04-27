# M4 Scenario C — Design [SUSPENDED until Live N accumulates]

**起案者**: 2026-04-27 evening session 後継 + Phase A audit (2026-04-27 19:30 JST)
**Rule**: R2 (Fast & Reactive — 損失停止)
**承認状態**: ⏸ **着手保留** (Phase A 実測で N 不足判明)
**目的**: WR<35% AND N>=20 cell の Live 投入禁止 → Aggregate Kelly 押し上げ

---

## 1. 当初の前提 (2026-04-27 evening Agent#3)

> 出血源: ema_trend_scalp 4 cells (ΣR=-211)、stoch_trend_pullback × USD_JPY × scalp 等、計 ~30 cells
> WR<35% AND N>=20 の cell を Live 投入禁止 → Live Kelly **+0.0157 → +0.0723** (Gate 2 月利100%相当)

## 2. Phase A audit による前提崩壊 (確定)

`tools/phase_a_production_audit.py` で /api/demo/trades?limit=2000 を direct read:

| 指標 | Agent#3 報告 | Phase A 実測 |
|---|---:|---:|
| Total Live closed N (post-cutoff 2026-04-16) | 数百〜 | **26** |
| Aggregate Kelly | **+0.0157** | **-0.1230** |
| WR<35% AND N>=20 cell 数 | 30 | **0** |

詳細: `raw/audits/phase_a_production_audit_2026-04-27.md`

## 3. 結論 (確定)

**着手保留**。理由:

1. **N が足りない**: WR<35% AND N>=20 を満たす deny target cell が production で **0 件**。Live closed trade 全体でも N=26、cell 別に分割すると個別 cell N は更に小さい (個別 N=10 未満が大半と推測)
2. **Aggregate Kelly が negative**: production 実測 -0.1230 で Agent#3 +0.0157 と符号逆転。シナリオ C 適用前後の Kelly 改善幅を計算する根拠が崩壊
3. **着手で Kelly 改善は実証不能**: deny 対象なしのため M4 を実装しても実測で改善検証できない (target=0)

## 4. 着手 trigger (再起案条件)

以下のいずれかを満たしたら Phase A audit を再実行し、cell リストが変わったら本 design を再起案:

### Trigger A: Live data N 蓄積後
- Live closed total N >= 100 (約 4 倍)
- かつ任意の cell で N >= 20 が発生
- 期待タイムライン: **1-2 週間** (現状ペース)

### Trigger B: M2 effect 観察で Live fire 増加
- M2 (commit f896bf9) deploy 後の 24-72h で streak_reversal × USD_JPY + ELITE 3 戦略の Live fire が
  従来比 +20% 以上に増加
- → Live N 蓄積加速、Trigger A の前倒し可能性

## 5. 実装方法 (再起案時に採用予定の B 案、設計のみ保留)

`_LIVE_DENY_CELLS` 独立テーブル新設:

```python
# modules/demo_trader.py 内
_LIVE_DENY_CELLS = {
    # (entry_type, instrument, mode) — production audit で WR<35% AND N>=20 確定 cell のみ
    # 着手 trigger 満了後に Phase A audit で確定したリストに置換
}

# _tick_entry 内、_is_promoted 評価直後に挿入
if (entry_type, instrument, mode) in self._LIVE_DENY_CELLS:
    if not _is_shadow:
        _is_shadow = True
        _is_promoted = False
        self._add_log(
            f"[LIVE_DENY] {entry_type} {instrument} {mode} "
            f"→ shadow (production audit deny cell)"
        )
```

- `tests/test_live_deny.py` 4-5 case で gate 動作 unit test
- Pre-reg LOCK 別途 (`wiki/decisions/m4-live-deny-prereg-YYYY-MM-DD.md`)

## 6. 関連

- Phase A audit: `raw/audits/phase_a_production_audit_2026-04-27.{json,md}`
- Lesson: [[lesson-agent-snapshot-bias-2026-04-28]]
- 関連 H4 task: handover-2026-04-27-evening.md §1.4
- Agent#3 出力 (要原因究明): /private/tmp/claude-501/-Users-jg-n-012-test/d48e0764-.../tasks/a740bdb9...
- M2 修正 (発火頻度向上の前提): commit f896bf9
