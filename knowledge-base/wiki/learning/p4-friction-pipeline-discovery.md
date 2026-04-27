# P4 Production-Side Smoke Test 重大発見

**Session**: curried-ritchie (Wave 2 Day 5 R1+R4+R6 後の Phase 3 BT pre-launch readiness)
**Date**: 2026-04-27 14:50 JST
**Status**: 🚨 **Critical finding — Phase 3 BT design needs revision**
**位置付け**: P4 smoke test の結果文書、LOCK 外 supplementary

---

## 0. Executive Summary (Quant TL;DR)

**`tools/phase3_bt.py:patch_friction_model()` の Mode A/B 切替は、実際の BT pipeline では機能しない**。

- `app.run_daytrade_backtest()` は friction を `_bt_spread()` (app.py:4614, hour-based hardcoded table) から取得
- `modules/friction_model_v2._SESSION_MULTIPLIER` は **Live trading では使用されるが、BT では使用されていない**
- → Phase 3 BT で Mode A vs Mode B を比較しても **同一結果**になり、friction sensitivity 検証は技術的に成立しない

**P4 smoke test が正しく検出したため、28 BT runs × 3h = 84h の無駄を事前に回避**。Phase 3 BT 着手前の必須 pre-flight check の真価が発揮された。

---

## 1. Smoke Test 実行結果 (証拠)

### 1.1 実行 command

```bash
cd /Users/jg-n-012/test/fx-ai-trader
python3 tools/phase3_friction_e2e_smoke.py --lookback 60 --symbol GBPUSD=X --strategy gbp_deep_pullback
```

### 1.2 結果

```
Status: FAIL ❌
Symbol: GBPUSD=X, lookback: 60d
Strategy filter: gbp_deep_pullback
All BT trades: A=371 / B=371
Filtered trades: A=16 / B=16

Mode A (status_quo):  EV=+0.3379pip WR=0.625 N=16 friction_mean=0.132pip
Mode B (calibrated):  EV=+0.3379pip WR=0.625 N=16 friction_mean=0.132pip
EV diff: +0.0000pip (friction diff: +0.000pip)
```

### 1.3 観察

- **trade count 同一** (A=371, B=371): entry signal 生成が friction-independent (期待通り)
- **filtered trades 同一** (gbp_deep_pullback A=16, B=16, WR=0.625 同一): outcome も同一
- **EV 同一** (+0.3379 pip): friction 適用後の pnl が両 mode で完全一致
- **friction_mean 同一** (0.132 pip): exit_friction_m が両 mode で identical

→ Mode A と Mode B で、friction 値が**ビット単位で同一**。`_SESSION_MULTIPLIER` 上書きが BT pipeline に伝播していない。

---

## 2. Root Cause Analysis

### 2.1 BT pipeline の friction 取得経路

`app.py:5488` (compute_daytrade_signal の BT 経路):

```python
_spread = _bt_spread(bar_time, symbol)
# Phase A: 決済時摩擦 (exit friction = half spread + slippage)
_exit_friction = _spread / 2 + _slip_sc
_exit_friction_m = _exit_friction / max(atr7, 1e-6)
```

### 2.2 `_bt_spread()` (app.py:4614)

```python
def _bt_spread(bar_time, symbol: str = "USDJPY=X") -> float:
    """BT用 時間帯変動スプレッドモデル v2 (ペア別実測値ベース)"""
    h = bar_time.hour
    _is_jpy = "JPY" in symbol.upper()
    _is_gbp_usd = "GBPUSD" in symbol.upper()
    # ... hour-based hardcoded table per pair
    if _is_gbp_usd:
        if h < 2:     return 0.00020  # 2.0pip
        elif h < 7:   return 0.00015  # 1.5pip
        elif h < 16:  return 0.00010  # 1.0pip (最狭)
        # ...
```

→ **Hour-based hardcoded spread table**、`_SESSION_MULTIPLIER` を参照しない。

### 2.3 `friction_model_v2` の実用域

`modules/friction_model_v2.friction_for()` は:
- `_SESSION_MULTIPLIER` (`patch_friction_model` で上書き対象) を使用
- `live_trader` / `demo_trader` 等の **Live execution path** で参照される
- **BT path では使用されていない** (BT は `_bt_spread()` を使う)

### 2.4 結論: 構造的乖離

- **Live**: `friction_model_v2._SESSION_MULTIPLIER` で friction adjusted
- **BT**: `_bt_spread()` の hardcoded table で friction adjusted
- → Mode A vs Mode B 比較は Live 側でのみ意味あり、BT 側では無効

これは CLAUDE.md `wiki/analyses/bt-live-divergence.md` で指摘されている **6 BT 楽観バイアス因子 #2 「固定 Spread モデル」**の具体例。BT と Live で別 friction モデルが動作している事実を、本 P4 smoke test が初めて end-to-end で実証した。

---

## 3. Phase 3 BT design への影響

### 3.1 LOCK 文書 (`phase3-bt-pre-reg-lock.md`) の認識

§4 "Friction Model Selection (Mode A vs Mode B)" は LOCK terms に含まれる:
> 全 7 戦略を **両 Mode で BT 実行**、Live N≥30 観測値と AIC/BIC 比較で best-fit Mode 採用

LOCK 時点では `_SESSION_MULTIPLIER` 上書きが BT に伝播する想定だった。本 P4 で**前提が崩れた**ことが判明。

### 3.2 LOCK terms 不変 vs 実装可能性

HARKing 防止規律で LOCK terms は不変。しかし**現コードでは LOCK 通りの BT は実行不可**。

