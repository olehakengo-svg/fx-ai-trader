"""
Statistical Utilities — 統計的検定・リスク指標・Kelly推定・MAFE分析
═══════════════════════════════════════════════════════════════════

提供機能:
  1. 二項検定 (WR有意性)
  2. ベイズ事後分布 (WR推定)
  3. Bootstrap信頼区間 (EV)
  4. Sortino / Calmar / Profit Factor
  5. Kelly Criterion
  6. Risk of Ruin
  7. MAFE分布分析 (SL/TP最適化)
  8. 指数減衰ウェイト (Recency weighting)

設計方針:
  - scipy 非依存 (純Python + math)
  - 全関数が dict を返す (JSON シリアライズ可能)
  - N不足時は insufficient=True を返し、呼び出し側が判断
"""
import math
import random
from typing import List, Dict, Optional, Tuple


# ═══════════════════════════════════════════════
#  1. 統計的有意性検定
# ═══════════════════════════════════════════════

def binomial_test_wr(wins: int, n: int, null_wr: float = 0.45) -> dict:
    """
    片側二項検定: H0: WR <= null_wr, H1: WR > null_wr
    N>=20: 正規近似(連続性補正付き), N<20: 正確二項

    Returns:
      p_value, significant (α=0.10), observed_wr, n
    """
    if n == 0:
        return {"p_value": 1.0, "significant": False, "observed_wr": 0.0,
                "null_wr": null_wr, "n": 0}

    observed_wr = wins / n

    if n < 20:
        p_value = sum(_binom_pmf(k, n, null_wr) for k in range(wins, n + 1))
    else:
        mu = n * null_wr
        sigma = math.sqrt(n * null_wr * (1 - null_wr))
        if sigma == 0:
            return {"p_value": 0.0 if wins > mu else 1.0,
                    "significant": wins > mu,
                    "observed_wr": round(observed_wr, 4),
                    "null_wr": null_wr, "n": n}
        z = (wins - 0.5 - mu) / sigma
        p_value = 1 - _normal_cdf(z)

    return {
        "p_value": round(p_value, 4),
        "significant": p_value < 0.10,
        "observed_wr": round(observed_wr, 4),
        "null_wr": null_wr,
        "n": n,
    }


def bayesian_wr_posterior(wins: int, n: int,
                          prior_alpha: float = 1.0,
                          prior_beta: float = 1.0) -> dict:
    """
    Beta-Binomial モデルによるWRベイズ事後分布。
    Default prior: Beta(1,1) = 無情報事前分布

    Returns:
      posterior_mean, posterior_mode, ci_90, p_wr_above_45, p_wr_above_50
    """
    post_a = prior_alpha + wins
    post_b = prior_beta + (n - wins)

    mean = post_a / (post_a + post_b)
    mode = ((post_a - 1) / (post_a + post_b - 2)
            if (post_a > 1 and post_b > 1) else mean)

    ci_low = _beta_quantile(0.05, post_a, post_b)
    ci_high = _beta_quantile(0.95, post_a, post_b)

    p_above_45 = 1 - _beta_cdf(0.45, post_a, post_b)
    p_above_50 = 1 - _beta_cdf(0.50, post_a, post_b)

    return {
        "posterior_mean": round(mean, 4),
        "posterior_mode": round(mode, 4),
        "ci_90": (round(ci_low, 4), round(ci_high, 4)),
        "p_wr_above_45": round(p_above_45, 4),
        "p_wr_above_50": round(p_above_50, 4),
        "n": n, "wins": wins,
    }


