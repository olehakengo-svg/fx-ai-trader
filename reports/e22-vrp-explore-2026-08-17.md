# E22 fx_variance_risk_premium explore report — 2026-08-17 (台帳 #24)

**verdict: ❌ explore FAIL — gate C+D+F 同時不通過でクローズ (OOS 2022+ 非接触封印)**

- pre-reg: `knowledge-base/wiki/decisions/e22-vrp-explore-prereg-2026-08-17.md` (🔒 凍結 `f50b680a` → pass-1 `0287371e` → pass-2 測定、two-pass 厳守)
- 敵対的検証: `knowledge-base/raw/analysis/e22-vrp-adversarial-verification-2026-08-17.md` (GO-WITH-CONDITIONS 17 条 / blocking 10 条 — §10 で全消化)
- ハーネス: `tools/e22_vrp_explore.py` (seed 20260817)。artifacts: `knowledge-base/raw/bt-results/e22/`

## 1. 設計 (凍結どおり、逸脱ゼロ)

VRP(t) = EVZ(t) − RV21(t) (年率 vol point) × EUR_USD、primary = 時系列 Spearman IC(VRP, fwd 21bd) **両側登録**、
null = circular-shift permutation (B=10,000、MIN_SHIFT=42、実測 VRP ACF lag42=+0.03 で正当化済み)。
explore = 2014-01-01..2021-12-31 (N=2,066 日次 obs / 非重複窓 98 / IC MDE 0.283)。単一構成・grid なし。

## 2. 機械判定 (pass-2、`pass2-2026-08-17.json`)

| gate | 凍結条件 | 実測 | 判定 |
|---|---|---|---|
| A headroom (pass-1) | median \|fwd21\| ≥ 40.0p | **137.7p** (3.4×) | ✅ |
| B power (pass-1) | N ≥ 1,500 ∧ 窓 ≥ 70 | 2,066 / 98 | ✅ |
| **C primary** | 両側 p < 0.05 | **IC = −0.0249、p = 0.760** | ❌ |
| **D stressed-net** | adverse 端 mean net > 0 | **−11.2p** (gross +8.9p / swap adverse −16.2p / RT −4.0p)。point 端 −3.1p / RT6 感度 −13.2p | ❌ |
| E 集中 | max year share ≤ 0.50 | 0.265 | ✅ |
| **F 一貫性** | 年次符号 ≥6/8 ∧ LOYO 8/8 | **5/8 / 7/8** (2016 IC −0.334 / 2019 +0.293 と年次振動) | ❌ |
| G 単調性 | tercile 単調 (違反 ≤1) ∧ T3−T1 符号 = g | 違反 1、符号一致 (g=−1) | ✅ |

knife-edge は全 gate PASS 時のみの規約どおり **未実行** (敗者の感度検査は選択バイアス源)。

## 3. 読み (事後解釈 — 判定には不使用)

1. **IC ≈ 0 の完全 null** — 「方向は合うが弱い」死型 (ppp/qs/rn/cc-mr の 4 例) にすら該当しない。EVZ−RV21 は explore 8 年の EUR_USD 21bd 方向に対し情報ゼロ。年次符号は 5/8 で振動し、最大年 (2016 −0.334 / 2019 +0.293) が互いに打ち消す = regime 反転型ノイズと整合。
2. **swap 支配構造の実証** — extreme-tercile の gross +8.9p (これ自体 null) に対し adverse swap −16.2p。**21bd hold の EUR_USD では swap が RT の 4 倍の支配的摩擦** — pre-reg §7 の事前記録どおり。仮に IC が有意でも gate D は独立に殺していた。
3. **g = −1 (高 VRP → EUR 下落) 側に出た点推定** は Della Corte 型 (高 VRP 通貨は増価) と逆符号だが、p=0.76 の点推定の符号に解釈価値はない。

## 4. クローズ範囲 (pre-reg §9 凍結どおり発効)

**「通貨 VRP (IV−RV 差分・レベル・比率の全変種) × G10 ペア × 日次〜月次固定ホライズン、EVZ/VXFXICLS 等の無料 proxy 系列を含む」— vol モダリティは E24/E25 棄却と合わせ恒久クローズ。**

**power caveat (凍結条項、引用時必読)**: FAIL は効果不在の証明ではない (文献級 IC 0.05–0.15 への検出力 8–17%。ただし本実測は点推定自体が −0.02 ≈ 0)。クローズの根拠は「無料経路での retail-viability 不成立 + 供給ライン経済性」。将来「VRP は falsified」型の引用は estimand 監査なしに禁止 (user 恒久指示 2026-08-05)。復活経路 = 真正 OTC FX オプション面 (Databento 等有償) + 新 family + 事前差分節 + 新規敵対的検証のみ。

## 5. §2.1 事前コミット節の帰結執行

- **FAIL 帰結**: vol モダリティ恒久クローズ → **探索空間が確定的に縮小** (scan 第 3 次の生存 6 系統 → 5 系統)。「無料で vol モダリティに白黒をつける」という主目的は達成 — Databento 調達の user 決裁は**不要になった** (PASS 時のみの決裁点)。
- **OOS 2022-01..2025-03-11 は非接触のまま封印** (ハーネスの OOS モードは explore FAIL で機械ロック)。
- explore→OOS 生存: 外部/新規 family 系統 **0/16** に更新。

## 6. 残置資産

- `data/external/vrp/EVZCLS.csv` — FRED EVZ 全系列 (確定終了系列、git 追跡化済み)。
- `tools/e22_gap_backfill.py` — **EUR_USD 15m の 2020-10-23..11-16 ベンダー穴を OANDA mid で修復 (+1,440 行、米大統領選挙週回収)** — E22 と無関係に全 EUR_USD 研究の恒久的なデータ品質改善。
- `tools/e22_vrp_explore.py` — 時系列 IC + circular-shift null + git-commit assert 型 OOS ロックのハーネス (流用可)。
- data freeze manifest (sha256): `knowledge-base/raw/bt-results/e22/data_freeze_manifest_2026-08-17.json`。

## 7. 供給ラインへの含意

能動的に動かせる系統は **E21 (帰属分解、user 決裁待ち registry 08-31) のみ**になった。残りは全て calendar-lock (E12 2027-02-05 / E1 2026-10-15 / #22 ECG 2026-11-06 / E23 は E7 verdict 08-17 着地でゲート解除済み — 起動判断は次スキャンまたは別 wave)。live/tier/lot 変更ゼロ。
