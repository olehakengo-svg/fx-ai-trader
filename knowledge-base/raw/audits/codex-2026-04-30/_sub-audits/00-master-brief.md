# Master Brief — Codex 並列クオンツ監査 (2026-04-30)

すべてのサブ監査タスクは本ファイルを必ず先に読み、共通前提と出力フォーマットを遵守すること。

---

## ミッション

シニアクオンツ × プロフェッショナル監査人として `fx-ai-trader` を監査する。

ユーザーから与えられた監査の核:
1. **バグはないか** (loss-of-fund / silent statistical contamination / maintainability)
2. **ロードマップ達成に進めているのか** — 月利100% (¥454,816/月) / 年利1,200%
3. **負けているエッジが「なぜ負けか」「どう調整すれば勝てるか」**
4. **構造的問題がないか**

---

## ロードマップ目標 (絶対基準)

- ロードマップ v2.1: `knowledge-base/wiki/syntheses/roadmap-v2.1.md`
- 目標 PnL: **月利100% (¥454,816/月) → 年利1,200%**
- 想定エッジ: DT 433pip/年 + Scalp 200pip/年 = 約 **+633pip/年**
- ゲート構造:
  - Gate 0 [即時]: DT LIVE + Scalp SENTINEL + AVOID 全停止
  - Gate 1 [W1-2]: Aggregate Kelly > 0 → DD 0.2x → 0.3x
  - Gate 2 [W2-3]: Kelly>0.05, PnL>+50pip, 破産<70% → 0.3x → 0.5x → ★月利100%
  - Gate 3 [W4-6]: PF>1.0, N≥100, 破産<30%, DSR>0.80 → 1.0x
  - Gate 4 [W8+]: DSR>0.95, 破産<10%, N≥200 → Kelly Half (3.0lot)

---

## クオンツ規律 (memory: feedback_*)

- **クオンツファースト**: 分析→判断→実装の順序
- **部分的クオンツの罠を回避**: N/WR/EV だけで結論しない。
  必ず **PF / Wilson CI / WF / Bonferroni / Kelly** まで出す
- **ラベル実測主義**: 「X のロジックは問題ないか?」をコードの演繹だけで答えるな。
  ラベル × WR の実測クエリを根拠にせよ
- **XAU は損失分析・ラベル分析から除外**
- **KB は更新するもの、絶対視も無視も禁止** (CLAUDE.md 参照)
  - 新データ × 統計的に堅い分析 が KB を更新するなら、KB を変える方向で判断
  - 「KB に書いてあるから」「書いてないから」の思考停止は規律違反

## 4 原則 (絶対遵守)

1. マーケット開いてる間は攻める
2. デスゾーン = スプレッド異常 (動的検出) のみ
3. 静的時間ブロックは使わない
4. 攻撃は最大の防御 (フィルター積み上げよりデータ蓄積を優先)

---

## 既知の重要事実 (監査前に頭に入れておくこと)

- 直近で `_bt_regime_cascade_scalp_vec.py` の `simulate_outcome()` に
  **pip_mult バグ 2 件** 発覚 (obs 641-643, 2026-04-30):
  1. EXPIRED trade の PnL が non-JPY pair で 100倍 過小計算
  2. `pip_mult` が常に truthy 判定される条件分岐
  → Sub 5 はこのバグを再検出するだけでなく、**他 BT ランナー 22 本に同型バグが波及していないか横展開チェック** を行うこと

- `bb_rsi_reversion` ライブパフォーマンス急速悪化 (obs 639): 5 日間で -34.1pip
- `session_time_bias` ライブパフォーマンス更新 (obs 638): N=6, WR=16.7%, PnL=-33.4pip
- M3 SCORE_GATE 修正後 (obs 626): ELITE_LIVE SELL 戦略の発火確認、session_time_bias が 0件→8件へ
- ML Training NameError (`symbol` 変数スコープ外) は修正済み (S333)
- 当日 wiki snapshot (obs 636-640): DD 36.78%, Kelly edge -19.22%, bb_rsi_reversion 急劣化

---

## 共通出力フォーマット (厳守)

各サブ監査は本フォーマットで `XX-name.md` に出力する。

```markdown
# Sub XX: {タスク名}

## Scope
{自分の監査対象ファイル一覧と行範囲}

## 1. Bugs Found
| # | Severity | File:Line | Description | Root Cause | Suggested Fix |
|---|----------|-----------|-------------|-----------|--------------|
| 1 | Sev1 | path/to.py:123 | ... | ... | ... |

Severity 定義:
- **Sev1**: 損益に直結 (誤PnL, 注文重複, データ破損, ライブ停止)
- **Sev2**: 統計汚染 (BT-Live 乖離, ルックアヘッド, ラベル汚染)
- **Sev3**: 保守性・スタイル

## 2. Structural Issues
番号付きで根拠 (該当ファイル/行) を必ず添える。

1. {問題タイトル} — {根拠} — {推奨対応}
2. ...

## 3. Losing Edge Analysis (Sub 6 のみ必須、他は該当時のみ)
| Strategy | Cell | N | WR | PF | Wilson Lower | Kelly | 負けの帰属 | 調整案 |

帰属候補: regime mismatch / friction 過小評価 / signal lag / 重複戦略 / 統計ノイズ (N不足)

## 4. Roadmap Alignment
- 自分のスコープ内で、ロードマップ Gate 進行を阻害している要素は何か
- 律速要因 (DD / Kelly / DSR / 破産確率 のうち)
- 自分のスコープから提案する加速施策

## 5. Top 3 Action Items (impact 順)
1. {action} — Impact: {期待効果} — Confidence: {根拠の強さ low/med/high}
2. ...
3. ...

## 6. Out-of-Scope Findings (オプション)
範囲外で偶然見つけた重要事項。マスター統合で他サブと突き合わせる材料。
```

---

## ハードルール

- **範囲外は触らない / 範囲内は深く掘る**
- 推測ではなくコード/データの引用で語る (`file:line` を必ず付ける)
- 統計的主張には N と CI を併記
- 「問題なし」と結論する場合も、何を確認したかを明示
- 改善提案は「現状 → 提案 → 期待効果 → リスク」の 4 点セットで書く

---

## 参考リンク

- [CLAUDE.md](../../../CLAUDE.md) — クオンツ規律全文
- [roadmap-v2.1.md](../../../knowledge-base/wiki/syntheses/roadmap-v2.1.md)
- [tier-master.md](../../../knowledge-base/wiki/tier-master.md)
- [index.md](../../../knowledge-base/wiki/index.md)
