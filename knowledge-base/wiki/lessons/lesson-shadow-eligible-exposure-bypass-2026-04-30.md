### `[[lesson-shadow-eligible-exposure-bypass-2026-04-30]]`
**発見日**: 2026-04-30 | **修正**: rule:R3 commit `a88852f` (本体) + `d955aae` (regression test)

## 問題
`modules/demo_trader.py:3081` (修正前) の ExposureManager bypass が **`_is_shadow_eligible`** で gating されていた:

```python
# 修正前 (バグ)
if not _is_shadow_eligible:
    _exp_ok, _exp_reason = self._exposure_mgr.check_new_trade(...)
```

`_is_shadow_eligible_full` は `entry_type in (FORCE_DEMOTED ∪ SCALP_SENTINEL ∪ UNIVERSAL_SENTINEL)` で True になる「**shadow 化する資格**」フラグ。実際に shadow に escalate されるのは per-cell / hedge / max_open のいずれかで slot bypass が triggered されたときのみで、その結果は `_is_shadow` (空変数 `_is_shadow=False` で初期化、escalate 時に True) に入る。

旧版は eligible だが Live スロット空きで normal Live (OANDA 送信可) として通過するパスでも `check_new_trade()` を skip していた。

## 症状
- FORCE_DEMOTED / Sentinel 戦略 (例: `ema_trend_scalp`, `sr_anti_hunt_bounce`) が Live スロット空き時に **20k currency cap / same-direction 3件 cap を全バイパスして OANDA 実弾注文を出す**
- ExposureManager.check_new_trade の通貨集中リスク制限が機能しない
- 観測ログ: `exposure_block` が全パターンで Live 経由で発火しない (実弾リスク漏洩)
- Render 本番ログで `[ALERT] Exposure blocked` が FORCE_DEMOTED 戦略について**一度も発火していなかった**ことを確認

## 原因
1. **意図と実装の乖離**: `v9.0` コメントは「Shadow/Demo bypass」と書かれていたが、実装は「**eligible** Demo bypass」で、最終的な shadow フラグではなく資格判定でgateしていた
2. **2 段階分離 (`v8.9`) の不完全な反映**: `_is_shadow_eligible_full` (フィルター免除用) と `_is_slot_shadow_eligible` (スロット制約免除用) を分離した時、`_is_shadow` (実際に escalate されたか) を最終 gate に使うべきポイントが exposure check で更新されなかった
3. **テスト不在**: FORCE_DEMOTED 戦略が Live 通過するパスの exposure check を assert する test が無く、通過数が 0 件でも警告されなかった

## 修正
`if not _is_shadow_eligible:` → `if not _is_shadow:` に narrow。`_is_shadow` は per-cell / hedge / max_open でいずれかが triggered された時のみ True なので、eligible でも Live 通過する場合は `_is_shadow=False` のまま exposure check が必ず走る。

```python
# 修正後
if not _is_shadow:  # 実際に shadow flag が立った場合のみ skip
    _exp_ok, _exp_reason = self._exposure_mgr.check_new_trade(...)
```

regression test: `tests/test_entry_gates.py::TestExposureBypassNarrowed`

## 教訓
**「資格 (eligible)」と「実際の状態 (effective)」を区別する**。bypass フラグは最終状態 (`_is_shadow`) で gating すべきで、資格フラグ (`_is_shadow_eligible`) で gating すると「資格はあるが該当しない」ケースが意図せずバイパスされる。同類: `_is_promoted_eligible` vs `_is_promoted`、`_can_emit` vs `_emitted` 等。設計レビューでは bypass 条件式の右辺がどの抽象レベルの変数を参照しているか確認する。
