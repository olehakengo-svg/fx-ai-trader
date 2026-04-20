# PAIR_PROMOTED 白紙状態の分析と候補抽出 (2026-04-20)

**Priority**: 2
**Branch**: `task/priority2-pair-promoted-review`
**作成**: 2026-04-20
**担当**: Claude (quant analyst-implementer)
**前提**: v9.1 で demo_trader.py の `_PAIR_PROMOTED` が大幅整理された後、demo_db.py
L341-347 の `_pair_promoted_overrides` (5 組合せ) のみが独立して残存している状態を監査。

---

## 1. 背景

v9.1 で下記の整理が行われた（`modules/demo_trader.py`):

- `orb_trap`: 365d BT 全ペア負EV → FORCE_DEMOTED + PAIR_PROMOTED 削除
- `fib_reversal × EUR`, `sr_channel_reversal × EUR`, `bb_squeeze_breakout × *`,
  `ema_pullback × JPY`, `engulfing_bb × EUR`, `stoch_trend_pullback × GBP_JPY`,
  `macdh_reversal × *_JPY` などを FORCE_DEMOTED 死コードとして `_PAIR_PROMOTED`
  から削除
- `session_time_bias`, `trendline_sweep`: ELITE_LIVE 昇格に伴い PAIR_PROMOTED 冗長行削除

結果として現行 `_PAIR_PROMOTED` (demo_trader.py L5046-5102) は 15 行で正常化されている。

**問題:** `modules/demo_db.py` L341-347 の `_pair_promoted_overrides` にはまだ
v9.1 で削除された 5 組合せが残存しており、Shadow migration ロジックが
古い想定で動作している:

```python
_pair_promoted_overrides = {
    ("ema_pullback", "USD_JPY"),
    ("fib_reversal", "EUR_USD"),
    ("bb_squeeze_breakout", "USD_JPY"),
    ("bb_squeeze_breakout", "EUR_USD"),
    ("sr_channel_reversal", "EUR_USD"),
}
```

demo_trader.py の `_PAIR_PROMOTED` にはもはやこれらが存在しないため、この
override は「shadow migration で is_shadow=0 のまま残す特例」としてのみ
作用する — 現行トレード判断に対する直接の影響はない。ただし**ソース・オブ・
トゥルースの二重化**により将来のドリフトの温床となり、`tier-master.md`
生成ツールの参照経路を混乱させる。

---

## 2. 現行 5 組の Live 実績（本番データ）

**データ源:** `https://fx-ai-trader.onrender.com/api/demo/trades?limit=5000`
（2046 trades, fetched 2026-04-20 17:27 UTC）

### 2.1 カットオフ別サマリ

#### Cutoff = 2026-04-07 (pre v5.95 cut)

| Strategy × Pair | N | (shadow / live) | WR | PnL (pip) | EV/trade | PF | Verdict |
|---|---|---|---|---|---|---|---|
| ema_pullback × USD_JPY | 18 | (3 / 15) | 38.9% | +17.1 | +0.950 | 1.47 | **marginal +EV** |
| fib_reversal × EUR_USD | 51 | (22 / 29) | 39.2% | -15.2 | -0.298 | 0.83 | **負EV** |
| bb_squeeze_breakout × USD_JPY | 52 | (42 / 10) | 26.9% | +21.1 | +0.406 | 1.18 | shadow 主体 |
| bb_squeeze_breakout × EUR_USD | 26 | (22 / 4) | 11.5% | -60.4 | -2.323 | 0.17 | **壊滅的** |
| sr_channel_reversal × EUR_USD | 26 | (18 / 8) | 19.2% | -31.1 | -1.196 | 0.50 | **壊滅的** |

#### Cutoff = 2026-04-14 (v8.9 cut)

| Strategy × Pair | N | (shadow / live) | WR | PnL (pip) | EV/trade | PF | Verdict |
|---|---|---|---|---|---|---|---|
| ema_pullback × USD_JPY | 4 | (3 / 1) | 25.0% | +1.8 | +0.450 | 1.23 | N<10 判断不能 |
| fib_reversal × EUR_USD | 21 | (21 / 0) | 23.8% | -25.3 | -1.205 | 0.47 | **負EV** |
| bb_squeeze_breakout × USD_JPY | 46 | (40 / 6) | 28.3% | +35.4 | +0.770 | 1.35 | shadow 主体 |
| bb_squeeze_breakout × EUR_USD | 22 | (22 / 0) | 0.0% | -69.7 | -3.168 | 0.00 | **壊滅的** |
| sr_channel_reversal × EUR_USD | 15 | (14 / 1) | 20.0% | -17.5 | -1.167 | 0.55 | **壊滅的** |

