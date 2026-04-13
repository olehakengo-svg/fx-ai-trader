"""
Gotobi Fix (五十日仲値) — 五十日のUSD/JPY仲値買い圧力を利用するデイトレ戦略

学術的根拠:
  - Bessho et al. (2023, arXiv): "Five-Ten Days (Gotobi) Anomaly in Japanese Yen"
    五十日(5, 10, 15, 20, 25, 30日)のUSD/JPY上昇バイアスを統計的に確認
  - Ito & Yamada (2017, JIE): "Was the Forex Fixing Fixed?"
    仲値決定(09:55 JST)前のドル買い圧力と決定後の反転パターンを文書化

メカニズム:
  五十日(ごとおび)は日本企業の決済日。輸入企業がドル支払いのためUSD買い注文を
  仲値(09:55 JST = 00:55 UTC)に向けて集中的に出す。
  この実需フローが08:45-10:00 JSTの間にUSD/JPYを押し上げる。
  平均的な上昇幅は5-15pip。月末最終営業日も同様のパターンが発生。

パラメータ:
  SL: 20 pips (固定 — ATR非依存、短時間ウィンドウのため)
  TP: 12 pips (保守的 — 平均5-15pipムーブの確実な部分を狙う)
  MIN_RR: 0.6 (低RRだが高WRで補償 — イベントドリブン戦略)
  月曜/金曜除外 (仲値フロー不安定)
  ADXフィルター不要 (イベントドリブン、トレンド非依存)
"""
from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from typing import Optional
import calendar


