# commodity_cross_range_mr (台帳 #21) explore pre-reg — 観測前プロトコル凍結 (2026-08-05)

**状態**: 🔒 FROZEN (本コミットが凍結点 — 以後の定義・閾値変更禁止、逸脱は verdict 無効)
**family**: wave-6 EA-a。[[ea-landscape-sweep-2026-07-31]] §4.1 (GO 63/56)、G0 ✅ PASS 3/3 ([[commodity-cross-g0-rt-freeze-2026-08-03]]、freeze `981ae119`)。
**敵対的検証**: [[wave6-cc-mr-adversarial-verification-2026-08-05]] = **GO-WITH-CONDITIONS (21 条 / blocking 12 条)** — §8 が SSOT。本書 §10 に条件番号→解決の全マッピング。payload: `knowledge-base/raw/analysis/wave6-cc-mr-explore-candidates-2026-08-05.json`。
**ハーネス**: `tools/cc_mr_explore.py` (本コミット同梱、seed 20260805)。**測定は本コミット後のみ・two-pass 厳守**。
**台帳スロット**: #21 explore = **1/3 active** (G0 は枠非消費 / #20 PARK 非消費 / #22 forward LOCK 別枠 — 検証 §1.1-11 で確定)。

## §1 仮説と prior (正直申告)

**H1**: コモディティ三角クロス (AUD_NZD / AUD_CAD / NZD_CAD) の D1 スケール z-score 極値 onset を fade すると、+5 営業日ホライズンで正の摩擦・swap 調整後純移動を持つ。

**機構**: AU/NZ/CA は輸出構造・金利サイクルが共動するコモディティ経済でクロスは構造的レンジ。取る相手 = レンジ内ブレイク追随の trend-chaser。消えない理由 = capacity 極小 + negative-skew 保有プレミアム + レイテンシ非依存 (§4.1)。**外部 EA 実績は証拠価値ゼロと認定済み** — 根拠は構造 prior のみ。

**負の prior (§4.1 逐語継承)**: 遅い均衡回帰系は「方向は合うが弱い」死型 3 例 (ppp/quote-spread/round-number、実効果 +2.9〜+11.9p) の家系。RBA/RBNZ 政策デシンク局面 (2014-15 = explore 内, 2022-24 = OOS 内) でエッジが死ぬ regime 依存が実証済み (2024 の Waka ユーザー破綻)。AUDNZD MR は機関 RV デスクの定番でリテール残余のみの可能性。**家系前例サイズ (+3-6p) の効果は本設計では構造的に FAIL する — これは意図された retail-viability filter であって、9.1p での 80% power 推論ではない** (検証 §5.3 逐語)。

**erratum 訂正 (条件 21)**: §4.1 line 55「AUD_NZD は 2002 年以降 0.615-0.99」は NZD/AUD の逆数レンジ。実際の AUD_NZD は ~1.00-1.35。

## §2 データ凍結 (条件 1-8 の消化 — 全て実測済み)