#### Cutoff = 2026-04-17 (v9.1 cut — すべて FORCE_DEMOTED 反映後)

| Strategy × Pair | N | (shadow / live) | WR | PnL (pip) | EV/trade | PF | Verdict |
|---|---|---|---|---|---|---|---|
| ema_pullback × USD_JPY | 0 | — | — | — | — | — | データなし |
| fib_reversal × EUR_USD | 8 | (8 / 0) | 25.0% | -13.1 | -1.638 | 0.43 | **負EV** |
| bb_squeeze_breakout × USD_JPY | 21 | (21 / 0) | 42.9% | +84.7 | +4.033 | 3.38 | Shadow で好調 |
| bb_squeeze_breakout × EUR_USD | 8 | (8 / 0) | 0.0% | -27.9 | -3.487 | 0.00 | **壊滅的** |
| sr_channel_reversal × EUR_USD | 1 | (1 / 0) | 100% | +8.2 | +8.200 | ∞ | N<10 判断不能 |

### 2.2 観察

1. **全 5 組合せで非 shadow (実弾候補) Live N ≪ 10** — そもそも実弾経路に乗った
   件数が極めて少なく、昇格判断の Live N 条件を全く満たしていない
2. `bb_squeeze_breakout × USD_JPY` の v9.1 後 Shadow パフォーマンス (+84.7pip,
   PF=3.38) は興味深いが、**Live N=0** のため lesson-orb-trap-bt-divergence
   の再現（短期 WR 高騰 → 365d BT で崩壊）を警戒すべき局面
3. `fib_reversal × EUR_USD`, `bb_squeeze_breakout × EUR_USD`,
   `sr_channel_reversal × EUR_USD` は **どの cutoff でも明確な負EV** —
   再復活の根拠なし

---

## 3. 365d BT EV+ (戦略 × ペア) 抽出

**データ源:**

- `raw/bt-results/bt-365d-scan-2026-04-16.md` — DT 15m 365d 全戦略
- `raw/bt-results/full-bt-scan-2026-04-15.md` — DT 15m 365d + Scalp 1m/5m 180d
- `raw/bt-results/bt-365d-2026-04-16.json` — GBP_USD 詳細 breakdown
- `raw/bt-results/bt-target-2026-04-17.json` — FORCE_DEMOTED 戦略の 365d 検証

### 3.1 FORCE_DEMOTED 戦略 × ペアの 365d BT 発火状況

| Strategy (FORCE_DEMOTED) | TF | 365d DT BT EV+ ペア | 短期 BT EV+ ペア (180d 以下) | 365d N≥100 |
|---|---|---|---|---|
| `atr_regime_break` | DT | なし (全ペア N≈0) | なし | なし |
| `bb_squeeze_breakout` | Scalp/DT | — | USD_JPY 5m (N=18 EV=+0.457), EUR_JPY 5m (N=19 EV=+0.422), GBP_JPY 1m (N=67 EV=+0.340), EUR_USD 1m (N=46 EV=+0.274) | なし |
| `dt_bb_rsi_mr` | DT | なし (全ペア負EV) | — | GBP: N=117 EV=-0.182 |
| `ema_cross` | DT | EUR_JPY N=32 EV=+0.337, EUR_USD +0.021 | — | なし |
| `ema_pullback` | DT | (BT 発火なし) | — | なし |
| `ema_ribbon_ride` | DT/Scalp | — | — | なし |
| `ema_trend_scalp` | Scalp | GBP_JPY 5m (N=226 EV=+0.091, 弱) / 1m (N=1185 EV=+0.042, 弱) | — | N≥100あるが EV<+0.2 |
| `engulfing_bb` | Scalp | USD_JPY 5m (N=36 EV=+0.213) | — | なし |
| `fib_reversal` | Scalp/DT | — | EUR_USD 1m: 60d EV=+0.271 → **180d EV=-0.147** | **60d→180dで符号反転** |
| `inducement_ob` | DT | GBP_USD (N=2, EV=+1.022 で N=2 のため無視) | — | なし |
| `intraday_seasonality` | DT | なし (全ペア負EV or 弱正) | — | なし |
| `lin_reg_channel` | DT | (データなし) | — | なし |
| `macdh_reversal` | DT | (GBP_USD EV=-0.818) | — | なし |
| `orb_trap` | DT | GBP: N=25 EV=-0.258 (全ペア負EV, v9.1 で削除済み) | — | なし |
| `sr_break_retest` | DT | GBP: N=47 EV=-0.067 | — | なし |
| `sr_channel_reversal` | Scalp/DT | — | GBP_JPY 5m (N=70 EV=+0.122) | なし |
| `sr_fib_confluence` | DT | GBP: N=241 EV=+0.015 (ほぼ 0) | — | GBP N=241 だが EV<+0.2 |
| `stoch_trend_pullback` | Scalp | GBP_JPY 5m (N=90 EV=+0.240) | — | なし |

