---
id: 20260603-1635-sr-fib-confluence-v3-redesign-bt
priority: P1
gate: R3
rule: R3
status: superseded
created: 2026-06-03
closed: 2026-06-05
owner: claude
superseded_by: 20260604-1513-sr-fib-confluence-v3-resume-bt
closure_reason: 22h stall (2026-06-03 16:38 JST 起動 → 07:40 UTC 以降 log 停止、auto-expired)。working tree に V3 実装 + tests は残存、BT runner と実行のみ未了。Resume task が supersede。queue cleanup (2026-06-05 新方針 Codex=review/rescue 層) で done に移動。
---

# sr_fib_confluence V3 redesign — Classical MR+Follow combined (TV-validated PF 1.194)

**Rule classification**: R3 (Fast & Loose — shadow-first redesign, BT は軽量 sanity
filter のみ。Accept gate は v2.1 catastrophic check のみ。Live promotion 基準を
BT に課さない。memory `[feedback_shadow_first_quant_architecture]` 準拠)

## Background — なぜこれを入れるか

prod の `sr_fib_confluence` shadow が **直近 30 日で N=248 / WR 19.8% / PnL=-893 pip**
と最大級の bleeding を出していた (cell_negative_edge_audit 2026-06-03 で 37 NG cell)。
原因究明のため 2026-06-03 session で TradingView Pine v6 に再実装して反復検証した結果、
**致命的な direction バグ + 設計欠陥** が判明:

### 既存 (legacy `_evaluate_legacy`) の致命傷

1. **EMA 順張り continuation トリガー** が **Fib MR 思想と真逆** を実装している
   - 現実装: `ema_score > thresh AND ema9 > ema21 → signal="BUY"`
   - 結果: 「Fib 抵抗線にぶつかる直前で順張り BUY」 → 構造的に負ける
   - memory `[feedback_ma_filter_breaks_mr]` の派生罠

2. **6 fib levels の symmetry 重複**: f382_bull == f618_bear など、unique level は 3 本
   のみだが全 6 計算して nearest 取っているため計算冗長

3. **impulse 方向 (swing direction) 未検出**: classical Fib retracement は「impulse 後
   の押し目で順張り」が古典正しい用法だが、現実装は swing 方向を見ずに固定 logic で発火

### TV 検証 (Pine v6 on EUR_USD M15, 365d) で確認した V3 設計

順次 variant を試して下記が finalist:

| Variant | N | WR | PF | PnL | Max DD |
|---|---:|---:|---:|---:|---:|
| 順張り (legacy 再現) | 601 | 33.11% | 0.988 | -0.32 | 4.12 |
| direction 反転 | 609 | 34.32% | 1.073 | +1.87 | 2.14 |
| + ADX 20-30 band | 499 | 34.87% | 1.138 | +2.72 | 1.70 |
| + Fib 50% mid 除外 | 387 | 36.43% | 1.238 | +3.60 | 1.44 |
| **Classical MR+Follow combined ★** | **529** | **37.62%** | **1.194** | **+4.12** | **1.63** |
| (参考) SHORT only | 295 | 41.02% | 1.39 | +4.39 | 0.91 |
| (参考) SHORT+H4 bear hybrid | 152 | 44.08% | 1.544 | +2.92 | 0.57 |

**WFO 3-fold (Classical MR+Follow combined)**: F1 PF 1.326 / F2 1.245 / F3 1.167 で 3/3 PASS、
全 fold PnL>0。over-fit signal 不検出。

### 採用 variant

ユーザ判断: **「Both (Classical MR+Follow combined, PF 1.194)」を prod に適用**。理由:
- WFO 全 fold PASS で時系列 robust
- direction バイアス特化 (SHORT only) より LONG/SHORT 両方取って regime 依存性を低減
- impulse 方向だけで自動的に LONG/SHORT 決まるので EMA filter 不要 (理論的にクリーン)

## V3 設計仕様 — 詳細

### 1. Impulse direction detection (新規)