def bootstrap_ev_ci(pnl_list: List[float], n_boot: int = 5000,
                     ci: float = 0.90) -> dict:
    """
    Bootstrap パーセンタイル法によるEV信頼区間。

    Returns:
      ev_mean, ci_low, ci_high, ev_significantly_positive
    """
    n = len(pnl_list)
    if n < 5:
        ev = sum(pnl_list) / max(n, 1)
        return {"ev_mean": round(ev, 4), "ci_low": None, "ci_high": None,
                "n": n, "insufficient": True, "ev_significantly_positive": False}

    boot_means = []
    for _ in range(n_boot):
        sample = random.choices(pnl_list, k=n)
        boot_means.append(sum(sample) / n)

    boot_means.sort()
    alpha = (1 - ci) / 2
    ci_low = boot_means[int(alpha * n_boot)]
    ci_high = boot_means[int((1 - alpha) * n_boot)]

    return {
        "ev_mean": round(sum(pnl_list) / n, 4),
        "ci_low": round(ci_low, 4),
        "ci_high": round(ci_high, 4),
        "ci_level": ci,
        "n": n,
        "insufficient": False,
        "ev_significantly_positive": ci_low > 0,
    }


# ═══════════════════════════════════════════════
#  2. リスク調整済みパフォーマンス指標
# ═══════════════════════════════════════════════

def sortino_ratio(returns: List[float], target: float = 0.0,
                  annualize: int = 252) -> float:
    """
    Sortino Ratio = (mean - target) / downside_std * sqrt(annualize)
    下方偏差のみ考慮（上振れはペナルティにしない）
    """
    if len(returns) < 2:
        return 0.0
    mean_r = sum(returns) / len(returns)
    downside_sq = [min(0, r - target) ** 2 for r in returns]
    dd = math.sqrt(sum(downside_sq) / len(downside_sq))
    if dd == 0:
        return 0.0
    return round((mean_r - target) / dd * math.sqrt(annualize), 3)


def calmar_ratio(returns: List[float], annualize: int = 252) -> float:
    """
    Calmar Ratio = annualized_return / max_drawdown
    テールリスク対比のリターン効率
    """
    if len(returns) < 2:
        return 0.0
    eq, peak, max_dd = 0.0, 0.0, 0.0
    for r in returns:
        eq += r
        if eq > peak:
            peak = eq
        dd = peak - eq
        if dd > max_dd:
            max_dd = dd
    if max_dd == 0:
        return 0.0
    mean_r = sum(returns) / len(returns)
    return round(mean_r * annualize / max_dd, 3)


def profit_factor(returns: List[float]) -> float:
    """Profit Factor = 総利益 / 総損失"""
    gross_profit = sum(r for r in returns if r > 0)
    gross_loss = abs(sum(r for r in returns if r < 0))
    if gross_loss == 0:
        return float('inf') if gross_profit > 0 else 0.0
    return round(gross_profit / gross_loss, 3)


# ═══════════════════════════════════════════════
#  3. Kelly Criterion & Risk of Ruin
# ═══════════════════════════════════════════════

def kelly_criterion(win_rate: float, avg_win: float,
                    avg_loss: float) -> dict:
    """
    Kelly Criterion: f* = (p*b - q) / b
    p=WR, q=1-p, b=avg_win/avg_loss

    Returns: full_kelly, half_kelly, edge, odds_ratio
    """
    if avg_loss == 0 or win_rate <= 0 or win_rate >= 1:
        return {"full_kelly": 0.0, "half_kelly": 0.0,
                "edge": 0.0, "odds_ratio": 0.0, "win_rate": win_rate}

    b = avg_win / avg_loss
    p = win_rate
    q = 1 - p
    full_kelly = (p * b - q) / b
    edge = p * b - q

    return {
        "full_kelly": round(max(0, full_kelly), 4),
        "half_kelly": round(max(0, full_kelly / 2), 4),
        "edge": round(edge, 4),
        "odds_ratio": round(b, 4),
        "win_rate": round(p, 4),
    }


