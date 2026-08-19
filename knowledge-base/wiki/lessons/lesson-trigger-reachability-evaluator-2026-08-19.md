# 教訓: 「常時 WATCHING」は監視ではない — 条件付きトリガの評価器レベル欠陥 (2026-08-19)

**分類**: rule:R3 (構造バグ) / ZN 教訓 (external-hypothesis-scan-round3-2026-08-14 / MEMORY `project_edge_scan_round3_2026_08_14`) の **4 例目**
**関連**: [[family-c-anchor-automation-2026-08-18]] / `knowledge-base/wiki/decisions/prereg-trigger-registry.json`

## 何が起きたか

`prereg_trigger_watch.py` の `info` / `conditional_info` 型は、評価器の
dispatch で **無条件に `STATE_WATCHING` を返すハードコード**だった。

```python
elif ttype in ("info", "conditional_info"):
    res = {"state": STATE_WATCHING, "detail": trig.get("condition") or "..."}
```

つまり `condition` フィールドに書かれた発火条件は **一度も評価されない**。
どれだけ条件が成立しても TRIGGERED にならない設計だった。

実害: `statement-ladder-foundation-readiness` は条件「当局発言ラダー基盤が
main に着地したら発火」が **PR #194 (commit 569dbe3f, 2026-08-18) の着地で
既に成立していた**のに、翌日も `👁 watching` 表示のままだった。
このトリガは family A (発言ラダー→介入確率) の pre-reg 起草ゲートであり、
**能動測定ラインが 0 本の状況で、唯一動かせる供給ライン作業が黙って止まっていた**。

さらに `deadline` フィールドも無視されていたため、期日付き手動エントリ
(`volstate-split-*` 2027-01-31 / 2026-12-31、`carry-dip-v3-revival-watch`
2026-11-30) は **自分から期限切れを名乗ることができなかった**。

## なぜ 4 回も繰り返したか

過去 3 例は「個別エントリの到達経路が無い」という **データ側**の欠陥だった
(ZN cache overwrite で条件到達不能 / 計数器契約バグ ×2)。
今回は **評価器側** — つまり entry をどれだけ正しく書いても発火しない。
「到達経路を message に書く」という従来の対策は、評価器が条件を読まない限り
効かない。対策が一段浅い層に留まっていた。

## 恒久対策 (本 PR)

1. **機械評価型を 2 つ追加** — 条件を人手判定に委ねない
   - `artifact_presence`: 成果物 (glob + `min_files`) の実在で判定。
     「main に着地したら発火」型を実ファイルで評価する
   - `data_coverage`: cache の被覆 max 日付 vs 閾値日付。
     「cache が延伸したら発火」型 (ZN=F 1h) を実データで評価する
2. **`info`/`conditional_info` にも `deadline` を効かせる** (`evaluate_manual_info`)
   — 期日超過で TRIGGERED。手動エントリでも滞留を検出できる
3. **到達経路 lint** (`lint_reachability` / `--lint`) — 機械評価型でないエントリは
   `reachability` (誰/どのジョブが状態を進めるか) の明記を **必須**にし、
   pytest で強制。これが 5 例目の再発防止の本体

## 一般化して覚えること

> **「watching」表示は健全性の証拠ではない。**
> 監視エントリを追加したら「どの入力が変化したらこの行が TRIGGERED に変わるか」
> を必ず 1 つ挙げること。挙げられないなら、それは監視ではなく**メモ**である。
>
> 条件を人手判定に委ねる型を作るときは、**評価器がその型で TRIGGERED を
> 返しうるか**をコードで確認する。型の追加は「状態遷移が起こりうるか」の
> 検査とセットにする。

## 副次成果

- `statement-ladder-foundation-readiness` は発火 → **resolve 済み**。
  family A の pre-reg 起草ゲート解除 (09-18 スキャンの A/B/C 統合裁定の前提材料)
- `ws3-round4-eur-divergence-conditional` は実測値表示に変化
  (「被覆 2026-08-18 / 閾値 2026-11-15 まで延伸待ち」) — 延伸経路の実在も同時に確認
