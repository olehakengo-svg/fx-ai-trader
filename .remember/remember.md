# Handoff (2026-07-10 15:10 JST, zen-mahavira セッション)

## State
**WS3 stage-2 完結**: PR #73 (LOCK) → PR #75 (verdict) 全て main マージ済み。**verdict = ❌ PASS ゼロ / 全体 UNDERPOWERED** ([[ws3-stage2-barrier-ev-prereg-2026-07-09]] §8 が SSOT)。lfr×EUR_USD は全 9 構成負 (best −6.51 p/t、p_cell=1.0) で**セルクローズ**。htf_fb×AUD_JPY は 1 構成のみ +1.15 (2022 円介入期 fold 集中・孤立格子点) で **UNDERPOWERED 残置** — registry `ws3-stage2-underpowered-recheck` が shadow N≥100 (AUD_JPY 限定) を毎日監視、到達で同一 grid 1 回限り再判定。独立再計算で符号検証済み。TV canon は moot (未評価)。

## Next (v2.3 WS3 の固定分岐執行済み — 追加 user 決裁不要)
**主戦線 = 新シグナル系統 (外部仮説) の探索**。roadmap 既定候補: T10 gbp_deep_pullback (WR72%/EV−1.39、高WR×負EV 筆頭) / T11 sr_anti_hunt_bounce (WR63%/EV−4.49)。着手前に必ず:
1. `.ai/tasks/queue/` claim 確認 (二重実装レース防止)
2. **最短経路決裁 (MEMORY `project_shortest_path_decision_2026_07_10`) との整合確認** — agg-Kelly gate 恒久閉鎖 (正セルも live 発火不能)・目標段階化 M1→M3・探索2周目 claim が並行決裁済み。WS3 新系統探索の設計はこの決裁と突き合わせてから
3. T2 + stage-2 で「現行母集団の exit 側改善」は完全否定済み — 同型提案は §8 を根拠に棄却

## Context
- exit 幾何の交換実験 (stage-2) の教訓: 中央値 MFE/MAE 非対称は first-touch sequencing で反転し得る。次の barrier 系設計では sequencing (先着順序) を探索段階から計測する
- htf_fb recheck は registry 通知が来たときだけ。grid/検定の変更禁止 (§4 UNDERPOWERED 分岐の宣言)
- 判定器 `tools/ws3_stage2_barrier_sim.py` は --extract/--sim 分離 (§3 執行順序の構造強制) — 再判定時にそのまま使う
- prereg_trigger_watch に instrument フィルタ配線済み (shadow_count_decision のセル粒度計上)
- 環境注意: このシェルは `$(cat <<EOF)` が bad substitution — commit/PR body はファイル経由 (`git commit -F` / `--body-file`)。pre-commit pytest は ~3-10 分、run_in_background 必須、--no-verify 禁止。hot KB ファイル conflict は union 解決、マージ直列
- 完了済み (07-09〜10): PR #68 (T15) / #69 (stage-1 verdict) / #70 (tools 修復) / #71 (stage-2 DRAFT) / #73 (LOCK) / #75 (verdict)。chip の post-commit-verify hook 修正も #72 で main 反映済み
