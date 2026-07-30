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

## 関連
- [[preserve-exit-overlay-2026-07-28]] §6.6-5 (発端) / §7 (exit 側是正)
- [[price-shock-reversion]] / [[price-shock-rev-promote-criteria-2026-05-18]]
- [[hourly-engine-shadow-ramp-2026-05-18]] — surface slot の設計意図
- [[score-gate-direction-aware-2026-04-28]] — 勝者 DMB を殺した gate の pre-reg
- MEMORY: `project_engine_reconstruction_live_dedup_dead` (recent_emit が実効 dedup 層)
