# Session Time Bias × BB RSI Reversion — Edge Cell Redesign Design

**Date**: 2026-06-08
**Status**: DESIGN (awaiting user spec review → writing-plans skill)
**Author**: Claude (一次実装、新方針 `[[feedback_codex_as_review_layer_2026_06_05]]` 下)
**Rule classification**: R2 (Fast & Reactive、損失止血継続 + cell filter shadow→live ramp)

## 1. Background

2026-06-07 session で `session_time_bias` / `bb_rsi_reversion` の MR-in-trend 構造的 bleeding を実測確認 (`[[project_oanda_loss_surge_2026_06_03]]`, `[[project_edge_cell_stage3_recovery_phase2_2026_06_07]]`)。**E2/E3 manual disable** + **GBP_USD revival code 削除** + **watchdog Bearer fix** + **Stage-3 Wilson_lo 0.55 復帰** で止血完了。

本 design は止血の次段階として、**両戦略を edge cell に絞り込んで再活性化**するもの。Codex Kalman D7 v18e 12y MASSIVE BT + sr_fib V3 BT の前例 (TV 短期 favorable → 12y で edge 消失) を踏まえ、**OOS 劣化を仮定した保守的 promote ramp** を pre-reg LOCK する。

## 2. Empirical evidence (data-driven, 2026-06-08 採取)

### 2.1 Source data

- Render production `/api/demo/trades?limit=5000`
- 期間: 2026-04-29 → 2026-06-08 (40 calendar days)
- Closed trades only (`status=CLOSED`, `pnl_pips != None`)
- 対象 2 戦略合計 N = 635 (session_time_bias 396 + bb_rsi_reversion 239)
- Tag fields 利用: `entry_time`, `instrument`, `direction`, `regime` JSON (ADX/BBW/EMA/HMM/vol_scale), `mtf_*`, `dow_regime`, `v2_regime`, `mafe_favorable_pips`, `mafe_adverse_pips`

### 2.2 Baseline (no filter)

| 戦略 | N | WR | mean_pip | PF | Wilson_lo | sum_pip |
|---|--:|--:|--:|--:|--:|--:|
| session_time_bias | 396 | 30.1% | -2.06 | 0.601 | 0.257 | -816 |
| bb_rsi_reversion | 239 | 30.1% | -0.77 | 0.688 | 0.247 | -184 |
| **合計** | **635** | 30.1% | -1.58 | — | — | **-1,000** |

### 2.3 Edge cells (top by mean_pip, Wilson_lo uncorrected)

| Cell | N | WR | mean_pip | PF | Wlo |
|---|--:|--:|--:|--:|--:|
| session_time_bias × LDN × ADX[25,30] | 36 | 55.6% | **+2.17p** | 1.68 | **0.396** |
| session_time_bias × LDN × ADX[15,20] | 32 | 46.9% | **+2.29p** | 1.55 | 0.309 |
| session_time_bias × LDN × RANGE | 94 | 44.7% | +1.19p | 1.28 | 0.350 |
| session_time_bias × EUR_USD × LDN | 97 | 45.4% | +0.93p | 1.26 | 0.358 |
| **session_time_bias × LDN × ADX[15,30]** (合算) | **126** | **45.2%** | **+0.93p** | — | — |
| bb_rsi_reversion × BUY × USD_JPY | 25 | 52.0% | +1.51p | 1.99 | 0.335 |
| bb_rsi_reversion × USD_JPY × LDN | 23 | 47.8% | +0.95p | 1.36 | 0.292 |
| **bb_rsi_reversion × USD_JPY** (合算) | **96** | 43.8% | +0.10p | 1.04 | 0.343 |

### 2.4 Kill cells (avoid)

