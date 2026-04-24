# lesson-preregistration-gate-mechanism-mismatch

**発見日**: 2026-04-24 | **修正**: 次 pre-reg 設計から反映
**Source**: [[mafe-dynamic-exit-result-2026-04-24]], [[pre-registration-mafe-dynamic-exit-2026-04-24]]

## 問題

MAFE 動的 exit の 365 日 BT (N=14,185) で、**16 cells が ΔEV +0.53〜0.54p を literal p=0 で
達成**したのに、**SURVIVOR=0** となった。単一ゲート「Wilson 95% lower on V2_WR > 53%」
だけで全 CANDIDATE を block し、機構自体は強い alpha を持っているのに binding criteria
で検出できなかった。

## 症状

- base_wr=39.9%, base_ev=-2.78p の baseline に対し、V2 (X=3,Y=2,Z=3): WR=17.0%, EV=-2.24p
- ΔEV=+0.54p / Welch p=0 / Fisher p=0 / WF 2-bucket 同符号 / V2 engaged N=11,723 ≫ 80
- 唯一 FAIL: Wilson WR lower **16.4%** << **53%** ゲート (差 36.6pp)
- **48 cells 全てで wilson_lo < 35%** → N を holdout で倍増しても 53% 到達は mathematical に不可能

## 原因 — ゲート設計と機構タイプの不整合

pre-reg §4 の SURVIVOR binding criteria は以下を含む:

> Wilson 95% lower bound on V2_WR > **BEV + 3pp** (= ~53%)

この 53% ゲートは **"WR を上げて勝つ"** 機構 (対称 R:R での filter 導入) を暗黙に想定した
設計だった。しかし MAFE 動的 exit の実質機構は:

- **winners を増やさない** (TP 到達 trade は baseline と同じ)
- **losers を小さく切る** (SL まで待つ大損を早期 cut で小損化)
- **むしろ一部の winner が "MFE 未到達" で早切りされるため V2_WR は下がる**

→ 機構は「**WR 軸に効かない / loss magnitude 軸に効く**」型だったのに、gate は WR 軸で
合格を求めていた。機構と指標のカテゴリーミスマッチ。

## なぜ事前に気づけなかったか

1. pre-reg の Hypothesis 文に "EV 改善" は書いていたが、**WR が構造的にどう動くか**
   (上がる / 下がる / 無関係) の mechanism thinking が抜けていた
2. "BEV gate" のテンプレートを対称 R:R 戦略から流用し、cut-loss 機構特有の
   "WR は落ちるが EV は上がる" ケースを想定していなかった
3. Bonferroni / WF / V2_N など "rigor を積む" gate は豊富だったが、
   **"機構の方向と指標の方向が噛み合っているか"** の sanity layer が欠けていた

## 修正 — 今セッションでは何もしない (遡及変更禁止)

本 BT 結果を見てからゲートを緩めれば **HARKing**。pre-reg §7 Anti-pattern Guard で明示的に
禁止している "Bonferroni loosening" と structurally 同じ post-hoc 救済。

→ 現 pre-reg は §6.2 Extended Shadow path を遵守し、2026-05-14 時点で再集計。
Wilson gate の mathematical 到達不能性から §6.3 収束が高確率で予想されるが、
予想を action に影響させない。

## 教訓

**pre-reg の binding gate は、機構の作用方向と同じ軸の指標を選ばなければならない。**

- cut-loss 機構 → Wilson WR gate ではなく、以下のどれかを使う:
  - Wilson 95% upper on **mean loss** (小さい方へのシフト検出)
  - ΔCVaR (下側テール圧縮の定量化)
  - PF lower bound (ratio-based、WR×R:R 複合)
  - Expected-shortfall delta in worst quartile
- win-rate 改善機構 (filter 型) → 従来の Wilson WR gate が適切
- edge creation 機構 (新 signal) → WR + EV 両軸

**How to apply**: 次の pre-reg 作成時、§4 Binding Criteria の前に以下の
"mechanism-gate alignment" sanity を 1 パラグラフで書く:

> "本 hypothesis が勝利条件を達成する場合、WR / mean win / mean loss / PF / CVaR の
> どの指標がどの方向に動くか" を列挙 → その最小セットに対する ΔN / p / lower bound
> を binding gate とする。他軸の変化は "anti-criteria" (例: 悪化しないこと) として
> 片側制約のみ。"

## Why this matters

pre-reg の目的は **HARKing 防止** であって **機構の正当な alpha を blind に殺すこと**
ではない。厳格なゲートが「機構には効いているのに棄却される」動作を生み出すと、
規律と実益のバランスが崩れ、**次回以降 pre-reg を書く motivation が失われる**
(= 規律そのものの erosion)。

gate と機構の整合性チェックは、事前に追加コストほぼゼロで実施でき、
棄却の false-negative を構造的に減らす。

## References

- [[pre-registration-mafe-dynamic-exit-2026-04-24]] — 本 lesson の発火元 pre-reg
- [[mafe-dynamic-exit-result-2026-04-24]] — 48-cell 結果
- [[lesson-reactive-changes]] — 1 日データで code 変更禁止 (別 lesson、HARKing 回避の別系)
- [[shadow-deep-mining-2026-04-24]] — §"Statistical artifact caught" の self-audit 例
- CLAUDE.md 判断プロトコル — pre-reg 設計の基礎ルール
