# weekend_gap 短ホライズン fade — OOS confirm verdict (2026-07-24)

**pre-reg**: `knowledge-base/wiki/decisions/weekend-gap-oos-prereg-2026-07-24.md` (🔒 LOCKED 2026-07-24, rule:R1 stage-1)
**実行**: `tools/weekend_gap_fill_oos_confirm.py --oos` — **単一実行 (2026-07-24)**。dry-run 再現 (explore 窓 2014–2021、凍結統計 10/10 一致) + 敵対的監査 CLEAN 通過後に OOS 初接触。以降の再実行は禁止 (スクリプト自体が既存出力検知で拒否)
**OOS 窓**: 2022-01-01〜2026-06-30 (explore 窓と重複ゼロ)。seed 20260724 / B=10,000 / one-sided / p 床 = 1/(B+1) → 「p<1e-4」表記
**データ**: ローカル 12y parquet (MASSIVE)。GBP_USD は **ロードすらしていない** (--oos モードで pair map から除去 + assert)
**JSON**: `bt-results/weekend_gap_oos_confirm-2026-07-24.json` (+ `knowledge-base/raw/bt-results/` 同名)

---

## 結論 (frozen decision table の機械的適用 — 裁量ゼロ)

| arm | N (floor) | arm p | (a) 方向 | (b) BH | (c) stressed-net | (d) headroom | (e) N floor | knife-edge | **最終** |
|---|---|---|---|---|---|---|---|---|---|
| **A** EUR_USD 4h+12h | 46 (25) | p=0.1189 (IUT max) | ✅ | ❌ | ✅ | ✅ | ✅ | flip なし (非適用: pre-KE FAIL) | **FAIL** |
| **B** pooled 4h | 177 (60) | p<1e-4 | ✅ | ✅ | ✅ | ✅ | ✅ | **4/4 flip なし** | **PASS** |

**family verdict (§4.2 優先順位規則 1): ≥1 arm PASS → family #3 = PASS 候補**。arm A は当該 arm のみクローズ。次段 = §9 R1 手続き (日曜 open 実スプレッド ≥8 週末実測 → 執行設計 pre-reg stage-2 → user 最終承認)。**live パラメータ変更ゼロ** — PASS ≠ live。

---

## 1. arm A (EUR_USD 単独、co-primary 4h AND 12h) — ゲート walk-through

| endpoint | N | gross mean | boot p (event-block) | stressed-net (−6.0p) | MFE p50 (要求 ≥20.0p) |
|---|---|---|---|---|---|
| 4h | 46 | **+13.22p** | p<1e-4 | +7.22p | 21.6p ✅ |
| 12h | 46 | **+7.38p** | **p=0.1189** | +1.38p | 30.3p ✅ |

- **(e) N floor**: 46 ≥ 25 → **検定対象** (UNDERPOWERED ではない)
- **(a) 方向性**: gross > 0 が 4h/12h 両方 → ✅。arm p = max(p_4h, p_12h) = max(p<1e-4, 0.1189) = **0.1189** (IUT、凍結)
- **(b) 多重性 BH q=0.10 step-up (m=2、両 arm N floor 充足)**: p 昇順 = p(1)=arm B (p<1e-4)、p(2)=arm A (0.1189)。判定表: (i) p(2)=0.1189 ≤ 0.10? **NO** → (ii) p(1) ≤ 0.05? **YES → p(1) の arm (=B) のみ通過**。arm A は **(b) 不通過** → ❌
- **(c) stressed-net (3×RT=6.0p 控除)**: +7.22p / +1.38p 両方 > 0 → ✅ (ただし 12h は +1.38p と薄い)
- **(d) headroom**: 21.6p / 30.3p ≥ 20.0p → ✅
- **pre-knife-edge status = FAIL** (ゲート (b) 単独落ち)。knife-edge 格下げは PASS arm のみに適用のため状態不変 (記録: 4 検査全て flip なし)
- **arm A 最終 = FAIL (検定済み)**

**機械的裁定の含意**: 12h endpoint の bootstrap p 崩壊 (explore p<1e-4 → OOS 0.1189) が IUT arm p を支配し BH を落とした。4h 単独なら p<1e-4 だが、**co-primary AND は凍結 (§10-3 裁定) — 事後の endpoint 変更は §9 で禁止**。

## 2. arm B (pooled {EUR_USD, USD_JPY, AUD_USD}、4h 単一) — ゲート walk-through

| endpoint | N | weekends | gross mean | weekend-block boot p | stressed-net (−6.56p 固定) | MFE p50 (要求 ≥21.9p 固定) |
|---|---|---|---|---|---|---|
| 4h | 177 | 112 | **+15.60p** | **p<1e-4** | **+9.04p** | 24.8p ✅ |

