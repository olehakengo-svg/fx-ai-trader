"""tools/phase3_bt.py — Phase 3 BT Pre-reg LOCK 実装 (Phase 1 skeleton)

Pre-reg LOCK commit:    34c404c (`docs(pre-reg): Phase 3 BT Pre-Registration LOCK + Wave 1 R2-A Power Analysis`)
Implementation commit:  (TBD - set after first commit)

LOCK source:    knowledge-base/wiki/learning/phase3-bt-pre-reg-lock.md
Skeleton design: knowledge-base/wiki/learning/phase3-bt-skeleton-design.md

Phase 1 scope (本ファイル):
  - LOCK Constants (K=7, ALPHA_BONFERRONI, WFA dates, FRICTION_MODE_A/B)
  - Friction Mode A/B context manager
  - Strategy loader (skip-on-missing)
  - Statistical functions (wilson_lower, welch_t_test, bonferroni_test)
  - Anchored WFA runner (1 strategy で動作確認)

Phase 2+ (別実装):
  - Rolling WFA framework
  - G1-G5 audit functions
  - Result aggregator (3D matrix)
  - Full orchestrator (K=7 × 2 modes × 2 WFA = 28 BT runs)
  - Range-fetch (lookback_days → date range)

HARKing 防止規律:
  - LOCK 値 (K, α, WFA dates, FRICTION_MODE_*) は constants で hard-code、動的計算禁止
  - BT data 観測前に commit + push で時刻署名
  - re-fit 禁止 (IS で最適化したパラメータを OOS で再最適化しない)
"""
from __future__ import annotations

import logging
import math
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Dict, Iterator, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────
# Section 1: LOCK Constants (Pre-reg LOCK 文書由来、絶対不変)
# ─────────────────────────────────────────────────────────────────────────

PHASE3_STRATEGIES: Tuple[str, ...] = (
    "pullback_to_liquidity_v1",
    "asia_range_fade_v1",
    "gbp_deep_pullback",
    "vol_momentum_scalp",
    "htf_false_breakout",
    "liquidity_sweep",
    "london_fix_reversal",
)
K = len(PHASE3_STRATEGIES)  # = 7

# Bonferroni (confirmatory): α/K = 0.05/7 = 0.00714... (LOCK)
ALPHA_BONFERRONI: float = 0.05 / 7  # 約 0.007142857142857143

# FDR (exploratory)
FDR_Q: float = 0.10

# WFA Anchored 期間 (LOCK)
WFA_ANCHORED_IS_START = datetime(2025, 1, 1, tzinfo=timezone.utc)
WFA_ANCHORED_IS_END = datetime(2025, 9, 30, 23, 59, 59, tzinfo=timezone.utc)
WFA_ANCHORED_OOS_START = datetime(2025, 10, 1, tzinfo=timezone.utc)
WFA_ANCHORED_OOS_END = datetime(2026, 4, 26, 23, 59, 59, tzinfo=timezone.utc)

# WFA Rolling 設定 (Phase 2 で使用、Phase 1 は定数定義のみ)
WFA_ROLLING_IS_MONTHS = 6
WFA_ROLLING_OOS_MONTHS = 1
WFA_ROLLING_STEP_MONTHS = 1

# Hold-out validation set 開始日 (LOCK)
HOLDOUT_START = datetime(2026, 5, 1, tzinfo=timezone.utc)

# Friction Mode A: 現 status quo (modules/friction_model_v2._SESSION_MULTIPLIER)
FRICTION_MODE_A: Dict[str, float] = {
    "label": "status_quo",
    "London": 1.00,
    "NY": 1.20,
    "Tokyo": 1.45,
    "overlap_LN": 0.85,
    "default": 1.10,
}

# Friction Mode B: U13/U14 calibrated (Tokyo halve, London tighten)
FRICTION_MODE_B: Dict[str, float] = {
    "label": "u13_u14_calibrated",
    "London": 0.85,
    "Tokyo": 0.80,
    "NY": 1.20,
    "overlap_LN": 0.85,
    "default": 1.10,
}