| 項目 | 凍結値 / 実測 |
|---|---|
| bars | MASSIVE 1h、**open-time ラベル実証済み** (2015/2018/2021 の 7 月サンプル週: 日曜初バー 21:00 UTC = 17:00 NY EDT 開場、金曜末レギュラーバー 20:00 UTC。金曜 21:00+ UTC の閉場後プリントは週末 trading day に写像され除外・件数報告) |
| 被覆 (条件 1) | 3/3 ペア first 1h bar = **2013-01-13 22:00 UTC** ≤ 2013-03-01 assert PASS。`fetch_massive_data.py --days 4950` フル再取得 (2026-08-05、fresh full fetch)。**merge_never_shorten (PR #138) claim の訂正 (条件 21)**: 08-05 fetch は素の全置換で当該ガード不在 — 本凍結は代わりに sha256 pin + row-count assert で drift を封鎖 |
| 穴修復 (条件 2) | `tools/cc_mr_gap_backfill.py` (本コミット同梱) = OANDA v20 mid backfill (07-29 手法継承、既存行不変 assert / era pattern guard / .bak / audit 来歴)。**窓 2019-09-14..2019-10-06 + 2020-10-13..2021-01-03 (実測穴に合わせ延長)**。追加行: AUD_NZD +792 / AUD_CAD +41 / NZD_CAD +192+1,152。**再 census assert PASS: explore 窓の >72h 週内 gap = 年末休場 (12-22..1-03) のみ、最大 79h** — 全件 census は audit.json 参照 |
| despike (条件 3) | flag = (H−L) > **8× centered rolling-49 median (min_periods 25)**。flag バーの H/L は MFE/MAE 極値から除外。D1 close / entry / exit を供給する flag バーは pinned CSV (`despike_replacements_2026-08-05.csv`) の OANDA mid close を常用 (判定閾値なしの決定論形)、CSV 不在なら同日前バー close (degraded flag)、それも無ければ void。**census (explore 窓)**: AUD_NZD 36 / AUD_CAD 21 / NZD_CAD 15 バー、うち D1-close 供給 = **0 件**、entry 時刻 = **2 件** (AUD_CAD 2015-11-12 / 2015-12-10、両方 OANDA と 0.5p 以内一致 = 実相場変動、置換は no-op 同然) |
| D1 再構築 (条件 4) | trading day T = close-time ∈ (NY17:00\_{T−1}, NY17:00\_T]、境界は **America/New_York zoneinfo** (固定 21/22:00 UTC 禁止)。D1 close = 境界一致バー (close-time = 17:00 NY ちょうど)、なければ最終バー + `degraded_close` flag、最終バー close が 14:00 NY 以前 (境界 3h 超前) なら day void。D1 H/L = 構成バー max/min。週末ラベル bar 除外。**assert PASS: bars/week median = 5.0、曜日分布一様 (share 0.199-0.201)、構成バー数 p50 = 24** |
| 横断 assert (条件 5) | 単調 ✓ / 重複 0 ✓ / 三角残差 \|log AUD_CAD − log AUD_NZD − log NZD_CAD\| D1 日次: p50 0.053%、p99 0.54% (despike 前実測; close は last-print 時刻差起因のタイミングノイズを含む — ハーネス QA が despike 後値を報告)。3 ペアの三角依存 = pooled 実効自由度 ~2 の実測 pin として §6 block 設計の根拠 |
| sha256 pin (条件 6) | `data_freeze_manifest_2026-08-05.json` (本コミット同梱): 3 parquets + 3 audit.json + `e20_carry_level.csv` + cc-g0-rt 2026-08-03/04 snapshots + despike CSV。**ハーネスはロード時に sha256 + row-count (90,959 / 84,620 / 84,572) を assert = フル parquet 強制** (worktree 部分 parquet 罠対策)。測定は本 freeze commit 後のみ |
| P-10 (条件 7) | ハーネスは `columns=["Open","High","Low","Close"]` でロードし **Volume/vwap 非読取をコード assert** (E12 ban 2027-02-05 まで) |
| 照合順序 (条件 8) | 独立ソース event 件数スポットチェック (≥1 ペア、±10%) = **pass-1 で可**。pooled 符号の照合 = **pass-2 解錠後のみ** (gate A 前の符号 peek は forward look で禁止) |

## §3 イベント定義 (全 DoF 凍結 — variant A、grid 探索禁止)

| 要素 | 凍結値 |
|---|---|
| variant | **PRIMARY = A (D1 z-score fade) 単独**。**variant B (H1 range-percentile + D1 trend veto) = declared NON-TESTED** (DoF 厳密増、variant scan 禁止) — §9 FAIL クローズ範囲に B を明示的に含む |
| signal | z(t) = (close_D1(t) − SMA200_D1) / std60_D1。SMA200 = 直前 200 D1 close の単純平均 (**当日バー除外**)、std60 = 直前 60 D1 close の標本標準偏差 (**ddof=1、当日バー除外**)。std60 < 1e-6 → バー void |
| warmup | バー適格 = SMA200/std60/z(t)/z(t−1) 全計算可能。**per-pair first-eligible = 2013-10-22 (3 ペアとも、導出)** → explore 窓 2014-01-01 開始は全域適格 = **被覆 option (a) 成立、gate F はリスケールなしの原型** |
| event | **ONSET crossing のみ**: \|z(t)\| ≥ 2.0 ∧ \|z(t−1)\| < 2.0。方向 = fade (z ≥ +2.0 → SHORT / z ≤ −2.0 → LONG)。one event per excursion (再エントリは \|z\| < 2.0 のバー通過後のみ)。**端点規則 (条件 10)**: 系列先頭 z(t−1) 未定義 → onset 非成立 (件数報告) / excursion 内符号反転 (+2→−2 が \|z\|<2 を経ない) は新イベントを作らない (件数報告、期待 ≈0) / z(t−1)→z(t) が >5 営業日 gap を跨ぐ場合 onset void (件数報告) |
| hold-collision (条件 11) | **skip 禁止 — 全 onset を測定** (skip は事前イベント条件付けでクラスタ stress 期を間引く PASS 方向バイアス — 検証 §4.2、全 lens 一致)。skip 版 (live-feasibility) は診断のみ。overlap share + 同週 cross-pair co-fire share を報告義務 |
| entry (条件 9) | **primary = 19:00 America/New_York バー close** (= NY17:00 close の 2h 後、夏 23:00 / 冬 00:00 UTC ラベル)。実装 = 各 NY-evening の最初の open-hour ∈ [19,22] NY バー (evening grid、19:00 欠損時の決定論 fallback; 実 entry 時刻分布を報告)。onset 日の evening node が存在しなければ次 evening、**node 日 > onset+4 暦日 → void (件数報告)** |
| 金曜規則 (条件 10) | 金曜 D1 close の onset → **次営業 evening = 日曜 19:00 NY バー (= 月曜 trading day)** に自動繰越 (evening grid の自然な次 node)。遅延日数を per-event 報告。「holiday なら skip」条項は**削除** (金曜イベント全滅 + 曜日選択バイアスの欠陥だった — 検証 §1.2-2) |
| horizons | PRIMARY = fade 方向純移動 @ **+5 evening-grid nodes** (entry close → exit close、H_cal = 実暦日数を per-event 記録 — swap 算入用)。diagnostic = +10 nodes、MFE/MAE (5d 窓、despike 済 1h H/L)。**D1 close-to-close 版は診断のみ** (執行遅延を隠すため primary 不可 — 検証 Q2 裁定)。他ホライズンなし |
| 窓 | **explore = onset D1 date ∈ 2014-01-01..2021-12-31 のみ (本セッション)** / OOS = 2022-01-01..2026-06-30 (単一接触、explore PASS + OOS pre-reg + user 承認後のみ)。12 月末 onset のホライズン完了は 2022-01-31 close まで許容 — これは explore イベントの outcome 完了であって OOS シグナル接触ではない (on-record) |
| pairs | AUD_NZD, AUD_CAD, NZD_CAD (pip = 1e-4) |

**entry の on-record 偏差 (条件 9)**: catalog #21 行の字面は「執行 23:00 UTC 凍結」(出典訂正 (条件 21): この文言の出典は catalog #21 行であり、G0 freeze doc §4 は「hourly map を entry 時刻特定に使う」としか言っていない)。しかし固定 23:00 UTC は **DST で冬に毒窓 (rollover 帯が ~22:00-23:59 UTC へシフト) 内に入る**。G0 の 60 営業日証跡 (5-8 月) は 100% 夏時間で、「23:00 UTC」の実体は「NY close + 2h」だった — よって NY アンカー形 (19:00 NY) が原意の DST-safe 表現である (検証 Q2 裁定)。**hour-23 の実数 (条件 21)**: p50 2.7-2.9p / **p75 2.9-3.1p** (NZD_CAD は 2.9-3.1p 帯の上端)。**冬の 23:00 UTC スプレッドは未測定** — 本測定 (歴史 mid) には影響しないが、**将来の live 化 (本測定の外) は冬スプレッド再測定を必須とする** (honesty 条項)。固定 23:00 UTC (非金曜) と 00:00 UTC 翌日は knife-edge に残置。

## §4 接触順序 (two-pass、#19 §4 パターン)

1. **pass-1**: `date|pair|side|z|d1_close|entry_ts|entry_price|mfe5` のみ export (net 系ゼロ)。**gate A 判定 + pooled N/blocks + per-pair 無条件 5-node \|Δclose\| 分散 (event 非依存、despike 後) + MDE 再計算をコミット**してから pass-2 解錠。
2. **pass-2** (gate A 生存ペアのみ): `net5|net10|mae5` + gates C-G + verdict。stats はハーネス同梱 (seed 20260805)。
3. gate A で生存 <2 ペア → **family KILL** (pass-2 に進まない)。

## §5 統計 gates (凍結)

- **Gate A (headroom)**: per-pair fade 方向 MFE(5d) p50 ≥ **10× G0 stressed_RT** = AUD_NZD 38.0p / AUD_CAD 37.0p / NZD_CAD 39.0p。不通過ペアは凍結時除外 (pass-1 時点のみ)。生存 <2 → family KILL。
- **Gate B (power、条件 15)**: **events ≥ 120 かつ blocks (§6 定義、event を含む 2-ISO-週 block) ≥ 50**。どちらか未達 → verdict = **UNDERPOWERED** (PASS/FAIL ではない)。閾値いじり禁止。
- **Gate C (primary、条件 12)**: pooled (生存ペア・両サイド) mean fade net5d > 0、**block sign-flip permutation (§6) の片側 p < 0.05 (単独 family m=1)**。
- **Gate D (stressed-net、条件 18)**: pooled mean [net5d + swap_pips − stressed_RT_pair] > 0 を **markup adverse 端で要求** (§7)。point/favorable は感度併記 (非拘束)。
- **Gate E (集中)**: S_w = block w の符号付き net5d 和として、**max_w \|S_w\| / Σ_w \|S_w\| ≤ 0.50** (分母凍結 — pooled net 分母は 0 近傍発散のため禁止)。
- **Gate F (一貫性、条件 17)**: explore 年次 (onset 年) 符号 ≥ **6/8** 正 **+ LOYO 8/8 正** (被覆 option (a) 成立につき原型維持)。**事前記録: pooled ~19 events/yr で真の +8p エッジでも P(≥6/8) ≈ 0.47 — gate F 単独の false-kill 率 ≈50%。それでも binding (#19 は 5/8 で死んだ — 今緩めるのは gate-shopping)。C-PASS/F-FAIL は「regime-inconsistent の FAIL close」で再審禁止**。2014-15 デシンク副窓 mean は診断報告。
- **Gate G (coherence、条件 16 — binding)**: (i) per-pair pooled mean 符号 正 ≥ 2/3 (生存ペア比)。(ii) **サイド kill**: 片サイド (L/S pooled) mean < 0 **∧** 片側 block-perm p(against) < **0.10** → family FAIL。サイド N < 30 は kill 発火不能 (flag 報告; 負ノイズサイドのみなら PASS に「one-sided effect」注記 → OOS pre-reg へ逐語継承)。
- **knife-edge (全 gate PASS 後のみ、選択不使用)**: z {1.75, 2.25} / SMA {160, 240} / std {45, 75} / entry {固定 23:00 UTC 同日 (非金曜), 00:00 UTC 翌日} / block {1-ISO-週}。**いずれかで primary 符号反転 → FAIL**。std ddof=1、SMA/std 当日バー除外は全変種共通。
- verdict: 全 binding gate 通過 = **PASS** → §9。gate B 未達 = **UNDERPOWERED**。他 = **FAIL クローズ** (OOS 非接触)。**閾値の事後変更禁止**。

**§4.1 Bonferroni 行の on-record 修正 (条件 12)**: §4.1 逐語「共通: single-entry のみ (grid/averaging は評価対象外)、**3 ペア × 2 サイド Bonferroni**、explore/OOS 時分割、event-block bootstrap、D1 曜日ラベル罠対策」。6-cell Bonferroni は棄却する: N=150 均等割で per-cell N=25、α'=0.05/6 → per-cell MDE = 3.236×sd/5 = **29.1p (sd45) / 38.8p (sd60)** — 家系実測効果の 3-6 倍 = 保証された UNDERPOWERED 非テスト。さらに 6 cell は三角恒等 + 共有週で非独立 = /6 自体が誤較正。同 §4.1 内の「pre-reg 起案時に primary 1 本へ凍結」と矛盾する pre-prereg スケッチと認定 (検証 §5.1、5 lens 一致)。**補償 (これが崩れたら本修正は失効)**: (a) gate G binding 化 (上記)。(b) **claim 範囲 = family-pooled のみに恒久限定 — per-pair / per-side の claim は結果如何によらず禁止**。(c) 本 verdict 前に他の wave-6 explore family が起動した場合は **BH q=0.10 で分母合流** (vix #7 knife-edge 死の再演防止)。

## §6 block 構造と permutation (条件 13/14 — 完全凍結)

- **block = 固定 2-ISO-週 [2k−1, 2k]** (block key = (ISO 年, ⌈ISO 週/2⌉)、週 53 は単独 block)。割当 = **onset D1 日付**。**全ペア pool、block 単位 sign-flip (1 flip = 当該 block の全ペア全イベントに同時適用 — 三角依存のため per-pair block 禁止)**。
- 根拠: 5 営業日 = 7 暦日で**全**イベントの return 窓が ISO 週境界を跨ぐ — #19 の 3d で成立した 1-週近似は 5d では構造的に破綻 (検証 §5.2)。**#19 前例からの deviation-strengthening として記録**。1-ISO-週版は knife-edge、診断併記 (選択不使用)。
- **permutation 仕様**: numpy `default_rng(20260805)`、B = 10,000、**p = (1 + #{perm ≥ obs}) / (1 + B)**、統計量 = pooled mean net5d。gate G サイドテストは同一 block 構造 + 派生 seed **20260806 (L) / 20260807 (S)** (p(against) = (1 + #{perm ≤ obs})/(1+B))。knife-edge は seed 20260805 再利用。

**MDE 表の公表 (条件 15)** — MDE = (1.645+0.842)×sd/√N (片側 α=0.05, power 0.8):

| sd (p) | N=120 | N=150 | blocks=50 (クラスタ上限) | blocks=90 |
|---|---|---|---|---|
| 45 | 10.2 | 9.1 | 15.8 | 11.8 |
| 60 | 13.6 | 12.2 | 21.1 | 15.7 |
| 80 | 18.2 | 16.3 | 28.1 | 21.0 |

blocks 列 = 級内相関 1 の worst case (MDE = 2.487×sd/√blocks)。**draft の sd=45p / MDE 9.1p は破棄** — 検証実測 robust σ_5d ≈ 74-86p → 正直 MDE(150) ≈ **12-17p**。pass-1 が凍結データの despike 後無条件 5-node 分散から MDE を再計算し report に記載する (gate 閾値は変えない)。

## §7 摩擦・swap (条件 18 — blocking)

- **stressed_RT (G0 凍結値)**: AUD_NZD 3.80 / AUD_CAD 3.70 / NZD_CAD 3.90p (freeze `981ae119`)。
- **swap 3 式 (三重検証済み、e20 csv 全列 base−quote %/yr、数値検証: 2013-01-02 AUD_USD = 2.875 = RBA 3.00 − Fed 0.125)**:
  `d_AUD_NZD = col_AUD_USD − col_NZD_USD` / `d_AUD_CAD = col_AUD_USD + col_USD_CAD` / `d_NZD_CAD = col_NZD_USD + col_USD_CAD`
- **per-event × per-side accrual (pooled スカラー廃止)**: `swap_pips = (rate_used/100) × (H_cal/365) × S_entry/1e-4`、rate_used = **worse-of( dir×d(t_entry) − m, snapshot_leg(pair, side) )** (負 = コスト)。dir = +1 (fade LONG) / −1 (fade SHORT)。H_cal = per-event 実暦日数。
- **snapshot legs (%/yr、有効スナップショット横断の worst、凍結)**: AUD_NZD L +0.75 / S −2.92、AUD_CAD L +1.07 / S −3.22、NZD_CAD L −0.82 / S −1.62 (**NZD_CAD は両サイド負 carry を実測確認 — pooled スカラー廃止の根拠**)。
- **0/0 = MISSING**: longRate=shortRate=0 のスナップショット (2026-08-03 の AUD_NZD/AUD_CAD) は ingest artifact = 棄却、ゼロコストの証拠として使用禁止。
- **markup 較正と on-record 偏差**: 条件 18 の字面は「per pair ≥10 本の非異常日次スナップショットから較正」。**凍結時点の非異常スナップショットは AUD_NZD/AUD_CAD 各 1 本・NZD_CAD 2 本しか物理的に存在しない** (収集開始 2026-08-03、Render cron 日次)。健全に ≥10 本較正はできないため、**より保守的な代替で凍結する**: m_point = 実測 implied (AUD_NZD 1.085 / AUD_CAD 1.075 / NZD_CAD 1.155 %/yr) を報告値とし、**gate D binding は per-pair adverse 端 m_adverse = max(1.5×m_point, 1.65) = AUD_NZD 1.65 / AUD_CAD 1.65 / NZD_CAD 1.73 %/yr で PASS を要求** (条件の感度帯 [0.55, 1.65] の adverse 端以上)。0/0 再発 >20% ペアへの m=1.65 適用規則は AUD_NZD/AUD_CAD (0/0 1/2 日) に既に効いている形。**OOS pre-reg 時に ≥10 本で再較正を義務付け** (それまで cron 蓄積継続)、再較正 1.5×m_point が凍結 adverse を超える場合は大きい方を使う。favorable 端 0.55%/yr は感度併記のみ。
- **fade-SHORT 脚 (AUD_NZD/AUD_CAD S) は ≈2.9-3.2%/yr ≈ 5-6p/5td 保有 — 正直 MDE と同オーダーの実 drag** (事前記録)。
- **E20 ファイアウォール (条件 17 の一部)**: rates の使用は outcome join 後の gate D 減算コストのみ (ハーネス構造で分離 — signal/event builder は e20 に非アクセス)。イベント選択・方向・サイズのいかなる rate 条件付けも E20 隣接違反。
- **OOS swap ソースの事前宣言**: `e20_carry_level.csv` は 2022-12-30 終端 (explore 完全被覆・OOS は不足)。OOS 側は **`tools/e20_rates_ingest.py` の BIS 再 ingest 拡張**で 2023+ を補完する (宣言のみ — 実行は OOS touch 前、look 問題なし)。

## §8 ban 隣接差分節 (条件 19/20 — blocking)

- **L-d `d1_regression_channel_reversion` (最近接 killed neighbor、2026-07-31 triage KILL)**: catalog line 115 =「ban scope 裁定 on-record: 06-25 決定は『この特徴量セット・チャネル定義では』と自己 scope + 別 lookback を IC-first で明示許容 → identity-BANNED ではなく ADJACENT。kill 理由 = 同一幾何が 15m massive-N で決定的 null + 最近傍死型 3/3 + price_shock family との低独立性 + スロット希少 (power は足りる — kill 理由ではないと正直記録)。再入場経路なし (同構造)。将来の並行線提案は決定文条項 (回帰±2σ/swing平行以外 + IC-first + 明示差分節) に従う」([[level-family-adversarial-verification-2026-07-31|level-family 検証]] 系譜)。**差分**: 本 family の anchor = **SMA200/std60 (回帰勾配なし・swing fit なし)** = L-d 裁定の許容空間 (「回帰±2σ/swing 平行以外」) 内。universe = 全チャネル測定 (6 majors × 15m) に**不在**の 3 コモディティクロス × D1 × 5d。**caveat on-record**: レンジ相場では regression-200 センターラインは SMA200 に収束する — 幾何の隣接性は否定しない。L-d は triage kill であって測定 kill ではなく (slot+prior 理由)、**この estimand (D1 z-fade × commodity cross × 5d) に測定済み null は存在しない** (検証 §3.1 裁定: ADJACENT, not re-skin)。**IC-first 字義履行**: 非拘束 Spearman IC(z, fwd5d) を explore report に記載し、06-25 決定文条項の discharge と宣言する (選択不使用・binding は gate C のみ)。
- **#3 回帰/swing チャネル (06-25 falsified)**: その estimand = チャネル幾何 × 15m 連続スキャン × 1-12h。本件 = 固定窓 z-score × D1 onset × 5d。ADJACENT、identity ではない。
- **#14 ppp (falsified)**: 月次 5y-z マクロアンカー × 21-63bd — anchor/頻度/ホライズン全て別。家系 resemblance は負の prior として §1 に継承済み (ban 違反ではない)。
- **E20 (凍結)**: ban 範囲 = rate-SIGNAL 2 変種 + carry 同型。v1 シグナルは純価格、rates は §7 の減算コストのみ (ソースコード監査済み、weekend_gap stressed-net 前例と同型) = 非違反。
- **bb_rsi_reversion (T10 KILL)**: intraday BB+RSI で scope 別 — 注記のみ。
- **session-mr-cross-wave1 (05-11 BLOCKED_DATA)**: 全 cell N=0 verdict 不在、supersession 適法 (別 estimand)。
- **price_shock (live family)**: H1 shock reversion (速い単発 bar) vs 遅い 200d anchor 極値 — event 週重複は診断報告 (期待低)。
- **#22 / #20 / E7 / E1 / E12 / MoF**: 非干渉 (#21 は shadow P&L 非接触・外部価格のみ。#22 P-10 ban は gate×outcome 計算限定で非干渉)。

## §9 分岐 (凍結) と接触規律

- **FAIL / UNDERPOWERED** → 台帳 verdict + report + KB 永続化、OOS 非接触保存。**FAIL 時クローズ範囲 (条件 20、事前凍結)**: 「**slow location-anchor (mean / percentile / regression) band fade × multi-day × AUD_NZD/AUD_CAD/NZD_CAD、全 anchor 着せ替えを含む — variant B (H1 range-percentile + D1 trend veto) を明示的に含む**」。B の復活経路 = 新 family + 事前差分節 + 新規敵対的検証のみ (L-e 条件付きクローズの鏡像)。
- **PASS** → **OOS pre-reg DRAFT 起案 → 停止、user 最終承認待ち**。OOS 設計事前宣言: 同定義・2022-01-01..2026-06-30 (2022-24 デシンク敵対窓を構造的に含む)・floor = explore 比例 (N ≥ 70 かつ blocks ≥ 30)・同 gates + swap 再較正 (≥10 snapshots) + 冬 DST 窓の entry 時刻検証。**PASS ≠ live。live 昇格は R1 全段 + 冬スプレッド再測定が別途必要。live/shadow 構成変更ゼロ。**
- **接触規律**: 測定は本 freeze commit 後のみ。pass-1 → コミット → pass-2。OOS 2022+ シグナル非接触 (ハーネスに OOS モード自体が存在しない)。TV/独立ソース照合は §2 の順序。
- **並行セッション競合の記録**: 本凍結と同日、別セッション (`勝てるEAのエッジ探索`) が variant B primary + 固定 23:00 UTC entry の未コミット draft (`.worktrees/ccrmr-prereg`) を並行構築していた。検証 blocking 条件 (variant A primary / B NON-TESTED / 条件 9) に抵触するため停止要請済み (#22 first-to-main 前例)。**当該 draft の成果物は本凍結に不使用・B の NON-TESTED 宣言は不変**。
- 動機記録 (R1): データ駆動 — G0 clean PASS 3/3 + 憲章既定の次手 + 敵対的検証 GO-WITH-CONDITIONS + user 委任 (2026-07-08 ミッション)。「安価で正直にゲートされた kill attempt」(検証 §10) として執行。

## §10 敵対的検証 21 条件 → 解決マッピング

| 条件 | [B] | 解決 |
|---|---|---|
| 1 被覆修復 (first bar ≤2013-03-01) | B | §2 (実測 2013-01-13、3/3 PASS、option (a)) |
| 2 穴修復 (窓延長 backfill) | B | §2 (`cc_mr_gap_backfill.py`、再 census PASS) |
| 3 despike 規則凍結 | B | §2 (census + pinned CSV + 決定論置換) |
| 4 D1 再構築規約再宣言 | B | §2 (zoneinfo NY17、ラベル語義実証、assert PASS) |
| 5 QA 横断 assert | — | §2 (単調/重複/三角残差) |
| 6 sha256 pin 一式 + フル parquet | B | §2 (manifest + ロード時 assert) |
| 7 P-10 hygiene | — | §2 (コード assert) |
| 8 TV 照合順序 | — | §2/§9 (件数 = pass-1 / 符号 = pass-2 後) |
| 9 entry 19:00 NY + 偏差 on-record | B | §3 (偏差節 + 冬未測定 honesty + live 化条件) |
| 10 金曜規則 + 端点規則 | B | §3 |
| 11 全 onset 測定 (skip 禁止) | B | §3 (+ skip 版診断、overlap/co-fire 報告) |
| 12 pooled m=1 + §4.1 逐語修正 + 補償 | B | §5 (Bonferroni 修正節、claim 恒久限定、BH q=0.10 条項) |
| 13 2-ISO-週 block primary | B | §6 |
| 14 permutation 完全凍結 | — | §6 (seed/B/p 式/派生 seed/gate E 分母) |
| 15 power 正直化 (gate B + MDE 表) | B | §5/§6 (events≥120 ∧ blocks≥50、9.1p/sd45 破棄) |
| 16 gate G binding 形 | — | §5 (≥2/3 + サイド kill p<0.10、N<30 発火不能) |
| 17 gate F 維持 + false-kill 事前記録 | — | §5 (option (a) 原型、≈50% 事前記録、再審禁止) |
| 18 swap 凍結一式 | B | §7 (3 式 + worse-of + 0/0=MISSING + adverse 端 + E20 firewall + OOS ソース宣言 + **≥10 本較正不能の保守的代替を on-record**) |
| 19 L-d 差分節 + IC-first 履行 | B | §8 |
| 20 FAIL クローズ範囲 (variant B 含む) | B | §9 |
| 21 記載修正 4 件 | — | §1 (erratum) / §3 (23:00 出典 + hour-23 実数) / §2 (merge_never_shorten 訂正) |

**コミット規律**: 本文書 + `tools/cc_mr_explore.py` + `tools/cc_mr_gap_backfill.py` + data manifest + despike CSV + 検証 report + payload を**同一コミットで凍結 (rule:R1)**。測定はコミット後開始。
