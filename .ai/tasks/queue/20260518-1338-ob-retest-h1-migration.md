---
id: 20260518-1338-ob-retest-h1-migration
title: "[ob_retest_h1 migration] H1 新戦略追加 (R1 pre-reg LOCK) + M5 ob_retest FORCE_DEMOTE (R2)"
owner: codex
status: queued
priority: P0
created_at: 2026-05-18T13:38:00+0900
roadmap_gate: "TV Pine BT (USDJPY 2026-02-09→2026-05-19) で M5 ob_retest を実測: Baseline N=733 WR=38.74% / Filter A (H1 EMA50 gate) N=519 WR=38.34% / Filter B (ADX≥20) N=451 WR=39.47%。Bonferroni m=3 補正前の α=0.05 でも全 null (|z| < 0.30)。H1 Gate (Wilson_lo≥0.40) 通過に必要な WR は N=300 で 45.5% — 現状 +6-7 pp の壁。TF 比較 BT で M5 -0.69%/y / M15 +0.24%/y / **H1 +0.40%/y (peak)** / H4 +0.20%/y。M5 構造では SL/ノイズ比とスプレッド占有が不利、entry filter では救えない。OB 思想を活かす前向き路は TF を H1 に上げて再設計のみ。Shadow N=36 WR=47.2% は M5 long-run mean からの 1.04σ 上振れ noise。"
rule: pre-reg
related:
  - strategies/hourly/__init__.py
  - strategies/hourly/donchian_momentum_breakout.py
  - strategies/hourly/keltner_squeeze_breakout.py
  - strategies/base.py
  - strategies/context.py
  - modules/demo_trader.py
  - app.py
  - data/cache/massive/USD_JPY_H1.parquet
  - data/cache/massive/EUR_USD_H1.parquet
  - data/cache/massive/GBP_USD_H1.parquet
  - data/cache/massive/EUR_JPY_H1.parquet
  - data/cache/massive/GBP_JPY_H1.parquet
  - knowledge-base/wiki/decisions/pre-reg-asia-range-fade-v1-2026-04-26.md
  - tools/sync_kb_index.py
  - tools/tier_integrity_check.py
  - feedback_shadow_first_quant_architecture
  - feedback_bt_must_use_massive
  - feedback_partial_quant_trap
  - feedback_label_empirical_audit
  - feedback_success_until_achieved
  - feedback_codex_mock_test_trap
  - feedback_codex_schema_hallucination
  - feedback_codex_stash_leak
  - feedback_spread_basis_for_mafe
  - feedback_exclude_xau
  - feedback_ma_filter_breaks_mr
  - project_fxai_state_2026_05_11
---

# 0. 背景 (Claude 司令塔 audit 完了)

## 0.1 観察 (TV Pine BT, USDJPY 2026-02-09 → 2026-05-19, 同期間/同パラメータ)

| 設定 | N | WR | Wilson_lo | z vs baseline | p | Bonferroni m=3 |
|---|---|---|---|---|---|---|
| Baseline (filters off) | 733 | 38.74% | 0.353 | — | — | — |
| + Filter A (H1 EMA50 gate) | 519 | 38.34% | 0.343 | -0.143 | 0.886 | NO |
| + Filter B (ADX ≥ 20 gate) | 451 | 39.47% | 0.351 | +0.250 | 0.803 | NO |

**結論**: M5 構造ではどのフィルタも WR を有意リフトしない (Bonferroni 補正前の α=0.05 でも null)。
H1 Gate (Wilson_lo ≥ 0.40) 通過に必要な WR は N=300 で 45.5%、N=500 で 44.3% 必要 — 現状 +6-7 pp の壁。

## 0.2 TF 比較 BT (同 Pine、パラメータ同一、USDJPY のみ)

- M5: WR 38.7%, EV<0, ~-0.69%/y (3.5mo BT)
- M15: WR 40.8%, breakeven, ~+0.24%/y (10.5mo BT)
- **H1: WR 41.8%, +1.35% / 3.4y, ~+0.40%/y (peak)**
- H4: WR 42.8%, +2.62% / 13.4y, ~+0.20%/y

H1 が sweet spot。M5 は SL/ノイズ比 (~3-6pip SL vs 1-3pip wick) と spread 占有 (0.7pip/5pip=14%) が構造的に不利、entry filter では救えない。

## 0.3 Shadow 現状 (Render API, 2026-05-15)

