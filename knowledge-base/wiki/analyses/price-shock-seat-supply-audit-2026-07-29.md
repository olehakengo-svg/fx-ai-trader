# price_shock_rev 席の供給監査 — eur_aud/usd_cad 3.5 ヶ月無発火の root cause と決裁パケット (2026-07-29)

**種別**: 供給経路監査 (分析のみ、live 変更なし — 修正案は §7 で user R1 決裁待ち)
**発端**: [[preserve-exit-overlay-2026-07-28]] §6.6-5 — counterfactual 分析で eur_aud / usd_cad の 2 席が
2026-05-18 活性化以来 shadow row ゼロと判明 (「0 件なら原因調査」プロトコル)

---

## 1. 期待 vs 観測 (2026-05-18〜07-24)

design 側期待 = MASSIVE H1 canonical で本番と同一の signal 条件 (log_return ≤ rolling 1%-tile ∧ vol_q) を再計算した signal bar 数:

| pair | vol_q | live feed | design 期待 | 観測 rows | capture |
|---|---|---|---|---|---|
| EUR_GBP | Q5 | **MASSIVE** | 11 | 8 | 73% |
| AUD_JPY | ALL | OANDA | 15 | 6 | 40% |
| NZD_JPY | Q5 | OANDA | 5 | 1 | 20% |
| **EUR_AUD** | Q5 | OANDA | **8** | **0** | **0%** |
| **USD_CAD** | Q5 | **yfinance** | **9** | **0** | **0%** |
| 計 | | | **48** | **15** | **31%** |

**問題は 2 席の無発火に留まらない — family 全体の供給が design の ~31% に絞られている。**

## 2. 棄却した仮説 (evidence 付き)

| 仮説 | 判定 | evidence |
|---|---|---|
| engine slot 停止/未登録 | ❌ | 全 5 slot auto_start=True、本番 /api/demo/status で running=True・tick 実測 (58 ticks/5.5h)、Watchdog HB にも常在 |
| live feed のデータ欠損 | ❌ | EUR_AUD: `[OANDA/1h] EURAUD=X 864本取得` を tick 毎に確認。USD_CAD: yfinance 1417 bars。全席 ≥273 bars (warmup 要件) 充足 |
| live feed 上で signal 条件が不成立 | ❌ | OANDA データで同条件を再計算 → EUR_AUD 6 / NZD_JPY 8 / AUD_JPY 18 発火 (05-18〜)。full-bar 条件は live feed でも成立する |
| 静的 shadow demote registry / ps auto-demotion | ❌ | `shadow_demote_registry.py` に price_shock/該当ペアなし、`price_shock_rev_auto_demotions.json` 経路も対象外 |
| forming-bar 検出窓が短すぎる | ❌ | MASSIVE 5m で閾値割れ窓を実測: EUR_AUD median 12min / USD_CAD 10min ≥ EUR_GBP 5min。signal bar は close ≤ 閾値なので窓は必ず bar 終端を含み、tick cadence (~2-5min) で捕捉可能なはず — **むしろ矛盾が深まる測定** |
| deploy/再起動 blackout | △ 部分 | 07-23 01:00 窓は instance 入替 2 回と重複 (寄与 1-2/17 窓)。main push 毎の auto-deploy で再起動は高頻度だが、単独では 0/17 を説明できない |

## 3. Root cause (確定): HourlyEngine winner-take-all × score 非対称

**smoking gun** (retention 内で再起動と重ならない唯一の EUR_AUD signal 窓、bar 13:00-14:00 の直後):

```
2026-07-20 14:00:48 [DemoTrader] [SCORE_GATE] Blocked: donchian_momentum_breakout
score=7.30 misaligned with signal=SELL | EUR_AUD daytrade_1h_euraud
```

機構 (`strategies/hourly/__init__.py` + `modules/demo_trader.py`):

1. `HourlyEngine.evaluate_all` は**全戦略を全 hourly mode で評価**し、`select_best` = 最高 score 1 本のみ採用
2. score は **price_shock = 1.0 固定** (base 実装) vs **DMB/KSB = base 5.0 + ボーナス** (実測 7.30)
3. **1%-tile クラッシュ bar は Donchian 安値 breakout と構造的に共起** → DMB SELL が候補を出した tick では price_shock BUY は必ず敗北
4. price_shock は `_shadow_always` 非所属 (normal single-best emit) → **best 以外の候補は shadow にも block_counts にも痕跡を残さず消滅**
5. 勝った DMB SELL 自身も SCORE_GATE (direction-aware misalign: SELL×正 score) 等の下流 gate で高頻度に block → **両候補とも row 化せず、席は「無発火」に見える**。block_counts は再起動でリセットされるため歴史観測も不能
6. 以前の反証 (「DMB rows が signal 窓近傍に無い」) はこの機構では**反証にならない** — DMB は gate で死ぬので row を残さない

