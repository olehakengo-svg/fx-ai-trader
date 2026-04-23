"""
Tokyo Range Breakout (T3) — 東京レンジブレイクアウト UP (Minimum Live 運用)

学術的根拠:
  - Andersen & Bollerslev (1997, J. Empirical Finance): "Intraday periodicity and
    volatility persistence in financial markets" — セッション間のボラティリティ
    構造と流動性遷移時のトレンド継続性を実証。
  - Ito & Hashimoto (2006, JJIE): Tokyo session の range 圧縮と London open の
    流動性流入によるブレイクアウトエッジ。
  - Corcoran (2002): London open はFX最大の流動性遷移点で価格発見が集中。

メカニズム:
  Tokyo セッション (UTC 0-7) の日中 range は相対的に狭く、London open (UTC 7-9)
  で upside breakout が発生する場合、欧州実需フローの流入により 4h 以内に
  +15-20pip のトレンド継続が発生する確率が有意に高い。

Walk-Forward 検証 (2026-04-23):
  USD_JPY UP breakout:
    IS (2025-04-20..2025-10-20): N=47 mean=+17.72p WR=70.2% t=+2.83
    OOS (2025-10-21..2026-04-23): N=51 mean=+17.62p WR=74.5% t=+3.59
    mean_diff=0.6%, WR_diff=4.3pp → 🟢 STABLE_EDGE
  Net EV (friction 2.14p RT): +15.48p/trade

Minimum Live 運用 (2026-04-23 開始):
  - 対象: USD_JPY のみ (最強エッジ & friction 最小)
  - 方向: BUY-only (UP breakout は STABLE_EDGE, DOWN は NOISY_BUT_ALIVE のため保留)
  - サイジング: Kelly 0.25x (= Kelly Half の半分) 相当を _STRATEGY_LOT_BOOST で制御
  - 2 週間観察 → friction 実測後に Full Live (全4ペア) 判断

ガードレール:
  - Live N=15 で EV_cost < -0.5p → 自動停止検討
  - Live WR が BT WR の 0.7x (52%) 以下 → 停止検討
  - BT vs Live mean 差分 > 30% → 停止検討

パラメータ:
  Tokyo range: UTC 0:00-7:00 の High/Low
  Entry window: UTC 7:00-9:00 (London open 2h)
  Trigger: first fresh breakout bar (close > Tokyo_high, prev closes <= Tokyo_high)
  TP: +20 pip (BT mean +17.6 + buffer)
  SL: -15 pip (std 39p なので tight すぎず)
  MAX_HOLD: 16 bars × 15m = 4h (BT window に整合)
  Min range: 15 pip (narrow-range day 除外)
"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from typing import Optional
import logging

logger = logging.getLogger("tokyo_range_breakout")


class TokyoRangeBreakout(StrategyBase):
    name = "tokyo_range_breakout_up"
    mode = "daytrade"
    enabled = True
    strategy_type = "trend"   # breakout follow

    # ── 時間帯 (UTC hour) ──
    TOKYO_START_H = 0
    TOKYO_END_H = 7           # exclusive: UTC 0:00-6:59
    LONDON_ENTRY_START_H = 7
    LONDON_ENTRY_END_H = 9    # exclusive: UTC 7:00-8:59

    # ── Tokyo range 品質フィルター ──
    MIN_TOKYO_BARS = 20       # 15m × 20 = 5h 以上必要 (欠損 day 除外)
    MIN_RANGE_PIP = 15.0      # narrow-range day 除外 (proposal Risk 4)

    # ── SL/TP (固定 pip) ──
    TP_PIP = 20.0             # BT OOS mean +17.6 + buffer
    SL_PIP = 15.0             # tight すぎず RR≈1.33 確保
    MIN_RR = 1.2

    # ── 保持 ──
    MAX_HOLD_BARS = 16        # 16 × 15m = 4h (BT exit UTC 13)

    # ── 対象ペア (Minimum Live: USD_JPY のみ) ──
    _ENABLED_PAIRS = {"USDJPY"}

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        # ── ペアフィルター: USD_JPY のみ (Minimum Live) ──
        _sym = ctx.symbol.upper().replace("=X", "").replace("/", "").replace("_", "")
        if _sym not in self._ENABLED_PAIRS:
            return None

        # ── タイムフレームフィルター: 15m のみ ──
        if ctx.tf not in ("15m",):
            return None

        # ── 時間帯: UTC 7:00-8:59 のみ ──
        if ctx.hour_utc < self.LONDON_ENTRY_START_H or ctx.hour_utc >= self.LONDON_ENTRY_END_H:
            return None

        # ── データ十分性 ──
        if ctx.df is None or len(ctx.df) < 50:
            return None
        if not hasattr(ctx.df.index, 'hour') or not hasattr(ctx.df.index, 'date'):
            return None

        # ── 当日 date 決定 ──
        bar_time = ctx.bar_time
        if bar_time is None:
            _idx_last = ctx.df.index[-1]
            if hasattr(_idx_last, 'date'):
                bar_time = _idx_last
            else:
                return None
        today_date = bar_time.date() if hasattr(bar_time, 'date') else None
        if today_date is None:
            return None

        # ── 金曜除外 (Risk 3: 週末オーバーハング) ──
        if hasattr(bar_time, 'weekday') and bar_time.weekday() == 4:
            return None

        # ── ATR 有効性 ──
        if ctx.atr <= 0:
            return None

        # ── Tokyo range 計算 (当日 UTC 0-7) ──
        _tokyo_mask = (
            (ctx.df.index.date == today_date)
            & (ctx.df.index.hour >= self.TOKYO_START_H)
            & (ctx.df.index.hour < self.TOKYO_END_H)
        )
        _tokyo_bars = ctx.df[_tokyo_mask]
        if len(_tokyo_bars) < self.MIN_TOKYO_BARS:
            return None

        _tokyo_high = float(_tokyo_bars["High"].max())
        _tokyo_low = float(_tokyo_bars["Low"].min())
        _tokyo_range = _tokyo_high - _tokyo_low
        _tokyo_range_pip = _tokyo_range * ctx.pip_mult
        if _tokyo_range <= 0:
            return None
        if _tokyo_range_pip < self.MIN_RANGE_PIP:
            return None

        # ── UP breakout 検出 (current bar close > Tokyo_high) ──
        if ctx.entry <= _tokyo_high:
            return None

        # ── Fresh breakout 検証: 今日の UTC 7-9 window で過去バーが未ブレイク ──
        # 今日の London open window 内の過去バー(現在バー除く)を取得
        _london_mask = (
            (ctx.df.index.date == today_date)
            & (ctx.df.index.hour >= self.LONDON_ENTRY_START_H)
            & (ctx.df.index.hour < self.LONDON_ENTRY_END_H)
        )
        _london_bars = ctx.df[_london_mask]
        if len(_london_bars) > 1:
            _earlier = _london_bars.iloc[:-1]
            if float(_earlier["Close"].max()) > _tokyo_high:
                return None   # 既に先にブレイク済み → 同一日 2nd entry 抑制

        # ── BOTH breakout 除外 (whipsaw 回避) ──
        if len(_london_bars) > 0:
            if float(_london_bars["Low"].min()) < _tokyo_low:
                return None   # 既に下方ブレイクも発生 → BOTH day

        # ── v9.1: HTF Hard Block (戦略内 self-contained) ──
        _htf = ctx.htf or {}
        _htf_agr = _htf.get("agreement", "mixed")
        if _htf_agr == "bear":
            return None   # HTF bearish → BUY breakout はブロック

        # ── ブレイク足の品質: 陽線かつ実体 >= range の 30% ──
        _bar_range = ctx.prev_high - ctx.prev_low
        if ctx.entry > 0:
            _curr_range = abs(float(ctx.df.iloc[-1]["High"]) - float(ctx.df.iloc[-1]["Low"]))
            _body = abs(ctx.entry - ctx.open_price)
            if _curr_range > 0:
                _body_ratio = _body / _curr_range
                if _body_ratio < 0.30:
                    return None   # 長ヒゲブレイクは fake の可能性
            if ctx.entry <= ctx.open_price:
                return None   # 陰線ブレイクは弱い

        # ═══════════════════════════════════════════════════
        # シグナル生成
        # ═══════════════════════════════════════════════════
        _pip_size = 0.01 if ctx.is_jpy else 0.0001
        entry = ctx.entry
        sl = entry - self.SL_PIP * _pip_size
        tp = entry + self.TP_PIP * _pip_size

        _sl_d = abs(entry - sl)
        _tp_d = abs(tp - entry)
        if _sl_d <= 0:
            return None
        _rr = _tp_d / _sl_d
        if _rr < self.MIN_RR:
            return None

        score = 5.5   # 学術★★★★★ + WFA STABLE_EDGE + WR=74.5% で高め
        reasons = []
        _dec = 3 if ctx.is_jpy or ctx.pip_mult == 100 else 5

        reasons.append(
            f"✅ Tokyo Range Breakout UP: Close={entry:.{_dec}f} > "
            f"Tokyo_high={_tokyo_high:.{_dec}f} (Andersen-Bollerslev 1997)"
        )
        reasons.append(
            f"✅ Tokyo range={_tokyo_range_pip:.1f}pip (>={self.MIN_RANGE_PIP:.0f}p), "
            f"London open UTC {ctx.hour_utc}:xx — fresh breakout"
        )
        reasons.append(
            f"📊 RR={_rr:.2f} TP=+{self.TP_PIP:.0f}p SL=-{self.SL_PIP:.0f}p "
            f"HTF={_htf_agr}"
        )

        # ═══════════════════════════════════════════════════
        # スコアボーナス
        # ═══════════════════════════════════════════════════

        # 広 Tokyo range (>= 25pip): 圧縮エネルギー大
        if _tokyo_range_pip >= 25.0:
            score += 0.5
            reasons.append(f"✅ 広 Tokyo range({_tokyo_range_pip:.1f}p >= 25p)")

        # HTF bull 完全一致
        if _htf_agr == "bull":
            score += 0.5
            reasons.append(f"✅ HTF方向一致(bull)")

        # EMA9>EMA21 (短期上昇)
        if ctx.ema9 > ctx.ema21:
            score += 0.3
            reasons.append("✅ EMA9>EMA21 短期上昇")

        # ADX >= 20 (ブレイクアウトにはトレンド地合い必要)
        if ctx.adx >= 20:
            score += 0.3
            reasons.append(f"✅ ADX={ctx.adx:.1f} >= 20")

        conf = int(min(85, 50 + score * 4))
        return Candidate(
            signal="BUY", confidence=conf, sl=sl, tp=tp,
            reasons=reasons, entry_type=self.name, score=score
        )