- `ob_retest` tier=PHASE0_SHADOW, N=36, WR=47.2%, +186.7 pips
- USD_JPY/BUY direction cell N=17 WR=52.9%, Wilson_lo=0.3096
- H1 Gate FAIL (Wilson_lo 0.32 ≪ 0.40), WF h1_avg=-0.522 (regime fit)
- shadow vs M5 BT WR (47.2% vs 38.7%) は 1.04σ 程度の上振れ = noise

---

# 1. 実装タスク (3 サブタスク)

## Task A: 新 H1 戦略 `ob_retest_h1` 実装 (rule: R1)

**ファイル**: `strategies/hourly/ob_retest.py` (新規)

**Class signature**:

```python
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext


class ObRetestH1(StrategyBase):
    name = "ob_retest_h1"
    mode = "hourly"
    enabled = True
```

**Parameters (LOCKED — post-hoc modification 禁止)**:

```python
# OB detection
IMPULSE_MIN_BARS = 3
IMPULSE_ATR_MULT = 2.0
OB_LOOKBACK = 60        # H1 × 60 = 60h ≈ 2.5 営業日
OB_FRESHNESS = 50       # H1 × 50 = ~2 営業日
OB_MAX_WIDTH_ATR = 2.0

# Entry confirmation
EMA_FAST = 9
EMA_SLOW = 21
RETEST_BUFFER_ATR = 0.10  # zone touch tolerance

# Risk
SL_BUFFER_ATR = 0.10      # SL = OB境界 ± 0.10 * ATR
TP_R_MULT = 1.5

# Pairs
ALLOWED_PAIRS = {"USDJPY", "EURUSD", "GBPUSD", "EURJPY", "GBPJPY"}
```

**Entry Logic** (USD_JPY/BUY for reference, SELL は対称):

```
1. OB 検出: 候補バー = 現在 - (IMPULSE_MIN_BARS+1)
   - 候補が陰線 (close < open)
   - その後 IMPULSE_MIN_BARS 本連続陽線
   - 連続陽線合計 range ≥ ATR * IMPULSE_ATR_MULT
   - 候補バー range ≤ ATR * OB_MAX_WIDTH_ATR
   → bullish OB { high, low, age=0 } を push

2. Age 管理: age > OB_FRESHNESS の OB は expire

3. Retest 判定 (BUY):
   - low ≤ ob_high + RETEST_BUFFER_ATR * ATR
   - low ≥ ob_low  - RETEST_BUFFER_ATR * ATR
   - close > open (bullish reversal candle)
   - EMA9 > EMA21 AND close > EMA21

4. SL/TP (entry_price ベース、signal_price ではない — feedback_spread_basis_for_mafe):
   - SL = ob_low - SL_BUFFER_ATR * ATR
   - risk = entry_price - SL
   - TP = entry_price + risk * TP_R_MULT
```

**Reference**: 既存 `strategies/hourly/donchian_momentum_breakout.py` の `evaluate()` パターン踏襲。`Candidate` 返却、`SignalContext` 経由でデータアクセス。

## Task B: HourlyEngine への登録 (rule: R1)

**ファイル**: `strategies/hourly/__init__.py`

**Diff**:

```python
from strategies.hourly.keltner_squeeze_breakout import KeltnerSqueezeBreakout
from strategies.hourly.donchian_momentum_breakout import DonchianMomentumBreakout
+from strategies.hourly.ob_retest import ObRetestH1


class HourlyEngine:
    def __init__(self):
        self.strategies: list[StrategyBase] = [
            KeltnerSqueezeBreakout(),
            DonchianMomentumBreakout(),
+           ObRetestH1(),
        ]
```

## Task C: M5 `ob_retest` を FORCE_DEMOTE (rule: R2)

**ファイル**: `modules/demo_trader.py`、`_FORCE_DEMOTED` set (現 line 6194 付近)

**Diff** (set リテラル末尾に追加):

```python
_FORCE_DEMOTED = {
    "ema_cross", "inducement_ob",
    ...既存全て維持...
    "donchian_momentum_breakout",
    "v_reversal",
+   # 2026-05-18 (rule:R2): M5 ob_retest demote
+   # TV Pine BT USDJPY M5 N=733 WR=38.74% EV<0
+   # Filter A/B sweep で Bonferroni m=3 全 null (|z|<0.30).
+   # Shadow N=36 WR 47.2% は M5 long-run mean からの 1.04σ noise.
+   # OB 思想は ob_retest_h1 (R1 pre-reg) へ移行。
+   # 詳細: knowledge-base/wiki/decisions/pre-reg-ob-retest-h1-2026-05-18.md
+   "ob_retest",
}
```

---

