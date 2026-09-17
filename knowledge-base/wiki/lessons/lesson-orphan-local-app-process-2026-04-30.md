---
title: 9日間放置されたローカル app.py オーファンプロセスがローカル DB を汚染し続けていた
date: 2026-04-30
type: lesson
severity: HIGH
related: [[lesson-data-source-production-first-2026-04-28]], [[lesson-is-shadow-filter-mandatory-2026-04-30]], [[lesson-shadow-vs-live-confusion-2026-04-28]]
---

# 9日間放置されたローカル app.py オーファンが DB を汚染 (2026-04-30)

## 何が起きたか

「本日 Tokyo セッションが調子いいのは fix のおかげか?」を分析中、ローカル `demo_trades.db` には本日 Tokyo の trade が **2 件 (両方 OPEN)** しか無く、本番 Render API には **65 件 (60 closed + 5 open)** あった。

「ローカル DB と本番が完全 sync 不良」と表現したが、調査の結果これは **設計通りの DB 分離 + ローカル開発プロセスの暴走** の合成事象だった。

```
PID 33137  jg-n-012  47.1% CPU  Apr 21〜現在 (9 日間)  1851 min  python3.9 app.py
```

→ 2026-04-21 から **9 日間ノンストップで動作していたローカル `app.py`** が、独自にシグナル評価・shadow trade 発火・OANDA pricing 呼び出しを続け、ローカル DB に 475 件の "phantom" trade を蓄積していた。本日 Tokyo の 2 件もこのプロセスが書き込んだもので、本番 trade_id とは一切一致しない。

## 設計と実態のギャップ

### 設計

[README.md:121,127] / [CLAUDE.md "Production Environment"]:
- 本番 DB: `/var/data/demo_trades.db` (Render 永続ディスク)
- ローカル DB: `./demo_trades.db` (開発用、本番との sync 機構なし)
- ルール: **「分析は本番(Render)データを使用。ローカルDBは開発用のみ」**

[app.py:12284-12288] の DB パス選択ロジック:
```python
_render_disk = "/var/data"
if os.path.isdir(_render_disk):
    _db_path = os.path.join(_render_disk, "demo_trades.db")
else:
    _db_path = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "demo_trades.db"))
```

### 実態

ローカルで `python app.py` を一度起動すると、**自前でシグナル発火スレッドを回し**、OANDA practice/live API を呼び出して shadow trade を生成する。明示的に kill しない限り CLAUDE Code セッションを跨いで生き残る。
- 4/21 起動 → 4/30 まで生存 (9日間)
- 47% CPU 占有
- 475 件の trade をローカル DB に書き込み
- 本番 Render と完全独立に動作 (両方が OANDA に同時接続している可能性あり — 二重発注リスク)

## 規律違反の連鎖

[lesson-data-source-production-first-2026-04-28] で 2 日前にすでに「ローカル DB 参照禁止」を lesson 化していたにもかかわらず、本セッションでも初動で `sqlite3 ./demo_trades.db` を実行し「2件 OPEN しかない」と誤った前提を作りかけた。

幸い user の指摘 (「本番環境からデータを取得して」) で軌道修正できたが、もし user が指示しなければ:
- 本日 Tokyo n=2 で「サンプル不足、結論不能」と短絡
- WR 35%/PF 1.64/Welch's t adj p=0.0042 という強い改善シグナルを完全に見逃す
- `feedback_partial_quant_trap` / `feedback_success_until_achieved` 両方を踏み抜く

## 失敗モード分析

1. **lesson の persistence が弱い**: 2日前に同種 lesson を作っても、PreToolUse hook が無いと session を跨いで効かない
2. **オーファンプロセス検出 checklist の欠如**: セッション開始時に `pgrep -f app.py` を確認するルールが無かった
3. **DB ファイル mtime のミスリード**: `demo_trades.db` の mtime が直近 (15:06) で「最新の本番データ」と誤認させる磁場を作っていた
4. **二重 DB 構成のドキュメント不足**: README に「ローカル DB は開発用」と書いてあるが、**「ローカル app.py を起動した瞬間からそれは独立した別世界の trade を作る」** という運用上の意味は文書化されていなかった
5. **二重発注リスクの未認識**: 本番口座 OANDA token が `.env` にあれば、ローカル prod のリアル発注も可能 (今回 `is_shadow=1` で抑制されていただけ)

