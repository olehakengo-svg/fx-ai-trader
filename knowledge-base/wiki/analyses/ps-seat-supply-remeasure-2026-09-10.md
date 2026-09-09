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
