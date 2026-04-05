"""
SR Break & Retest (SBR) — サポート/レジスタンス・ブレイク後リテスト戦略

学術的根拠:
  - Edwards & Magee (1948): Support becomes Resistance (role reversal原則)
  - Lo, Mamaysky & Wang (2000): テクニカルパターンの統計的有意性を実証
  - Osler (2000): 指値注文集中がSR水準を形成（市場構造的裏付け）
  - Williams (1995): Fractal High/Low による客観的SR水準特定

戦略コンセプト:
  HFB(HTF False Breakout Fade)の鏡像戦略。
  HFB = 偽ブレイク → レンジ回帰（カウンタートレンド）
  SBR = 真ブレイク → リテスト → 継続（トレンドフォロー）
  同一価格水準で逆シグナル = 負の相関 = 最大分散効果。

  「ブレイク」後のリテスト（元SR水準へのプルバック）を待つことで、
  偽ブレイクを構造的に排除しつつ、有利な価格でトレンド方向にエントリーする。

エントリーロジック（3段階検出）:
  ■ STEP1: SR水準検出
    Williams Fractal (n=5): 直近N本のHigh/Lowからフラクタル高値/安値を検出
    複数フラクタルの集中（±0.3ATR以内）でクラスター化→強力なSR水準

  ■ STEP2: ブレイク検出（過去2-10本）
    Close（実体）でSR水準を明確に超過（ヒゲ抜け除外）
    ブレイク足の実体 ≥ バーレンジの30%
    ADX ≥ 20（モメンタム裏付け）

  ■ STEP3: リテスト確認（現在足）
    価格がブレイクしたSR水準に戻る（±0.5ATR以内）
    現在足がリテスト方向から反転（陽線/陰線 + EMA回復）
    Role reversal確認: 旧レジスタンス→新サポート or 旧サポート→新レジスタンス

設計方針:
  - 全ペア対応（USD/JPY, EUR/USD, GBP/USD, EUR/GBP）
  - HFBとの負相関を意識した設計（同一SR水準で逆シグナル）
  - ADX・HTFフィルターでトレンド方向を確認
"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from typing import Optional
import numpy as np


class SrBreakRetest(StrategyBase):
    name = "sr_break_retest"
    mode = "daytrade"
    enabled = True

    # ══════════════════════════════════════════════════
    # パラメータ定数
    # ══════════════════════════════════════════════════

    # ── Fractal SR検出 ──
    FRACTAL_N = 3               # Williams Fractal: 両側N本 (n=3: 7バー窓)
    FRACTAL_LOOKBACK = 80       # Fractal検出のルックバック本数 (15m足80本 = 20H)
    CLUSTER_ATR_MULT = 0.5      # ±0.5ATR以内のフラクタルをクラスター化
    MIN_CLUSTERS = 1            # 単一フラクタルも有効SR（クラスター2+でボーナス）

    # ── ブレイク検出 ──
    BREAK_LOOKBACK_MIN = 2      # ブレイク検出: 最低2本前
    BREAK_LOOKBACK_MAX = 15     # ブレイク検出: 最大15本前 (≈4H)
    BREAK_BODY_MIN = 0.25       # ブレイク足の実体 ≥ レンジの25%
    BREAK_MARGIN_ATR = 0.05     # ブレイク: Close がSRから ≥ 0.05ATR 離れる

    # ── リテスト確認 ──
    RETEST_ZONE_ATR = 0.7       # リテストゾーン: SR水準 ± 0.7ATR
    RETEST_BOUNCE_EMA = True    # リテスト反転: Close が EMA9 を回復

    # ── ADXフィルター ──
    ADX_MIN = 20                # モメンタム最低閾値

    # ── SL/TP ──
    SL_ATR_BUFFER = 0.3         # SL = SR水準の裏側 + ATR×0.3
    TP_ATR_MULT = 2.0           # TP = ATR × 2.0
    MIN_RR = 1.5                # 最低リスクリワード比

    # ── 最大保持 ──
    MAX_HOLD_BARS = 12          # 12バー = 3時間 (15m足)

    def _find_fractal_levels(self, df, n: int = 3, lookback: int = 80):
        """Williams Fractal でフラクタル高値/安値を検出。

        Fractal High: bar[i] の High が前後 n 本の High より高い
        Fractal Low:  bar[i] の Low  が前後 n 本の Low  より低い

        Returns:
            (fractal_highs, fractal_lows): list of float
        """
        _start = max(0, len(df) - lookback)
        _end = len(df) - n  # 最新 n 本はフラクタル未確定
        highs = df["High"].values
        lows = df["Low"].values

        frac_highs = []
        frac_lows = []

        for i in range(_start + n, _end):
            # Fractal High: High[i] > all High[i-n:i] and High[i] > all High[i+1:i+n+1]
            _h = highs[i]
            if all(_h > highs[j] for j in range(i - n, i)) and \
               all(_h > highs[j] for j in range(i + 1, i + n + 1)):
                frac_highs.append(float(_h))

            # Fractal Low: Low[i] < all Low[i-n:i] and Low[i] < all Low[i+1:i+n+1]
            _l = lows[i]
            if all(_l < lows[j] for j in range(i - n, i)) and \
               all(_l < lows[j] for j in range(i + 1, i + n + 1)):
                frac_lows.append(float(_l))

        return frac_highs, frac_lows

    def _cluster_levels(self, levels: list, atr: float) -> list:
        """近接フラクタルをクラスター化し、タッチ回数2以上のSR水準を返す。

        Returns:
            list of (level_avg, touch_count) sorted by touch_count desc
        """
        if not levels:
            return []

        _threshold = atr * self.CLUSTER_ATR_MULT
        _sorted = sorted(levels)
        clusters = []
        _current_cluster = [_sorted[0]]

        for i in range(1, len(_sorted)):
            if _sorted[i] - _current_cluster[-1] <= _threshold:
                _current_cluster.append(_sorted[i])
            else:
                if len(_current_cluster) >= self.MIN_CLUSTERS:
                    _avg = sum(_current_cluster) / len(_current_cluster)
                    clusters.append((_avg, len(_current_cluster)))
                _current_cluster = [_sorted[i]]

        # 最後のクラスター
        if len(_current_cluster) >= self.MIN_CLUSTERS:
            _avg = sum(_current_cluster) / len(_current_cluster)
            clusters.append((_avg, len(_current_cluster)))

        # タッチ回数降順
        clusters.sort(key=lambda x: x[1], reverse=True)
        return clusters

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        # ── EUR/USD除外: EV≈0, スプレッド負担で本番負EV ──
        # USD/JPY: 64t WR=64.1% EV=+0.252 → 採用
        # GBP/USD: 46t WR=60.9% EV=+0.145 → 採用
        # EUR/USD: 27t WR=55.6% EV=+0.017 → 不採用
        # EUR/GBP: 未検証（低ボラ → 同様にスプレッド負担大）
        _sym = ctx.symbol.upper().replace("=X", "").replace("/", "").replace("_", "")
        if _sym in ("EURUSD", "EURGBP"):
            return None

        # ── DataFrame十分性チェック ──
        _min_bars = self.FRACTAL_LOOKBACK + self.FRACTAL_N + 2
        if ctx.df is None or len(ctx.df) < _min_bars:
            return None

        # ═══════════════════════════════════════════════════
        # STEP 0: ADXフィルター（モメンタム不在 = ブレイク信頼度低）
        # ═══════════════════════════════════════════════════
        if ctx.adx < self.ADX_MIN:
            return None

        # ═══════════════════════════════════════════════════
        # STEP 1: Fractal SR水準検出
        # ═══════════════════════════════════════════════════
        _frac_highs, _frac_lows = self._find_fractal_levels(
            ctx.df, n=self.FRACTAL_N, lookback=self.FRACTAL_LOOKBACK
        )

        # 高値と安値を統合してクラスター化
        _all_levels = _frac_highs + _frac_lows
        _clusters = self._cluster_levels(_all_levels, ctx.atr)

        if not _clusters:
            return None

        # ═══════════════════════════════════════════════════
        # STEP 2: ブレイク検出（過去2-10本でSR水準を実体ブレイク）
        # ═══════════════════════════════════════════════════
        _break_margin = ctx.atr * self.BREAK_MARGIN_ATR
        _retest_zone = ctx.atr * self.RETEST_ZONE_ATR

        _best_signal = None  # (signal, sr_level, touches, break_bar_idx)

        for _sr_level, _touches in _clusters:
            for _offset in range(self.BREAK_LOOKBACK_MIN,
                                 min(self.BREAK_LOOKBACK_MAX + 1,
                                     len(ctx.df) - 1)):
                _bar = ctx.df.iloc[-(_offset + 1)]
                _bar_close = float(_bar["Close"])
                _bar_open = float(_bar["Open"])
                _bar_high = float(_bar["High"])
                _bar_low = float(_bar["Low"])
                _bar_range = _bar_high - _bar_low

                # 実体チェック（ヒゲ抜け除外）
                _bar_body = abs(_bar_close - _bar_open)
                if _bar_range <= 0:
                    continue
                if _bar_body / _bar_range < self.BREAK_BODY_MIN:
                    continue

                # ── 上方ブレイク検出 → BUY候補 ──
                if _bar_close > _sr_level + _break_margin:
                    # ブレイク前にSR水準の下にいた確認（前のバーのCloseがSR以下）
                    if _offset + 2 <= len(ctx.df):
                        _pre_bar = ctx.df.iloc[-(_offset + 2)]
                        if float(_pre_bar["Close"]) > _sr_level + _break_margin:
                            continue  # 既にブレイク済み→このバーはブレイク足ではない

                    # ── リテスト確認: 現在足がSR水準に戻っている ──
                    if abs(ctx.entry - _sr_level) <= _retest_zone:
                        # かつ現在足がSR水準から反発（陽線 + Close > EMA9）
                        if ctx.entry > ctx.open_price and \
                           ctx.entry > _sr_level and \
                           (not self.RETEST_BOUNCE_EMA or ctx.entry > ctx.ema9):
                            if _best_signal is None or _touches > _best_signal[2]:
                                _best_signal = ("BUY", _sr_level, _touches, _offset)
                    break  # この SR水準で最初のブレイクのみ評価

                # ── 下方ブレイク検出 → SELL候補 ──
                elif _bar_close < _sr_level - _break_margin:
                    if _offset + 2 <= len(ctx.df):
                        _pre_bar = ctx.df.iloc[-(_offset + 2)]
                        if float(_pre_bar["Close"]) < _sr_level - _break_margin:
                            continue

                    if abs(ctx.entry - _sr_level) <= _retest_zone:
                        if ctx.entry < ctx.open_price and \
                           ctx.entry < _sr_level and \
                           (not self.RETEST_BOUNCE_EMA or ctx.entry < ctx.ema9):
                            if _best_signal is None or _touches > _best_signal[2]:
                                _best_signal = ("SELL", _sr_level, _touches, _offset)
                    break

        if _best_signal is None:
            return None

        signal, sr_level, touches, break_offset = _best_signal

        # ═══════════════════════════════════════════════════
        # STEP 3: HTFフィルター（逆方向ブロック）
        # ═══════════════════════════════════════════════════
        _htf = ctx.htf or {}
        _agreement = _htf.get("agreement", "mixed")

        if signal == "BUY" and _agreement == "bear":
            return None
        if signal == "SELL" and _agreement == "bull":
            return None

        # ═══════════════════════════════════════════════════
        # シグナル生成
        # ═══════════════════════════════════════════════════
        score = 4.0
        reasons = []

        # ── SL計算: SR水準の裏側 + ATRバッファ ──
        if signal == "BUY":
            # BUY: SLは旧レジスタンス（新サポート）の下
            sl = sr_level - ctx.atr * self.SL_ATR_BUFFER
        else:
            # SELL: SLは旧サポート（新レジスタンス）の上
            sl = sr_level + ctx.atr * self.SL_ATR_BUFFER

        # ── TP計算: ATR×2.0 (RR≥1.5保証) ──
        _sl_dist = abs(ctx.entry - sl)
        _tp_target = ctx.atr * self.TP_ATR_MULT
        _tp_min_rr = _sl_dist * self.MIN_RR
        _tp_dist = max(_tp_target, _tp_min_rr)

        if signal == "BUY":
            tp = ctx.entry + _tp_dist
        else:
            tp = ctx.entry - _tp_dist

        # ── RR最低保証チェック ──
        if _sl_dist <= 0 or _tp_dist / _sl_dist < self.MIN_RR:
            return None

        # ═══════════════════════════════════════════════════
        # Reasons & ボーナス
        # ═══════════════════════════════════════════════════
        _rr = _tp_dist / _sl_dist if _sl_dist > 0 else 0
        _pip = ctx.pip_mult

        reasons.append(
            f"✅ SR Break&Retest {signal}: "
            f"SR={sr_level:.{3 if ctx.is_jpy else 5}f} "
            f"(Fractal {touches}タッチ, Edwards&Magee 1948)"
        )
        reasons.append(
            f"✅ ブレイク確認: {break_offset}本前に実体ブレイク "
            f"(ADX={ctx.adx:.1f}≥{self.ADX_MIN})"
        )
        reasons.append(
            f"✅ リテスト反転: Close={ctx.entry:.{3 if ctx.is_jpy else 5}f} "
            f"{'>' if signal == 'BUY' else '<'} SR水準 "
            f"(Role Reversal確認)"
        )
        reasons.append(
            f"📊 RR={_rr:.1f} SL={sl:.{3 if ctx.is_jpy else 5}f} "
            f"TP={tp:.{3 if ctx.is_jpy else 5}f}"
        )

        # ── ボーナス条件 ──

        # SR強度ボーナス: タッチ回数が多いほど信頼度高
        if touches >= 3:
            score += 0.5
            reasons.append(f"✅ 強SR({touches}タッチ)")

        # ADX強度ボーナス
        if ctx.adx >= 30:
            score += 0.4
            reasons.append(f"✅ 強モメンタム(ADX={ctx.adx:.1f}≥30)")

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

        # EMA200方向一致ボーナス
        if (signal == "BUY" and ctx.entry > ctx.ema200) or \
           (signal == "SELL" and ctx.entry < ctx.ema200):
            score += 0.3
            reasons.append("✅ EMA200方向一致")

        # DI方向一致ボーナス
        if (signal == "BUY" and ctx.adx_pos > ctx.adx_neg) or \
           (signal == "SELL" and ctx.adx_neg > ctx.adx_pos):
            score += 0.3
            reasons.append(
                f"✅ DI方向一致(+DI={ctx.adx_pos:.1f} "
                f"-DI={ctx.adx_neg:.1f})"
            )

        # リテスト精度ボーナス: SR水準にどれだけ近いか
        _retest_accuracy = 1.0 - abs(ctx.entry - sr_level) / _retest_zone \
            if _retest_zone > 0 else 0
        if _retest_accuracy >= 0.7:
            score += 0.3
            reasons.append(f"✅ 精密リテスト(精度{_retest_accuracy:.0%})")

        conf = int(min(85, 50 + score * 4))
        return Candidate(
            signal=signal, confidence=conf, sl=sl, tp=tp,
            reasons=reasons, entry_type=self.name, score=score
        )
