# Claude Code Harness Design — v2 (2026-04-13 全面改訂)

## なぜv1が失敗したか

v1ハーネスは「存在するが機能しない」状態だった。以下が今日のセッションで証明された:

| v1の主張 | 実態 |
|---------|------|
| Lessons注入で同じ間違いを防ぐ | 0件注入されていた |
| Session要約で文脈を引き継ぐ | 未解決事項20行のみ、Phase記録なし |
| BT乖離ツールでデータに基づく判断 | パーサーバグで0件出力、使わずに判断 |
| 戦略変更時のBT検証必須 | EUR_USD SELLブロックを「即時」と判断して数時間放置 |
| KBに記録して記憶する | 意思決定ページ0件、session logは一括書き |
| 独立監査で品質保証 | 監査を走らせても結果をアクションに繋げない |

**根本原因**: ハーネスが「ルールの宣言」で終わり、「ルールの強制」になっていなかった。

## v2ハーネス: 3つの原則

### 原則1: 作る→検証する→使う→記録する (Build→Verify→Use→Record)

```
あらゆる成果物に対して:
  1. Build: コード/ツール/分析を作る
  2. Verify: 実データで正しい出力が返ることを検証する
  3. Use: その出力を判断の根拠として引用する
  4. Record: 判断と根拠をKBに記録する
  ※ どのステップも飛ばさない。飛ばしたらlessonに記録
```

**強制メカニズム**:
- PostToolUse hook (post-strategy-edit-check.sh): 戦略変更時にBT検証を強制リマインド
- pre-commit hook (git-pre-commit.sh): 97テスト + 6整合性チェック
- CI (ci.yml): push時に自動テスト

### 原則2: 存在≠機能 (Existence≠Function)

```
インフラの評価基準:
  ❌ 「KBがある」「hookがある」「テストが通る」
  ✅ 「KBの内容が読まれて判断に使われた」
  ✅ 「hookが有用な情報を注入し、その情報で行動が変わった」  
  ✅ 「テストが正しいことを検証している（空=OKはテストではない）」
```

**強制メカニズム**:
- 全分析ツールに正例テスト必須 (TestBtDivergenceParser等)
- hook出力のlessons件数を検証 (0件=バグ)
- session logのPhase記録を作業中にインクリメンタルに書く

### 原則3: 発見→実装を同一サイクルで完結 (Discovery→Action in same cycle)

```
Alpha Scanで毒性を発見 → 同じセッション内にブロック実装
BT乖離を検出 → 同じセッション内に対策実装
決定を行った → 同じコミットでdecisions/に記録
```

**v1の失敗**: Alpha ScanでEUR_USD SELL (EV=-2.714) を発見→「即時アクション」と判定→実装せずにインフラ作業に戻った。

**強制メカニズム**:
- Alpha Scan自動化 (alpha-scan.yml): 毎週月曜にCI実行、結果をDiscord通知
- 自動降格/復帰パイプライン (_evaluate_promotions): N≥20 EV<-0.5で自動FORCE_DEMOTED
- ランタイムペア別降格 (_runtime_pair_demoted): N≥15 EV<-0.5で動的ブロック

## 情報フロー設計

### 毎メッセージ注入 (UserPromptSubmit hook)
```
KB SYNC:
  INDEX: Tier分類 + System State (30行)
  UNRESOLVED: 最新の未解決事項 (20行, awkで最後のセクション)
  LESSONS: 12件の教訓本文 (grep '教訓:')
  MARKET: 市場セッション + 4原則 + クオンツルール
  LAST COMMIT: ドリフト検知
```

### セッション開始時注入 (SessionStart hook)
```
KB AUTO-LOAD:
  INDEX: Tier + System State (60行)
  SESSION CONTEXT: 最新Phase + コミット一覧 (30行)
  UNRESOLVED: 最新の未解決事項 (25行)
  LESSONS: 教訓タイトル + 本文
  DAILY REPORT: 最新レポート (15行)
  ANALYST MEMORY: 最新知見 (20行)
  KB DRIFT: check.pyの警告
```

### セッション終了時保存 (Stop hook)
```
1. pre-compact.sh: session logテンプレ生成
2. KB変更のauto-commit + push
3. JSON出力 (stdout汚染なし)
```

### 戦略変更時ゲート (PostToolUse on Edit)
```
post-strategy-edit-check.sh:
  strategies/ or demo_trader.py の変更を検知
  score/PROMOTE/DEMOTE/QUALIFIED キーワード検出
  → BT検証必須リマインドを注入
```

## 自動パイプライン

| パイプライン | 頻度 | 目的 | ファイル |
|---|---|---|---|
| Daily Report | 4回/日 | セッション別分析 + BT乖離テーブル | daily-report.yml |
| Weekly Audit | 日曜 | 戦略×ペアEV分解 + Tier再評価 | weekly-audit.yml |
| **Alpha Scan** | **月曜** | **ファクター分解 → 正EV/毒性自動検出** | **alpha-scan.yml** |
| Trade Monitor | 2h毎 | 異常検知 | trade-monitor.yml |
| CI | push時 | 97テスト + 6整合性チェック | ci.yml |
| Auto-demotion | 10trade毎 | N≥20 EV<-0.5 → 自動降格 | demo_trader.py |

## 今日のセッションで発覚した失敗と対策

| 失敗 | 根本原因 | 対策 | 状態 |
|------|---------|------|------|
| Lessons 0件注入 | head -10がヘッダーのみ | grep '教訓:' に変更 | ✅修正済 |
| Session要約未注入 | 未解決事項のみ | awk + Phase抽出追加 | ✅修正済 |
| BT乖離パーサー0件 | regex不一致 | パーサー修正 + 正例テスト | ✅修正済 |
| ツールを作って使わない | Build→Verifyで止まる | 原則1: Build→Verify→Use→Record | ✅原則定義 |
| EUR_USD SELL未実装 | 発見→実装が分離 | 原則3 + Alpha Scan自動化 | ✅実装済 |
| 意思決定ページ0件 | 記録が後回し | decisions/に即座に記録 | ✅8件作成 |
| is_shadow=0バグ | 非promotedの扱い | _is_promoted=False → shadow強制 | ✅修正済 |
| KB 14件不整合 | 更新が後回し | feat()と同一コミットでKB更新 | ✅修正済 |
| DD状態矛盾 | 複数ファイルに同じ値 | SSOTをindex.mdに一元化 | ✅修正済 |
| 2つ目の未解決ブロック不可視 | grep -A 15が最初のみ | awk化で最後のセクション | ✅修正済 |
| CI/pre-commitなし | テスト自動実行なし | ci.yml + pre-commit構築 | ✅修正済 |
| Alpha Scan手動のみ | 人間依存 | GitHub Action化 | ✅修正済 |

## リンク
- [[roadmap-to-100pct]] — 月利100%ロードマップ
- [[session-decisions-2026-04-13]] — 本日の8件の意思決定
- [[alpha-scan-2026-04-13]] — Alpha Scan結果
- [[lesson-tool-verification-gap]] — ツール検証の教訓
- [[system-reference]] — 全パラメータ
