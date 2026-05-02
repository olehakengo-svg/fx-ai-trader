<claude-mem-context>
# Memory Context

# [fx-ai-trader] recent context, 2026-05-03 2:49am GMT+9

Legend: 🎯session 🔴bugfix 🟣feature 🔄refactor ✅change 🔵discovery ⚖️decision 🚨security_alert 🔐security_note
Format: ID TIME TYPE TITLE
Fetch details: get_observations([IDs]) | Search: mem-search skill

Stats: 9 obs (3,667t read) | 77,008t work | 95% savings

### Apr 24, 2026
1 10:07p 🔵 FX AI Trader Session Restart — Handoff State Confirmed
2 10:08p 🔵 MTF Gate Category Audit: Category-Dependent Inversion Confirmed
3 " 🔵 Full Label Audit: 7 Labels with Inverse Calibration (≤-5pp Delta WR)
4 10:13p 🔵 claude-mem daemon running post-restart but CLI not in PATH
S6 Post-restart claude-mem integration analysis: determining how to implement Option B (injection-free, MCP-search-only) for fx-ai-trader (Apr 24 at 10:13 PM)
S1 Post-restart system health check for claude-mem in fx-ai-trader project (Apr 24 at 10:13 PM)
5 10:15p 🔵 fx-ai-trader .remember directory has handoff-next-session.md from prior session
6 " ⚖️ claude-mem integration strategy for fx-ai-trader: Option B (on-demand search only)
7 10:16p 🔵 claude-mem v12.3.9 hooks.json structure fully mapped
8 " 🔵 CLAUDE_MEM_EXCLUDED_PROJECTS setting can exclude fx-ai-trader from hook injection
9 " 🔵 EXCLUDED_PROJECTS uses regex matching against full cwd path, comma-separated
S11 claude-mem Option B-1 implementation — EXCLUDED_PROJECTS設定をfx-ai-traderに適用してinjection無効化 (Apr 24 at 10:35 PM)
**Investigated**: ~/.claude-mem/settings.jsonのEXCLUDED_PROJECTS設定と、どのhookがその短絡処理を尊重するかを調査。3つのhook（PostToolUse observation、UserPromptSubmit session-init、PreToolUse Read file-context）が対象で、SessionStart context injection・Stop summarize・SessionEnd session-completeは対象外であることを確認。

**Learned**: EXCLUDED_PROJECTS設定は6つのhookのうち3つのみを短絡させる。残り3つのhookはEXCLUDED_PROJECTSを無視するが、capturがゼロであるため実質的に注入されるデータも空になる。既存のグローバル設定（CLAUDE_MEM_SEMANTIC_INJECT=false、CLAUDE_MEM_CONTEXT_FULL_COUNT=0）との組み合わせで、fx-ai-traderでのclaude-mem injection全体を実質無効化できる。

**Completed**: - ~/.claude-mem/settings.jsonにCLAUDE_MEM_EXCLUDED_PROJECTS: "/Users/jg-n-012/test/fx-ai-trader"を設定
    - バックアップファイル ~/.claude-mem/settings.json.bak-b1-2026-04-24 を作成
    - commit 0d81c53 をmainにpush済み
    - ロールバック手順を確認（バックアップファイルを元の場所に戻すだけで即時復旧可能）

**Next Steps**: Phase 3の動作確認（次セッションで実施予定）:
    1. fx-ai-traderプロジェクトでKB_SYNC以外の自動injectionが発生しないことを目視確認
    2. ~/.claude-mem/logs/でfx-ai-trader由来のobservation記録が増えないことを確認
    3. 他プロジェクトcwdでMCP mcp__plugin_claude-mem_mcp-search__searchが正常動作することを確認


Access 77k tokens of past work via get_observations([IDs]) or mem-search skill.
</claude-mem-context>