## 再発防止

### 即時 (本セッション)

- [x] PID 33137 を kill する選択を user に提示 (返答待ち)
- [x] 本 lesson を作成して KB index を更新

### 短期 (次セッションで適用)

セッション開始 hook (SessionStart) に追加:
```bash
# fx-ai-trader workspace 入り口で実行
ORPHAN=$(pgrep -f "fx-ai-trader.*app\.py" | head -1)
if [ -n "$ORPHAN" ]; then
  RUNTIME=$(ps -o etime= -p $ORPHAN | xargs)
  echo "⚠ ローカル app.py プロセス検出: PID=$ORPHAN runtime=$RUNTIME"
  echo "  ローカル DB は phantom trade で汚染されている可能性あり。"
  echo "  分析は必ず https://fx-ai-trader.onrender.com/api/demo/trades を使用。"
fi
```

### 中期 (hookify 推奨)

`/Users/jg-n-012/.claude/hooks/quant-data-source.yaml` を拡張:
```yaml
PreToolUse:
  matcher: "Bash"
  pattern: 'sqlite3.*demo_trades\.db|sqlite3.*demo\.db'
  prompt: |
    ⚠ ローカル demo_trades.db に sqlite3 query を実行しようとしています。

    fx-ai-trader CLAUDE.md "Production Environment":
    > 分析は本番(Render)データを使用。ローカルDBは開発用のみ

    特に注意:
    - PID 33137 のような長期 orphan プロセスがローカル DB に
      phantom trade を書き続けている場合があります (lesson-orphan-local-app-process-2026-04-30)
    - mtime が最新でも、それは本番ではなくローカル app.py の自前 trade

    分析目的なら以下を使用:
      curl https://fx-ai-trader.onrender.com/api/demo/trades?limit=5000

    続行する場合は明確な理由 (schema 確認 / backup 比較等) を述べてから実行してください。
```

### 長期 (運用)

1. **二重 DB 構成の README 強化**: 「ローカル app.py 起動 = 別世界の trader が動く」を明示
2. **OANDA env スコープ確認**: `.env` の `OANDA_TOKEN` が practice / live のどちらか毎回確認 (本番 token をローカルに置かない)
3. **ローカル開発時は cron で `pgrep -f app.py` 監視**: 6h 以上 runtime のプロセスは alert

## 教訓

- **「ローカルにファイルがある = 分析に使える」は自動的に偽**。ファイルが本番由来か独立な別ランナー由来かを毎回判定する
- **mtime/サイズ単独では production-fresh の証拠にならない** — orphan が書き続けていたら「最新」だが「本番ではない」
- **lesson の文書化だけでは規律は持続しない** — PreToolUse hook で実行時に作動させる
- 過去 2 日内 (`lesson-data-source-production-first-2026-04-28`) の同種ミスを今回も繰り返した事実は **「lesson を読むだけでは効かない」** ことの実例
- ローカル `python app.py` 経由で OANDA に接続する開発スタイルは **二重発注リスクを内包する** — practice 環境への切り替えなしに長期常駐させてはならない

## 関連教訓

- [[lesson-data-source-production-first-2026-04-28]] — 2 日前に同根のミスを記録 (今回の即時親)
- [[lesson-is-shadow-filter-mandatory-2026-04-30]] — 本日午前に live/shadow 混在で監査結論 180度反転した先行ミス
- [[lesson-shadow-vs-live-confusion-2026-04-28]] — Shadow/Live 区別不徹底
- [[lesson-shadow-emit-dedup-2026-04-30]] — 本日午前 dedup guard デプロイの背景

## メタ教訓

`wiki/lessons/` に書いてあるが SessionStart hook の context に入っていない lesson は **存在しないのと同じ**。次のセッションで自動再認識させる仕組みが無い限り、9 日後に同じことが起きる。
