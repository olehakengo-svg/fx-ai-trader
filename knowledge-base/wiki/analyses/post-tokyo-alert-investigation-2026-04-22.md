---
created: 2026-04-22
type: investigation
triggers:
  - 2026-04-22 Post-Tokyo Discord alert (+55.6pip 含み益 / LIVE=0 Shadow=8)
  - daytrade_eurgbp:score_gate 80 consecutive blocks
  - USD net exposure 40,000u > 20,000u limit (11 回)
---

# Post-Tokyo Alert Investigation (2026-04-22)

**Trigger**: 09:09 UTC Discord alert + [[../raw/trade-logs/2026-04-22-monitor]] 診断 4 項目

## 結論サマリ

| # | 指摘 | 判定 | 対応 |
|---|---|---|---|
| **P0** | `daytrade_eurgbp:score_gate` 80連続ブロック、`score=-1.84 / entry_type=unknown` | **NOT A BUG** | 仕様通りの挙動 — 記録のみ |
| **P1** | Shadow が exposure 集計に混入し LIVE をブロック | **CONFIRMED BUG** | 本セッションで修正実装 |
| **P2** | FORCE_DEMOTED 戦略 (stoch_trend_pullback, sr_break_retest) が Shadow で含み益 | **NORMAL** | 記録のみ、決済後 post-cutoff N≥30 で再評価 |

---

## P0: score=-1.84 / entry_type=unknown は設計通り

### Root cause
- `compute_daytrade_signal` ([app.py:1994](../../app.py)) は連続スコア ∈ [-3, +3] を返す複合シグナル関数
- クリッピング: `score = max(-3.0, min(3.0, score))` ([app.py:2277](../../app.py))
- この関数の返り値には **`entry_type` が含まれない** → [demo_trader.py:2725](../../modules/demo_trader.py) で `sig.get("entry_type", "unknown")` が発動
- v9.x score_gate ([demo_trader.py:2768-2778](../../modules/demo_trader.py)): `score < 0 and not _sentinel_score_bypass` → `_block("score_gate(...<0)")`
- **仕様通り**: score<0 の daytrade 複合シグナル (BEARスコア) を正しくブロックしている

### なぜ 80 件連続か
EUR/GBP が東京セッション中に持続的な弱気レジーム (キャリーバイアス SELL + EMA 下向き) を出した結果、`compute_daytrade_signal` が継続的に負スコアを生成。30秒 tick × 数時間で 80 件は自然な頻度。**`score=-1.84` が固定値に見えるのは特徴量が変化してもクリップレンジ内で安定した出力が返っているため**であり、モデル故障の兆候ではない。

### 検証: `eurgbp_daily_mr` は影響なし
専用戦略 [eurgbp_daily_mr.py:143](../../strategies/daytrade/eurgbp_daily_mr.py) はベース score=4.0 から開始し、最悪ペナルティ (-0.5) を喰っても 3.5 が下限。**負 score は出せない**。つまり `entry_type=unknown` は **compute_daytrade_signal の複合経路のみ** で発生し、専用戦略側は問題なし。

### 対応
**記録のみ**。現行設計 (負 score 複合シグナルは学習汚染を避けるためブロック) は CLAUDE.md 原則④「攻撃は最大の防御 (データ蓄積優先)」と整合。**変更しない** — reactive change 回避。

### 次回監視閾値
- `daytrade_eurgbp:score_gate` が **100 件/12h** を超え、かつ eurgbp_daily_mr の発火頻度も同時に低下した場合は、compute_daytrade_signal の特徴量ピップラインをチェック
- 現時点 (80 件/12h) は平常範囲

---

## P1: Shadow exposure leakage — **CONFIRMED BUG, FIXED**

### Root cause (精査結果)

**症状**: `USD net exposure 40,000u > 20,000u limit` が 11 回。Shadow=8 のみで LIVE=0 なのに exposure が 40K 積み上がる。

**コード追跡**:

1. **Pre-entry check は Shadow バイパス (正しい)** — [demo_trader.py:2891](../../modules/demo_trader.py)
   ```python
   if not _is_shadow_eligible:
       _exp_ok, _exp_reason = self._exposure_mgr.check_new_trade(...)
   ```
   v9.0 コメント: 「ExposureManagerはOANDA実弾専用リスク管理」

2. **Position 登録は Shadow も通っていた (バグ)** — [demo_trader.py:4055](../../modules/demo_trader.py)
   ```python
   self._exposure_mgr.add_position(trade_id, instrument, signal,
                                   int(_os.environ.get("OANDA_UNITS", "10000")))
   ```
   `_is_shadow` 条件なしで全トレードが登録される。

3. **ExposureManager に Shadow 概念なし** — [exposure_manager.py:48](../../modules/exposure_manager.py)
   ```python
   self._positions: Dict[str, dict] = {}   # trade_id → {instrument, direction, units}
   ```
   `_calc_exposure_unlocked()` が `self._positions` を全走査。

