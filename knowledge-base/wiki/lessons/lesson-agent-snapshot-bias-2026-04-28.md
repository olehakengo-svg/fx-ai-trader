# Lesson: Parallel Agent Snapshot Bias (2026-04-28, rule:R3)

## Symptom

2026-04-27 evening session で 4 並列 agent (#1-#4) を spawn し、その #3 (Aggregate Kelly path) が以下を報告:

- Production Live aggregate Kelly = **+0.0157** (Gate 1 既通過)
- WR<35% AND N>=20 cell = **30 cells** (出血源として ema_trend_scalp 4 cells で ΣR=-211 等)
- bb_rsi_reversion × USD_JPY × scalp は **唯一の Live 黒字 cell** (N=74, WR=44.6%, Wlo=33.8%, ΣR=+7.21)
- シナリオ C 適用で Kelly **+0.0157 → +0.0723** (Gate 2 月利100%相当) 即射程

これらは月利 path 戦略 (M4 / H5) の起案根拠として採用されたが、次セッションで `tools/phase_a_production_audit.py` を新設し `/api/demo/trades?limit=2000` direct read で再検証したところ:

| 指標 | Agent#3 報告 | Phase A 実測 (2026-04-27 18:59 JST) |
|---|---|---|
| Total Live closed N (post-2026-04-16) | 数百〜 | **26** |
| Aggregate Kelly | **+0.0157** | **-0.1230** |
| WR<35% AND N>=20 cell | 30 | **0** |
| bb_rsi × USD_JPY × scalp | N=74 / +7.21R | N=8 / WR=12.5% / -20.8 pip |

**全項目で Agent#3 と production が乖離**。同方向の符号一致もない (Kelly は positive vs negative)。

## Root Cause

Agent#3 が使った data source が production /api/demo/trades の現在状態と異なっていた可能性が高い。具体的仮説:

1. **Local DB の古い snapshot**: `demo_trades.db` のローカルファイルが production と同期されておらず、過去日付のデータで集計
2. **異なる cohort filter**: post-cutoff 定義 / is_shadow フィルタ / mode フィルタが production audit と異なる
3. **N truncation**: /api/demo/trades は limit=2000 で truncate (実 trade 総数 ~2000+ で limit 内に収まっていない可能性) — ただし Phase A も同じ制約で aggregate -0.123 確認、Agent#3 が limit 拡張版を使っていれば説明つかない
4. **計算定義違い**: Kelly の符号定義 / pnl_r の取扱い違い (Agent#3 が earlier に -17.26% を +0.0157 に訂正した経緯あり、再度の符号 bug 可能性)

正確な原因は Agent#3 の出力ファイル (`/private/tmp/claude-501/-Users-jg-n-012-test/d48e0764-.../tasks/a740bdb9...`) を読んで確定する必要があるが、**production direct read を一次情報とする規律**を優先するため、本 lesson では原因究明より再発防止を重視する。

## Why This Matters (CLAUDE.md 整合性)

CLAUDE.md「ラベル実測主義」:
> 「X のロジック問題ない?」質問に対しコード演繹で回答禁止、ラベル×WR 実測クエリ必須

CLAUDE.md「KB は更新するもの、絶対のルールではない」:
> 真の規律は: KB を読む → 新データと突き合わせる → 整合/矛盾を分析する → 必要なら KB 更新

**並列 agent の集計値も「実測」に見えるが、production data ではない可能性がある**。Agent の出力を新発見として KB 更新の根拠に使う前に、production direct read で fact-check する SOP を本 lesson で確立する。

## SOP — Agent 集計値の取扱い

### Step 1: Agent 出力を「仮説」として受け取る
- 並列 agent は数千トークン規模の作業を切り出してくれる強力なツール
- だが出力は **production 1 次情報ではなく**、agent 内で 2 次加工された数値
- 受け取った数値を即座に KB / 実装根拠として使わない

### Step 2: 数値が KB / 実装に影響する場合は production audit で fact-check 必須

具体的なトリガー:
- Pre-reg LOCK の起案 (M4 / H5 / 新戦略 promotion)
- KB 更新 (Kelly / WR / EV の改訂)
- Live promotion / OANDA_TRIP 解除
- defensive mode unwind の判断

→ いずれも `tools/phase_a_production_audit.py` (or 同等の production direct read) で **3 つの key metric** を確認:
1. cell-level N / WR / Wilson lower
2. aggregate Kelly (production cohort)
3. 対象 cell の direction (positive / negative) が agent 報告と符号一致するか

### Step 3: 乖離検出時の対応
- 数値の符号が一致しない場合: agent 報告は **不採用**、production audit を一次情報として採用
- N 数のオーダーが違う場合: agent の cohort filter 仮説 (snapshot date / mode / cutoff) を確認
- 説明できない場合: agent の出力ファイル (`/private/tmp/.../tasks/*`) を読んで raw 計算過程を検証

### Step 4: 乖離を lesson + analyses に文書化
- 本 lesson のように再発防止記録
- 数値の改訂履歴を `wiki/decisions/` に残す

## What I Learned

私 (前任) は 2026-04-27 evening session で Agent#3 報告を **fact-check せずに KB 更新提案 / 月利 path 起案** に使った:
- `kb-update-2026-04-28.md` §2 defensive-mode-unwind: Agent#3 Kelly +0.0157 を反映する patch 起案
- `m4-scenario-c-design-2026-04-28.md`: Agent#3 の 30 cell リストを deny target 候補
- `pre-reg-bb-rsi-revival-2026-04-27.md`: Agent#3 の bb_rsi 黒字主張を起点に WATCH-only path

H5 起案中に bb_rsi cell を fact-check して初めて乖離を発見し、**4 度目の self-correction** に至った。
これは CLAUDE.md「KB-defer 罠」の隣に存在する **「Agent-defer 罠」**。

## Future Audit

- 並列 agent を spawn するタスクで、agent 出力を即時 KB / 実装に流す run book を **禁止**
- agent 出力が数値を含む場合、自動的に `tools/phase_a_production_audit.py` (or 同等) で fact-check する protocol を CLAUDE.md セッション開始 hook に追加検討
- 既存の Agent#3 報告を出した 2026-04-27 task の出力ファイルを読み、原因究明を別タスクで実施

## Related Lessons

- [[lesson-cell-audit-bt-required-2026-04-27]] — BT/KB と Live data の対応関係
- [[lesson-confounding-in-pooled-metrics-2026-04-23]] — pooled aggregate の誤解
- [[lesson-late-stage-signal-override]] — 上流情報を下流が override する pattern
- [[lesson-trend-bull-gate-overblock-2026-04-27]] — production direct read で発見した execution bug