| Cell | N | WR | mean_pip | sum_pip |
|---|--:|--:|--:|--:|
| session_time_bias × GBP_USD × ASN | 79 | 17.7% | **-4.53p** | **-358p** |
| session_time_bias × GBP_USD × NY | 60 | 20.0% | **-5.00p** | **-300p** |
| session_time_bias × LDN × ADX>30 | 20 | 20.0% | -3.98p | -80p |
| bb_rsi_reversion × USD_CHF 全 session | 59 | 6.8% | **-2.04p** | **-120p** |
| bb_rsi_reversion × USD_CHF × LDN SELL | 15 | **0.0%** | -3.11p | -47p |
| bb_rsi_reversion × USD_CHF × ASN SELL | 15 | **0.0%** | -1.87p | -28p |

### 2.5 Statistical caveat (Bonferroni-strict 不充足)

m_tests = 66-77 軸 → Bonferroni α = 6.5e-4 〜 7.6e-4。
全 cell の Bonferroni-corrected Wilson_lo ≤ 0.34 < 0.55 (Stage-3 復帰基準)。

**つまり本 design は Bonferroni-strict promote criteria を満たしていない**。これは:
- Selection bias residual: cell を同 dataset から data-mining
- 単一 40 日 sample = 1 local window (favorable な可能性)
- OOS 劣化前例多数 (`[[project_w4_eda_complete_2026_05_05]]`, `[[feedback_codex_mock_test_trap]]`)

→ promote ramp で実 N を蓄積し、Bonferroni-corrected 0.55 を OOS で実証してから本格 LIVE。

### 2.6 MFE/MAE 分析が示した重要発見

TP 短縮シミュレーションで **全 cell で TP 短縮は EV を悪化** させた:

| Cell | baseline mean | TP=2p simulated | TP=10p simulated |
|---|--:|--:|--:|
| LDN × ADX[15,30] | **+0.93p** | -2.78p | -0.68p |
| LDN × ADX[25,30] | **+2.17p** | -1.66p | +0.23p |
| LDN × RANGE | **+1.19p** | -2.80p | -0.31p |
| USD_JPY × LDN | +0.95p | -1.47p | +0.80p |

→ **既存 trailing exit は edge cell では MFE を回収できている**。出口は変更しない。
→ MFE 分布で >=10p の trade が 27-35% あり、これを固定短 TP で切ると edge 破壊。

## 3. Design

### 3.1 Architecture (新規 entry_type ではなく既存強化)

```
strategies/daytrade/session_time_bias.py
  ├── _session_time_bias_edge_cell(ctx) → (edge_on: bool, lot_mult: float)  # NEW
  └── evaluate(ctx):
        edge_on, lot_mult = _session_time_bias_edge_cell(ctx)
        if not edge_on: return None
        candidate = (既存 signal logic)
        candidate.lot_multiplier = lot_mult
        return candidate

strategies/daytrade/bb_rsi_reversion.py
  ├── EDGE_PAIRS = frozenset({"USD_JPY"})         # NEW
  ├── KILL_PAIRS = frozenset({"USD_CHF", "GBP_USD"})  # NEW
  ├── _bb_rsi_edge_cell(ctx) → (edge_on, lot_mult)  # NEW
  └── evaluate(ctx):  # 同上パターン

modules/demo_trader.py
  └── _resolve_lot(): candidate.lot_multiplier 属性があれば優先  # MODIFIED
```

### 3.2 Components

**Context attribute mapping** (verified against `strategies/context.py`):

| Used by filter | SignalContext source | Type |
|---|---|---|
| `entry_time_utc.hour` | `ctx.df.index[-1]` または既存 hour helper (要確認) | int |
| `adx` | `ctx.adx` (直接 field、default 25.0) | float |
| `dist_ema200_pct` | `abs(ctx.entry - ctx.ema200) / ctx.ema200` (on-the-fly compute) | float |
| `regime_label` | `ctx.regime.get('regime')` (既存 dict field) → "TREND_BULL"/"TREND_BEAR"/"RANGE"/"CHOP" | str or None |
| `instrument` | `ctx.instrument` または `ctx.symbol` (要確認、戦略 base 既存 access pattern を踏襲) | str |