# Pre-reg LOCK commit (時刻署名 anchor)
PRE_REG_COMMIT: str = "34c404c"

# 既知の未実装戦略 (skip+warn 対象)
# R-A revision (2026-04-27): pullback_to_liquidity_v1 / asia_range_fade_v1 が
# 実装されたため empty に更新。
MISSING_STRATEGIES: frozenset = frozenset()


# ─────────────────────────────────────────────────────────────────────────
# Section 2: Strategy Mapping (Phase 1 動作確認可能 5 戦略)
# ─────────────────────────────────────────────────────────────────────────

# Strategy name → (subdir, module_filename) マッピング
STRATEGY_PATHS: Dict[str, Tuple[str, str]] = {
    "gbp_deep_pullback":        ("daytrade", "gbp_deep_pullback"),
    "vol_momentum_scalp":       ("scalp",    "vol_momentum"),
    "htf_false_breakout":       ("daytrade", "htf_false_breakout"),
    "liquidity_sweep":          ("daytrade", "liquidity_sweep"),
    "london_fix_reversal":      ("daytrade", "london_fix_reversal"),
    "pullback_to_liquidity_v1": ("daytrade", "pullback_to_liquidity_v1"),
    "asia_range_fade_v1":       ("daytrade", "asia_range_fade_v1"),
}

# Strategy → BT runner selector マッピング (R4 revision verified 2026-04-27)
#
# 値の意味: BT runner 選択ラベル。"DT" は app.run_daytrade_backtest を選択、
# "Scalp" は app.run_scalp_backtest を選択。strategy class の `mode` 属性
# (e.g., "daytrade", "scalp") とは別の runner-selector key であることに注意。
#
# 検証 (R4 verification, 2026-04-27):
#   - gbp_deep_pullback   strategies/daytrade/gbp_deep_pullback.py: mode="daytrade" → DT ✓
#   - vol_momentum_scalp  strategies/scalp/vol_momentum.py:        mode="scalp"    → Scalp ✓
#   - htf_false_breakout  strategies/daytrade/htf_false_breakout.py: mode="daytrade" → DT ✓
#   - liquidity_sweep     strategies/daytrade/liquidity_sweep.py:    mode="daytrade" → DT ✓
#   - london_fix_reversal strategies/daytrade/london_fix_reversal.py: mode="daytrade" → DT ✓
#
# Production 統合確認 (modules/demo_trader.py):
#   - liquidity_sweep / london_fix_reversal は daytrade strategy list に登録 ✓
#   - vol_momentum_scalp は scalp strategy list に登録 ✓
STRATEGY_MODES: Dict[str, str] = {
    "gbp_deep_pullback":        "DT",
    "vol_momentum_scalp":       "Scalp",
    "htf_false_breakout":       "DT",
    "liquidity_sweep":          "DT",
    "london_fix_reversal":      "DT",
    "pullback_to_liquidity_v1": "DT",  # R-A: pre-reg LOCK 実装済 (2026-04-27)
    "asia_range_fade_v1":       "DT",  # R-A: pre-reg LOCK 実装済 (2026-04-27)
}

# Expected strategy class `mode` attribute (R4 verification source-of-truth)
# 本マッピングは load_strategy() / verify_strategy_modes() で source と
# cross-check するための reference。drift 検出時は warning。
EXPECTED_STRATEGY_CLASS_MODES: Dict[str, str] = {
    "gbp_deep_pullback":        "daytrade",
    "vol_momentum_scalp":       "scalp",
    "htf_false_breakout":       "daytrade",
    "liquidity_sweep":          "daytrade",
    "london_fix_reversal":      "daytrade",
    "pullback_to_liquidity_v1": "daytrade",
    "asia_range_fade_v1":       "daytrade",
}



