# family C (台帳 #26) 敵対的検証 report — 2026-08-19 (SSOT)

**対象**: [[family-c-rate-anchor-explore-prereg-2026-08-19]] (DRAFT 時点) + `tools/family_c_anchor_explore.py` + test pins
**方式**: 4 独立レンズ並列 (統計/leakage、ban 隣接/cross-LOCK、ハーネス⇄spec 整合、完全性 critic)、各レンズ REFUTE 指向・合成データ probe 許可・実 explore データの signal×outcome 接触禁止
**総合 verdict**: **GO-WITH-CONDITIONS — blocking 10 条 (dedup 後) / non-blocking 19 条。全 blocking は凍結前に pre-reg/ハーネスへ反映済み** (マッピングは pre-reg §10、本 report が SSOT)

## 最重要 finding 3 件

### 1. gate C の旧 null は反保守 (blocking C1 — 統計レンズ、合成 probe で実証)

旧設計 (year-matched placebo mean resampling) を純ランダムウォーク (エッジゼロ・ドリフトゼロ) に適用した合成 probe:
- **type-I = 20.6% (定常 vol) / 29.0% (vol クラスタ) @ 名目片側 5%** — 4-6 倍の反保守
- 経路 (i): min-sep 5 << h 21 → 実 onset はドローダウン episode 内に密集 (probe: 隣接 onset の 51% が gap < 21) = イベント net が強正相関、placebo 抽選はほぼ独立 → Var(mean_perm) が Var(mean_obs) を過小評価
- 経路 (ii): onset 日は高 vol ドローダウンに条件付く → 条件付き σ(fwd21) > 無条件 σ
- studentize では不足 (24.5%)、年内 constellation-shift は経路 (i) のみ修復 (定常 3.4% だが vol クラスタ 12.0%)

**採択された修復** (probe 較正済み): 統計量 = mean(net_21 − μ_year) (年内 demean)、null = episode-block (gap < 21 で連結) sign-flip。実測 size **8.7-9.2%** @ 名目 5% (両経路下)、drift-only では 4.3% (= timing 検定性を保持)。残余 ~1.8x inflation は**閾値側で吸収 (p ≤ 0.02 ≈ 実効 ~5%)**。probe スクリプトは scratchpad (placebo_probe{,2,3}.py、合成データのみ)。

### 2. 金利 staleness 5 日規則が explore 窓の 2019-2021 を連鎖 blackout (blocking — 完全性/整合レンズ、実データ census)

JGB 2y の実測公表 gap: 2014-01 (7 暦日) / 2019-01 (7) / **2019-05 Golden Week (11)** / 2020-01 (7)。旧 staleness 上限 5 日ではこれらが diff2y NaN を作り、**完全窓規則 (252 日連続 valid 必須) が各 NaN の後 252 valid D1 を void 連鎖** → 実効 explore が ~4.5-5 年に縮み、2020-03 COVID dip (最有力の非介入 undershoot クラスタ) も失われていた。修復 = **staleness 上限 12 暦日** (実測最大 gap 11 を被覆する最小整数 + DGS2 は >5 日 gap ゼロ) + gap census の on-record + test pin (GW シナリオ)。

### 3. rates-content 識別不能リスク (blocking C4 — 統計レンズ)

diff2y が窓内でほぼ動かない場合、fitted ≈ 定数となり z は「価格の rolling location band」に縮退 — **価格のみの dip-buy が生む onset 集合とほぼ同一になり、PASS が rates 機構に誤帰属されうる** (user 恒久指示 2026-08-05 の estimand 監査対象そのもの)。修復 = b≡0 ablation 対照 (価格のみ z、同 W・同 Z_th) の **Jaccard 重複 + 対照 mean net を pass-2 で診断報告**し、解釈規則を凍結 (Jaccard ≥ 0.5 ∧ 対照 net ≥ 0.8× primary → 「rates-content unidentified」caveat 義務 + rates 系拡張の禁止)。pass-1 には anchor 寄与 share census を追加。

## blocking 条件一覧 (dedup 後 10 条 — 解決は pre-reg §10 マッピング参照)

1. gate C null 反保守 (type-I 20-29%) → demean + episode-block sign-flip + p≤0.02
2. MDE σ 定義バグ (sd(|X|) ≈ 0.6×sd(X) → MDE ~1.6x 過小報告) → signed sd + 2.485
3. select_zth の未定義分岐 (混在 range 内ゼロで >150 側を暗黙採用) → UNDERPOWERED に凍結
4. rates-content 識別不能 → ablation 対照 + 解釈規則凍結
5. OOS 4 点機械ロックが凍結対象ハーネスに未実装 → `oos` モード凍結前実装
6. OOS 介入隣接の再判定汚染 (E-C 既公表 outcome の binding 混入) → +21d 隣接 partition 事前凍結
7. staleness 5d → 2019-2021 blackout → 12d + census + test pin
8. --parquet 実体が manifest 未照合 (bare/部分 parquet 差し替え可能) → 直接 sha256 照合
9. min-sep の単位不一致 (onset = valid-z index vs placebo = frame position) → frame position に統一
10. placebo pool に z-void 日混入 (交換可能性破れ) → valid-z 日に限定

## non-blocking (全て反映 or on-record — 19 条)

entry-lag knife-edge 追加 (無歯の log-fwd 変種と差替) / 測定 N 再チェック (drop 後 <30 → UNDERPOWERED) + 件数報告 / staleness 計測基準 wording / inf-z guard (RESID_STD_MIN=1e-12) / RNG 順序決定化 (sorted year) + numpy/pandas version 記録 / gross/swap/net 分解報告 (lane-owner 要請 4 と同一) / ロック網羅 (pass-1 イベント CSV + ハーネス自己 commit assert、manifest 行数 assert) / E20 条項の機構的 discharge (窓内 OLS 直交性 — 残差は金利差情報を構造的に含まない) / ppp ban の原文 verbatim 引用 (「推定量変更」は paraphrase だった) + 連言 scope 外を一次論拠に / BH「起動」= 凍結コミット定義 (family A DRAFT は分母外) / parquet living-cache 条項 (E22 条件 16 同型) + host-pin on-record / anchor 寄与 census / gate G false-kill 定量 (~40-50%、binding 維持は anti-gate-shopping 前例) / gate F 全疎年 fallback / yields 改定値 on-record / §9 harness 挙動 wording 一致 (2022+ onset は列挙後破棄) / knife-edge (v) 診断化明文 / RT3x の m_adverse 併用明記 / 永続 runtime 実測 (pass-2 permutation ≈ 1 分、対策不要)。

## レンズ別 verdict

| レンズ | verdict | blocking |
|---|---|---|
| 統計/leakage (合成 probe 3 本) | GO-WITH-CONDITIONS | 5 |
| ban 隣接 / cross-LOCK / 手続き | GO-WITH-CONDITIONS | 2 |
| ハーネス⇄spec 整合 (行単位) | GO-WITH-CONDITIONS | 3 |
| 完全性 critic (実データ coverage census) | GO-WITH-CONDITIONS | 3 |

(重複条件は dedup。lookahead 検査は 3 レンズが独立に CLEAN: z は C≤d + yields≤d−1 のみ、窓内 day-d 包含は z を減衰させる方向 = 保守側、公表時刻 knife-edge は lag-1 で構造排除・test pin 済み)
