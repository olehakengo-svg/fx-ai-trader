# level_failed_break_d1 (台帳 #18) explore pre-reg — 観測前プロトコル凍結 (2026-07-31)

**状態**: 🔒 FROZEN (本コミットが凍結点 — 以後の定義・閾値変更は禁止、逸脱は verdict 無効)
**family**: wave-4 level-family survivor L-a。敵対的検証: [[level-family-adversarial-verification-2026-07-31]]
(GO-WITH-CONDITIONS 12 条件 — §9 に解決マッピング)。候補 payload: `raw/analysis/level-family-candidates-2026-07-31.json`
**charter**: user 委任 2026-07-30「並行チャネル、水平線でエッジ開発」+ 2026-07-31 補強「ちゃんと調べて出来るまで」。
凍結解釈: 網羅的・正しい測定で未検証差分空間を使い切る。**p-hacking/閾値緩和はしない** — 健全な候補が
残らなければ全滅と正直に記録 (本 wave の並行線側 3 候補は敵対的検証で triage KILL 済み、記録は台帳参照)。

---

## §1 仮説と prior (正直申告)

**H1**: D1 スケール水平極値 (55 営業日 Donchian) の**失敗ブレイク** (D1 close でのブレイク → ≤3 D1 bars での
close 復帰) の後、価格は fade 方向 (復帰方向) に 5 営業日ホライズンで正の純移動を持つ。

**機構**: ブレイクアウト勢のトラップ + ストップ連鎖の巻き戻し。生存 prior = htf_false_breakout×AUD_JPY
(1H SR false-break fade、ws3 stage-1 OOS ratio 1.82 / p=0.0118) の 1-2 段上位 TF への一般化。
postmortem 成功形状 3/3 (低頻度・レベルアンカー・長ホールド)。

**prior の限界 (敵対的検証 §1 訂正の反映)**: htf_fb は「explore→OOS 2 段スクリーンを通過し今も生きている
唯一のセル」だが **stage-2 EV 変換は 8/9 負で UNDERPOWERED** — prior が裏書きするのは「機構が方向を持つ」
(stage-1 型 estimand) まで。**EV 変換 (収益化) の証拠はゼロ**。本 explore はまさに stage-1 型 (exit-free
純移動) であり prior の移転先として適切、ただし explore PASS ≠ 収益化可能。

**名称**: `level_failed_break_d1`。W1 レベル変種は **declared non-tested** (scan しない。将来試すなら
新 family + 台帳新行)。

## §2 イベント定義 (全 DoF 凍結 — grid 探索禁止)

| 要素 | 凍結値 |
|---|---|
| bars | TV OANDA D1 (NY 17:00 close 境界そのまま)。土曜/日曜ラベル bar は除外、週あたり bar 数 median=5 を assert |
| level | `H55 = max(high[1..55])` / `L55 = min(low[1..55])` (当該 bar 除外、55 営業日) |
| break | D1 **close** > H55 (upside) / close < L55 (downside)。wick 貫通は break としない |
| failure 確認 | break bar の後 **≤3 D1 bars** 以内に close が level 内側へ復帰 (upside break なら close < H55_at_break)。復帰 bar = event bar |
| level 凍結 | break 判定時点の H55/L55 を failure 確認まで固定 (rolling 更新でイベント自壊させない) |
| entry proxy | event bar close |
| direction | fade = 復帰方向 (failed upside break → SHORT / failed downside break → LONG) |
| dedup | 同一ペア・同一サイドで event 後 10 営業日は新規イベント不生成。同一ペア反対サイドは許容 (week-block が相関処理) |
| horizons | 純移動 {1, 3, 5, 10} D1 bars。**PRIMARY = 5d の 1 本のみ**、他は diagnostic (選択に使わない) |
| pairs | EUR_USD, USD_JPY, GBP_USD, AUD_USD, USD_CAD, EUR_JPY, AUD_JPY, NZD_USD (8) |
| 窓 | explore = 2014-01-01〜2021-12-31 / OOS = 2022-01-01〜2026-06-30 (§8 — 本セッションでは explore のみ執行) |

## §3 測定器と検証 (TV 主戦)

- **TV per-event table export** (wave-1 ハーネス直系: pine_set_source → pine_smart_compile →
  data_get_pine_tables、batch 8 ペア)。Live > TV > Python BT 序列で TV はローカル BT より上位。
