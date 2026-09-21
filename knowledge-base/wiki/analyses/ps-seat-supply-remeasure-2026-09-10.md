# ps 席供給 30d 再計測 — 中途窓 diagnostic と capture estimand の破綻 (2026-09-09)

**種別**: 供給率再計測 (計測・診断のみ / rule:R3 — live パラメータ・tier・lot・gate 変更なし)
**registry**: `ps-seat-supply-remeasure-30d` (since 2026-08-11 / 期日 2026-09-10 / N≥15 早期実施)
**親監査**: [[price-shock-seat-supply-audit-2026-07-29]] §9 検証計画 4 (「30d 後に供給率を再計測、目標 capture ≥80%」)
**ハーネス**: `tools/ps_seat_supply_remeasure.py` (pin: `tests/test_ps_seat_supply_remeasure.py`、19 tests)

> ⚠️ **本ページは verdict ではない。** 窓 (2026-08-11T00:00Z 〜 2026-09-10T23:59Z) は本日時点で未完
> (実効 29.1/31 日)、かつ早期実施条件 (観測 unique N≥15) も未成立 (N=7)。pre-reg の
> 「中途窓での verdict 禁止」に従い、ハーネスは `MID_WINDOW_DIAGNOSTIC` を自己申告する
> (この規律は prose ではなく `decide_verdict` にコード実装 + pin 済み)。
> **正式 verdict は窓完成後 (2026-09-11 以降) の再実行で確定する。** §5 に実行手順。

---

## 1. 中途窓 diagnostic (as-of 2026-09-09T03:00Z)

design 期待 = canonical MASSIVE H1 (凍結 12.3y audit parquet + live top-up の union-merge) 上で
**本番戦略オブジェクト自身の** `signal_mask_from_dataframe` を評価した closed-bar signal 数。
観測 = 本番 `/api/demo/trades` (全 1,700 行取得) のうち 5 席 `entry_type` ∧ `dedup_violation != 1`、
`unique` = (entry_type, instrument, direction, bar_ts) で計数。live 判定は `oanda_trade_id != ''` (canonical)。

| pair | vol_q | design 期待 | 観測 LIVE | 観測 shadow | 観測 unique | design bar 上 | capture | Wilson95 |
|---|---|---|---|---|---|---|---|---|
| EUR_GBP | Q5 | 5 | 4 | 1 | 5 | 1 | 100% | [57%, 100%] |
| AUD_JPY | ALL | 12 | 2 | 0 | 2 | 1 | 17% | [5%, 45%] |
| NZD_JPY | Q5 | 6 | 0 | 0 | **0** | 0 | **0%** | [0%, 39%] |
| EUR_AUD | Q5 | 7 | 0 | 0 | **0** | 0 | **0%** | [0%, 35%] |
| USD_CAD | Q5 | 4 | 0 | 0 | **0** | 0 | **0%** | [0%, 49%] |
| **計** | | **34** | **6** | **1** | **7** | **2** | **21%** | **[10%, 37%]** |

- design 期待 34 は既に判定床 (N≥15) を**超えている** → 窓完成時に `NEEDS_MORE_EVIDENCE` 分岐は
  ほぼ消滅。残り ~1.9 日で観測が 27 件増える経路は存在しないため、**窓完成時の verdict は
  `REJECT` (capture <80%) がほぼ確定** — ただし断定は 09-11 の実行に委ねる (§5)。
- 親監査 §1 の是正前 baseline は capture **31%** (design 48 / 観測 15、2026-05-18〜07-24)。
  今回 21% は**同一手法で baseline を下回る**。窓もペア構成も異なるため対応のある比較ではないが、
  「#172 で 31%→~100% (blackout 除く)」という §7(a) の予測は成立していない。
- 3 席 (NZD_JPY / EUR_AUD / USD_CAD) は観測ゼロ。EUR_AUD / USD_CAD は親監査時点の 0% 席のままで、
  **NZD_JPY が新たに 0 へ落ちた**。design 供給は 6/7/4 本存在するので「シグナルが無かった」ではない。

## 2. 🔴 主要 finding: capture は「捕捉率」ではない — 分子と分母がほぼ交わらない

観測 7 行を canonical データで 1 行ずつ判定した (15m close を intra-bar path の代理に使用):