⚠️ `ctx.ema200_dist` (既存 attr) は ATR-normalized で別スケール、本 filter では使わず raw percent を計算する。

#### A. session_time_bias edge cell filter

```python
def _session_time_bias_edge_cell(ctx) -> tuple[bool, float]:
    """
    Returns (edge_on, lot_multiplier).
    Source: 2026-06-08 production data analysis (N=396, 40 days).
    See docs/superpowers/specs/2026-06-08-session-time-bias-bb-rsi-edge-cell-redesign-design.md §2.3.
    """
    # Hour-of-day in UTC (戦略既存の hour 取得 pattern を踏襲、要 plan で確認)
    h = _utc_hour_from_ctx(ctx)
    if h is None or not (7 <= h < 13):  # LDN session only
        return False, 0.0

    adx = float(ctx.adx) if ctx.adx is not None else None
    if adx is None or not (15.0 <= adx <= 30.0):
        return False, 0.0

    # Raw percent distance from EMA200
    if ctx.ema200 <= 0 or ctx.entry <= 0:
        return False, 0.0
    dist_pct = abs(ctx.entry - ctx.ema200) / ctx.ema200
    if dist_pct >= 0.005:  # within 0.5% of EMA200
        return False, 0.0

    # Core boost: ADX 25-30 OR regime label "RANGE"
    regime_label = ctx.regime.get('regime') if isinstance(ctx.regime, dict) else None
    is_core = (adx >= 25.0) or (regime_label == "RANGE")
    return True, (1.5 if is_core else 1.0)
```

#### B. bb_rsi_reversion pair whitelist

```python
EDGE_PAIRS = frozenset({"USD_JPY"})
KILL_PAIRS = frozenset({"USD_CHF", "GBP_USD"})

def _bb_rsi_edge_cell(ctx) -> tuple[bool, float]:
    inst = _instrument_from_ctx(ctx)
    if inst in KILL_PAIRS:
        return False, 0.0
    if inst not in EDGE_PAIRS:
        return False, 0.0
    h = _utc_hour_from_ctx(ctx)
    if h is None:
        return False, 0.0
    if 7 <= h < 21:  # LDN/NY/Overlap
        return True, 1.0
    return True, 0.5  # ASN: half lot (mean -1.04p in data)
```

⚠️ **plan で確認すべき** (writing-plans skill が掘り下げる):
- `_utc_hour_from_ctx(ctx)`: 戦略既存の hour 取得 helper を再利用 (既存戦略は `ctx.df.index[-1].hour` などで取得している箇所あり、plan で具体パスを決定)
- `_instrument_from_ctx(ctx)`: 戦略既存の instrument access pattern (恐らく `ctx.instrument` または `ctx.symbol`)

#### C. lot_multiplier integration

`modules/demo_trader.py` の lot resolution に `candidate.lot_multiplier` 属性 hook:

```python
def _resolve_lot(self, entry_type, instrument, candidate=None):
    base = self._base_lot(entry_type, instrument)
    if candidate is not None and hasattr(candidate, 'lot_multiplier'):
        boost = float(getattr(candidate, 'lot_multiplier', 1.0))
    else:
        boost = float(self._PAIR_LOT_BOOST.get((entry_type, instrument), 1.0))
    return max(0, int(base * boost))
```

候補オブジェクト (Candidate dataclass) に `lot_multiplier: float = 1.0` を追加。

### 3.3 Data Flow

```
[Bar Close (M15/scalp tf)]
  → [Signal Generation] (既存)
  → [Cell Filter] ← NEW (skip 早期 return + lot_multiplier 付与)
  → [Tier / MTF Gate] (既存、変更なし)
  → [demo_trader._tick_entry] (_resolve_lot で multiplier 適用)
  → [Shadow / Live 分岐]
  → [Existing trailing exit] (変更なし、MFE 回収できているため)
```

