# rnb_usdjpy — 153 日間「動いているが 1 行も出せない」モードと、測っていない量を名乗る block カウンタ

**日付**: 2026-09-05 / **Rule**: R3 (構造バグ + 診断、365d BT 不要)
**きっかけ**: 監視ログ `rnb_usdjpy:direction_filter` の 8 回連続 🔴 escalation (2026-08-26 → 09-04)、
「本ログで最も古い un-actioned 🔴」として繰越されていた項目
**関連**: [[lesson-block-counter-unmeasured-estimand-2026-09-05]] / [[m1-kpi-readout-and-mechanical-flip-2026-09-04]] (M3 スループット) / MEMORY `project_price_history_zero_guard_pr38`

---

## 0. 要約

監視が 8 日間追っていた「`compute_rnb_signal` の WAIT-path バグ」仮説は**外れ**。実体は独立した 2 つの構造事実で、
どちらもコードを読めば確定する (統計不要 = Rule 3)。

| # | 事実 | 帰結 |
|---|---|---|
| **A** | `direction_filter` カウンタは「方向が逆」と「シグナルが無い (WAIT)」を同じ名前で数えていた。`direction_filter` を持つ唯一のモード `rnb_usdjpy` の signal_fn は **SELL への return path を持たない** | このカウンタは **恒久的に 100% が WAIT**。「方向棄却」を **一度も**測っていない = 名前が測っていない量を名乗っていた |
| **B** | `rnb_support_bounce` は **QUALIFIED_TYPES にも CONDITIONAL_TYPES にも登録されていない** | BUY が出ても `unknown_type:rnb_support_bounce` で落ちる ⇒ `auto_start: True` のまま **shadow 1 行すら出せない**。導入 (2026-04-05) から **153 日** |

A は本セッションで修正 (挙動不変・ラベルのみ)。**B は Rule 1 (user 決裁) 事項なので修正せず、検出可能な状態に固定した。**

---

## 1. 事実 A — カウンタが測っていない量を名乗っていた

### 1.1 コード上の確定

`app.compute_rnb_signal` (`app.py:4358-4517`) の return は **2 つだけ**:

- `_WAIT` (`"signal": "WAIT"`) — 早期 return 計 9 箇所 (bar 数不足 / UTC 7-20 外 / zone 不一致 / 接近方向 / momentum / overshoot / rejection)
- 末尾の `"signal": "BUY"` — 全 AND 条件通過時のみ

**`"SELL"` を返す経路は存在しない** (docstring も "BUY-only (支持線反発)")。
一方 gate は `modules/demo_trader.py`:

```python
_dir_filter = cfg.get("direction_filter")          # rnb_usdjpy のみ "BUY"
if _dir_filter and signal != _dir_filter:
    _block("direction_filter"); return             # ← WAIT もここに落ちる
```

`_tick_entry` は **毎 tick 無条件で呼ばれる** (`signal="WAIT"` でも呼ばれる) ので、
WAIT tick は全て `direction_filter` として計上されていた。
`direction_filter` は block chain の**最初**の判定なので、他モードなら WAIT が落ちる
`conf<30` にも到達しない — 09-04 の観測「`conf<30` が ZERO」はこれで説明が付く。

### 1.2 実測 (12.8 年 / USD_JPY 15m, MASSIVE `data/cache/massive/USD_JPY_15m.parquet`)

`compute_rnb_signal` を各バーの確定足に対して評価:

| 窓 | 評価バー | BUY | SELL | WAIT |
|---|---:|---:|---:|---:|
| full (2013-10 → 2026-09、12.8y) | 315,623 | 2,225 (**0.705%**) | **0** | 313,398 (99.295%) |
| last 365d | 24,695 | 157 (**0.636%**) | **0** | 24,538 (99.364%) |
| last 60d | 4,199 | 22 (**0.524%**) | **0** | 4,177 (99.476%) |

**SELL = 0 は 3 窓すべてで厳密にゼロ** — 統計的推定ではなく構造の実測確認。
⇒ 旧 `direction_filter` の中身は **定義上 100% が WAIT**。

### 1.3 本番観測との整合