capture 勾配の解釈: DMB/KSB の候補生成頻度・条件はペア依存 (+ AUD_JPY は 15m SELL ポジ由来の hedge_block も混入 — 本日 5.5h で 56 件実測)。EUR_GBP が 73% 通る理由 (同 bar での DMB 非発火率が高い) の分解は §8 補足検証項目。

**設計意図との乖離**: daytrade_1h_* surface slot は「price_shock_reversion Phase B surface」としてコメント上も明示された price_shock の席だが、engine は全戦略を評価するため pair-agnostic な DMB が事実上 slot を占拠している。「bypass 経路を作るときは guard chain のどれを共有するか明示」教訓の engine 版: **席 (surface slot) と emit 権 (select_best) が分離していない**。

## 4. 副次 finding: live feed 三分裂 (BT/live データソース統一原則違反)

| feed | pairs | 備考 |
|---|---|---|
| MASSIVE | EUR_GBP (+USDJPY/EURUSD 系) | 凍結統計と同一ソース — 唯一の estimand 整合席 |
| OANDA | EUR_AUD / AUD_JPY / NZD_JPY | `_MASSIVE_SYMBOLS` (live set) 不在のため fallback |
| **yfinance** | **USD_CAD** (+USD_CHF) | **`_OANDA_SYMBOLS` にすら不在** — OANDA fallback も素通りし品質最下位の Yahoo に到達 |

weekend_gap の AUDUSD=X 追加 (2026-07-28 rule:R3、`modules/data.py` コメント) と同型の不整合。full-bar 条件の成立自体は feed 間で近い (§2) ため root cause ではないが、閾値・vol_q の境界判定はソース依存で、凍結統計 (12.3y MASSIVE) との整合原則に反する。

## 5. 影響の定量

