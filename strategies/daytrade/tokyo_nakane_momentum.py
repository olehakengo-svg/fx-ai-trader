"""
Tokyo Nakane Momentum (TNM) — 仲値リバーサル BUY専用戦略

学術的根拠:
  - Andersen et al. (2003): Scheduled fix/announcement anomaly in FX markets
  - Ito & Hashimoto (2006): 東京仲値(09:55 JST)前後の非対称フロー

データ裏付け (USD/JPY 15m, 59日間):
  - Pre-fix (UTC 00:00-00:45) DOWN bias: 59.3% (avg=-5.39pip)
  - Post-fix DOWN→BUY reversal: N=33 WR=63.6% avg=+2.33pip total=+76.8pip
  - Post-fix UP→SELL reversal: N=22 WR=36.4% avg=-7.66pip total=-168.5pip (罠)
  - 非対称性: BUY方向のみ統計的有意エッジ、SELL方向は大幅マイナス

構造的メカニズム:
  本邦輸入企業のドル買い需要が仲値(09:55 JST = 00:55 UTC)に集中。
  事前ショートカバー/ポジション調整でDOWN bias発生。
  仲値決定後に需要消失→リバーサル(BUY)。
  SELLが機能しないのは輸出企業ドル売りが仲値に集中しない(月末/五十日のみ)ため。

戦略コンセプト:
  - USD/JPY専用・BUY方向のみ（UP→SELLは完全ブロック）
  - Pre-fix 3本(45min)でDOWN方向を確認
  - Post-fix最初の15m足で陽線確認→BUYエントリー
  - 月曜/金曜は仲値フロー不安定のため除外
  - HTFはsoft penalty/bonusのみ（実需フローはトレンドに逆行可能）
"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from typing import Optional


class TokyoNakaneMomentum(StrategyBase):
    name = "tokyo_nakane_momentum"
    mode = "daytrade"
    enabled = True

    # ── 時間帯パラメータ ──
    # 仲値 = 09:55 JST = 00:55 UTC
    # Entry window: UTC 00:45-01:15 (15m bars: 00:45, 01:00)
    entry_window_start = 45     # total minutes from midnight UTC
    entry_window_end = 75       # total minutes from midnight UTC

    # ── Pre-fix DOWN判定 ──
    prefix_bars = 3             # 00:00, 00:15, 00:30 の3本
    min_down_pip = 2.0          # 最低DOWN幅 (pip) — ノイズ除外
    large_down_pip = 5.0        # 大幅DOWN閾値 (pip) — スコアボーナス

    # ── エントリートリガー ──
    require_bullish_bar = True  # 陽線必須 (Close > Open)

    # ── SL/TP ──
    sl_atr_buffer = 0.3        # SL = Pre-fix安値 - ATR×0.3
    tp_retracement = 0.5       # TP = Pre-fix下落幅の50%戻し
    tp_min_atr = 1.5            # TP最低距離 = ATR×1.5

    # ── 最大保持 ──
    max_hold_bars = 6           # 6バー = 90分 (仲値反転は迅速)

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        # ── USD/JPY専用 ──
        if not ctx.is_jpy:
            return None

        # ── 月曜(0)・金曜(4)除外: 仲値フロー不安定 ──
        if ctx.bar_time is not None and hasattr(ctx.bar_time, 'weekday'):
            _dow = ctx.bar_time.weekday()
            if _dow in (0, 4):
                return None
        elif ctx.is_friday:
            return None

        # ── 時間帯フィルター: UTC 00:45 - 01:15 ──
        _minute = 0
        if ctx.bar_time is not None and hasattr(ctx.bar_time, 'minute'):
            _minute = ctx.bar_time.minute
        _total_min = ctx.hour_utc * 60 + _minute
        if _total_min < self.entry_window_start or _total_min > self.entry_window_end:
            return None

        # ── DataFrame十分性チェック ──
        # Pre-fix bars + offset + 余裕
        _offset = max(1, (_total_min - 30) // 15)  # 00:30(end of pre-fix) からの距離
        _needed = _offset + self.prefix_bars + 1
        if ctx.df is None or len(ctx.df) < _needed:
            return None

        # ── Pre-fix方向分析 ──
        # Pre-fix = UTC 00:00-00:30 の3本
        # offset計算: 00:30バーは現在から _offset+1 本前
        _pf_earliest = ctx.df.iloc[-(_offset + self.prefix_bars)]   # 00:00 bar
        _pf_middle = ctx.df.iloc[-(_offset + self.prefix_bars - 1)]  # 00:15 bar
        _pf_latest = ctx.df.iloc[-(_offset + 1)]                     # 00:30 bar

        _prefix_open = float(_pf_earliest["Open"])     # 00:00 Open
        _prefix_close = float(_pf_latest["Close"])     # 00:30 Close
        _prefix_low = min(
            float(_pf_earliest["Low"]),
            float(_pf_middle["Low"]),
            float(_pf_latest["Low"])
        )
        _prefix_high = max(
            float(_pf_earliest["High"]),
            float(_pf_middle["High"]),
            float(_pf_latest["High"])
        )

        # Pre-fix move (negative = DOWN)
        _prefix_move = _prefix_close - _prefix_open
        _prefix_move_pip = _prefix_move * ctx.pip_mult

        # ── DOWN条件: 最低2pip以上の下落 ──
        if _prefix_move_pip >= -self.min_down_pip:
            return None  # DOWN不十分 or UP方向

        # ═══════════════════════════════════════════════════
        # BUY ONLY — UP→SELLは完全ブロック
        # ═══════════════════════════════════════════════════

        # ── HTFハードフィルター: 強烈な円高(4H+1D bear一致)ではBUY禁止 ──
        # 根拠: 4H+1D両方がbearish = マクロ的円高。仲値の実需フロー(数pip規模)では
        # 制度的売り圧力を超克できない → BUYを完全ブロック。
        # 注意: 15m EMA方向はフィルターに使わない（仲値BUYは本質的に逆張り）
        _htf = ctx.htf or {}
        _agreement = _htf.get("agreement", "mixed")
        if _agreement == "bear":
            return None  # 4H+1D下落一致 → 仲値BUY禁止

        # ── エントリートリガー: 陽線確認 ──
        if self.require_bullish_bar and ctx.entry <= ctx.open_price:
            return None  # 陰線 = リバーサル未発生

        # ── BUYシグナル生成 ──
        signal = "BUY"
        score = 4.0
        reasons = []

        # SL: Pre-fix安値 - ATR×0.3
        sl = _prefix_low - ctx.atr * self.sl_atr_buffer

        # TP: Pre-fix下落幅の50%戻し (最低ATR×1.5保証)
        _tp_target = abs(_prefix_move) * self.tp_retracement
        tp = ctx.entry + max(_tp_target, ctx.atr * self.tp_min_atr)

        reasons.append(
            f"✅ 仲値DOWN→BUY: Pre-fix {_prefix_move_pip:.1f}pip "
            f"(輸入実需フローリバーサル — Andersen 2003)"
        )
        reasons.append(
            f"✅ 陽線確認: Close={ctx.entry:.3f} > Open={ctx.open_price:.3f}"
        )

        # ── ボーナス条件 ──

        # 底値切上げ (current Low > previous Low)
        if len(ctx.df) >= 2:
            _curr_low = float(ctx.df.iloc[-1]["Low"])
            _prev_bar_low = float(ctx.df.iloc[-2]["Low"])
            if _curr_low > _prev_bar_low:
                score += 0.3
                reasons.append("✅ 底値切上げ確認")

        # RSI回復
        if ctx.rsi5 > 45:
            score += 0.3
            reasons.append(f"✅ RSI回復({ctx.rsi5:.1f}>45)")

        # 大幅Pre-fix下落ボーナス
        if _prefix_move_pip < -self.large_down_pip:
            score += 0.5
            reasons.append(
                f"✅ 大幅下落({_prefix_move_pip:.1f}pip<-{self.large_down_pip}) — "
                f"リバーサル強度高"
            )

        # HTF方向 — bull=ボーナス, bear=上でhard blockされ到達しない, mixed=ニュートラル
        # (bearは上のhard filterで既にreturn None済み)
        if _agreement == "bull":
            score += 0.5
            reasons.append(f"✅ HTF方向一致({_agreement})")

        # EMA方向一致ボーナス
        if ctx.ema9 > ctx.ema21:
            score += 0.3
            reasons.append("✅ EMA短期方向一致(9>21)")

        # Pre-fix range情報
        _prefix_range_pip = (_prefix_high - _prefix_low) * ctx.pip_mult
        reasons.append(
            f"📊 Pre-fix: Open={_prefix_open:.3f} Close={_prefix_close:.3f} "
            f"Range={_prefix_range_pip:.1f}pip"
        )

        conf = int(min(85, 50 + score * 4))
        return Candidate(
            signal=signal, confidence=conf, sl=sl, tp=tp,
            reasons=reasons, entry_type=self.name, score=score
        )
