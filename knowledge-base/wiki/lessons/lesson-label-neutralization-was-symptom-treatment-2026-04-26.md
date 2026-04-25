# Lesson: ラベル神経化アプローチは症状治療だった (2026-04-26)

**Date**: 2026-04-26
**Type**: Meta-lesson (KB narrative の根本誤りを修正)
**Trigger**: ユーザー発言「現時点勝ててない、エッジがない、MTFの判定が出来ない」
**Severity**: 🔴 Highest — 過去 1 ヶ月の作業方針の根本誤り

## 1. 何が誤っていたか

2026-04-23 以降、私は「断定的ラベル (`*確度UP` `*方向一致` `BUY強化` `S/R確度UP`) の付与有無で WR を測定し、逆校正ラベルを発見したら conf_adj を中立化する」というアプローチで:

- VWAP zone (Δ-6.7pp 逆校正発見 → 中立化)
- 「方向一致」ラベル (Δ-16.2pp → 中立化)
- 機関フロー (Δ-10.4pp → 中立化)
- HVN/LVN (Δ-6.3pp → 中立化)
- MTF alignment (TF Δ-7.5pp → Phase 0 で disable)

を順次中立化してきた。`feedback_label_empirical_audit.md` を memory に追加し、「問題ないか?」質問に対する empirical 回答ルールも整備した。

これらの作業自体は数学的に妥当だった (実害ある signal を消した)。しかし**根本的な誤りが 2 つあった**。

## 2. 根本的な誤り

### 誤り 1: Edge 不在を覆い隠していた

ラベル中立化は「実害ある signal を消す」作業であり、「edge を作る」作業ではない。

実際の Live データ (post-2026-04-08, FX-only):
- N=259, WR=39.0%, Kelly=**-17.97%**, PnL=**-215 pip**
- TP-hit grid (N≥50) で **16/16 cells すべて BEV gap < 0**

つまり戦略レベルで edge が**負**。ラベル中立化を完璧にやっても、戦略の負 EV はそのまま残る。

「ラベルを中立化すれば WR が改善する」という暗黙の期待は、edge があった場合の話。
edge がない時にラベル中立化しても、ラベル付き has と no の WR が**両方同じくらい悪くなる**だけ。

### 誤り 2: KB narrative が誤った方向を強化していた

`feedback_label_empirical_audit.md` および `lesson-why-missed-inversion-meta-2026-04-23.md` は:

- 「コードが設計通り動いている」と「市場で効果を発揮している」を分離する原則 ✅ 正しい
- ラベル付き WR を直接測定する手法 ✅ 正しい

…までは正しい。しかし**そこで止まり**、edge そのものの存在検証に進まなかった。

「逆校正ラベルを潰せば直る」という暗黙の楽観があり、それが KB narrative として強化され、
私自身が「次は何のラベルを監査するか」というループに閉じこもっていた。

ユーザーは別セッションで Phase 5 (5m Pure Edge 9 戦略 BT) を進めており、結果は **6/9 DEAD + 3/9 SURVIVOR 兆候**。これは「edge 不在」を独立に確認していた。
私はそのコンテキストを参照せず、ラベル神経化を続けようとしていた。

## 3. 本来やるべきだった分解

ユーザー発言「MTF/regime ロジック問題ないか?」を受けた時、本来は 2 段階の問いに分解すべきだった:

### Q1 (System): ラベル付与 × WR の関係は妥当か? (= ラベル神経化の問い)

→ これは私がやっていた問い。逆校正発見 → 中立化で対応可能。

### Q2 (Strategic): そもそも、その戦略の base WR / EV は edge を持っているか?

→ これを問わなかった。Q2 を問わずに Q1 だけやっても、edge 不在を治せない。

Q2 の答えが No なら、ラベル神経化はゼロベース付近の signal を整えるだけで PnL に意味のある影響を与えない。

## 4. なぜこれを見逃したか

### 理由 (a): 「partial_quant_trap」を昇格判断のみに適用