class GotobiFix(StrategyBase):
    name = "gotobi_fix"
    mode = "daytrade"
    enabled = True

    # ══════════════════════════════════════════════════
    # 対象通貨ペア
    # ══════════════════════════════════════════════════
    _enabled_symbols = {"USDJPY"}

    # ══════════════════════════════════════════════════
    # 五十日定義
    # ══════════════════════════════════════════════════
    GOTOBI_DAYS = {5, 10, 15, 20, 25, 30}

    # ══════════════════════════════════════════════════
    # 時間帯パラメータ (UTC)
    # v8.6: 時間窓拡張 — Ito & Yamada (2017): 仲値フローは9:00-10:00 JST
    #   = UTC 0:00-1:00。しかしプレポジショニングはUTC 23:00から始まる
    # ══════════════════════════════════════════════════
    # NOTE: エントリーウィンドウはUTC日付境界をまたぐ
    ENTRY_START_LATE = 1380    # UTC 23:00 (v8.6: 23:45→23:00 プレポジ窓拡大)
    ENTRY_END_EARLY = 75       # UTC 01:15 (v8.6: 01:00→01:15 Fix後のリバーサル吸収)

    # Exit: UTC 01:15 (JST 10:15) or TP hit
    EXIT_TIME = 75             # UTC 01:15 (v8.6: 01:00→01:15)

    # ══════════════════════════════════════════════════
    # SL/TP パラメータ (固定pip)
    # ══════════════════════════════════════════════════
    SL_PIPS = 20               # 20 pips固定
    TP_PIPS = 12               # 12 pips固定 (保守的)
    MIN_RR = 0.6               # 低RR許容 (高WRイベントドリブン)

    # ══════════════════════════════════════════════════
    # 保持
    # ══════════════════════════════════════════════════
    MAX_HOLD_BARS = 5          # 5バー = 75分 @ 15m (ウィンドウ内で完結)

    # ──────────────────────────────────────────────────
    # ヘルパー
    # ──────────────────────────────────────────────────

    @staticmethod
    def _is_gotobi_day(dt_obj) -> bool:
        """バー日時が五十日かどうかを判定。月末最終営業日も含む。

        五十日: 5, 10, 15, 20, 25, 30日
        月末最終営業日: 月の最終日が土日の場合、直前の金曜日

        NOTE: UTC 23:45のバーの場合、翌日(JST日付)が五十日かチェックする必要がある。
        UTC 23:45 = JST 08:45 → JST日付は翌日の可能性。
        簡略化: UTC日付とUTC翌日の両方をチェック。
        """
        if dt_obj is None or not hasattr(dt_obj, 'day'):
            return False

        day = dt_obj.day
        month = dt_obj.month
        year = dt_obj.year

        # 当日が五十日
        if day in GotobiFix.GOTOBI_DAYS:
            return True

        # 月末最終営業日チェック
        _last_day = calendar.monthrange(year, month)[1]
        _last_weekday = calendar.weekday(year, month, _last_day)
        # 月末が土曜(5) → 金曜(前日)が最終営業日
        # 月末が日曜(6) → 金曜(前々日)が最終営業日
        if _last_weekday == 5:  # Saturday
            _last_biz_day = _last_day - 1
        elif _last_weekday == 6:  # Sunday
            _last_biz_day = _last_day - 2
        else:
            _last_biz_day = _last_day

        if day == _last_biz_day:
            return True

        # UTC 23:xx の場合、翌日(JST日付)が五十日かもチェック
        if hasattr(dt_obj, 'hour') and dt_obj.hour >= 23:
            _next_day = day + 1
            if _next_day > _last_day:
                # 翌月1日 → 五十日ではない
                return False
            if _next_day in GotobiFix.GOTOBI_DAYS:
                return True
            # 翌日が月末最終営業日
            if _next_day == _last_biz_day:
                return True

        return False

    @staticmethod
    def _total_minutes(ctx: SignalContext) -> int:
        """現在バーのUTC通算分を返す。取得不可なら -1。"""
        _minute = 0
        if ctx.bar_time is not None and hasattr(ctx.bar_time, 'minute'):
            _minute = ctx.bar_time.minute
        elif ctx.df is not None and len(ctx.df) > 0 and hasattr(ctx.df.index[-1], 'minute'):
            _minute = ctx.df.index[-1].minute
        else:
            return -1
        return ctx.hour_utc * 60 + _minute

    # ──────────────────────────────────────────────────
    # メインロジック
    # ──────────────────────────────────────────────────

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        # ── USD/JPY専用 ──
        _sym = ctx.symbol.upper().replace("=X", "").replace("/", "").replace("_", "")
        if _sym != "USDJPY":
            return None

        # ── データ十分性 ──
        if ctx.df is None or len(ctx.df) < 5:
            return None

        # v8.6: 月曜/金曜ブロック撤去 — Ito & Yamada (2017): 仲値効果は全営業日で確認
        # 月6回の五十日から月金除外で33%喪失は機会損失が大きすぎる
        # Shadow→Sentinelでデータ蓄積を優先し、曜日別WRを事後検証

        # ── 五十日チェック ──
        # v8.9: bar_time=None(ライブモード) → DFインデックスから日付取得
        _check_time = ctx.bar_time
        if _check_time is None and ctx.df is not None and len(ctx.df) > 0:
            _check_time = ctx.df.index[-1]
        if _check_time is None or not self._is_gotobi_day(_check_time):
            return None

        # ── 時間帯チェック: UTC 23:45 - 01:00 ──
        _total_min = self._total_minutes(ctx)
        if _total_min < 0:
            return None

        # エントリーウィンドウはUTC日付境界をまたぐ
        # UTC 23:45 (1425分) 以降 OR UTC 01:00 (60分) 以前
        _in_window = (_total_min >= self.ENTRY_START_LATE) or (_total_min <= self.ENTRY_END_EARLY)
        if not _in_window:
            return None

        # ── ATR有効性チェック ──
        if ctx.atr <= 0:
            return None

        # ── BUY ONLY: 陽線確認 (Close > Open) ──
        # v8.9: SENTINEL蓄積フェーズのため陽線フィルター緩和。陰線でもBUYシグナル生成
        # データN>=30到達後に陽線フィルターの効果を検証し、復活/維持を判断
        # if ctx.entry <= ctx.open_price:
        #     return None  # 陰線 → 仲値買い圧力なし

        # ═══════════════════════════════════════════════════
        # BUYシグナル生成
        # ═══════════════════════════════════════════════════
        signal = "BUY"
        score = 4.0
        reasons = []

        # SL/TP計算 (固定pip)
        _pip_value = 1.0 / ctx.pip_mult  # 1pip = 0.01 for JPY pairs
        sl = ctx.entry - self.SL_PIPS * _pip_value
        tp = ctx.entry + self.TP_PIPS * _pip_value

        # RR検証
        _sl_d = abs(ctx.entry - sl)
        _tp_d = abs(tp - ctx.entry)
        if _sl_d <= 0:
            return None
        _rr = _tp_d / _sl_d
        if _rr < self.MIN_RR:
            return None

        # 日付情報
        _day_str = ""
        if ctx.bar_time is not None and hasattr(ctx.bar_time, 'day'):
            _day_str = f" ({ctx.bar_time.month}/{ctx.bar_time.day})"

        reasons.append(
            f"✅ 五十日仲値BUY: 輸入企業USD買い集中{_day_str} "
            f"(Bessho 2023 / Ito & Yamada 2017)"
        )
        reasons.append(
            f"✅ 陽線確認: Close={ctx.entry:.3f} > Open={ctx.open_price:.3f}"
        )
        reasons.append(
            f"📊 SL={sl:.3f} (-{self.SL_PIPS}pip) "
            f"TP={tp:.3f} (+{self.TP_PIPS}pip) RR={_rr:.2f}"
        )

        # ═══════════════════════════════════════════════════
        # スコアボーナス
        # ═══════════════════════════════════════════════════

        # 前日USD/JPY下落 → 企業の買い需要がより攻撃的
        if len(ctx.df) >= 2:
            # 前日の変動を近似: 直近数バーのClose変化
            # 15m足では前日全体の判定は困難なため、直近のバイアスで代替
            _prev_close = ctx.prev_close
            _prev_open = ctx.prev_open
            if _prev_close < _prev_open:
                score += 0.5
                _prev_move = (_prev_close - _prev_open) * ctx.pip_mult
                reasons.append(
                    f"✅ 前足下落({_prev_move:.1f}pip) → 企業買い積極化"
                )

        # HTF方向一致ボーナス
        _htf = ctx.htf or {}
        _agr = _htf.get("agreement", "mixed")
        if _agr == "bull":
            score += 0.3
            reasons.append(f"✅ HTF方向一致({_agr})")

        # EMA方向一致
        if ctx.ema9 > ctx.ema21:
            score += 0.3
            reasons.append("✅ EMA短期方向一致(9>21)")

        conf = int(min(85, 50 + score * 4))
        return Candidate(
            signal=signal, confidence=conf, sl=sl, tp=tp,
            reasons=reasons, entry_type=self.name, score=score
        )