| 観測 entry (UTC) | anchor bar | thr(1%-tile) | closed_ret | 15m partial 最小 | 閉値 vol_q | 判定 |
|---|---|---|---|---|---|---|
| 08-17 09:56 EUR_GBP | 09:00 | −0.000666 | −0.000514 | −0.000514 | Q5 | **NEITHER** |
| 08-20 07:41 EUR_GBP | 07:00 | −0.000648 | −0.000186 | −0.000571 | Q5 | **NEITHER** |
| 08-20 12:59 EUR_GBP | 12:00 | −0.000648 | −0.000385 | −0.000385 | Q4 | **NEITHER** |
| 08-21 11:39 EUR_GBP | 11:00 | −0.000649 | −0.000747 | −0.000712 | **Q4** | partial-only (閉値は Q5 要件を外す) |
| 08-26 14:59 AUD_JPY | 14:00 | −0.001384 | −0.001374 | −0.001374 | Q3 | **NEITHER** (閾値まで 0.7%) |
| 09-03 15:08 EUR_GBP | 15:00 | −0.000810 | −0.000605 | −0.000931 | Q5 | partial-only (recovered) |
| 09-03 05:58 AUD_JPY | 05:00 | −0.002237 | −0.002667 | −0.002667 | Q5 | ✅ **closed-bar design** |

**closed-bar design signal に対応するのは 7 行中 1 行のみ** (anchor を floor(entry)−1h まで緩めても 2 行)。
逆向きに見ると、design 34 本のうち row 化したのは 1〜2 本 = **closed-bar 基準の真の capture は ~3〜6%**。

機構は「バグ」ではなく **estimand の不一致**である:
- live は **forming bar** を評価する ([[price-shock-seat-supply-audit-2026-07-29]] §2 /
  `tools/price_shock_exit_counterfactual.py` header の 2026-07-28 検証)。したがって live の
  (log_return, vol20, vol_quintile) の三つ組は**部分バー量**であり、閾値越えが bar 終値で
  戻れば closed-bar design には現れない (08-21 / 09-03 15:00 がこの型)。
- vol_q 側でも同じ非対称が起きる: 08-21 11:00 は closed_ret が閾値を**越えている**のに
  閉値 vol_quintile が Q4 で、Q5 要件の design mask からは落ちる。live は部分バーの vol20 で
  判定するため通る。
- 昇格根拠の凍結 grid (12.3y MASSIVE、BH-FDR m=3744、全席 p=0.0001) は **closed-bar 母集団**で
  測られている。**live が実際に建てている bar 母集団はそれとほぼ交わらない。**

したがって:
1. §9 検証計画 4 の「capture ≥80%」という目標は、**分子と分母が別母集団**であるため
   そのままでは達成も反証もできない量を測っている。これは #172 の成否とは独立の設計問題。
2. 親監査 §5 の「昇格根拠 BT の N/EV は select_best 競合を含まない = entry 供給の estimand 逸脱」
   は、**競合以前に部分バー/閉バーの層で既に逸脱していた**と読み替えるべき。
3. これは pre-reg 中の指標を書き換える理由には**しない** — 09-11 は凍結された境界どおり
   実行し、estimand の張り替えは別 R3 パケットとして起案する (§6)。

**caveat**: intra-bar path の代理に 15m close を使っているため、`NEITHER` 4 行については
tick レベルでより深い一時的下落があった可能性を排除できない (解像度の限界)。一方 08-21 の
vol_quintile 不一致は閉バーから決定的に計算されるため代理解像度に依存しない。

## 3. データ provenance (design 側の健全性)

凍結 12.3y audit parquet は 2026-07-24 10:00Z で終わるため、窓 (08-11〜) は **全て live top-up 由来**。
top-up が凍結系列の正当な延長であることを重複区間で実測 (overwrite ではなく union-merge、
「rolling 窓キャッシュは union-merge が既定」教訓準拠):

| pair | 重複バー | 完全一致 | median \|Δclose\| | p95 | max |
|---|---|---|---|---|---|
| EUR_GBP | 1,280 | 1,254 (98.0%) | 0.000000 | 0.000000 | 0.00075 |
| AUD_JPY | 1,291 | 1,258 (97.4%) | 0.000000 | 0.000000 | 0.026 |
| NZD_JPY | 1,310 | 1,275 (97.3%) | 0.000000 | 0.000000 | 0.029 |
| EUR_AUD | 1,286 | 1,258 (97.8%) | 0.000000 | 0.000000 | 0.00052 |
| USD_CAD | 1,310 | 1,292 (98.6%) | 0.000000 | 0.000000 | 0.00028 |

median/p95 = 0 かつ 97〜99% が bit-exact。max は少数の外れバーのみ。
**ベンダー drift は design 計数を左右する水準ではない** (「歴史バーは drift する」既知事象の範囲内、
MEMORY `project_massive_vendor_gap_backfill`)。design 側の数字は信頼できる。

## 4. §8 補足検証の状態

窓完成時に `REJECT` が確定した場合、パケットは §8 (hedge_block 寄与分離 / 再起動 blackout 床 /
未説明残余) の完遂を要求する。本日時点では**未着手** — 中途窓で回すと帰属の分母が動くため
意図的に 09-11 以降へ回す。ただし §2 の finding により §8 の位置づけは変わる:

