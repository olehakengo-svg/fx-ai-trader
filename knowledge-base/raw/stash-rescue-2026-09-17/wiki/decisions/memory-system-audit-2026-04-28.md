---
title: メモリシステム監査 — KB-defer 罠 4 回目を受けた構造診断
date: 2026-04-28
type: decision
severity: HIGH
related:
  - "[[../lessons/lesson-shadow-vs-live-confusion-2026-04-28]]"
  - "[[../lessons/lesson-asymmetric-agility-2026-04-25]]"
  - "[[../lessons/lesson-agent-snapshot-bias-2026-04-28]]"
---

# メモリシステム監査 (2026-04-28)

## Context

同じ根本原因のミス (KB-defer 罠) を user が **4 回**訂正している (最新は本日 2026-04-28、`lesson-shadow-vs-live-confusion-2026-04-28.md`)。CLAUDE.md は明示的にこのパターンを警告し、lesson も書かれているにもかかわらず再発が続く。メモリは 5 つの重複層 (CLAUDE.md / wiki/ / MEMORY.md / claude-mem MCP / .remember/) に分散している。本監査は再発機序を診断し、最高レバレッジの 1 点修正を処方する。

---

## Section 1 — 根本原因分析

KB-defer 罠の再発は lesson の不在ではなく、**ルールの保管形式と呼び出し経路の構造的ミスマッチ**が原因:

1. **CLAUDE.md は密度過多で階層化されていない**
   151 行に 4 原則 / KB 判断メタルール / 読み書きルール / Asymmetric Agility R1/R2/R3 / インフラが混在。「KB-defer 罠」警告 (lines 13–35) が「クリーンデータ蓄積最優先」(line 41) と**テキスト上隣接**しており、認知負荷下でモデルは隣接=同等権威と読み、後者をドメイン横断の絶対ルールとして引用する。これが「Live データ衛生の話」を「Shadow 探索抑制」と読み替えた本日の失敗。

2. **Lesson は振り返り用で、呼び出し用になっていない**
   各 lesson は 5–8KB の物語形式。`lesson-shadow-vs-live-confusion` lines 61–67 にそのまま使えるチェックリストがあるが、90 行の lesson 内に埋まっており、デフォルトでロードされない。**洞察は記録されているがゲートが存在しない**。

3. **Live/Shadow コスト構造区別が CLAUDE.md に明記されていない**
   最も頻繁に違反される invariant (asymmetric bet, downside 限定) なのに、4 原則にも読み書きルールにも一行もない。lesson 物語の中にしか存在せず、**失敗した後にしか見えない**。

4. **メモリ層の冗長性がノイズを生んでいる**
   `.remember/` (now/today/recent/archive)、claude-mem MCP、MEMORY.md、session-start hook が同情報を多重注入。プライミングが 5 重になると、モデルは表層トークンマッチング (「クリーンデータ」→「凍結」) に退行し、文脈再解釈を放棄する。

**総合**: 密な規則 + 振り返り型 lesson + 冗長プライミング = 文字通り適用が高確率。

---

## Section 1.5 — CLAUDE.md 容量分析

**定量**:
- 9,545 バイト / 151 行 / 558 単語 / **約 2,500–3,000 トークン**
- 見出し 21 個 (H2: 13, H3: 5, H4: 3) / 本文 103 行 → **見出し密度 1/5 行**
- 毎セッション自動ロードされる固定コスト

**判定**: **容量過多** (典型的健全 CLAUDE.md は 500–1,500 トークン、本ファイルは 2 倍超)。ただし「総バイト数」より以下 3 重複が真の問題:

1. **R1/R2/R3 ルール重複** (CLAUDE.md lines 97–110 / 14 行 vs `lesson-asymmetric-agility-2026-04-25.md` 144 行) → CLAUDE.md 側は 3 行サマリ + 参照で十分 (**-11 行**)
2. **KB 構造テーブル ↔ 読み取りルール** (lines 53–64 と 77–95 でファイルパス二重列挙) → 統合 (**-10 行**)
3. **「詳細: wiki/...」散在** (lines 5, 39, 59, 126, 138, 141 の 6 箇所) → 末尾「詳細リファレンス」に集約 (**-6 行**)