# 2. Pre-Registration LOCK (R1)

**ファイル**: `knowledge-base/wiki/decisions/pre-reg-ob-retest-h1-2026-05-18.md` (新規)

本 task spec の Section 0 + 1 + 2 を pre-reg LOCK 文書としてそのまま転記し、commit に含める。
既存 `pre-reg-asia-range-fade-v1-2026-04-26.md` の構造を踏襲。

## 2.1 Hypothesis (LOCKED)

H1 TF では SL/ノイズ比 (~30-50pip SL vs ~5-8pip wick noise) と spread 占有率 (0.7pip / 40pip SL = 1.75%) が改善し、OB 構造の institutional anchoring が機能。USD_JPY/BUY direction で **WR ≥ 44%, Wilson_lo ≥ 0.40, EV ≥ +0.20 pip/trade**。

## 2.2 Pre-reg PASS / FAIL 基準 (LOCKED, post-hoc modification 禁止)

365d MASSIVE BT (USD_JPY, EUR_USD, GBP_USD, EUR_JPY, GBP_JPY) 5 pair で:

**PASS**: 全 5 pair で **少なくとも 1 pair が**:
- N ≥ 200
- WR ≥ 44.0%
- Wilson_lo (95% CI) ≥ 0.40
- EV ≥ +0.20 pip/trade (spread + slippage 摩擦控除後)
- PF ≥ 1.10
- WF (walk-forward, 3+ folds) h1 / h2 / h3 全て EV ≥ 0

**FAIL**: 上記いずれか満たさず → 以下のロールバック:
- `strategies/hourly/ob_retest.py` を `enabled = False` に変更
- HourlyEngine 登録は維持 (将来再評価のため)
- 失敗 evidence を pre-reg LOCK 文書末尾に追記

## 2.3 Bonferroni 補正

m=5 (pair 数) → 1 pair PASS の α=0.05/5 = 0.01。Wilson_lo 計算は 95% CI 維持、Wilson_bf_lo は z=2.575 (99%) で別途算出して併記。

## 2.4 マルチプル検定範囲

本 BT で **パラメータ sweep は禁止**。LOCKED parameter で 5 pair 一発勝負。
将来 sweep するなら別 pre-reg LOCK + Bonferroni m 増加で対応。

---

# 3. BT 実行要件

**データソース**: `data/cache/massive/*.parquet` (MASSIVE Market Data API 由来) のみ。Yahoo 禁止 (feedback_bt_must_use_massive)。
実行前に `ls data/cache/massive/` で対象 5 pair の H1 parquet 存在を確認、不在 pair があれば**実行前に Claude に報告**し本 LOCK を修正する (post-hoc 除外禁止)。

**TF**: 1h

**期間**: 365d (2025-05-18 → 2026-05-18, 結合 1 年 OOS-only)

**ペア**: USD_JPY, EUR_USD, GBP_USD, EUR_JPY, GBP_JPY (XAU 除外 — feedback_exclude_xau)

**摩擦モデル**:
- Spread (pip): USD_JPY=0.7, EUR_USD=0.6, GBP_USD=1.0, EUR_JPY=1.0, GBP_JPY=1.5
- Slippage: 0.2 pip 固定
- Commission: 0

**WF Folds**: 3 folds (各 ~120 日, h1=Q1, h2=Q2-3, h3=Q4)

**Live/Shadow 分離** (feedback_live_shadow_separation): BT 出力には Live/Shadow フラグは持たない (BT は単一 universe)。OANDA Live 集計時の混入のみ警戒点であり、本 task では該当しない。

**Output**:
- `raw/bt-results/ob_retest_h1_365d_2026_05_18.json` (pair × WR / N / EV / PF / Wilson_lo / Wilson_bf_lo / WF folds)
- `knowledge-base/wiki/strategies/ob_retest_h1.md` (戦略カード新規)

---

# 4. Tier Sync (実装後)

```bash
python3 tools/sync_kb_index.py --write
python3 tools/tier_integrity_check.py --write
python3 tools/tier_integrity_check.py --check  # ERROR=0 確認
```

`ob_retest` (M5) が `_FORCE_DEMOTED` のみに残り、`PAIR_PROMOTED` / `LOT_BOOST` / `WHITELIST` 等から消えることを `tier_integrity_check.py` で確認。ERROR が 1 件でも出たら **commit 前に停止して報告**。

---

# 5. Tests (必須、E2E 含む)

**ファイル**: `tests/test_ob_retest_h1.py` (新規)

**Coverage**:

