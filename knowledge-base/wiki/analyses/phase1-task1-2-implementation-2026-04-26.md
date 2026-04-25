# Phase 1 Task 1+2 実装ログ (2026-04-26)

**Date**: 2026-04-26
**Phase**: Edge Reset Phase 1 (Option A: 検証性最優先 scope)
**Plan**: `/Users/jg-n-012/.claude/plans/luminous-fluttering-shannon.md`
**Status**: 実装完了、commit + push 済

## 1. 実装スコープ (Option A 採用)

ユーザー意思決定で **Option A: Phase 1 Task 1+2 のみ** を選択。
クオンツ判断: 単一セッションで Task 3+4 (MTF gate 復活 + A/B) まで詰めると、
複数 change が multivariate confound して Live Kelly 改善への寄与を切り分け不能になる。

### 本セッション scope (実装済)

- **Task 1**: `modules/htf_data_source.py` 新規 — OANDA native H4/D1 fetcher
- **Task 2** (plumbing only): `MassiveSignalEnhancer` 経由で `apply_policy()` を wire up

### 本セッション **out of scope** (次セッションへ)

- Task 3: MTF gate 復活 (`app.py:1665-1681` 再有効化)
- Task 4: A/B 測定 (mtf_gated vs label_only の WR 差)
- `app.py:2740-2785` compute_daytrade_signal の ema_boost / MACD / VWAP deviation 統合
  - 理由: app.py 13560 行の主シグナル経路。entry_type 解決タイミングが分岐構造に
    依存しており、安全な統合には独立検証が必須

## 2. Task 1: OANDA native H4/D1 fetcher

### 設計判断

**問題**: 従来 H4/D1 は M5 を `resample_df()` で集約していた。
- microstructure 喪失 (集約により bar 内 tick の挙動が消える)
- look-ahead 潜在リスク (resample 完了時刻の曖昧性)
- η²<0.005 の単一 TF ADX に依存し統計的にノイズと変わらない

**解決**: OANDA `/v3/instruments/{instrument}/candles?granularity=H4&price=M` を直接呼ぶ。
- `complete=True` バーのみ採用 (look-ahead 除去)
- TTL キャッシュ (H4: 5min, D: 30min)
- fail-graceful (OANDA 未設定/429/network error 時は None 返し、上位で fallback 可)

### API

```python
from modules.htf_data_source import fetch_htf_candles

df = fetch_htf_candles("USDJPY=X", "H4", count=100)
# index: tz-aware UTC datetime
# columns: open/high/low/close/volume + Capitalized aliases
# attrs: instrument, granularity, fetched_at, source="oanda_native"
```

### 設計上の約束

- look-ahead protection: `complete=False` のバーは必ず drop
- DI: `client=` 引数で OandaClient mock 可能 → tests がリアル API を叩かない
- ファイル分離: 既存 `modules/oanda_client.py` を変更せず、新ファイルで完結
- 副作用なし: import 時点では何もしない

### Tests (17/17 PASS)

`tests/test_htf_data_source.py`:
- normalize_instrument の各 input pattern
- happy path (DataFrame 返却 / OANDA 引数正確 / source 属性)
- look-ahead protection (incomplete bars drop / 全 incomplete で None)
- failure modes (unconfigured / OANDA error / exception / invalid granularity / empty / malformed)
- caching (cache hit / disabled / stats)

## 3. Task 2: strategy_category.apply_policy() を MassiveSignalEnhancer に統合

### 設計判断 (クオンツ補正)

当初 plan は app.py の compute_daytrade_signal にも統合する予定だったが、
13560 行の主シグナル経路で entry_type 解決タイミングが複雑なため、
本セッションでは `modules/massive_signals.py` 経由のみに絞った。

理由 (Option A の趣旨):
- app.py 統合は Live trade に直接影響 → 慎重な検証が必要
- `MassiveSignalEnhancer.enhance()` は `/api/signal` API view 専用
  (app.py:9712 のみで使用、Live entry decision には未関与)
- → API view 側で plumbing を整備 → app.py 統合は Phase 1.5 で安全に分離可能

### 実装 (3 階層)

#### (a) `modules/strategy_category.py`

`_POLICY` を全エントリ 0.0 に統一し、Phase 1.5 用キーも追加:

```python
_POLICY: Dict[str, Dict[Category, float]] = {
    "vwap_zone":           {"TF": 0.0, "MR": 0.0, "BR": 0.0, "OTHER": 0.0},
    "vwap_slope":          {"TF": 0.0, "MR": 0.0, "BR": 0.0, "OTHER": 0.0},
    "institutional_flow":  {"TF": 0.0, "MR": 0.0, "BR": 0.0, "OTHER": 0.0},
    "mtf_alignment":       {"TF": 0.0, "MR": 0.0, "BR": 0.0, "OTHER": 0.0},
    "volume_profile_hvn":  {"TF": 0.0, "MR": 0.0, "BR": 0.0, "OTHER": 0.0},
    "volume_profile_lvn":  {"TF": 0.0, "MR": 0.0, "BR": 0.0, "OTHER": 0.0},
    # Phase 1.5 candidate keys (app.py compute_daytrade_signal 統合用)
    "ema_alignment":       {"TF": 0.0, "MR": 0.0, "BR": 0.0, "OTHER": 0.0},
    "macd_alignment":      {"TF": 0.0, "MR": 0.0, "BR": 0.0, "OTHER": 0.0},
    "vwap_deviation":      {"TF": 0.0, "MR": 0.0, "BR": 0.0, "OTHER": 0.0},
}
```

