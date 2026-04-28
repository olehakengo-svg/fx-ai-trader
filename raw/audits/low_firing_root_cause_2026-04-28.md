# LIVE/Shadow発火低調Edge 根本原因調査レポート (本番データ版)

- **作成日**: 2026-04-28
- **データソース**: 本番 `https://fx-ai-trader.onrender.com/api/demo/trades?limit=2000` + `/api/demo/status` (Render復旧後再取得)
- **本番データ範囲**: 2026-04-16T13:22Z 〜 2026-04-28T06:34Z (約12日分、2,004件、limit=2000で打切り)
- **集計窓**: 過去7日 (`entry_time >= now - 7d`)
- **発火低調定義**: 7日合算 N<3 または 全期間 NEVER_EVER
- **除外**: 2026-04-27 commit `fe5344d` 追加の `pullback_to_liquidity_v1`, `asia_range_fade_v1`

> **重要訂正**: 本レポート初版はローカル `demo_trades.db` で集計したため本番と全く異なる結果でした。CLAUDE.md「分析は本番データを使用」に従い本番APIで全面再集計しています。

---

## エグゼクティブサマリ

**前回ローカル版の主張は誤り**: PRIME gate (commit `6e8b30a` 2026-04-22) が「LIVEをほぼ停止」させたという結論はローカルDB特有の現象で、**本番では成立しません**。

本番側では:
- LIVE発火は継続: 04-22 (PRIME導入日) は 4件、04-27 は **16件**、04-28 は **9件**(午後段階)
- `bb_rsi_reversion USD/JPY` が PRIME gate 経由で 7日間 LIVE=26件 (130件中)
- `vwap_mean_reversion` が 7日 LIVE=8件
- ELITE_LIVE戦略も発火実績あり: `trendline_sweep` LIVE=3, `gbp_deep_pullback` LIVE=1

**実際の発火低調Edgeの真因は L1 Signal生成段の条件厳格性** + **新規戦略の蓄積時間不足** + **session_time_bias の真の停止異常**。

---

## 1. 本番 日次LIVE/Shadow分布

| 日 | LIVE | Shadow | Total | 備考 |
|----|------|--------|-------|------|
| 2026-04-28 | 9 | 40 | 49 | 06:34Zまで |
| 2026-04-27 | 16 | 198 | 214 | 過去最多LIVE |
| 2026-04-24 | 2 | 211 | 213 | |
| 2026-04-23 | 8 | 292 | 300 | |
| **2026-04-22** | **4** | **265** | **269** | **PRIME gate導入日** |
| 2026-04-21 | 2 | 261 | 263 | |
| 2026-04-20 | 3 | 324 | 327 | |
| 2026-04-17 | 0 | 315 | 315 | |
| 2026-04-16 | 0 | 54 | 54 | データ取得最古 |

→ **PRIME gate前後でLIVE発火に有意な減少なし**。むしろ04-27に最多。

---

## 2. 本番 7日間 戦略別発火実績

**全体**: 70戦略中 **42戦略が発火**、**32戦略が NEVER_LOGGED in 7d** (内 NEVER_EVER 32戦略全て)

### 2.1 N<3 (発火低調) — 11戦略

| 戦略 | LIVE | Shadow | 7d Total | 全期間 first→last | category | tier |
|------|------|--------|----------|-------------------|----------|------|
| **lin_reg_channel** | 0 | 1 | 1 | 04-27 | daytrade | (registry) |
| **gbp_deep_pullback** | 1 | 0 | 1 | 04-23 | daytrade | **ELITE_LIVE** |
| **liquidity_sweep** | 0 | 1 | 1 | 04-22 | daytrade | UNIVERSAL_SENTINEL |
| **eurgbp_daily_mr** | 0 | 1 | 1 | 04-21 | daytrade | UNIVERSAL_SENTINEL |
| confluence_scalp | 0 | 1 | 1 | 04-24 | scalp | (registry外?) |
| mtf_reversal_confluence | 0 | 1 | 1 | 04-23 | scalp | (registry外?) |
| ema_pullback | 0 | 1 | 1 | 04-22 | scalp | (registry外) |
| ny_close_reversal | 0 | 1 | 1 | 04-21 | (legacy) | (registry外) |
| streak_reversal | 0 | 2 | 2 | 04-27 | (legacy) | PAIR_PROMOTED USD/JPY |
| ema_cross | 0 | 2 | 2 | 04-27 | daytrade | FORCE_DEMOTED |
| doji_breakout | 1 | 1 | 2 | 04-22 | daytrade | UNIVERSAL_SENTINEL+PAIR_PROMOTED |

