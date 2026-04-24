# ELITE Freeing Patch + vwap_mr 緊急トリップ (2026-04-24)

## 背景

### 症状
Live post-cutoff 2026-04-08〜2026-04-23 (16日) で ELITE_LIVE 3 戦略の fire が機能不全:

| Strategy | Total (365d API) | Live (is_shadow=0) | Shadow | Shadow Rate |
|----------|------------------|---------------------|--------|-------------|
| gbp_deep_pullback | 500 (limit) | 12 | 488 | 97.6% |
| session_time_bias | 500 (limit) | 12 | 488 | 97.6% |
| trendline_sweep | 500 (limit) | 12 | 488 | 97.6% |

BT 365d は全て STRONG α 確認済 (EV +0.22 〜 +1.06) にも関わらず、**Live は 97.6% Shadow 化**
されており OANDA 実行に到達していない. ELITE は本来 `_SHADOW_MODE=True` でも
Phase0 gate を免除される設計だったが、新設された 2 gate でその免除が抜け落ちていた.

### 並行症状: vwap_mean_reversion の濃毒化
Live post-cutoff:
- N=8 → N=10 (+2 trade)
- PnL: +36.9 → -4.6 → **-17.5pip** → **-47.7pip** (3日で急転落)
- 平均 -4.77pip/trade (avg_loss >> avg_win)
- BT EV=+1.025 (GBPJPY 15m) / +0.672 (EURJPY 15m) との乖離が ~5pip/trade

## 根本原因 — ELITE 3 戦略の Shadow 降格

| Location | Gate | ELITE 免除 (patch 前) |
|----------|------|----------------------|
| `demo_trader.py:3435` | MTF A/B gate (A 群 conflict で shadow 降格) | ❌ なし |
| `demo_trader.py:4284` | Q4 gate (Kelly<0 AND Wilson_hi<BEV AND N>=15) | ❌ なし |
| `demo_trader.py:4294` | `_SHADOW_MODE` Phase0 gate | ✅ あり (ELITE/SENTINEL/PRIME 免除済み) |

3つの gate のうち Phase0 だけが ELITE 免除を持ち、他2つで **MTF hash A/B の半分 + Q4
発動時に shadow 化** → 結果的に 97.6% Shadow 化. これは ELITE_LIVE pre-reg の趣旨
(BT STRONG 確認済み戦略は LIVE 送信維持) に反する **実装漏れ = バグ**.

## 適用パッチ

### Patch A — MTF gate ELITE 免除 (`demo_trader.py:3435`)

```python
# 変更前
if _gate_group == "mtf_gated":
    if _mtf_alignment == "conflict":
        if not _is_shadow:
            _is_shadow = True
            ...

# 変更後
if _gate_group == "mtf_gated" and entry_type not in self._ELITE_LIVE:
    if _mtf_alignment == "conflict":
        ...
elif _gate_group == "mtf_gated" and entry_type in self._ELITE_LIVE:
    _mtf_gate_action = "elite_exempt"
```

### Patch B — Q4 gate ELITE 免除 (`demo_trader.py:4284`)

```python
# 変更前
if _q4_should_shadow(entry_type, _q4_conf_val):
    ...

# 変更後
if entry_type not in self._ELITE_LIVE and _q4_should_shadow(entry_type, _q4_conf_val):
    ...
```

### Patch C — vwap_mr OANDA 緊急トリップ (`demo_trader.py:4266+`)

```python
_VWAP_MR_OANDA_TRIP = _os.environ.get("VWAP_MR_OANDA_TRIP", "1") == "1"
if _VWAP_MR_OANDA_TRIP and entry_type == "vwap_mean_reversion":
    if not _is_shadow:
        _is_shadow = True
        _is_promoted = False
        _shadow_at_open = True
        self._add_log("[EMERGENCY_TRIP] vwap_mean_reversion OANDA 送信停止 ...")
```

- Kill-switch は env var 制御 (`VWAP_MR_OANDA_TRIP=0` で即時解除可能)
- Shadow 経路 (DB 記録のみ) は継続 → 統計蓄積に支障なし
- 解除条件: v2 sublimation logic が Shadow で N≥20 正 EV を実証

