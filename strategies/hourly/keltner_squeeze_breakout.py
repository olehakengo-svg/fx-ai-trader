"""
Keltner Squeeze Breakout (KSB) — 1H足ボラティリティ圧縮→爆発

学術的根拠:
  - Bollinger (2001): BB squeeze（BB幅がKeltner内に収縮）がボラ爆発の前兆
  - Keltner (1960) / ATR-based channel: ボラティリティ正規化チャネル
  - Brock, Lakonishok & LeBaron (1992, JoF): チャネルブレイクアウトの統計的有意性
  - Schulmeister (2009): FXテクニカルルールの1H以上TFでの有効性

戦略コンセプト:
  1H足でBB(20,2.0)がKeltner(20,1.5)チャネル内に収縮（スクイーズ）した後、
  スクイーズが解除される方向にエントリー。

  Scalp bb_squeeze_breakout (1m, 19t WR=36.8%) が失敗した理由:
  - 1mのスクイーズ = 数分のランダム狭小 → ノイズ圧縮にすぎない
  - 1Hのスクイーズ 6本以上 = 6時間以上の本物のボラ収縮 → 機関のポジション蓄積

  15mでブレイクアウトが失敗した理由と1Hでの優位性:
  - 15m足: ヒゲがレジスタンスを一瞬突破→反転（偽ブレイク）が頻発
  - 1H足: ヒゲが実体に吸収 → Close基準のブレイクが本物の資金流入を反映

エントリーロジック:
  ■ スクイーズ検出 (前N本):
    1. squeeze_on = True (BB上限 < Keltner上限 AND BB下限 > Keltner下限)
    2. スクイーズ継続 ≥ MIN_SQUEEZE_BARS 本 (6時間以上の圧縮)

  ■ スクイーズ放出 (現在足):
    3. squeeze_on → False (スクイーズ解除)
    4. Close > Keltner上限 (BUY) or Close < Keltner下限 (SELL)
    5. ブレイク足の実体 ≥ バーレンジの BODY_RATIO_MIN (本気のブレイク)

  ■ モメンタム確認:
    6. MACD-H: 方向一致 かつ 前足より拡大
    7. ADX ≥ ADX_MIN or ADX前足比 +3以上上昇 (トレンド開始)

  ■ HTFフィルター (実4H+1Dデータ使用):
    8. htf agreement != 逆方向

SL/TP:
  SL: スクイーズ期間のswing low/high - ATR×0.3、最大ATR×SL_MAX_ATR_MULT(1.5)で制限
  TP: ATR(14) × TP_ATR_MULT (50pip+目標)
  BE: TP×BE_TRIGGER_PCT到達でSL→BE+1pip
  Trailing: BE後、直近N本の安値/高値 - ATR×TRAIL_ATR_MULT で追従
"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from typing import Optional


class KeltnerSqueezeBreakout(StrategyBase):
    name = "keltner_squeeze_breakout"
    mode = "hourly"
    enabled = True

    # ══════════════════════════════════════════════════
    # ペア別パラメータ定数
    # ══════════════════════════════════════════════════

    # ── スクイーズ検出 ──
    MIN_SQUEEZE_BARS_JPY = 3    # USD/JPY: 最低3時間の圧縮 (6→3: 放出頻度改善)
    MIN_SQUEEZE_BARS_EUR = 3    # EUR/USD: 最低3時間の圧縮 (6→3: 放出頻度改善)
    MAX_SQUEEZE_BARS = 30       # 30時間超のスクイーズ = デッドマーケット

    # ── ブレイク検出 ──
    # スクイーズ検出: BB inside Keltner(ATR×1.5) — indicators.pyで定義
    # ブレイク確認: Keltner(ATR×1.2)基準 — ATR×1.5では28→7件しかブレイク通過しない
    KELT_BREAK_MULT = 0.80      # break threshold = kelt_mid + (kelt_upper-kelt_mid)*0.80 ≈ ATR×1.2
    BODY_RATIO_MIN = 0.35       # ブレイク足の実体 ≥ バーレンジの35% (0.45→0.35: EUR対応)

    # ── ADX ──
    ADX_MIN_JPY = 15            # USD/JPY: トレンド開始検出 (18→15: 圧縮後ADXは構造的に低い)
    ADX_MIN_EUR = 15            # EUR/USD: トレンド開始検出 (18→15: 圧縮後ADXは構造的に低い)
    ADX_RISE_THRESHOLD = 2.0    # ADX前足比で+2以上 = トレンド開始 (3.0→2.0: 圧縮後緩和)

    # ── SL/TP ──
    SL_MAX_ATR_MULT = 1.5       # SL最大距離 = ATR × 1.5 (2.0→1.5: SL 40-60pip→30-45pip, RR 1.5→2.0)
    TP_ATR_MULT_JPY = 3.0       # TP = ATR × 3.0 (JPY ATR≈25pip → TP≈75pip)
    TP_ATR_MULT_EUR = 3.0       # TP = ATR × 3.0 (EUR ATR≈15pip → TP≈45pip)
    MIN_RR = 1.5                # 最低リスクリワード比

    # ── BE / トレーリング ──
    BE_TRIGGER_PCT = 0.50       # TP50%到達でSL→BE+1pip
    TRAIL_ATR_MULT = 1.5        # トレーリング: 直近高値/安値 - ATR×1.5

    # ── 最大保持 ──
    MAX_HOLD_BARS = 24          # 24時間

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        # ── USD/JPY無効化: WR=33.3% EV=+2.2pip → 実環境スプレッド/スリッページで負EV転落リスク大 ──
        if ctx.is_jpy:
            return None

        # ── DataFrame十分性チェック ──
        if ctx.df is None or len(ctx.df) < 20:
            return None

        # ── squeeze_on列の存在チェック ──
        if "squeeze_on" not in ctx.df.columns:
            return None
        if "kelt_upper" not in ctx.df.columns:
            return None

        # ── ペア別パラメータ選択 ──
        if ctx.is_jpy:
            _min_sq = self.MIN_SQUEEZE_BARS_JPY
            _adx_min = self.ADX_MIN_JPY
            _tp_mult = self.TP_ATR_MULT_JPY
        else:
            _min_sq = self.MIN_SQUEEZE_BARS_EUR
            _adx_min = self.ADX_MIN_EUR
            _tp_mult = self.TP_ATR_MULT_EUR

        # ═══════════════════════════════════════════════════
        # 条件1-2: スクイーズ検出 — 前N本で連続squeeze_on=True
        # ═══════════════════════════════════════════════════
        _curr_squeeze = bool(ctx.df["squeeze_on"].iloc[-1])

        # 現在足でスクイーズ中 = まだ放出されていない → WAIT
        if _curr_squeeze:
            return None

        # 直前バーまでのスクイーズ連続長を計測
        _sq_count = 0
        for i in range(2, min(self.MAX_SQUEEZE_BARS + 3, len(ctx.df))):
            if bool(ctx.df["squeeze_on"].iloc[-i]):
                _sq_count += 1
            else:
                break

        # 最低スクイーズ長チェック
        if _sq_count < _min_sq:
            return None

        # デッドマーケット排除
        if _sq_count > self.MAX_SQUEEZE_BARS:
            return None

        # ═══════════════════════════════════════════════════
        # 条件3-4: スクイーズ放出方向の確認
        # ═══════════════════════════════════════════════════
        _kelt_upper = float(ctx.df["kelt_upper"].iloc[-1])
        _kelt_lower = float(ctx.df["kelt_lower"].iloc[-1])
        _kelt_mid = float(ctx.df["kelt_mid"].iloc[-1])
        _close = ctx.entry
        _open = ctx.open_price

        # ブレイク閾値: Keltner(ATR×1.5)の80% = 実質ATR×1.2相当
        # スクイーズ検出はATR×1.5を使うが、ブレイク確認は緩和
        _break_upper = _kelt_mid + (_kelt_upper - _kelt_mid) * self.KELT_BREAK_MULT
        _break_lower = _kelt_mid - (_kelt_mid - _kelt_lower) * self.KELT_BREAK_MULT

        _is_buy = _close > _break_upper
        _is_sell = _close < _break_lower

        if not _is_buy and not _is_sell:
            return None  # Keltnerバンド内 → 不明確な放出

        # ═══════════════════════════════════════════════════
        # 条件5: ブレイク足の品質 — 実体比率
        # ═══════════════════════════════════════════════════
        _bar_range = float(ctx.df.iloc[-1]["High"]) - float(ctx.df.iloc[-1]["Low"])
        _body = abs(_close - _open)
        _body_ratio = _body / _bar_range if _bar_range > 0 else 0

        if _body_ratio < self.BODY_RATIO_MIN:
            return None

        # 方向確認: ブレイク足が陽線(BUY)/陰線(SELL)
        if _is_buy and _close <= _open:
            return None
        if _is_sell and _close >= _open:
            return None

        # ═══════════════════════════════════════════════════
        # 条件6: MACD-Hモメンタム確認
        # ═══════════════════════════════════════════════════
        if _is_buy:
            if ctx.macdh <= 0:
                return None
            if ctx.macdh_prev >= ctx.macdh:
                return None  # 拡大していない
        else:
            if ctx.macdh >= 0:
                return None
            if ctx.macdh_prev <= ctx.macdh:
                return None  # 縮小していない

        # ═══════════════════════════════════════════════════
        # 条件7: ADXトレンド開始検出
        # ═══════════════════════════════════════════════════
        _adx_rising = False
        if len(ctx.df) >= 2 and "adx" in ctx.df.columns:
            _prev_adx = float(ctx.df["adx"].iloc[-2])
            _adx_rising = (ctx.adx - _prev_adx) >= self.ADX_RISE_THRESHOLD

        if ctx.adx < _adx_min and not _adx_rising:
            return None

        # ═══════════════════════════════════════════════════
        # 条件8: HTFハードフィルター
        # ═══════════════════════════════════════════════════
        _htf = ctx.htf or {}
        _agreement = _htf.get("agreement", "mixed")
        if _is_buy and _agreement == "bear":
            return None
        if _is_sell and _agreement == "bull":
            return None

        # ── EMA200方向: ソフトペナルティ (ハード→ソフト変更) ──
        # 圧縮後のブレイクはEMA200付近で発生することがあるため、
        # ハードブロックではなくスコア減算で対応
        _ema200_aligned = True
        if _is_buy and ctx.entry < ctx.ema200:
            _ema200_aligned = False
        if _is_sell and ctx.entry > ctx.ema200:
            _ema200_aligned = False

        # ═══════════════════════════════════════════════════
        # シグナル生成
        # ═══════════════════════════════════════════════════
        signal = "BUY" if _is_buy else "SELL"
        score = 5.0  # 1H戦略は基本スコア高め
        reasons = []

        # ── SL: スクイーズ期間のスイングHL + ATR×MAX cap ──
        # 旧: 反対側Keltnerバンド → SLが140pipと巨大化する問題
        # 新: スクイーズ中のswing low/high + ATRバッファ、最大ATR×1.5で制限
        _sq_start = -(1 + _sq_count)
        _sq_end = -1
        if _is_buy:
            # BUY: SL = スクイーズ中のLow最低値 - ATR×0.3
            _swing_low = float(ctx.df["Low"].iloc[_sq_start:_sq_end].min())
            _sl_raw = _swing_low - ctx.atr * 0.3
            # ATR×MAX_ATR_MULT で制限
            _max_sl_dist = ctx.atr * self.SL_MAX_ATR_MULT
            sl = max(_sl_raw, ctx.entry - _max_sl_dist)
        else:
            # SELL: SL = スクイーズ中のHigh最高値 + ATR×0.3
            _swing_high = float(ctx.df["High"].iloc[_sq_start:_sq_end].max())
            _sl_raw = _swing_high + ctx.atr * 0.3
            # ATR×MAX_ATR_MULT で制限
            _max_sl_dist = ctx.atr * self.SL_MAX_ATR_MULT
            sl = min(_sl_raw, ctx.entry + _max_sl_dist)

        # ── TP: ATR × TP_MULT ──
        _sl_dist = abs(ctx.entry - sl)
        _tp_target = ctx.atr * _tp_mult
        _tp_min_rr = _sl_dist * self.MIN_RR
        _tp_dist = max(_tp_target, _tp_min_rr)

        if _is_buy:
            tp = ctx.entry + _tp_dist
        else:
            tp = ctx.entry - _tp_dist

        # ── RR最低保証 ──
        if _sl_dist <= 0 or _tp_dist / _sl_dist < self.MIN_RR:
            return None

        # ═══════════════════════════════════════════════════
        # Reasons & ボーナス
        # ═══════════════════════════════════════════════════
        _pair_label = "JPY" if ctx.is_jpy else "EUR"
        _rr = _tp_dist / _sl_dist if _sl_dist > 0 else 0
        _sl_pip = _sl_dist * ctx.pip_mult
        _tp_pip = _tp_dist * ctx.pip_mult

        reasons.append(
            f"✅ KSB {signal}: スクイーズ{_sq_count}本({_sq_count}h)→放出 "
            f"(Bollinger 2001 / Keltner 1960)"
        )
        reasons.append(
            f"✅ Keltnerブレイク: Close={ctx.entry:.3f} "
            f"{'>' if _is_buy else '<'} "
            f"{'Upper' if _is_buy else 'Lower'}(80%)="
            f"{_break_upper if _is_buy else _break_lower:.3f}"
        )
        reasons.append(
            f"✅ 実体比率: {_body_ratio:.0%}≥{self.BODY_RATIO_MIN:.0%}"
        )
        reasons.append(
            f"✅ MACD-H加速: {ctx.macdh:.4f} "
            f"({'拡大' if _is_buy else '縮小'}中)"
        )
        reasons.append(
            f"📊 RR={_rr:.1f} SL={_sl_pip:.1f}pip TP={_tp_pip:.1f}pip ({_pair_label})"
        )

        # ── ボーナス / ペナルティ条件 ──

        # EMA200方向: 一致=ボーナス, 不一致=ペナルティ
        if _ema200_aligned:
            score += 0.3
            reasons.append(f"✅ EMA200方向一致")
        else:
            score -= 0.5
            reasons.append(f"⚠️ EMA200逆方向 (ペナルティ)")

        # 長スクイーズ: 12本以上 = 12時間以上の圧縮→爆発力大
        if _sq_count >= 12:
            score += 0.5
            reasons.append(f"✅ 長スクイーズ({_sq_count}h≥12) — 爆発力大")

        # ADX上昇ボーナス
        if _adx_rising:
            score += 0.5
            reasons.append(f"✅ ADX急上昇(+{ctx.adx - _prev_adx:.1f})")

        # HTF方向一致ボーナス
        if (_is_buy and _agreement == "bull") or \
           (_is_sell and _agreement == "bear"):
            score += 0.5
            reasons.append(f"✅ HTF方向一致({_agreement})")

        # EMAパーフェクトオーダーボーナス
        if _is_buy and ctx.ema9 > ctx.ema21 > ctx.ema50:
            score += 0.3
            reasons.append("✅ EMAパーフェクトオーダー(9>21>50)")
        elif _is_sell and ctx.ema9 < ctx.ema21 < ctx.ema50:
            score += 0.3
            reasons.append("✅ EMAパーフェクトオーダー(9<21<50)")

        # 高RRボーナス
        if _rr >= 2.5:
            score += 0.3
            reasons.append(f"✅ 高RR({_rr:.1f}≥2.5)")

        conf = int(min(90, 50 + score * 4))
        return Candidate(
            signal=signal, confidence=conf, sl=sl, tp=tp,
            reasons=reasons, entry_type=self.name, score=score
        )
