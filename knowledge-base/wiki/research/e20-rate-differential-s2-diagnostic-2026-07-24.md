# E20 金利差方向バイアス — S2 診断 (rapid_edge_probe 実 series、2026-07-24)

> **rule:R3 (S2 探索診断)。これは診断であり判定ではない — live/tier 判断・昇格は禁止。**
> S3 pre-reg は別手続き (本診断は S3 を起案**しない**根拠の記録)。
> **S1 裁定**: [[e20-rate-differential-feasibility-2026-07-22]] (条件付き採用 / S2 GO、variant 2 本凍結)
> **ハーネス**: `tools/rapid_edge_probe.py` (PR #108) — テンプレ `rate_diff_breakout_template` の
> `__dummy_e20__` を実 series に差し替えて執行。探索窓 **2014-06-01〜2022-12-31 のみ**
> (全 8 run の max_entry ≤ 2022-12-29、OOS 2023+ 非接触を JSON で確認済み)。

---

## 1. データ準備 (S1 §3 台帳 → 実配線)

### 1a. rates パネル — `tools/e20_rates_ingest.py` (新規)

S1 §3 の keyless ソースから日次パネルを取得し、rapid_edge_probe series spec 用の
per-pair CSV を生成:

| 系列 | ソース | 実取得 |
|---|---|---|
| 政策金利 8/8 通貨 | BIS SDMX WS_CBPOL (D9) | 2013-01〜2026-07、31,914 行 |
| US 2y | MASSIVE `/fed/v1/treasury-yields` (D1) | 2013-01〜2026-07-22、3,389 行 |
| EUR 2y | ECB YC SR_2Y (D2) | 2013-01〜2026-07-22 |
| JPY 2y | MOF jgbcm_all.csv (D3、和暦+Shift-JIS parse) | 1974〜2026-06-30 |
| GBP | BOE IADB **IUDSNZC = 5y ZC 代用** (D4) | 2013-01〜2026-07-01 |
| CAD 2y | BoC Valet BD.CDN.2YR.DQ.YLD (D5) | 2013-01〜2026-07-22 |

- **⚠️ GBP テナー caveat**: BOE IADB に 2y ZC 系列は存在しない (2026-07-24 probe: IUDZNZC →
  HTML error)。S1 台帳 D4 の検証済み 5y ZC で代用 — mom variant の GBP レグのみ影響。
- シグナル CSV は**探索窓保護のため 2022-12-31 で物理切断**して commit
  (`knowledge-base/raw/bt-results/e20/e20_carry_level.csv` sha256 `0b03ea58…` /
  `e20_mom63_2y.csv` sha256 `e0306b61…`、2,609 営業日 × 13/7 ペア。
  生 snapshot sha256 は `e20_ingest_manifest.json`)。
- 正気検査済み: 2015-06 (AUD/NZD 高金利)、2019-06 (US>全通貨)、2022-11 (US 3.125 = 利上げ前
  band midpoint、JGB YCC ピン留め) が既知の金利体制と一致。carry 符号転換 0〜7 回/8.5y。
- look-ahead 排除: spec `lag_days=1` (営業日) — 値は翌営業日 bar から有効。

### 1b. 価格パネル — E15 凍結台帳と同一 (sha256 13/13 一致)

診断に使った 15m parquet は **[[e15-e7-event-modality-prereg-2026-07-18]] phase-0 OOS verdict
が凍結した data_ledger (`e15_phase0_oos_verdict.json`) と sha256 完全一致の 13 ペア版**
(e15-oos-20260722 worktree に現存するものを配線)。注意: main checkout の
`data/cache/massive/*_15m.parquet` は refresh cron により一部が短縮版に置換されており
(USD_JPY は 2024-05 以降のみ等)、**plain 名ファイルを無検査で研究に使ってはならない**
(部分 parquet 罠の変種)。coverage は 13/13 全ペア included。

## 2. 診断結果 — pooled EV_fric (pips、摩擦込み・financing 未算入)

variant は S1 §6-2 凍結の 2 本のみ。horizons = 96/480/960 bars (1d/5d/10d 保有)。
uncond = trigger なし bars hold (バイアス裸の IC/EV、§7 計測 1/2) /
breakout = 20-bar breakout × first_touch σ_h (user 仮説の形)。

### full 窓 2014-06〜2022-12 (13/7 ペア)

| run (spec_hash) | N(h480) | h96 (1d) | h480 (5d) | h960 (10d) | fold(h480/h960) | S3 目安 |
|---|---|---|---|---|---|---|
| carry_uncond (`a2b77cf9…`) | 2,857 | −2.51 | −3.04 | −4.54 | [−−+] / [−−+] | ⬜ 0/3 |
| carry_breakout (`eb5e22b1…`) | 2,739 | −4.13 | −7.24 | −5.76 | [−−−] / [−−+] | ⬜ 0/3 |
| mom63_uncond (`d85336f8…`) | 1,558 | −0.09 | **+4.78** | **+6.46** | **[−−+]** / [+−+] | ⬜ 0/3 |
| mom63_breakout (`91fbb4ab…`) | 1,498 | −1.01 | +0.35 | **+3.97** | [+−+] / [+−+] | ⬜ 0/3 |

### regime slice (§6-3 ガード 3、uncond/bars)

| run | h96 | h480 | h960 | N(h960) |
|---|---|---|---|---|
| carry pre2022 (収斂期) | −2.53 | −3.35 | −5.79 | 2,483 |
| carry 2022 (発散期) | −5.03 | −8.47 | +5.55 | 360 |
| mom63 pre2022 | −1.53 | +0.35 | +1.63 | 1,361 |
| mom63 2022 | −7.20 | −3.11 | **+21.42** | 190 |

**読み**:
- **carry**: 全 horizon 負、breakout 条件付けでさらに悪化。正セルは EUR_JPY +18.3 /
  USD_JPY +13.1 (全 fold 正) のみで、これは 2021–22 の JPY 減価ドリフトと不可分。
  古典 carry ペア AUD_JPY は **−4.82**。
- **mom63**: h480/h960 で pooled 正。ただし **h480 [−,−,+] = 平均正が fold 3
  (2020-10〜2022-12) 単独駆動**、h960 も fold 2 が負。2022 slice h960 +21.4 / pre2022 +1.6 の
  regime 濃度は S1 §5-4 の観測前警告どおり。cell 単位 IC 有意ゼロ (全 78 cell、
  best は GBP_USD h960 IC 0.105 p=0.119)。
- **テクニカル entry の寄与は負**: breakout 条件付けは両 variant で uncond より劣化
  (mom63 h480: +4.78 → +0.35)。「バイアス × テクニカル entry」という E20 の仮説形そのものが
  探索窓で価値を引いている。

## 3. 必須ガード 3 点 + financing overlay (`tools/e20_s2_guards.py`、S1 §6-3/§5-2)

| ガード | carry-level (13 ペア) | mom63_2y (7 ペア) | 判定 |
|---|---|---|---|
| **1. quintile 単調性** (within-pair Q → fwd5d pips) | Q1 **+7.3** / Q2 +6.9 / Q3 −2.0 / Q4 −2.9 / Q5 **−16.0** — **単調逆行** | Q1 +1.0 / **Q2 −12.9** / Q3 −1.0 / Q4 +4.3 / Q5 +4.2 — 非単調 (中抜け) | **両方 FAIL** |
| pooled Spearman IC (lag 1bd) | **−0.047 (p≈0, N=24,185)** — 機構と**逆符号で有意** | **+0.026 (p=0.003, N=13,051)** — 機構整合符号・微小 | carry 逆 / mom 整合だが微小 |
| **2. USD-neutrality** (\|net USD\|/gross) | 0.241 (cross 6/13) | 0.358 (cross 3/7) | D1 failure mode (0.54) 未満 — 通過 |
| **3. regime slice** | 年別: 2015 −15.8 … 2020 +7.2 / 2021 +9.7 — 正は 2020+ のみ | 2016 +20.0 / **2017 −14.6** / 2022 +16.9 — 年次分散大 | carry regime 依存 / mom 不安定 |
| **financing overlay** (政策金利差 ± markup 1%/yr) | pooled −0.32p/5d | pooled **−2.2p/5d・−4.4p/10d** (Δ63 方向はしばしば anti-carry) | S1 §5-2 の警告どおり mom に逆風 |

**financing 調整後 pooled EV (概算 overlay)**:
- carry: h480 **−3.4p** / h960 **−5.2p** — 負のまま
- mom63: h480 **+2.6p** / h960 **+2.1p** — **正が残る**が、その正は §2 のとおり
  fold 3 / 2022 に集中しており標本安定性がない

## 4. S2 exit 条件の裁定 (S1 §7 で観測前固定)

> §7: 「pooled IC が機構整合符号で有意水準に近い ∧ EV_net(k=5) > 0 ∧ 単調性 OK →
> S3 pre-reg 起案。**いずれか大きく欠ける → 棄却 doc 化 (research/ に append)**」

| 条件 | carry-level | mom63_2y |
|---|---|---|
| pooled IC 機構整合符号・有意近傍 | ❌ **逆符号で有意** (−0.047, p≈0) | ✅ +0.026 (p=0.003) — ただし効果量ほぼゼロ |
| EV_net(k=5) > 0 (financing 込み) | ❌ −3.4p | ✅ +2.6p |
| 単調性 OK | ❌ **単調逆行** | ❌ **非単調 (Q2 −12.9 の中抜け)** |
| (補助) harness S3 目安 (fold 全一致 ∧ N ∧ ペア比率) | 0/3 horizon | 0/3 horizon |

**→ 裁定: 両 variant とも §7 の ∧ 条件未達 = 既定の棄却分岐。本 doc がその「棄却 doc 化
(research/ append)」に当たる。E20 は S3 起案なしでクローズ。**

- **carry-level は 3/3 欠け** — 継続 claim は探索窓で**逆向きに**有意。widest-carry quintile が
  最弱 (−16p) という結果は、2014–22 の G10 では金利差が「継続」でなく「すでに織り込まれ
  た後の反転リスク」を運んでいたことを示す。carry 系の同型再提案は禁止。
- **mom63 は 1/3 欠け (単調性) + 補助不合格 3 点** (fold 不一致が EV 正 horizon で発生 /
  regime 集中 / cell IC 有意ゼロ)。§7 は ∧ 条件かつ本プロジェクトの探索→OOS 死屍累々
  (fold 2/3・regime 集中型は OOS で全滅の実績) を踏まえ、**S3 に進めない**。
  ただし carry と異なり探索窓で完全死ではないことを記録する — 将来 rates 系の新 S1 を
  起案する場合、**本診断の Q2 中抜けと fold 3 集中を機構で説明できる仮説に限る**。
- **再試行禁止 scope**: 凍結 2 variant (sign(政策金利差) / sign(Δ63bd 2y 差) × 日足バイアス
  ×テクニカル entry、保有 1–10d) の同型再提案。第 3 variant の後出しは S1 §6-2 で禁止済み。
- **階層注意**: これは S2 探索診断による棄却であり、OOS 検証を経た falsified 6 系統とは
  証拠階層が異なる (探索窓で S3 起案基準に届かないため OOS に進む根拠がない、という棄却)。
  OOS 窓 2023+ は**未接触のまま温存** (別 family が使える)。

## 5. 制約・限界 (再現性のための記録)

1. financing overlay は解析近似 (日次平均 × 保有日数、markup 1%/yr、週末 3 倍 rollover は
   calendar-day 換算で近似) — trade-level 算入は S3 に進む場合の必須実装項目だった (S1 §5-2)。
2. GBP レグ 5y ZC 代用 (§1a caveat)。
3. shadow 履歴との bias-agreement uplift (S1 §7 計測 4) は**未実施** — §7 exit が確定した
   ため追加計測の限界効用なしと判断 (読み取りのみの計測であり、将来必要なら独立に実行可)。
4. 初回 run は main の非正規 parquet (refresh cron 短縮版 + `_2014_2026` 別ビルド) を使って
   おり 9/13 coverage だった — E15 台帳一致版への差し替えで 13/13 に再実行済み
   (結論同方向、mom63 の EV_net(k=5) 符号のみ − → + に変化。**ビルド違いで Open 価格が
   最大 130 pips 乖離しており、データ台帳 sha256 突合を先にやる教訓を再確認**)。
5. 探索窓は 2014-06〜2022-12 のみ。regime slice の「2024+ unwind 期」は窓外で未検査。

## 位置づけ

- 実行: 2026-07-24、S2 R3 診断 (読み取り + 純研究 artifact のみ。live/shadow/Kelly/tier 不変更)。
- 成果物: `tools/e20_rates_ingest.py` / `tools/e20_s2_guards.py` / spec 8 本
  (`tools/rapid_probe_specs/e20_*.json`) / 診断 raw 16 ファイル
  (`raw/bt-results/rapid_probe_e20_*_2026_07_24.{md,json}`) /
  ガード `raw/bt-results/e20/e20_s2_guards_2026_07_24.json` / test +14 (オフライン)。
- **外部仮説パイプラインの現況への含意**: E20 (rates モダリティ第 1 案) は S2 棄却。
  供給ラインは E7 phase-1 (サプライズ、verdict 08-28) と E1 positioning (first look 10-15)
  が継続。rates データ配管 (`e20_rates_ingest`) は残置 — 次の rates 系仮説の S1→S2 は
  数時間で回せる。
