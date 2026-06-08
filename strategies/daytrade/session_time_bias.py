"""
Session Time Bias (STB) — セッション時間帯の通貨減価バイアスを利用するデイトレ戦略

学術的根拠:
  - Breedon & Ranaldo (2013, JMCB): 通貨はホームセッション中に減価する傾向
    "Net Order Flow and the Term Structure of Foreign Exchange" Journal of Money, Credit and Banking
  - JPY: 東京セッション中にJPY減価 → USD/JPY BUY方向バイアス
  - EUR: ロンドンセッション中にEUR減価 → EUR/USD SELL方向バイアス
  - GBP: ロンドンセッション中にGBP減価 → GBP/USD SELL方向バイアス

メカニズム:
  ホーム市場参加者(輸入企業・機関投資家)が自国通貨を売却し外貨建て資産を購入。
  この実需フローがセッション中の通貨安バイアスを生む。
  セッション開始直後の30分は初期ボラティリティスパイクを回避。

パラメータ:
  SL: ATR(15m, 14) x 1.5
  TP: ATR(15m, 14) x 2.0
  MIN_RR: 1.2
  ADX < 35 (極端トレンドは構造的バイアスを上回る)
  確認: 現在足Closeがバイアス方向
  保持: 4-6時間 (セッション中間点またはセッション終了)
"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from typing import Optional


class SessionTimeBias(StrategyBase):
    name = "session_time_bias"
    mode = "daytrade"
    enabled = True

    # ══════════════════════════════════════════════════
    # セッション定義 (UTC分)
    # ══════════════════════════════════════════════════

    # v8.6: 時間窓拡張 — N蓄積加速のため、学術根拠の範囲内で拡張
    # Breedon & Ranaldo (2013): 効果は「セッション全体」に存在。midpoint制限は不要
    # Tokyo session: UTC 0:00 - 6:00 (全6時間をエントリー窓に)
    TOKYO_ENTRY_START = 30     # UTC 00:30 (session open + 30min、初期スパイク回避)
    TOKYO_ENTRY_END = 330      # UTC 05:30 (v8.6: 3:00→5:30 セッション終了30分前まで)
    TOKYO_EXIT = 360           # UTC 06:00

    # London session: UTC 7:00 - 15:00 (v8.6: 12:00→15:00 NY overlapまで拡張)
    # Ranaldo (2009): EUR/GBP減価効果はNYオープンまで持続
    LONDON_ENTRY_START = 450   # UTC 07:30
    LONDON_ENTRY_END = 840     # UTC 14:00 (v8.6: 9:30→14:00 NY open前まで)
    LONDON_EXIT = 900          # UTC 15:00 (v8.6: 12:00→15:00)

    # ══════════════════════════════════════════════════
    # SL/TP パラメータ
    # ══════════════════════════════════════════════════
    SL_ATR_MULT = 1.5
    TP_ATR_MULT = 2.0
    MIN_RR = 1.2

    # ══════════════════════════════════════════════════
    # フィルター
    # ══════════════════════════════════════════════════
    ADX_MAX = 35               # 極端トレンド排除
    MIN_BODY_RATIO = 0.40      # 確認足の実体比率

    # ══════════════════════════════════════════════════
    # 保持
    # ══════════════════════════════════════════════════
    MAX_HOLD_BARS = 24         # 24バー = 6時間 @ 15m

    # ══════════════════════════════════════════════════
    # ペア×セッション×バイアス定義
    # ══════════════════════════════════════════════════
    # (symbol_clean, session, bias_signal)
    PAIR_SESSION_MAP = {
        "USDJPY": ("TOKYO", "BUY"),      # JPY減価 → USD/JPY BUY
        "EURUSD": ("LONDON", "SELL"),     # EUR減価 → EUR/USD SELL
        "GBPUSD": ("LONDON", "SELL"),     # GBP減価 → GBP/USD SELL
    }

    # ──────────────────────────────────────────────────
    # ヘルパー
    # ──────────────────────────────────────────────────

    @staticmethod
    def _total_minutes(ctx: SignalContext) -> int:
        """現在バーのUTC通算分を返す。取得不可なら -1。"""
        _minute = 0
        if ctx.bar_time is not None and hasattr(ctx.bar_time, 'minute'):
            _minute = ctx.bar_time.minute
        elif ctx.df is not None and len(ctx.df) > 0 and hasattr(ctx.df.index[-1], 'minute'):
            # v8.9: ライブモードでbar_time=None → DFインデックスから取得
            _minute = ctx.df.index[-1].minute
        else:
            return -1
        return ctx.hour_utc * 60 + _minute

    # ── Edge cell filter (added 2026-06-08, see docs/superpowers/specs/) ──
    # Source: production shadow trades 2026-04-29..06-08, N=396.
    # EDGE: LDN × ADX[15,30] × dist_EMA200<0.5% → 1.0x (mean +0.93p, WR 45.2%)
    # CORE: +ADX[25,30] OR regime=RANGE         → 1.5x (mean +1.19-2.17p)
    def _edge_cell(self, ctx) -> tuple:
        """Return (edge_on, lot_multiplier). False/0.0 = skip.

        Env flag SESSION_TIME_BIAS_CELL_FILTER_V1=0 bypasses filter
        (returns (True, 1.0) for rollback).
        """
        import os as _os
        if _os.environ.get("SESSION_TIME_BIAS_CELL_FILTER_V1", "1") == "0":
            return True, 1.0  # bypass

        # Hour (UTC) — strategies/context.py provides ctx.entry_time_utc OR
        # we derive from ctx.df.index. Tests set ctx.entry_time_utc directly.
        entry_time = getattr(ctx, "entry_time_utc", None)
        if entry_time is None:
            # Fallback: try ctx.df last bar index
            try:
                entry_time = ctx.df.index[-1]
                if hasattr(entry_time, "to_pydatetime"):
                    entry_time = entry_time.to_pydatetime()
            except (AttributeError, IndexError, TypeError):
                return False, 0.0
        try:
            h = entry_time.hour
        except AttributeError:
            return False, 0.0

        if not (7 <= h < 13):  # LDN session only
            return False, 0.0

        adx = getattr(ctx, "adx", None)
        if adx is None:
            return False, 0.0
        try:
            adx = float(adx)
        except (TypeError, ValueError):
            return False, 0.0
        if not (15.0 <= adx <= 30.0):
            return False, 0.0

        # Distance from EMA200 as raw fraction (not ATR-normalized).
        ema200 = getattr(ctx, "ema200", 0.0) or 0.0
        entry_px = getattr(ctx, "entry", 0.0) or 0.0
        if ema200 <= 0 or entry_px <= 0:
            return False, 0.0
        dist_pct = abs(entry_px - ema200) / ema200
        if dist_pct >= 0.005:  # >= 0.5% → not in range vicinity
            return False, 0.0

        # Core boost trigger
        regime_label = None
        if isinstance(getattr(ctx, "regime", None), dict):
            regime_label = ctx.regime.get("regime")
        is_core = (adx >= 25.0) or (regime_label == "RANGE")
        return True, (1.5 if is_core else 1.0)

    # ──────────────────────────────────────────────────
    # メインロジック
    # ──────────────────────────────────────────────────

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        # ── ペアフィルター ──
        _sym = ctx.symbol.upper().replace("=X", "").replace("/", "").replace("_", "")
        if _sym not in self.PAIR_SESSION_MAP:
            return None

        _session_name, _bias_signal = self.PAIR_SESSION_MAP[_sym]

        # ── データ十分性 ──
        if ctx.df is None or len(ctx.df) < 10:
            return None

        # ── 時間帯チェック ──
        _total_min = self._total_minutes(ctx)
        if _total_min < 0:
            return None

        # セッションに基づくエントリーウィンドウ判定
        if _session_name == "TOKYO":
            if _total_min < self.TOKYO_ENTRY_START or _total_min > self.TOKYO_ENTRY_END:
                return None
        elif _session_name == "LONDON":
            if _total_min < self.LONDON_ENTRY_START or _total_min > self.LONDON_ENTRY_END:
                return None
        else:
            return None

        # v8.6: 金曜フィルター撤去 — Breedon & Ranaldo (2013): セッションバイアスは全営業日
        # 保有4-6hで週末前のNYクローズまでにエグジット

        # ── Edge cell filter (added 2026-06-08) ──
        edge_on, lot_mult = self._edge_cell(ctx)
        if not edge_on:
            return None

        # ── ADXフィルター: 極端トレンド排除 ──
        if ctx.adx >= self.ADX_MAX:
            return None

        # ── 確認足: Closeがバイアス方向 ──
        if _bias_signal == "BUY" and ctx.entry <= ctx.open_price:
            return None  # BUYバイアスなのに陰線 → 確認失敗
        if _bias_signal == "SELL" and ctx.entry >= ctx.open_price:
            return None  # SELLバイアスなのに陽線 → 確認失敗

        # ── ATR有効性チェック ──
        if ctx.atr <= 0:
            return None

        # ── v9.1: HTF Hard Block (戦略内self-contained) ──
        # DTE HTF Block (app.py L2464) に加え、戦略内でも独立ガード
        # GBP_USD Live: HTF=bull時にSELL 4/4全敗の根本原因対策
        _htf = ctx.htf or {}
        _htf_agreement = _htf.get("agreement", "mixed")
        if _htf_agreement == "bull" and _bias_signal == "SELL":
            return None  # HTF bullish → SELL ブロック
        if _htf_agreement == "bear" and _bias_signal == "BUY":
            return None  # HTF bearish → BUY ブロック

        # ═══════════════════════════════════════════════════
        # シグナル生成
        # ═══════════════════════════════════════════════════
        signal = _bias_signal
        score = 5.5  # v8.9: 4.0→5.5 (学術根拠★★★★★ + BT WR=69-77%, スコア競争で埋没していた)
        reasons = []
        _dec = 3 if ctx.is_jpy or ctx.pip_mult == 100 else 5

        # SL/TP計算
        if signal == "BUY":
            sl = ctx.entry - ctx.atr * self.SL_ATR_MULT
            tp = ctx.entry + ctx.atr * self.TP_ATR_MULT
        else:  # SELL
            sl = ctx.entry + ctx.atr * self.SL_ATR_MULT
            tp = ctx.entry - ctx.atr * self.TP_ATR_MULT

        # RR検証
        _sl_d = abs(ctx.entry - sl)
        _tp_d = abs(tp - ctx.entry)
        if _sl_d <= 0:
            return None
        _rr = _tp_d / _sl_d
        if _rr < self.MIN_RR:
            return None

        # Reasons
        _session_label = "Tokyo" if _session_name == "TOKYO" else "London"
        _currency = "JPY" if _sym == "USDJPY" else ("EUR" if _sym == "EURUSD" else "GBP")
        reasons.append(
            f"✅ Session Time Bias {signal}: {_session_label}セッション "
            f"{_currency}減価バイアス (Breedon & Ranaldo 2013)"
        )
        reasons.append(
            f"✅ 確認足: Close={ctx.entry:.{_dec}f} vs Open={ctx.open_price:.{_dec}f} "
            f"(バイアス方向一致)"
        )
        reasons.append(
            f"📊 ADX={ctx.adx:.1f} (<{self.ADX_MAX}) RR={_rr:.1f} "
            f"SL={sl:.{_dec}f} TP={tp:.{_dec}f}"
        )

        # ═══════════════════════════════════════════════════
        # スコアボーナス
        # ═══════════════════════════════════════════════════

        # ADX 15-25: レンジ/マイルドトレンド環境 → セッションバイアスが最も効く
        if 15 <= ctx.adx <= 25:
            score += 0.5
            reasons.append(f"✅ ADXレンジ環境({ctx.adx:.1f}: 15-25 → バイアス最適)")

        # 足実体比率 >= 0.40: 方向性の強い確認足
        _bar_range = abs(ctx.prev_high - ctx.prev_low) if ctx.df is not None and len(ctx.df) >= 2 else 0
        _curr_high = float(ctx.df.iloc[-1]["High"]) if ctx.df is not None else ctx.entry
        _curr_low = float(ctx.df.iloc[-1]["Low"]) if ctx.df is not None else ctx.entry
        _curr_range = _curr_high - _curr_low
        if _curr_range > 0:
            _body = abs(ctx.entry - ctx.open_price)
            _body_ratio = _body / _curr_range
            if _body_ratio >= self.MIN_BODY_RATIO:
                score += 0.3
                reasons.append(f"✅ 確認足実体比率({_body_ratio:.0%} >= {self.MIN_BODY_RATIO:.0%})")

        # HTF方向一致ボーナス
        _htf = ctx.htf or {}
        _agr = _htf.get("agreement", "mixed")
        if (signal == "BUY" and _agr == "bull") or \
           (signal == "SELL" and _agr == "bear"):
            score += 0.5
            reasons.append(f"✅ HTF方向一致({_agr})")

        # EMA短期方向一致ボーナス
        if (signal == "BUY" and ctx.ema9 > ctx.ema21) or \
           (signal == "SELL" and ctx.ema9 < ctx.ema21):
            score += 0.3
            reasons.append("✅ EMA短期方向一致")

        conf = int(min(85, 50 + score * 4))
        return Candidate(
            signal=signal, confidence=conf, sl=sl, tp=tp,
            reasons=reasons, entry_type=self.name, score=score,
            lot_multiplier=lot_mult,   # edge cell SIZE lever (added 2026-06-08)
        )