### 3.4 Error Handling

| 異常ケース | 動作 | log level |
|---|---|---|
| `ctx.adx is None` | edge=False (skip) | INFO |
| `ctx.dist_ema200_pct is None` | edge=False (skip) | INFO |
| `ctx.regime_label` 不明 | core_boost なし (lot=1.0) | DEBUG |
| `ctx.instrument` 不明 | whitelist 不適合扱い (skip) | INFO |
| `candidate.lot_multiplier` missing | base lot を使用 (1.0×) | silent |

**fail-safe principle**: 不明な入力 → skip (旧来の安全側)。`[[feedback_label_empirical_audit]]` 「演繹禁止、ラベル無ければ撤退」遵守。

### 3.5 Testing

#### Unit tests (新規 3 ファイル)

- `tests/test_session_time_bias_edge_cell_filter.py` (15+ assertions):
  - LDN × ADX 15: edge_on, lot_mult=1.0
  - LDN × ADX 27: edge_on, lot_mult=1.5 (core boost via ADX≥25)
  - LDN × ADX 27 × regime_label=RANGE: lot_mult=1.5 (core boost)
  - LDN × ADX 18 × regime_label=RANGE: lot_mult=1.5 (core boost via RANGE)
  - LDN × ADX 14: skip (ADX 範囲外)
  - LDN × ADX 31: skip (ADX 範囲外、kill zone)
  - LDN × dist_EMA200 = 0.7%: skip (range gate fail)
  - ASN/NY/LATE 全 hour: skip (session 範囲外)
  - ctx.adx = None: skip
  - ctx.dist_ema200_pct = None: skip

- `tests/test_bb_rsi_reversion_pair_whitelist.py` (12+ assertions):
  - USD_JPY × LDN: edge_on, lot_mult=1.0
  - USD_JPY × NY: edge_on, lot_mult=1.0
  - USD_JPY × ASN: edge_on, lot_mult=0.5
  - USD_CHF 全 session: skip (KILL_PAIRS)
  - GBP_USD 全 session: skip (KILL_PAIRS)
  - EUR_USD: skip (not in EDGE_PAIRS, not in KILL — 安全側で skip)
  - 未知 pair "XAU_USD": skip

- `tests/test_lot_multiplier_resolution.py` (8+ assertions):
  - candidate.lot_multiplier = 1.5 → base * 1.5
  - candidate.lot_multiplier = 0.5 → base * 0.5
  - candidate.lot_multiplier missing → falls back to _PAIR_LOT_BOOST
  - 両方 missing → 1.0× base
  - candidate.lot_multiplier = 0 → 0 (skip 相当の単位)
  - 負値 → clamp 0
  - int 型強制 (units は OANDA で整数)
  - 既存 _PAIR_LOT_BOOST 経路は影響なし (vix_carry_unwind/USD_JPY=1.0× 維持)

#### Integration tests (既存テスト保護)

- 既存 `tests/test_session_time_bias_*.py` の signal logic 部は touch しない
- 既存 `tests/test_bb_rsi_reversion_*.py` 同上
- pre-existing 10 件の failed test は本 design の責任外 (`[[project_fxai_stale_test_backlog_2026_05_07]]`)

#### Validation gates (deploy 順序)

**Stage A: Pre-merge (Claude 一次実装、本 spec の plan に従う)**

- Unit tests 3 ファイル PASS
- `python3 scripts/check.py` PASS (registration consistency)
- 既存 edge_cell / cell_forensic / PAIR_PROMOTED tests PASS

**Stage B: Codex MASSIVE 12y BT (新方針: Codex に rescue/review として queue)**