@dataclass
class StrategyHandle:
    """Loaded strategy の reference + metadata。"""
    name: str
    mode: str  # "DT" or "Scalp"
    module_path: str  # e.g. "strategies.daytrade.gbp_deep_pullback"


def load_strategy(name: str) -> Optional[StrategyHandle]:
    """Phase 3 採用 K=7 戦略のうち、source 実装ありを load。

    MISSING_STRATEGIES (pullback_to_liquidity_v1, asia_range_fade_v1) は
    pre-reg LOCK 既設だが source 未実装、warn + None を返す。

    Args:
        name: PHASE3_STRATEGIES のいずれか

    Returns:
        StrategyHandle or None (skip 該当時)

    Raises:
        ValueError: name が PHASE3_STRATEGIES に無い場合
    """
    if name not in PHASE3_STRATEGIES:
        raise ValueError(
            f"{name!r} not in PHASE3_STRATEGIES (K=7 LOCK). "
            f"Adding strategies requires new Pre-reg LOCK."
        )

    if name in MISSING_STRATEGIES:
        logger.warning(
            "Strategy %r is in PHASE3_STRATEGIES but source is not yet implemented. "
            "Pre-reg LOCK candidate, skip in current Phase 3 BT.", name
        )
        return None

    if name not in STRATEGY_PATHS:
        logger.warning("Strategy %r has no STRATEGY_PATHS entry, skip.", name)
        return None

    subdir, module_filename = STRATEGY_PATHS[name]
    module_path = f"strategies.{subdir}.{module_filename}"

    # Security note (CWE-706): module_path は STRATEGY_PATHS (LOCK constant) から
    # のみ構築され、外部入力経路はない。Phase 1 では実 import 検証は省略し、
    # actual loading は run_anchored_wfa() 内で app.py の statically-imported
    # BT runners を経由する (動的 import なし)。

    return StrategyHandle(
        name=name,
        mode=STRATEGY_MODES.get(name, "DT"),
        module_path=module_path,
    )


# ─────────────────────────────────────────────────────────────────────────
# Section 3: Friction Mode Context Manager
# ─────────────────────────────────────────────────────────────────────────

@contextmanager
def patch_friction_model(mode: Dict[str, float]) -> Iterator[None]:
    """`modules.friction_model_v2._SESSION_MULTIPLIER` を一時的に上書き。

    Mode A (status quo) と Mode B (calibrated) を切替えて BT 実行する用。
    `try/finally` で必ず restore する。

    Usage:
        with patch_friction_model(FRICTION_MODE_B):
            result = run_daytrade_backtest(...)

    Args:
        mode: FRICTION_MODE_A or FRICTION_MODE_B (label 含む dict)
    """
    from modules import friction_model_v2

    # snapshot original
    original = dict(friction_model_v2._SESSION_MULTIPLIER)

    # apply (label key を除いた数値のみ)
    mode_numeric = {k: v for k, v in mode.items() if k != "label" and isinstance(v, (int, float))}

    try:
        friction_model_v2._SESSION_MULTIPLIER.clear()
        friction_model_v2._SESSION_MULTIPLIER.update(mode_numeric)
        logger.info(
            "patch_friction_model applied: mode=%s, _SESSION_MULTIPLIER=%s",
            mode.get("label", "?"), mode_numeric,
        )
        yield
    finally:
        friction_model_v2._SESSION_MULTIPLIER.clear()
        friction_model_v2._SESSION_MULTIPLIER.update(original)
        logger.info("patch_friction_model restored: original keys=%s", list(original.keys()))


# ─────────────────────────────────────────────────────────────────────────
# Section 4: Statistical Functions
# ─────────────────────────────────────────────────────────────────────────