### 2.2 NEVER_LOGGED in 7d — 32戦略

#### A. 設計通り静止 (2)
| 戦略 | 理由 |
|------|------|
| hmm_regime_filter | overlay only — by design `signal生成しない` |
| london_close_reversal | コードで `DISABLED` (commentで明示) |

#### B. 本日 (2026-04-28) 追加戦略 — 時間不足 (8)
| 戦略 | 追加コミット | サンプル時間 |
|------|-------------|--------------|
| cpd_divergence | afe41b9 04-28 11:08 | <20h |
| vdr_jpy | 2010ce1 04-28 10:47 | <20h |
| vsg_jpy_reversal | fc1f16d 04-28 10:48 | <20h |
| rsk_gbpjpy_reversion | c23aaf9 04-28 10:50 | <20h |
| mqe_gbpusd_fix | c23aaf9 04-28 10:50 | <20h |
| pd_eurjpy_h20_bbpb3_sell | 9a0c868 04-28 (本日) | <12h |
| sr_anti_hunt_bounce | 4bc55bd 04-28 10:35 | <20h |
| sr_liquidity_grab | 4bc55bd 04-28 10:35 | <20h |

#### C. 既存だがNEVER_EVER (本番DB全期間で1件もない) — 14戦略 ⚠
| 戦略 | category | 主因仮説 |
|------|----------|---------|
| **session_time_bias** ⚠⚠ | daytrade | **ELITE_LIVE** なのに本番全期間 0件 — 真の異常 |
| adx_trend_continuation | daytrade | ADX trend (条件厳格) |
| atr_regime_break | daytrade | ATR regime breakout (稀) |
| gold_trend_momentum | daytrade | XAU専用 — instrumentが対象外 |
| gold_vol_break | daytrade | XAU専用 — 同上 |
| gotobi_fix | daytrade | USD/JPY 09:55 JST 仲値特化 |
| htf_false_breakout | daytrade | EUR/USD False breakout — 事象稀 |
| jpy_basket_trend | daytrade | JPY basket signal — 稀 |
| london_close_reversal_v2 | daytrade | UTC 20:30-21:00 + RSI極値 |
| london_ny_swing | daytrade | EUR/GBP 前日HL break |
| london_session_breakout | daytrade | EUR/USD London open特化 |
| tokyo_nakane_momentum | daytrade | USD/JPY 09:55 JST 特化 |
| tokyo_range_breakout_up | daytrade | USD/JPY × BUY only (Minimum Live) |
| turtle_soup | daytrade | Liquidity grab reversal — 稀 |

#### D. scalp/1h engine NEVER_EVER — 8戦略
| 戦略 | category |
|------|----------|
| ema_ribbon_ride | scalp |
| gold_pips_hunter | scalp |
| london_breakout | scalp |
| london_shrapnel | scalp |
| session_vol_expansion | scalp |
| three_bar_reversal | scalp |
| donchian_momentum_breakout | 1h |
| keltner_squeeze_breakout | 1h |

---

## 3. 本番でLIVE発火している戦略 (PRIME gate 通過実績)

| 戦略 | 7d LIVE | 全期間LIVE | 通過機構 |
|------|---------|------------|---------|
| bb_rsi_reversion | 26 | 26 | PRIME `bb_rsi_reversion_NY_ATRQ2` |
| vwap_mean_reversion | 8 | 10 | PAIR_PROMOTED (5ペア) |
| trendline_sweep | 3 | 3 | ELITE_LIVE (全期間 LIVE only) |
| gbp_deep_pullback | 1 | 1 | ELITE_LIVE |
| doji_breakout | 1 | 1 | PAIR_PROMOTED USD/JPY/GBP_USD |
| fib_reversal | 1 | 1 | PRIME `fib_reversal_PRIME` |
| post_news_vol | 1 | 1 | PAIR_PROMOTED EUR_USD/GBP_USD |
| vix_carry_unwind | 1 | 1 | PAIR_PROMOTED USD/JPY |

→ **PRIME gate は意図通り動作**。6 PRIME条件 + PAIR_PROMOTED が LIVE側に通過している。

---

## 4. 4層切り分け (本番データ版)

### L4 DB Persistence — 健全
- 7日 1,277トレード INSERT 成功、is_shadow flag 正常分離

### L2 Gating Filter — 設計通り作動
- PRIME gate (commit `6e8b30a`) は LIVE発火を抑制していない
- bb_rsi_reversion USD/JPY が NY ATRQ2 条件 (Tier A) で LIVE=26件
- `tier-master.json::pair_promoted` の 18 (戦略, ペア) も正常通過