```python
# df は 15m bars (Open/High/Low/Close)
swing_lb = 100
swing_high = df["High"].rolling(swing_lb).max()
swing_low  = df["Low"].rolling(swing_lb).min()

# 現 bar から swing extreme を付けた bar までの距離 (bars since)
# Pine の ta.barssince(high >= sh) と同等
last_idx = len(df) - 1
high_age = 0
for i in range(last_idx, max(0, last_idx - swing_lb), -1):
    if df["High"].iloc[i] >= swing_high.iloc[last_idx]:
        high_age = last_idx - i
        break
# 同様に low_age
low_age = 0
for i in range(last_idx, max(0, last_idx - swing_lb), -1):
    if df["Low"].iloc[i] <= swing_low.iloc[last_idx]:
        low_age = last_idx - i
        break

is_up_impulse   = high_age <  low_age  # swing_high の方が直近 → 上昇 impulse 後
is_down_impulse = low_age  <  high_age
```

Pure Python ループでも、numpy 化 (`np.argmax(df["High"].values[-swing_lb:][::-1] >= sh)`)
でもよい。BT 全 bar スキャン時は vectorize 推奨だが、daytrade evaluator は 1 bar/呼出
なので素朴実装でも OK。

### 2. Fib levels (50% mid を **除外**)

```python
rng = swing_high.iloc[last_idx] - swing_low.iloc[last_idx]
fib_a = swing_high.iloc[last_idx] - rng * 0.382  # = sl + rng * 0.618
fib_b = swing_high.iloc[last_idx] - rng * 0.618  # = sl + rng * 0.382
# 50% mid (sh - rng * 0.5) は除外 — TV BT で 50% mid 含むと PF 1.073→1.138 改善が頭打ち
candidates = [fib_a, fib_b]
distances = [abs(close - lv) for lv in candidates]
best_dist = min(distances)
best_lv = candidates[distances.index(best_dist)]
```

### 3. Confluence & filter

```python
# Fib confluence 条件
fib_confluence = (rng > 2 * atr14) and (best_dist <= 0.35 * atr14)

# ADX chop band (上限追加が V3 の改善の柱)
adx_ok = 20.0 <= adx <= 30.0

base_ok = fib_confluence and adx_ok
```

### 4. Entry direction = impulse direction (Classical MR+Follow combined)

```python
if base_ok and is_up_impulse:
    signal = "BUY"
    tp = entry + atr7 * 2.0
    sl = entry - atr7 * 1.0
elif base_ok and is_down_impulse:
    signal = "SELL"
    tp = entry - atr7 * 2.0
    sl = entry + atr7 * 1.0
else:
    return None
```

**EMA filter は撤廃**。TV BT で impulse-only (EMA フィルタなし) が最良だった (combined
PF 1.194 vs EMA filter ありの 1.225 だが N が 128 まで激減で per-trade EV ほぼ同等、
N 多い方を採用)。

### 5. TP/SL (既存と同じ)

- atr7 = ATR(7) (既存 ctx.atr7 を利用)
- BUY: tp = entry + atr7 × 2.0, sl = entry - atr7 × 1.0
- SELL: tp = entry - atr7 × 2.0, sl = entry + atr7 × 1.0
- shift_tp_inside (round number 回避): 既存 legacy と同じく適用
- round_number_boost (entry が round 近傍なら score +0.3): 既存と同様

### 6. entry_type

- 既存と同じ `sr_fib_confluence` を使う (oanda_audit etc の戦略識別維持)
- OB retest path は V3 では使わない (純粋 fib only)

### 7. Dedup

既存 V2 と同じ `_v3_seen_signal_keys: set` を追加し、`reset_dedup_state` で V2 と V3
両方をクリア。dedup key 形式は V2 を踏襲:

```python
dedup_key = (
    ctx.symbol.upper().replace("=X", "").replace("/", "").replace("_", ""),
    self.name,
    signal,
    str(signal_bar_time),
    "fib_classical_v3",
)
```

## Files to modify

### `strategies/daytrade/sr_fib_confluence.py`

1. クラス内に `_v3_seen_signal_keys: set = set()` を追加
2. `reset_dedup_state` を V3 set もクリアするよう更新:
   ```python
   @classmethod
   def reset_dedup_state(cls):
       cls._v2_seen_signal_keys.clear()
       cls._v3_seen_signal_keys.clear()
   ```