- **coverage assert (測定前必須)**: per-pair D1 first bar ≤ 2014-01-01。不通過ペア = **data-blocked**
  (「取れたところまでで走る」への事後緩和禁止 — W3-2 横断警告の無変更継承)。
- **feed QA**: 土曜 bar 除外 (wave-1 凍結事項継承)、bars/week assert (§2)。
  **QA 修正記録 (2026-07-31、fwd-return look ゼロ時点)**: 初回 META 読み (USDCAD pass-1) で凍結 assert が
  wknd=1257 を検出 — OANDA D1 の Monday bar は UTC open が日曜 21/22 時のため、UTC open-time ラベルでは
  全 Monday bar が「日曜」に誤分類され event 検出から除外されていた (実週末 stub は存在せず bars/week≈4.97)。
  測定器を trading-day ラベル (= bar close 日、America/New_York) に修正。定義・閾値の変更ではなく
  ラベリング実装の修正であり、凍結 QA が設計どおり作動した記録。
- **cross-check**: main checkout `data/cache/massive/*_1d*.parquet` (AUD_JPY のみ `AUD_JPY_1h` の D1
  resample) で**イベント数 + pooled 符号**を照合。乖離時は測定停止・原因究明。**worktree parquet は
  部分版につき使用禁止**。
- **測定のみ**: Pine strategy()/engine 登録等の実装は explore gates 通過後 (h4 決定文の IC-first 恒常条項の履行)。

## §4 接触順序 (two-pass — headroom を fwd-look より先に)

1. **pass-1 (headroom)**: table export は **fade 方向 MFE(5d) のみ** (符号付き純移動列を含めない)。
   Gate A 判定 → 不通過ペアをここで除外 (凍結時除外 — OOS 後の事後除外は禁止)。
2. **pass-2 (primary)**: 生存ペアのみ、純移動 {1,3,5,10}d + MAE を export。stats は
   `tools/level_fb_d1_explore_stats.py` (seed 20260731、モジュールトップ副作用なし)。

## §5 統計 (凍結)

- **Gate A (headroom)**: per-pair fade-MFE(5d) p50 ≥ **10× RT** (凍結 RT: USD_JPY 2.14 / EUR_USD 2.00 /
  GBP_USD 4.53 / EUR_JPY 2.50 / AUD_JPY 3.00 / AUD_USD 2.50 / NZD_USD 3.00 / USD_CAD 2.80p、
  floor 1.30p 感度併記)。**生存ペア <3 → family KILL (構造的 sub-headroom)**。
- **Gate B (power floor、Poisson 導出)**: 想定発生率 4-10/pair/年 → pooled explore 期待 256-640。
  per-event sd ≈ 40p (D1 5d、実測併記) とすると N=200 で MDE(片側 α=0.05, power 0.8) ≈ 7.0p。
  **floor = pooled N ≥ 200** (未満 → **UNDERPOWERED verdict**、PASS/FAIL を主張しない)。
  payload 旧床「<40」は本条で置換 (敵対的検証 条件 5)。
- **Gate C (primary)**: pooled 8-pair (生存ペア)・h=5d・fade 方向純移動 (pips) の平均 > 0、
  **ISO 週 event-block sign-flip permutation** (週内全イベント同時反転、10,000 draws、seed 20260731) の
  **片側 p < 0.05** (単独 family m=1 — 敵対的検証 §8 Q1 裁定: singles 直列、family 横断補正なし)。
  実効独立 N (イベント保有週数) を必須診断で併記。
- **Gate D (net EV)**: pooled mean − 実ペア加重 RT − swap 純額 > 0。感度 2 系統 (RT floor 1.30p /
  swap markup ±50%) で符号不反転。
- **Gate E (集中)**: 最大単一 ISO 週の寄与 ≤ 50% (SNB 型ガード)。
- **Gate F (一貫性)**: explore 年次符号 ≥6/8 正 + LOYO (leave-one-year-out) 全 8 通りで pooled mean > 0。
- **knife-edge 検査 (verdict 時必須、選択に使わない)**: 5 変種 = lookback {44, 66}d / 確認窓 {2, 4} bars /
  wick-break 定義。**いずれかで primary 符号反転 → FAIL** (weekend_gap「4/4 flip なし」水準)。