def wilson_lower(wins: int, n: int, z: float = 1.96) -> float:
    """Wilson 95% confidence interval lower bound (%)。

    p̂ = wins / n, n=0 のとき 0.0 を返す。

    Args:
        wins: 勝ち数 (≥ 0)
        n: 総 trade 数 (≥ 0)
        z: critical value (default 1.96 = 95% two-sided / 97.5% one-sided)

    Returns:
        Lower bound (%, 0-100)
    """
    if n <= 0:
        return 0.0
    if wins < 0 or wins > n:
        raise ValueError(f"wins={wins} must be in [0, {n}]")

    p = wins / n
    denom = 1.0 + (z * z) / n
    centre = p + (z * z) / (2 * n)
    margin = z * math.sqrt((p * (1 - p) + (z * z) / (4 * n)) / n)
    lower = (centre - margin) / denom
    return lower * 100.0


def welch_t_test(xs: List[float], ys: List[float]) -> Tuple[float, float]:
    """Welch's two-sample t-test (両側 p-value)。

    Args:
        xs: sample 1 (length n_x)
        ys: sample 2 (length n_y)

    Returns:
        (t-statistic, two-sided p-value)
    """
    from scipy import stats
    if not xs or not ys:
        return (float("nan"), 1.0)
    result = stats.ttest_ind(xs, ys, equal_var=False, alternative="two-sided")
    return (float(result.statistic), float(result.pvalue))


def bonferroni_test(p_values: List[float], k: Optional[int] = None,
                    alpha: float = 0.05) -> List[bool]:
    """Bonferroni-corrected significance test。

    Args:
        p_values: 各仮説の p-value
        k: 多重検定の数 (default: len(p_values))
        alpha: family-wise error rate (default 0.05)

    Returns:
        List[bool]: 各仮説について p < α/K で True (帰無棄却)
    """
    if k is None:
        k = len(p_values)
    if k <= 0:
        return []
    threshold = alpha / k
    return [p < threshold for p in p_values]


# ─────────────────────────────────────────────────────────────────────────
# Section 5: Anchored WFA Runner
# ─────────────────────────────────────────────────────────────────────────

@dataclass
class WFAStats:
    """WFA period 統計 (IS or OOS)。"""
    n: int
    wins: int
    wr: float  # 0-1
    ev: float  # avg pnl_pips
    pf: float  # profit factor
    wilson_lower: float  # %, 95% CI lower

    @classmethod
    def from_trades(cls, trades: List[Dict]) -> "WFAStats":
        if not trades:
            return cls(n=0, wins=0, wr=0.0, ev=0.0, pf=0.0, wilson_lower=0.0)
        n = len(trades)
        wins = sum(1 for t in trades if t.get("outcome") == "WIN")
        pnls = [float(t.get("pnl_pips", 0) or 0) for t in trades]
        wr = wins / n if n > 0 else 0.0
        ev = sum(pnls) / n if n > 0 else 0.0
        gross_profit = sum(p for p in pnls if p > 0)
        gross_loss = abs(sum(p for p in pnls if p < 0))
        pf = gross_profit / gross_loss if gross_loss > 0 else float("inf")
        wlow = wilson_lower(wins, n)
        return cls(n=n, wins=wins, wr=wr, ev=ev, pf=pf, wilson_lower=wlow)


@dataclass
class AnchoredWFAResult:
    """Anchored WFA 結果 (1 strategy × 1 mode × 1 symbol)。"""
    strategy: str
    symbol: str
    mode_label: str
    is_stats: WFAStats
    oos_stats: WFAStats
    oos_ev_degradation: float  # OOS EV / IS EV (negative = OOS worse)
    p_value: float  # Welch t-test on IS vs OOS pnls


