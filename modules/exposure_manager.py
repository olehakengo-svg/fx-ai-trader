"""
Cross-Pair Exposure Manager — 通貨別ネットエクスポージャー管理
═══════════════════════════════════════════════════════════════

目的:
  全オープンポジションの通貨別ネットエクスポージャー(USD, EUR, GBP, JPY, XAU)を
  リアルタイム計算し、単一通貨への過剰集中を防止する。

学術的根拠:
  - ポートフォリオリスク管理の基本原則: 分散不足による集中リスク (Markowitz 1952)
  - 通貨ペア間の相関: USD/JPY↑ と EUR/USD↓ は共にUSDロング (実質2倍エクスポージャー)
  - FX ポートフォリオの因子分解: base/quote 通貨別に集約することで真のリスクを可視化

使用方法:
  em = ExposureManager()
  em.add_position("t1", "USD_JPY", "BUY", 5000)
  allowed, reason = em.check_new_trade("EUR_USD", "SELL", 5000)
  # → False, "USD exposure 10000u > 20000u limit" (if cumulative)
"""
import threading
from typing import Dict, Tuple, Optional


class ExposureManager:
    """通貨別ネットエクスポージャー計算・制限エンジン"""

    # ── 通貨ペア → (Base, Quote) 分解テーブル ──
    _PAIR_CURRENCIES: Dict[str, Tuple[str, str]] = {
        "USD_JPY": ("USD", "JPY"),
        "EUR_USD": ("EUR", "USD"),
        "EUR_JPY": ("EUR", "JPY"),
        "GBP_USD": ("GBP", "USD"),
        "GBP_JPY": ("GBP", "JPY"),
        "EUR_GBP": ("EUR", "GBP"),
        "AUD_USD": ("AUD", "USD"),
        "XAU_USD": ("XAU", "USD"),
    }

    # ── 制限パラメータ ──
    MAX_CURRENCY_EXPOSURE = 20_000   # 単一通貨ネット上限 (units)
    MAX_SAME_DIRECTION = 3           # 同方向ポジション上限 (ペア横断)
    # v7.2: 通貨別上限オーバーライド — XAUはコモディティ、FXとは独立リスク枠
    _CURRENCY_LIMITS = {
        "XAU": 10_000,   # XAU専用枠 (FX USDカウントと分離)
    }

    def __init__(self):
        self._positions: Dict[str, dict] = {}   # trade_id → {instrument, direction, units, is_shadow}
        self._lock = threading.Lock()

    # ── ポジション管理 ──

    def add_position(self, trade_id: str, instrument: str, direction: str,
                     units: int, is_shadow: bool = False):
        """ポジション追加 (エントリー時に呼ぶ).

        is_shadow=True のポジションは登録のみ行い、エクスポージャー集計および
        同方向カウントから除外する (OANDA未送信のため実弾リスクなし).
        v9.0 設計: ExposureManager は OANDA実弾専用リスク管理。
        """
        with self._lock:
            self._positions[trade_id] = {
                "instrument": instrument,
                "direction": direction,
                "units": units,
                "is_shadow": bool(is_shadow),
            }

    def remove_position(self, trade_id: str):
        """ポジション除去 (クローズ時に呼ぶ)"""
        with self._lock:
            self._positions.pop(trade_id, None)

    def set_shadow_status(self, trade_id: str, is_shadow: bool) -> bool:
        """既存ポジションの is_shadow を更新 (post-entry gate escalation 用).

        Returns True if the position existed and was updated.
        """
        with self._lock:
            pos = self._positions.get(trade_id)
            if pos is None:
                return False
            pos["is_shadow"] = bool(is_shadow)
            return True

    def clear(self):
        """全ポジションクリア"""
        with self._lock:
            self._positions.clear()

    # ── エクスポージャー計算 ──

    def get_currency_exposure(self) -> Dict[str, int]:
        """
        通貨別ネットエクスポージャーを返す。
        BUY USD_JPY 5000u → USD: +5000, JPY: -5000
        SELL EUR_USD 3000u → EUR: -3000, USD: +3000
        """
        with self._lock:
            return self._calc_exposure_unlocked()

    def _calc_exposure_unlocked(self) -> Dict[str, int]:
        """ロックなしの内部計算 (ロック取得済みの文脈で使用).

        Shadow ポジション (is_shadow=True) は OANDA未送信のため集計から除外。
        """
        exposure: Dict[str, int] = {}
        for pos in self._positions.values():
            if pos.get("is_shadow"):
                continue
            currencies = self._PAIR_CURRENCIES.get(pos["instrument"])
            if not currencies:
                continue
            base, quote = currencies
            sign = 1 if pos["direction"] == "BUY" else -1
            # BUY = base通貨ロング, quote通貨ショート
            exposure[base] = exposure.get(base, 0) + sign * pos["units"]
            exposure[quote] = exposure.get(quote, 0) - sign * pos["units"]
        return exposure

    # ── 新規トレード可否判定 ──

    def check_new_trade(self, instrument: str, direction: str, units: int
                        ) -> Tuple[bool, str]:
        """
        新規トレードがエクスポージャー制限に抵触しないか判定。
        Returns: (allowed: bool, reason: str)
        """
        currencies = self._PAIR_CURRENCIES.get(instrument)
        if not currencies:
            return True, ""  # 未知ペアは制限なし (フェイルオープン)

        base, quote = currencies
        sign = 1 if direction == "BUY" else -1

        with self._lock:
            current = self._calc_exposure_unlocked()

            # 1. 通貨別ネットエクスポージャー上限チェック
            new_base = current.get(base, 0) + sign * units
            new_quote = current.get(quote, 0) - sign * units

            # v7.2: 通貨別上限 — XAUはコモディティ専用枠
            _limit_base = self._CURRENCY_LIMITS.get(base, self.MAX_CURRENCY_EXPOSURE)
            _limit_quote = self._CURRENCY_LIMITS.get(quote, self.MAX_CURRENCY_EXPOSURE)
            if abs(new_base) > _limit_base:
                return False, (f"{base} net exposure {abs(new_base):,}u "
                               f"> {_limit_base:,}u limit")
            if abs(new_quote) > _limit_quote:
                return False, (f"{quote} net exposure {abs(new_quote):,}u "
                               f"> {_limit_quote:,}u limit")

            # 2. 同方向ポジション数チェック (通貨横断) — Shadow除外
            same_dir_count = sum(
                1 for p in self._positions.values()
                if p["direction"] == direction and not p.get("is_shadow")
            )
            if same_dir_count >= self.MAX_SAME_DIRECTION:
                return False, (f"same-direction ({direction}) positions "
                               f"{same_dir_count} >= {self.MAX_SAME_DIRECTION} limit")

        return True, ""

    # ── サマリー ──

    def get_summary(self) -> dict:
        """ダッシュボード / ログ用サマリー"""
        exposure = self.get_currency_exposure()
        max_exp = max((abs(v) for v in exposure.values()), default=0)
        return {
            "open_positions": len(self._positions),
            "currency_exposure": exposure,
            "max_single_currency": max_exp,
            "limit": self.MAX_CURRENCY_EXPOSURE,
            "utilization_pct": round(max_exp / self.MAX_CURRENCY_EXPOSURE * 100, 1)
                               if self.MAX_CURRENCY_EXPOSURE > 0 else 0,
        }

    def get_exposure_for_log(self) -> str:
        """1行ログ用フォーマット"""
        exp = self.get_currency_exposure()
        if not exp:
            return "exposure=empty"
        parts = [f"{k}:{v:+,}" for k, v in sorted(exp.items()) if v != 0]
        return "exposure={" + ", ".join(parts) + "}"