### 3.2 重要な所見

- **365d DT 15m BT で N≥100 かつ EV≥+0.2 の FORCE_DEMOTED × ペアは存在しない**
- 180d Scalp BT で正EV を示す候補 (bb_squeeze_breakout, sr_channel_reversal,
  stoch_trend_pullback, engulfing_bb) は**全て N<100**
- `fib_reversal × EUR_USD` は**60d→180d で EV 符号反転**した典型例
  (lesson-orb-trap-bt-divergence 再現)
- `ema_trend_scalp × GBP_JPY` は Scalp で N≥100 を満たすが EV=+0.04〜+0.09 と弱い

---

## 4. 復活候補 Gate チェック

### Gate 定義

1. **365d BT EV ≥ +0.2 ATR** (同一 TF, friction-adjusted)
2. **365d BT N ≥ 100**
3. **SENTINEL 非重複** (UNIVERSAL_SENTINEL / SCALP_SENTINEL)
4. **60d BT と 365d BT の EV 符号一致** (lesson-orb-trap-bt-divergence)
5. **Live N ≥ 10**（新設ルール、safety net）

### 4.1 現行 5 組合せの Gate 評価

| Combo | Gate1 EV≥+0.2 | Gate2 N≥100 | Gate3 no SENTINEL | Gate4 sign OK | Gate5 Live N≥10 | 結果 |
|---|---|---|---|---|---|---|
| ema_pullback × USD_JPY | ❌ (BT 発火なし) | ❌ | ✅ | — | △ live=1 | **FAIL** |
| fib_reversal × EUR_USD | ❌ (180d=-0.147) | ❌ | ✅ | ❌ **符号反転** | △ live=0 | **FAIL** |
| bb_squeeze_breakout × USD_JPY | △ (5m +0.457 / 短期) | ❌ (N=18) | ✅ | — | ❌ live=0 | **FAIL** |
| bb_squeeze_breakout × EUR_USD | △ (1m +0.274 / 短期) | ❌ (N=46) | ✅ | — | ❌ live=0 | **FAIL** |
| sr_channel_reversal × EUR_USD | ❌ (EUR_USD BT 発火なし) | ❌ | ✅ | — | ❌ live=0 | **FAIL** |

**結論: 現行 5 組合せのいずれも復活 Gate を通過しない。**

### 4.2 FORCE_DEMOTED 全体の探索結果

365d DT 15m BT で Gate1+Gate2 を同時に満たす FORCE_DEMOTED × ペアは
**存在しない**。短期 (180d Scalp) BT で EV+ を示す候補は、Gate4 (符号一致)
を検証した `fib_reversal × EUR_USD` が**既に符号反転した実例**であり、
ほかの短期 EV+ 候補も同じリスクを抱えるため、**独立した 365d Scalp BT で
EV≥+0.2 かつ N≥100 を再確認するまで PAIR_PROMOTED 追加はしない**。

---

## 5. 判定

### 5.1 新規 PAIR_PROMOTED 追加候補

**なし**。365d BT + Gate を通過する FORCE_DEMOTED × ペアの組み合わせは
現時点のデータでは抽出できなかった。

### 5.2 現行 demo_db.py 5 overrides の扱い

**削除 (クリーンアップ)** を推奨:

- 5 組合せ全てが `demo_trader.py _PAIR_PROMOTED` から既に削除されており、
  Live 挙動上の意味は「shadow migration での is_shadow=0 保持のみ」に縮退
- 該当 entry_type は全て `_FORCE_DEMOTED` に含まれているため、現行コード
  では override を残しても新規 trade の is_shadow=0 通過には寄与せず
  （新規 trade は発火時点で shadow=True になる: xs_momentum 等が
  lesson-sentinel-promoted-conflict の通り）
- 残しておくと tier-master の Source of Truth である demo_trader.py と
  demo_db.py が乖離し、将来のドリフトの温床となる