- **(e) N floor**: 177 ≥ 60 → 検定対象
- **(a) 方向性**: +15.60p > 0、weekend-block bootstrap (同一週末クロスペア相関をブロック化) p<1e-4 → ✅
- **(b) BH step-up**: 上記判定表 branch (ii) で **arm B 通過** → ✅
- **(c) stressed-net**: 15.60 − 6.56 = **+9.04p > 0** → ✅ (点推定、凍結 stressed RT — OOS 構成での再加重なし)
- **(d) headroom**: MFE p50 24.8p ≥ 21.9p (凍結定数) → ✅
- **pre-knife-edge status = PASS** → knife-edge 3 点 + spike-revert 検査 (§3) へ

## 3. ナイフエッジ検査 (§2.1 / §3.1 / §7-3 — PASS arm B に全適用、arm A も記録)

維持要求 (凍結、§10-4 厳格側): **gross mean 符号 AND stressed-net mean 符号の両方**が全 frozen endpoint で正を維持。

| 検査 | arm B (PASS — 拘束) | arm A (記録のみ) |
|---|---|---|
| (i) DST NY17:00 anchor 再定義 | N=197/130wk、gross **+12.53p** / stressed **+5.97p** → **flip なし** ✅ | N=48、4h +12.82/+6.82、12h +8.25/+2.25 → flip なし |
| (ii) qualify 8×RT (−20%) | N=219、gross +14.71p / stressed +8.15p → flip なし ✅ | N=53、4h +11.77/+5.77、12h +8.18/+2.18 → flip なし |
| (ii) qualify 12×RT (+20%) | N=140、gross +15.50p / stressed +8.94p → flip なし ✅ | N=37、4h +15.43/+9.43、12h +8.94/+2.94 → flip なし |
| (iii) spike-revert flag 除外再計算 (§3.1) | flag 2 件除外 → N=175、gross **+15.20p** / stressed **+8.64p**、weekend-block **p<1e-4**、全ゲート再計算 ✅ → flip なし | flag 1 件除外 → N=45、4h +12.74/+6.74 (p<1e-4)、12h +6.26/+0.26 (p=0.1564) → flip なし |

- **spike-revert flag 一覧 (凍結規則: イベントバー Close が Friday close から |gap| の 20% 以内へ即時回帰)**: pooled 2 件 — EUR_USD 2022-07-29 (gap −24.6p) / AUD_USD 2022-03-18 (gap −64.7p)。arm A は 1 件 (EUR_USD 2022-07-29)
- 補足 (非ゲート): DST 定義での arm B MFE p50 は 21.90p と headroom 定数ちょうど — ただし knife-edge 維持要求は gross/stressed **符号のみ** (凍結) であり headroom は対象外
- **arm B: 4 検査全て flip なし → 格下げなし → 最終 PASS**

## 4. §4.1 shrinkage 事前予測 vs OOS 実測 (凍結記録との突合)

| endpoint | explore gross | 50% 減衰予測 | 予測 stressed-net | **OOS 実測 gross** | **OOS stressed-net** | 実測減衰率 |
|---|---|---|---|---|---|---|
| arm A 4h | +12.3p | +6.2p | +0.2p (限界的) | **+13.22p** | **+7.22p** | **−7%** (むしろ増) |
| arm A 12h | +15.6p | +7.8p | +1.8p | **+7.38p** | **+1.38p** | **53%** (予測どおり) |
| arm B 4h | +8.92p | +4.46p | −2.10p (負) | **+15.60p** | **+9.04p** | **−75%** (増幅) |

**事前記述との突合 (正直な記録)**: 事前予測は「現実的な PASS 経路は arm A の効果保存、arm B は 50% 減衰で FAIL」だったが、実際は**逆** — arm A 12h がほぼ正確に 50% 減衰して IUT を壊し (点推定は正でも p=0.1189)、arm B pooled 4h は explore 比 +75% に**増幅**して全ゲートを余裕で通過した。増幅の主因は診断上 USD_JPY (4h net +14.6p, p=0.0002) と AUD_USD (4h +18.3p) の OOS 寄与 — explore 窓では EUR_USD が牽引していた。効果の pair 構成が explore と異なる点は §6 構成シフト宣言の範疇であり、arm B の estimand (pooled 3 ペア) 自体は凍結どおり。

## 5. 完全性監査 (§3.1 — verdict 計算前に同一実行内で実施)

| pair | rows | weekends measured / 暦 | missing | skips (no_fri / no_sun / incomplete) | >1 週欠損区間 |
|---|---|---|---|---|---|
| EUR_USD | 112,061 | **232 / 234** (0.85%) | <10% ✅ | 1 / 0 / 1 | **なし** |
| USD_JPY | 111,759 | **232 / 234** (0.85%) | <10% ✅ | 1 / 0 / 1 | **なし** |
| AUD_USD | 110,314 | **232 / 234** (0.85%) | <10% ✅ | 1 / 0 / 1 | **なし** |