過去 commit 9787dd8 当時の仮説初期値 (TF:1.0/MR:-1.0/BR:0.5 等) は
**BT 楽観バイアス + 検証なし**で設定されていたため Phase 1 で凍結。
Phase 1.5 で shadow N≥15/category の monotonicity 実測後に data-driven tuning。

#### (b) `modules/massive_signals.py`

各 enhancer に `entry_type: Optional[str] = None` 引数追加:

```python
def _vwap_zone_analysis(self, df, direction, entry_type=None) -> dict:
    ...
    raw_adj = 0  # Phase 1: keep raw at 0 until monotonicity confirmed
    result["conf_adj"] = int(_apply_policy("vwap_zone", entry_type, raw_adj))
```

`enhance()` は entry_type を `base_signal["entry_type"]` から fallback で解決し、
内部 enhancer に貫通させる。

#### (c) Tests (19/19 PASS)

`tests/test_strategy_category_plumbing.py`:
- `apply_policy()` 単体: 全エントリ 0.0 → 任意 raw で 0.0 返し
- `monkeypatch` で _POLICY 書き換え時に scale が反映されることを確認
- `category_of()` の TF/MR/BR/OTHER 判定
- `MassiveSignalEnhancer.enhance()` の plumbing 検証:
  - entry_type 未指定 / TF / MR で confidence が 50 のまま (中立)
  - base_signal["entry_type"] からの fallback
  - vwap 無し / 短い df で base そのまま返却
- enhancer 内部関数の entry_type 引数受領

## 4. Verification (本セッション内完結)

| Check | 結果 |
|---|---|
| 新規 tests/test_htf_data_source.py | **17/17 PASS** |
| 新規 tests/test_strategy_category_plumbing.py | **19/19 PASS** |
| 既存 tests 全 280 件 (regression) | **280/280 PASS** |
| Pre-commit consistency check | ✅ 全 6 チェック通過 |
| app.py / massive_signals.py syntax | ✅ AST parse OK |

合計 **316 tests pass**, 既存に対する regression なし。

## 5. Phase 1.5 タスク (次セッション)

### Task 3 候補: MTF gate を category 別で復活

- `app.py:1665-1681` の disable された soft modulation を、
  `apply_policy("mtf_alignment", entry_type, raw)` 経由で復活
- 復活前に shadow N≥100 で TF/MR × MTF state の 2D WR 確認
- TF aligned: 12.9% → ≥20% に回復するか
- MR aligned: 30.3% を維持するか

### Task 4 候補: A/B 測定 (`tests/test_ab_gate.py` 既存)

- 1 週間以上 shadow 走らせた後に WR 差を Wilson 95% CI で検証
- 統計的有意性が確認されたら gate を full enable

### Task 5 候補: app.py compute_daytrade_signal 統合

- `app.py:2740-2785` ema_boost / MACD / VWAP deviation を `apply_policy()` 経由化
- entry_type が解決される箇所まで dispatch を追って、安全な hook point を特定
- ★ Live trade 影響範囲が大きい change のため**独立コミット**で実施

### Task 6 候補: _POLICY data-driven tuning

- shadow データで `(enhancer, category) × (raw_adj, has/no) × WR` の 3D 集計
- monotonicity 確認後、Phase 1.5 で _POLICY 値復活
- 凍結された過去仮説値 (TF:1.0/MR:-1.0/BR:0.5) は**廃棄**し、
  実測ベースで再設定

## 6. クオンツ的注意点 (継続監視)

- ❌ **「全 _POLICY を一気に活性化」誘惑**: Phase 1 Q2 (edge existence) 検証なしの
  policy 活性化は過去のラベル神経化と同じ症状治療の再生産
- ❌ **app.py への急ぎ統合**: 13560 行の主経路で multivariate confound の温床
- ✅ **shadow データ蓄積期間を尊重**: 1 週間 N≥100 が最低条件 (Wilson CI 計算可能)
- ✅ **A/B router (mtf_gated vs label_only)** で hash-based 50/50 振り分け確実化

## References

- Plan: `/Users/jg-n-012/.claude/plans/luminous-fluttering-shannon.md`
- [[edge-reset-direction-2026-04-26]] — Phase 0 方向転換決定
- [[lesson-label-neutralization-was-symptom-treatment-2026-04-26]] — meta-lesson
- [[tf-inverse-rootcause-2026-04-23]] — TF/MR 逆校正実測
- [[bt-live-divergence]] — 6 構造的楽観バイアス
- 関連 commit: `b37ee8b` `9787dd8` `2a6d1da` `91f34ac` `51b8cd2` (Phase 0)