3. `_redesign_v3_enabled` メソッド追加:
   ```python
   def _redesign_v3_enabled(self) -> bool:
       return os.environ.get("SR_FIB_CONFLUENCE_REDESIGN_V3") == "1"
   ```
4. `evaluate` メソッドの分岐を更新 (V3 を V2 より先に判定):
   ```python
   def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
       if self._redesign_v3_enabled():
           return self._evaluate_redesign_v3(ctx)
       if self._redesign_v2_enabled():
           return self._evaluate_redesign_v2(ctx)
       return self._evaluate_legacy(ctx)
   ```
5. `_evaluate_redesign_v3` 実装 (上記仕様準拠)。signal_df は backtest_mode の有無で
   `df.iloc[:-1]` 処理を v2 と同じパターンで適用 (closed bar 限定)

### `tools/sr_fib_confluence_redesign_v3_bt.py` (新規)

既存 `tools/sr_fib_confluence_shadow_bt.py` をテンプレに、以下のみ差分:

- `FLAG = "SR_FIB_CONFLUENCE_REDESIGN_V3"`
- `SHADOW_PROMOTE_FLAG = "SR_FIB_CONFLUENCE_REDESIGN_V3_SHADOW_PROMOTE"`
- `OUTFILE = ROOT / "bt-results" / "sr_fib_confluence-redesign-v3-2026-06-03.json"`
- `variant = "classical_mr_follow_v3"`
- `TARGETS` は `[("EUR_USD", "EURUSD=X")]` のみ (env override も尊重)
- `LOOKBACK_DAYS = 365`、`MINIMUM_DAYS = 365`、`INTERVAL = "15m"`
- `_criteria` は v2.1 catastrophic check のみ (PnL sign preserved)。PF / Wilson_lo /
  N drop は warn-only:
  ```python
  def _criteria(current, proposed):
      if proposed["N"] < 20:
          return {"verdict": "INSUFFICIENT_BT_EVIDENCE", ...,
                  "shadow_promote_recommendation": "RECOMMEND_SHADOW"}
      pnl_sign_preserved = not (current["PnL"] > 0 and proposed["PnL"] < 0)
      verdict = "PASS" if pnl_sign_preserved else "REJECT"
      return {"pnl_sign_preserved": pnl_sign_preserved,
              "catastrophic_check": pnl_sign_preserved,
              "sanity_floor": "REMOVED_IN_V2_1",
              "verdict": verdict,
              "shadow_promote_recommendation": "RECOMMEND_SHADOW" if verdict == "PASS" else "REJECT"}
  ```

A/B:
- `proposed=True` → `SR_FIB_CONFLUENCE_REDESIGN_V3=1`, `SR_FIB_CONFLUENCE_REDESIGN_V2=0`
- `proposed=False` (current/legacy) → 両方 0

`_compute_sr_fib_only_signal` は v2 BT のものを再利用 (SrFibConfluence().evaluate() を
呼び出すので、内部で V3 enabled なら V3 path に行く)。

### `data/cache/massive/EUR_USD_15m.parquet`

存在確認のみ。なければ BT は `BLOCKED_DATA` で early return (v2 BT と同じ挙動)。

## BT 実行

```bash
cd /Users/jg-n-012/test/fx-ai-trader
python3 tools/sr_fib_confluence_redesign_v3_bt.py
```

期待出力:
- `bt-results/sr_fib_confluence-redesign-v3-2026-06-03.json`
- stdout 最後の `Saved: ...` と `Overall: PASS|REJECT|INSUFFICIENT_BT_EVIDENCE|BLOCKED_DATA`

## Acceptance criteria (v2.1 catastrophic check のみ)

- proposed N >= 20
- pnl_sign_preserved = NOT (current.PnL > 0 AND proposed.PnL < 0)
- proposed.verdict in {PASS, INSUFFICIENT_BT_EVIDENCE}
- 上記すべて満たせば task PASS

**Codex BT 結果が TV と ±20% 以内なら成功と判定** (data source 差・signal pricing 差・
ATR 系列差で完全一致不能、近似一致で OK)。

期待値 (TV から推定):
- proposed (V3): PF ~ 1.10-1.30, WR ~ 35-40%, N ~ 400-600, PnL > 0
- current (legacy): PF ~ 0.95-1.05, WR ~ 30-35%, N ~ 500-700, PnL ~ 0 or 弱負

