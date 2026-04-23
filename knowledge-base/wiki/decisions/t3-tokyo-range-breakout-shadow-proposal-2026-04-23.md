# T3 Tokyo Range Breakout — Shadow Registration Proposal (2026-04-23)

**Status**: PROPOSAL (未実装). ユーザ承認後に実装フェーズへ。
**Validation**: 🟢 365d BT + Walk-Forward (IS/OOS 158-159d) で 4/5 ペア STABLE_EDGE 確定。
**Reference**:
- `knowledge-base/raw/bt-results/tokyo-range-breakout-2026-04-23.md` (raw BT)
- `knowledge-base/raw/bt-results/tokyo-range-breakout-wfa-2026-04-23.md` (WFA)
- `knowledge-base/wiki/sessions/quant-edge-scan-2026-04-23.md` (session)

---

## 1. エッジの定義 (既検証)

**Trigger条件** (daily, 1 event/day/pair):
```
Tokyo range = [max(H), min(L)] over UTC 0-7
IF London_open_high > Tokyo_range.max AND London_open_low >= Tokyo_range.min over UTC 7-9:
    entry = LONG at London open first close
    signal_name = "tokyo_range_breakout_up"
    hold = 4h (exit at UTC 13)
```

**確認済パフォーマンス (365d, per pair)**:
| Pair | N | OOS mean | OOS WR | Friction RT | Net EV |
|------|---:|---------:|-------:|-----------:|-------:|
| USD_JPY | 51 | +17.62 | 74.5% | 2.14p | **+15.48p** |
| GBP_JPY | 57 | +16.76 | 66.7% | 2.50p* | +14.26p |
| EUR_JPY | 52 | +12.55 | 65.4% | 2.50p | +10.05p |
| GBP_USD | 51 | +9.63 | 64.7% | 4.53p | +5.10p |

*GBP_JPY friction は EUR_JPY 同等と仮定 (未計測). **要個別測定**。

---

## 2. 実装設計 (提案)

### 2.1 新規戦略として実装

**ファイル構成**:
```
modules/signals/tokyo_range_breakout.py  (new)
  - compute_tokyo_range(df) -> (high, low)
  - signal_tokyo_range_breakout_up(df, pair) -> sig dict
```

**signal dict** (本番 signal function 規約):
```python
{
    "entry_type": "tokyo_range_breakout_up",
    "signal": "BUY",  # UP only (DOWN は NOISY_BUT_ALIVE なので保留)
    "entry_price": london_open_close,
    "tp": entry + 20 * pip_mult(pair),   # +20 pip (mean +17 + buffer)
    "sl": entry - 15 * pip_mult(pair),   # -15 pip (std 39 なので tight は避ける)
    "hold_max_minutes": 240,             # 4h cap
    "reasons": ["Tokyo range breakout UP (UTC7-9)", f"range={range_pip:.1f}p"],
    "confidence": min(0.95, range_pip / 30),
}
```

**呼び出しタイミング**: UTC 7-9 window の最初の 15m bar close で評価。
既存 daytrade_engine は 15m bar 毎に全戦略をチェックするため、時間 gate のみ必要。

### 2.2 Shadow 登録 (PHASE0_SHADOW)

CLAUDE.md 判断プロトコルに従い、Live の前に Shadow N≥30 蓄積:

1. 新 entry_type を `_FORCE_DEMOTED` に追加 → 自動的に PHASE0_SHADOW 扱い
   - → トレード試行は log されるが OANDA 発注しない
   - → N が 30 到達した時点で独立監査

2. Shadow 蓄積中に確認すべき指標:
   - Live N=30 時点の mean pip, WR%
   - BT との divergence (`wiki/analyses/bt-live-divergence.md` の 6 bias 確認)
   - friction 実測値 (spread + slippage)
   - NONE day (breakout しなかった日) の比率 — BT で ~30% だが live も一致するか

3. Promotion gate:
   - Live N≥30 & mean ≥ BT × 0.5 & WR ≥ BT × 0.9 → Kelly Half 昇格候補
   - Bootstrap EV CI lower > 0 必須 (Phase 1 から適用)

### 2.3 対象ペア (段階的)

**Phase 0 (Shadow)**: USD_JPY のみ (最強シグナル、friction 最小)
**Phase 1**: + GBP_JPY, EUR_JPY (N≥30 達成後、Phase 0 成績次第)
**Phase 2**: + GBP_USD (Phase 1 成績次第、friction 高で慎重)

EUR_USD は NOISY_BUT_ALIVE のため Shadow 登録しない。

---

## 3. 実装手順 (ユーザ承認後)

### Step 1: Signal function
- `modules/signals/tokyo_range_breakout.py` 新規作成
- Unit test: `tests/test_tokyo_range_breakout.py`

### Step 2: Registration
- `daytrade_engine.py` の QUALIFIED_TYPES に `"tokyo_range_breakout_up"` 追加
- `daytrade_engine.py` の `_FORCE_DEMOTED` に追加 (Shadow 扱い)
- `wiki/strategies/tokyo-range-breakout.md` 新規作成 (pre-commit 要件)

### Step 3: Integration
- `app.py` or `demo_trader.py` で 15m loop 時に signal 呼び出し
- UTC hour gate: `7 <= h < 9` のみ fire

### Step 4: Monitor
- `tools/t3_shadow_progress.py` (新規): Live Shadow N 追跡
- 週次 audit で BT vs Live divergence を計測

---

## 4. リスク & 否定仮説

**Risk 1: NONE day (breakout なし) の判定が本番と BT で異なる**
- 対策: BT で NONE day の log も出力して比較可能にする

**Risk 2: 4h 持ち時間中に指標発表**
- 対策: UTC 12:30 (US 指標) と 14:00 (欧州 close 近辺) の前に exit を検討
- 初期は no-gate で net EV を観察

**Risk 3: weekend effect, month-end rebalancing**
- 対策: 金曜 (UTC 7) の signal は week-overhang あり → 初期除外を検討
- Shadow 蓄積期に金/月/通常日で mean pip 差を測定

**Risk 4: Tokyo range が極端に狭い日 (< 10 pip)**
- 対策: minimum range filter: `range_pip >= 15` のみ fire を試す
- BT で現状分布を確認 (別タスク)

---

## 5. 承認要否

以下は**コード変更**でありユーザ承認要:
- Step 1-3 全て (modules/, daytrade_engine.py, app.py)

以下は**分析のみ**で即座に可能:
- Tokyo range 分布確認 (raw BT)
- weekend/month-end subgroup 分析
- friction 個別測定 (per pair)

---

## 6. 現時点の判断

- T3 は**最強の新規エッジ候補** (Bonferroni-safe, WFA-passed, 4 pair)
- しかし**未実装のため自動運用には載っていない**
- 次セッションで: (a) ユーザ承認, (b) Step 1-3 実装, (c) Shadow 観察開始

**リスク許容度**: 実装コスト 1-2h, Shadow N=30 到達目安 30 営業日 (1.5 months).