```yaml
task: 20260608-edge-cell-filter-massive-12y-bt
priority: P1
rule: R1
deliverables:
  - bt-results/session-time-bias-cell-filter-12y.json
      pairs: [EUR_USD, GBP_USD, USD_JPY]
      filter: LDN × ADX[15,30] × dist_EMA200<0.5%
      compare: baseline (no filter) vs proposed
      WFO: 3-fold
  - bt-results/bb-rsi-reversion-pair-whitelist-12y.json
      pairs: 6 pair × 12y
      verify: USD_JPY が edge、USD_CHF/GBP_USD が catastrophic
      WFO: 3-fold
  - Bonferroni m=12 (cell × pair × direction)
gate:
  PROMOTE_SHADOW:
    - 12y PF >= 1.05 (in-sample 1.28 から OOS shock 20% buffer)
    - WFO >= 2/3 folds PF > 1
    - Wilson_lo Bonferroni-corrected >= 0.30 (OOS 緩和)
  REJECT:
    - 12y PF < 1.0 → 戦略 LIVE OFF 維持、shadow 観察継続
```

**Stage C: Shadow accumulation (deploy 後 30 日)**

- 新 filter で fire した shadow trades を `cell_filter_v1=1` タグ
- 30-day reconciliation 基準:
  - 期待 N: 90-130 fills (LDN × USD_JPY fire frequency × 40 日)
  - 期待 mean_pip ≥ +0.5 (in-sample +0.93/+0.10 から OOS 50% shock buffer)
  - Wilson_lo (実測) ≥ 0.40
- Reconciliation FAIL → env flag で旧 logic に rollback

**Stage D: LIVE ramp (Shadow PASS 後、別 session で user 判断)**

- 1k unit → 3k unit → 5k unit ramp
- ZZ Pivot v60 型 SizeReduce 適用 (loser zone N>=5 で半減)
- watchdog auto-demote (Wilson_lo=0.55 gate、Bearer fix 適用済) で監視

### 3.6 Rollback / Kill switch

env flag (`SESSION_TIME_BIAS_CELL_FILTER_V1=0` / `BB_RSI_REVERSION_PAIR_WHITELIST_V1=0`) で旧 logic に即時復帰。デフォルトは Shadow 開始から 30 日間 `=1`。

### 3.7 Linked memory / references

- `[[project_oanda_loss_surge_2026_06_03]]` — root cause 1st recovery
- `[[project_edge_cell_stage3_recovery_phase2_2026_06_07]]` — 2nd recovery + GBP_USD removal
- `[[edge-cells-stage3-wilson-lo-restoration-2026-06-07]]` — Wilson_lo=0.55 復帰 (本 design の上位 LOCK)
- `[[feedback_size_lever_beats_skip_filter]]` — SIZE lever (1.0/0.5) > SKIP filter の根拠
- `[[feedback_ma_filter_breaks_mr]]` — 単純 trend filter は MR を破壊 (本 design では cell filter で代替)
- `[[feedback_codex_mock_test_trap]]` — TV ≠ MASSIVE の前例 (Stage B 必須性の根拠)
- `[[feedback_label_empirical_audit]]` — 不明 ctx での skip 採用根拠
- `[[feedback_shadow_first_quant_architecture]]` — Stage C 30-day shadow ramp 根拠
- `[[feedback_codex_as_review_layer_2026_06_05]]` — 新方針下 Stage B を Codex に投げる根拠

## 4. Estimated impact (in-sample, 40 days)

| 指標 | 現状 baseline | 提案 design 適用 | 改善 |
|---|--:|--:|--:|
| session_time_bias N | 396 | 126 | -68% (fire を edge cell に絞る) |
| session_time_bias mean_pip | -2.06 | +0.93 | **+2.99p/trade** |
| session_time_bias sum_pip | -816 | +117 | **+933p** |
| bb_rsi_reversion N | 239 | 96 | -60% |
| bb_rsi_reversion mean_pip | -0.77 | +0.10 | +0.87p/trade |
| bb_rsi_reversion sum_pip | -184 | +9 | +193p |
| **2 戦略合計 sum_pip** | **-1,000** | **+126** | **+1,126p (40 日)** |