### L3 Entry Condition — Shadow/LIVE双方で通過実績あり
- 戦略によっては Shadow 100件超 (ema_trend_scalp 425, sr_channel_reversal 126, engulfing_bb 85)
- TP/SL/Spread reject は別途 logs/ で集計可能だが、Shadow発火多数のため致命的問題ではない

### L1 Signal生成 — **本レポート最重要層**

#### 4.1 真の異常: `session_time_bias` (ELITE_LIVE で全期間 NEVER_EVER) ⚠⚠
- ELITE_LIVE は最重要昇格区分にも関わらず本番DB全期間で 0件
- 設定: `PAIR_SESSION_MAP` (3-4ペア × TOKYO/LONDON × bias_signal限定)
- ローカルでも全期間 N=3 (04-15最終) → 約2週間途絶
- **`PAIR_SESSION_MAP` の中身と現在のctxペアの整合性**を確認すべき (mismatch疑い)
- 別セッションで PAIR_SESSION_MAP, ctx.symbol正規化, hour_utc tracker のデバッグ要

#### 4.2 既存 NEVER_EVER 14戦略 — 条件厳格性
**XAU依存 (2)**: gold_trend_momentum, gold_vol_break — 本システムが XAU instrument を ctx に含めていない可能性 (要確認)

**特定時刻特化 (2)**: gotobi_fix (09:55 JST=00:55 UTC), tokyo_nakane_momentum (同) — 1日1分しかチャンスがない

**London特化 (3)**: london_close_reversal_v2 (20:30-21:00 UTC), london_ny_swing, london_session_breakout — Londonセッション + 厳しい補助条件

**条件AND過多 (4)**: adx_trend_continuation, atr_regime_break, htf_false_breakout, jpy_basket_trend, turtle_soup, tokyo_range_breakout_up — 多段ANDで実発火率 <0.01%/bar 試算

#### 4.3 N<3 戦略の真因
- `liquidity_sweep`, `lin_reg_channel`, `eurgbp_daily_mr`, `gbp_deep_pullback`: 単一ペア + 構造的稀イベント (BB%B 極値, 日足MR等)
- `doji_breakout`: USD/JPY と GBP_USD のみ PAIR_PROMOTED — 残りペアでは FORCE_DEMOTED 相当

---

## 5. 根本原因サマリ (本番版・訂正後)

| Cat | 件数 | 説明 | 優先度 |
|-----|------|------|--------|
| **Cat A: 設計通り静止** | 2 | hmm_regime_filter (overlay), london_close_reversal (DISABLED) | 不要 |
| **Cat B: 本日追加 (時間不足)** | 8 | 04-28 追加戦略、観察継続 | 1週間後再集計 |
| **Cat C: 過度に狭い条件 (XAU/特定時刻)** | 6 | gold_*, gotobi_fix, tokyo_nakane_momentum, tokyo_range_breakout_up, pd_eurjpy_h20_bbpb3_sell | BT条件緩和検証 |
| **Cat D: ELITE_LIVE 真の異常** ⚠⚠ | **1** | **session_time_bias** — 全期間 0件 | **最優先深掘り** |
| **Cat E: 既存ANDチェーン段過剰** | 8 | adx_trend_continuation, atr_regime_break, htf_false_breakout, london_*, jpy_basket_trend, turtle_soup | BT条件緩和 |
| **Cat F: 単一ペア×構造稀** | 4 | liquidity_sweep, lin_reg_channel, eurgbp_daily_mr, gbp_deep_pullback | 当面様子見、N≥30蓄積待ち |
| **Cat G: scalp/1h engine 未発火** | 8 | ema_ribbon_ride, gold_pips_hunter, london_breakout 等 | engine別監査 |

---

## 6. 提案アクション (修正は別セッション)

### 即対応 (Cat D — ELITE_LIVE異常) — **真因確定 (2026-04-28 P0調査)**

**結論**: `session_time_bias` は signal生成は **正常**。本番で1分間隔で SELL EUR_USD/GBP_USD のsignalを出している (本番logs `/api/demo/logs?limit=10000` の 30件中9件で `[SCORE_GATE] Blocked: session_time_bias score=-3.77 < 0`)。

**真因**: [modules/demo_trader.py:2862-2873](modules/demo_trader.py:2862) の SCORE_GATE バイパスに **ELITE_LIVE が含まれていない**:

```python
_sentinel_score_bypass = (
    entry_type in self._SCALP_SENTINEL
    or entry_type in self._UNIVERSAL_SENTINEL
)  # ← _ELITE_LIVE が無い
if _entry_score < 0 and not _sentinel_score_bypass:
    _block(f"score_gate({_entry_score:.2f}<0)")
```

