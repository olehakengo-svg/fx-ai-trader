# Micro-Scalp Strategy Suite 設計書

**作成日**: 2026-04-17
**位置づけ**: 疑似スキャルピング（pseudo-scalping）戦略群
**対象TF**: 1秒足（tickデータ集約）
**保有期間**: 3〜15分のマイクロトレンド

## 設計仕様

| 項目 | 値 | 根拠 |
|------|---|------|
| スプレッド前提 | 0.8 pips | OANDA USD/JPY 流動性時間帯実績 |
| 通信遅延 | 150 ms | 個人投資家の典型RTT |
| 遅延slippage係数 | 0.001 pips/ms | Evans&Lyons (2002)実測値 |
| 最低TP | 8 pips | 片道コスト 0.95pips × 約8倍のエッジ |
| 最大保有時間 | 15分 | HFT領域（数秒決済）を明示排除 |
| パラメータ上限 | 各戦略 **2個まで** | 過学習防止 |

## 収録戦略

### 1. TVSM (Tick Volume Spike Momentum)
- **仮説**: 大口注文が tick_volume 3σ超スパイクとして現れ、数分の慣性を生む
- **エントリー**: スパイク検知+2バー後の方向継続確認
- **SL/TP**: 1.2 ATR / 3.0 ATR (≥ 8 pips ガード)
- **パラメータ**: spike_z (3.0), tp_atr_mult (3.0)
- **学術根拠**: Kyle (1985), Biais et al. (1995)

### 2. VBP (Volatility Breakout Pullback)
- **仮説**: ブレイク直後HFTに負けるが、最初の押し目からの二番動きは個人でも取れる
- **エントリー**: 30分レンジブレイク → 50%戻し → 反発確認3バー
- **SL/TP**: 押し目極値 - 0.5ATR / ブレイク初速幅 × 2.0 (≥ 8 pips)
- **パラメータ**: lookback_sec (1800), pullback_ratio (0.5)
- **学術根拠**: Lo, Mamaysky, Wang (2000), Brock et al. (1992)

### 3. OFIMR (Order Flow Imbalance Mean Reversion)
- **仮説**: 3分OFI 2σ超偏り + VWAP乖離1ATR超 → 在庫不均衡の反転を取る
- **エントリー**: OFI方向と**逆**方向へfade（反平均回帰）
- **SL/TP**: 極値+0.3ATR / micro-VWAP (≥ 8 pips)
- **パラメータ**: window_sec (180), z_thresh (2.0)
- **学術根拠**: Chordia & Subrahmanyam (2004), Evans & Lyons (2002)

### 補完関係

```
時刻 t:    大口注文発生
           ↓ tick_volume spike
時刻 t+2:  TVSM エントリー ← モメンタム取得（慣性1〜3分）
           ↓ モメンタム継続
時刻 t+3〜8分: TVSM決済 / マイクロトレンド終焉
           ↓ OFI過剰偏りのまま
時刻 t+8〜12分: OFIMR エントリー ← 反転取得（MR 5〜10分）
```

TVSM と OFIMR は**時間差で補完関係**。同一方向のスパイクから、
モメンタム取得→反転取得の2回転エッジ取得を目指す。

## Look-ahead Bias 防止

| 指標 | 計算範囲 | 現在バー除外 |
|------|---------|-------------|
| TVSM μ/σ | `bars[-(LOOKBACK+3):-3]` | ✅ スパイクバーも除外 |
| ATR(60) | `bars[:-1]` | ✅ |
| VBP レンジ | `bars[-(L+1):-1]` | ✅ |
| OFIMR 分布 | `bars[-(DIST+W):-W]` | ✅ 現在窓を除外 |

## コストモデル

```python
片道コスト = spread/2 + slippage_per_ms × latency_ms
           = 0.4 + 0.001 × 150 = 0.55 pips
往復コスト = 2 × 0.55 = 1.1 pips
```

エントリー・決済の双方で適用することで、
最低TP 8 pips > 1.1 pips × 約7倍の安全マージン確保。

## 実運用時の留意点

1. **tick_volume取得**: OANDA v20 API streaming で `tick_count`
   または bid/ask 更新カウントを1秒集約
2. **latency実測**: 利用ブローカーへの ping 実測値で `CostModel.latency_ms` を調整
3. **ボラティリティ異常時停止**: ATR(60) > 通常値の5倍 → 全戦略停止
4. **ニュース時間帯**: 経済指標発表±5分は spread拡大のため disable 推奨

## 既存システムとの統合

現状は**独立モジュール**として `strategies/micro_scalp/` 配置。
本格統合前に必要な作業:
1. 1秒足データ取得パイプライン構築（OANDA streaming API ラッパー）
2. `MicroBacktester` で 30日以上の tick データで検証
3. PAIR_PROMOTED 判定基準: N≥30, WR≥50%, PF≥1.3, 摩擦込みEV>0

現時点ではpaper tradingとして蓄積、365日相当のデータで検証後に Shadow → Live 昇格判断。

## ファイル構成

```
strategies/micro_scalp/
├── __init__.py              # 公開API
├── base.py                  # TickBar / CostModel / MicroSignal / MicroStrategyBase
├── tvsm.py                  # Strategy #1
├── vbp.py                   # Strategy #2
├── ofi_mr.py                # Strategy #3
└── backtest.py              # MicroBacktester + 合成データ生成
```