### Patch D — vwap_mr v2 sublimation filters (`app.py:3175` DT + `:8267` Scalp)

既存 2σ signal の後段に 4つの追加 gate を AND 結合で挿入 (env var `VWAP_MR_V2=1`):

1. **VWAP slope flat** — 直近 10 bar の slope を σ で正規化し `|norm|>0.3` で reject
   (trend 時は MR が機能しない)
2. **ADX hard block** — `ADX>=22` で MR を完全停止 (従来は confidence penalty のみ)
3. **Active hours** — UTC 7-20 のみ (Asia 深夜 / NY 引け後の流動性枯渇帯を除外)
4. **Reclaim confirmation** — 直前バーが σ 端に対して中心寄りであること (底打ち/天井打ち確認)

既存 HTF Hard Block / v2 anti-trend penalty / pair boost は温存 → ロールバック容易.

## 想定される効果

### ELITE 3 戦略
- MTF hash A 群 × conflict: 従来 100% shadow → **0% shadow** (exempt)
- Q4 gate 発動時: 従来 100% shadow → **0% shadow** (exempt)
- 複合して shadow 率 97.6% → 数% (純粋な pair gate と conf<30 etc. のみ) への改善期待
- OANDA 送信 N 期待値: 12 → 数十 (Phase0 gate では fire だが MTF/Q4 で捕捉されていた分)

### vwap_mr
- OANDA 送信: **即時ゼロ** (Live PnL の追加悪化停止)
- DB shadow 記録は継続 → v2 logic の Shadow 検証 N 蓄積
- v2 filter 通過率は Shadow 観測で測定 (想定 20-40% 程度)

## リスク / 観測ポイント

1. **ELITE 3 戦略が BT と同等の +EV を Live で再現するか**
   - BT 365d: gbp_deep_pullback +1.06 / trendline_sweep +0.60 / session_time_bias +0.58 等
   - Live で同等なら月利目標に大きく貢献、乖離したら BT-Live divergence 深掘り
2. **vwap_mr の v2 通過 signal が Shadow で正 EV か**
   - 正 EV で N≥20 確認 → env var `VWAP_MR_OANDA_TRIP=0` で解除検討
   - 負 EV 継続 → v2 logic 自体を reject
3. **Emergency trip は Shadow 記録を維持するか**
   - `[EMERGENCY_TRIP]` log が Render で出力されること、`is_shadow=1` で DB 記録されることを
     デプロイ後に curl `/api/demo/logs` / `/api/demo/trades` で検証

## 検証コマンド (デプロイ後)

```bash
# Emergency trip log 確認
curl -s https://fx-ai-trader.onrender.com/api/demo/logs | jq '.logs[] | select(.message | contains("EMERGENCY_TRIP"))'

# MTF/Q4 gate elite_exempt action 確認
curl -s https://fx-ai-trader.onrender.com/api/demo/logs | jq '.logs[] | select(.message | contains("MTF_GATE"))'

# ELITE 3 戦略の live (is_shadow=0) trade 発生確認
curl -s 'https://fx-ai-trader.onrender.com/api/demo/trades?limit=200&date_from=2026-04-24' | \
  jq '[.[] | select(.entry_type == "session_time_bias" or .entry_type == "trendline_sweep" or .entry_type == "gbp_deep_pullback")] | group_by(.entry_type) | map({type: .[0].entry_type, n: length, live: [.[] | select(.is_shadow == 0)] | length})'
```

## 参照

- [[phase4c-mtf-regime-result-2026-04-24]] (MTF signal A の null result)
- [[phase4d-v6-cell-edge-test-result-2026-04-24]] (cell-level edge null)
- [[vwap-mean-reversion]] (本戦略 KB)
- [[roadmap-v2.1]] (DT幹 ELITE 3 戦略の位置づけ)
- [[phase2a-deploy-status-2026-04-23]] (MTF gate 稼働記録)