戦略コードは `score = 5.5` (+ボーナス最大1.6) を返すが、engine層で `sig['score']` が負値 (-3.77等) に加工され、ELITE_LIVE であるにも関わらず一律blockされている。

**他のELITE_LIVE比較** (本番log 30件):
| 戦略 | log内mention | 本番LIVE発火 (7d) | 状況 |
|------|-------------|-------------------|------|
| session_time_bias | 9件 (全SCORE_GATE block) | 0 | **異常** |
| trendline_sweep | 0件 | 3 (04-23) | 正常通過 |
| gbp_deep_pullback | 0件 | 1 (04-23) | 正常通過 |

trendline_sweep / gbp_deep_pullback は最終 score が正値で SCORE_GATE 通過。session_time_bias のみ engine層加工で負値に変換される。

**修正候補 (別セッション、設計判断要)**:
- **A**: `_sentinel_score_bypass` に `entry_type in self._ELITE_LIVE` を追加 → 最小差分、安全
- **B**: `sig['score']` を session_time_bias で負にする加工層を特定して根本修正 → 加工の正当性次第
- **C**: 戦略コード L158 の base score を 5.5 → 9.0+ に再上方修正 → curve fitting risk

**A推奨**: ELITE_LIVE は 365日BT STRONG確認済の昇格区分。score_gate バイパスは Sentinel と同等の信頼担保で正当化可能 ([modules/demo_trader.py:6034](modules/demo_trader.py:6034) コメント `Elite strategies — NEVER shadowed`)。

---

### Q1+Q2 完了 → 修正実装 (2026-04-28 P0結論)

**Q1 score=-3.77 加工層完全特定**:

[app.py:2544](app.py:2544) (compute_daytrade_signal):
```python
_dte_score = _dt_best.score * 0.5 if _dt_best.signal == "BUY" else -(_dt_best.score * 0.5)
```

[app.py:2552-2554](app.py:2552):
```python
if _dt_best.signal == "BUY":  score += _dt_best.score * 0.5
else:                          score -= _dt_best.score * 0.5  # 符号反転
```

→ daytrade pipeline で `sig["score"]` 符号 = 方向情報 (BUY=正, SELL=負)。session_time_bias の戦略score=5.5+ボーナス → SELL signalで `sig["score"]` ≈ -2.75〜-3.55 に変換され、SCORE_GATE で全block。

**本番LIVE direction内訳 (12日 44件)**:
- BUY=30, SELL=14
- SELL 14件は全て scalp pipeline (compute_signal経由) または UNIVERSAL_SENTINEL
- **daytrade pipeline + ELITE_LIVE + SELL = 0件** = ELITE_LIVE 3戦略全てで SELL 構造的block

**Q2 設計矛盾の性質**: Q2(c) **legacy semantics conflict** (バグでもlegacyでもなく、二つのレイヤーの設計合意失敗)
- app.py: score符号 = 方向二値表現 (旧設計)
- demo_trader.py SCORE_GATE: score<0 = 戦略「入るな」(後付け、score=方向中立を前提)
- 両者の前提が衝突 → ELITE_LIVE SELL が構造的にblock

### 実装した修正 (Q3: 案C採用)

**[modules/demo_trader.py:2862-2890](modules/demo_trader.py:2862)** を direction-aware misalignment 判定に変更:

```python
_score_misaligned = (
    (signal == "BUY" and _entry_score < 0)
    or (signal == "SELL" and _entry_score > 0)
)
if _score_misaligned and not _sentinel_score_bypass:
    _block(f"score_gate(misalign:{signal},{_entry_score:.2f})")
    return
```

**Pre-reg LOCK (rule:R1, 2026-05-12 まで)**: [knowledge-base/wiki/decisions/score-gate-direction-aware-2026-04-28.md](knowledge-base/wiki/decisions/score-gate-direction-aware-2026-04-28.md)

**Primary KPI**: ELITE_LIVE 3戦略 × {BUY, SELL} = 6 strata で N≥15, WR≥40% (Wilson下限>30%), PF≥0.8, EV≥-0.5p, 連敗<6, Bonferroni補正済

**即停止条件 (rule:R2)**: 
1. ELITE_LIVE×SELL N≥10で WR<30%
2. 全体 N≥15で PF<0.6
3. 同一戦略×ペアで6連敗
4. Live累計損失>-¥10,000

