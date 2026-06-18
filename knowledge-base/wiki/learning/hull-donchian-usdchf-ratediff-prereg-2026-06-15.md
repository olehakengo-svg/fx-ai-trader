# 🔒 Pre-reg LOCK: USD_CHF fade × 金利差転換 regime ゲート (反証テスト) — 2026-06-15

**MEMORY:** `project_hull_donchian_multipair_prereg_2026_06_12.md`
**LOCK 規律**: spec・ゲート定義・閾値・判定条件を実行前に凍結。実行後の閾値変更・
別ゲート探索は禁止。結果は PASS/FAIL 問わず append。**一発判定**。

## 背景と user 因果仮説

横展開 pre-reg ([[hull-donchian-fade-multipair-prereg-2026-06-12]]) で USD_CHF は C3 (WF) のみ
落ちたが post-2020 は強かった (>=2022 N=1994 WR.813 +1.96p PF1.33)。user の因果仮説 =
**「金利差転換 regime」**: USD-CHF 政策金利差が wide な局面では carry が pair をレンジに
ピン留めしトレンドが続かない → 二重確認ブレイクの fade が効く。

## post-hoc 罠の回避設計 (本 pre-reg の肝)

「2020以降が良い」を金利差ゲートで再現するのは **変数を変えただけの期間選択**。
金利差仮説が真なら、**同一 "wide 金利差" regime が存在した別時代でも効く**はず。
金利差 (Fed funds 上限 − SNB 政策金利) は 2 つの wide 窓を持つ:
- **2018-06..2019-07**: Fed 利上げで差 ≈ 2.5-3.25% (← これは「F1/F2 負けコホート」の中)
- **2022-09..2024**: 差 ≈ 3.0-3.75%

→ **真の反証テスト = pre-2020 wide 窓 (2018-2019) で fade が黒字か**。
ここが黒字なら仮説支持 (コホートと独立に rate-diff が効いている)。
ここがコホートと一緒に負けるなら post-2020 はコホート運 = 仮説falsified。

## 金利差データ (外生ステップ系列、結果に非依存)

Fed funds 上限目標 / SNB 政策金利の公知の変更月で再構成 (script 内に schedule をコメント明記)。
差 = Fed_upper − SNB。閾値由来は経済的ラウンド値で、binで単調性も示すため閾値は load-bearing にしない。

## 凍結 spec

- 戦略: **横展開と同一の凍結ルール** (Hull55×Don20、width≤own-q33、fidelity exit:
  TP=static basis / SL=4×ATR / hold96)。USD_CHF、spread 1.2p。**再最適化なし**。
- ゲート: trade entry 時刻の金利差 (月次ステップ)。
  - "wide" = 差 ≥ **2.5%** (凍結)
  - "narrow" = 差 < 2.5%

## 判定条件 (実行前凍結)

**仮説 SUPPORTED (= 別系統 forward pre-reg に進める) には ALL 必要:**
- S1: **pre-2020 wide 窓 (entry ∈ 2018-06..2019-07) で net EV > 0** (N≥100、反証テストの本体)
- S2: 単調性 — 金利差 bin (<0.5 / 0.5-2.5 / ≥2.5) で net EV が差の増加と共に単調増加
- S3: wide 部分集合 net EV > narrow 部分集合 net EV、かつ wide 両side EV > 0
- S4: wide 部分集合 bootstrap p < 0.05

**報告のみ**: 各 bin の N/WR/EV/PF、2018-2019 と 2022-2024 の wide 窓個別、narrow 窓個別。

**SUPPORTED でも即 LIVE 不可** — gated 全期間も in-sample。SUPPORTED なら「wide-diff ゲート付き
USD_CHF」の forward shadow / forward pre-reg を別途起こす (user 決裁)。
**FAIL → 金利差仮説 falsified、USD_CHF 完全クローズ**。

## 結果 (2026-06-15 実行、verdict 確定 — 金利差仮説 FALSIFIED、USD_CHF クローズ)

**FALSIFIED。** raw: `hull-donchian-1m-validation/reports/prereg_usdchf_ratediff.txt`

| 判定 | 結果 |
|---|---|
| **S1 反証テスト** (pre-2020 wide窓 2018-06..2019-07) | ❌ **FAIL: N=292 WR.726 EV=−1.142p PF=0.802** (diff 2.50-3.25%) |
| S2 単調性 (<0.5 / 0.5-2.5 / ≥2.5) | ❌ FAIL: −0.54 / **+3.42** / +1.38p (逆、中域が最良) |
| S3 wide>narrow ∧ wide両side>0 | ❌ FAIL: NARROW +2.99p > WIDE +1.38p、wide LONG −0.01p |
| S4 wide bootstrap p<0.05 | ✅ (p<0.0001、但し巨大N由来で仮説の検定ではない) |

### 決定的所見

1. **同一 carry regime・別時代で負ける**: 2022-2024 wide窓 (+2.043p) と**同じ金利差 2.5-3.25%**
   を持つ 2018-2019 wide窓は **−1.142p**。carry が効くなら両方黒字のはず → carry は
   post-2020 エッジのドライバーではない。**post-2020 の強さはコホート (2020-2026 のボラ
   regime) そのもの**で、金利差とは無関係。
2. **単調性が逆**: エッジは金利差と共に増えない。むしろ中域 (0.5-2.5%) が最良 (+3.42p)。
3. **規律の効果**: naive な全期間 wide ゲートなら S4 (p<0.0001) だけ見て誤「支持」しえた。
   pre-2020 wide 窓の OOS テスト (S1) が仮説を正しく棄却した。

### 帰結

金利差転換仮説は falsified。**USD_CHF は完全クローズ。** Hull×Donchian fade ファミリで
LIVE 可能なのは EUR_USD 単体のみ ([[hull-donchian-fade-multipair-prereg-2026-06-12]]・
[[hull-donchian-gbpusd-rawfade-prereg-2026-06-12]] と合わせ三重に確認)。
