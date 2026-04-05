"""
Turtle Soup (Liquidity Grab Reversal) — 流動性狩り逆張り

学術的根拠:
  - Connors & Raschke (1995): "Street Smarts" — Turtle Soup 戦略の原典
  - Osler (2003): Stop-loss clustering at round numbers and swing extremes
  - Kyle (1985): Informed traders exploit predictable stop-loss placement
  - Lo & MacKinlay (1988): 短期リバーサル効果 — stop run 後の価格修正

戦略コンセプト:
  個人投資家のSLが集中するMajor Fractal High/Lowの少し外側まで
  大口がわざと価格を押す（Liquidity Grab / Stop Hunt）。
  SL注文の流動性を食い尽くした後、価格は素早くフラクタル内に回帰する。
  この「ストップ狩り→回帰」パターンを検出し、逆張りエントリー。

  ORB Trapとの構造的差異:
    ORB Trap = 固定時間レンジ（セッション開始30分）のフェイクアウト
    Turtle Soup = 動的なフラクタルHigh/Low（直近数日間の極値）のフェイクアウト
    → より強い流動性クラスター（SL集中帯）を狙うため、構造的エッジが高い

エントリーロジック（3段階検出）:

  ■ STEP1: Major Fractal High/Low 検出
    Williams Fractal (n=FRACTAL_N) で直近 FRACTAL_LOOKBACK 本のHigh/Lowを検出。
    複数フラクタルの集中（±CLUSTER_ATR_MULT × ATR以内）でクラスター化。
    タッチ回数2+のクラスター = Major Fractal（SL集中が濃い水準）。

  ■ STEP2: Sweep（流動性グラブ）検出
    過去 SWEEP_LOOKBACK 本以内で、HighまたはLowがMajor Fractal水準を
    SWEEP_MARGIN_ATR × ATR 以上超過（ヒゲ or 実体でブレイク）。
    大口介入証拠: sweep足の bar_range / ATR ≥ VOL_RATIO_MIN（ボリュームプロキシ）。

  ■ STEP3: Reclaim（回帰確認）— 現在足
    Close（実体）がMajor Fractal水準の内側に回帰。
    前足のCloseは外側（fresh return = 1回限りのトリガー保証）。
    確認: 現在足の実体方向がリバーサル方向（BUY時は陽線、SELL時は陰線）。

  SL: sweep extreme（突き抜けた最大値/最小値）± ATR × SL_ATR_BUFFER
  TP: 次のMajor Fractal水準（対面）、または ATR × TP_ATR_MULT
"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from typing import Optional
import numpy as np


class TurtleSoup(StrategyBase):
    name = "turtle_soup"
    mode = "daytrade"
    enabled = True

    # ══════════════════════════════════════════════════
    # パラメータ定数
    # ══════════════════════════════════════════════════

    # ── Fractal SR 検出 ──
    FRACTAL_N = 5               # Williams Fractal: 両側5本 (11バー窓 = 2.75H on 15m)
    FRACTAL_LOOKBACK = 120      # ルックバック120本 (15m × 120 = 30H ≈ 直近2営業日)
    CLUSTER_ATR_MULT = 0.4      # ±0.4ATR以内のフラクタルをクラスター化
    MIN_CLUSTER_TOUCHES = 2     # クラスター内タッチ2回以上 = Major Fractal

    # ── Sweep 検出 ──
    SWEEP_LOOKBACK = 6          # sweep検出: 最大6本前まで (= 1.5H)
    SWEEP_MARGIN_ATR = 0.05     # sweep: フラクタルから ≥ 0.05ATR 超過
    VOL_RATIO_MIN = 1.2         # sweep足の bar_range/ATR ≥ 1.2 (大口介入証拠)

    # ── Reclaim 確認 ──
    RECLAIM_BODY_CONFIRM = True  # 現在足の実体方向がリバーサル方向

    # ── ADXフィルター ──
    ADX_MAX = 40                # ADX > 40 は強トレンド → 逆張り危険
    ADX_MIN = 12                # ADX < 12 は無風 → sweep自体がノイズ

    # ── SL/TP ──
    SL_ATR_BUFFER = 0.3         # SL = sweep extreme ± ATR×0.3
    TP_ATR_MULT = 2.5           # TP fallback = ATR × 2.5
    MIN_RR = 1.5                # 最低リスクリワード比

    # ── 時間帯フィルター ──
    ACTIVE_HOURS_START = 6      # UTC 06:00 以降
    ACTIVE_HOURS_END = 20       # UTC 20:00 まで (NY後半は流動性低下)

    # ── 金曜フィルター ──
    FRIDAY_BLOCK_HOUR = 16      # 金曜 UTC 16:00 以降ブロック

    # ══════════════════════════════════════════════════
    # ペアフィルター (BT 55d検証結果に基づく)
    # GBP/USD: 30t WR=66.7% EV=+0.467 → 採用 (BUY/SELL均等)
    # XAU/USD: 27t WR=59.3% EV=+0.304 → 採用 (BUY/SELL均等)
    # EUR/GBP: 27t WR=51.9% EV=+0.138 → SELL-only (SELL WR=80%, BUY WR=35%)
    # USD/JPY: 28t WR=42.9% EV=-0.057 → 除外
    # EUR/USD: 9t WR=33.3% EV=-0.267 → 除外
    # ══════════════════════════════════════════════════
    ALLOWED_PAIRS = {
        "GBPUSD", "XAUUSD", "EURGBP",
    }
    # EUR/GBP: BUY WR=35% → SELL-onlyフィルター
    SELL_ONLY_PAIRS = {"EURGBP"}

    def _normalize_symbol(self, symbol: str) -> str:
        return symbol.upper().replace("=X", "").replace("/", "").replace("_", "")

    # ══════════════════════════════════════════════════
    # Fractal 検出（SBRから流用＋Major判定）
    # ══════════════════════════════════════════════════

    def _find_fractal_levels(self, df, n: int, lookback: int):
        """Williams Fractal でフラクタル高値/安値を検出。

        Returns:
            (fractal_highs, fractal_lows): list of (price, bar_index)
        """
        _start = max(0, len(df) - lookback)
        _end = len(df) - n  # 最新n本はフラクタル未確定
        highs = df["High"].values
        lows = df["Low"].values

        frac_highs = []
        frac_lows = []

        for i in range(_start + n, _end):
            _h = highs[i]
            if all(_h > highs[j] for j in range(i - n, i)) and \
               all(_h > highs[j] for j in range(i + 1, i + n + 1)):
                frac_highs.append((float(_h), i))

            _l = lows[i]
            if all(_l < lows[j] for j in range(i - n, i)) and \
               all(_l < lows[j] for j in range(i + 1, i + n + 1)):
                frac_lows.append((float(_l), i))

        return frac_highs, frac_lows

    def _cluster_levels(self, levels: list, atr: float):
        """近接フラクタルをクラスター化。

        Args:
            levels: list of (price, bar_index) tuples

        Returns:
            list of (cluster_avg_price, touch_count) sorted by touch_count desc
        """
        if not levels or atr <= 0:
            return []

        _threshold = atr * self.CLUSTER_ATR_MULT
        prices = sorted(levels, key=lambda x: x[0])
        clusters = []
        _current = [prices[0]]

        for i in range(1, len(prices)):
            if prices[i][0] - _current[-1][0] <= _threshold:
                _current.append(prices[i])
            else:
                if len(_current) >= self.MIN_CLUSTER_TOUCHES:
                    _avg = sum(p for p, _ in _current) / len(_current)
                    clusters.append((_avg, len(_current)))
                _current = [prices[i]]

        if len(_current) >= self.MIN_CLUSTER_TOUCHES:
            _avg = sum(p for p, _ in _current) / len(_current)
            clusters.append((_avg, len(_current)))

        clusters.sort(key=lambda x: x[1], reverse=True)
        return clusters

    # ══════════════════════════════════════════════════
    # Sweep + Reclaim 検出
    # ══════════════════════════════════════════════════

    def _detect_sweep_and_reclaim(self, df, level: float, direction: str,
                                  atr: float):
        """Sweep（流動性グラブ）+ Reclaim（回帰）を検出。

        Args:
            df: DataFrame
            level: Major Fractalの価格水準
            direction: "UP" (高値sweep → SELL) or "DOWN" (安値sweep → BUY)
            atr: ATR(14)

        Returns:
            dict with sweep info, or None
        """
        if len(df) < self.SWEEP_LOOKBACK + 2:
            return None

        _cur_idx = len(df) - 1
        _prev_idx = _cur_idx - 1
        _sweep_margin = atr * self.SWEEP_MARGIN_ATR

        cur_close = float(df["Close"].iloc[_cur_idx])
        prev_close = float(df["Close"].iloc[_prev_idx])
        cur_open = float(df["Open"].iloc[_cur_idx])

        # ── Sweep検出: 過去SWEEP_LOOKBACK本以内でlevelを超過 ──
        _sweep_extreme = None
        _sweep_bar_idx = None
        _sweep_found = False

        for lookback in range(1, self.SWEEP_LOOKBACK + 1):
            _idx = _cur_idx - lookback
            if _idx < 0:
                break

            _bar_h = float(df["High"].iloc[_idx])
            _bar_l = float(df["Low"].iloc[_idx])
            _bar_range = _bar_h - _bar_l

            if direction == "UP":
                # 高値sweepを検出: Highがlevelを超過
                if _bar_h > level + _sweep_margin:
                    # ボリュームプロキシ: bar_range/ATR チェック
                    if atr > 0 and _bar_range / atr >= self.VOL_RATIO_MIN:
                        if _sweep_extreme is None or _bar_h > _sweep_extreme:
                            _sweep_extreme = _bar_h
                            _sweep_bar_idx = _idx
                            _sweep_found = True
            else:  # DOWN
                # 安値sweepを検出: Lowがlevelを下回る
                if _bar_l < level - _sweep_margin:
                    if atr > 0 and _bar_range / atr >= self.VOL_RATIO_MIN:
                        if _sweep_extreme is None or _bar_l < _sweep_extreme:
                            _sweep_extreme = _bar_l
                            _sweep_bar_idx = _idx
                            _sweep_found = True

        if not _sweep_found:
            return None

        # ── Reclaim検出: 現在足のCloseがlevel内側に回帰 ──
        if direction == "UP":
            # 高値sweep後: Close < level (内側回帰) & 前足Close > level (外側)
            _reclaimed = cur_close < level and prev_close >= level
            # 実体方向確認: 陰線（売り圧力）
            _body_confirm = cur_close < cur_open if self.RECLAIM_BODY_CONFIRM else True
        else:  # DOWN
            # 安値sweep後: Close > level (内側回帰) & 前足Close <= level (外側)
            _reclaimed = cur_close > level and prev_close <= level
            # 実体方向確認: 陽線（買い圧力）
            _body_confirm = cur_close > cur_open if self.RECLAIM_BODY_CONFIRM else True

        if not _reclaimed or not _body_confirm:
            return None

        return {
            "sweep_extreme": _sweep_extreme,
            "sweep_bar_idx": _sweep_bar_idx,
            "level": level,
            "direction": direction,
        }

    # ══════════════════════════════════════════════════
    # メイン評価
    # ══════════════════════════════════════════════════

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        # ── ペアフィルター ──
        _sym = self._normalize_symbol(ctx.symbol)
        if _sym not in self.ALLOWED_PAIRS:
            return None

        # ── DataFrame十分性 ──
        _min_bars = self.FRACTAL_LOOKBACK + self.FRACTAL_N + 2
        if ctx.df is None or len(ctx.df) < _min_bars:
            return None

        # ── 時間帯フィルター ──
        if ctx.hour_utc < self.ACTIVE_HOURS_START or ctx.hour_utc >= self.ACTIVE_HOURS_END:
            return None

        # ── 金曜フィルター ──
        if ctx.is_friday and ctx.hour_utc >= self.FRIDAY_BLOCK_HOUR:
            return None

        # ── ADXフィルター（レンジ/強トレンド除外） ──
        if ctx.adx < self.ADX_MIN or ctx.adx > self.ADX_MAX:
            return None

        # ═══════════════════════════════════════════════════
        # STEP 1: Major Fractal 検出
        # ═══════════════════════════════════════════════════
        _frac_highs, _frac_lows = self._find_fractal_levels(
            ctx.df, n=self.FRACTAL_N, lookback=self.FRACTAL_LOOKBACK
        )

        _major_highs = self._cluster_levels(_frac_highs, ctx.atr)
        _major_lows = self._cluster_levels(_frac_lows, ctx.atr)

        if not _major_highs and not _major_lows:
            return None

        # ═══════════════════════════════════════════════════
        # STEP 2 & 3: 各Major Fractalに対してSweep + Reclaimを検出
        # ═══════════════════════════════════════════════════
        _best_candidate = None
        _best_touches = 0

        # -- 高値sweep → SELL --
        for _level, _touches in _major_highs:
            # 水準が現在価格に近いものだけ（±5ATR以内）
            if abs(_level - ctx.entry) > ctx.atr * 5:
                continue

            result = self._detect_sweep_and_reclaim(
                ctx.df, _level, "UP", ctx.atr
            )
            if result and _touches > _best_touches:
                _best_candidate = result
                _best_candidate["signal"] = "SELL"
                _best_candidate["touches"] = _touches
                _best_touches = _touches

        # -- 安値sweep → BUY --
        for _level, _touches in _major_lows:
            if abs(_level - ctx.entry) > ctx.atr * 5:
                continue

            result = self._detect_sweep_and_reclaim(
                ctx.df, _level, "DOWN", ctx.atr
            )
            if result and _touches > _best_touches:
                _best_candidate = result
                _best_candidate["signal"] = "BUY"
                _best_candidate["touches"] = _touches
                _best_touches = _touches

        if _best_candidate is None:
            return None

        # ── SELL-onlyペアフィルター ──
        if _sym in self.SELL_ONLY_PAIRS and _best_candidate["signal"] != "SELL":
            return None

        # ═══════════════════════════════════════════════════
        # STEP 4: SL/TP 計算
        # ═══════════════════════════════════════════════════
        signal = _best_candidate["signal"]
        _extreme = _best_candidate["sweep_extreme"]
        _level = _best_candidate["level"]
        _touches = _best_candidate["touches"]
        _is_buy = signal == "BUY"

        # SL: sweep extreme の外側 + バッファ
        if _is_buy:
            sl = _extreme - ctx.atr * self.SL_ATR_BUFFER
        else:
            sl = _extreme + ctx.atr * self.SL_ATR_BUFFER

        # TP: 対面のMajor Fractal、なければATRベース
        _tp_target = None
        if _is_buy and _major_highs:
            # 最も近い上方Major Fractal High
            _above = [lv for lv, _ in _major_highs if lv > ctx.entry + ctx.atr * 0.5]
            if _above:
                _tp_target = min(_above)
        elif not _is_buy and _major_lows:
            # 最も近い下方Major Fractal Low
            _below = [lv for lv, _ in _major_lows if lv < ctx.entry - ctx.atr * 0.5]
            if _below:
                _tp_target = max(_below)

        # TP fallback: ATRベース
        if _tp_target is None:
            _tp_target = ctx.entry + ctx.atr * self.TP_ATR_MULT * (1 if _is_buy else -1)

        tp = _tp_target

        # ── RR チェック ──
        _sl_dist = abs(ctx.entry - sl)
        _tp_dist = abs(tp - ctx.entry)

        if _sl_dist <= 0:
            return None

        # MIN_RR未達の場合TPを拡張
        if _tp_dist / _sl_dist < self.MIN_RR:
            _tp_dist = _sl_dist * self.MIN_RR
            tp = ctx.entry + _tp_dist if _is_buy else ctx.entry - _tp_dist

        _rr = _tp_dist / _sl_dist

        # ── SL方向チェック（BUYならSL < entry, SELLならSL > entry） ──
        if _is_buy and sl >= ctx.entry:
            return None
        if not _is_buy and sl <= ctx.entry:
            return None

        # ═══════════════════════════════════════════════════
        # スコア計算
        # ═══════════════════════════════════════════════════
        _score = 5.0
        # タッチ回数ボーナス（SL集中が濃いほど高信頼）
        if _touches >= 4:
            _score += 2.0
        elif _touches >= 3:
            _score += 1.0

        # RRボーナス
        if _rr >= 2.5:
            _score += 1.0
        elif _rr >= 2.0:
            _score += 0.5

        # ADX中間域（20-30）ボーナス — レンジ崩壊の初動
        if 20 <= ctx.adx <= 30:
            _score += 0.5

        _reasons = [
            f"Turtle Soup: {signal} — Major Fractal {_level:.5f} "
            f"(touches={_touches})",
            f"Sweep extreme={_extreme:.5f}, reclaim confirmed",
            f"RR={_rr:.1f}, ADX={ctx.adx:.1f}",
        ]

        return Candidate(
            signal=signal,
            confidence=min(85, 50 + _touches * 5 + int(_rr * 5)),
            sl=round(sl, 5 if not ctx.is_jpy else 3),
            tp=round(tp, 5 if not ctx.is_jpy else 3),
            reasons=_reasons,
            entry_type=self.name,
            score=_score,
        )