1. **OB 検出 unit**: 既知の synthetic candle 列で bullish/bearish OB を正しく push
2. **Retest entry unit**: OB push 後の 適切な retest bar で BUY/SELL Candidate 返却
3. **Risk geometry unit**: SL/TP が ATR-based で entry_price 基準で正しく計算 (feedback_spread_basis_for_mafe)
4. **HourlyEngine integration**: `HourlyEngine().strategies` に `ObRetestH1` インスタンスが含まれる
5. **`_FORCE_DEMOTED` integration**: `"ob_retest" in DemoTrader._FORCE_DEMOTED == True`
6. **E2E** (feedback_codex_mock_test_trap 対応): MASSIVE parquet (USD_JPY_H1 fixture) を読み込んで H1 BT を 30d 走らせる → 0 件以上の trade、no exception、結果が dict 構造で返る

`python3 -m pytest tests/test_ob_retest_h1.py -x -v` で全 pass 必須。
既存 `python3 -m pytest tests/ -x -q` も全 pass 維持。

---

# 6. Commit 構造 (R1 規律)

1 つの feat commit に以下を全て含む:

- `strategies/hourly/ob_retest.py` (新規)
- `strategies/hourly/__init__.py` (登録)
- `modules/demo_trader.py` (`_FORCE_DEMOTED` 更新)
- `tests/test_ob_retest_h1.py` (新規)
- `knowledge-base/wiki/decisions/pre-reg-ob-retest-h1-2026-05-18.md` (新規)
- `knowledge-base/wiki/strategies/ob_retest_h1.md` (新規)
- `raw/bt-results/ob_retest_h1_365d_2026_05_18.json` (BT 結果)
- `CHANGELOG.md` 更新
- 関連 `knowledge-base/wiki/index.md` / `tier-master.md` 自動再生成

**Commit message prefix**: `feat(strategy): ob_retest_h1 + M5 ob_retest demote — pre-reg LOCK + R2 demote`
**Body**: `rule:R1` (H1 add) と `rule:R2` (M5 demote) 両方明示、BT verdict (PASS/FAIL)、5 pair 結果サマリ。

feedback_codex_stash_leak 防止: final.md の宣言だけでなく、必ず以下を CI 内で実 verify:

- `git log --oneline -1` で実コミットを確認
- `git diff HEAD~1 -- strategies/hourly/ob_retest.py` で実 diff を確認
- `git stash list` が空であることを確認

---

# 7. 想定される失敗ケースと対応

| シナリオ | 対応 |
|---|---|
| 5 pair 全 NULL | pre-reg FAIL → `enabled = False`、wiki/decisions に REJECT 記録、ob_retest 系統は OB 思想自体を退役候補化 |
| 1-2 pair PASS, 残り FAIL | enabled=True、PAIR_PROMOTED は最初の Live N≥30 監査まで適用なし。Shadow から開始 |
| BT で N が 200 未満 | N 不足 → pre-reg FAIL (parameter loosen post-hoc 禁止) |
| Wilson_lo 0.38-0.39 で borderline | FAIL 扱い (0.40 が LOCKED 閾値) |
| MASSIVE parquet 不在 pair | Codex は実行前に `ls data/cache/massive/` で確認、不在 pair は **実行前に Claude へ報告**し本 LOCK を修正する (post-hoc 除外禁止) |
| pytest fail | commit 前停止、報告 |
| tier_integrity_check ERROR | commit 前停止、報告 |

---

# 8. 完了報告フォーマット

Codex は完了時に以下を Discord 経由で返す:

- ✅/❌ 各 pair の BT 結果サマリ (N / WR / Wilson_lo / EV / PF)
- pre-reg PASS / FAIL verdict (Section 2.2 基準)
- Tier integrity check ERROR/WARN 件数
- pytest 結果 (全 N pass / N fail)
- commit hash + branch
- `git stash list` 結果 (空 expected)

---

# 9. 禁止事項

- 本 task 範囲外のファイル (`.env`, OANDA 認証情報, 本番 DB) への書き込み
- 既存戦略の挙動変更 (`donchian_momentum_breakout.py` 等)
- pre-reg LOCK 後のパラメータ修正 (LOCKED parameters は post-hoc 変更禁止)
- BT 結果の cherry-pick (5 pair 全結果を `raw/bt-results/` に保存、verdict は LOCKED 基準のみで判定)
- `--no-verify` `--no-gpg-sign` 等の hook bypass
- 機微情報 (`OANDA_API_KEY=`, `sk-`, `rnd_`, `ghp_`, `OPENAI_API_KEY=`) のコミット