- 3 席 (NZD_JPY / EUR_AUD / USD_CAD) の観測ゼロは design 17 本に対するゼロなので、
  hedge_block / blackout の寄与分離は依然として必要 (0 の説明は §8 の領分)。
- 一方 EUR_GBP / AUD_JPY の「観測はあるが design bar ではない」7→1 の落差は
  hedge_block でも blackout でも説明されない — **§8 の 3 項目に含まれない第 4 の要因**
  (部分バー評価) であり、§6 の別パケットで扱う。

## 5. 窓完成後の実行手順 (09-11 以降、1 コマンド)

```
python3 tools/ps_seat_supply_remeasure.py --json > /tmp/ps_remeasure_final.json
```

- `--cache-dir` は worktree 実行時のみ main repo の `data/cache/massive` を指す (worktree に
  parquet と `.env` が無いため。`.env` fallback は `tools/massive_gap_backfill.py` と同一規約)。
- `--as-of` は既定で現在時刻。窓完成後は `window.complete=true` となり `decide_verdict` が
  ACCEPT / NEEDS_MORE_EVIDENCE / REJECT のいずれかを返す。
- **実行主体 = fx-roadmap-autopilot の日次実行** (ローカル `.env` に MASSIVE_API_KEY があるため
  GitHub Actions / Render cron には現状のせられない — CI にも render.yaml にも当該 secret が無い)。
  registry `ps-seat-supply-remeasure-30d` の message に本コマンドを明記し、到達経路を固定した
  (「KPI を定義したら同じコミットで毎日再計算する主体を定義せよ」教訓準拠)。
- verdict 後: analyses に verdict 追記 + 親監査 §9 末尾に 1 行 + registry resolve/roll を**同一コミット**で。

## 6. 起案 (実装しない — 別パケット)

- **P-1 (R3、分析のみ)**: 供給率の estimand を「closed-bar design capture」と
  「forming-bar 発火の closed-bar 妥当性」の 2 軸に分離し直す。前者は席の取りこぼし、
  後者は「凍結 grid が live 母集団を記述しているか」を測る別問題。現行の単一 capture 指標は
  両者を混ぜており、どちらの問いにも答えられない (§2)。
- **P-2 (R1、実装は user 決裁)**: 部分バー発火を closed-bar 条件に揃える (bar 確定後に評価) か、
  逆に部分バー母集団で grid を再検証するか。**どちらも席の EV 前提を変えるため R1**。
  P-1 の計測結果なしに着手しない。
- いずれも `ps-carveout-regate-post-172` (09-30、clean live N≥10 で EV 判定) の look を
  burn しない (本ページは EV / WR / PnL を一切計算していない — P-10 型 ban 準拠)。