**構造的問題**: 「絶対」が 2 つ並列 — 4 原則 (line 7) と KB 判断ルール (line 13)「KB は絶対のルールではない」が両方「絶対」を主張。モデルは優先順位を判別できず、目に入った順 (line 41) を機械引用 → KB-defer 罠の構造的原因。

**削減目標**: 151 行 → 90–100 行 / ~1,500–1,800 トークン。
**収支**: -32 行 / +5 行 (Live/Shadow ゲート) = 正味 **-27 行**

---

## Section 2 — 推奨修正 (最高レバレッジの 1 点)

**`CLAUDE.md` の「実装ルール」セクション直後に Live/Shadow コスト構造の事前チェックを「KB ルール引用より絶対先行」として追加する。**

具体的編集 (`/Users/jg-n-012/test/fx-ai-trader/CLAUDE.md`):

- **line 35–37 の間**に新規セクション「**判断前の Live/Shadow 区別チェック (絶対先行)**」を挿入
- 本文: `lesson-shadow-vs-live-confusion-2026-04-28.md` lines 61–67 の 5 項目チェックリストを逐語コピー、見出し「**任意の停止/凍結/保留提案の前に必ず実行**」
- line 26 の「過去の同種ミス」に 4 件目を追加: `(2026-04-28) Shadow vs Live コスト構造を混同し、Live 損失で Shadow 凍結を提案`

**最高レバレッジの理由**:
- ストレージギャップではなく**呼び出しギャップ**を埋める。lesson は既に書かれており、修正は「モデルが推奨を形成する経路」にゲートを差し込む
- 短い (10 行未満) ので密度をさらに上げない
- 4 回の再発全てが「停止/凍結/保留」の形を取った — そこを直接ターゲット
- 他案 (`.remember/` 統廃合、KB 再構築) は規模が大きくノイズを扱うが、因果ギャップは塞がない

---

## Section 3 — 実装アウトライン

1. `CLAUDE.md` lines 22–35: 「過去の同種ミス」に 4 件目追加、「実装ルール」直後に 5 項目 Live/Shadow チェックリスト挿入
2. `wiki/lessons/index.md`: `lesson-shadow-vs-live-confusion-2026-04-28.md` を再発パターン節に追加
3. `lesson-shadow-vs-live-confusion-2026-04-28.md` line 87 「CLAUDE.md 追記推奨」を DONE + コミット ref に更新
4. 可能なら `python3 tools/sync_kb_index.py --write` 実行、コミットに `rule:R3` タグ
5. コード変更・DB 変更なし

---

## メモリ層別判定

| 層 | 判定 | 理由 |
|---|---|---|
| `CLAUDE.md` | **修正 (圧縮 + ゲート追加)** | -27 行で容量適正化 + Live/Shadow ゲート挿入 |
| `wiki/lessons/` | **維持** | 振り返り物語は価値あり、統合しない |
| `wiki/decisions/` & `wiki/syntheses/` | **維持** | 役割が独立 |
| `~/.claude/.../MEMORY.md` (auto-memory) | **維持** | プロジェクト横断、スコープが直交 |
| `claude-mem` MCP | **維持** | 検索可能な cross-session DB、CLAUDE.md を補完 |
| `.remember/` | **再構築または廃止** | claude-mem MCP と session-start hook と重複。`core-memories.md` だけが固有信号。日次/buffer ファイルは hook が能動消費していなければ廃止推奨 |

---

## 検証方法

- **Test 1**: 新セッションで「データ品質を守るために shadow を凍結すべき?」と聞く → モデルは「クリーンデータ蓄積最優先」を引用する**前に** Live/Shadow チェックを実行すべき
- **Test 2**: 次セッションの hook 注入コンテキストに 4 件目の「過去の同種ミス」が含まれているか grep で確認
- **Test 3**: 再発カウントを追跡 — 2 週間以内に 5 件目が出たらテキスト修正は不十分、hook ベースのゲートが必要

---

## 関連

- [[../lessons/lesson-shadow-vs-live-confusion-2026-04-28]] — 4 回目の再発記録 (本監査の起点)
- [[../lessons/lesson-asymmetric-agility-2026-04-25]] — R1/R2/R3 詳細 (CLAUDE.md と重複している分の参照先)
- [[../lessons/lesson-agent-snapshot-bias-2026-04-28]] — 直前の自己訂正
- [[../syntheses/roadmap-v2.1]] — Gate 1 = Kelly>0 を発掘待ちと誤読した文脈