選択肢:
- **Option X**: LOCK 通り Mode A/B BT を実行 → 両者同一結果で意味なし、Phase 3 BT 全体が技術的失敗
- **Option Y**: BT pipeline を改修 (`_bt_spread()` を `friction_for()` 呼び出しに置換 or session multiplier override) → LOCK terms は不変だが実装が LOCK の意図に追いついた状態
- **Option Z**: 新 Pre-reg LOCK を発行、Mode A/B 比較を諦め別 dimensions (e.g., Anchored vs Rolling のみ) に focus

**Quant 推奨 Option Y**: LOCK terms は仕様 (intent) であり、コード改修で実装合致させるのは HARKing ではない。改修は LOCK §4 の "全 7 戦略を両 Mode で BT 実行" 要件を満たすためのプリレキジット。ただし改修自体が new Pre-reg LOCK 案件かどうかは慎重判断。

### 3.3 推奨改修案 (実装は別 session)

`app.py:_bt_spread()` を session multiplier-aware に変更:

```python
def _bt_spread(bar_time, symbol="USDJPY=X"):
    base_spread = ... # 現状の hour-based table
    # ── R6 Phase 3 BT compatibility: session multiplier 適用 (2026-04-27 補正) ──
    try:
        from modules.friction_model_v2 import _SESSION_MULTIPLIER
        sess = _classify_session(bar_time)  # "Tokyo" / "London" / "NY" / "overlap_LN"
        mult = _SESSION_MULTIPLIER.get(sess, _SESSION_MULTIPLIER.get("default", 1.0))
        return base_spread * mult
    except Exception:
        return base_spread  # fail-open
```

これで `patch_friction_model()` が BT に伝播するようになる。

### 3.4 Phase 3 BT 着手 timing への影響

`phase3-bt-supplementary-2026-04-27.md` で Phase 3 BT 着手は ζ (+14d, 2026-05-11) と reference 提示済。本 P4 finding により:
- (a) `_bt_spread()` 改修が ζ までに完了するなら Phase 3 BT 着手 timing 維持可能
- (b) 改修が間に合わない場合、Phase 3 BT 着手は更に延期 (Mode A/B 比較放棄 or 改修待ち)

改修 estimate: 2-4h (修正 + tests + smoke 再実行)。間に合う見込み。

---

## 4. Quant Rigor 的な意義

### 4.1 P4 smoke test の真の価値

事前 power calc / Bonferroni 補正設計で完璧と思えた Pre-reg LOCK でも、**実装層の bug** で全体が無効化される事例。Quant rigor では:

1. **設計の数学的正しさ** (Bonferroni K, WFA dates, 採用基準): 既に R1 で固定済
2. **実装の technical correctness** (friction patch propagation): 本 P4 で検証
3. **両者の cross-check**: Phase 3 BT 着手前に必須

R6 (`verify_friction_patch_works()` で `friction_for()` 単体検証) では P4 を捉えられなかった理由は:
- R6 は `friction_for()` 関数の input/output を直接検証 → 関数は正しく動作
- BT は `friction_for()` を呼ばずに `_bt_spread()` を呼ぶ → R6 verify でも安全に通過
- → **end-to-end smoke test (P4) が必要だった**

### 4.2 教訓 (lesson candidate)

`wiki/lessons/lesson-bt-friction-pipeline-discovery-2026-04-27.md` 候補:

> BT と Live で friction model が分離しているシステムでは、設計上の "Mode A/B 比較" を実装するには両 path で同 model を使う必要がある。設計と実装の乖離を検出するには **end-to-end smoke test** が必須で、関数単体検証 (`verify_friction_patch_works()`) では不十分。Phase 3 BT 着手前の P4 smoke は今回 84h の無駄を回避した。

---

## 5. 残課題 / Action Items

### 5.1 即時 (本 session で実施)

- [x] P4 smoke test 実行 + finding 文書化
- [ ] P3 coordination doc 作成 (本 finding を反映、Mode A/B 比較を保留可能性として明記)
- [ ] supplementary doc に P4 finding section 追加
- [ ] commit + push (LOCK 不変、supplementary 文書のみ修正)

### 5.2 別 session

- [ ] **`_bt_spread()` 改修 PR** (session multiplier-aware): 2-4h
- [ ] 改修後に P4 smoke test 再実行で PASS 確認
- [ ] Phase 3 BT 着手 (ζ +14d) までに完了

### 5.3 Phase 3 BT 着手 gating 状況更新

| Gate | Status | 備考 |
|------|--------|------|
| Pre-reg LOCK formal design | CLOSED ✅ | LOCK terms 不変 |
| **R6 friction_for() 単体検証** | **CLOSED ✅** | passed |
| **P4 BT pipeline end-to-end** | **🚨 FAIL** | `_bt_spread()` 改修必要 |
| Phase 3 BT script Phase 1 | CLOSED ✅ | 470 tests pass |
| Wave 1+2 effect 計測 | 計測中 | β +12h, γ +24h, ζ +14d |
| Phase 3 BT 着手 | **延期** | `_bt_spread()` 改修完了まで |

---

## 6. References

- `tools/phase3_friction_e2e_smoke.py` (本 finding 検出 script)
- `app.py:4614 _bt_spread()` (BT friction source)
- `app.py:5488 _spread = _bt_spread()` (BT pnl 計算)
- `modules/friction_model_v2._SESSION_MULTIPLIER` (Live friction source)
- `tools/phase3_bt.py:patch_friction_model()` (上書き対象、現 BT に届かず)
- `phase3-bt-pre-reg-lock.md` §4 Friction Model Selection (LOCK terms 不変)
- `phase3-bt-supplementary-2026-04-27.md` (本 finding を §6 として追加予定)
- CLAUDE.md `wiki/analyses/bt-live-divergence.md` 6 因子 #2 「固定 Spread モデル」