def risk_of_ruin(win_rate: float, avg_win: float, avg_loss: float,
                 risk_per_trade: float = 0.02,
                 ruin_level: float = 0.50) -> float:
    """
    近似 Risk of Ruin:
      RoR = ((1-edge)/(1+edge))^(ruin_level/risk_per_trade)
    edge = WR*(avg_win/avg_loss) - (1-WR)

    ruin_level=0.50 → 資金50%喪失を「破産」と定義
    """
    if avg_loss == 0:
        return 0.0
    edge = win_rate * (avg_win / avg_loss) - (1 - win_rate)
    if edge <= 0:
        return 1.0
    ratio = (1 - edge) / (1 + edge)
    if ratio >= 1:
        return 1.0
    n_units = ruin_level / max(risk_per_trade, 0.001)
    ror = ratio ** n_units
    return round(min(1.0, max(0.0, ror)), 6)


# ═══════════════════════════════════════════════
#  4. MAFE 分布分析
# ═══════════════════════════════════════════════

def analyze_mafe(trades: List[dict]) -> dict:
    """
    MAE/MFE 分布分析 → SL/TP最適化の推奨値を算出。

    期待する trade dict keys:
      mafe_adverse (float), mafe_favorable (float),
      pnl_pips (float), outcome ("WIN"/"LOSS")

    Returns:
      mae/mfe 統計, SL/TP推奨値, TP効率
    """
    if len(trades) < 10:
        return {"insufficient": True, "n": len(trades)}

    mae_list = sorted(abs(t.get("mafe_adverse", 0))
                      for t in trades
                      if t.get("mafe_adverse") is not None)
    mfe_list = sorted(abs(t.get("mafe_favorable", 0))
                      for t in trades
                      if t.get("mafe_favorable") is not None)

    if len(mae_list) < 5 or len(mfe_list) < 5:
        return {"insufficient": True, "n": len(trades),
                "mae_n": len(mae_list), "mfe_n": len(mfe_list)}

    def pctl(lst, p):
        idx = min(int(len(lst) * p), len(lst) - 1)
        return lst[idx]

    # WIN / LOSS 分割
    win_mfe = sorted(abs(t.get("mafe_favorable", 0))
                     for t in trades
                     if t.get("outcome") == "WIN"
                     and t.get("mafe_favorable") is not None)
    win_pnl = [t.get("pnl_pips", 0) for t in trades
               if t.get("outcome") == "WIN"]

    result = {
        "insufficient": False,
        "n": len(trades),
        "mae": {
            "mean": round(sum(mae_list) / len(mae_list), 4),
            "median": round(pctl(mae_list, 0.50), 4),
            "p25": round(pctl(mae_list, 0.25), 4),
            "p75": round(pctl(mae_list, 0.75), 4),
            "p90": round(pctl(mae_list, 0.90), 4),
        },
        "mfe": {
            "mean": round(sum(mfe_list) / len(mfe_list), 4),
            "median": round(pctl(mfe_list, 0.50), 4),
            "p25": round(pctl(mfe_list, 0.25), 4),
            "p75": round(pctl(mfe_list, 0.75), 4),
            "p90": round(pctl(mfe_list, 0.90), 4),
        },
        "sl_recommendation": {
            "value": round(pctl(mae_list, 0.75) * 1.1, 4),
            "note": "MAE P75 + 10% buffer — 75%のトレードでSL未到達",
        },
        "tp_recommendation": {
            "value": round(pctl(mfe_list, 0.50), 4),
            "note": "MFE P50 — 50%のトレードがこの水準に到達",
        },
    }

    # TP効率: 実現利益 / 利用可能MFE
    if win_mfe and win_pnl:
        avg_captured = sum(win_pnl) / len(win_pnl)
        avg_available = sum(win_mfe) / len(win_mfe)
        if avg_available > 0:
            result["tp_efficiency"] = round(avg_captured / avg_available, 4)

    return result


# ═══════════════════════════════════════════════
#  5. 指数減衰ウェイト
# ═══════════════════════════════════════════════

