# round_number_major_level (台帳 #19) explore pre-reg — 観測前プロトコル凍結 (2026-07-31)

**状態**: 🔒 FROZEN (本コミットが凍結点 — 以後の定義・閾値変更禁止、逸脱は verdict 無効)
**family**: wave-4 level-family survivor L-b。敵対的検証 12 条件: [[level-family-adversarial-verification-2026-07-31]] §4 — 解決マッピングは §9。
**先行 wave**: #18 level_failed_break_d1 は explore FAIL クローズ済み ([[level-failed-break-d1-explore-prereg-2026-07-31]] / `reports/level-fb-d1-explore-2026-07-31.md`) — 実行順序 (L-a verdict 後に単独 wave) を遵守。

## §1 仮説と prior (正直申告)

**H1**: メジャーラウンドナンバー (JPY クロス整数 00 / USD-quoted 0.0100 grid) への **fresh approach**
(20 営業日以上未接触後の初回タッチ) の後、価格は接近方向から**反転** (レベルから離れる方向へ) し、
3 営業日ホライズンで正の純移動を持つ。

**機構**: Osler (2003, J. Finance) — **実注文データ**で TP 指値はラウンドナンバー**上**に、SL は**すぐ外側**に
クラスタする。指値クラスタ = 反発圧力。本 set で唯一、機構の一次証拠が価格系列の外にある候補。
**限界**: Osler 証拠は intraday — D1×multi-day への外挿は untested。McLean-Pontiff 減衰 ~50%。
prior = medium (上限)。Osler 予測 2 (貫通後の stop cascade 加速) は**本 family で検定しない**
(別 family 候補として台帳注記のみ — 事後の目的変更を封鎖)。

## §2 イベント定義 (全 DoF 凍結 — grid 探索禁止)

| 要素 | 凍結値 |
|---|---|
| bars | TV OANDA D1、trading-day ラベル = bar close 日 (America/New_York) — #18 QA 修正済み規約を無変更継承。土日 bar 除外、bars/week≈5 assert |
| level grid | *JPY ペア: **1.00 刻み整数 00** (例 150.00)。*USD ペア: **0.0100 刻み** (例 1.1000)。**50-levels (0.50/0.0050) は declared non-tested** (variant scan 禁止) |
| touch | D1 の low ≤ L ≤ high (wick 接触を含む) |
| fresh | 同一レベル L の直前タッチから **>20 営業 bar** (未タッチ含む)。レジストリは全タッチで更新 (fresh 判定は当日タッチ前の状態) |
| event | 当日 fresh タッチされた level のうち **前日 close に最近接の 1 本のみ** (1 pair 1 日 1 event)。前日 close == L は skip |
| direction | 前日 close < L (下から接近) → **SHORT** (反転=下落)。前日 close > L → **LONG**。reversal 片側仮説 |
| entry proxy | event bar close |
| horizons | 反転方向純移動 {1, 3, 5} D1 bars。**PRIMARY = 3d の 1 本**、他は diagnostic |
| pairs | USD_JPY, EUR_JPY, AUD_JPY, EUR_USD, GBP_USD, AUD_USD (6) |
| 窓 | explore = 2014-01-01〜2021-12-31 (レジストリは全履歴で走行) / OOS = 2022-01-01〜2026-06-30 — 本セッションでは explore のみ |

## §3 測定器と検触 (#18 と同一規約)

