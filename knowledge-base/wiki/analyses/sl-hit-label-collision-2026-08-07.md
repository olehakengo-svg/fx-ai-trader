# `SL_HIT` ラベル衝突 — 勝ち決済が SL 狩り防御を発火させていた (2026-08-07, rule:R3)

**分類**: Rule 3 (構造バグ / 算数破綻) — 365日BT スキップ、code derivation + 本番実測で確定
**きっかけ**: 2026-08-05 daily で提起された「`SL_HIT` の 46.2% が正 PnL」= ラベル汚染疑い (2日間 未着手のまま繰越)
**結論**: **汚染ではなく「ラベル衝突」**。データは正しく、`SL_HIT` という 1 ラベルが**経済的に正反対の 2 事象**を指していた。ただし**下流の防御ロジック 2 本が「損切りされた」前提で消費していた**ため、実挙動のバグである。

---

## 1. 何が起きているか (機構)

`modules/demo_trader.py::_check_sltp_realtime` の close_reason 判定:

```python
if direction == "BUY":
    if price <= sl:          # ← sl は「現在の」SL
        close_reason = "SL_HIT"
```

`sl` は entry 時の値に固定されていない。同じ関数の上流で **BE-lock / トレーリング / Profit Extender** が `modify_sl_sync` + `update_sl_tp` で SL を**利益側へ動かす**。したがって:

- トレールが利益側へ動いた SL に価格が触れて決済 → **利確 exit なのに `close_reason="SL_HIT"`**

`SL_HIT` は「**現在の SL に触れた**」以上の意味を持っていない。ラベル自体は嘘をついていない — 名前と下流の解釈が間違っていた。

## 2. 本番実測 (N=3308, `/api/demo/trades?limit=4000`, 2026-08-07 取得)

判別子 = **SL が entry のどちら側にあるか** (BUY: `sl>entry` なら利益側)。

| SL の位置 | N | pnl>0 | pnl<0 | pnl=0 | pnl 中央値 | MFE 中央値 |
|---|---:|---:|---:|---:|---:|---:|
| **利益側** (BE/トレール後) | 1894 | **1848 (97.6%)** | 44 | 2 | **+2.00p** | 5.70p |
| **リスク側** (当初の保護 SL) | 1414 | 6 | **1408 (99.6%)** | 0 | **−6.95p** | 0.00p |

**誤分類は 50/3308 = 1.5%** — SL の位置は事実上完全な判別子。仮説「BE/トレール由来」は棄却されず、他の説明 (labeller のランダム欠陥) は MFE 中央値 5.70p vs 0.00p の分離で否定される。

`outcome` フィールドでの内訳: **WIN 1792 (54.2%) / LOSS 1441 / BREAKEVEN 75**。

> 08-05 に記録された「46.2%」は 106 本の小標本値。全体では **54.2%** で、方向は同じだが**過小評価**だった。

## 3. 実害 — 防御ロジック 2 本が勝ちで発火する

`_sl_hit_history` は SL 狩り検出用のフィードで、消費者は 2 本とも「たった今ストップ狩りに遭った」前提:

| 消費者 | 挙動 | 勝ちで発火したときの害 |
|---|---|---|
| **cascade cooldown** (`_sl_hit_history` → `_block(cascade_cd)`) | 同一 instrument の**全戦略**を 45–600s ブロック (scalp 45 / DT 90 / DT-1h 300 / swing 600) | **勝ちトレール決済の直後に、そのペアの攻撃を全面停止**。4原則 #1「攻める」/ #4「攻撃は最大の防御」に正面から反する |
| **Fast-SL 適応防御** (hold<120s かつ直近5分) | 次エントリーの SL を `ATR×0.3` 拡大 | **勝ち決済を根拠に次トレードの損失幅を広げる**。リスク幾何を無根拠に悪化 |

**発火イベントに占める誤発火率 = 1792/3308 = 54.2%**。
Fast-SL 側 (hold<120s) は **315 件中 180 件 = 57.1% が勝ち**。

誤発火の instrument 分布 (上位): USD_JPY 494 / GBP_USD 444 / EUR_USD 306 / GBP_JPY 199 / EUR_JPY 185 — **主力ペアに集中**。

## 4. なぜ「構造バグ」と断定できるか (Rule 3 の根拠)

