# max_open グローバル上限が shadow 建玉を数えて live を削る — R3 修理の code derivation (2026-11-03)

**分類**: rule:R3 (構造バグ、365d BT スキップ、code derivation のみ)。観測: [[daily-observations-2026-11]] O-2026-11-02-1。registry `max-open-live-cap-counts-shadow-r3` (11-04)。修理 PR: PR #363 (autopilot 2026-11-03)。

## 1. 欠陥 (code 事実)

`modules/demo_trader.py` `_tick_entry` のグローバル上限節 (PR 前):

```python
_max_open = self._params["max_open_trades"]      # 8
_shadow_max = _max_open + 8                       # 16
_n_open = len(open_trades)                        # live + shadow の総数
if _n_open >= _max_open:
    if entry_type in self._COUNT_GATE_BYPASS_LIVE_EXCEPTIONS: LIVE 許可
    elif _is_slot_shadow_eligible and _n_open < _shadow_max: shadow 化 + "[SHADOW_BYPASS] max_open"
    else: _block("max_open(n/8)")
```

`open_trades = self._db.get_open_trades()` は `status='OPEN'` 全行 (is_shadow 0/1 とも)。per-cell 上限 `max_per_mode_pair` は 2026-04-30 (rule:R2 / H1) で `_mode_inst_live` / `_mode_inst_shadow` に分離済みだったが、グローバル上限は総数のままだった。

**帰結**: shadow 建玉が 8 本あれば open live 0 でも live-eligible 型 (bypass 例外非所属 = `usdjpy_carry_dip_accumulator` / `weekend_gap_fade`) が shadow に落ちる。kalman_d7 ×3 は例外所属で影響 0。

## 2. 実測 (estimand 宣言)

- 母集団: PROD snapshot 20,307 行、`entry_time ≥ 2026-10-05` (単一エンジン期)。live-eligible 型 = carry_dip + kalman_d7 + weekend_gap。計数 = reasons に `[SHADOW_BYPASS] max_open` を含む行数 / LIVE 行数。outcome 列は読まない
- carry_dip: LIVE 11 / `max_open` shadow 化 **1** (10-30 08:02:59Z row 20285、同時刻 open live 0) = live 機会喪失 **1/12**。全型 9 件
- 原則 1 (機会を逃すのが最大の敵) + Live vs Shadow 厳格分離の違反。lot / シグナル / 凍結値とは独立

## 3. 修理 (PR 後)

```python
_n_open = len(open_trades)                                       # 総数 (shadow 上限の母数、不変)
_n_open_live = sum(1 for _t in open_trades if not _t.get("is_shadow", False))
if _n_open_live >= _max_open:                                    # live 上限は live 建玉数のみ
    (bypass 例外 → LIVE / shadow eligible ∧ 総数 < 16 → shadow + marker / else block "max_open(live/8)")
elif _is_shadow and _n_open >= _shadow_max:                      # 上流 shadow 行にも総数上限 (メモリ保護)
    _block("max_open_shadow_cap(total/16)")
```

| ケース | live | 総数 | 旧 | 新 |
|---|---|---|---|---|
| carry_dip、open live 0、shadow 8 | 0 | 8 | shadow (`[SHADOW_BYPASS] max_open`) | **LIVE** |
| carry_dip、live 8 | 8 | 8 | shadow + marker | shadow + marker (不変) |
| carry_dip、live 8、総数 16 | 8 | 16 | block | block (不変) |
| kalman (bypass 例外)、live 8 | 8 | 8+ | LIVE | LIVE (不変) |
| 上流 shadow 行、live 0、総数 16 | 0 | 16 | block | block (reason は `max_open_shadow_cap`) |
| 上流 shadow 行、live 0、総数 8〜15 | 0 | 8–15 | 記録 + **誤 marker** `[SHADOW_BYPASS] max_open` | 記録、marker なし |

副作用: 旧実装は上流で shadow 化済みの行に総数 ≥ 8 で `[SHADOW_BYPASS] max_open` を**誤付与**していた (全型 9 件の一部はこれ)。修理後は live 候補だった行にだけ付く = readout の分子が正しくなる。block reason の parse 形式 `max_open(<n>/<limit>)` (`block_event_logger._METRIC_PATTERNS`) は不変、新 reason `max_open_shadow_cap` は計測なし (NULL)。

## 4. pin (tests/test_max_open_live_cap_counts_live_only_r3.py、7 本)

CF 1 (shadow 3 本 / live 上限 3 で LIVE のまま、revert で落ちる) / 対称 3 (live 上限は不変、live+shadow 満杯の hard block 不変、bypass 例外不変) / shadow 上限 2 (上流 shadow 行の総数 block、総数 < 上限で marker なし) / AST 1 (`_n_open_live` 比較、総数比較への回帰禁止)。

## 5. 非接触

lot 契約 / `_COUNT_GATE_BYPASS_LIVE_EXCEPTIONS` / per-cell 上限 / hedge_block / 凍結値 / シグナル。マージは live 経路変更のため `tools/pr_review_gate.py --wait 600` + open live 0 の窓 (sprint-triage §3.2 (a))。

## 6. 読み手

次の wiki-daily / autopilot で `[SHADOW_BYPASS] max_open` が live-eligible 型で 0 件 (deploy 後) を確認 → registry resolve。carry_dip N 30 (pre-reg 評価 N) は本修理で増えないが、修理前の喪失 1 本は D11 の分母に数えない (shadow 化行の outcome は読まない、S0 規約)。
