---
id: 20260707-1640-exit-repair-tp-sl-grid
title: "[v2.3 WS-Diag T2/R1] exit-repair TP/SL 実走距離整合 grid BT — pre-reg LOCK 済み検証"
owner: claude
status: done
verdict: "FAIL (H0 採択) 2026-07-08 — 全9構成 BH-FDR 不通過 (p=1.0) / WF 0/3 / EV 負 (最良 -2.96 p/t)。ナイフエッジ3点検査済。詳細 = pre-reg §8。WS3 全振りへ"
executor_note: "2026-07-08 executor 変更 codex→claude (Fable5)。user 承認済 (運用委任)。理由: 期日リスク (T5 18日ギャップ前歴、.ai/runs 06-08 以降停止) + MCP/repo 直接アクセス。pre-reg LOCK 対象 (§2-§4) は不変。PASS 構成が出た場合のみ Codex 独立再現を追加"
priority: P1
created_at: 2026-07-07T16:40:00+0900
roadmap_gate: "v2.3 WS-Diag T2 (正式版 2026-07-07)。実装は verdict PASS 後の user 最終承認が別途必要"
rule: R1
prereq_artifacts:
  - knowledge-base/wiki/decisions/exit-repair-tp-sl-prereg-2026-07-07.md
  - knowledge-base/wiki/analyses/payoff-asymmetry-diagnosis-2026-07-07.md
related:
  - knowledge-base/wiki/syntheses/roadmap-v2.3-payoff-friction-repair.md
---

# 0. なぜこのタスクか

T3 診断 (2026-07-07、敵対的検証済) で payoff 0.274 の主因 = 「設計 TP が実走 MFE の約5倍遠い」勝ち側 exit 執行崩壊と確定。exit 微調整では黒字化不能のため、**TP/SL を実走距離に整合させる構造是正**が唯一の exit 側レバー。pre-reg は LOCK 済み — **本タスクは pre-reg の実行であり、設計の変更・追加は禁止** (変更が必要ならタスクを止めて pre-reg 改訂 PR を先に)。

# 1. 要求仕様 (pre-reg §2-§4 の機械的実行)

- Grid: TP_mult ∈ {0.4, 0.6, 0.8} × SL_mult ∈ {0.6, 0.8, 1.0} (9 構成)、**BE/Trail OFF 固定**
- エンジン: 本番 signal 関数 `backtest_mode=True`、365d、**診断窓 2026-06-07〜2026-07-08 除外**
- 対象: 6 entry_type (trendline_sweep / wick_imbalance_reversion / zz_pivot_v60_sr / vix_carry_unwind / dt_sr_channel_reversal / vsg_jpy_reversal) × 診断窓で live 発火した pair。**bb_rsi_reversion は T10 KILL につき除外**
- 摩擦: per-pair 理論値控除 (判定用) + 実測フロア 1.30/t (感度、記述のみ)
- Primary: ポートフォリオ pooled 摩擦調整 EV、m=9 BH-FDR q=0.10、日次ブロックブートストラップ SE
- WF 3-fold の fold 別符号を記録
- 出力: `raw/bt-results/exit_repair_tp_sl_grid_2026_07.json` + 集計 markdown

# 2. Verdict (Claude が実施、Codex は BT 実行と生データまで)

- PASS/FAIL 判定は pre-reg §4 の条件のみで機械判定
- **ナイフエッジ3点検査必須** (pre-reg §5): メカニズム整合 / 擬似反復 (lag-1 ρ + 日次クラスタ補正) / 閾値リーク (隣接格子整合)
- verdict を pre-reg 文書へ追記 + registry `exit-repair-bt-deadline` を inactive 化 + session log 記録
- PASS 時: user 最終承認を経て実装 PR (live パラメータ変更はそこまで禁止)
- FAIL 時: v2.3 の「WS3 シグナル張り替えへ全振り」を正式反映する PR

# 3. 期日

registry `exit-repair-bt-deadline` = **2026-07-21**。未着なら Tier A cron が stale アラート。

# 4. Claude Review (2026-07-08)

## Claude Review

- **執行**: executor は codex→claude (Fable5) に変更 (user 運用委任 2026-07-08)。pre-reg LOCK (§2-§4) の設計は一切変更していないことをレビューで確認 — grid/エンドポイント/対象セル/摩擦モデル全て仕様通り
- **機械判定の検証**: 全9構成 FAIL — (a) BH-FDR q=0.10 全構成 p=1.0 (b) WF 3-fold 全構成 0/3 (c) 摩擦調整EV 全構成負 (最良 tp0.4×sl0.6 −2.96 p/t)。判定コードは runner 内で pre-reg §4 の3条件をそのまま実装、baseline は m=9 の外 (記述のみ) であることを確認
- **ナイフエッジ3点検査 (pre-reg §5)**: ①メカニズム整合 = TP-hit 0.215→0.44・EV 両軸厳密単調 (診断機構どおり作動した上での構造的 FAIL) ②擬似反復 = lag-1 ρ −0.058 (trade) / +0.055 (daily)、日次ブロックで補正済み、p=1.0 は補正で不変 ③閾値リーク = PASS ゼロで該当なし・曲面単調
- **頑健性**: 感度 run (pre-#58 code) 同結論 / 実測フロア摩擦 (1.30p/t) でも pooled 全構成負 / エントリー母集団ドリフト軽微 (N=549-628)
- **verdict**: ❌ **FAIL / H0 採択** → pre-reg §4 固定分岐により WS3 全振り。詳細 = pre-reg §8 (同コミット)。live パラメータ変更なし (純研究)