- TV per-event table export (`bt-results/tv-overlays/round_number_export.pine`)、two-pass (§4)。
- **coverage assert**: per-pair D1 first bar ≤ 2014-01-01、不通過 = data-blocked (事後緩和禁止)。
- feed QA: #18 で検証済みの trading-day ラベル規約 + wknd=0 + bars/week assert を無変更継承。
- cross-check: #18 で測定器系統 (TV export + NY 境界) の妥当性は検証済み — 本 family では
  イベント数オーダーの目視整合のみ (乖離兆候があれば 1h フル版で #18 同型の再照合)。
- 測定のみ (strategy 実装は explore gates 通過後)。

## §4 接触順序 (two-pass)

1. **pass-1**: `date|side|level|entry|mfe3` のみ export → Gate A 判定 → 不通過ペアを凍結時除外。
2. **pass-2**: 生存ペアのみ `date|side|level|entry|net1|net3|net5|mfe3|mae3`。
   stats = `tools/round_number_explore_stats.py` (seed 20260731、副作用なし)。

## §5 統計 (凍結)

- **Gate A (headroom)**: per-pair 反転方向 MFE(3d) p50 ≥ **10× RT** (USD_JPY 2.14 / EUR_JPY 2.50 /
  AUD_JPY 3.00 / EUR_USD 2.00 / GBP_USD 4.53 / AUD_USD 2.50p、floor 1.30p 感度併記)。生存 <3 ペア → family KILL。
- **Gate B (power floor)**: 想定 6-15 event/pair/年 → pooled explore 期待 288-720。per-event sd ≈ 30p (3d) で
  N=200 の MDE (片側 α=0.05, power 0.8) ≈ 5.3p。**floor = 200** (未満 → UNDERPOWERED verdict)。
- **Gate C (primary)**: pooled 6-pair (生存ペア)・h=3d・反転方向純移動の平均 > 0、ISO 週 event-block
  sign-flip permutation (10,000 draws、seed 20260731) の**片側 p < 0.05** (単独 family m=1)。実効週数併記。
- **Gate D (net EV)**: pooled mean − 実ペア加重 RT − swap 純額 > 0。swap = e20 歴史 proxy
  (`e20_carry_level.csv` イベント日参照、hold 3 営業日 = 暦 4.2 日、markup 0.50%/年、感度 ±50%)。
  RT floor 1.30p 感度併記。
- **Gate E (集中)**: 最大単一 ISO 週寄与 ≤ 50%。
- **Gate F (一貫性)**: explore 年次符号 ≥6/8 正 + LOYO 全 8 通り正。
- **介入ガード (条件 7)**: explore 窓 2014-2021 の USD_JPY 介入ゼロを `data/external/mof_interventions.csv` で
  assert (機械)。OOS 執行時 (別途 pre-reg) は介入週重複 share 診断 + LOYO 2022/2024 除外検査を必須とする。
- **knife-edge 検査 (全 gate 通過時のみ、選択に使わない)**: 3 変種 = fresh 窓 {15, 25} 営業 bar /
  touch 定義 close-touch (close が L を跨ぐ) 化。**いずれかで primary 符号反転 → FAIL**。
- verdict: 全 gate 通過 = explore PASS → §8。不通過 = FAIL クローズ (OOS 非接触)。閾値の事後変更禁止。

## §6 #18 とのイベント重複診断 (条件 11)

pair-ISO週 単位で #18 イベント (`level-fb-d1-pass2-2026-07-31.json`) との重複 share を報告。
**>30% なら台帳に部分依存を注記** (BH 分母は変えない、「独立 2 家系」と誇張しない)。

## §7 rnb_usdjpy reconciliation (条件 8)

- 本 family は**歴史測定のみ** — rnb_usdjpy shadow (live-forward 収集、歴史主張なし) と重複しない。
- rnb shadow の trade データは本 explore/OOS に**一切使用しない**。
- PASS 時は本結果を rnb_usdjpy トラックの設計入力として扱う (tier action は R1 別途)。

## §8 分岐 (凍結) と接触規律

- **FAIL / UNDERPOWERED** → 台帳 verdict + report + KB 永続化、OOS 非接触保存。wave-4 は全 family 決着 →
  セッションサマリで「水平線・平行線 差分空間の残存」を総括して終了。
- **PASS** → **OOS pre-reg DRAFT 起案 → 停止、user 最終承認待ち** (セッション規律 #6)。OOS 設計事前宣言:
  同定義・2022-01-01〜2026-06-30・floor N ≥ 90・同 gates + 介入週診断 (§5)。
- **PASS ≠ live**。live 昇格は R1 全段が別途必要。live/shadow 構成変更ゼロ。
- 動機記録: データ駆動 (Osler 実注文根拠 + 非 swing レベル生成の差分空間 + user 委任)。

## §9 敵対的検証 12 条件 → 解決マッピング

| 条件 | 解決 |
|---|---|
| 1 level grid 凍結 + 50-levels non-tested | §2 |
| 2 touch/approach/方向 + 同日複数 level 規則 | §2 (最近接 1 本、1 pair 1 日 1 event) |
| 3 primary 1 本 + acceleration 非検定宣言 | §1/§5 Gate C |
| 4 week-block bootstrap | §5 Gate C |
| 5 headroom を fwd-look 前 + 凍結時除外のみ | §4/§5 Gate A |
| 6 N floor Poisson + UNDERPOWERED 経路 | §5 Gate B |
| 7 介入汚染ガード | §5 (explore assert + OOS 診断宣言) |
| 8 rnb_usdjpy reconciliation | §7 |
| 9 swap 歴史 proxy | §5 Gate D |
| 10 TV coverage assert + feed QA | §3 |
| 11 #18 重複診断 | §6 |
| 12 接触規律 | §8 |

**コミット規律**: 本文書 + 測定器 + stats tool を同一コミットで凍結 (rule:R1)。測定はコミット後開始。
