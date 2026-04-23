# Meta-Lesson: なぜ MTF/regime 逆校正を過去何度も見逃したか

**Date**: 2026-04-23
**Type**: 自己反省 (meta)
**Trigger**: ユーザーから「MTF とレジーム判定ロジック問題ないか何度か聞いていた」との指摘

## 事実確認

2026-04-23 に判明した逆校正問題:
- VWAP alignment: aligned WR 20.0% vs conflict 26.7% (Delta -6.7pp)
- 機関フロー has: Delta -10.4pp
- 「方向一致」ラベル has: Delta -16.2pp
- MTF alignment aligned: WR 10.0% (TF内)
- HVN has: Delta -6.3pp

これらはすべて **複数セッション前から問題として存在**していたはずで、ユーザーから
「MTF/regime 判定問題ないか」と聞かれた複数の機会に発見できなかった。

## なぜ見逃したか — 原因分析

### 1. ラベル文言を「設計意図」として信頼し実測しなかった (主因)

コード内の `"BUY確度UP"` `"BUY方向一致 (+3)"` `"S/R確度UP"` といった断定的ラベルを
**動作している前提**で扱っていた。「確度UP」と書かれていれば確度が上がっているはず、
という暗黙の信頼。

- 検証すべき問い: 「このラベル付きトレードは実際に WR が高いのか?」
- 実際にやったこと: コードを読み、ロジックの妥当性を**演繹的に**判定
- 本来やるべきだった: `WHERE reasons LIKE '%方向一致%'` で WR を直接測定

これは **"コードが正しければ結果も正しい"** という開発者的な思考から来ている。
クオンツ的には「コードの挙動と市場での効果は別問題」として常に分離して計測すべき。

### 2. Aggregate stats だけ見て分解しなかった

過去の分析で「全体 WR 22%」「confidence 70+ の WR 25%」のような粗い集計は実施していた。
しかし以下の分解を怠った:

- **ラベル × WR** の直接 join (1クエリで判明したはず)
- **bucket × strategy category** の 2D (今回初実施)
- **reasons-tag 含有フラグ × WR** (今回初実施)

「何かおかしい」は感知していたが、**それが逆校正(符号問題)なのか単なる弱小エッジなのか**
を区別する分解をしていなかった。

### 3. TF-bias な仮説フレーム

過去の議論で「VWAP 上位なら TF は強い」「機関フローが一致すれば BUY 強い」といった
TF semantics を既定としていた。そのため:

- Shadow の多くが MR 戦略だという事実を軽視
- MR にとって「aligned」が逆作用する可能性を最初から除外していた
- ユーザー質問「判定ロジックに問題ないか?」に対して **TF仮説の内部整合性**だけを
  チェックして「問題なし」と回答

### 4. Lesson "partial_quant_trap" の不完全な適用

[feedback_partial_quant_trap](/Users/jg-n-012/.claude/projects/-Users-jg-n-012-test/memory/feedback_partial_quant_trap.md)
には「N/WR/EV だけでは不十分、PF/Wilson CI/WF/Bonferroni/Kelly まで」と書いてある。
これは **昇格判断** に関する教訓で守っていた。

しかし **既存ロジックの監査** に同じ厳格さを適用していなかった。
「既に動いているもの」に対しては統計的検証の網をかけていなかった。

### 5. Confirmation bias — 既存実装への信頼

MassiveSignalEnhancer, MTF gate などは以前のセッションで設計された機能で、
「過去に実装時に検証された」という暗黙の前提を持っていた。実際には当時のデータ量・
shadow カバレッジは少なく、検証は不十分だった可能性が高い。

新規分析でベースラインにアクセスした時も「既存の confidence は機能している」
前提で、calibration 自体を疑わなかった。

### 6. 1クエリで暴けたのに着手しなかった

今回 `/tmp/tf_inverse_rootcause.py` は 160 行、実行数分で判明した。
過去に同じ質問を受けた時、なぜこれを走らせなかったか:

- 「MTF 判定は問題ない (コード的に妥当)」で質問に回答完結してしまった
- ユーザーの懸念が「コードレベルの問題」ではなく「効果(EV)が出ているか」
  だったことを汲み取らなかった
- **「問題ないか」= 二値質問 と受け取り、計測実行を提案しなかった**

## 本当にやるべきだった会話フロー

過去のセッションで「MTF/regime ロジック問題ないか?」と聞かれたとき、
正しい応答は:

```
Q: MTF/regime ロジック問題ないか?
A (過去の私): コードを見ましたが設計は妥当、特に問題見当たりません。
A (あるべき私):
  「問題ない」は計測結果で定義します。
  - MTF alignment × WR を shadow post-cutoff で分解
  - Aggregate では見えないため category × alignment の 2D を必須
  - 今から /tmp/mtf_audit.py を回します (所要2-3分)
  結果を見るまで「問題ない」とは言えません。
```

## 予防策 (今後適用)

### Rule 1: ラベル実測ルール

コード内の断定ラベル (`"*確度UP"` `"*方向一致"` `"BUY強化"` 等) に遭遇したら、
**ラベル付与データの WR を直接測定するまで信用しない**。

検証クエリテンプレート:
```sql
SELECT
  CASE WHEN reasons LIKE '%{label}%' THEN 'has' ELSE 'no' END AS tag,
  COUNT(*) AS n,
  100.0 * SUM(CASE WHEN pnl_pips > 0 THEN 1 ELSE 0 END) / COUNT(*) AS wr
FROM demo_trades WHERE is_shadow=1 AND status='CLOSED' AND entry_time >= ?
GROUP BY tag;
```

### Rule 2: 二値質問を分解質問に変換

ユーザーから「X は問題ないか?」形式で質問を受けた場合:

1. 「問題ない」の定義を数値で明確化 (例: "WR が label_on > label_off で
   統計的有意")
2. その数値を測定するクエリ/スクリプトを提示
3. 実測結果で回答

### Rule 3: Calibration audit を四半期 cadence で

`tools/vwap_calibration_monitor.py` を拡張して週次定点観測。
全 enhancer の add-flag × WR 相関を monotonic check。

### Rule 4: 実装監査と運用監査を分離

- 実装監査: コードロジックの数学的整合性
- 運用監査: ラベル/gate/加点が実データで期待効果を出しているか
- **「コードが正しい」=「効果がある」ではない**

### Rule 5: shadow DB を信用せず再標本

shadow トレードの aggregate だけでなく、**labeled subset の
Wilson/Bootstrap CI** まで下ろすのを標準化。

## memory 更新

- `feedback_label_empirical_audit.md` を新規作成
- 「partial_quant_trap」と並ぶ上位 feedback memory として運用

## クオンツ的教訓の一般化

> 「コードが設計通り動いている」と「その設計が市場で効果を発揮している」
> は独立した2命題。前者は演繹、後者は帰納。
>
> **演繹で済ませた瞬間、逆校正 bug は何四半期も生存する。**

## References

- [[vwap-calibration-baseline-2026-04-23]]
- [[tf-inverse-rootcause-2026-04-23]]
- [[lesson-vwap-inverse-calibration-2026-04-23]]
- [[lesson-mtf-gate-inversion-observation-2026-04-23]]
- User memory: [feedback_partial_quant_trap](/Users/jg-n-012/.claude/projects/-Users-jg-n-012-test/memory/feedback_partial_quant_trap.md)