- 削除後は shadow migration が 5 combos を含む全 FORCE_DEMOTED trade を
  is_shadow=1 に揃える — **これは本来の意図と一致** (v9.1 で PAIR_PROMOTED
  から削除した戦略は shadow 扱いで統一する方針)

### 5.3 マイグレーション影響評価

`demo_db.py` の override を削除すると、起動時の shadow migration で
「過去に is_shadow=0 で記録された 5 combos のトレード」も is_shadow=1 に
上書きされる。本番 DB の影響:

- ema_pullback × USD_JPY: 15 件 (live) → is_shadow=1 化
- fib_reversal × EUR_USD: 29 件 → is_shadow=1 化
- bb_squeeze_breakout × USD_JPY: 10 件 → is_shadow=1 化
- bb_squeeze_breakout × EUR_USD: 4 件 → is_shadow=1 化
- sr_channel_reversal × EUR_USD: 8 件 → is_shadow=1 化

合計 **~66 trades** が遡及的に shadow 扱いになる。これは:

- `/api/demo/stats` の live PnL 集計から除外される
- Shadow ledger 側では保存継続
- 月利計算への影響: 上表の通り全体 PnL は -98.0pip （負 EV セル主体）なので、
  shadow 化で live PnL はむしろ**改善する**方向 (フィクションの損失除去)

**よってこの遡及 shadow 化は是正的変更** (accounting clean-up) であり、
quant 判断として GO。

---

## 6. 実装

### 6.1 demo_db.py クリーンアップ

`_pair_promoted_overrides` を空セットに変更し、コメントで根拠を明記。
互換性のため変数名は残す (将来 PAIR_PROMOTED 復活候補が出た際に再利用可能)。

### 6.2 新規 PAIR_PROMOTED 追加

**なし**。全候補が Gate 不通過。

### 6.3 KB 更新

- 本分析ページ (本ドキュメント) を analyses/ に配置
- `wiki/strategies/ema-pullback.md`, `fib-reversal.md`, `bb-squeeze-breakout.md`,
  `sr-channel-reversal.md` の「Current Configuration」節を現状 (PAIR_PROMOTED
  なし) に揃える
- `wiki/changelog.md` に v9.x エントリ追加

---

## 7. Gate 未通過候補 (保留) の KB 記録

将来 365d Scalp BT 実装時に再検証すべき候補:

| Strategy × Pair | BT (180d Scalp) | 365d Scalp 要件 | 備考 |
|---|---|---|---|
| bb_squeeze_breakout × USD_JPY (5m) | N=18 EV=+0.457 | N≥100 要 | 5m 365d BT 未実装 |
| bb_squeeze_breakout × GBP_JPY (1m) | N=67 EV=+0.340 | N≥100 要 | 1m 365d BT 未実装 |
| bb_squeeze_breakout × EUR_JPY (5m) | N=19 EV=+0.422 | N≥100 要 | 5m 365d BT 未実装 |
| stoch_trend_pullback × GBP_JPY (5m) | N=90 EV=+0.240 | N≥100 要 | Live 壊滅 (全ペア-EV) と整合性要確認 |
| engulfing_bb × USD_JPY (5m) | N=36 EV=+0.213 | N≥100 要 | Live 壊滅 (N=14 Kelly=-14.7%) |
| sr_channel_reversal × GBP_JPY (5m) | N=70 EV=+0.122 | EV<+0.2 で Gate1 不通過 |

**いずれも短期 BT を 60d→180d→365d に延伸した際に EV 符号が維持されるか
確認するまで実装保留**。直近のセッションで `fib_reversal × EUR_USD` が
60d→180d で符号反転した事例は、これらの候補にも同様のリスクがあることを
示唆している。

---

## 8. 成功基準チェック

- [x] 分析レポート存在 + 現行 5 組の数字化
- [x] 復活候補 Gate 付き一覧化
- [x] 実装候補は 365d BT + Gate 通過根拠明示 (=該当なし)
- [ ] tier_integrity_check.py --check ERROR=0 (実装フェーズで確認)

---

## Related

- [[tier-master]] — 現行 Tier 分類
- [[lesson-orb-trap-bt-divergence]] — 短期 BT 過学習パターン
- [[lesson-sentinel-promoted-conflict]] — SENTINEL 重複禁止
- [[lesson-reactive-changes]] — 1日データ反射変更禁止
- [[bt-365d-scan-2026-04-16]] — 365d DT 15m スキャン
- [[full-bt-scan-2026-04-15]] — DT + Scalp 統合スキャン
- [[bt-revival-analysis-2026-04-15]] — 過去 5 戦略復活評価