def exponential_decay_weights(n: int, half_life: int = 30) -> List[float]:
    """
    n個のトレードに指数減衰ウェイトを付与。
    最新トレード(index=n-1)のウェイト=1.0, 古いほど減衰。
    half_life: ウェイトが0.5になるトレード数 (default: 30トレード前)

    Returns: 正規化済みウェイトリスト (sum=1.0)
    """
    if n <= 0:
        return []
    lam = math.log(2) / max(half_life, 1)
    raw = [math.exp(-lam * (n - 1 - i)) for i in range(n)]
    total = sum(raw)
    if total == 0:
        return [1.0 / n] * n
    return [w / total for w in raw]


def weighted_stats(values: List[float], weights: List[float]) -> dict:
    """加重平均・加重分散を計算"""
    if not values or not weights or len(values) != len(weights):
        return {"mean": 0.0, "std": 0.0}
    w_sum = sum(weights)
    if w_sum == 0:
        return {"mean": 0.0, "std": 0.0}
    w_mean = sum(v * w for v, w in zip(values, weights)) / w_sum
    w_var = sum(w * (v - w_mean) ** 2 for v, w in zip(values, weights)) / w_sum
    return {"mean": round(w_mean, 4), "std": round(math.sqrt(w_var), 4)}


# ═══════════════════════════════════════════════
#  Internal math helpers (scipy 非依存)
# ═══════════════════════════════════════════════

def _binom_pmf(k: int, n: int, p: float) -> float:
    if p == 0:
        return 1.0 if k == 0 else 0.0
    if p == 1:
        return 1.0 if k == n else 0.0
    log_pmf = _log_comb(n, k) + k * math.log(p) + (n - k) * math.log(1 - p)
    return math.exp(log_pmf)


def _log_comb(n: int, k: int) -> float:
    return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)


def _normal_cdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def _beta_cdf(x: float, a: float, b: float, steps: int = 200) -> float:
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    h = x / steps
    total = 0.0
    for i in range(steps):
        t0 = i * h
        t1 = (i + 1) * h
        f0 = (t0 ** (a - 1) * (1 - t0) ** (b - 1)) if (t0 > 0 or a >= 1) else 0
        f1 = (t1 ** (a - 1) * (1 - t1) ** (b - 1)) if (t1 < 1 or b >= 1) else 0
        total += (f0 + f1) * h / 2
    beta_b = math.exp(math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b))
    return min(1.0, total / beta_b)


def _beta_quantile(p: float, a: float, b: float, tol: float = 1e-4) -> float:
    low, high = 0.0, 1.0
    for _ in range(60):
        mid = (low + high) / 2
        if _beta_cdf(mid, a, b) < p:
            low = mid
        else:
            high = mid
        if high - low < tol:
            break
    return (low + high) / 2


# ═══════════════════════════════════════════════
#  9. Deflated Sharpe Ratio (DSR)
# ═══════════════════════════════════════════════