- family の shadow N 蓄積レート = design 供給の ~31% → promote 基準 (registry N≥100 系) への到達が **~3.2 倍遅延**
- live 化済み 5 席の実発火率も同率で抑制 = 機会損失 (4原則 #1「マーケット開いてる間は攻める」に直結)
- 昇格根拠 BT (12.3y MASSIVE) の N/EV は select_best 競合を含まない = **entry 供給の estimand 逸脱** (exit 側は [[preserve-exit-overlay-2026-07-28]] §7 で是正済み、こちらは entry 側の残存逸脱)

## 6. 教訓 (lessons 昇格候補)

- **「無発火」は「無シグナル」ではない。winner-take-all 選抜で敗北した候補は block_counts にも shadow にも痕跡を残さない — 席の供給監査は engine 選抜層まで降りること**
- 反証に使う観測 (DB rows) が、機構 (gate 死) によって系統的に欠損するケースがある — 「不発とゼロ件の区別」教訓の選抜層版

## 7. 決裁パケット (user R1 — 本日は live 変更なし)

| 案 | 内容 | Pros | Cons |
|---|---|---|---|
| **(a) 推奨: price_shock の独立 emit** | HourlyEngine で PRICE_SHOCK_REV_TIER1_TYPES の候補を select_best 競合から外し、best と並行して emit (方向衝突は既存の hedge/dedup gate が裁く) | 席の設計意図を回復 / 他戦略の挙動不変 / 供給 31%→~100% (blackout 除く) | emit 経路の実装変更 (dedup/hedge の共有を明示する設計が必要) |
| (b) score 引き上げ (1.0 → DMB 上限超) | 最小 diff | 1 行 | **DMB 促進ペア (NZD_JPY/NZD_USD) で live DMB を系統的に負かす副作用** — 席同士の優先順位を暗黙に反転させるため非推奨 |
| (c) 併決: live feed 統一 | `_MASSIVE_SYMBOLS` (live) に AUDJPY/NZDJPY/EURAUD/USDCAD 追加 + `_OANDA_SYMBOLS` に USDCAD=X 追加 (fallback 穴) | AUDUSD=X R3 前例踏襲 / 凍結統計とのソース整合 / USD_CAD の Yahoo 依存解消 | MASSIVE API 呼び出し増 (~1.5×)。同 symbol の他 TF mode (15m 等) もソースが変わる — 影響列挙が必要 |

**推奨 = (a) + (c)。(a) は R1 (emit 経路の live 変更、pre-reg 的な影響列挙必須)、(c) は R3 前例 (AUDUSD=X) と同型だが対象が 4 ペア × 複数 TF に及ぶため R1 扱いで併決を推奨。**
初回イベントの検証: (a) 実装後、次の design signal bar (family ~0.33%/bar) で row 化 + 正しい exit (horizon/2×ATR のみ、§7 是正済み) を確認する。

## 8. 補足検証項目 (実装前 pre-reg に含める)

- EUR_GBP 73% の分解 (同 bar DMB 非発火率のペア差) — (a) の効果予測の精緻化
- AUD_JPY hedge_block (15m SELL 由来) の寄与分離 — (a) 後も残る抑制要因の見積もり
- 再起動 blackout の頻度実測 (deploy 回数/日 × warmup 時間) — 恒常的な取りこぼし率の床

## 9. 執行記録 (2026-08-11 — rule:R1、user 決裁「進めて」2026-08-03/08-11)

§7 の (a)+(c) を執行。**(b) は非推奨のまま不採用。** 変更根拠 = 新エッジではなく、BT 検証済み席
(昇格 grid 12.3y MASSIVE BH-FDR m=3744: AUD_JPY N=426 WR 63.8% / NZD_JPY N=303 64.0% /
USD_CAD N=247 66.4% / EUR_AUD N=262 67.6% / EUR_GBP N=239 72.8%、07-24 exit-free 監査全席 p=0.0001)
の**供給経路の回復**。リスク面: 全席 Sentinel 1000u 固定 + ps watchdog (4h cron) + firstweek-regate 併設。

### (a) 席優先 select (`strategies/hourly/__init__.py`)
- `select_best`: ps 候補が存在する tick では ps が primary emit を取る。席集合は instance から導出
  (`_seat_priority_types`、循環 import 回避 + family 追随)
- **影響列挙 (凍結)**:
  - 変化する tick = ps 候補と guest (DMB/KSB) 候補が**共起した tick のみ** (family 発火 ~0.33%/bar × 共起率)
  - displaced guest は `split_shadow_always` 経由で shadow emit 継続 (pin: `test_displaced_guest_still_flows_to_shadow`) — **DMB/KSB の shadow 系列は途切れない**
  - DMB の live 送信は Track C D-c-2 で carve-out 除外中 (shadow のみ) のため **live 挙動の変化はゼロ**。将来 DMB×NZD_JPY を carve-out に入れる場合、共起 tick では ps 優先となる — その時点の再決裁事項としてここに明記
  - ps 候補が出ない slot (usdchf / audusd / nzdusd / USDJPY / eur) は完全不変。ob_retest は disabled、usdjpy_carry は USDJPY のみで共存なし
- pin: `tests/test_price_shock_seat_priority.py` (smoking-gun 再現ケース含む 6 tests)

### (c) live feed 統一 (`modules/data.py`)
- `_MASSIVE_SYMBOLS` (live set) に AUDJPY=X / NZDJPY=X / EURAUD=X / USDCAD=X を追加 (AUDUSD=X R3 前例と同型)
- `_OANDA_SYMBOLS` に USDCAD=X 追加 (yfinance 落ちの fallback 穴修復)
- **影響列挙 (凍結)**:
  - live feed が MASSIVE に切替わる mode: daytrade_1h_{audjpy,nzdjpy,euraud,usdcad} + **daytrade_audjpy (15m)** + 同 symbol の HTF (4h) 取得。15m 切替は BT (MASSIVE parquet) との整合方向 = データソース統一原則
  - MASSIVE 障害時の fallback は OANDA (USDCAD=X 含む) → 従来チェーン
  - MASSIVE fetch 対象 symbol 8→12 (~1.5×、paid 契約 + 既存キャッシュ)
  - **USD_CHF は同じ yfinance 穴が残る** — ps 席ではないためスコープ外 (別途 cosmetic/整合タスク)
- pin: `TestFeedUnificationPins` (source pin + `_OANDA_SYMBOLS` 直接検査)

### 敵対的レビューで確定した副作用と対処 (実装前 3 レンズ × 検証、CONFIRMED 2 件)

1. **DMB JPY SELL の解錠 (feed 切替の非自明な副作用)**: OANDA (864 bars/60d 要求) → MASSIVE (63 暦日フル)
   への切替で D1 リサンプル行数が ~44-45 → ~54 になり、`_compute_1h_htf_bias` の `len(d1) >= 50` 閾値を
   跨ぐ。これまで d1_ema50_falling が恒久 False で**構造的に不可能だった DMB JPY SELL が AUD_JPY/NZD_JPY
   で候補化可能**になる。primary としては SCORE_GATE (SELL×正 score misalign) が block するため row なし
   (従来と同じ) だが、**(a) の席優先が作る displaced-guest 経路は SCORE_GATE を共有しておらず**、
   `_open_shadow_emit_trade` 経由で最大 18h の shadow SELL が開き、hedge gate (shadow も計数) が
   後続の席 BUY を live/shadow とも block し得た — multi-crash-bar 連鎖 (席の狙う局面そのもの) で
   2 大席の再抑制ベクトルになる
   → **対処: shadow_emit ループに primary SCORE_GATE のミラーを実装** (sentinel bypass 込みの同一条件、
   `demo_trader.py` — 「bypass 経路は guard chain の共有を明示」教訓の適用)。これにより displaced
   DMB SELL は row 化せず (primary 時と同じ帰結)、**guest の観測系列は正味不変**が回復する
2. **_MASSIVE_SYMBOLS の substring pin がコメントアウトで素通り** (mutation 実証)
   → **対処: 機能的 dispatch テストに置換** (`test_massive_live_dispatch_for_price_shock_pairs` —
   provider を monkeypatch し 4 symbol × 1h の初手が massive であることを直接検証)
3. **残存 (スコープ外記録)**: hedge gate が shadow ポジションを live 席 entry に対して計数する挙動自体は
   既存仕様 (例: 15m 系 shadow SELL による audjpy hedge_block 56 件/5.5h 実測)。§8 の
   hedge_block 寄与分離で定量し、必要なら別パケット化

### 検証計画 (deploy 後)
1. 次の design signal bar (family どのペアでも) で row 化を確認 — 特に eur_aud / usd_cad の初 row
2. displaced DMB の shadow row 継続を確認
3. `[Massive/1h] AUDJPY=X` 等の feed 切替ログ実測
4. **30d 後に供給率を再計測** (§2 と同手法、design 期待 vs 観測) — 目標 capture ≥80%。未達なら §8 の補足検証 (hedge_block 寄与 / blackout 床) を精査
   → **監視主体併設済み (2026-08-12)**: registry `ps-seat-supply-remeasure-30d` (shadow_count_decision、since 08-11 / N≥15 早期実施 / 期日 09-10) — 「pre-reg には監視主体を必ず併設」教訓 (T5) 準拠。daily の prereg_trigger_watch → Discord レポートに載る

## 10. 追補: WEEKEND_CLOSE 残存逸脱の初実射と counterfactual verdict (2026-08-11)

id=14900 (aud_jpy shadow、2026-07-31 金 13:31 entry) で WEEKEND_CLOSE (金 21:45 強制 close) が初めて material に bind:
- realized: **−126.5p** (WEEKEND_CLOSE)
- design counterfactual (bar-index 週末跨ぎ保有、exit = Close[i+12] = 月曜 02:00、SL 距離 287.7p 非発火): **−191.0p**
- **Δ = WEEKEND_CLOSE が +64.5p 保護的に働いた** (週末ギャップ AUD_JPY 続落)

**verdict: WEEKEND_CLOSE 免除は非推奨で確定** — (i) N=1 ながら初実射が保護方向、(ii) 週末跨ぎ保有は
ポートフォリオ全体のギャップリスクポリシー事項で、席単独の estimand 整合より上位、(iii) 免除の期待値改善の
evidence がない。preserve-exit-overlay §7 の「既知の残存逸脱」ステータスを維持し、G-gate 解釈時に
金曜午後 entry のみ WEEKEND_CLOSE ラベルが混じる点を注記する。

## 関連
- [[preserve-exit-overlay-2026-07-28]] §6.6-5 (発端) / §7 (exit 側是正)
- [[price-shock-reversion]] / [[price-shock-rev-promote-criteria-2026-05-18]]
- [[hourly-engine-shadow-ramp-2026-05-18]] — surface slot の設計意図
- [[score-gate-direction-aware-2026-04-28]] — 勝者 DMB を殺した gate の pre-reg
- MEMORY: `project_engine_reconstruction_live_dedup_dead` (recent_emit が実効 dedup 層)
