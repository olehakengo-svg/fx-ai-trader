# family A statement_ladder — pass-1 readout (2026-09-18)

**凍結**: [[family-a-statement-ladder-prereg-2026-08-19]] §10 (2026-09-18、PR #265)
**ハーネス**: `tools/family_a_pass1.py` (凍結検出器 `tools/family_a_ladder_detector.py` を実行)
**生値**: `knowledge-base/raw/analysis/family-a-pass1-events-2026-09-18.json`

> **label 非接触**。本 readout で参照したのは `lexicon_scores.csv` のみ。
> `interventions_daily.csv` は開いていない (`tests/test_family_a_pass1.py` で構造 pin)。
> pass-1 の存在理由は「explore outcome に触れずに park 判定できること」(pre-reg §10.3)。

---

## 1. 結果: **Gate A / Gate B ともに PASS → pass-2 解錠**

| gate | 凍結条件 | 実測 | 判定 |
|---|---|---|---|
| **Gate A (特異度)** | armed 営業日率 ≤ 0.25 | **0.1327** (147 / 1,108 bd) | ✅ PASS |
| **Gate B (供給)** | event ≥ 5 かつ相異なる暦年 ≥ 2 | **event 7 / 暦年 2 (2022, 2026)** | ✅ PASS |

Gate A の実測 0.133 は、凍結時に論拠として書いた設計期待 (event 5–8 本 × 21bd / 約 1,120bd
= **9–15%**) の中に入った。閾値 0.25 はその約 2 倍に置いてあり、**データを見ずに置いた
閾値が実測と整合した** = 事後的に緩めた閾値ではない。

## 2. イベント (7 本、rearm R=20bd 後)

```
2022-05-19   2022-09-29
2026-01-16   2026-03-17   2026-04-24   2026-05-29   2026-06-30
```

## 3. 窓内サマリ

| 項目 | 値 |
|---|---|
| explore 窓 | 2022-01-07 〜 2026-07-29 (凍結) |
| 営業日 | 1,108 |
| 窓内の会見 | 464 |
| 実効水準ヒストグラム | L0:287 / L1:22 / L2:37 / L3:101 / **L4:17** / **L5:0** |
| 非営業日会見 (翌営業日へ roll) | 13 件 (A-8) — うち **2026-05-04 は L4** |

**L5 が 0 件**なのは A-1 の remap が効いているため (corpus の L5 は全て retrospective で
talk 水準へ降格)。`レートチェック` は explore 窓に 1 件も出現していない。

## 4. ⚠️ 凍結条件を満たした上での正直な power 所見 (verdict で必ず併記すること)

- **Gate B は下限ぎりぎりで通っている** — 相異なる暦年は **ちょうど 2**、内訳は
  **2022: 2 本 / 2026: 5 本**。L4 `断固` の年次分布 (2022:3 / 2023:0 / 2024:0 / 2025:0 / 2026:13)
  のとおり、**イベント供給の 5/7 は片山期**に集中する。
- Gate B の「暦年 ≥ 2」は A-6 でまさにこの交絡を分離するために置いた条件であり、
  **通ったのだから pass-2 は解錠する**。ただし「話者非依存の検出器である」ことを
  示したわけではない — verdict では **speaker-stratified な記述 (secondary)** を併記し、
  **2022 の 2 本だけで結論が反転しないか**を必ず点検する。
- **閾値の事後強化は禁止** (§10.5)。ここで「暦年 ≥ 3 にすべきだった」と動かすのは
  ゴールポストの移動であり、pre-reg の破棄に等しい。所見は **caveat として書く**のであって
  gate を変えない。
- 有効 N = 4 episode blocks の拘束は不変 — **PASS しても主張上限は記述級**。

## 5. 次: pass-2 (測定)

pre-reg §10.2 の凍結どおり:

- 統計量 **J = P(armed | 介入日) − P(armed | 非介入日)** (day-level Youden、m=1)
- Null = episode-block circular-shift、**B = 10,000**。相異なるシフト数が B を下回る場合は
  全数を使い `p = (1 + #{J_shift ≥ J_obs}) / (1 + #shifts)`
- **α = 0.05 片側** (J > 0)
- verdict 分岐 = §10.4。期日 = registry `family-a-explore-verdict-deadline` (**2026-09-28**)

**本 readout をコミットしてから pass-2 を走らせること** (pre-reg §10.3 の two-pass 手続き。
イベント集合を先に凍結してから outcome に触れる = event set のチューニング防止)。