def run_anchored_wfa(
    handle: StrategyHandle,
    symbol: str,
    friction_mode: Dict[str, float],
    bt_runner: Optional[Callable] = None,
) -> Optional[AnchoredWFAResult]:
    """1 strategy × 1 symbol × 1 friction_mode で Anchored WFA を実行。

    IS = 2025-01-01 ~ 2025-09-30 (9m)
    OOS = 2025-10-01 ~ 2026-04-26 (~7m)

    Phase 1 caveat: app.run_daytrade_backtest() は lookback_days API のため、
    full IS/OOS range fetch は Phase 2 で対応。Phase 1 は **lookback で動作確認**
    のみ実施し、結果の trade_log を entry_time で IS/OOS に分割する。

    Args:
        handle: load_strategy() の戻り値
        symbol: e.g. "USDJPY=X"
        friction_mode: FRICTION_MODE_A or FRICTION_MODE_B
        bt_runner: テスト用に inject 可能な BT runner (default: app の標準)

    Returns:
        AnchoredWFAResult or None (BT 実行失敗 / 戦略 missing)
    """
    if handle is None:
        logger.warning("run_anchored_wfa: handle is None (missing strategy), skip.")
        return None

    # BT runner を inject (テスト用) または app.py からダイナミック import
    if bt_runner is None:
        try:
            import app
            if handle.mode == "Scalp":
                bt_runner = app.run_scalp_backtest
            else:
                bt_runner = app.run_daytrade_backtest
        except Exception as e:
            logger.warning("Failed to import app BT runner: %s", e)
            return None

    # Phase 1: lookback で範囲指定 (~480 日 = IS+OOS approx)
    # Phase 2 で range fetch に置換
    LOOKBACK_DAYS = 480

    with patch_friction_model(friction_mode):
        try:
            result = bt_runner(symbol=symbol, lookback_days=LOOKBACK_DAYS)
        except Exception as e:
            logger.error("BT runner failed: %s", e)
            return None

    if not result or "trade_log" not in result:
        logger.warning("BT result missing trade_log: %s", result.get("error") if result else "no result")
        return None

    # 戦略単位 filter
    all_trades = result.get("trade_log", [])
    strat_trades = [t for t in all_trades if t.get("entry_type") == handle.name]

    # IS/OOS split
    is_trades = []
    oos_trades = []
    for t in strat_trades:
        ts = t.get("entry_time", "")
        if not ts:
            continue
        try:
            et = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if et.tzinfo is None:
                et = et.replace(tzinfo=timezone.utc)
            if WFA_ANCHORED_IS_START <= et <= WFA_ANCHORED_IS_END:
                is_trades.append(t)
            elif WFA_ANCHORED_OOS_START <= et <= WFA_ANCHORED_OOS_END:
                oos_trades.append(t)
        except (ValueError, TypeError):
            continue

    is_stats = WFAStats.from_trades(is_trades)
    oos_stats = WFAStats.from_trades(oos_trades)

    # OOS EV degradation: OOS_EV / IS_EV (近 1.0 = no degradation, ≤ 0.5 = severe)
    if is_stats.ev != 0:
        oos_ev_degradation = oos_stats.ev / is_stats.ev
    else:
        oos_ev_degradation = float("nan")

    # Welch t-test on per-trade PnL distributions
    is_pnls = [float(t.get("pnl_pips", 0) or 0) for t in is_trades]
    oos_pnls = [float(t.get("pnl_pips", 0) or 0) for t in oos_trades]
    if len(is_pnls) >= 2 and len(oos_pnls) >= 2:
        _, p_value = welch_t_test(is_pnls, oos_pnls)
    else:
        p_value = float("nan")

    return AnchoredWFAResult(
        strategy=handle.name,
        symbol=symbol,
        mode_label=str(friction_mode.get("label", "?")),
        is_stats=is_stats,
        oos_stats=oos_stats,
        oos_ev_degradation=oos_ev_degradation,
        p_value=p_value,
    )


# ─────────────────────────────────────────────────────────────────────────
# Section 5.5: Verification helpers (R4, R6 quant rigor revision 2026-04-27)
# ─────────────────────────────────────────────────────────────────────────

