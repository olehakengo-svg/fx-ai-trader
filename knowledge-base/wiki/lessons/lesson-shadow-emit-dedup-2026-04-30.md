---
title: SHADOW_EMIT 経路が _tick_entry の 60s dedup をバイパスしていた構造バグ
date: 2026-04-30
type: lesson
severity: HIGH
related: [[lesson-shadow-always-emit-cleanup-2026-04-28]], [[lesson-select-best-bottleneck-2026-04-28]], [[lesson-shadow-contamination]], [[sr-strategies-signal-track-2026-04-28]]
---

# SHADOW_EMIT が 60s dedup をバイパスし、tick 毎に shadow を量産していた (2026-04-30)

## 何が起きたか

ユーザーから「本番デモで shadow 戦略が同タイミングで複数発火している」との指摘。本番 Postgres を直接読めなかったため、コード経路を静的トレースしたところ、以下の **2 系統で gate が分離している** ことが判明:

- **Primary trade 経路**: `_tick(...)` → `_tick_entry(mode, cfg, sig, tf, instrument)` (`modules/demo_trader.py:2738`)
  - L3156-3171 で `_signal_key = (entry_type, instrument, signal)` をキーに 60s 重複防止 (`self._recent_signal_emits`) が動作
  - L3172 以降で 同価格帯ブロック / cooldown / max_open / hedge / SMC 等の guard chain が実行される
- **SHADOW_EMIT 経路**: `_tick(...)` → L2700-2734 の `for _se in sig.get("shadow_emit_signals")` ループ
  - `_tick_entry` を経由せず、`self._db.open_trade(... is_shadow=True)` を**直接呼んでいた**
  - 60s dedup・cooldown・同価格帯ブロックを**いずれも適用していなかった**

結果として、`SHADOW_ALWAYS_STRATEGIES = {vsg_jpy_reversal, rsk_gbpjpy_reversion, mqe_gbpusd_fix}` (`strategies/daytrade/__init__.py:201-205`) の戦略は、primary 競争で連敗するため **tick 毎に shadow_emit 候補に並び続ける** → tick 毎に新 UUID で `is_shadow=1` レコードが INSERT される構造。daytrade tick が ~30-60s 間隔だとすると、1 つの「シグナル機会」で数件〜数十件の shadow が `entry_time` ほぼ同時で連続生成される。

## 根本原因

**shadow_emit ループの設計時に「dedup は primary の責務」という暗黙仮定があった**。

`decisions/sr-strategies-signal-track-2026-04-28.md` で SHADOW_EMIT 経路を導入した際、最小実装として `open_trade(is_shadow=True)` を直接呼ぶ形にしたが、`_tick_entry` 内に閉じ込められていた `_recent_signal_emits` を共有しなかった。`_recent_signal_emits` は `__init__` で生成されるインスタンス属性で、API 上は両経路から触れる構造になっているにも関わらず、shadow_emit 側で参照する責務が抜けていた。

これは **memory: lesson-shadow-always-emit-cleanup-2026-04-28** で「per-bar dedup なし」と明記されていた既知の欠陥が、SHADOW_ALWAYS を `frozenset()` で空にしたことで一旦表面化を免れただけで、Phase 10 G2 (`vsg_jpy_reversal` / `rsk_gbpjpy_reversion` / `mqe_gbpusd_fix` を SHADOW_ALWAYS_STRATEGIES に再投入した 2026-04-29 commit `febe1cd` 系列) で**再発した**形。

## クオンツ規律違反

- **R3 違反検知の遅れ**: SHADOW_ALWAYS を再投入した 2026-04-29 時点で、過去の lesson-shadow-always-emit-cleanup-2026-04-28 を参照して「per-bar dedup なし」の構造的脆弱性を継承している事実をチェックすべきだった。再投入 commit に対する事前検証で「dedup gate を共有しているか」を確認していれば、本番デプロイ前に防げた。
- **partial quant trap (再発)**: `is_shadow=1` の N が tick 数分インフレされていたため、`learning_engine` の Wilson_BF / Bonferroni / Kelly 計算が**実シグナル発火回数ではなく tick 回数で割られていた**可能性。N の質を見ずに数だけ蓄積した形で、partial quant trap (memory: feedback_partial_quant_trap) の典型例。
- **本番監視の欠落**: `is_shadow=1` per-minute 件数の異常検知アラートを持っていなかったため、ユーザー目視まで気づけなかった。

## 修正 (commit `6a45bb2` rule:R3)

`modules/demo_trader.py:2700-2734` の shadow_emit ループに、`_tick_entry` と同じ `_recent_signal_emits` ベースの 60s dedup を移植:

```python
_se_signal_key = (_se_entry_type, instrument, _se_signal)
_se_now = datetime.now(timezone.utc)
_se_dedup_window = timedelta(seconds=60)
with self._lock:
    _se_last = self._recent_signal_emits.get(_se_signal_key)
    if _se_last and (_se_now - _se_last) < _se_dedup_window:
        continue
    self._recent_signal_emits[_se_signal_key] = _se_now
self._db.open_trade(... is_shadow=True)
```

key 空間を primary と共有することで、primary が出た直後の同 (entry_type, instrument, signal) shadow も自然抑止される。dedup window は primary 側と同じ 60s。