def deflated_sharpe_ratio(
    sharpe_observed: float,
    n_trades: int,
    n_trials: int,
    skewness: float = 0.0,
    kurtosis: float = 3.0,
) -> dict:
    """
    Deflated Sharpe Ratio — Bailey & Lopez de Prado (2014)

    多重検定補正済みSharpe Ratio。N_trials個の戦略をテストした場合、
    最良の観測Sharpeが偶然である確率を補正する。

    Args:
        sharpe_observed: 観測されたSharpe Ratio (annualized)
        n_trades: バックテストのトレード数
        n_trials: テストした戦略の総数（多重検定のN）
        skewness: リターン分布の歪度（0=正規分布）
        kurtosis: リターン分布の尖度（3=正規分布）

    Returns:
        dsr: Deflated Sharpe Ratio（0-1、1に近いほど信頼性が高い）
        sharpe_threshold: n_trialsに対する最低必要Sharpe
        is_significant: DSR > 0.95（5%有意水準）
        haircut: 観測Sharpeからの削減率 (%)

    学術根拠:
        Bailey, Borwein, Lopez de Prado & Zhu (2014)
        "Pseudo-Mathematics and Financial Charlatanism"
        AMS Notices, 61(5), 458-471.

        Bailey & Lopez de Prado (2014)
        "The Deflated Sharpe Ratio: Correcting for Selection Bias,
         Backtest Overfitting, and Non-Normality"
        Journal of Portfolio Management, 40(5), 94-107.
    """
    if n_trades < 2 or n_trials < 1 or sharpe_observed <= 0:
        return {
            "dsr": 0.0,
            "sharpe_threshold": 0.0,
            "sharpe_observed": sharpe_observed,
            "is_significant": False,
            "haircut": 100.0,
            "n_trials": n_trials,
            "n_trades": n_trades,
        }

    # ── Expected maximum Sharpe under null (all strategies have zero edge) ──
    # E[max(SR)] ≈ sqrt(2 * ln(N_trials)) for N_trials independent strategies
    # With skewness/kurtosis correction:
    #   SR* = sqrt(V) * ((1 - gamma) * z_alpha + gamma * z_alpha^2 - 1) / sqrt(T-1))
    # Simplified: SR_threshold = sqrt(2 * ln(N_trials)) * (1 / sqrt(n_trades))
    # This is the Sharpe you'd expect the best strategy to achieve BY CHANCE

    import math

    _ln_trials = math.log(max(n_trials, 2))

    # Euler-Mascheroni constant approximation for expected max of N standard normals
    _euler_gamma = 0.5772156649
    _z_expected_max = math.sqrt(2 * _ln_trials) - (_euler_gamma + math.log(math.pi)) / (2 * math.sqrt(2 * _ln_trials))

    # Sharpe threshold: expected max Sharpe under null hypothesis
    # Annualized Sharpe with T trades: SR ~ N(0, 1/sqrt(T)) under null
    sharpe_threshold = _z_expected_max / math.sqrt(max(n_trades - 1, 1))

    # ── Skewness/Kurtosis correction ──
    # SE(SR) = sqrt((1 - skew*SR + (kurtosis-1)/4 * SR^2) / (T-1))
    _sr = sharpe_observed
    _se_sr = math.sqrt(
        max(1 - skewness * _sr + (kurtosis - 1) / 4 * _sr ** 2, 0.01)
        / max(n_trades - 1, 1)
    )

    # ── DSR = Prob(SR_observed > SR_threshold | H0) ──
    # Using standard normal CDF approximation
    _z_score = (_sr - sharpe_threshold) / max(_se_sr, 0.0001)

    # Normal CDF approximation (Abramowitz & Stegun)
    def _norm_cdf(x):
        if x < -6:
            return 0.0
        if x > 6:
            return 1.0
        t = 1 / (1 + 0.2316419 * abs(x))
        d = 0.3989422804014327  # 1/sqrt(2*pi)
        p = d * math.exp(-x * x / 2) * (
            t * (0.319381530 + t * (-0.356563782 + t * (1.781477937 +
            t * (-1.821255978 + t * 1.330274429))))
        )
        return 1 - p if x > 0 else p

    dsr = _norm_cdf(_z_score)

    # Haircut: how much of observed Sharpe is explained by luck
    haircut = max(0, (1 - sharpe_threshold / max(_sr, 0.0001))) * 100
    if sharpe_threshold >= _sr:
        haircut = 0.0  # threshold exceeds observed → 100% luck

    return {
        "dsr": round(dsr, 4),
        "sharpe_threshold": round(sharpe_threshold, 4),
        "sharpe_observed": round(sharpe_observed, 4),
        "is_significant": dsr > 0.95,
        "haircut": round(haircut, 1),
        "n_trials": n_trials,
        "n_trades": n_trades,
        "z_score": round(_z_score, 3),
    }
