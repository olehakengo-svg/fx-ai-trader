"""
GBP Deep Pullback — GBP/USD ディープ押し目/戻り目エントリー

学術的根拠:
  - Wilder (1978): ADX≥20でトレンド存在を定量的に識別
  - Menkhoff et al. (2012): FX市場におけるモメンタム効果の普遍性
  - Bollinger (2002): BB-2σタッチは統計的に価格の過延長を示唆

実装背景:
  - ADX TC EUR/USD: 15t WR=78.6% EV=+1.706 → EUR/USD専用で成功
  - ADX TC GBP/USD: 11t WR=36.4% EV=-1.618 → ボラ過大で浅い押し目が機能せず
  - 仮説: GBP/USDはボラティリティが高く、EMA9-21の浅い押し目では
    ノイズに巻き込まれる。BB-2σ or EMA50-100ゾーンの「深い押し目」まで
    待つことで、真のリバーサルポイントを捉える

コンセプト:
  ADX TC の GBP/USD 特化版。以下を変更:
    1. 押し目の深さ基準: EMA9-21 → BB-2σ (bbpb≤0.05) OR EMA50付近
    2. EMAオーダー: 9>21>50 厳格 → 9>21 (方向一致で十分)
    3. ADX閾値: 25 → 20 (GBPのベースボラが高い)
    4. TP: ATR×2.5 → ATR×3.0 (深い押し目=大きな反発期待)

  Entry:
    BUY: トレンドUP + 価格がBB下限 or EMA50付近まで下落 + 反転確認
    SELL: トレンドDOWN + 価格がBB上限 or EMA50付近まで上昇 + 反転確認

  SL: スイング安値/高値 (10本) ± ATR×0.3
  TP: ATR × 3.0
"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from typing import Optional


class GbpDeepPullback(StrategyBase):
    name = "gbp_deep_pullback"
    mode = "daytrade"
    enabled = True

    # ══════════════════════════════════════════════════
    # パラメータ定数
    # ══════════════════════════════════════════════════

    # ── トレンド確認 ──
    ADX_MIN          = 20       # ADX閾値 (GBP: ベースボラ高→低めでOK)

    # ── 深い押し目条件 (OR条件: いずれかを満たす) ──
    # Condition A: BB-2σタッチ
    BB_PB_THRES_BUY  = 0.20     # BUY: BB %B ≤ 0.20 (下限20%以内)  # v6.6: 0.10→0.20 (発火率2倍化, BT WR=73.7%にマージンあり)
    BB_PB_THRES_SELL = 0.80     # SELL: BB %B ≥ 0.80 (上限20%以内)  # v6.6: 0.10→0.20 (発火率2倍化, BT WR=73.7%にマージンあり)
    # Condition B: EMA50付近
    EMA50_DIST_ATR   = 0.5      # EMA50からATR×0.5以内 = 「EMA50ゾーン」

    # ── プルバック検出ルックバック ──
    PB_LOOKBACK      = 6        # 直近N本以内に深い押し目  # v6.6: 4→6 (パターン形成の時間的余裕を確保)

    # ── リバウンド確認 ──
    RSI_RECOVER_MIN  = 40       # BUY: RSI ≥ 40 (暴落中ではない)
    RSI_RECOVER_MAX  = 60       # SELL: RSI ≤ 60

    # ── SL/TP ──
    SL_SWING_LOOKBACK = 10      # スイング検出ルックバック (深い押し目→広め)
    SL_ATR_BUFFER    = 0.3      # SL = swing ± ATR×0.3
    TP_ATR_MULT      = 3.0      # TP = ATR × 3.0 (深い押し目=大反発)
    MIN_RR           = 1.5      # 最低リスクリワード比

    # ── 保持 ──
    MAX_HOLD_BARS    = 16       # 最大16バー (4時間 @ 15m)

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        # ── ペアフィルター: GBP/USD のみ ──
        _sym = ctx.symbol.upper().replace("=X", "").replace("/", "").replace("_", "")
        if _sym not in ("GBPUSD",):
            return None

        # ── データ十分性 ──
        if ctx.df is None or len(ctx.df) < self.SL_SWING_LOOKBACK + self.PB_LOOKBACK + 5:
            return None

        # ═══════════════════════════════════════════════════
        # トレンド確認
        # ═══════════════════════════════════════════════════

        # ── ADX ≥ 20 ──
        if ctx.adx < self.ADX_MIN:
            return None

        # ── 方向判定: DI ──
        _buy_dir = ctx.adx_pos > ctx.adx_neg
        _sell_dir = ctx.adx_neg > ctx.adx_pos

        # ── EMA順序: 9 > 21 (方向一致) ──
        _buy_ema = ctx.ema9 > ctx.ema21
        _sell_ema = ctx.ema9 < ctx.ema21

        _is_buy = _buy_dir and _buy_ema
        _is_sell = _sell_dir and _sell_ema

        if not _is_buy and not _is_sell:
            return None

        # ── HTFフィルター ──
        _htf = ctx.htf or {}
        _agr = _htf.get("agreement", "mixed")
        if _is_buy and _agr == "bear":
            return None
        if _is_sell and _agr == "bull":
            return None

        # ═══════════════════════════════════════════════════
        # STEP1: ディープ押し目検出 (前1-4本)
        #   Condition A: BB %B ≤ 0.10 (BUY) / ≥ 0.90 (SELL)
        #   Condition B: |price - EMA50| ≤ ATR × 0.5
        # ═══════════════════════════════════════════════════
        _deep_pb_found = False
        _pb_type = ""
        _pb_price = 0.0

        for offset in range(1, self.PB_LOOKBACK + 1):
            idx = -(offset + 1)
            if abs(idx) > len(ctx.df):
                break
            _bar = ctx.df.iloc[idx]

            # BB %B チェック
            _bbpb = float(_bar.get("bb_pband", 0.5))
            # EMA50距離チェック
            _bar_close = float(_bar["Close"])
            _ema50_dist = abs(_bar_close - ctx.ema50) / ctx.atr if ctx.atr > 0 else 999

            if _is_buy:
                _bb_deep = _bbpb <= self.BB_PB_THRES_BUY
                _ema50_deep = _ema50_dist <= self.EMA50_DIST_ATR and _bar_close <= ctx.ema50 + ctx.atr * 0.2
                if _bb_deep or _ema50_deep:
                    _deep_pb_found = True
                    _pb_type = "BB-2σ" if _bb_deep else "EMA50"
                    _pb_price = float(_bar["Low"])
                    break
            else:
                _bb_deep = _bbpb >= self.BB_PB_THRES_SELL
                _ema50_deep = _ema50_dist <= self.EMA50_DIST_ATR and _bar_close >= ctx.ema50 - ctx.atr * 0.2
                if _bb_deep or _ema50_deep:
                    _deep_pb_found = True
                    _pb_type = "BB+2σ" if _bb_deep else "EMA50"
                    _pb_price = float(_bar["High"])
                    break

        if not _deep_pb_found:
            return None

        # ═══════════════════════════════════════════════════
        # STEP2: リバウンド確認 (現在足)
        # ═══════════════════════════════════════════════════

        # ── 反転足: 陽線(BUY) / 陰線(SELL) ──
        if _is_buy and ctx.entry <= ctx.open_price:
            return None
        if _is_sell and ctx.entry >= ctx.open_price:
            return None

        # ── 価格回復: Close > EMA21 (BUY) / Close < EMA21 (SELL) ──
        # GBP: EMA9回復ではなくEMA21回復で十分(深い押し目からの回復)
        if _is_buy and ctx.entry <= ctx.ema21:
            return None
        if _is_sell and ctx.entry >= ctx.ema21:
            return None

        # ── RSI回復確認 ──
        if _is_buy and ctx.rsi < self.RSI_RECOVER_MIN:
            return None
        if _is_sell and ctx.rsi > self.RSI_RECOVER_MAX:
            return None

        # ═══════════════════════════════════════════════════
        # シグナル生成
        # ═══════════════════════════════════════════════════
        signal = "BUY" if _is_buy else "SELL"
        score = 4.5
        reasons = []

        # ── SL: スイング安値/高値 ± ATR×0.3 ──
        _lookback = min(self.SL_SWING_LOOKBACK, len(ctx.df) - 1)
        if _is_buy:
            _swing = float(ctx.df["Low"].iloc[-_lookback:].min())
            sl = _swing - ctx.atr * self.SL_ATR_BUFFER
        else:
            _swing = float(ctx.df["High"].iloc[-_lookback:].max())
            sl = _swing + ctx.atr * self.SL_ATR_BUFFER

        # ── TP: ATR × 3.0 (RR≥1.5保証) ──
        _sl_dist = abs(ctx.entry - sl)
        _tp_target = ctx.atr * self.TP_ATR_MULT
        _tp_min_rr = _sl_dist * self.MIN_RR
        _tp_dist = max(_tp_target, _tp_min_rr)

        tp = ctx.entry + _tp_dist if _is_buy else ctx.entry - _tp_dist

        # ── RR確認 ──
        if _sl_dist <= 0 or _tp_dist / _sl_dist < self.MIN_RR:
            return None

        _rr = _tp_dist / _sl_dist

        # ═══════════════════════════════════════════════════
        # Reasons & ボーナス
        # ═══════════════════════════════════════════════════
        _dec = 5  # GBP/USD = 5桁
        reasons.append(
            f"✅ GBP Deep PB {signal}: ADX={ctx.adx:.1f}≥{self.ADX_MIN} "
            f"+DI={ctx.adx_pos:.1f} -DI={ctx.adx_neg:.1f}"
        )
        reasons.append(
            f"✅ ディープ押し目({_pb_type}): "
            f"PB price={_pb_price:.{_dec}f}"
        )
        reasons.append(
            f"✅ リバウンド確認: Close={ctx.entry:.{_dec}f} "
            f"{'>' if _is_buy else '<'} EMA21={ctx.ema21:.{_dec}f}"
        )
        reasons.append(
            f"📊 RR={_rr:.1f} SL={sl:.{_dec}f} TP={tp:.{_dec}f}"
        )

        # ADX強度ボーナス
        if ctx.adx >= 30:
            score += 0.5
            reasons.append(f"✅ 強トレンド(ADX={ctx.adx:.1f}≥30)")

        # HTF一致ボーナス
        if (signal == "BUY" and _agr == "bull") or \
           (signal == "SELL" and _agr == "bear"):
            score += 0.5
            reasons.append(f"✅ HTF方向一致({_agr})")

        # EMA50方向一致ボーナス
        if (_is_buy and ctx.ema21 > ctx.ema50) or \
           (_is_sell and ctx.ema21 < ctx.ema50):
            score += 0.3
            reasons.append("✅ EMA50方向一致(トレンド確認)")

        # EMA200方向一致ボーナス
        if (_is_buy and ctx.entry > ctx.ema200) or \
           (_is_sell and ctx.entry < ctx.ema200):
            score += 0.3
            reasons.append("✅ EMA200方向一致")

        # BB-2σ + EMA50ダブル確認ボーナス
        _curr_bbpb = ctx.bbpb
        _curr_ema50_dist = abs(ctx.entry - ctx.ema50) / ctx.atr if ctx.atr > 0 else 999
        if _pb_type.startswith("BB") and _curr_ema50_dist <= 1.0:
            score += 0.3
            reasons.append("✅ BB+EMA50ダブル確認")

        conf = int(min(85, 50 + score * 4))
        return Candidate(
            signal=signal, confidence=conf, sl=sl, tp=tp,
            reasons=reasons, entry_type=self.name, score=score
        )
