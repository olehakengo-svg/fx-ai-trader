"""
London Fix Reversal (LFR) — London 4pm Fix後のUSD反転を狙う戦略

学術的根拠:
  - Krohn, Mueller & Whelan (2024, Journal of Finance):
    USDは London 4pm Fix 前に上昇し、Fix後に反転する W-shaped 24h return pattern
  - Melvin & Prins (2015): 月末最終3営業日はFixフローが特に大きく、反転効果が増幅

構造的メカニズム:
  機関投資家のリバランスフロー（ヘッジ需要等）がFix前にUSD需要を生む。
  Fix決定（UTC 15:00-16:00）後に需要消失 → USD反転。
  月末はファンドのリバランスが集中し効果が増幅。

戦略コンセプト:
  - EUR/USD, GBP/USD, USD/JPY対応
  - Pre-fix (UTC 14:30-15:30) でUSD方向を計測
  - Post-fix (UTC 16:00-16:30) で逆方向エントリー
  - 月末3営業日はconfidence boost +10
  - ADX < 30 フィルター（極端なトレンドではFixフロー無効）
  - Post-fix barの反転確認（Close vs Open）
"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from typing import Optional


class LondonFixReversal(StrategyBase):
    name = "london_fix_reversal"
    mode = "daytrade"
    enabled = True

    # ── 対象通貨ペア ──
    _enabled_symbols = {"EURUSD", "GBPUSD", "USDJPY"}

    # ══════════════════════════════════════════════════
    # パラメータ定数
    # ══════════════════════════════════════════════════

    # ── 時間帯 (UTC 通算分) ──
    PREFIX_START     = 870       # UTC 14:30
    PREFIX_END       = 930       # UTC 15:30
    ENTRY_START      = 960       # UTC 16:00
    ENTRY_END        = 990       # UTC 16:30

    # ── Pre-fix動き閾値 ──
    PREFIX_ATR_MULT  = 0.3       # Pre-fixの価格変動 > ATR(15m) × 0.3 で有意とみなす

    # ── SL/TP ──
    SL_ATR_MULT      = 1.0       # SL = ATR(15m, 14) × 1.0
    TP_ATR_MULT      = 1.5       # TP = ATR(15m, 14) × 1.5
    MIN_RR           = 1.2       # 最低リスクリワード比

    # ── フィルター ──
    ADX_MAX          = 30        # ADX < 30 (極端なトレンドではFix効果が弱い)

    # ── 月末ボーナス ──
    MONTH_END_DAYS   = 3         # 月末最終3営業日でconfidenceブースト
    MONTH_END_BONUS  = 10        # confidence加算

    # ── 保持 ──
    MAX_HOLD_BARS    = 4         # 最大4バー (60分 @ 15m)

    # ── Pre-fixバー走査 ──
    PREFIX_SCAN_BARS = 8         # Pre-fix走査のための最大バー数

    # ──────────────────────────────────────────────────
    # ヘルパー
    # ──────────────────────────────────────────────────

    @staticmethod
    def _bar_minutes(bar_dt) -> int:
        """バー時刻 -> UTC 通算分 (0-1439)。取得不可なら -1。"""
        if hasattr(bar_dt, 'hour') and hasattr(bar_dt, 'minute'):
            return bar_dt.hour * 60 + bar_dt.minute
        return -1

    @staticmethod
    def _bar_date(bar_dt):
        """バーの日付部分を返す。取得不可なら None。"""
        if hasattr(bar_dt, 'date') and callable(bar_dt.date):
            return bar_dt.date()
        return None

    def _is_month_end_window(self, bar_dt) -> bool:
        """月末最終3営業日かどうか判定。"""
        try:
            import calendar
            _date = self._bar_date(bar_dt)
            if _date is None:
                return False
            _year = _date.year
            _month = _date.month
            _last_day = calendar.monthrange(_year, _month)[1]
            # 月末から逆算して営業日を数える
            _biz_days = 0
            for d in range(_last_day, 0, -1):
                try:
                    from datetime import date
                    _check = date(_year, _month, d)
                    if _check.weekday() < 5:  # 月-金
                        _biz_days += 1
                        if _check == _date:
                            return _biz_days <= self.MONTH_END_DAYS
                        if _biz_days > self.MONTH_END_DAYS:
                            break
                except ValueError:
                    continue
        except Exception:
            pass
        return False

    def _calc_prefix_move(self, ctx: SignalContext, today) -> Optional[float]:
        """Pre-fix (UTC 14:30-15:30) の価格変動を計算。

        Returns:
            float: 価格変動量 (正=上昇, 負=下落)。計算不可の場合 None。
        """
        df = ctx.df
        if df is None or len(df) < self.PREFIX_SCAN_BARS:
            return None

        _prefix_opens = []
        _prefix_closes = []

        for j in range(min(self.PREFIX_SCAN_BARS, len(df))):
            idx = len(df) - 1 - j
            if idx < 0:
                break
            bdt = df.index[idx]
            bm = self._bar_minutes(bdt)
            if bm < 0:
                continue
            # 当日チェック
            if today is not None:
                bd = self._bar_date(bdt)
                if bd is not None and bd != today:
                    continue
            if self.PREFIX_START <= bm < self.PREFIX_END:
                _prefix_opens.append(float(df.iloc[idx]["Open"]))
                _prefix_closes.append(float(df.iloc[idx]["Close"]))

        if not _prefix_opens or not _prefix_closes:
            return None

        # Pre-fix全体の動き: 最初のOpen と 最後のClose の差
        # (リスト先頭=最新バー, 末尾=最古バー)
        _earliest_open = _prefix_opens[-1]
        _latest_close = _prefix_closes[0]
        return _latest_close - _earliest_open

    # ──────────────────────────────────────────────────
    # メインロジック
    # ──────────────────────────────────────────────────

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        # ── ペアフィルター ──
        _sym = ctx.symbol.upper().replace("=X", "").replace("/", "").replace("_", "")
        if _sym not in self._enabled_symbols:
            return None

        _is_jpy_pair = "JPY" in _sym

        # ── データ十分性 ──
        if ctx.df is None or len(ctx.df) < 20:
            return None

        # ── バータイム取得 ──
        _bt = ctx.bar_time
        if _bt is None and hasattr(ctx.df.index[-1], 'minute'):
            _bt = ctx.df.index[-1]
        if _bt is None:
            return None

        _cur_min = self._bar_minutes(_bt)
        if _cur_min < 0:
            return None

        # ── 時間帯フィルター: UTC 16:00-16:30 (Post-fix entry window) ──
        if not (self.ENTRY_START <= _cur_min < self.ENTRY_END):
            return None

        # ── 金曜ブロック (週末リスクでFix反転不安定) ──
        if ctx.is_friday:
            return None

        # ── ADXフィルター: 極端なトレンドではFix効果が弱い ──
        if ctx.adx >= self.ADX_MAX:
            return None

        # ═══════════════════════════════════════════════════
        # Pre-fix方向分析
        # ═══════════════════════════════════════════════════
        _today = self._bar_date(_bt)
        _prefix_move = self._calc_prefix_move(ctx, _today)
        if _prefix_move is None:
            return None

        # Pre-fixの動きがATR × 0.3 以上で有意判定
        _threshold = ctx.atr * self.PREFIX_ATR_MULT
        if abs(_prefix_move) < _threshold:
            return None  # Pre-fix方向が不明瞭

        _prefix_up = _prefix_move > 0
        _prefix_down = _prefix_move < 0

        # ═══════════════════════════════════════════════════
        # シグナル方向決定 (Fix後反転)
        # ═══════════════════════════════════════════════════
        # 非JPYペア (EUR/USD, GBP/USD):
        #   Pre-fix UP (USD強) → Post-fix SELL (USD反転弱に)
        #   Pre-fix DOWN (USD弱) → Post-fix BUY (USD反転強に)
        # USD/JPY:
        #   Pre-fix UP = USD/JPY上昇 = USD強 → Post-fix USD弱 → USD/JPY下落 → SELL
        #   Pre-fix DOWN = USD/JPY下落 = USD弱 → Post-fix USD強 → USD/JPY上昇 → BUY

        if _is_jpy_pair:
            # USD/JPY: Pre-fix UP(USD強)→SELL, Pre-fix DOWN(USD弱)→BUY
            if _prefix_up:
                signal = "SELL"
            else:
                signal = "BUY"
        else:
            # EUR/USD, GBP/USD: Pre-fix UP(pair上昇=USD弱)→期待:USD強に→SELL pair
            # Pre-fix DOWN(pair下落=USD強)→期待:USD弱に→BUY pair
            if _prefix_up:
                signal = "SELL"
            else:
                signal = "BUY"

        # ── Post-fix反転確認: 現在足が期待方向 ──
        if signal == "BUY" and ctx.entry <= ctx.open_price:
            return None  # 陰線 = 反転未発生
        if signal == "SELL" and ctx.entry >= ctx.open_price:
            return None  # 陽線 = 反転未発生

        # ── HTFハードフィルター ──
        _htf = ctx.htf or {}
        _agr = _htf.get("agreement", "mixed")
        if signal == "BUY" and _agr == "bear":
            return None
        if signal == "SELL" and _agr == "bull":
            return None

        # ═══════════════════════════════════════════════════
        # SL/TP計算
        # ═══════════════════════════════════════════════════
        _dec = 3 if _is_jpy_pair or ctx.pip_mult == 100 else 5

        sl_dist = ctx.atr * self.SL_ATR_MULT
        tp_dist = ctx.atr * self.TP_ATR_MULT

        if signal == "BUY":
            sl = ctx.entry - sl_dist
            tp = ctx.entry + tp_dist
        else:
            sl = ctx.entry + sl_dist
            tp = ctx.entry - tp_dist

        # ═══════════════════════════════════════════════════
        # RR検証
        # ═══════════════════════════════════════════════════
        _sl_d = abs(ctx.entry - sl)
        _tp_d = abs(tp - ctx.entry)
        if _sl_d <= 0:
            return None

        _rr = _tp_d / _sl_d
        if _rr < self.MIN_RR:
            _tp_d = _sl_d * self.MIN_RR
            tp = ctx.entry + _tp_d if signal == "BUY" else ctx.entry - _tp_d
            _rr = _tp_d / _sl_d

        if _rr < self.MIN_RR:
            return None

        # ═══════════════════════════════════════════════════
        # スコアリング & Reasons
        # ═══════════════════════════════════════════════════
        score = 4.0
        reasons = []
        _prefix_pip = abs(_prefix_move) * ctx.pip_mult
        _direction = "UP" if _prefix_up else "DOWN"

        reasons.append(
            f"✅ LFR {signal}: Post-fix反転 "
            f"(Pre-fix {_direction} {_prefix_pip:.1f}pip — Krohn et al. 2024)"
        )

        # ── Post-fix反転足確認ボーナス ──
        score += 0.5
        reasons.append(
            f"✅ Post-fix反転足確認: "
            f"Close={ctx.entry:.{_dec}f} vs Open={ctx.open_price:.{_dec}f}"
        )

        # ── Pre-fix動き強度ボーナス ──
        _prefix_atr_ratio = abs(_prefix_move) / ctx.atr if ctx.atr > 0 else 0
        if _prefix_atr_ratio > 0.6:
            score += 0.5
            reasons.append(
                f"✅ 強Pre-fix動き (ATR比={_prefix_atr_ratio:.2f}>0.6)"
            )

        # ── 月末ボーナス (Melvin & Prins 2015) ──
        _is_month_end = self._is_month_end_window(_bt)

        # ── EMA方向一致ボーナス ──
        if (signal == "BUY" and ctx.ema9 > ctx.ema21) or \
           (signal == "SELL" and ctx.ema9 < ctx.ema21):
            score += 0.3
            reasons.append("✅ EMA短期方向一致")

        # ── HTF方向一致ボーナス ──
        if (signal == "BUY" and _agr == "bull") or \
           (signal == "SELL" and _agr == "bear"):
            score += 0.5
            reasons.append(f"✅ HTF方向一致({_agr})")

        # ── RSI反転ボーナス ──
        if (signal == "BUY" and ctx.rsi < 40) or \
           (signal == "SELL" and ctx.rsi > 60):
            score += 0.3
            reasons.append(f"✅ RSI反転方向一致(RSI={ctx.rsi:.0f})")

        reasons.append(f"📊 RR={_rr:.1f} SL={sl:.{_dec}f} TP={tp:.{_dec}f}")

        # ── Confidence計算 ──
        conf = int(min(85, 50 + score * 4))

        # 月末ボーナス (confidence加算)
        if _is_month_end:
            conf = min(95, conf + self.MONTH_END_BONUS)
            reasons.append(
                f"✅ 月末最終{self.MONTH_END_DAYS}営業日 "
                f"(Fixフロー増幅 — Melvin & Prins 2015, conf+{self.MONTH_END_BONUS})"
            )

        return Candidate(
            signal=signal, confidence=conf, sl=sl, tp=tp,
            reasons=reasons, entry_type=self.name, score=score
        )