| 日付 | `rnb_usdjpy:direction_filter` / ticks | 備考 |
|---|---|---|
| 2026-08-26 | 1.0008 | 端数は窓境界 |
| 2026-08-31 | 0.9788 | |
| 2026-09-02 | 残余 family 40 | |
| 2026-09-03 | 残余 family 18 | |
| **2026-09-04** | **535 / 535 = 1.0000**、`conf<30` = 0 | 単一 filter がモードの全 tick を占める |

`interval_sec: 30` ⇒ **~2,880 blocks/日**。09-04 の全システム block 集計 (3,435 blocks / 46 keys) では
`direction_filter` が **15.6% = 第 4 位の family**。監視ダッシュボードの 1/6 が**恒久的に無情報**だった。

### 1.4 修正 (本セッション)

```python
if _dir_filter and signal != _dir_filter:
    _block("no_signal" if signal not in ("BUY", "SELL") else "direction_filter")
    return
```

**同一分岐内のラベル分離のみ。制御フロー・発注挙動・shadow 判定は一切不変。**
`direction_filter` を持つモードは `rnb_usdjpy` ただ 1 つなので作用域も 1 モードに閉じる
(この作用域自体を `test_direction_filter_is_only_used_by_rnb_usdjpy` で pin)。

### 1.5 検証可能な予測 (デプロイ後にこれで答え合わせする)

1. `rnb_usdjpy:direction_filter` → **恒久 0**。非ゼロが出たら §1.1 の構造前提が壊れた合図 = 本ページを更新する
2. `rnb_usdjpy:no_signal` ≈ tick 数 (~2,880/日)
3. `rnb_usdjpy:unknown_type:rnb_support_bounce` が **初めて可視化**され、tick の **~0.5-0.7%** に出る
   — これが RNB の live セットアップ頻度の初の直接観測になる

---

## 2. 事実 B — 登録漏れによる 153 日の dead mode

### 2.1 確定

`rnb_support_bounce` ∉ `QUALIFIED_TYPES` (104 型) ∪ `CONDITIONAL_TYPES` (空集合)。
`_tick_entry` の

```python
if entry_type not in QUALIFIED_TYPES and entry_type not in CONDITIONAL_TYPES:
    _block(f"unknown_type:{entry_type}"); return
```

は **shadow bypass を持たない無条件 gate**。⇒ BUY が出ても DB 行は 1 行も生まれない。

### 2.2 いつから

導入コミット `db5e3e4c` (2026-04-05「feat: RNB (Round Number Barrier) strategy — USD/JPY BUY-only」) は

- ✅ `MODE_CONFIG["rnb_usdjpy"]` (`auto_start: True`)
- ✅ `signal_fn` ディスパッチ (`_base_mode_fn == "rnb"`)
- ✅ `_1H_PRESERVE_SLTP` への追加
- ✅ `MAX_HOLD_SEC["rnb_usdjpy"] = 7200`

を配線した一方、**`QUALIFIED_TYPES` にだけ追加しなかった**。
`git log -S'"rnb_support_bounce"' -- modules/demo_trader.py` は **この 1 コミットのみ** =
その後も一度も登録されていない。⇒ **2026-04-05 → 2026-09-05 = 153 日**。

> これは `deploy` エージェントの「4 箇所同期」チェックリストが防ぐはずだった型そのもの。
> 既存テスト `tests/test_preserve_types_tick_entry.py` は
> 「rnb_support_bounce is in the preserve set but NOT in QUALIFIED_TYPES … pins that current behavior」
> と **事実を正しく記録していた**が、それを「意図された設計」として pin しており、
> **異常として上申する読み手がいなかった** (M1 KPI と同じ「読み手不在」型、[[m1-kpi-readout-and-mechanical-flip-2026-09-04]])。

### 2.3 恒久ガード (本セッションで新設)

全 `auto_start` モードについて、その signal_fn が返しうる **literal** `entry_type` が
`QUALIFIED ∪ CONDITIONAL ∪ BLOCKED` に含まれることをテストで pin。
変数経由で entry_type を組む関数 (`compute_daytrade_signal` 等) からは WAIT sentinel の
`"wait"` しか抽出できない = ガードは **false positive を出さない保守側**に倒れる。

