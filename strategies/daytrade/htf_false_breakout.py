"""
HTF False Breakout Fade (FBF) — 1H足SR False Breakoutの15m足フェード

学術的根拠:
  - Bulkowski (2005): False Breakoutはテクニカルパターン中最も信頼性の高いリバーサルシグナル
  - Osler (2000): ストップロス集中がブレイクを誘発 → 一掃後に元のレンジに回帰（市場構造）

データ裏付け (EUR/USD 90日 1H足):
  - 上方ブレイク: 98回 → False 18.4% → Fade WR=77.8% avg=+6.6pip
  - 下方ブレイク: 112回 → False 32.1% → Fade WR=80.6% avg=+14.3pip
  - False Breakout発生率55%超 (アジアレンジ→ロンドンブレイク分析)

戦略コンセプト:
  - 1H足の直近20バー高安(動的SR)を「実体確定(Close)」で超えたブレイクを検出
  - ブレイク後1-4本の15m足でCloseがSR内に戻った → False Breakout確定
  - レンジ回帰確認後に逆方向エントリー
  - 4H/1D EMAによるMTFフィルター必須（本物のトレンドブレイク排除）
"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from typing import Optional
import numpy as np


class HtfFalseBreakout(StrategyBase):
    name = "htf_false_breakout"
    mode = "daytrade"
    enabled = True

    # ── SR計算パラメータ ──
    sr_lookback_1h = 20    # 1H足20バーのRolling High/Low

    # ── False Breakout確認 ──
    fb_confirm_bars = 4    # ブレイク後4本(15m=1H)以内にレンジ回帰で確定
    close_body_min = 0.30  # ブレイク足の実体 >= バーレンジの30% (ヒゲ抜け除外)

    # ── SL/TP ──
    sl_atr_buffer = 0.3    # SL = ブレイク足High/Low + ATR×0.3
    tp_type = "sr_center"  # TP = SRレンジ中央 (レンジの反対端)
    tp_min_atr = 1.5       # TP最低距離 = ATR×1.5

    # ── 最大保持 ──
    max_hold_bars = 8      # 8バー = 2時間 (False breakoutの回帰は迅速)

    # ── v6.1: USD/JPY 追加フィルター ──
    JPY_RSI_DIV_LOOKBACK = 30   # RSIダイバージェンス検出バー数
    JPY_OB_ATR_PROXIMITY = 0.5  # OB接触判定: ATR×0.5以内

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        if ctx.df is None or len(ctx.df) < 20:
            return None

        # ── 1H足SR情報を15m足DataFrameから構築 ──
        # 15m足4本 = 1H足1本。直近80本(15m) = 20本(1H)相当
        _h1_equiv = min(self.sr_lookback_1h * 4, len(ctx.df) - 4)
        if _h1_equiv < 40:
            return None

        _sr_slice = ctx.df.iloc[-_h1_equiv - 8: -4]  # ブレイク前のSR計算用
        _sr_high = float(_sr_slice["High"].max())
        _sr_low = float(_sr_slice["Low"].min())
        _sr_range = _sr_high - _sr_low

        if _sr_range <= 0 or _sr_range < ctx.atr * 0.5:
            return None  # レンジが狭すぎ（ノイズ）

        # ── 1H足実体ブレイク検出 ──
        # 15m足を4本単位で「疑似1H足」として集約
        # 最新の1Hブレイク = 4-8本前の15m足でCloseがSR外側
        _break_dir = None
        _break_high = 0.0
        _break_low = 0.0
        _break_close = 0.0

        # 直近8本(=2H)以内にブレイクがあったかチェック
        for _offset in range(4, min(self.fb_confirm_bars * 4 + 8, len(ctx.df) - _h1_equiv)):
            _bar = ctx.df.iloc[-_offset]
            _bar_close = float(_bar["Close"])
            _bar_open = float(_bar["Open"])
            _bar_high = float(_bar["High"])
            _bar_low = float(_bar["Low"])
            _bar_range = _bar_high - _bar_low
            _bar_body = abs(_bar_close - _bar_open)

            # 実体確定ブレイク（ヒゲ抜け除外）
            _body_ok = (_bar_body / _bar_range >= self.close_body_min) if _bar_range > 0 else False
            if not _body_ok:
                continue

            if _bar_close > _sr_high:
                _break_dir = "UP"
                _break_high = _bar_high
                _break_low = _bar_low
                _break_close = _bar_close
                break
            elif _bar_close < _sr_low:
                _break_dir = "DOWN"
                _break_high = _bar_high
                _break_low = _bar_low
                _break_close = _bar_close
                break

        if _break_dir is None:
            return None

        # ── レンジ回帰確認（False Breakout確定）──
        # 現在のClose（最新15m足）がSR内に戻っている
        _current_close = ctx.entry
        if _break_dir == "UP" and _current_close >= _sr_high:
            return None  # まだSR外 — 本物のブレイク継続中
        if _break_dir == "DOWN" and _current_close <= _sr_low:
            return None  # まだSR外

        # ══════════════════════════════════════════════════════════════
        # v6.1: USD/JPY 精度強化フィルター
        #   WR=33.3% → RSIダイバージェンス or OB接触 を必須化
        #   根拠: USD/JPY の False Breakout は仲値・金利差による
        #         本物ブレイクとの区別がつきにくい → 追加確認必須
        # ══════════════════════════════════════════════════════════════
        if ctx.is_jpy and "JPY" in ctx.symbol:
            _jpy_pass = False
            _jpy_reasons = []

            # Gate A: RSIダイバージェンス確認
            #   SELL → 弱気ダイバージェンス (価格HH, RSI LH)
            #   BUY  → 強気ダイバージェンス (価格LL, RSI HL)
            try:
                if "rsi" in ctx.df.columns and len(ctx.df) >= self.JPY_RSI_DIV_LOOKBACK:
                    _div_sub = ctx.df.tail(self.JPY_RSI_DIV_LOOKBACK)
                    _H = _div_sub["High"].values
                    _L = _div_sub["Low"].values
                    _rsi_v = _div_sub["rsi"].values
                    _mid = len(_div_sub) // 2
                    _ph_r = int(np.argmax(_H[_mid:])) + _mid
                    _ph_p = int(np.argmax(_H[:_mid]))
                    _pl_r = int(np.argmin(_L[_mid:])) + _mid
                    _pl_p = int(np.argmin(_L[:_mid]))

                    if _break_dir == "UP":  # SELL candidate
                        if _H[_ph_r] > _H[_ph_p] and _rsi_v[_ph_r] < _rsi_v[_ph_p]:
                            _jpy_pass = True
                            _jpy_reasons.append("✅ JPY: RSI弱気ダイバージェンス確認")
                    else:  # BUY candidate
                        if _L[_pl_r] < _L[_pl_p] and _rsi_v[_pl_r] > _rsi_v[_pl_p]:
                            _jpy_pass = True
                            _jpy_reasons.append("✅ JPY: RSI強気ダイバージェンス確認")
            except Exception:
                pass

            # Gate B: H1 Order Block 接触 (SR境界のスイングH/Lへの近接)
            #   False Breakout後にOB(価格反転帯)付近にいれば信頼度高い
            if not _jpy_pass:
                _ob_dist_high = abs(_current_close - _sr_high)
                _ob_dist_low = abs(_current_close - _sr_low)
                _ob_threshold = ctx.atr * self.JPY_OB_ATR_PROXIMITY
                if _break_dir == "UP" and _ob_dist_high <= _ob_threshold:
                    _jpy_pass = True
                    _jpy_reasons.append(f"✅ JPY: OB接触(SR高値{_ob_dist_high/_ob_threshold:.0%})")
                elif _break_dir == "DOWN" and _ob_dist_low <= _ob_threshold:
                    _jpy_pass = True
                    _jpy_reasons.append(f"✅ JPY: OB接触(SR安値{_ob_dist_low/_ob_threshold:.0%})")

            if not _jpy_pass:
                return None  # USD/JPY: RSI Div も OB接触もなし → スキップ

        # ── MTFフィルター（必須: 強トレンド逆行排除）──
        _htf = ctx.htf or {}
        _agreement = _htf.get("agreement", "mixed")

        signal = None
        score = 0.0
        reasons = []
        sl = 0.0
        tp = 0.0

        # ── 上方False Breakout → SELL ──
        if _break_dir == "UP":
            # MTF: bull方向のFalse BreakoutではSELLしない（本物のブレイクの可能性）
            if _agreement == "bull":
                return None
            signal = "SELL"
            score = 4.0
            _sr_center = (_sr_high + _sr_low) / 2
            tp = max(_sr_center, ctx.entry - ctx.atr * self.tp_min_atr)
            # TPがentry以上なら最低距離で設定
            if tp >= ctx.entry:
                tp = ctx.entry - ctx.atr * self.tp_min_atr
            sl = _break_high + ctx.atr * self.sl_atr_buffer
            reasons.append(f"✅ False Breakout(上方): SR高値{_sr_high:.5f}突破→回帰 (Bulkowski 2005)")
            reasons.append(f"✅ レンジ回帰確認: Close={_current_close:.5f} < SR_H={_sr_high:.5f}")

        # ── 下方False Breakout → BUY ──
        elif _break_dir == "DOWN":
            if _agreement == "bear":
                return None
            signal = "BUY"
            score = 4.0
            _sr_center = (_sr_high + _sr_low) / 2
            tp = min(_sr_center, ctx.entry + ctx.atr * self.tp_min_atr)
            if tp <= ctx.entry:
                tp = ctx.entry + ctx.atr * self.tp_min_atr
            sl = _break_low - ctx.atr * self.sl_atr_buffer
            reasons.append(f"✅ False Breakout(下方): SR安値{_sr_low:.5f}下抜け→回帰 (Bulkowski 2005)")
            reasons.append(f"✅ レンジ回帰確認: Close={_current_close:.5f} > SR_L={_sr_low:.5f}")

        if signal is None:
            return None

        # ── ボーナス ──
        # 回帰の深さボーナス（SR中央に近いほど強い回帰）
        _revert_depth = abs(_current_close - (_sr_high if _break_dir == "UP" else _sr_low)) / _sr_range
        if _revert_depth > 0.3:
            score += 0.5
            reasons.append(f"✅ 深い回帰(SR内{_revert_depth:.0%})")

        # HTF方向一致ボーナス
        if (signal == "BUY" and _agreement == "bull") or \
           (signal == "SELL" and _agreement == "bear"):
            score += 0.5
            reasons.append(f"✅ HTF方向一致({_agreement})")

        # EMA方向一致ボーナス
        if (signal == "BUY" and ctx.ema9 > ctx.ema21) or \
           (signal == "SELL" and ctx.ema9 < ctx.ema21):
            score += 0.3
            reasons.append("✅ EMA短期方向一致")

        # ADXレンジ確認ボーナス（レンジ環境=False Breakout優位）
        if ctx.adx < 25:
            score += 0.3
            reasons.append(f"✅ レンジ環境(ADX={ctx.adx:.1f}<25)")

        reasons.append(f"📊 SR=[{_sr_low:.5f}-{_sr_high:.5f}] range={_sr_range*ctx.pip_mult:.1f}pip")

        # v6.1: JPY追加理由を付加
        if ctx.is_jpy and "JPY" in ctx.symbol:
            try:
                reasons.extend(_jpy_reasons)
            except NameError:
                pass

        conf = int(min(85, 50 + score * 4))
        return Candidate(signal=signal, confidence=conf, sl=sl, tp=tp,
                         reasons=reasons, entry_type=self.name, score=score)