`feedback_partial_quant_trap.md` (PF/Wilson CI/WF/Bonferroni/Kelly まで) は新戦略昇格時のチェックとしては守っていた。
しかし**現存戦略の維持 (incremental tuning)** には適用していなかった。
「既に動いている戦略の edge は別途検証必要」という発想が抜けていた。

### 理由 (b): ラベル監査が「成果が見える」作業だった

ラベル中立化は commit 単位で「Δ-X pp 逆校正を発見、中立化」と数値化できる。
心理的に達成感がある。一方で「戦略を再設計する」は数ヶ月単位で結果が出ず、達成感が出にくい。
**達成感の出やすさで作業優先度が決まっていた** (anti-pattern)。

### 理由 (c): 「KB の積み上げ」を進捗と錯覚していた

VWAP calibration baseline / TF rootcause / mtf inversion observation 等の KB ページが増えるたびに「進捗あり」と感じていた。
実態は「同じ症状の異なる露呈を記録していただけ」で、edge 再構築には進んでいなかった。

### 理由 (d): Phase 5 (別セッションの BT 結果) を活用しなかった

cbbbc8b で Phase 5 の「5m Pure Edge 6/9 DEAD」が記録されていたのに、私のセッションはそれを参照せず、ラベル神経化を続けようとしていた。
**並行する work stream を統合して全体最適化する視点が欠落**。

## 5. 修正された動作 (今後)

### Rule N: 「問題ない?」に対する 2 段階分解 (拡張版)

ユーザーから「X は問題ないか?」と聞かれたら:

1. **Q1 (Calibration)**: ラベル付与 × WR を測定 ← 既存ルール
2. **Q2 (Edge existence)**: 戦略 base の WR/EV/Kelly が正か測定 ← 追加
3. **Q1 が逆校正なら中立化、Q2 が負なら戦略レベル再設計**

Q2 が負なら Q1 の作業はほぼ無意味と判定する。

### Rule N+1: KB の積み上げを進捗と錯覚しない

KB ページが増えても、Live Kelly / WR / PnL が改善していないなら**進捗ゼロ**と認識する。
「KB 充実度」ではなく「Live PnL の trend」を進捗指標とする。

### Rule N+2: 並行 work stream の必須統合

session 跨ぎで複数の work stream (label audit / Phase 5 BT / friction calibration / cell routing 等) が並行する場合、
**新規作業を始める前に最新コミット (`git log --oneline -10`) と関連 KB lesson を読む**。
別ストリームが既に同じ結論に到達していないか確認する。

## 6. 方向転換 (2026-04-26 Edge Reset)

`wiki/decisions/edge-reset-direction-2026-04-26.md` で:

- ラベル神経化の incremental 作業を停止
- Phase 1: MTF を真に機能させる (OANDA native H4/D1 + category 分岐)
- Phase 2: 全戦略の mechanism thesis 棚卸し (thesis なしは shadow 除外)
- Phase 3: TF/Range の高勝率エッジ研究 (mechanism thesis 必須)

## 7. 一般化された教訓

> 「ラベルが正しく付与されているか」と「ラベルが指す戦略に edge があるか」は独立した 2 命題。
> 前者だけ完璧にしても、後者がなければ Live で勝てない。
>
> **症状治療を続けることで、根本治療への着手が何ヶ月も遅れる。**
>
> KB が充実しても Live Kelly が負なら、それは進捗ではない。

## References

- [[edge-reset-direction-2026-04-26]] — 方向転換決定
- [[lesson-why-missed-inversion-meta-2026-04-23]] — 前 meta-lesson (本 lesson が補強)
- [[bt-live-divergence]] — BT 楽観バイアス 6 因子
- [[friction-analysis]] — 実測 friction
- Phase 5 lesson (cbbbc8b): 5m Pure Edge 6/9 DEAD — 並行 stream の独立検証
- User memory: `feedback_label_empirical_audit.md` (継続維持、ただし Q2 を追加)
- User memory: `feedback_partial_quant_trap.md` (現存戦略の維持にも拡張適用)
- Plan: `/Users/jg-n-012/.claude/plans/luminous-fluttering-shannon.md`
