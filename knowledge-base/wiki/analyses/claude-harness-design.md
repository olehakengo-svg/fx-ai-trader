# Claude Code Harness Design — クオンツアナリスト100%+

## 問題定義
82件のユーザー指示/決定のうち29件(35%)が毎回手動遵守に依存。
ユーザーの全発言の20%がゴム印承認。6回以上「クオンツ見解は？」と聞かれた。
根本原因: Claudeがエンジニアモードでデフォルト動作し、分析が後回しになる。

## 5層ハーネス

### Layer 1: CLAUDE.md — デフォルト動作モード宣言
- **クオンツファーストプロトコル**: 分析→判断→実装の順序を強制
- **自動実行 vs 承認必要**: BT/分析/KB操作は確認不要、デプロイ/PROMOTE/ロット変更は要承認
- **クオンツ判断ルール**: XAU除外、ペア×戦略粒度、Post-cutoff起点等を明文化
- 実装: CLAUDE.md冒頭に追加 (v8.9)

### Layer 2: UserPromptSubmit Hook — 毎回のコンテキスト注入
- KB状態(index/未解決/lessons)の注入（既存）
- **市場セッション判定**: UTC時刻からTokyo/London/NY/Overlapを自動判定して注入
- **4原則リマインダ**: 毎メッセージで表示
- **クオンツルールリマインダ**: XAU除外等のフィルタルールを表示
- 実装: user-prompt-kb-sync.sh 拡張 (v8.9)

### Layer 3: コードレベル強制 — 人間の判断に依存しない
- **XAU除外**: risk_analytics.py compute_risk_dashboard()入口でXAUフィルター
- **Shadow除外**: get_stats() exclude_shadow=True（既存v8.4）
- **DD equity**: Equity Resetで XAU除外（既存v8.9）
- **Spread/SL Gate**: コード内で強制（既存）

### Layer 4: セッション開始プロトコル強化
- git log確認 + changelog整合 + **市場セッション認識** + **直近12hトレード活動チェック**
- 0件なら即座に原因調査（4原則「攻める」への違反検知）

### Layer 5: Scheduled Tasks / GitHub Actions
- **Daily Report**: 4回/日（pre_tokyo/post_tokyo/post_london/post_ny）
- **Weekly Audit**: 日曜UTC 02:00（戦略×ペアEV分解 + Tier再評価）
- **Trade Monitor**: 15分毎（異常検知→Discord通知）
- **KB自動コミット**: 全ワークフローにPAT_TOKEN + git commit/push

## ユーザー介入パターンと自動化状態

| パターン | 頻度 | 自動化 |
|---------|------|--------|
| "クオンツの見解は？" | 6回+ | Layer 1: デフォルトモードで解消 |
| "お願いします" (ゴム印) | 15回 | Layer 1: 自動実行ティアで解消 |
| XAU除外忘れ | 3回 | Layer 3: コードレベル強制で解消 |
| 市場タイミング無視 | 5回 | Layer 2: 毎回セッション注入で解消 |
| BT前にデプロイ | 2回 | Layer 1: 判断ルール明文化 |
| KB更新忘れ | 5回 | Layer 2,4: フック自動化で解消 |
| Post-cutoff忘れ | 2回 | Layer 1,2: ルール注入で解消 |

## 未自動化（人間判断が必要な領域）
- 戦略のPROMOTE/DEMOTE判断（統計的根拠は自動、最終決定は人間）
- ロットサイズ変更（DD防御ポリシー変更）
- 新戦略の採用可否（BT結果は自動、ビジネス判断は人間）
- ロードマップの時間軸変更

## リンク
- [[roadmap-to-100pct]] — 月利100%ロードマップ
- [[independent-audit-2026-04-10]] — 独立監査
- [[system-reference]] — 全パラメータ
