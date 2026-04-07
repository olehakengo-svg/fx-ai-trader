"""
ORB Trap (Opening Range Breakout Trap) — セッションオープンレンジのフェイクアウト逆張り

学術的根拠:
  - Corcoran (2002): セッション境界での流動性遷移は価格ディスロケーションを生む
  - Bulkowski (2005): False breakout後のチャネル回帰パターン勝率 70-80%
  - Lo & MacKinlay (1988): 短期リバーサル効果 — オーバーリアクション是正

実装背景:
  - LSB (London Session Breakout) BT: WR=10% → 90%のブレイクアウトがフェイクアウト
  - フェイクアウト率の高さ = ORB Trap の理論的エッジ
  - HFB (HTF False Breakout Fade) の2段階確認パターンを踏襲

数学的定義:
  Opening Range (OR):
    London = UTC 07:00-07:30 の High/Low (15m × 2 bars)
    NY     = UTC 13:30-14:00 の High/Low (15m × 2 bars)

  Break Detection:
    ∃ bar ∈ (range_end, current): Close(bar) > OR_high  →  UP break
    ∃ bar ∈ (range_end, current): Close(bar) < OR_low   →  DOWN break

  Trap Confirmation (2条件同時成立):
    1. Close(current) ∈ [OR_low, OR_high]   … レンジ内に実体回帰
    2. Close(prev)    ∉ [OR_low, OR_high]   … 前足はレンジ外 (fresh return)

  Entry:
    UP break   → SELL (上方フェイクアウト、売り手主導)
    DOWN break → BUY  (下方フェイクアウト、買い手主導)

  SL: max(High of break bars) + ATR×0.3  [UP]
      min(Low  of break bars) - ATR×0.3  [DOWN]
  TP: OR反対端 (SELL → OR_low, BUY → OR_high)
"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from typing import Optional


class OrbTrap(StrategyBase):
    name = "orb_trap"
    mode = "daytrade"
    enabled = True

    # ══════════════════════════════════════════════════
    # パラメータ定数
    # ══════════════════════════════════════════════════

    # ── Opening Range (UTC 通算分) ──
    LDN_RANGE_START = 420       # UTC 07:00
    LDN_RANGE_END   = 450       # UTC 07:30
    LDN_ENTRY_END   = 600       # UTC 10:00

    NY_RANGE_START   = 810      # UTC 13:30
    NY_RANGE_END     = 840      # UTC 14:00
    NY_ENTRY_END     = 960      # UTC 16:00

    # ── Trap検出 ──
    MIN_BREAK_ATR    = 0.05     # ブレイク最低超過: ATR × 5%
    MAX_SCAN_BARS    = 12       # ブレイク極値スキャン範囲

    # ── レンジ品質 ──
    MIN_RANGE_ATR    = 0.3      # OR ≥ ATR × 0.3 (ノイズ排除)
    MAX_RANGE_ATR    = 2.5      # OR ≤ ATR × 2.5 (過大レンジ排除)

    # ── SL/TP ──
    SL_ATR_BUFFER    = 0.3      # SL = フェイクアウト極値 + ATR × 0.3
    MIN_RR           = 1.3      # 最低リスクリワード比

    # ── 保持 ──
    MAX_HOLD_BARS    = 12       # 最大12バー (3時間 @ 15m)

    # ── v6.1: 仲値フィルター (USD/JPY専用) ──
    NAKANE_START     = 45       # UTC 00:45 (JST 09:45)
    NAKANE_END       = 90       # UTC 01:30 (JST 10:30)
    NAKANE_MOVE_ATR  = 1.2      # 仲値期間のレンジ > ATR×1.2 で汚染判定

    # ──────────────────────────────────────────────────
    # ヘルパー
    # ──────────────────────────────────────────────────

    @staticmethod
    def _bar_minutes(bar_dt) -> int:
        """バー時刻 → UTC 通算分 (0-1439)。取得不可なら -1。"""
        if hasattr(bar_dt, 'hour') and hasattr(bar_dt, 'minute'):
            return bar_dt.hour * 60 + bar_dt.minute
        return -1

    @staticmethod
    def _bar_date(bar_dt):
        """バーの日付部分を返す。取得不可なら None。"""
        if hasattr(bar_dt, 'date') and callable(bar_dt.date):
            return bar_dt.date()
        return None

    def _calc_opening_range(self, df, range_start, range_end, today):
        """当日の Opening Range (high, low, bars_found) を返す。"""
        hi = lo = None
        count = 0
        for j in range(min(24, len(df))):
            idx = len(df) - 1 - j
            bdt = df.index[idx]
            bm = self._bar_minutes(bdt)
            if bm < 0:
                continue
            # 当日チェック (日付不明時はスキップしない)
            if today is not None:
                bd = self._bar_date(bdt)
                if bd is not None and bd != today:
                    continue
            if range_start <= bm < range_end:
                h = float(df.iloc[idx]["High"])
                l = float(df.iloc[idx]["Low"])
                hi = max(hi, h) if hi is not None else h
                lo = min(lo, l) if lo is not None else l
                count += 1
        return hi, lo, count

    def _scan_breaks(self, df, range_end, rh, rl, today):
        """ブレイクバーをスキャン。

        Returns:
            (saw_up, saw_down, up_extreme_high, down_extreme_low)
        """
        saw_up = saw_down = False
        up_ext = None
        dn_ext = None
        for j in range(1, min(self.MAX_SCAN_BARS + 1, len(df))):
            idx = len(df) - 1 - j
            bdt = df.index[idx]
            bm = self._bar_minutes(bdt)
            if bm < 0 or bm < range_end:
                continue
            if today is not None:
                bd = self._bar_date(bdt)
                if bd is not None and bd != today:
                    continue
            c = float(df.iloc[idx]["Close"])
            if c > rh:
                saw_up = True
                h = float(df.iloc[idx]["High"])
                up_ext = max(up_ext, h) if up_ext is not None else h
            if c < rl:
                saw_down = True
                l = float(df.iloc[idx]["Low"])
                dn_ext = min(dn_ext, l) if dn_ext is not None else l
        return saw_up, saw_down, up_ext, dn_ext

    # ──────────────────────────────────────────────────
    # メインロジック
    # ──────────────────────────────────────────────────

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        # ── ペアフィルター ──
        _sym = ctx.symbol.upper().replace("=X", "").replace("/", "").replace("_", "")
        if _sym not in ("EURUSD", "USDJPY", "GBPUSD"):
            return None

        # ── データ十分性 ──
        if ctx.df is None or len(ctx.df) < 20:
            return None

        # ── バータイム取得 (分精度) ──
        _bt = ctx.bar_time
        if _bt is None and hasattr(ctx.df.index[-1], 'minute'):
            _bt = ctx.df.index[-1]
        if _bt is None:
            return None

        _cur_min = self._bar_minutes(_bt)
        if _cur_min < 0:
            return None

        # ── セッション判定 ──
        session = None
        rs = re = 0

        if self.LDN_RANGE_END <= _cur_min < self.LDN_ENTRY_END:
            session, rs, re = "LDN", self.LDN_RANGE_START, self.LDN_RANGE_END
        elif self.NY_RANGE_END <= _cur_min < self.NY_ENTRY_END:
            session, rs, re = "NY", self.NY_RANGE_START, self.NY_RANGE_END

        if session is None:
            return None

        # ── 金曜 UTC 15+ ブロック ──
        if ctx.is_friday and _cur_min >= 900:
            return None

        # ══════════════════════════════════════════════════
        # v6.1: 仲値フィルター (USD/JPY × LDN session)
        #   東京仲値(09:55 JST = 00:55 UTC)前後の異常ボラが
        #   LDN ORBレンジを汚染するケースを排除
        #   NY sessionは影響外のためパススルー
        # ══════════════════════════════════════════════════
        if ctx.is_jpy and "JPY" in ctx.symbol and session == "LDN":
            try:
                _today_nak = self._bar_date(_bt)
                _nak_bars = []
                for _i in range(len(ctx.df)):
                    _bi = ctx.df.index[_i]
                    if hasattr(_bi, 'date') and self._bar_date(_bi) == _today_nak:
                        _bm = self._bar_minutes(_bi)
                        if self.NAKANE_START <= _bm <= self.NAKANE_END:
                            _nak_bars.append(_i)
                if len(_nak_bars) >= 2:
                    _nak_sl = ctx.df.iloc[_nak_bars]
                    _nak_range = float(_nak_sl["High"].max()) - float(_nak_sl["Low"].min())
                    if _nak_range > ctx.atr * self.NAKANE_MOVE_ATR:
                        return None  # 仲値汚染: ORBレンジの信頼性低下
            except Exception:
                pass

        # ═══════════════════════════════════════════════════
        # Opening Range 計算
        # ═══════════════════════════════════════════════════
        _today = self._bar_date(_bt)
        _rh, _rl, _rc = self._calc_opening_range(ctx.df, rs, re, _today)
        if _rh is None or _rl is None or _rc < 1:
            return None

        _or = _rh - _rl
        if _or <= 0:
            return None

        # ── レンジ品質チェック ──
        if ctx.atr > 0:
            _ratio = _or / ctx.atr
            if _ratio < self.MIN_RANGE_ATR or _ratio > self.MAX_RANGE_ATR:
                return None

        # ═══════════════════════════════════════════════════
        # Trap検出: 2段階確認
        #   1. 現在足 Close がレンジ内 (実体回帰)
        #   2. 前足 Close がレンジ外 (fresh return = フェイクアウト成立)
        # ═══════════════════════════════════════════════════

        # Step 1: 現在足 Close がレンジ内
        if not (_rl <= ctx.entry <= _rh):
            return None

        # Step 2: 前足 Close がレンジ外 (fresh return)
        if _rl <= ctx.prev_close <= _rh:
            return None

        # ── ブレイク方向判定 (前足の位置) ──
        if ctx.prev_close > _rh:
            _break_dir = "UP"
        elif ctx.prev_close < _rl:
            _break_dir = "DOWN"
        else:
            return None

        # ── 両方向ブレイクチェック (ホイップソー排除) ──
        _saw_up, _saw_down, _up_ext, _dn_ext = self._scan_breaks(
            ctx.df, re, _rh, _rl, _today
        )
        if _saw_up and _saw_down:
            return None

        # ── ブレイク極値 (SL参照点) ──
        if _break_dir == "UP":
            _extreme = _up_ext if _up_ext is not None else ctx.prev_high
        else:
            _extreme = _dn_ext if _dn_ext is not None else ctx.prev_low

        # ── ブレイク最低超過チェック ──
        _min_exc = ctx.atr * self.MIN_BREAK_ATR
        if _break_dir == "UP" and (_extreme - _rh) < _min_exc:
            return None
        if _break_dir == "DOWN" and (_rl - _extreme) < _min_exc:
            return None

        # ═══════════════════════════════════════════════════
        # シグナル生成
        # ═══════════════════════════════════════════════════
        _htf = ctx.htf or {}
        _agr = _htf.get("agreement", "mixed")

        signal = None
        score = 4.5
        reasons = []
        sl = tp = 0.0
        _dec = 3 if ctx.is_jpy or ctx.pip_mult == 100 else 5
        _or_pip = _or * ctx.pip_mult

        if _break_dir == "UP":
            # 上方フェイクアウト → SELL
            if _agr == "bull":
                return None  # 強Bull HTFでは本物ブレイクの可能性
            signal = "SELL"
            sl = _extreme + ctx.atr * self.SL_ATR_BUFFER
            tp = _rl
            _exc_pip = (_extreme - _rh) * ctx.pip_mult
            reasons.append(
                f"✅ ORB Trap SELL: {session}上方フェイクアウト "
                f"(OR={_or_pip:.1f}pip, 超過={_exc_pip:.1f}pip)"
            )
        elif _break_dir == "DOWN":
            # 下方フェイクアウト → BUY
            if _agr == "bear":
                return None
            signal = "BUY"
            sl = _extreme - ctx.atr * self.SL_ATR_BUFFER
            tp = _rh
            _exc_pip = (_rl - _extreme) * ctx.pip_mult
            reasons.append(
                f"✅ ORB Trap BUY: {session}下方フェイクアウト "
                f"(OR={_or_pip:.1f}pip, 超過={_exc_pip:.1f}pip)"
            )

        if signal is None:
            return None

        # ═══════════════════════════════════════════════════
        # RR検証
        # ═══════════════════════════════════════════════════
        _sl_d = abs(ctx.entry - sl)
        _tp_d = abs(tp - ctx.entry)
        if _sl_d <= 0:
            return None

        # RR不足時のTP補正
        _rr = _tp_d / _sl_d
        if _rr < self.MIN_RR:
            _tp_d = _sl_d * self.MIN_RR
            tp = ctx.entry - _tp_d if signal == "SELL" else ctx.entry + _tp_d
            _rr = _tp_d / _sl_d

        # RR再確認
        if _rr < self.MIN_RR:
            return None

        # ═══════════════════════════════════════════════════
        # Reasons & ボーナス
        # ═══════════════════════════════════════════════════
        reasons.append(
            f"✅ OR: H={_rh:.{_dec}f} L={_rl:.{_dec}f} "
            f"(range={_or_pip:.1f}pip)"
        )
        reasons.append(f"📊 RR={_rr:.1f} SL={sl:.{_dec}f} TP={tp:.{_dec}f}")

        # 反転足確認ボーナス (break方向と逆の実体)
        if (_break_dir == "UP" and ctx.entry < ctx.open_price) or \
           (_break_dir == "DOWN" and ctx.entry > ctx.open_price):
            score += 0.5
            reasons.append("✅ 反転足確認(実体方向一致)")

        # HTF方向一致ボーナス
        if (signal == "BUY" and _agr == "bull") or \
           (signal == "SELL" and _agr == "bear"):
            score += 0.5
            reasons.append(f"✅ HTF方向一致({_agr})")

        # EMA短期方向一致ボーナス
        if (signal == "BUY" and ctx.ema9 > ctx.ema21) or \
           (signal == "SELL" and ctx.ema9 < ctx.ema21):
            score += 0.3
            reasons.append("✅ EMA短期方向一致")

        # レンジ環境ボーナス (ADX低 → trap成功率↑)
        if ctx.adx < 25:
            score += 0.3
            reasons.append(f"✅ レンジ環境(ADX={ctx.adx:.1f}<25)")

        conf = int(min(85, 50 + score * 4))
        return Candidate(
            signal=signal, confidence=conf, sl=sl, tp=tp,
            reasons=reasons, entry_type=self.name, score=score
        )