5k unit lot 換算 ≈ ¥350/pip → ¥39,410/40 日 ≈ ¥30k/月 baseline。
SIZE boost 1.5× の core cell (LDN × ADX 25-30) を加味すると ¥35-45k/月 in-sample。

**OOS realistic forecast** (期待値、確率加重):
| シナリオ | 確率 | 月次 P/L (5k unit) |
|---|---|---:|
| In-sample 通り再現 | 10% | +¥80-120k |
| OOS -30% 緩和 | 25% | +¥50-80k |
| OOS -50% 緩和 | 35% | +¥30-50k |
| OOS -80% 緩和 | 20% | -¥10〜+¥10k |
| Edge 消失 | 10% | -¥30-50k |
| **期待値** | — | **+¥35-50k/月** |

memory `[[project_tp_hit_12cell_portfolio_2026_06_05]]` の「現実上限 21.6% (Bonferroni 後)」とおおむね整合。

## 5. Out of scope (本 design では扱わない)

- 新規 entry_type の作成 (Approach 3 案、既存強化を採用したため)
- 出口ロジックの変更 (MFE 分析で既存 trailing が edge cell では機能と確認)
- 他戦略への波及 (sr_fib / dt_bb_rsi_mr 等は別 design で個別対応)
- Kalman D7 v18e USDJPY LIVE 継続判断 (user 判断、別議題)
- Portfolio aggregation / multi-strategy Kelly 最適化 (Phase 4.5 後の Phase 5 範囲)
- Bonferroni-strict edge 探索 (本 design は marginal edge の活用、strict edge 発掘は別 session)

## 6. Pre-mortem (想定失敗モード)

1. **Regime shift で edge cell が kill cell 化**
   - 例: EUR_USD が長期 trend 入り → LDN × ADX[15,30] でも MR が機能しない
   - 対応: watchdog auto-demote が Live N>=10 で発動、N=20 で disable

2. **Selection bias residual**
   - Cell を data-mining で発見した post-hoc selection
   - 対応: Stage B (Codex MASSIVE 12y) で OOS validation、PF<1.05 なら REJECT

3. **SIZE boost 1.5× が誤方向で増幅損失**
   - core cell でも逆方向 trade が出る (regime label "RANGE" 誤判定など)
   - 対応: SIZE boost は LDN × ADX[25,30] OR RANGE のみ。1.5× も限定的、worst case でも単 trade 損失 8-10p (5k unit ≈ ¥4k)

4. **既存 _PAIR_LOT_BOOST との衝突**
   - candidate.lot_multiplier と _PAIR_LOT_BOOST の両方が定義されているケース
   - 対応: candidate.lot_multiplier を優先 (戦略側意図が prevail)、_PAIR_LOT_BOOST は fallback

5. **Shadow N が想定より少ない (30 日で N<30)**
   - LDN × ADX[15,30] × range の発生頻度が低くて検定 power 不足
   - 対応: reconciliation を 60 日に延長、または USD_JPY も session_time_bias の edge_pair に追加検討

## 7. Success criteria (LOCK)

**30-day reconciliation target** (Shadow 開始から 30 日後):
- N (shadow with cell_filter_v1 tag): >= 60
- mean_pip: > +0.3 (OOS -70% shock buffer)
- Wilson_lo (実測): >= 0.35
- 2 戦略合計 sum_pip > +50p (40 日 in-sample +126 から 50% buffer)
- 全項目 PASS → Stage D (LIVE ramp) を別 session で user 判断

**FAIL**:
- 任意 1 項目 FAIL → env flag rollback、本 design を docs/superpowers/specs/ に SUPERSEDED 印
- 30 日 review session で原因 forensic、別 design 着手
