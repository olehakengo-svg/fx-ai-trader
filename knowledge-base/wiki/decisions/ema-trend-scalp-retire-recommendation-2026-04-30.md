# ema_trend_scalp 廃止提案 (2026-04-30)

**Status**: 📝 Recommendation only — 撤廃自体はユーザ判断
**Author**: Claude (clean-quant analyst mode)
**Trigger**: ma_trend_perfect (v1b) Pre-reg LOCK 提出に伴う相対比較

## 1. 提案

`strategies/scalp/ema_trend_scalp.py` を以下のいずれかで処遇する:

| Option | 概要 | 推奨度 |
|---|---|---|
| **A. 完全削除** | コード削除、`__init__.py` 登録削除、`_FORCE_DEMOTED` から除去、KB に retire 記録 | ⭐⭐⭐ |
| B. ファイル維持 + 登録解除 | `__init__.py` から登録だけ外す、コードは history として残す | ⭐⭐ |
| C. 現状維持 (FORCE_DEMOTED) | 何もしない | ⭐ |

## 2. 根拠 (クオンツ的論理)

### 直接エビデンス
- **LIVE 実績**: N=0 (2026-04-22 〜 2026-04-30 で実弾発火ゼロ)
- **Shadow 実績**: N=88, EV=-1.219 pip, PF<1.0 (pre-registration-2026-04-22.md)
- **構造的負け要因**:
  - pullback 型ゆえ ADX>31 で `confidence_v2` ペナルティ発火
  - 強トレンド中は発火停止 / 弱トレンドではダマシ
  - BB%B 中間帯 (0.25-0.75) フィルタが過剰制限
  - 摩擦 (friction) コストがエッジを上回る (BT EV<0 with friction)

### 相対エビデンス (vs ma_trend_perfect v1b, 同一 USD_JPY × 180d × 0.8 spread)
| 指標 | ema_trend_scalp Shadow (N=88) | ma_trend_perfect v1b BT (N=369) | 比 |
|---|---|---|---|
| EV pip | -1.219 | +1.732 | n/a (符号反転) |
| PF | <1.0 (~0.685) | 1.99 | **2.9x** |
| WR | ~30-40% (推定) | 60.7% | n/a |
| Kelly | 0% | 30.2% | n/a |
| Tokyo 特化 PF | n/a | 3.84 | **5.6x** |
| Tokyo Wilson95 下限 | n/a | 63.75% | n/a |

→ Plan 設計時の「相対 PF 比 > 1.5x で真の改善」基準を **大幅クリア (2.9x)**。

### v1b は ema_trend_scalp の構造的弱点をすべて克服している
1. **pullback 型 → 純粋順張り**: パーフェクトオーダー条件を要求し、強トレ
   ンドが逆風にならない設計
2. **過剰フィルタ撤廃**: BB%B 中間帯ロジック削除、代わりに H1 EMA200 +
   M15 大循環という構造的トレンド確認
3. **friction 越え**: BT で spread 0.8 pip 控除後も Kelly 30% を維持
4. **多時間軸カスケード**: H1 → M15 → M5 → M1 の 3 段で ダマシを統計的削減

### 撤廃のリスク
- ema_trend_scalp Shadow が稼働続行で「逆張り兆候を発見する反証データ」を
  生成できる可能性 → **低い** (88 trades で十分なサンプル、構造的負けは確定)
- 将来 pullback 戦略全般を再設計するときの参照点として残したい
  → **B Option (登録解除のみ) が妥協点**

## 3. 提案する具体的変更 (Option A 採用時)

```python
# strategies/scalp/__init__.py 修正
# 削除する行:
from strategies.scalp.ema_trend_scalp import EmaTrendScalp
# strategies リストから:
EmaTrendScalp(),

# modules/demo_trader.py:5851 から削除
"ema_trend_scalp",   # _FORCE_DEMOTED set から
```

`strategies/scalp/ema_trend_scalp.py` 削除。
`knowledge-base/wiki/strategies/ema-trend-scalp.md` に retire 記録を追加
(もし KB ページが存在すれば; 存在しなければ作成不要)。

## 4. 推奨待機期間

**ma_trend_perfect Pre-reg LOCK 解除 (2026-05-14) 以降に判断するのが安全**:
- v1b が LIVE 昇格条件を満たした後で撤廃すれば「代替戦略あり」と確定
- v1b が逆に Phase B で reject されたら、ema_trend_scalp 系の再設計が
  必要となる可能性があるので保持しておく

## 5. ユーザ判断ポイント

- [ ] Option A (完全削除) でよいか
- [ ] Option B (登録解除のみ、コード残置) を選ぶか
- [ ] 待機 (2026-05-14 v1b 判定後) を選ぶか
- [ ] 関連 KB ページ (`wiki/strategies/ema-trend-scalp.md` 存在しない) の作成要否

## Related

- ma_trend_perfect Pre-reg LOCK: [[pre-reg-ma-trend-perfect-2026-04-30]]
- MA-Generic Family v1 設計書: [[ma_generic_family_v1]]
- ema_trend_scalp 当初 BT: [[pre-registration-2026-04-22]]