## Self-review checklist

- [ ] `_evaluate_redesign_v3` で **impulse-aware** classical fib になっている (LONG は
      up-impulse + fib、SHORT は down-impulse + fib)
- [ ] EMA filter (ema_score 閾値) は V3 path で **使っていない**
- [ ] ADX 範囲は **[20, 30] 両端含む** (>= AND <=)
- [ ] Fib level は **38.2 と 61.8 の 2 つのみ** (50% mid は除外)
- [ ] MASSIVE cache (BT_REQUIRE_MASSIVE_CACHE=1) を強制し Yahoo fallback 禁止
- [ ] V3 flag OFF で `_evaluate_legacy` 出力が変わらない (regression guard)
- [ ] V2 flag と V3 flag を両方 ON にしても V3 が優先される (evaluate メソッドの順序)
- [ ] `reset_dedup_state` で V2 と V3 両方の set をクリア
- [ ] BT 出力 JSON が v2 BT と同 schema
- [ ] `_criteria` が v2.1 (catastrophic check only) で sanity_floor を含めない
- [ ] git commit + push 到達 ([feedback_codex_stash_leak] 対策、stash 経由禁止)

## Tests

新規ユニットテストは必須ではないが、既存 `tests/strategies/test_sr_fib_confluence.py`
(存在すれば) を壊さないこと。

最低限の手動確認:
```python
# Python REPL
import os
from strategies.daytrade.sr_fib_confluence import SrFibConfluence

s = SrFibConfluence()

os.environ["SR_FIB_CONFLUENCE_REDESIGN_V3"] = "0"
os.environ["SR_FIB_CONFLUENCE_REDESIGN_V2"] = "0"
# → _evaluate_legacy が呼ばれることを確認 (内部分岐 trace)

os.environ["SR_FIB_CONFLUENCE_REDESIGN_V3"] = "1"
# → _evaluate_redesign_v3 が呼ばれることを確認

s.reset_dedup_state()
# → _v2_seen_signal_keys と _v3_seen_signal_keys 両方が空になることを確認
```

## Deliverables

1. `strategies/daytrade/sr_fib_confluence.py` を編集 (上記 spec)
2. `tools/sr_fib_confluence_redesign_v3_bt.py` を新規作成
3. `bt-results/sr_fib_confluence-redesign-v3-2026-06-03.json` を生成 (BT 実行結果)
4. `final.md` (タスク run dir 直下) に:
   - TV 数値 vs Codex BT 数値の差分テーブル (N / WR / PF / PnL)
   - verdict (PASS / INSUFFICIENT_BT_EVIDENCE / REJECT / BLOCKED_DATA)
   - shadow ramp plan (次の shadow 投入手順、N≥30 蓄積目標、別タスク化)
   - self-review checklist の結果
5. **git commit + push 必須** ([feedback_codex_stash_leak])

## Out of scope (この task で **やらない** こと)

- multi-pair BT (今回 EUR_USD のみ。GBP_USD / USD_JPY / GBP_JPY 等は別タスクで)
- Live promotion / OANDA bridge 設定変更
- SHORT only / hybrid variant の prod 実装 (combined だけ)
- WFO の自動化
- shadow worker への V3 flag 配備 (今回は BT 結果確認まで)

## References

- TV Pine v6 source: 直近 session の編集履歴 (slot `USER;FMxhuESzrit5BbljIYds3injwD7sVSmp`)
- TV BT 結果 screenshots: `/Users/jg-n-012/test/tradingview-mcp/screenshots/tv_strategy_tester_2026-06-03T*.png`
- 既存 V2 spec: `tools/sr_fib_confluence_shadow_bt.py` (variant=structured_layer3_fib_ob_gate_v2)
- cell_negative_edge_audit 結果 (2026-06-03 morning shadow 30d): live_ng_cells テーブル
  に entry_type='sr_fib_confluence' で 37 NG cell 持続
- memory: `[feedback_shadow_first_quant_architecture]`、`[feedback_bt_must_use_massive]`、
  `[feedback_ma_filter_breaks_mr]`、`[feedback_codex_stash_leak]`、
  `[feedback_size_lever_beats_skip_filter]`