- **verdict**: 全 Gate 通過 = explore PASS → §8 分岐。いずれか不通過 = FAIL クローズ (OOS 非接触保存)。
  UNDERPOWERED は独立 verdict。**事後に閾値・定義を動かさない** (#7 vix p=0.050091 kill の前例に従う)。

## §6 摩擦・swap 会計 (凍結)

- **RT**: §5 Gate A の凍結表 (理論値) + floor 1.30p 感度 — wave-1 プロトコルの無変更継承。
- **swap (5d hold = 暦 7 日換算、×1.4)**: OANDA 現行 snapshot の一律適用は**禁止** (explore 窓は
  低金利差 regime — 系統誤差)。**歴史 proxy**: `knowledge-base/raw/bt-results/e20/e20_carry_level.csv`
  (BIS CBPOL 政策金利差、日次 ffill、2013-2022) をイベント日で参照。
  `swap_pips/日 = P_event × (r_diff ± markup)/365/100 ÷ pip_size`、position 符号適用。
  **markup = 0.50%/年 (対 position 逆風向き固定)、感度 ±50% (0.25/0.75%)**。
  panel は explore 窓を完全カバー。**OOS 執行時は e20_rates_ingest の機械リフレッシュが前提** (設計変更に該当しない)。

## §7 台帳関係 (凍結)

- **台帳 #18**。単独 wave (m=1)。#19 (round_number_major_level) は本 explore verdict 後に別の単独 wave。
- **#11 (htf_fb×AUD_JPY recheck) とは別 family** — #11 は LOCKED 一回限り再判定でありその grid/分母は
  不変。**本件の PASS/FAIL は #11 の判定に影響しない (双方向)**。htf_fb の shadow live データは本 family の
  explore/OOS に一切使用しない。
- #19 との pair-week イベント重複診断は #19 側 pre-reg で実施 (>30% なら部分依存を台帳注記)。
- pooled 前例の正直な引用: weekend_gap arm-B pooled は **3 ペア**であり 8 ペアの直接前例ではない。
  8 ペアは USD 共通因子で実効独立数が名目より小さい — week-block + 実効 N 診断で処理 (敵対的検証 §8 Q3)。

## §8 分岐 (凍結) と接触規律

- **explore FAIL / UNDERPOWERED** → 台帳 verdict 追記 + report + KB 永続化。OOS 非接触保存。
  次アクション = #19 (L-b) の凍結・測定へ。
- **explore PASS** → **OOS pre-reg DRAFT を起案して停止、user 最終承認待ち** (セッション規律 #6)。
  OOS 設計 (事前宣言): 同定義・2022-01-01〜2026-06-30・floor N ≥ 90・同 gates・
  介入週重複診断 (`data/external/mof_interventions.csv`)。**OOS は user 承認後に単一接触**。
- **PASS ≠ live**。live 昇格は R1 全段 (敵対的レビュー → LOCK → OOS → user 承認) が別途必要。
  live パラメータ・shadow 構成の変更ゼロ。
- 動機記録: データ駆動 (postmortem 成功形状 + htf_fb 生存 prior + user 委任)。感情動機なし。

## §9 敵対的検証 12 条件 → 解決マッピング

| 条件 | 解決 |
|---|---|
| 1 定義 DoF 凍結 + w1 落とし | §2 (55d/3bar/10d 単一値、W1 = non-tested、名称変更済み) |
| 2 primary 1 本 | §5 Gate C (pooled・5d・両サイド合算 fade 純移動) |
| 3 week-block bootstrap | §5 Gate C (ISO 週 sign-flip、実効 N 診断) |
| 4 headroom を fwd-look 前 | §4 two-pass (pass-1 = MFE のみ export) |
| 5 Poisson N floor | §5 Gate B (N≥200、UNDERPOWERED 経路併設) |
| 6 swap 歴史 proxy | §6 (e20 panel + markup 0.50% ±50%) |
| 7 機械 kill rules | §5 Gate E/F + knife-edge 5 変種 |
| 8 TV coverage assert | §3 (data-blocked、事後緩和禁止) |
| 9 ローカル cross-check | §3 (main checkout 1d、AUD_JPY は 1h resample) |
| 10 #11 別 family 宣言 | §7 |
| 11 IC-first 履行 | §3 (測定のみ、実装は gates 後) |
| 12 接触規律 | §8 |

**コミット規律**: 本文書 + 台帳更新 + 候補 payload + 敵対的検証レポートを同一コミット (rule:R1 明示)。
測定はコミット後に開始。