## 関連
- [[price-shock-seat-supply-audit-2026-07-29]] (親監査 §1 手法 / §8 補足項目 / §9 執行記録)
- [[ps-carveout-firstweek-regate-disposition-2026-08-12]] (初週窓無効判定 → #172 後へ再アンカー)
- [[preserve-exit-overlay-2026-07-28]] §6.6-5 (発端) / [[price-shock-reversion]]
- [[live-roster-attrition-2026-09-06]] (「発火機会不足は摩擦調整 EV 不在の帰結」仮説の検証材料)
- MEMORY: `project_massive_vendor_gap_backfill` / `feedback_live_vs_shadow_strict_separation`

---

# 追補 (2026-09-11): 窓完成後の正式 verdict と §8 帰属

## 7. 正式 verdict = 🔴 **REJECT** (窓完成、as-of 2026-09-11T01:32Z)

`python3 tools/ps_seat_supply_remeasure.py --json` を §5 の手順どおり **1 回だけ**実行。
`window.complete=true` (frozen end 2026-09-11T00:00Z ≤ as_of) を確認済み。
生 JSON: `knowledge-base/raw/audits/ps-seat-supply-verdict-2026-09-11.json`

| pair | vol_q | design 期待 | 観測 LIVE | 観測 shadow | 観測 unique | design bar 上 (緩/厳) | capture | Wilson95 |
|---|---|---|---|---|---|---|---|---|
| EUR_GBP | Q5 | 5 | 4 | 1 | 5 | 1 / 0 | 100% | [57%, 100%] |
| AUD_JPY | ALL | 12 | 2 | 0 | 2 | 1 / 1 | 17% | [5%, 45%] |
| NZD_JPY | Q5 | 6 | 0 | 0 | **0** | 0 / 0 | **0%** | [0%, 39%] |
| EUR_AUD | Q5 | 7 | 0 | 0 | **0** | 0 / 0 | **0%** | [0%, 35%] |
| USD_CAD | Q5 | 4 | 0 | 0 | **0** | 0 / 0 | **0%** | [0%, 49%] |
| **計** | | **34** | **6** | **1** | **7** | **2 / 1** | **20.6%** | **[10.3%, 36.8%]** |

**判定根拠 (pre-reg 境界そのまま)**: design 期待 34 ≥ 床 15 ∧ capture 20.6% < 80% → `REJECT`。
`decide_verdict` がコードで返した文字列をそのまま採用しており、事後の閾値変更は無い。

**09-09 中途窓 diagnostic からの差分 = ゼロ** (design 34 / 観測 unique 7 / capture 21% で完全一致)。
残り 1.9 日で design bar も観測行も 1 件も増えなかった。§1 の「観測が +27 件になる経路は無い」は
予測として当たったが、**design 側も動かなかった**点は予告していない — 週末 (09-06/07) と
09-08〜09-10 の低ボラが両側を止めた。

**是正前 baseline との比較**: 親監査 §1 は design 48 / 観測 15 / capture **31%** (2026-05-18〜07-24)。
PR #172 (§7(a) 席優先 select + §7(c) feed 統一、08-11 deploy) の後に **20.6% へ低下**している。
窓もペア構成も異なるため対応のある比較ではないが、§7(a) が予測した「31% → ~100% (blackout 除く)」は
**成立していない**と結論できる (予測値との差が Wilson 上限 36.8% を大きく超える)。

---

## 8. §8 補足検証の完遂 — 3 項目とも「説明しない」ことが確定

pre-reg は REJECT 時に §8 (hedge_block 寄与 / 再起動 blackout 床 / 未説明残余) の完遂を要求する。
帰属対象を **3 席 (NZD_JPY / EUR_AUD / USD_CAD) の design 17 本に対する観測ゼロ** に固定して実行した
(EUR_GBP 5/5 と AUD_JPY 2/12 の「観測はあるが design bar ではない」落差は §2 の第 4 要因であり、
§8 の領分ではない)。

### 8-1. hedge_block 寄与 = **0 本** (構造的に bind 不能、確定)

`hedge_block` は同一 instrument に反対方向の建玉があるときに発火する
(`_block(f"hedge_block({_base_mode}/{instrument}:{signal})")`, demo_trader.py)。
`MODE_CONFIG` を実測で引くと、3 席のペアには**搬送 mode が席そのものしか存在しない**:

| pair | そのペアを扱う全 mode | 15m 対向 mode |
|---|---|---|
| EUR_AUD | `daytrade_1h_euraud` のみ | **無し** |
| USD_CAD | `daytrade_1h_usdcad` のみ | **無し** |
| NZD_JPY | `daytrade_1h_nzdjpy` のみ | **無し** |
| AUD_JPY | `daytrade_audjpy` (15m) + `daytrade_1h_audjpy` | 有り |
| EUR_GBP | `daytrade_eurgbp` (15m) + `daytrade_1h_eurgbp` | 有り |

反対建玉を作る経路が無い以上、3 席で hedge_block は**原理的に発火しない**。
実測でも裏付けられる ([[ps-seat-hedge-block-snapshot-2026-09-10]] §2、3.47h 窓):
`daytrade_1h_euraud` / `_usdcad` / `_nzdjpy` / `_audjpy` の hedge_block は**全て 0**、
3 桁 (129 / 109) が立つのは 15m 側の `daytrade_eurgbp` / `daytrade_audjpy` のみ。

→ 親監査 §3 が AUD_JPY について挙げた hedge_block は **AUD_JPY 固有**であり、
family 全体の供給抑制要因ではなかった。**3 席の 17 本に対する寄与 = 0。**

### 8-2. 再起動 blackout 床 = **上界でも 17 本中 ~1.2 本** (説明力を持たない)

窓内 (08-11〜09-10) の deploy を Render buildFilter (`ignoredPaths` 26 パターン) を
commit の変更ファイルに適用して再構成: **104 deploy / 31 日 = 3.4 deploy/日**
(08-11〜08-22 は 2.3/日、08-23〜09-10 は 4.0/日。PR #199/#201 の churn ゼロ化後も
コード PR 自体は残るため 0 にはならない)。1 回あたりの無評価時間は
Render の cutover (旧 instance は build 中も tick 継続) + 新 instance の初 tick までで、
実測 tick cadence ~79s (09-11 00:34:55Z deploy → 01:32Z で 44 tick) から**上界 5 分**と置く。

感度解析 (意図的に過大な仮定):

| 仮定 | blackout 割合 | 17 本中の期待被覆 | P(17 本すべて被覆) |
|---|---|---|---|
| 実測 3.4/日 × 5 分 | 1.2% | 0.20 本 | ~10⁻³³ |
| **10× 過大 34/日 × 5 分** | 11.8% | **2.0 本** | ~10⁻¹⁶ |
| 17 本ゼロが p>0.05 で説明できる境界 | **84%** | 14.3 本 | 0.05 |

blackout が説明要因になるには wall-clock の **84%** を覆う必要があり、
実測の 70 倍の deploy 頻度に相当する。→ **床としては存在するが、3 席の 17 本ゼロを説明しない。**

### 8-3. 未説明残余 = **17 本中 ~17 本 (~100%)**、かつ帰属先は「計装の不在」

残余を上流 (A: `evaluate_all` が候補を出していない) と下流 (B: 候補は出て席優先 select で
勝ったが `_tick_entry` / order 層で落ちた) に割る作業を試みたが、**3 つの観測面すべてが
hourly 経路を覆っていない**ため計算できなかった:

| 観測面 | 窓 (08-11〜09-10) を覆うか | 理由 |
|---|---|---|
| `_block_counts` (in-memory) | ❌ | 再デプロイ毎にゼロリセット。09-11 取得時点で tick_counts=45 = 直近数十分ぶんのみ |
| `gate_block_daily` (PR #248) | ❌ | 永続だが**稼働開始が 2026-09-11** — 窓の履歴を 1 日も持たない |
| `evaluated_candidates` (C1) | ❌ | 2026-04-28 以来 `_dt_engine` 経路にしか call site が無い。**HourlyEngine には log_candidates 呼び出しが存在しない** |

C1 の不在は本日実測で確定: `/api/demo/evaluated-candidates?view=summary&days=31` が返す
48 戦略に `price_shock_rev_*` は **1 つも無い** — 観測 7 行を実際に出した EUR_GBP / AUD_JPY の席すら
不在。`app.py` の `compute_hourly_signal` は `evaluate_all` → `select_best` →
`split_shadow_always` を呼ぶだけで `log_candidates` を呼んでいなかった。

**残余の性質が「未知の抑制要因」ではなく「測っていない」である**点が本節の結論。
hull funnel (2026-08-24) が 49 日未診断だったのは「書けるが読めない」だったが、
ここは**そもそも書いていない**段階の欠損で、1 段階手前にある。

参考: `daytrade_1h_nzdjpy` には 3.47h で `score_gate` 23 件の block が立っている
([[ps-seat-hedge-block-snapshot-2026-09-10]] §2) ので、この mode の下流層は動いている。
しかし `per_strategy_counts` の hedge_block 帰属が `unknown` 596 件に落ちるのと同様、
**どの戦略の候補が落ちたかは現行計装では分からない** — (A) と (B) を分ける情報が無い。

---

## 9. 執行 (本コミット、rule:R3 — live 挙動不変)

§8-3 で確定した計装欠損を塞ぐ。**live のパラメータ・tier・lot・gate は一切変更しない**
(pre-reg の「REJECT でも是正実装は別タスク」は *supply 是正* に掛かる禁止であり、
帰属を可能にする観測面の追加は §8 完遂の前提条件そのものなので同一タスク内で行う。
PR #248 の `gate_block_daily` が同じ論拠で同じ扱いを受けた前例に揃える)。

- `app.py::compute_hourly_signal`: `select_best` の直後に `log_candidates` を呼ぶ。
  best-effort (`try/except` で握り潰し) — DTE 経路と同一契約で trade flow に影響しない。
  `bar_time` は PR #168 / 2026-08-24 の fallback (`bar_time or df.index[-1]`、UTC 正規化) を
  踏襲 — live は `compute_fn(df, tf, sr, symbol)` で bar_time を渡さないため、素の
  `bar_time` を渡すと hourly 行も全て NULL になり bar 粒度への正規化が不能になる (4 例目の再発防止)
- pin: `tests/test_hourly_candidate_logging.py` (10 tests) — call site の存在 / 敗者を含む全候補を
  渡すこと / 早期 return より前であること / try-except 保護 / bar_time が派生値であること /
  DB 往復の行動証拠 / 候補ゼロ tick の no-op / counterfactual (呼び出し不在で finder が空を返す) /
  5 席すべてが HourlyEngine 所属であること
- 書込み量の見積り: DTE 経路の実測が 3,125 行/日 (7d summary 21,872 行 / 48 戦略)。hourly は
  10 mode × 7 戦略で同オーダーと見込む。C1 retention は 90 日 + `prune_candidates` +
  `disk_guard` (PR #205/#206) が上限を握っており、本日の disk は 60.35% / free 370MB。
  **次節のチェックポイントで実測に置き換える** (見積りのまま放置しない)

## 10. 後続 (registry 登録済み)

- `ps-seat-supply-hourly-c1-coverage` (新設、期日 **2026-09-25**): 計装 deploy 後 14 日で
  (i) `/api/demo/evaluated-candidates?view=summary&days=14` に `price_shock_rev_*` 5 席が
  出現しているか、(ii) C1 書込み量の実測が §9 見積りの範囲か (disk 逼迫なら retention 短縮)、
  (iii) 3 席の残余が (A) 上流不在 / (B) 下流 gate のどちらかに割れたか、を判定する。
  **この 3 点が揃うまで §8-3 の残余は「未帰属」のまま据え置く** (盛らない)
- `ps-seat-supply-remeasure-30d` は本 verdict で **resolved**。供給是正の再試行は
  (iii) の帰属が出てから設計する — 帰属なしに §7(a) 型の是正を重ねない
- `ps-carveout-regate-post-172` (09-30、clean live N≥10 で EV 判定) の look は**未消費**。
  本ページは EV / WR / PnL を一切計算していない (P-10 型 ban 準拠)。
  ただし供給率 20.6% のままでは 09-30 までに N≥10 到達は困難 —
  同エントリの「N<10 なら供給側の別問題として stale レビュー」分岐に入る見込み

---

## 11. ✅ readout 執行 = **(B) 下流 100%** (2026-09-21、期日 09-25 の 4 日前倒し)

registry `ps-seat-supply-hourly-c1-coverage` の 3 点を執行。rule:R3 (readout と帰属のみ
— gate / tier / lot / 供給是正は本節の範囲外、EV/WR/PnL は計算していない = P-10 型 ban 準拠)。

as-of **2026-09-21T01:05Z** / `days=14` (窓 09-07〜09-21、hourly C1 計装は 09-11 稼働)。

### 11.1 (i) 計装到達 = **PASS**

`/api/demo/evaluated-candidates?view=summary&days=14` の `n_strategies=50` に
`price_shock_rev_*` **5 席すべてが出現**。§9 の配線は本番に届いている
(期日 09-25 を待たず確認できたので、配線落ちだった場合の 14 日ロスを回避した)。

### 11.2 (ii) 書込み量 = **見積り範囲内、retention 短縮不要**

| 実測 (09-21T01:05Z) | 値 |
|---|---|
| `evaluated_candidates` 行数 | **325,530** (first 2026-06-23 / last 2026-09-21T01:05:30) |
| disk `used_pct` | **60.4%** (`level=ok`、warn 75 / critical 90) |
| disk free | 387,461,120 B |
| `c1_retention_days` | 90 |
| `write_probe` | `ok=true` @ 01:05:43Z |

§9 の見積り (DTE 経路 3,125 行/日と同オーダー) を覆す逼迫は無い。**retention 短縮は不要** —
見積りを実測で置き換え、§9 の「見積りのまま放置しない」を履行した。

### 11.3 (iii) 帰属 = **(B) 下流。上流 (A) は棄却**

**⚠️ 機会の単位は行ではなく `bar_time`。** C1 行は `evaluate_all()` の全候補を
~30s poll ごとに記録する (app.py:4634 の call site、estimand は
`gate_block_attribution` と同じ per-tick)。生 141 行 → distinct bar **10 本** =
**14.1 倍の重複膨張**。行数で機会を数えると 1 バーを 39 回数える
(hunt_events の N 膨張と同型 — MEMORY `project_hunt_events_dataset_readout_2026_09_19`)。

| seat | `vol_q` | C1 行 | **distinct bar** | `selected=1` | order_bar_dedup | recent_emit | spread_wide | velocity_down | gbp_asia_flash_crash | Σblocks |
|---|---|---|---|---|---|---|---|---|---|---|
| nzd_jpy | Q5 | 42 | **2** | 42/42 | 39 | 1 | **2** | – | – | **42** |
| eur_aud | Q5 | 24 | **3** | 24/24 | 20 | 1 | **3** | – | – | **24** |
| usd_cad | Q5 | 39 | **1** | 39/39 | 37 | – | **2** | – | – | **39** |
| aud_jpy | ALL | 15 | **2** | 15/15 | 11 | 2 | – | **2** | – | **15** |
| eur_gbp | Q5 | 21 | **2** | 21/21 | – | – | – | – | **21** | **21** |
| **計** | | **141** | **10** | **141/141** | 107 | 4 | 7 | 2 | 21 | **141** |

**Σblocks が C1 行数と 5 席すべてで厳密一致** = order 層に到達した候補はゼロ。
かつ `selected=1` が **141/141** なので、席優先 select は一度も負けていない。

→ **(A) 上流 = `evaluate_all` が候補を出していない は棄却。(B) 下流で確定。**

### 11.4 どの gate が落としたか (コード照合済み)

`_maybe_reserve_order_bar_emit` (modules/demo_trader.py:1348) は
`(entry_type, instrument, signal, 正規化 bar_ts)` で **1 バー 1 予約**。初回は `None`
(= 通過)、同バーの再評価が `order_bar_dedup`。call site は `_tick_entry` primary 経路の
**5491 行**で、`spread_wide` 判定は **6244 行 = 予約より後**。したがって:

- **初回/バー**の候補は dedup を通過して終端 gate に到達する
- **同バー再評価**ぶんは `order_bar_dedup` / `recent_emit` が吸収する = **これは機会損失ではない**

この分解を当てると、**終端 gate の発火数 ≒ distinct bar 数**になり実測と合う:

- nzd_jpy: bar 2 / spread_wide 2 ✅ ・ eur_aud: bar 3 / spread_wide 3 ✅ ・ aud_jpy: bar 2 / velocity_down 2 ✅
- usd_cad のみ bar 1 に対し spread_wide 2 (+1)。最も素直な説明は
  `_order_bar_signal_emits` が **in-memory dict** で、Render 再起動が同バー中に予約を消して
  2 本目が終端まで届いたこと (MEMORY `project_engine_reconstruction_live_dedup_dead` /
  「in-memory dedup はプロセス境界を越えられない」)。**独立確認はしていない** — 帰属の向きは変わらない
- eur_gbp は `order_bar_dedup` が **0** で `gbp_asia_flash_crash` が全 21 行 =
  この guard は**予約より前**に評価されている (gate 順序が本番データから直接読める)

**結論: 対象 3 席 (NZD_JPY / EUR_AUD / USD_CAD) の distinct bar 機会 6/6 は
`spread_wide` で落ちている。** `order_bar_dedup` 107 + `recent_emit` 4 は同バー重複の
抑制であって attrition ではない。
(`recent_emit` 4 本は初回/バーか重複かを現行計装で分離できない — この規模では帰属を変えない)

### 11.5 🔴 これは配線バグではなく **設計レベルの衝突**

3 席の entry 条件を読むと (`strategies/hourly/price_shock_reversion_base.py:63-70`):

- **`log_return ≤ 252 バー rolling 1%-tile`** = 定義上「最も極端な下落 ~1%」でのみ発火
- **3 席すべて `vol_q="Q5"`** (nzd_jpy / eur_aud / usd_cad) = **最高ボラ分位でのみ**発火

一方 `spread_wide` の閾値は**静的な per-pair 定数** (modules/demo_trader.py:6221-6236):
USD_CAD **1.5p** / EUR_AUD **2.0p** / NZD_JPY **3.0p** — 平常時基準の値。

**つまり席の設計 (Q5 ボラ × 1%-tile ショック) は、spread gate が弾く状態を狙って撃っている。**
スプレッドはショック時に拡大するので、**entry 条件と block 条件が構造的に正相関**している。
同じ構造は他 2 席にも出る — aud_jpy (`vol_q=ALL`) の終端 gate は `velocity_down`
(急落速度) で、これもショック条件と同軸。eur_gbp は 2 本とも **21:00 UTC** (Asia 開始) に
落ちており `gbp_asia_flash_crash` に当たる — こちらは 4原則#3 の
「LIVE 側は勝てる場所で勝つ条件だけ転送」に沿った**意図された**静的ブロックなので欠陥ではない。

**したがって ps 席が clean live N を産まないのは供給不足ではなく、
「ショックを狙う戦略」と「ショック時に閉じる保護 gate 群」の設計衝突である。**

### 11.6 ⚠️ 残る 1 つの未測定量 — 本コミットで計装した

「marginal (3.1p vs 3.0p limit = 調整可能)」と「absolute (15p = 構造的)」は
**disposition を正反対にする**が、判定できなかった: `gate_block_daily` は
`reason.split('(')[0]` で正規化していたため `spread_wide(4.2pip>3.0)` の **4.2 を捨てていた**
(in-memory counter のキー爆発防止が永続面まで波及していた)。Render ログも ~2 週で失効し、
09-17/09-18 のバーは既に取れない。

**本コミットの実装 (rule:R3、live 挙動不変)**:
- `modules/block_event_logger.py`: `gate_block_daily` に `metric_n / metric_sum /
  metric_min / metric_max` を追加 (既存本番テーブルは `_ensure_metric_columns` で
  idempotent に ALTER、過去行は NULL = 「測っていない」を捏造しない)。
  `parse_reason_metric()` が raw reason の最初の括弧内の数値を取る
- `modules/demo_trader.py::_record_entry_block`: raw `reason` から magnitude を抜いて渡す。
  **in-memory キーは従来どおり `'('` 前で正規化 = 挙動不変。PRIMARY KEY も不変なので
  キー空間は増えない** (magnitude は行ではなく min/sum/max に畳む)
- **読み手を同一コミットで併設**: `query_block_counts` が `per_cell_metrics`
  (`{n, min, mean, max}`) を返し、`/api/demo/block-counts` が **top-level キーとしても
  明示的に露出**する。収集だけ足して読み手を足さないのが本プロジェクト再発の
  write-only 欠陥 ([[c1-candidate-readout-hull-funnel-2026-08-24]])
  - ⚠️ **初版は `persisted` 経由の dict 透過だけで済ませようとして pre-commit に止められた** —
    estimand 宣言 `gate_block_attribution` の reader 配線検査 (`app.py` に検索文字列が
    実在するか) が「読み手がコード上のどこにも**名前で**現れない」を ERROR にした。
    **暗黙の透過は「読み手あり」ではない**ので宣言を緩めずコード側を直した
    (`per_cell_metrics` を endpoint payload に明示)。検査が設計の弱点を捕まえた事例
  - ⚠️ **magnitude の単位は reason ごとに違う** — `spread_wide`=pip / `cooldown`=秒 /
    `velocity_down`=pip (符号つき) / `gbp_asia_flash_crash`=**UTC 時**。
    `per_cell_metrics` のキーが reason を含むので同一 reason 内では一貫するが、
    **reason を跨いだ平均は無意味** (`test_metric_unit_is_per_reason_not_global` で pin)
- pin: `tests/test_gate_block_metric.py` (12 tests)。**counterfactual を実測で確認済み** —
  `_persist_gate_block` の metric passthrough を外すと
  `test_spread_wide_magnitude_survives_entry_block_path` が落ちる (恒真な pin ではない)。
  「NG を返す既知の入力」も同時に pin (`order_bar_dedup` /
  `hedge_block(daytrade/EUR_USD:BUY)` = 括弧内に数値なし → None)
  — MEMORY `project_review_gate_vacuous_2026_09_11`

### 11.7 所見 (帰属のみ。是正は起案せず)

- **`confidence=70` / `score=1.0` が 141 行すべてで定数**なのは
  `price_shock_reversion_base.py:88` のハードコード = **設計どおり**。
  「定数なら異常」の不変条件に対する**文書化された例外** (次の読み手が再フラグしないように記録)
- 10 本の機会バーは **09-15/16/17/18 に集中**し、09-11〜09-14 と 09-19〜09-21 はゼロ =
  バースト構造 (MEMORY `project_row_freshness_candidate_cadence`)。
  レート主張には bar 単位の窓が必要
- **供給量そのものは (A) を支持しない**が「design どおり」とも言わない:
  3 席 design 17 本/30d → 計装窓 11 日ぶんの期待 ≈ 6.2 に対し実測 distinct bar **6**。
  Poisson(6.2) の下で完全に整合する一方、**N=6 では ~2 倍の不足も排除できない**。
  言えるのは「**(A) が律速ではない**」だけ (§2 の分子/分母 disjoint 問題と同じ規律)

### 11.8 registry 処理

- `ps-seat-supply-hourly-c1-coverage` → **resolved** (3 点すべて判定、roll 不要)
- **ps 席残余は本節で「帰属済み」に昇格**。§8-3 の「未帰属残余 ~100%」は
  **`spread_wide` (3 席) / `velocity_down` (aud_jpy) / `gbp_asia_flash_crash` (eur_gbp)**
  へ解決した。§7(a) 型の**供給**是正は引き続き不要 — 律速は下流である
- **次の決裁点は Rule 1** (autopilot は執行しない): 3 席の disposition =
  (a) 退役 / (b) ショック時スプレッドを許容する per-strategy cap の pre-reg
  (`weekend_gap_fade` の専用 cap 10.0p が同型の前例、
  modules/demo_trader.py:6241) / (c) 静的閾値を動的 (ATR 比 / 分位) 化。
  **いずれも 11.6 の magnitude 分布が溜まるまで選べない** ので、
  新 registry `ps-seat-spread-magnitude-readout` (期日 **2026-10-19**、
  計装 deploy + 4 週) で min/mean/max を読んでから起案する
- `ps-carveout-regate-post-172` (09-30) の凍結 look は**未消費** (本節は EV/WR/PnL を
  計算していない)。live N=6/10 で、供給が下流 gate に律速されている以上
  09-30 までの N≥10 到達は見込めない → 同エントリの
  「N<10 なら供給側の別問題として stale レビュー」分岐に入る見込みは §10 から変更なし
