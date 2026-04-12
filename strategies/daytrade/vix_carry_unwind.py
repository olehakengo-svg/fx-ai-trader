"""
VIX Carry Unwind (VCU) — VIXスパイク時のキャリートレード巻き戻し戦略

学術的根拠:
  - Brunnermeier, Nagel & Pedersen (2009, NBER):
    急激なボラティリティ上昇がキャリートレードの巻き戻しを引き起こす。
    低金利通貨(JPY)が急騰し、高金利通貨(AUD, NZD等)が急落。
  - IMF Working Paper WP/19/136:
    VIXスパイク後の最初の1週間がキャリー巻き戻しの最も急激な局面。

構造的メカニズム:
  リスクオフ局面でVIXが急騰 → キャリートレーダーがJPYショートを解消
  → JPY急騰(USD/JPY急落)。巻き戻しは数日-1週間続く。
  VIX直接参照不可のため、ATR拡大率(5日/20日)をVIXプロキシとして使用。

戦略コンセプト:
  - USD/JPY専用 (SELL方向のみ = JPY強化)
  - 低頻度イベント戦略 (年2-5回)
  - VIXプロキシ: 5日ATR / 20日ATR > 1.8 (ボラ倍増)
  - 代替判定: 日足レンジ > 3× 平均日足レンジ (極端な1日)
  - 広いSL/TP (イベントドリブンの大きな動きに対応)
  - 最大5日保持
"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from typing import Optional


class VixCarryUnwind(StrategyBase):
    name = "vix_carry_unwind"
    mode = "daytrade"
    enabled = True

    # ── 対象通貨ペア ──
    _enabled_symbols = {"USDJPY"}

    # ══════════════════════════════════════════════════
    # パラメータ定数
    # ══════════════════════════════════════════════════

    # ── VIXプロキシ ──
    ATR_SHORT_PERIOD = 5         # 短期ATR期間
    ATR_LONG_PERIOD  = 20        # 長期ATR期間
    VIX_PROXY_THRESH = 1.8       # 短期ATR / 長期ATR > 1.8 でVIXスパイクとみなす

    # ── 代替判定: 極端な日足レンジ ──
    EXTREME_RANGE_MULT = 3.0     # 日足レンジ > 平均 × 3.0 で極端な日とみなす
    RANGE_LOOKBACK     = 20      # 平均日足レンジ計算期間

    # ── エントリー条件 ──
    REQUIRE_BEARISH_BAR = True   # 陰線必須 (Close < Open)
    REQUIRE_BELOW_EMA21 = True   # Price < EMA21 必須

    # ── EMAフィルター ──
    REQUIRE_EMA_CROSS   = True   # EMA9 < EMA21 必須 (トレンド転換確認)

    # ── SL/TP ──
    SL_ATR_MULT      = 2.0       # SL = ATR(15m) × 2.0 (イベント駆動のボラに対応)
    TP_ATR_MULT      = 4.0       # TP = ATR(15m) × 4.0 (巻き戻し 100-500pip)
    MIN_RR           = 1.5       # 最低リスクリワード比

    # ── 保持 ──
    MAX_HOLD_BARS    = 32        # 最大32バー (8時間 @ 15m × 5日 ≈ 32bars/day相当)
    # 実際の5日保持は demo_trader の MAX_HOLD 設定で制御

    # ── スコアリング ──
    ATR_RATIO_BONUS_STEP = 0.5   # ATR比が閾値を0.5上回るごとに +0.5点
    EMA_ALIGN_BONUS      = 0.5   # EMA9 < EMA21 アライメントボーナス

    # ──────────────────────────────────────────────────
    # ヘルパー
    # ──────────────────────────────────────────────────

    def _calc_atr_ratio(self, ctx: SignalContext) -> Optional[float]:
        """5日ATR / 20日ATR 比率を計算。

        15m足データから近似計算:
        - 5日 ATR ≈ 直近 5 × (24h/15m) = 480本 → 簡略化: 直近20本のATRを使用
        - 20日 ATR ≈ 直近 20 × (24h/15m) → 簡略化: ctx.atr (14期間 = 約3.5時間)
        実際にはdfの行数に基づいて近似ATRを計算
        """
        df = ctx.df
        if df is None or len(df) < 40:
            return None

        # 短期ATR: 直近5本の True Range 平均
        _short_trs = []
        for i in range(min(self.ATR_SHORT_PERIOD, len(df) - 1)):
            idx = len(df) - 1 - i
            _h = float(df.iloc[idx]["High"])
            _l = float(df.iloc[idx]["Low"])
            _pc = float(df.iloc[idx - 1]["Close"]) if idx > 0 else _l
            _tr = max(_h - _l, abs(_h - _pc), abs(_l - _pc))
            _short_trs.append(_tr)

        # 長期ATR: 直近20本の True Range 平均
        _long_trs = []
        for i in range(min(self.ATR_LONG_PERIOD, len(df) - 1)):
            idx = len(df) - 1 - i
            _h = float(df.iloc[idx]["High"])
            _l = float(df.iloc[idx]["Low"])
            _pc = float(df.iloc[idx - 1]["Close"]) if idx > 0 else _l
            _tr = max(_h - _l, abs(_h - _pc), abs(_l - _pc))
            _long_trs.append(_tr)

        if not _short_trs or not _long_trs:
            return None

        _short_atr = sum(_short_trs) / len(_short_trs)
        _long_atr = sum(_long_trs) / len(_long_trs)

        if _long_atr <= 0:
            return None

        return _short_atr / _long_atr

    def _check_extreme_daily_range(self, ctx: SignalContext) -> bool:
        """現在の日足レンジ > 平均日足レンジ × 3.0 かチェック。

        15m足しかないため、当日のH/Lレンジと過去バーの平均レンジで近似。
        """
        df = ctx.df
        if df is None or len(df) < self.RANGE_LOOKBACK + 5:
            return False

        # 現在足の High-Low レンジ (当日の近似)
        _curr_range = float(df.iloc[-1]["High"]) - float(df.iloc[-1]["Low"])

        # 過去20本の平均レンジ
        _ranges = []
        for i in range(1, min(self.RANGE_LOOKBACK + 1, len(df))):
            idx = len(df) - 1 - i
            _r = float(df.iloc[idx]["High"]) - float(df.iloc[idx]["Low"])
            _ranges.append(_r)

        if not _ranges:
            return False

        _avg_range = sum(_ranges) / len(_ranges)
        if _avg_range <= 0:
            return False

        return _curr_range > _avg_range * self.EXTREME_RANGE_MULT

    # ──────────────────────────────────────────────────
    # メインロジック
    # ──────────────────────────────────────────────────

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        # ── ペアフィルター: USD/JPY専用 ──
        _sym = ctx.symbol.upper().replace("=X", "").replace("/", "").replace("_", "")
        if _sym not in self._enabled_symbols:
            return None

        # ── データ十分性 ──
        if ctx.df is None or len(ctx.df) < 40:
            return None

        # ── VIXプロキシ: ATR拡大率チェック ──
        _atr_ratio = self._calc_atr_ratio(ctx)
        _vix_spike = False
        _extreme_day = False

        if _atr_ratio is not None and _atr_ratio > self.VIX_PROXY_THRESH:
            _vix_spike = True

        # ── 代替判定: 極端な日足レンジ ──
        if not _vix_spike:
            _extreme_day = self._check_extreme_daily_range(ctx)

        # どちらも非該当なら見送り
        if not _vix_spike and not _extreme_day:
            return None

        # ── EMAフィルター: EMA9 < EMA21 (トレンド転換確認) ──
        if self.REQUIRE_EMA_CROSS and ctx.ema9 >= ctx.ema21:
            return None

        # ── Price < EMA21 (下降トレンド確認) ──
        if self.REQUIRE_BELOW_EMA21 and ctx.entry >= ctx.ema21:
            return None

        # ── 陰線確認 (Close < Open) ──
        if self.REQUIRE_BEARISH_BAR and ctx.entry >= ctx.open_price:
            return None

        # ── 金曜ブロック (週末リスクでキャリー巻き戻し不安定) ──
        if ctx.is_friday:
            return None

        # ═══════════════════════════════════════════════════
        # SELL USD/JPY (JPY強化 = USD/JPY下落)
        # ═══════════════════════════════════════════════════
        signal = "SELL"

        # ── HTFフィルター: 強bullではSELL禁止 ──
        _htf = ctx.htf or {}
        _agr = _htf.get("agreement", "mixed")
        if _agr == "bull":
            return None

        # ═══════════════════════════════════════════════════
        # SL/TP計算
        # ═══════════════════════════════════════════════════
        sl_dist = ctx.atr * self.SL_ATR_MULT
        tp_dist = ctx.atr * self.TP_ATR_MULT

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
            tp = ctx.entry - _tp_d
            _rr = _tp_d / _sl_d

        if _rr < self.MIN_RR:
            return None

        # ═══════════════════════════════════════════════════
        # スコアリング & Reasons
        # ═══════════════════════════════════════════════════
        score = 5.0  # イベント駆動戦略: 高い初期スコア
        reasons = []

        if _vix_spike:
            reasons.append(
                f"✅ VCU SELL USD/JPY: VIXプロキシスパイク検出 "
                f"(ATR比={_atr_ratio:.2f}>{self.VIX_PROXY_THRESH} "
                f"— Brunnermeier et al. 2009)"
            )
            # ATR比のマグニチュードボーナス (+0.5 per 0.5x above threshold)
            _excess = _atr_ratio - self.VIX_PROXY_THRESH
            _magnitude_bonus = (_excess / self.ATR_RATIO_BONUS_STEP) * 0.5
            _magnitude_bonus = min(_magnitude_bonus, 2.0)  # キャップ
            if _magnitude_bonus > 0:
                score += _magnitude_bonus
                reasons.append(
                    f"✅ ATR比マグニチュード (+{_magnitude_bonus:.1f})"
                )
        elif _extreme_day:
            reasons.append(
                f"✅ VCU SELL USD/JPY: 極端な日足レンジ検出 "
                f"(>avg×{self.EXTREME_RANGE_MULT:.0f} — IMF WP/19/136)"
            )
            score += 0.5

        # ── 陰線確認ボーナス ──
        reasons.append(
            f"✅ 陰線確認: Close={ctx.entry:.3f} < Open={ctx.open_price:.3f}"
        )

        # ── EMAアライメントボーナス ──
        if ctx.ema9 < ctx.ema21:
            score += self.EMA_ALIGN_BONUS
            reasons.append(
                f"✅ EMAアライメント: EMA9({ctx.ema9:.3f}) < EMA21({ctx.ema21:.3f})"
            )

        # ── Price below EMA21 ──
        reasons.append(
            f"✅ Price < EMA21: {ctx.entry:.3f} < {ctx.ema21:.3f}"
        )

        # ── HTF方向一致ボーナス ──
        if _agr == "bear":
            score += 0.5
            reasons.append(f"✅ HTF方向一致({_agr})")

        # ── ADX高値 = トレンド強度ボーナス ──
        if ctx.adx > 25:
            score += 0.3
            reasons.append(f"✅ ADXトレンド強度({ctx.adx:.1f}>25)")

        # ── RSI過売ゾーン接近ボーナス ──
        if ctx.rsi < 40:
            score += 0.3
            reasons.append(f"✅ RSI売り圧力確認(RSI={ctx.rsi:.0f}<40)")

        reasons.append(f"📊 RR={_rr:.1f} SL={sl:.3f} TP={tp:.3f}")

        # ── Confidence計算 ──
        conf = int(min(90, 50 + score * 4))

        return Candidate(
            signal=signal, confidence=conf, sl=sl, tp=tp,
            reasons=reasons, entry_type=self.name, score=score
        )