**期待効果**:
- session_time_bias × {EUR_USD, GBP_USD} × SELL Live発火復旧 (1分間隔のsignal出力実績あり)
- trendline_sweep × {EURUSD, EURGBP, XAUUSD} (SELL_ONLY_PAIRS) Live発火復旧
- gbp_deep_pullback × GBP_USD × SELL Live発火復旧

**監視**: 本番デプロイ後 24時間で `[SCORE_GATE] Blocked: misalign` ログ確認、3戦略の direction別 LIVE 件数推移、Sentry warning化推奨。

### 中期 (Cat C, E)
**BT による条件緩和検証** (Wilson CI + Bonferroni 前提):
- adx_trend_continuation, htf_false_breakout, jpy_basket_trend, turtle_soup → AND段ごとの通過率測定
- gold_*, tokyo_*, gotobi_fix → instrument/時刻条件の合理性検証

### 待機
- **Cat B**: 2026-05-05 (1週間後) に再集計
- **Cat F**: N≥30 まで蓄積待ち、Wilson CI 確定まで判断保留
- **Cat G**: scalp/1h engine 監査は別セッションでまとめて実施

---

## 7. 検証ログ (本番)

```bash
# 本番ステータス取得
curl -s "https://fx-ai-trader.onrender.com/api/demo/status" -o /tmp/prod_status.json

# 本番トレード取得 (limit=2000で12日分カバー)
curl -s "https://fx-ai-trader.onrender.com/api/demo/trades?limit=2000" -o /tmp/prod_trades.json

# entry_type別 7日集計 (Python)
python3 -c "import json; from datetime import datetime,timezone,timedelta; \
  d=json.load(open('/tmp/prod_trades.json')); \
  cutoff=(datetime.now(timezone.utc)-timedelta(days=7)).isoformat(); \
  recent=[t for t in d['trades'] if t['entry_time']>=cutoff]; \
  agg={}; \
  [agg.setdefault(t['entry_type'],[0,0]).__setitem__(t.get('is_shadow',0), agg[t['entry_type']][t.get('is_shadow',0)]+1) for t in recent]; \
  [print(k,v) for k,v in sorted(agg.items(), key=lambda x:sum(x[1]))]"
```

**根拠コミット**:
- `6e8b30a 2026-04-22 09:46:27 feat(prime-gate): 6 PRIME LIVE trial v9.4 (binding until 2026-05-15)` — LIVE停止源ではないと本番データで確認
- `1c295b9 2026-04-27 21:52:25 fix(tier-master): demote trend_rebound to FORCE_DEMOTED (rule:R2)`
- `afe41b9 2026-04-28 11:08:32 fix(registry): Phase 2-5 5戦略を DaytradeEngine + tier-master 登録`

**根拠ファイル**:
- `modules/prime_gate.py` (PRIME 6 rules, 動作確認済)
- `modules/demo_db.py:476-495` (INSERT健全)
- `strategies/daytrade/session_time_bias.py` ⚠ Cat D 深掘り対象
- `knowledge-base/wiki/tier-master.json`

---

## 8. 前回 (ローカルDB版) の主張誤り訂正

| 前回主張 | 本番事実 | 訂正 |
|---------|---------|------|
| PRIME gate (04-22) でLIVE発火が劇的低下 | 04-22以降もLIVE発火継続 (04-27 16件最多) | **誤り**。PRIME gate は LIVE通過機構として正常動作 |
| `gbp_deep_pullback` 全期間 NEVER_EVER | 本番LIVE 1件 (04-23) | **誤り**。ELITE_LIVE として発火実績あり |
| `trendline_sweep` 全期間 NEVER_EVER | 本番LIVE 3件 (04-23) | **誤り**。同上 |
| ローカルDBで集計 | 本番DBは別物 | **CLAUDE.md 違反**。本番API使用に訂正 |

---

## 9. ユーザー方針への適合

- ✅ **本番データ使用** (`CLAUDE.md`): 本版で訂正済
- ✅ **ラベル実測主義**: SQL→API実測クエリ + git blame
- ✅ **成功するまでやる**: Cat D (session_time_bias) の真の異常を発見し別セッション深掘り提案
- ✅ **Live/Shadow区別**: PRIME gate は LIVE側機構、Shadow観測コストは無関係
- ✅ **クオンツファースト**: 仮説 (PRIME gate犯人説) → 実測で反証 → 真因特定

**未実施 (明示)**:
- 本番API trades は limit=2000 で04-16まで遡及。それ以前のデータ確認には別エンドポイント要 (offset/page)
- Cat D session_time_bias の `PAIR_SESSION_MAP` 実 trace は別セッションで debug log 追加して確認
- scalp/1h engine の registry 全数監査は別タスク