- explore 窓に存在した USD_JPY の穴 (2019-09 / 2020-10) は OOS 窓には**なし**。>10% 欠損ペアなし → 低下 N 注記は不要
- skip 2 件/ペアは窓端 (2022-01-02 跨ぎ + 2026-06 末の 120h forward 不足) — pre-reg §3 の事前明文化どおり

## 6. 診断 (§5 — 非ゲート)

**年次 qualifying 件数 (pooled、|gap| p50/p90)**: 2022: 42 件 (45.4/96.5p) / 2023: 48 (41.0/87.2) / 2024: 26 (45.2/103.3) / 2025: 34 (38.4/87.6) / 2026H1: 27 (36.2/68.1)。発生率 ~39 件/年は explore (21.1 件/年) の約 1.9 倍 — 2022+ の高ボラ regime (利上げ、円介入、キャリー巻き戻し) を反映。特定年への極端な集中なし。

**fill dynamics (§7-1 メカニズム整合、explore 参照形状: t-half 1–2h / t-full ~9–15h / MFE 優位)**:
| pair | t-half p50 | t-full p50 | 120h fill 率 | 4h MFE/MAE p50 |
|---|---|---|---|---|
| EUR_USD | 2.75h | 11.5h | 80.4% | 21.6 / 6.3p |
| USD_JPY | 1.0h | 2.75h | 89.2% | 42.3 / 10.7p |
| AUD_USD | 12.5h | 29.1h | 72.7% | 16.3 / 13.1p |

EUR_USD/USD_JPY は explore 同型 (即時 half-fill、MFE 優位で MAE 崩壊型ではない)。AUD_USD は遅め — pooled arm の中で最弱の fill 動学として記録 (非ゲート、R1 stage-2 設計への入力)。pooled 4h は MFE p50 24.8p vs MAE p50 9.9p で **MFE 優位** — 見かけの正値が MAE 崩壊による人工物ではない。

**tercile net@24h (期待形状 = flat/hump)**: EUR_USD は monotone **increasing** (explore と逆方向のシフト徴候として記録)、USD_JPY は monotone decreasing、AUD_USD は non-monotone。ペア間で形状不一致 = 「大ギャップほど埋まる」型の一般主張は OOS でも**成立しない** (pre-reg §1 のとおり主張しない)。

**擬似反復 (§7-2)**: 同一週末複数ペア qualifying = 50 週末 (分布 1ペア:62 / 2ペア:35 / 3ペア:15) — weekend-block bootstrap がこの相関をブロック化済み。週末レベル net4h lag-1 ρ = **−0.059** (系列依存なし)。arm A イベント非重複 assert 通過 (全間隔 >12h)。

**全ホライズン透明性出力 (判定外)**: pooled net mean は 4h +15.6 / 12h +11.2 / 24h +15.0 / 72h +23.8 / 120h +32.1p だが、12h 以降の p は 0.0388〜0.0169 で凍結 endpoint (4h) より弱く、MAE も比例拡大 (explore の multiday 棄却と整合)。判定は凍結 endpoint のみ。

## 7. 拘束事項の再掲 (pre-reg 要求)

- **AUD_USD RT 2.5p は KB friction table 外の理論仮置き** (§2 の verdict 再掲義務) — arm B の stressed 6.56p 固定にもこの仮置きが混入している。R1 手続き 1 (実スプレッド ≥8 週末実測) で必ず置換
- swap: 保有 ≤12h のため無視 (multi-week 条項非該当)
- GBP_USD OOS は未接触のまま維持 — 将来の「GBP continuation」新 family 用に清浄
- **禁止 (§9)**: endpoint/arm/閾値の事後変更、OOS 再接触・再実行、news-type 事後サブセット化。arm A の「4h 単独なら…」という再集計は**明示的に禁止された救済**である
- 台帳: [[hypothesis-catalog-2026-07-24]] family #3 の OOS スロット消費 (m=12 内)。PASS 率の帰無突合のため全 verdict 追記式記録

## 8. 次のアクション (§4.2 固定分岐 → §9)

1. family #3 = **PASS 候補** (arm B)。arm A (EUR_USD 単独 co-primary) は本 verdict でクローズ
2. **即 live 禁止**。R1 手続き (省略不可): (i) OANDA live で日曜 open 実スプレッド ≥8 週末実測 → 3× 仮定の検証/置換 + EV 再計算 → (ii) 執行設計 pre-reg stage-2 (entry mechanics / サイジング / time-exit 4h 実装 / 部分 fill) → (iii) user 最終承認
3. 台帳 row #3 更新 + pre-reg 本文書へ verdict 追記 (§8 成果物) — 実施済み
