### `[[lesson-cooldown-key-globalization-2026-04-30]]`
**発見日**: 2026-04-30 | **修正**: rule:R3 commit `a88852f` (本体) + `d955aae` (regression test)

## 問題
`self._last_exit` が **`mode` 単独**を辞書キーにしていた:

```python
# 修正前 (バグ)
self._last_exit[mode] = {...}                # close時の書き込み
last_ex = self._last_exit.get(mode)          # entry時の読み出し
```

`mode` は `"scalp"` / `"scalp_eur"` / `"daytrade"` 等の単純 key で、**pair も direction も含まない**。close 時に `direction` を value 内に保存していたが、読み出し側は direction を一切参照せず単に最新 exit の経過秒で全方向を block していた。

## 症状
- USD_JPY scalp の SL exit 直後に **EUR_USD scalp も 60s 全停止** (異ペア巻き添え)
- BUY スカルプの SL exit 直後に **同 pair の SELL シグナルも block** (反対方向巻き添え)
- daytrade 900s, daytrade_1h 3600s, swing 14400s のクールダウン中、全ペア・全方向が停止 → N 蓄積を最大に毀損
- 連敗カウンタ `self._consec_losses[mode][signal]` は **direction-aware**(`mode_cl.get(signal, 0) >= max_cl`) だが、cooldown は `mode` 単独 → 設計の非対称が連敗ロジックを上書き
- 本番ログで「単一の SL hit が 7 ペア × 2 方向 = 14 cells を 60-3600s 停止」していた

## 原因
1. **辞書 key の暗黙の前提**: 初期実装時は scalp 1 pair (USD_JPY) のみで pair / direction 概念が薄く、mode 単独で十分だった。multi-pair / multi-direction 対応 (v6.x で導入) で key の責務が変わったが、key 構造は据え置き
2. **value にデータを保存して使わない**: close 書き込みで `"direction"` フィールドを保存していたが、読み出し側で使わず、定期的なリファクタで「保存しているのに参照しない」フィールドが見落とされた
3. **テスト不在**: cooldown lookup の独立性 (異ペア / 異方向 / shadow分離) を assert する unit test が無く、direction-agnostic な block を検出できなかった
4. **連敗 vs cooldown の非対称が不可視**: 連敗ロジックの direction-aware 設計と cooldown の direction-agnostic 設計が同一ファイル内で共存していたが、レビュー時に矛盾を指摘するメカニズムが無かった

## 修正
辞書 key を `(mode, instrument, direction, is_shadow)` の tuple に拡張。専用ヘルパーで lookup を集約:

```python
# modules/demo_trader.py
def _cooldown_key(self, mode, instrument, direction, is_shadow):
    return (mode, instrument, direction, bool(is_shadow))

def _get_cooldown_age(self, mode, instrument, direction, *, is_shadow=False):
    key = self._cooldown_key(mode, instrument, direction, is_shadow)
    last = self._last_exit.get(key)
    return None if not last else (datetime.now(...) - last["time"]).total_seconds()
```

書き込み 2 箇所 (`demo_trader.py:2165`, `:5152`) と読み出し 2 箇所 (`:3437`, `:4239`) を全て新 key に統一。

`is_shadow` を key に含めた理由: **shadow exit はそもそも実弾リスクなしなので live entry を止める必要が無い**。shadow と live を分離することで shadow 経路の N 蓄積を阻害しない。

regression test: `tests/test_entry_gates.py::TestCooldownKeyIndependence` (4 test)

## 教訓
**辞書キーは「同じ block 域に属する単位」を全て含める**。block の意図 (この cooldown は「同じ mode × 同じ pair × 同じ方向 × 同じ実弾リスクの再エントリー」を抑止する) を明示的に key 構造に反映する。value 内に分類情報を保存しているのに read 側で使っていない場合、key の責務が古い可能性が高い (技術負債のシグナル)。さらに**同一ファイル内で direction-aware と direction-agnostic な制御が混在していたら、設計の非対称が必ずバグを生む**ので統一する。
