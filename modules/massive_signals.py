"""
Massive Signal Enhancer — Massive API固有データを活用したシグナル強化モジュール
=================================================================================
Massive API (Polygon互換) が提供するVWAP・高品質OHLCVを活用し、
compute_signal / compute_daytrade_signal が返す基本シグナルの確度を補正する。

3つの強化軸:
  1. VWAPゾーン分析 (バンド + スロープ)
  2. ボリュームプロファイル (HVN/LVN)
  3. 機関投資家フロー検出 (大口キャンドル)

設計原則:
  - 加算的 (additive): confidence を調整するのみ。signal方向は変えない
  - 後方互換: vwap列が無いDFではシグナルをそのまま返す
  - numpy/pandas のみ依存 (追加ライブラリ不要)
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple


class MassiveSignalEnhancer:
    """Enhance trading signals using Massive API data features."""

    # ── 定数 ──────────────────────────────────────────
    VWAP_LOOKBACK = 20        # VWAPスロープ計算の期間
    VOLUME_PROFILE_BARS = 20  # ボリュームプロファイル計算期間
    VOLUME_PROFILE_BINS = 20  # 価格レベルのビン数
    INST_BODY_MULT = 2.0      # 機関キャンドル判定: body > avg * mult
    INST_VOL_MULT = 2.0       # 機関キャンドル判定: volume > avg * mult
    INST_LOOKBACK = 50        # 機関フロー計算の平均期間
    INST_CANDLE_COUNT = 3     # 直近N本の大口キャンドルを評価
    CONF_CAP = 95             # 最大confidence

    def enhance(self, df: pd.DataFrame, base_signal: dict,
                symbol: str = "USDJPY=X") -> dict:
        """
        基本シグナルをMassive固有データで強化する。

        Parameters
        ----------
        df : pd.DataFrame
            OHLCV + indicators付きDataFrame (vwap列が必要)
        base_signal : dict
            compute_signal / compute_daytrade_signal の戻り値
        symbol : str
            通貨ペアシンボル

        Returns
        -------
        dict
            強化済みシグナル (confidenceとreasonsが更新される)
        """
        # vwap列がない場合はそのまま返す
        if "vwap" not in df.columns or len(df) < 5:
            return base_signal

        sig = base_signal.copy()
        direction = sig.get("signal", "WAIT")
        conf = sig.get("confidence", 50)
        reasons = list(sig.get("reasons", []))
        enhancement_details = {}

        # ── 1. VWAPゾーン分析 ──
        vwap_result = self._vwap_zone_analysis(df, direction)
        conf += vwap_result["conf_adj"]
        reasons.extend(vwap_result["reasons"])
        enhancement_details["vwap_zone"] = vwap_result["zone"]
        enhancement_details["vwap_slope"] = vwap_result["slope_direction"]

        # ── 2. ボリュームプロファイル分析 ──
        vp_result = self._volume_profile_analysis(df, direction)
        conf += vp_result["conf_adj"]
        reasons.extend(vp_result["reasons"])
        enhancement_details["volume_profile"] = {
            "hvn_levels": vp_result.get("hvn_levels", []),
            "lvn_levels": vp_result.get("lvn_levels", []),
            "near_node": vp_result.get("near_node", "none"),
        }

        # ── 3. 機関投資家フロー ──
        inst_result = self._institutional_flow(df, direction)
        conf += inst_result["conf_adj"]
        reasons.extend(inst_result["reasons"])
        enhancement_details["institutional_flow"] = {
            "direction": inst_result.get("flow_direction", "neutral"),
            "large_candle_count": inst_result.get("large_candle_count", 0),
        }

        # confidence cap
        conf = int(max(0, min(self.CONF_CAP, conf)))

        sig["confidence"] = conf
        sig["reasons"] = reasons
        sig["massive_enhancement"] = enhancement_details

        return sig

    # ══════════════════════════════════════════════════
    #  1. VWAPゾーン分析
    # ══════════════════════════════════════════════════
    def _vwap_zone_analysis(self, df: pd.DataFrame,
                            direction: str) -> dict:
        """
        VWAPバンド (±1sigma, ±2sigma) + スロープで確度補正。
        """
        result: Dict = {"conf_adj": 0, "reasons": [], "zone": "NEUTRAL",
                        "slope_direction": "flat"}

        vwap = df["vwap"].values
        close = df["Close"].values if "Close" in df.columns else df["close"].values
        volume = df["Volume"].values if "Volume" in df.columns else df["volume"].values

        current_price = float(close[-1])
        current_vwap = float(vwap[-1])

        if current_vwap <= 0:
            return result

        # ── VWAPバンド計算 (volume-weighted std dev) ──
        lookback = min(self.VWAP_LOOKBACK, len(df))
        recent_close = close[-lookback:]
        recent_vwap = vwap[-lookback:]
        recent_vol = volume[-lookback:]

        # vwapがゼロの行をフィルタ
        valid_mask = recent_vwap > 0
        if valid_mask.sum() < 5:
            return result

        deviations = recent_close[valid_mask] - recent_vwap[valid_mask]
        weights = recent_vol[valid_mask]
        total_weight = weights.sum()
        if total_weight <= 0:
            return result

        weighted_mean_dev = np.average(deviations, weights=weights)
        weighted_var = np.average((deviations - weighted_mean_dev) ** 2,
                                 weights=weights)
        sigma = float(np.sqrt(weighted_var))

        if sigma <= 0:
            return result

        # ── ゾーン分類 ──
        # 2026-04-23: VWAP alignment 実測で逆校正 (aligned WR 20.0% vs conflict WR 26.7%)。
        # 根本原因: このロジックは TF (trend-following) 前提だが、shadow データの多くは
        # MR (mean-reversion) 戦略で価格のVWAP上下は support/resistance として逆作用。
        # conf_adj を 0 に中立化。ゾーン情報は reasons に残し分析・ログ用途で保持。
        # 検証: /tmp/triple_audit.py, wiki/analyses/shadow-subcell-analysis-2026-04-23.md
        dev = current_price - current_vwap
        zone = "NEUTRAL"
        adj = 0  # neutralized — see comment above

        if dev > 2 * sigma:
            zone = "VWAP_EXTENDED"
            result["reasons"].append(
                f"VWAP +{dev / sigma:.1f}sigma ゾーン (過伸長域)")
        elif dev > 0:
            zone = "VWAP_ABOVE_NEAR"
            result["reasons"].append(
                f"VWAP上位 (+{dev / sigma:.1f}sigma)")
        elif dev < -2 * sigma:
            zone = "VWAP_EXTENDED_DOWN"
            result["reasons"].append(
                f"VWAP {dev / sigma:.1f}sigma ゾーン (下方過伸長)")
        elif dev < 0:
            zone = "VWAP_BELOW_NEAR"
            result["reasons"].append(
                f"VWAP下位 ({dev / sigma:.1f}sigma)")

        result["zone"] = zone
        result["conf_adj"] = adj

        # ── VWAPスロープ ──
        slope_bars = min(self.VWAP_LOOKBACK, len(df))
        if slope_bars >= 5:
            vwap_slice = vwap[-slope_bars:]
            valid_vwap = vwap_slice[vwap_slice > 0]
            if len(valid_vwap) >= 5:
                # 線形回帰でスロープを計算
                x = np.arange(len(valid_vwap))
                slope = float(np.polyfit(x, valid_vwap, 1)[0])

                # 2026-04-23: slope_adj も TF 前提のため中立化 (VWAP ゾーン修正と同理由)。
                # 方向情報は reasons にログ保持、conf_adj は加算しない。
                if slope > 0:
                    result["slope_direction"] = "rising"
                elif slope < 0:
                    result["slope_direction"] = "falling"

                if result["slope_direction"] != "flat":
                    result["reasons"].append(
                        f"VWAPスロープ {result['slope_direction']}")

        return result

    # ══════════════════════════════════════════════════
    #  2. ボリュームプロファイル分析
    # ══════════════════════════════════════════════════
    def _volume_profile_analysis(self, df: pd.DataFrame,
                                 direction: str) -> dict:
        """
        価格帯別出来高分布からHVN (High Volume Node) / LVN (Low Volume Node) を検出。
        """
        result: Dict = {"conf_adj": 0, "reasons": [],
                        "hvn_levels": [], "lvn_levels": [], "near_node": "none"}

        lookback = min(self.VOLUME_PROFILE_BARS, len(df))
        recent = df.iloc[-lookback:]

        close = recent["Close"].values if "Close" in recent.columns else recent["close"].values
        high = recent["High"].values if "High" in recent.columns else recent["high"].values
        low = recent["Low"].values if "Low" in recent.columns else recent["low"].values
        volume = recent["Volume"].values if "Volume" in recent.columns else recent["volume"].values

        if volume.sum() <= 0:
            return result

        # 価格レンジをビンに分割
        price_min = float(low.min())
        price_max = float(high.max())
        price_range = price_max - price_min
        if price_range <= 0:
            return result

        n_bins = self.VOLUME_PROFILE_BINS
        bin_edges = np.linspace(price_min, price_max, n_bins + 1)
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
        vol_profile = np.zeros(n_bins)

        # 各バーの出来高をHigh-Low範囲のビンに比例分配
        for i in range(len(close)):
            bar_low = float(low[i])
            bar_high = float(high[i])
            bar_vol = float(volume[i])
            if bar_vol <= 0 or bar_high <= bar_low:
                continue
            for j in range(n_bins):
                bin_lo = bin_edges[j]
                bin_hi = bin_edges[j + 1]
                # ビンとバーの重複部分を計算
                overlap_lo = max(bar_low, bin_lo)
                overlap_hi = min(bar_high, bin_hi)
                if overlap_hi > overlap_lo:
                    overlap_ratio = (overlap_hi - overlap_lo) / (bar_high - bar_low)
                    vol_profile[j] += bar_vol * overlap_ratio

        if vol_profile.sum() <= 0:
            return result

        # ── HVN / LVN 判定 ──
        vol_mean = vol_profile.mean()
        vol_std = vol_profile.std()
        if vol_std <= 0:
            return result

        hvn_threshold = vol_mean + vol_std  # 平均+1σ以上がHVN
        lvn_threshold = vol_mean - 0.5 * vol_std  # 平均-0.5σ以下がLVN

        hvn_levels = [float(bin_centers[i]) for i in range(n_bins)
                      if vol_profile[i] >= hvn_threshold]
        lvn_levels = [float(bin_centers[i]) for i in range(n_bins)
                      if vol_profile[i] <= lvn_threshold and vol_profile[i] > 0]

        result["hvn_levels"] = [round(p, 5) for p in hvn_levels]
        result["lvn_levels"] = [round(p, 5) for p in lvn_levels]

        # 現在価格の位置判定
        current_price = float(close[-1])
        atr = float(df["atr"].iloc[-1]) if "atr" in df.columns else price_range * 0.1

        # HVN近接: support/resistance → +3
        near_hvn = any(abs(current_price - h) < atr * 0.3 for h in hvn_levels)
        # LVN内: 不安定ゾーン → -2
        near_lvn = any(abs(current_price - l) < atr * 0.3 for l in lvn_levels)

        if near_hvn and direction != "WAIT":
            result["conf_adj"] = +3
            result["near_node"] = "HVN"
            result["reasons"].append(
                f"HVN近接 (高出来高ノード): S/R確度UP (+3)")
        elif near_lvn and direction != "WAIT":
            result["conf_adj"] = -2
            result["near_node"] = "LVN"
            result["reasons"].append(
                f"LVN内 (低出来高ノード): 不安定ゾーン (-2)")

        return result

    # ══════════════════════════════════════════════════
    #  3. 機関投資家フロー検出
    # ══════════════════════════════════════════════════
    def _institutional_flow(self, df: pd.DataFrame,
                            direction: str) -> dict:
        """
        大口キャンドル (body > 2x avg, volume > 2x avg) の方向から機関フローを推定。
        """
        result: Dict = {"conf_adj": 0, "reasons": [],
                        "flow_direction": "neutral", "large_candle_count": 0}

        if len(df) < self.INST_LOOKBACK:
            return result

        close = df["Close"].values if "Close" in df.columns else df["close"].values
        open_ = df["Open"].values if "Open" in df.columns else df["open"].values
        volume = df["Volume"].values if "Volume" in df.columns else df["volume"].values

        # ボディサイズ
        bodies = np.abs(close - open_)

        lookback = min(self.INST_LOOKBACK, len(df))
        avg_body = bodies[-lookback:].mean()
        avg_vol = volume[-lookback:].mean()

        if avg_body <= 0 or avg_vol <= 0:
            return result

        # 大口キャンドル検出
        is_large = ((bodies > avg_body * self.INST_BODY_MULT) &
                    (volume > avg_vol * self.INST_VOL_MULT))

        # 直近のN本の大口キャンドルの方向
        large_indices = np.where(is_large)[0]
        if len(large_indices) == 0:
            return result

        recent_large = large_indices[-self.INST_CANDLE_COUNT:]
        result["large_candle_count"] = len(recent_large)

        bullish_count = 0
        bearish_count = 0
        for idx in recent_large:
            if close[idx] > open_[idx]:
                bullish_count += 1
            elif close[idx] < open_[idx]:
                bearish_count += 1

        # フロー方向判定
        if bullish_count > bearish_count:
            result["flow_direction"] = "bullish"
            if direction == "BUY":
                result["conf_adj"] = +3
                result["reasons"].append(
                    f"機関フロー: 買い優勢 ({bullish_count}/{len(recent_large)}本) "
                    f"BUY方向一致 (+3)")
            elif direction == "SELL":
                result["reasons"].append(
                    f"機関フロー: 買い優勢 ({bullish_count}/{len(recent_large)}本) "
                    f"SELL方向不一致")
        elif bearish_count > bullish_count:
            result["flow_direction"] = "bearish"
            if direction == "SELL":
                result["conf_adj"] = +3
                result["reasons"].append(
                    f"機関フロー: 売り優勢 ({bearish_count}/{len(recent_large)}本) "
                    f"SELL方向一致 (+3)")
            elif direction == "BUY":
                result["reasons"].append(
                    f"機関フロー: 売り優勢 ({bearish_count}/{len(recent_large)}本) "
                    f"BUY方向不一致")

        return result

    # ══════════════════════════════════════════════════
    #  診断用: 現在のシグナル品質メトリクス
    # ══════════════════════════════════════════════════
    def get_signal_quality(self, df: pd.DataFrame,
                           symbol: str = "USDJPY=X") -> dict:
        """
        シグナル品質メトリクスを返す (/api/massive/signal-quality 用)。
        """
        if "vwap" not in df.columns or len(df) < 5:
            return {"available": False, "reason": "VWAP data not available"}

        close = df["Close"].values if "Close" in df.columns else df["close"].values
        current_price = float(close[-1])

        # VWAPゾーン
        vwap_info = self._vwap_zone_analysis(df, "BUY")  # direction neutral
        # ボリュームプロファイル
        vp_info = self._volume_profile_analysis(df, "BUY")
        # 機関フロー
        inst_info = self._institutional_flow(df, "BUY")

        return {
            "available": True,
            "symbol": symbol,
            "current_price": round(current_price, 5),
            "vwap": {
                "zone": vwap_info["zone"],
                "slope": vwap_info["slope_direction"],
            },
            "volume_profile": {
                "hvn_levels": vp_info.get("hvn_levels", []),
                "lvn_levels": vp_info.get("lvn_levels", []),
                "current_node": vp_info.get("near_node", "none"),
            },
            "institutional_flow": {
                "direction": inst_info.get("flow_direction", "neutral"),
                "large_candle_count": inst_info.get("large_candle_count", 0),
            },
        }