def _load_strategy_classes() -> Dict[str, type]:
    """全 PHASE3 戦略の class object を static import で取得 (security 対応)。

    importlib.import_module() の dynamic import を避け、静的 import
    で whitelisted modules のみを load (CWE-706 対策)。

    Returns:
        Dict[strategy_name, class_object | None]
        MISSING_STRATEGIES や ImportError は None。
    """
    classes: Dict[str, type] = {}

    # Static imports (whitelisted modules only, no dynamic dispatch)
    try:
        from strategies.daytrade.gbp_deep_pullback import GbpDeepPullback as _gbp
        classes["gbp_deep_pullback"] = _gbp
    except ImportError:
        classes["gbp_deep_pullback"] = None

    try:
        from strategies.scalp.vol_momentum import VolMomentumScalp as _vms
        classes["vol_momentum_scalp"] = _vms
    except ImportError:
        classes["vol_momentum_scalp"] = None

    try:
        from strategies.daytrade.htf_false_breakout import HtfFalseBreakout as _hfb
        classes["htf_false_breakout"] = _hfb
    except ImportError:
        try:
            # クラス名が異なる可能性 (snake_case → CamelCase 変換差)、
            # 失敗時は module を import せず None を保持
            classes["htf_false_breakout"] = None
        except ImportError:
            classes["htf_false_breakout"] = None

    try:
        from strategies.daytrade.liquidity_sweep import LiquiditySweep as _ls
        classes["liquidity_sweep"] = _ls
    except ImportError:
        classes["liquidity_sweep"] = None

    try:
        from strategies.daytrade.london_fix_reversal import LondonFixReversal as _lfr
        classes["london_fix_reversal"] = _lfr
    except ImportError:
        classes["london_fix_reversal"] = None

    # R-A: Pre-reg LOCK 実装 (2026-04-27)
    try:
        from strategies.daytrade.pullback_to_liquidity_v1 import PullbackToLiquidityV1 as _ptlv1
        classes["pullback_to_liquidity_v1"] = _ptlv1
    except ImportError:
        classes["pullback_to_liquidity_v1"] = None

    try:
        from strategies.daytrade.asia_range_fade_v1 import AsiaRangeFadeV1 as _arfv1
        classes["asia_range_fade_v1"] = _arfv1
    except ImportError:
        classes["asia_range_fade_v1"] = None

    return classes


def verify_strategy_modes() -> Dict[str, Dict[str, str]]:
    """STRATEGY_MODES と各 strategy class `mode` 属性の整合性を verify。

    R4 revision: Phase 3 BT 実行前に runner selector mapping が strategy
    class の actual mode と一致しているか確認。drift 検出時は warning を返す。

    Static import 使用 (CWE-706 対策、_load_strategy_classes 経由)。

    Returns:
        Dict[strategy_name, {"runner_selector": str, "class_mode": str | None,
                              "match": bool, "error": str | None}]
    """
    classes = _load_strategy_classes()
    results: Dict[str, Dict[str, str]] = {}

    for name in PHASE3_STRATEGIES:
        if name in MISSING_STRATEGIES:
            results[name] = {
                "runner_selector": "(skip)",
                "class_mode": None,
                "match": False,
                "error": "MISSING_STRATEGIES (source not found)",
            }
            continue

        runner_selector = STRATEGY_MODES.get(name, "?")
        expected_class_mode = EXPECTED_STRATEGY_CLASS_MODES.get(name, "?")
        cls = classes.get(name)

        if cls is None:
            results[name] = {
                "runner_selector": runner_selector,
                "class_mode": None,
                "match": False,
                "error": "class not loadable (static import failed)",
            }
            continue

        class_mode = getattr(cls, "mode", None)
        class_name_attr = getattr(cls, "name", None)
        match = (class_mode == expected_class_mode and class_name_attr == name)
        results[name] = {
            "runner_selector": runner_selector,
            "class_mode": class_mode or "(not found)",
            "match": match,
            "error": None if match else (
                f"expected mode={expected_class_mode!r} name={name!r}, "
                f"got mode={class_mode!r} name={class_name_attr!r}"
            ),
        }

    return results