走査結果 (auto_start 22 モード): **違反は `("rnb_usdjpy", "rnb_support_bounce")` の 1 件のみ**。
既知集合との **完全一致** (⊆ ではなく ==) で assert するので、
**新規ドリフトも既知ドリフトの解消も必ずテストを落とす** = どちらでも判断が要求される。

---

## 3. M3 スループットへの含意 (Rule 1 決裁事項の提示 — 本セッションでは執行しない)

[[m1-kpi-readout-and-mechanical-flip-2026-09-04]] §6 で M3 (clean live N≥30 セル × 3) が
「エッジ不在」でなく「**発火機会不足**」に律速され最短 ~14 ヶ月と起票された。その文脈で:

| セル | 発火頻度 |
|---|---:|
| `usdjpy_carry_dip_accumulator×USD_JPY×BUY` (現行最速) | **2.10 /週** |
| `price_shock_rev_eur_gbp_h1_long` | 0.93 /週 |
| `price_shock_rev_aud_jpy_h1_long` | 0.47 /週 |
| **`rnb_support_bounce×USD_JPY×BUY` (未登録・確定足ベース推定)** | **3.0 /週** (365d: 157 setups / 52.1 週) — 12.8y 平均 3.3 /週 |

登録すれば shadow 蓄積レーンとして現行最速セルを上回る頻度になりうる。**ただし採用は Rule 1**:

- ⚠️ **estimand 注意**: 上表は**確定足**評価。live は 30 秒ごとに**形成中バー**を評価するため、
  消える一時的 BUY を拾う。live 実測頻度はこれより高く・ノイジーになりうる (§1.5 の予測 3 で実測が取れる)
- ⚠️ config コメントの `BUY EV=+7.7` は 2026-04-05 の Phase1/2 BT (`_rnb_phase1_bt.py` / `_rnb_phase2_bt.py`) 由来で、
  **BE/Trail ablation 前**の数字。MEMORY `project_be_trail_inflates_python_bt_wr` (WR +20pp 水増し) の対象
- ⚠️ `QUALIFIED_TYPES` 追加は `_UNIVERSAL_SENTINEL` 経由の minlot live 経路にも触れうる = **無条件 shadow ではない**
- ⚠️ MEMORY 教訓「無条件 emit 設計は EV<0 で自動的にデータ汚染源化する。bypass には R2 自動 demotion gate を併設する」

**提案 (user 決裁)**: 365d BT を BE/Trail ablated で再走 → Bonferroni → pre-reg LOCK →
shadow 限定登録 (+ R2 自動 demote gate 併設) の Rule 1 手続きに乗せる。
registry: `rnb-support-bounce-registration-decision`。

**本セッションでは登録しない。** 現状 (auto_start 継続・登録なし) は
①原則 1 に反しない (このモードは元から 1 行も出せない = 止めるものが無い)
②`_price_history` への USD_JPY 実 Close 供給 (2026-07-06 `PRICE_HISTORY_GUARD` 修正の対象) を壊さない
③§1.5 の予測 3 でセットアップ頻度の live 実測が無料で取れる、の 3 点で維持が合理的。

---

## 4. 変更したもの / しなかったもの

| | 内容 |
|---|---|
| ✅ 変更 | block 理由ラベルの estimand 分離 (`no_signal` / `direction_filter`)。**挙動不変** |
| ✅ 新設 | `tests/test_rnb_block_reason_estimand.py` 7 本 (挙動 pin 3 + 構造 pin 4)。**counterfactual 8/8 が所望どおり落ちる**ことを確認、初回素通りゼロ |
| ❌ しない | `rnb_support_bounce` の登録 (Rule 1 = user 決裁) |
| ❌ しない | `auto_start: False` 化 (§3 の 3 点により維持が合理的) |
| ❌ しない | `conf<30` 等の他 block ラベルの estimand 分離 — 同型の折り畳みだが**全モードの block 家族構成が変わる**ため、影響評価を伴う別件として起票 |
