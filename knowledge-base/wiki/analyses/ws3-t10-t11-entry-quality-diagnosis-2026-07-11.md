# WS3 T10/T11 エントリー品質診断 — 高WR×負EV 群の「entry 劣化 vs payoff/摩擦 kill」分離 (2026-07-11)

> **Rule 3 (診断)。** live/shadow パラメータ変更なし・純 read-only 分析。roadmap v2.3 WS3 の T10 (gbp_deep_pullback) / T11 (sr_anti_hunt_bounce) 診断項目に応答。
> **関連**: [[roadmap-v2.3-payoff-friction-repair]] WS3 / [[ws3-mfe-distribution-2026-07-08]] (母集団 MFE/MAE 基準線) / [[ws3-round2-explore-prereg-2026-07-10]] (round-2 の N≥30 選抜規則) / [[shortest-path-decision-memo-2026-07-10]] §6 (供給ライン = 外部仮説 + T10/T11)

## 0. 背景と問い

Track B (供給ライン) の探索2周目が OOS FAIL 0/5 (PR #79) でクローズし、**shadow 母集団の「非対称×barrier」軸は 2 周で枯渇確定**。残る内部候補は roadmap WS3 の T10/T11 の 2 セルのみ (以降は外部仮説へ)。両者は「高WR だが shadow EV は負」という共通形をもち、roadmap が明示した診断の問いは:

- **T10 gbp_deep_pullback**: pullback エントリーのエッジ有無を分離し、**payoff/摩擦 kill か entry 劣化か**判定
- **T11 sr_anti_hunt_bounce**: EV −4.49 は payoff/摩擦か、それとも **thesis 劣化**か

この問いは「exit に依存しない entry 品質」を測れば直接答えられる。**MFE/MAE 前方分布 (シグナル方向に対する最大順行 / 最大逆行)** がその指標で、既に [[ws3-mfe-distribution-2026-07-08]] の `tools/ws3_mfe_scan.py` が全 entry_type × pair について 365d BT (診断窓 2026-06-07 以降除外) で計測済み。本診断はその成果物 (`knowledge-base/raw/bt-results/ws3_mfe_scan_2026_07.json`, N_entries=6,995, 118 cells) を再利用し、新規 BT を回さずに答える。

**判定基準 (本データセット自身から導出、記憶値に依存しない)** — N≥30 の 63 セルで:

| horizon | median MFE/MAE ratio | p90 | ratio≥1.3 の割合 |
|---|---|---|---|
| h24 | 0.88 | 1.19 | 3% (2/63) |
| h48 | 0.86 | 1.12 | 0% |
| h96 | 0.90 | 1.17 | 2% (1/63) |

→ **ratio ≈ 0.88 = 方向性エッジなし (母集団の中央)**、**ratio ≥ 1.3 = 希少な順行非対称 (上位 2-3%)**。round-1/round-2 の選抜床 (ratio≥1.3 ∧ N≥30) と同一基準。

## 1. T10: gbp_deep_pullback × GBP_USD — **entry 劣化 (CLOSE)**

現状: shadow WR 72% / EV −1.39、tier = PAIR_DEMOTED (GBP_USD)。**N=56 (十分な検出力)**。

| horizon | n | MFE_p50 | MAE_p50 | ratio | p(MFE≥15p) |
|---|---|---|---|---|---|
| h6  | 56 | 8.2  | 11.5 | **0.72** | 0.321 |
| h12 | 56 | 11.1 | 13.5 | **0.82** | 0.393 |
| h24 | 56 | 15.9 | 18.6 | **0.85** | 0.518 |
| h48 | 56 | 23.4 | 24.6 | **0.95** | 0.643 |
| h96 | 56 | 30.2 | 38.1 | **0.79** | 0.750 |

**全 horizon で ratio ≤ 0.95、ピークでも h48 の 0.95 < 1.0。** 母集団中央 (0.88) と同水準で、順行非対称は皆無。エントリー後は「順行と逆行がほぼ拮抗、やや逆行優位」= **エントリー・シグナルに前方の方向性エッジが無い**。

→ **診断結論: entry 劣化。** shadow WR 72% は entry エッジの反映ではなく、**BE/Trail + 早利確による WR 水増しアーティファクト** (MEMORY `project_be_trail_inflates_python_bt_wr`、payoff 0.27 の署名 = 小さく多く勝ち稀に大きく負ける) の典型。真の順行エッジが payoff/摩擦で殺されているのではなく、**そもそも順行エッジが無い**。barrier/EV 再設計で救済不能 (round-2 枯渇と整合)。**T10 CLOSE。**

## 2. T11: sr_anti_hunt_bounce — **集計 −4.49 は異質性を隠蔽。USD_JPY のみ順行非対称、ただし underpowered**

現状: aggregate shadow WR 63% / EV −4.49。**この集計は 5 ペアの平均で、劣化ペアに支配されている** (教訓「平均値は嘘をつく / 必ずセグメント分解」)。ペア別 MFE/MAE:

| cell | n | h24 ratio | h48 ratio | h96 ratio | 判定 |
|---|---|---|---|---|---|
| **×USD_JPY** | **19** | **1.71** | **1.71** | **1.33** | **順行非対称・horizon 持続 (希少)** ⚠️ N<30 |
| ×GBP_JPY | 32 | 1.07 | 0.80 | 0.54 | h12 で 1.22 ピーク後 急減衰 → 非持続 |
| ×EUR_JPY | 33 | 0.90 | 1.12 | 0.76 | 振動、持続非対称なし |
| ×EUR_USD | 10 | 0.58 | 0.80 | 0.61 | underpowered かつ逆行優位 (劣化) |
| ×GBP_USD | 13 | 0.15 | 0.23 | 0.62 | underpowered かつ深い逆行優位 (劣化) |

**sr_anti_hunt_bounce × USD_JPY** は h24/h48 で ratio 1.71、h96 で 1.33 と、母集団上位 2-3% の希少な順行非対称を示す。p(MFE≥15p) も 0.42→0.47→**0.79→0.90→0.95** と単調上昇 = 中央値ベース (外れ値頑健) の広域シグナルで、[[ws3-mfe-distribution-2026-07-08]] が探した「持続型 (h96 まで増幅)」に該当。**SR family で audit を生き延びた唯一の survivor という位置づけ (roadmap WS3 T11) とも整合。**

**なぜ round-2 が拾わなかったか (redundant でない証明)**: round-2 の選抜床は **N≥30**。USD_JPY セルは **N=19 < 30** で構造的に除外されていた。本診断は「検出力床が structurally 見落とした underpowered セル」を特定したもので、枯渇済みの N≥30 軸とは独立。

→ **診断結論**:
1. **T11 の aggregate EV −4.49 は payoff/摩擦でも単一 thesis 劣化でもなく、「ペア横断の混合」。** GBP_USD / EUR_USD / GBP_JPY / EUR_JPY の 4 ペアは entry 劣化 (順行非対称なし) → これらは close。
2. **sr_anti_hunt_bounce × USD_JPY のみ、payoff/摩擦で殺されている可能性のある真の順行エッジ候補。** ただし **N=19 < 30 で昇格不能**、かつ本測定は探索窓 (365d, 診断窓除外) で **OOS 未検証**。lfr×EUR_USD 型 (点推定再現するが EV 化不能) の失敗も踏まえ、点推定だけで候補確定はしない。
3. **処分: shadow N≥30 まで蓄積 → 到達で round-1/round-2 と同一の OOS スクリーン (非診断窓での ratio 再計測 + block bootstrap + BH-FDR + first-touch EV レグ + ナイフエッジ3点) の 1 回限り検証枠に載せる。** registry に監視エントリを追加 (`ws3-t11-anti-hunt-usdjpy-recheck`)。

## 3. 供給ラインへの含意

- **内部母集団の残余候補は事実上枯渇**: T10 は well-powered な null で確定 close。T11 は 5 ペア中 4 ペアが close、残 1 (USD_JPY) も underpowered + OOS 未検証で、**即戦力の survivor は無い**。
- これは round-2 OOS FAIL 0/5 および [[friction-adjusted-ev-map-2026-07-07]] (現行母集団に live viable な正セル不在) と **三重に一致** — 現行シグナル母集団からの供給は尽きた。
- **主戦線は外部仮説 (学術/TV 由来の新シグナル系統) の探索へ全面移行** ([[shortest-path-decision-memo-2026-07-10]] §6 既定路線を実証的に追認)。sr_anti_hunt×USD_JPY は「蓄積待ちの単一の細い糸」として registry で監視するのみ。
- **カーブフィッティング禁止 / falsified 6系統 (H4 level / channel / sweep&reclaim horizontal / mtf SELL / bb_rsi / T11 counter-USD) 再試行禁止**は不変。sr_anti_hunt×USD_JPY の再検証は「既存 entry_type の非対称の OOS 化」であり、falsified ハーネス仮説の再試行ではない (round-2 で turtle_soup を残置と裁定したのと同じ estimand 区別)。

## 4. 再現

```bash
# 母集団基準線 + T10/T11 セル抽出 (BT 再実行不要、成果物再利用)
python3 - <<'PY'
import json, statistics
d=json.load(open('knowledge-base/raw/bt-results/ws3_mfe_scan_2026_07.json'))
c=d['cells']
for H in ['h24','h48','h96']:
    r=sorted(c[k][H]['mfe_p50']/c[k][H]['mae_p50'] for k in c
             if c[k].get('n',0)>=30 and H in c[k] and c[k][H]['mae_p50'])
    print(H,'median',round(statistics.median(r),2),'n>=1.3',sum(x>=1.3 for x in r),'/',len(r))
for k in sorted(x for x in c if 'deep_pullback' in x or 'anti_hunt' in x):
    row=[f"{c[k][h]['mfe_p50']/c[k][h]['mae_p50']:.2f}" for h in ['h24','h48','h96'] if h in c[k]]
    print(f"{k:<32} n={c[k]['n']:>3}  h24/48/96={row}")
PY
```

## 5. 判定サマリ

| 項目 | 診断 | 処分 | Rule |
|---|---|---|---|
| **T10 gbp_deep_pullback×GBP_USD** | entry 劣化 (ratio≤0.95, N=56 well-powered)。72% WR は exit アーティファクト | **CLOSE** (barrier 救済不能) | R3 |
| **T11 sr_anti_hunt_bounce (agg)** | 集計 −4.49 は 5 ペア混合。4 ペア (GBP_USD/EUR_USD/GBP_JPY/EUR_JPY) は entry 劣化 | 4 ペア **CLOSE** | R3 |
| **T11 sr_anti_hunt_bounce×USD_JPY** | 順行非対称 (1.71 h24-48, 持続型)。ただし N=19<30 + OOS 未検証 | **shadow N≥30 蓄積 → OOS 再検証枠** (registry 監視) | R3 (診断) → R1 (促進時) |
| **供給ライン全体** | 内部母集団枯渇を三重確認 (本診断 + round-2 FAIL + T4 EV マップ) | **外部仮説探索へ全面移行** | — |
