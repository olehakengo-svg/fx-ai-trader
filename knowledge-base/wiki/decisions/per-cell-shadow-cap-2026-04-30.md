# Decision: Per-cell Shadow Cap (H1) + Hedge Bypass Removal (H2) — 2026-04-30

**ステータス**: 採用 (rule:R2)
**コミット**: `a88852f` (本体), `d955aae` (regression test)
**関連 lessons**: [[lesson-shadow-eligible-exposure-bypass-2026-04-30]] (C1), [[lesson-cooldown-key-globalization-2026-04-30]] (C2)
**関連 plan**: `/Users/jg-n-012/.claude/plans/shadow-open-position-cozy-quilt.md`

---

## Context

2026-04-30 のオープンポジション制限ロジック監査で 2 件の構造バグを発見:

- **H1**: `per-cell shadow 除外` ([demo_trader.py:2967-2971](../../modules/demo_trader.py)) が同 cell 内の shadow を上限カウントから完全除外し、duplicate observations を量産していた
- **H2**: ヘッジ shadow バイパス ([demo_trader.py:2981-2995](../../modules/demo_trader.py)) が score-max selection の比較 sample を破壊していた

両者は実弾リスク漏洩 (C1) ほど致命ではないが、**蓄積されている shadow 統計の信頼性を構造的に毀損**する。Wilson CI の偽縮小と戦略間ランキングの破壊により、demote/promote 判定で false positive を生む。CLAUDE.md の Rule 2 (Fast & Reactive — 構造的データ品質劣化は即修正) に該当。

---

## H1: Per-cell Shadow Cap

### 問題

```python
# 修正前
_mode_inst_trades = [t for t in open_trades if ...
                     and not t.get("is_shadow", False)]  # ← shadow を完全除外
if len(_mode_inst_trades) >= _mode_limit:
    if _is_slot_shadow_eligible:
        _is_shadow = True  # ← 上限なしに shadow を積み上げ可能
```

scalp の Live=2 が埋まった状態で shadow がカウントされず、同 cell に **shadow BUY 5本以上**同時保有可能。価格過程は単一なので 5本は相関 ρ≈1 の duplicate observations。

### 数学的結果

Wilson 信頼区間下限 `WL = (p + z²/2n - z√(p(1-p)/n + z²/4n²)) / (1 + z²/n)` は分母に √n を持つ。effective N が水増しされると CI が**偽縮小**し、`ema_trend_scalp` の `N=88, WR=20%` のような数字が「Bonferroni 補正でも有意」に見えてしまう恐れ。実際の独立観測数は cell 内 shadow 同時保有数で割って ~30 程度の可能性。

### 解決

`_shadow_per_cell_limits` 辞書を導入し、shadow を per-cell で別カウント:

| mode | live cap (`_mode_limits`) | shadow cap (`_shadow_per_cell_limits`) |
|---|---|---|
| scalp | 2 | 4 |
| scalp_5m | 1 | 2 |
| daytrade | 1 | 2 |
| daytrade_1h | 1 | 2 |
| swing | 1 | 2 |

shadow cap は live cap の概ね 2 倍。これは:
- Live 上限の単純倍 = 観測機会を 2 倍程度確保しつつ
- 上限を有限にして duplicate observations を限界づける

数値の根拠: Live 上限自体が portfolio σ² の経験則 (scalp は方向転換に対応するため 2、他は 1)。shadow は学習資産なので live より緩めるが、相関 1 の duplicate を防ぐ意味で **2 倍以下に抑える**。BT で実際の independent N を測ってから次回見直し。

---

## H2: Hedge Bypass Removal

### 問題

```python
# 修正前
if _hedge_blocked:
    if _is_slot_shadow_eligible:
        _is_shadow = True  # ← 逆方向も shadow で記録
```

Live BUY 中に逆方向 shadow SELL が同時保有可能。score-max selection で「BUY 戦略 score > SELL 戦略 score」だったとしても、SELL 側を shadow として DB に記録。

### 統計的結果

同一時刻 × 同一 pair × 逆方向の sample が両方記録されると:
1. 価格過程は 1 つしか無いので、片方は必ず逆風 → shadow WR が構造的に低下
2. 戦略間の WR / EV 比較で「ランキング情報」が破壊される (score 競争で負けた戦略のサンプルが追加される)
3. SHADOW_EMIT で観察される 20% 台の WR にこの artefact が混入していた可能性

### 解決

ヘッジ bypass を撤廃し、逆方向は **Live/Shadow 問わず常に block**:

```python
# 修正後
for _ot in _mode_inst_live + _mode_inst_shadow:
    if _ot.get("direction") and _ot["direction"] != signal:
        _block(f"hedge_block({_base_mode}/{instrument}:{signal})")
        return
```

shadow データの獲得機会が減るが、**60s dedup gate (`_maybe_reserve_signal_emit`) が同一 (entry_type, instrument, signal) tuple で 60s ブロックする**ので signal 反転時は 60s 経過後に shadow 化可能。dedup の存在により本ヘッジ bypass は不要。

---

## 実装

- **本体**: `modules/demo_trader.py:3033-3074` (rule:R2 範囲)
- **テスト**:
  - `tests/test_entry_gates.py::TestPerCellShadowCap` (H1 — 辞書定義の検証)
  - `tests/test_entry_gates.py::TestHedgeBypassRemoved` (H2 — bypass 経路撤廃の検証)
- **デプロイ**: `a88852f..origin/main` 経由 Render auto-deploy (2026-04-30 ~17:53 GMT+9)

---

## 検証 (out-of-scope, 別タスク)

H1/H2 は「shadow データ品質の構造的修復」なので、本番ログで以下を 1 週間 monitor:

1. `max_per_mode_pair(... shadow=4/4)` block の発生頻度 (H1 の cap 到達率)
2. `hedge_block(...)` 発生頻度 (H2 — bypass が無くなったので件数増加が想定)
3. shadow trade の per-cell 同時保有数の分布 (P95 が 4 以下に収束するか)
4. `_evaluate_promotions` が H1 適用後の shadow N で false positive 昇格を出さないか

---

## 関連 out-of-scope items (別 plan で推進)

- **H3**: Shadow → Live promotion 時の ExposureManager exposure rebalance (race condition)
- **H4**: `_evaluate_promotions` の Bonferroni α/616-cell 補正
- **M1**: `_max_open + 8 = 16` のマジックナンバー数学的根拠 (portfolio σ² からの逆算)