## 構造的対策 (次セッションで実装すべき P2)

1. **共通 gate helper の抽出**:

```python
def _maybe_reserve_signal_emit(
    self, entry_type: str, instrument: str, signal: str,
    *, window_sec: int = 60
) -> bool:
    """Return True if we can emit (and reserves the slot), False if recent dup."""
    key = (entry_type, instrument, signal)
    now = datetime.now(timezone.utc)
    with self._lock:
        last = self._recent_signal_emits.get(key)
        if last and (now - last).total_seconds() < window_sec:
            return False
        self._recent_signal_emits[key] = now
        # cleanup
        cutoff = now - timedelta(seconds=2 * window_sec)
        self._recent_signal_emits = {
            k: v for k, v in self._recent_signal_emits.items() if v > cutoff
        }
        return True
```

primary / shadow_emit / 将来の variant 経路すべてからこの helper を呼ぶようにし、key 空間と window を一元管理する。

2. **本番アラート**:

```sql
-- daily_review に追加候補
SELECT entry_type, instrument, COUNT(*) AS n
FROM demo_trades
WHERE is_shadow=1
  AND entry_time >= NOW() - INTERVAL '1 hour'
GROUP BY entry_type, instrument, date_trunc('minute', entry_time)
HAVING COUNT(*) > 1;
```

`HAVING COUNT(*) > 1` が任意の 1 時間枠でヒットしたら Discord 通知。

3. **再発防止チェックリスト** (SHADOW_ALWAYS_STRATEGIES 追加時の pre-flight):
   - [ ] 当該経路で `_recent_signal_emits` または共通 gate helper を経由しているか
   - [ ] 過去 24h の本番 demo_trades で同一 (entry_type, instrument, signal) bar が COUNT(*) > 1 でヒットしないか
   - [ ] N 集計が tick 数ではなく実シグナル発火回数で割られているか

## 影響範囲 (デプロイ前の汚染データ)

- `learning_engine` で SHADOW_ALWAYS 3 戦略の N が膨張していた可能性 → `wilson_lower` / `wilson_bf_lower` / `Kelly fraction` が信頼できない
- `entry_time >= 2026-04-29` の `is_shadow=1` × `entry_type IN ('vsg_jpy_reversal','rsk_gbpjpy_reversion','mqe_gbpusd_fix')` のレコードはクリーンアップ対象候補
- 修正デプロイ後 60 分以降のデータからクリーンに再蓄積される

## 関連 commit / decision

- 2026-04-28 `lesson-shadow-always-emit-cleanup-2026-04-28.md` — SHADOW_ALWAYS を `frozenset()` 化 (R2)
- 2026-04-29 `febe1cd` — Phase 10 G2 で 3 戦略を SHADOW_ALWAYS に再投入 (R3)
- 2026-04-30 `6a45bb2` — 60s dedup gate を SHADOW_EMIT 経路に移植 (R3) ← 本 lesson 対象

## 追記: 二次の構造的 leak — restart で in-memory state が消失する (2026-04-30 後半発見)

post-fix の loop 監視 (08:20 UTC) で、`_recent_signal_emits` の sub-60s rate が **81.2%** と発覚。診断カウンタ (`primary_called/blocked/passed`, `shadow_called/blocked/passed`) を追加して原因特定したところ:

- gate code 自体は **正常動作中** (primary path で blocked=43% を観測)
- leak rows (07:57-08:14 UTC, 19件) の発生窓は **2 commit deploy のタイミングと完全一致** (`87cc750`@07:58 + `8aade72`@08:05)
- 各 deploy → gunicorn 再起動 → `__init__()` 再実行 → `self._recent_signal_emits = {}` でクリア → 60s 履歴消失 → 連続 emit が「初回」として通過

### この発見の意味

dedup gate は機能していた。しかし **active development の deploy 連発で履歴が消失** → 60s window が再起動毎にリセットされる構造を持っていた。本番運用では deploy 頻度が低く実害は限定的だが、開発期は容易に劣化する。

### 構造的対策 (commit `<次の commit>`)

1. **DB ベース startup hydration** — `DemoDB.get_recent_signal_emits(window_sec=120)` を追加し、`DemoTrader.__init__` で過去 120 秒分の demo_trades 行から `_recent_signal_emits` を復元。再起動後も gate が即座に有効。
2. **Backfill cutoff の動的化** — `_DEDUP_BACKFILL_CUTOFF` を NOW に dynamic 化。deploy-storm leak rows (19件) も `dedup_violation=1` に flag されるようにする。
3. **`hydrated_from_db` 計測カウンタ** — `_dedup_stats["hydrated_from_db"]` で起動時の復元件数を可視化、deploy 後の gate 健全性を `/api/admin/dedup_status` で確認可能。

### 一般化された教訓

> **In-memory な dedup / cooldown / cache state は、process restart で必ず消失することを設計時に前提する。** 短い時間窓 (60s 等) を持つ gate は、deploy を「見かけ上の bypass」として誤動作させる。`__init__` で DB から hydrate するか、永続層 (system_kv 等) に書き出すか、stateless 判定 (DB 直接 query) のいずれかを選択すべき。
