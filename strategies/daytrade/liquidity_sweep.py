"""
Liquidity Sweep (Institutional Stop-Hunt Reversal) -- 機関投資家ストップ狩り逆張り

学術的根拠:
  - Osler (2003): "Currency orders and exchange rate dynamics: Explaining the
    success of technical analysis." — 個人投資家のSLがスイングH/Lの直外に
    高密度で集中し、これが流動性プールとして機関投資家に利用される。
  - Kyle (1985): "Continuous Auctions and Insider Trading" — 情報を持つ
    大口投資家が予測可能なSL配置を利用して大口注文の約定流動性を確保する。
  - Bulkowski (2005): "Encyclopedia of Chart Patterns" — False breakout後の
    リバーサルパターン勝率 60-70%。ブレイクアウトの大半がフェイクアウト。
  - Lo & MacKinlay (1988): "Stock Market Prices Do Not Follow Random Walks" —
    短期リバーサル効果。オーバーリアクションの是正メカニズム。
  - Andersen & Bollerslev (1998): "Deutsche Mark-Dollar Volatility" —
    セッション開始直後の価格行動は情報イベントに支配される (= 真のBK多い)。
    → セッション開始30分はフィルターで除外。

戦略コンセプト:
  機関投資家(スマートマネー)は、個人投資家のSL注文が集中するスイングH/L付近
  まで価格を押し込み、SL注文の流動性を利用して大口ポジションを構築する。
  SL注文を食い尽くした後、価格は急速にスイングレベル内に回帰する。
  この「ストップ狩り → 回帰」パターンをウィック構造で検出し、逆張りエントリー。

  Turtle Soupとの構造的差異:
    Turtle Soup = "Close実体"ベースのブレイク＆リクレーム (Connors 1995)
    Liquidity Sweep = "ウィック比率"ベースのsweep検出 + ボリューム確認 + レジームフィルター
    → Turtle Soupがreclaimの「事実」を見るのに対し、Liquidity Sweepは
       sweepの「構造」(wick rejection + volume spike)を数量的に評価。
    → ADX < 25 + BB width 制約で RANGE 限定 = Turtle Soup (ADX 12-40) と低相関。

  ORB Trapとの構造的差異:
    ORB Trap = 固定時間ORのフェイクアウト (セッション開始30分)
    Liquidity Sweep = 動的なスイングH/L (フラクタルベース) のフェイクアウト
    → 時間軸が完全に異なり、信号は独立。

数学的定義:
  ■ A. Swing Level (流動性プール) 検出:
    Williams Fractal (lookback_n=FRACTAL_N) で直近 FRACTAL_LOOKBACK バーの
    スイングH/Lを検出。±CLUSTER_ATR以内のフラクタルをクラスター化。
    タッチ回数 >= MIN_TOUCHES のクラスター = 「流動性プール」確認済み水準。

  ■ B. Sweep (ストップ狩り) 検出:
    sweep_bar.High > swing_high (高値sweep) または
    sweep_bar.Low < swing_low (安値sweep)
    ウィック比率: wick_beyond_level / total_bar_range >= WICK_RATIO_MIN (0.60)
      → ヒゲが足レンジの60%以上 = 実体ではなくウィックで突き抜け = 即時rejection
    Close がスイングレベル内側に回帰 = 「狩り終了」確認
    ボリュームプロキシ: bar_range / ATR >= VOL_RATIO_MIN (1.5)
      → tick volume 代替: 大きなbar_rangeは高ボリュームの代理変数

  ■ C. Entry:
    sweep確認バーの「次の足」でエントリー (追認エントリー)
    次足Open がスイングレベル内側 AND 逆方向への動き確認
    BUY: 安値sweep後 (swept below swing low, rejected, enter long)
    SELL: 高値sweep後 (swept above swing high, rejected, enter short)

  ■ D. SL/TP:
    SL = sweep wick extreme ± ATR x SL_ATR_BUFFER (0.3)
    TP = 対面のスイングレベル (mean-reversion to other side of range)
    TP fallback = ATR x TP_ATR_MULT (2.5) (対面が遠すぎる場合)
    MIN_RR >= 1.5

  ■ E. Regime Filters:
    ADX < ADX_MAX (25) — レンジ環境のみ (トレンドでは真のブレイクアウト)
    BB width percentile < BB_WIDTH_PCT_MAX (0.50) — squeeze前環境は除外
    セッション開始30分を除外 (London/NY open = 真のBK多い)

摩擦分析 (15m USD_JPY):
  ATR(15m) ~= 12 pips
  Spread: ~1.0 pip roundtrip = 2.0 pip
  Typical SL: sweep_extreme + ATR*0.3 ~= 15-20 pips
  Friction/SL ratio: 2.0/17.5 = 11.4% (acceptable, BEV_WR ~= 35%)
  Target WR based on literature: 60-70% (Bulkowski 2005)
"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from typing import Optional
import numpy as np


class LiquiditySweep(StrategyBase):
    name = "liquidity_sweep"
    mode = "daytrade"
    enabled = True

    # ══════════════════════════════════════════════════
    # A. Swing Level (流動性プール) 検出パラメータ
    # ══════════════════════════════════════════════════

    # Williams Fractal 窓: 両側N本 (2N+1バー窓)
    # N=5 → 11バー窓 = 2.75H on 15m (十分なスイング構造)
    FRACTAL_N = 5

    # フラクタル検出ルックバック: 最大何本前まで遡るか
    # 120本 × 15m = 30H ≈ 2営業日 (Osler 2003: SL集中は直近数日のスイングに最も濃い)
    FRACTAL_LOOKBACK = 120

    # クラスター化閾値: この距離以内のフラクタルを同一水準とみなす
    # 0.4 ATR ≈ 5 pips (15m) — 同一SL帯を集約
    CLUSTER_ATR_MULT = 0.4

    # 最低タッチ回数: 流動性プール確認の閾値
    # 2回以上タッチ = 多数の個人投資家がSLを置く水準 (Osler 2003)
    MIN_TOUCHES = 2

    # ══════════════════════════════════════════════════
    # B. Sweep (ストップ狩り) 検出パラメータ
    # ══════════════════════════════════════════════════

    # sweep検出: 直近何本以内でsweepが発生したか
    # 2本 = 直近1-2バー限定 (鮮度最大化、sweep→即回帰パターン)
    SWEEP_LOOKBACK = 2

    # sweep最低超過: フラクタルからの最低突き抜け距離
    # ATR × 5% ≈ 0.6 pips (ノイズ排除: 最低限のpenetration必須)
    SWEEP_MARGIN_ATR = 0.05

    # ウィック比率: sweep方向のウィック / 足全体のレンジ
    # 0.60 = ウィックが足の60%以上 → 実体突き抜けではなく「狩り」の痕跡
    # (Bulkowski 2005: wick-dominant bars have higher reversal rates)
    WICK_RATIO_MIN = 0.60

    # ボリュームプロキシ: bar_range / ATR
    # 1.5 = 通常の1.5倍のbar_range → 大口介入の痕跡 (tick volume代替)
    # OANDA tick volumeは不均一なため、bar_rangeを代理変数として使用
    VOL_RATIO_MIN = 1.5

    # ══════════════════════════════════════════════════
    # C. Entry 確認パラメータ
    # ══════════════════════════════════════════════════

    # 次足の実体方向がリバーサル方向であることを要求
    # True = BUY時は陽線(C>O)、SELL時は陰線(C<O) を追加確認
    NEXT_BAR_BODY_CONFIRM = True

    # ══════════════════════════════════════════════════
    # D. SL/TP パラメータ
    # ══════════════════════════════════════════════════

    # SLバッファ: sweep extreme の外側に ATR × この係数を追加
    SL_ATR_BUFFER = 0.3

    # TP: 対面スイングレベルへの回帰
    # fallback: ATR × この係数 (対面が遠すぎる場合)
    TP_ATR_MULT = 2.5

    # 最低リスクリワード比
    MIN_RR = 1.5

    # TP最大距離: ATR × この係数を超えるTPは切り詰め
    # (平均回帰戦略で過大なTPは非現実的)
    TP_MAX_ATR = 4.0

    # ══════════════════════════════════════════════════
    # E. Regime Filters (偽陽性防止)
    # ══════════════════════════════════════════════════

    # ADX上限: これ以上はトレンド → 真のブレイクアウトの確率が上昇
    # 25 = Wilder (1978) の定義するトレンド/レンジ境界
    ADX_MAX = 25

    # ADX下限: 無風状態ではsweep自体がノイズ
    ADX_MIN = 10

    # BB width percentile 上限: squeeze直前を除外
    # 0.50 = 50パーセンタイル以下のみ (圧縮が解放される瞬間を回避)
    BB_WIDTH_PCT_MAX = 0.50

    # セッション開始ブロック (UTC分単位)
    # v8.6: 30min→15minに短縮 — Barardehi & Bernhardt (2025): 真のボラスパイクは開始15分に集中
    # N蓄積加速のため、ブロック時間を最小化しつつ最も危険な15分は維持
    LDN_OPEN_START = 420   # UTC 07:00
    LDN_OPEN_END = 435     # UTC 07:15 (v8.6: 07:30→07:15)
    NY_OPEN_START = 810    # UTC 13:30
    NY_OPEN_END = 825      # UTC 13:45 (v8.6: 14:00→13:45)

    # ══════════════════════════════════════════════════
    # 時間帯・ペアフィルター
    # ══════════════════════════════════════════════════

    # 活動時間帯 (UTC hour)
    ACTIVE_HOURS_START = 6   # UTC 06:00 以降
    ACTIVE_HOURS_END = 20    # UTC 20:00 まで

    # 金曜ブロック (UTC hour)
    FRIDAY_BLOCK_HOUR = 16   # 金曜 UTC 16:00 以降ブロック

    # 対象ペア
    ALLOWED_PAIRS = {"USDJPY", "EURUSD", "GBPUSD"}

    # 最大保持バー (15m × 12 = 3時間)
    MAX_HOLD_BARS = 12

    # ══════════════════════════════════════════════════
    # ヘルパー: フラクタル検出
    # ══════════════════════════════════════════════════

    def _find_fractal_levels(self, df, n: int, lookback: int):
        """Williams Fractal でフラクタル高値/安値を検出。

        Williams Fractal: バーiが両側n本より高ければ(低ければ)フラクタルH(L)。
        i.e., High[i] > High[j] for all j in [i-n, i+n] (j != i)

        Args:
            df: OHLCV DataFrame
            n: フラクタル窓の片側サイズ
            lookback: 最大何本前まで検出するか

        Returns:
            (fractal_highs, fractal_lows): list of (price, bar_index)
        """
        _start = max(0, len(df) - lookback)
        _end = len(df) - n  # 最新n本はフラクタル未確定
        highs = df["High"].values
        lows = df["Low"].values

        frac_highs = []
        frac_lows = []

        for i in range(_start + n, _end):
            _h = highs[i]
            if all(_h > highs[j] for j in range(i - n, i)) and \
               all(_h > highs[j] for j in range(i + 1, i + n + 1)):
                frac_highs.append((float(_h), i))

            _l = lows[i]
            if all(_l < lows[j] for j in range(i - n, i)) and \
               all(_l < lows[j] for j in range(i + 1, i + n + 1)):
                frac_lows.append((float(_l), i))

        return frac_highs, frac_lows

    # ══════════════════════════════════════════════════
    # ヘルパー: クラスター化 (複数タッチの流動性プール検出)
    # ══════════════════════════════════════════════════

    def _cluster_levels(self, levels: list, atr: float):
        """近接フラクタルをクラスター化。

        Osler (2003) の知見: SL注文は「丸い番号」およびスイングH/Lの直外に
        集中する。近接する複数のフラクタルH/Lは同一の流動性帯を形成する。

        Args:
            levels: list of (price, bar_index) tuples
            atr: ATR(14) for proximity threshold

        Returns:
            list of (cluster_avg_price, touch_count) sorted by touch_count desc
        """
        if not levels or atr <= 0:
            return []

        _threshold = atr * self.CLUSTER_ATR_MULT
        prices = sorted(levels, key=lambda x: x[0])
        clusters = []
        _current = [prices[0]]

        for i in range(1, len(prices)):
            if prices[i][0] - _current[-1][0] <= _threshold:
                _current.append(prices[i])
            else:
                if len(_current) >= self.MIN_TOUCHES:
                    _avg = sum(p for p, _ in _current) / len(_current)
                    clusters.append((_avg, len(_current)))
                _current = [prices[i]]

        # 最後のクラスター
        if len(_current) >= self.MIN_TOUCHES:
            _avg = sum(p for p, _ in _current) / len(_current)
            clusters.append((_avg, len(_current)))

        clusters.sort(key=lambda x: x[1], reverse=True)
        return clusters

    # ══════════════════════════════════════════════════
    # ヘルパー: ウィック構造によるSweep検出
    # ══════════════════════════════════════════════════

    def _detect_wick_sweep(self, df, level: float, direction: str, atr: float):
        """ウィック構造によるSweep (ストップ狩り) を検出。

        Turtle Soupとの差異:
          - Turtle Soup: Close実体でのreclaim (binary: inside/outside)
          - Liquidity Sweep: ウィック比率の定量評価 + ボリュームプロキシ

        検出条件 (全て同時成立):
          1. 直近SWEEP_LOOKBACKバー以内でHighまたはLowがlevelを超過
          2. ウィック比率 >= WICK_RATIO_MIN (0.60)
          3. bar_range / ATR >= VOL_RATIO_MIN (1.5) — ボリュームプロキシ
          4. Closeがlevelの内側に回帰

        Args:
            df: OHLCV DataFrame
            level: スイングH/Lの水準
            direction: "UP" (高値sweep → SELL) or "DOWN" (安値sweep → BUY)
            atr: ATR(14)

        Returns:
            dict with sweep info, or None
        """
        if len(df) < self.SWEEP_LOOKBACK + 2:
            return None

        _cur_idx = len(df) - 1
        _sweep_margin = atr * self.SWEEP_MARGIN_ATR

        # 現在足の情報 (= sweep確認バーの次足 = エントリー足)
        cur_close = float(df["Close"].iloc[_cur_idx])
        cur_open = float(df["Open"].iloc[_cur_idx])

        # sweep候補バーを探索 (前足または2本前)
        _best_sweep = None

        for lookback in range(1, self.SWEEP_LOOKBACK + 1):
            _idx = _cur_idx - lookback
            if _idx < 0:
                break

            _bar_h = float(df["High"].iloc[_idx])
            _bar_l = float(df["Low"].iloc[_idx])
            _bar_c = float(df["Close"].iloc[_idx])
            _bar_o = float(df["Open"].iloc[_idx])
            _bar_range = _bar_h - _bar_l

            if _bar_range <= 0:
                continue

            if direction == "UP":
                # ── 高値sweep: High > level ──
                if _bar_h <= level + _sweep_margin:
                    continue  # levelを超えていない

                # ウィック = levelを超えた部分 (upper wick beyond level)
                _wick_beyond = _bar_h - level
                _wick_ratio = _wick_beyond / _bar_range

                if _wick_ratio < self.WICK_RATIO_MIN:
                    continue  # ウィック比率不足 (実体で突き抜けている → 真のBK)

                # Close がlevel以下に回帰 (sweep後の即時rejection)
                if _bar_c > level:
                    continue  # Close が外側 → reclaimなし

                # ボリュームプロキシ: bar_range / ATR
                if atr > 0 and _bar_range / atr < self.VOL_RATIO_MIN:
                    continue  # ボリューム不足

                # 現在足のOpen がlevel内側 (次足確認)
                if cur_open > level:
                    continue  # 翌足もlevel外で始まった → 回帰不十分

                _sweep_quality = _wick_ratio * (_bar_range / atr)
                if _best_sweep is None or _sweep_quality > _best_sweep["quality"]:
                    _best_sweep = {
                        "sweep_extreme": _bar_h,
                        "sweep_bar_idx": _idx,
                        "level": level,
                        "direction": direction,
                        "wick_ratio": _wick_ratio,
                        "vol_ratio": _bar_range / atr if atr > 0 else 0,
                        "quality": _sweep_quality,
                    }

            else:  # DOWN
                # ── 安値sweep: Low < level ──
                if _bar_l >= level - _sweep_margin:
                    continue  # levelを割っていない

                # ウィック = levelを下回った部分 (lower wick beyond level)
                _wick_beyond = level - _bar_l
                _wick_ratio = _wick_beyond / _bar_range

                if _wick_ratio < self.WICK_RATIO_MIN:
                    continue  # ウィック比率不足

                # Close がlevel以上に回帰
                if _bar_c < level:
                    continue

                # ボリュームプロキシ
                if atr > 0 and _bar_range / atr < self.VOL_RATIO_MIN:
                    continue

                # 現在足のOpen がlevel内側
                if cur_open < level:
                    continue

                _sweep_quality = _wick_ratio * (_bar_range / atr)
                if _best_sweep is None or _sweep_quality > _best_sweep["quality"]:
                    _best_sweep = {
                        "sweep_extreme": _bar_l,
                        "sweep_bar_idx": _idx,
                        "level": level,
                        "direction": direction,
                        "wick_ratio": _wick_ratio,
                        "vol_ratio": _bar_range / atr if atr > 0 else 0,
                        "quality": _sweep_quality,
                    }

        if _best_sweep is None:
            return None

        # ── 次足 (現在足) のbody方向確認 ──
        if self.NEXT_BAR_BODY_CONFIRM:
            if direction == "UP":
                # 高値sweep後 → SELL方向 → 現在足は陰線 (C < O)
                if cur_close >= cur_open:
                    return None  # 陽線 = リバーサル方向不一致
            else:  # DOWN
                # 安値sweep後 → BUY方向 → 現在足は陽線 (C > O)
                if cur_close <= cur_open:
                    return None  # 陰線 = リバーサル方向不一致

        return _best_sweep

    # ══════════════════════════════════════════════════
    # ヘルパー: セッション開始30分チェック
    # ══════════════════════════════════════════════════

    @staticmethod
    def _bar_minutes(bar_dt) -> int:
        """バー時刻 -> UTC通算分 (0-1439)。取得不可なら -1。"""
        if hasattr(bar_dt, 'hour') and hasattr(bar_dt, 'minute'):
            return bar_dt.hour * 60 + bar_dt.minute
        return -1

    def _is_session_open(self, bar_minutes: int) -> bool:
        """セッション開始30分かどうか判定。

        London open: UTC 07:00-07:30
        NY open: UTC 13:30-14:00
        これらの時間帯では情報フロー主導の真のブレイクアウトが多い。
        (Andersen & Bollerslev 1998)

        Args:
            bar_minutes: UTC通算分

        Returns:
            True if in session open window (should be blocked)
        """
        if self.LDN_OPEN_START <= bar_minutes < self.LDN_OPEN_END:
            return True
        if self.NY_OPEN_START <= bar_minutes < self.NY_OPEN_END:
            return True
        return False

    # ══════════════════════════════════════════════════
    # ヘルパー: シンボル正規化
    # ══════════════════════════════════════════════════

    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        """シンボル文字列を正規化。"""
        s = symbol.upper().replace("=X", "").replace("=F", "").replace("/", "").replace("_", "")
        return s

    # ══════════════════════════════════════════════════
    # メイン評価 (evaluate)
    # ══════════════════════════════════════════════════

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        """市場状態を評価し、Liquidity Sweep シグナルを返す。

        検出フロー:
          1. ペア・時間帯・レジームフィルター
          2. フラクタルベースのスイングH/L検出 → クラスター化 (流動性プール)
          3. 各流動性プールに対してウィック構造によるsweep検出
          4. SL/TP/RR計算 → Candidate生成

        Args:
            ctx: SignalContext (全インジケータ + レイヤー情報)

        Returns:
            Candidate or None
        """
        # ══════════════════════════════════════════════════
        # Filter 1: ペアフィルター
        # ══════════════════════════════════════════════════
        _sym = self._normalize_symbol(ctx.symbol)
        if _sym not in self.ALLOWED_PAIRS:
            return None

        # ══════════════════════════════════════════════════
        # Filter 2: データ十分性
        # ══════════════════════════════════════════════════
        _min_bars = self.FRACTAL_LOOKBACK + self.FRACTAL_N + 2
        if ctx.df is None or len(ctx.df) < _min_bars:
            return None

        # ══════════════════════════════════════════════════
        # Filter 3: 時間帯フィルター
        # ══════════════════════════════════════════════════
        if ctx.hour_utc < self.ACTIVE_HOURS_START or ctx.hour_utc >= self.ACTIVE_HOURS_END:
            return None

        # v8.6: 金曜フィルター撤去 — Osler (2003): SLクラスターは曜日非依存
        # 保有30min-数時間で週末リスクは限定的

        # ── セッション開始30分ブロック ──
        _bt = ctx.bar_time
        if _bt is None and hasattr(ctx.df.index[-1], 'minute'):
            _bt = ctx.df.index[-1]
        if _bt is not None:
            _bm = self._bar_minutes(_bt)
            if _bm >= 0 and self._is_session_open(_bm):
                return None

        # ══════════════════════════════════════════════════
        # Filter 4: レジームフィルター (ADX + BB width)
        # ══════════════════════════════════════════════════

        # ADX < 25: レンジ環境のみ (Wilder 1978)
        # トレンド環境 (ADX >= 25) では真のブレイクアウトが多い → 逆張り危険
        if ctx.adx >= self.ADX_MAX:
            return None

        # ADX > 10: 最低限の方向性がないとsweep自体がノイズ
        if ctx.adx < self.ADX_MIN:
            return None

        # BB width percentile < 50%: squeeze直前環境を除外
        # squeeze (BB圧縮→解放) は真のブレイクアウトを生む → 逆張り禁止
        if ctx.bb_width_pct >= self.BB_WIDTH_PCT_MAX:
            return None

        # ══════════════════════════════════════════════════
        # STEP 1: フラクタルベース スイングH/L検出
        # ══════════════════════════════════════════════════
        _frac_highs, _frac_lows = self._find_fractal_levels(
            ctx.df, n=self.FRACTAL_N, lookback=self.FRACTAL_LOOKBACK
        )

        # クラスター化: 流動性プール (複数タッチ水準) の特定
        _major_highs = self._cluster_levels(_frac_highs, ctx.atr)
        _major_lows = self._cluster_levels(_frac_lows, ctx.atr)

        if not _major_highs and not _major_lows:
            return None

        # ══════════════════════════════════════════════════
        # STEP 2: ウィック構造によるSweep検出 + STEP 3: Entry確認
        # 各流動性プールに対してsweep + 次足確認を実施
        # ══════════════════════════════════════════════════
        _best_candidate = None
        _best_quality = 0.0

        # -- 高値sweep → SELL --
        for _level, _touches in _major_highs:
            # 水準が現在価格から遠すぎる場合スキップ (±3ATR以内)
            if abs(_level - ctx.entry) > ctx.atr * 3:
                continue

            result = self._detect_wick_sweep(
                ctx.df, _level, "UP", ctx.atr
            )
            if result is not None:
                _q = result["quality"] * (1 + _touches * 0.2)  # タッチ回数加重
                if _q > _best_quality:
                    _best_candidate = result
                    _best_candidate["signal"] = "SELL"
                    _best_candidate["touches"] = _touches
                    _best_quality = _q

        # -- 安値sweep → BUY --
        for _level, _touches in _major_lows:
            if abs(_level - ctx.entry) > ctx.atr * 3:
                continue

            result = self._detect_wick_sweep(
                ctx.df, _level, "DOWN", ctx.atr
            )
            if result is not None:
                _q = result["quality"] * (1 + _touches * 0.2)
                if _q > _best_quality:
                    _best_candidate = result
                    _best_candidate["signal"] = "BUY"
                    _best_candidate["touches"] = _touches
                    _best_quality = _q

        if _best_candidate is None:
            return None

        # ══════════════════════════════════════════════════
        # STEP 4: HTF方向フィルター (逆方向hard block)
        # ══════════════════════════════════════════════════
        _htf = ctx.htf or {}
        _agr = _htf.get("agreement", "mixed")
        signal = _best_candidate["signal"]

        # 強トレンドHTFへの逆張りブロック
        if signal == "BUY" and _agr == "bear":
            return None
        if signal == "SELL" and _agr == "bull":
            return None

        # ══════════════════════════════════════════════════
        # STEP 5: SL/TP 計算
        # ══════════════════════════════════════════════════
        _extreme = _best_candidate["sweep_extreme"]
        _level = _best_candidate["level"]
        _touches = _best_candidate["touches"]
        _wick_ratio = _best_candidate["wick_ratio"]
        _vol_ratio = _best_candidate["vol_ratio"]
        _is_buy = signal == "BUY"
        _dec = 3 if ctx.is_jpy or ctx.pip_mult == 100 else 5

        # SL: sweep extreme の外側 + ATR バッファ
        if _is_buy:
            sl = _extreme - ctx.atr * self.SL_ATR_BUFFER
        else:
            sl = _extreme + ctx.atr * self.SL_ATR_BUFFER

        # SL方向チェック (BUYならSL < entry, SELLならSL > entry)
        if _is_buy and sl >= ctx.entry:
            return None
        if not _is_buy and sl <= ctx.entry:
            return None

        # TP: 対面のスイングレベル (mean-reversion target)
        _tp_target = None
        if _is_buy and _major_highs:
            # BUY → 上方の最も近いスイングH
            _above = [lv for lv, _ in _major_highs if lv > ctx.entry + ctx.atr * 0.3]
            if _above:
                _tp_target = min(_above)
        elif not _is_buy and _major_lows:
            # SELL → 下方の最も近いスイングL
            _below = [lv for lv, _ in _major_lows if lv < ctx.entry - ctx.atr * 0.3]
            if _below:
                _tp_target = max(_below)

        # TP fallback: ATRベース
        if _tp_target is None:
            _tp_target = ctx.entry + ctx.atr * self.TP_ATR_MULT * (1 if _is_buy else -1)

        # TP最大距離キャップ
        _max_tp_dist = ctx.atr * self.TP_MAX_ATR
        _tp_dist_raw = abs(_tp_target - ctx.entry)
        if _tp_dist_raw > _max_tp_dist:
            _tp_target = ctx.entry + _max_tp_dist * (1 if _is_buy else -1)

        tp = _tp_target

        # ── RR チェック ──
        _sl_dist = abs(ctx.entry - sl)
        _tp_dist = abs(tp - ctx.entry)

        if _sl_dist <= 0:
            return None

        # MIN_RR未達の場合TPを拡張
        if _tp_dist / _sl_dist < self.MIN_RR:
            _tp_dist = _sl_dist * self.MIN_RR
            tp = ctx.entry + _tp_dist if _is_buy else ctx.entry - _tp_dist

        _rr = _tp_dist / _sl_dist

        # RR再確認 (TP最大距離キャップ後にRR不足の場合はスキップ)
        if _rr < self.MIN_RR:
            return None

        # ══════════════════════════════════════════════════
        # STEP 6: スコア計算 + Candidate生成
        # ══════════════════════════════════════════════════
        _score = 5.0

        # タッチ回数ボーナス (流動性プール密度: Osler 2003)
        if _touches >= 4:
            _score += 2.0
        elif _touches >= 3:
            _score += 1.0
        elif _touches >= 2:
            _score += 0.3

        # ウィック比率ボーナス (0.60-1.0, 高いほどrejectionが鮮明)
        if _wick_ratio >= 0.80:
            _score += 1.0
        elif _wick_ratio >= 0.70:
            _score += 0.5

        # ボリュームプロキシボーナス (大口介入の痕跡)
        if _vol_ratio >= 2.0:
            _score += 1.0
        elif _vol_ratio >= 1.7:
            _score += 0.5

        # RRボーナス
        if _rr >= 2.5:
            _score += 1.0
        elif _rr >= 2.0:
            _score += 0.5

        # HTF方向一致ボーナス
        if (_is_buy and _agr == "bull") or (not _is_buy and _agr == "bear"):
            _score += 0.5

        # EMA短期方向一致ボーナス
        if (_is_buy and ctx.ema9 > ctx.ema21) or (not _is_buy and ctx.ema9 < ctx.ema21):
            _score += 0.3

        # ADX中間域ボーナス (15-22 = 最適レンジMR環境)
        if 15 <= ctx.adx <= 22:
            _score += 0.3

        # ── Reasons ──
        _level_pip = _level * ctx.pip_mult
        _exc_pip = abs(_extreme - _level) * ctx.pip_mult
        _sl_pip = _sl_dist * ctx.pip_mult
        _tp_pip = _tp_dist * ctx.pip_mult

        _reasons = [
            f"Liquidity Sweep: {signal} -- "
            f"Swing {'High' if not _is_buy else 'Low'} {_level:.{_dec}f} "
            f"(touches={_touches})",
            f"Sweep: wick_ratio={_wick_ratio:.0%} vol_ratio={_vol_ratio:.1f}x "
            f"extreme={_extreme:.{_dec}f} (+{_exc_pip:.1f}pip beyond level)",
            f"RR={_rr:.1f} SL={sl:.{_dec}f}({_sl_pip:.1f}pip) "
            f"TP={tp:.{_dec}f}({_tp_pip:.1f}pip)",
            f"Regime: ADX={ctx.adx:.1f} BB_width_pct={ctx.bb_width_pct:.0%}",
        ]

        # 確認ボーナスの理由追記
        if (_is_buy and _agr == "bull") or (not _is_buy and _agr == "bear"):
            _reasons.append(f"HTF agreement: {_agr}")
        if (_is_buy and ctx.ema9 > ctx.ema21) or (not _is_buy and ctx.ema9 < ctx.ema21):
            _reasons.append("EMA9/21 direction aligned")

        # Confidence: 基礎50 + タッチ×5 + RR×5 + wick×10
        _conf = int(min(90, 50 + _touches * 5 + int(_rr * 5) + int(_wick_ratio * 10)))

        return Candidate(
            signal=signal,
            confidence=_conf,
            sl=round(sl, 5 if not ctx.is_jpy else 3),
            tp=round(tp, 5 if not ctx.is_jpy else 3),
            reasons=_reasons,
            entry_type=self.name,
            score=_score,
        )