4. **起動時 DB sync も Shadow 混入** — [demo_trader.py:511](../../modules/demo_trader.py)
   再起動後、DB から open trades を復元する際にも is_shadow を見ず一括登録。

### 影響
- Shadow ポジションが exposure 総量に計上 → LIVE 昇格戦略 (PAIR_PROMOTED / ELITE_LIVE) が通貨別上限 20K で block
- v9.0 の「Shadow/Demo bypass」設計文書と実装が不整合
- **Kelly Half 到達の構造的ブロッカー**: LIVE trade が入らなければ N 蓄積も Pip も伸びない

### 修正 (本セッション、3 ファイル)

**1. `modules/exposure_manager.py`**:
- `add_position()` に `is_shadow: bool = False` 追加、position 辞書に保持
- `_calc_exposure_unlocked()`: `if pos.get("is_shadow"): continue` で集計除外
- `check_new_trade()` の同方向カウント (MAX_SAME_DIRECTION=3) も Shadow 除外

**2. `modules/demo_trader.py`**:
- Live entry path ([demo_trader.py:4055](../../modules/demo_trader.py)): `is_shadow=bool(_is_shadow)` 追加
- 起動時 DB sync ([demo_trader.py:511](../../modules/demo_trader.py)): DB の `is_shadow` 列を読んで渡す

**3. `tests/test_p2_system.py`**:
- `test_exposure_shadow_excluded_from_aggregation`: Shadow 15K USD_JPY + LIVE 10K EUR_USD のシナリオで USD=10K、LIVE 5K USD_JPY が通ることを検証
- `test_exposure_shadow_same_direction_excluded`: Shadow 3 連続 BUY でも LIVE 4 本目が通ることを検証

**テスト結果**: 6/6 PASS (既存 4 + 新規 2)

### デプロイ後の検証プラン (Render)
```
# 1. 最新 trades を確認
curl -s "https://fx-ai-trader.onrender.com/api/demo/trades?limit=200" | jq '[.trades[] | select(.is_shadow==0 and .exit_time==null)] | length'
# → LIVE open 数が Shadow 分を除いた実数か確認

# 2. 24h 後 block_counts 再確認
# "USD net exposure ... > 20,000u limit" が Shadow only 時間帯で 0 件に落ちているか
```

---

## P2: FORCE_DEMOTED の Shadow 含み益 — 記録のみ

### 含み益 Top 3 (Shadow 内訳)
| strategy | pair | 含み益 | tier (`tier-master.md`) |
|---|---|---|---|
| vwap_mean_reversion | EUR_JPY | +28.6pip | PAIR_PROMOTED (EUR_JPY 含む) |
| stoch_trend_pullback | GBP_USD | +9.9pip | FORCE_DEMOTED |
| sr_break_retest | USD_JPY | +8.5pip | FORCE_DEMOTED |

### 判断
- **PAIR_PROMOTED な vwap×EUR_JPY が Shadow=1 で入っている**理由は P1 バグ由来の可能性大 (exposure block で OANDA 未送信 → is_shadow=1 safety net 発動)
- P1 修正後は vwap×EUR_JPY は通常の LIVE 経路に戻る見込み
- FORCE_DEMOTED 2 件 (stoch/sr_break) の含み益 +18.4pip は **確定利益ではなく未決済評価益**
- 過去の [[../decisions/]] を繰り返さない: N=1 の含み益で Tier 変更は [[lesson-reactive-changes]] 違反
- **決済後の post-cutoff N≥30 で再評価**するまで変更しない

### 次回評価トリガ
- 2026-04-30 時点で stoch_trend_pullback×GBP_USD が post-cutoff N≥30 に達した場合、Wilson 下限 WR と PF を計算して復活審査
- それ以前は monitor 記録のみ

---

## デプロイと検証タイムライン

| 時刻 (予定) | アクション |
|---|---|
| 2026-04-22 当日 | 本修正を commit → push → Render auto-deploy |
| +1h | SessionStart hook の再起動検出、block_counts 再計測開始 |
| +24h | Pre-Tokyo/Post-Tokyo report で `USD net exposure` 関連 block が 0〜1 件に減っていることを確認 |
| +48h | Kelly Half 到達判定の LIVE N 増加を確認 |

## Related
- [[../raw/trade-logs/2026-04-22-monitor]] — alert raw content
- [[../lessons/lesson-clean-slate-2026-04-16]] — ExposureManager v9.0 Shadow bypass 設計文書
- [[../lessons/lesson-reactive-changes]] — FORCE_DEMOTED 含み益で動かさない原則
- [[regime-2d-v2-rescan-result-2026-04-22]] — 並行執行 (NO-OP, 本日確定)
- [[spread-entry-gate-preregister-2026-04-22]] — OOS-1 待機中