def verify_friction_patch_works() -> Dict[str, object]:
    """Friction Mode A vs B で実際に friction value が変わることを verify。

    R6 revision: Phase 3 BT 着手前の必須 smoke test。
    `patch_friction_model()` が `_SESSION_MULTIPLIER` を上書きするだけでは
    不十分で、`friction_for()` 関数が実際に異なる値を返すかどうかを確認。

    Returns:
        {"passed": bool, "mode_a_tokyo": float, "mode_b_tokyo": float,
         "diff": float, "error": str | None}
    """
    try:
        from modules.friction_model_v2 import friction_for
    except ImportError as e:
        return {"passed": False, "error": f"cannot import friction_for: {e}"}

    # Mode A 適用
    with patch_friction_model(FRICTION_MODE_A):
        try:
            result_a = friction_for("USD_JPY", mode="DT", session="Tokyo")
            mode_a_tokyo = float(result_a.get("adjusted_rt_pips", float("nan")))
        except Exception as e:
            return {"passed": False, "error": f"Mode A friction_for failed: {e}"}

    # Mode B 適用
    with patch_friction_model(FRICTION_MODE_B):
        try:
            result_b = friction_for("USD_JPY", mode="DT", session="Tokyo")
            mode_b_tokyo = float(result_b.get("adjusted_rt_pips", float("nan")))
        except Exception as e:
            return {"passed": False, "error": f"Mode B friction_for failed: {e}"}

    diff = mode_a_tokyo - mode_b_tokyo
    # Mode A Tokyo=1.45, Mode B Tokyo=0.80 → 約 1.81× 差
    expected_min_diff = 0.5  # USD_JPY 2.14pip × (1.45-0.80) ≈ 1.39pip 差期待

    passed = abs(diff) >= expected_min_diff and not math.isnan(diff)
    return {
        "passed": passed,
        "mode_a_tokyo": mode_a_tokyo,
        "mode_b_tokyo": mode_b_tokyo,
        "diff": diff,
        "expected_min_diff": expected_min_diff,
        "error": None if passed else f"insufficient diff: {diff:.4f} < {expected_min_diff}",
    }


# ─────────────────────────────────────────────────────────────────────────
# Section 6: CLI entry (dry-run)
# ─────────────────────────────────────────────────────────────────────────

def _print_summary() -> None:
    """Configuration の概要を print。dry-run で interface 確認用。"""
    print(f"=== Phase 3 BT Pre-reg LOCK Configuration ===")
    print(f"Pre-reg LOCK commit: {PRE_REG_COMMIT}")
    print(f"K (strategy universe): {K}")
    print(f"  PHASE3_STRATEGIES: {list(PHASE3_STRATEGIES)}")
    print(f"  MISSING (skip): {sorted(MISSING_STRATEGIES)}")
    print(f"ALPHA_BONFERRONI: {ALPHA_BONFERRONI:.6f} (= 0.05/{K})")
    print(f"FDR_Q: {FDR_Q}")
    print(f"WFA Anchored:")
    print(f"  IS:  {WFA_ANCHORED_IS_START.date()} - {WFA_ANCHORED_IS_END.date()}")
    print(f"  OOS: {WFA_ANCHORED_OOS_START.date()} - {WFA_ANCHORED_OOS_END.date()}")
    print(f"WFA Rolling: IS={WFA_ROLLING_IS_MONTHS}m / OOS={WFA_ROLLING_OOS_MONTHS}m / step={WFA_ROLLING_STEP_MONTHS}m")
    print(f"HOLDOUT_START: {HOLDOUT_START.date()}")
    print(f"\nFRICTION_MODE_A: {FRICTION_MODE_A}")
    print(f"FRICTION_MODE_B: {FRICTION_MODE_B}")
    print(f"\n=== Strategy load test ===")
    for name in PHASE3_STRATEGIES:
        h = load_strategy(name)
        status = "LOADED" if h else "SKIP (missing)"
        print(f"  {name}: {status}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--dry-run":
        _print_summary()
    else:
        print("Usage: python3 tools/phase3_bt.py --dry-run")
        sys.exit(1)
