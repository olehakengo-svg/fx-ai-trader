# 教訓: 構造欠陥を 1 箇所直したら、同じ形の兄弟を同じ PR で掃くこと (2026-09-17)

**rule**: R3 / **発見**: [[../research/external-hypothesis-scan-round5-2026-09-17|外部仮説スキャン第5次]] §1.2-1.3
**欠陥族**: 「多ソース直列 ingest + 無条件 commit step」= 1 ソースの失敗が全ソースの成果を破棄する

## 何が起きたか

2026-09-10 (第4次スキャン) で `rate_anchor_ingest` の**同一欠陥**を発見し、per-source 隔離 + workflow commit step の `if: !cancelled()` 化で修復した。しかし**同じ形を持つ姉妹ツール `mof_statements_daily` を検査しなかった**。

7 日後、その姉妹ツールで欠陥が**実データ欠落として顕在化**した:

- `mof-statements-daily` は直近 20 run で **8 失敗 (40%)**、単一根因 = GDELT の HTTP 429
- `main()` が 5 ソースを dict literal で直列評価 → 最後段 GDELT の raise が**先に成功した 4 ソースごとプロセスを落とす**
- workflow の "Commit data" step に `if:` が無く、collect 失敗時に走らない → runner の ephemeral disk ごと消える
- 実害: 失敗 run 35163419350 は `[daily-conf] new=1` (my20260915.html) / `[daily-rss] new=1` / `[score] 512 conferences` まで到達して**全破棄**。repo は 511 conferences で取り残されていた

## なぜ悪質だったか

失われかけたのは **negative sample** だった。回収した `my20260915.html` の lexicon スコアは **L 語句ヒット 0** — family A (#27) の検出器は「発言ラダー → 介入確率」であり、その価値は **FP 率の較正**にある。negative を落として positive だけ残す欠損は、検出器の precision を**機械的に押し上げる**方向のバイアスで、凍結期日 (09-24) の 1 週間前に起きていた。

## 教訓

1. **欠陥は族で存在する。** 「多ソース ingest」「無条件 commit step」のような形を 1 つ直したら、**同じ形を grep して同じ PR で掃く**。横展開コストは grep 1 回、放置コストは今回 = 実データ欠落 + 7 日の潜伏。
2. **「自己回復するので恒久損失なし」を ingest 設計の性質として述べるな。** 救っているのは**上流アーカイブの永続性**であって ingest ではない。ソースごとに保証は違う — MoF conferences は恒久アーカイブ (回収窓 ~1 ヶ月) だが **RSS はローリング窓で救済が構造的に存在しない**。第4次の「日次 union だから恒久損失なし」は rss について**偽**だった。
3. **慢性的に失敗するソースを hard 扱いのまま放置すると、アラートが死ぬ。** 40% の頻度で鳴る失敗通知は読まれなくなる = 「読み手のいない検知器」の再生産。全範囲を毎回再取得する派生系列 (GDELT) は **soft** に分類し、警告のみ・exit 0 とする。soft 集合の拡大は「失敗が観測されなくなる」ことなので **test で pin する**。

## 再発防止 (実装済み)

- `tools/mof_statements_daily.py`: `_STEPS` タプル + per-source try/except、**全ソース試行後**に hard 失敗のみ raise。失敗も summary に `error` を残す
- `_SOFT_SOURCES = {"gdelt"}` — soft は警告のみ。**集合そのものを test で pin**
- `.github/workflows/mof-statements-daily.yml`: "Commit data" を `if: ${{ !cancelled() }}`
- `tests/test_mof_statements_daily_isolation.py` 4 本 (soft 非 raise / hard raise / **raise は全ソース試行後** / soft 集合固定)

## 関連

- [[../research/external-hypothesis-scan-round4-2026-09-10]] (§1.1 — 1 例目・2 例目の修復。横展開を欠いた)
- [[../research/external-hypothesis-scan-round5-2026-09-17]] (§1.2-1.4 — 本件の全記録)
- [[../decisions/family-a-statement-ladder-prereg-2026-08-19]] (#27 — 被害を受けたコーパスの利用者)