同じ close 経路の**直前のブロック**が、**同一目的で既に WIN を除外している**:

```python
# ── クールダウン記録（SL後の即再エントリー防止、WINは除外）──
if outcome != "WIN":
    self._last_exit[_ck] = {...}
    self._total_losses_window.append(...)

# ── SL狩り対策: SL_HIT履歴記録（カスケード防御 + Fast-SL検出用）──
if close_reason == "SL_HIT":        # ← ガード無し
    self._sl_hit_history.append(...)
```

**「SL 後の再エントリーを止める」という同一意図の 2 ブロックが、隣接して非対称に書かれている。** 統計的新規主張ではなく設計の内部矛盾なので、365日BT を要さない (CLAUDE.md Rule 3)。

## 5. 修正 (本コミット)

1. **`modules/demo_trader.py`** — `if close_reason == "SL_HIT" and outcome != "WIN":`
   - `== "LOSS"` ではなく `!= "WIN"` を採用: BE 決済 (75 本) は**依然として逆行スイープの証拠**なので防御に残す。隣接ブロックの規約とも一致
2. **`modules/learning_engine.py`** — `sl_losses` を `outcome=="LOSS"` で絞る (変数名どおりの意味に)
3. **`modules/daily_review.py`** — `sl_hits` 同上。両者とも「SLヒット率 > 60/70% → **SL幅拡大検討**」を焚く advisory で、生カウントでは **82.7%** (真の損切り率は **36.0%** = 1441/4000) になり、**勝ちが多い book に対して SL 拡大を勧めていた**
4. **`tests/test_sl_hit_history_win_guard.py`** — AST レベルの回帰ピン 4 本 (負のコントロール検証済: 修正前ソースで assert が落ちることを確認)

### 意図的に**やらなかった**こと

- **`close_reason` の改名 (`TRAIL_EXIT` 等) はしない。** DB の既存 3308 行と全 BT/分析ハーネスが `SL_HIT` をキーにしており、改名は estimand の非可換な破壊 + 履歴比較不能を招く。ラベルは据え置き、**消費者側を正す**方針を採用
- **shadow 行の扱いは変更しない。** 誤発火 1792 件中 1786 件が `is_shadow=1`。cascade 防御は価格レベルの microstructure 事象を見るものなので shadow 由来の混入は設計上ありうる (要検討事項として記録するが、本コミットの scope 外)

## 6. 波及 — 今後の分析規律

**`close_reason` 起点の分析は全て、`outcome` または SL 位置での分割を前提にすること。**

影響を受ける既存記述:
- `modules/shadow_demote_registry.py:40` の demote 根拠「**SL_HIT 56.2%**」— この 56.2% は本ページの汚染値そのもの。**当該 demote 判断の再検討が必要** (※ demote は保守側なので緊急性はない。R2 で別途)
- v2.3 T3 [[payoff-asymmetry-diagnosis-2026-07-07]] の payoff 非対称診断 — `close_reason` を使っている箇所があれば再確認
- MEMORY `project_be_trail_inflates_python_bt_wr` (BE/Trail が Python BT の WR を ~20pp 膨らませる) と**同一機構**。BT 側で既知だった歪みが、live のラベルと防御ロジックにも出ていた

## 7. 未解決 (本コミット外)

- **`_sl_hit_history` に shadow 行を入れる是非** — 上記 §5
- **cascade_cd / Fast-SL の block 実数の観測系が無い** — `_block(cascade_cd)` は audit に出ない。修正の効果 (発火 −54%) を実測するには block カウンタの輸出が要る。本日の「シグナル供給が 5 session 連続で半減」(2026-08-06 daily 核心2) の候補要因の 1 つでもあり、**要 instrumentation** (次の作業候補)
- `modules/demo_trader.py:7373` 付近の exit 文言生成は `outcome=="LOSS"` 側でのみ `SL_HIT` を「逆行SL」と表示しており**既に正しい** (修正不要、確認済)

## 関連
- `raw/trade-logs/` の 2026-08-05 / 2026-08-06 daily (提起元)
- [[payoff-asymmetry-diagnosis-2026-07-07]] (v2.3 T3)
- MEMORY: `project_be_trail_inflates_python_bt_wr`
