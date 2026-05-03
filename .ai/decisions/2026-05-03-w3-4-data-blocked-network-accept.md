---
date: 2026-05-03
task: 20260503-1721-w3-4-data-gbpjpy-m5-12yr-backfill
verdict: ACCEPT_AS_SUPERSEDED
rule: R3
gate: Gate 1 (新 alpha 候補のための data backfill)
---

# W3-4-data GBPJPY M5 12yr backfill — ACCEPT_AS_SUPERSEDED decision

## Verdict

**ACCEPT** — Codex は task spec の Decision Procedure (pre-flight network gate) に honest に従って `BLOCKED_NETWORK` で停止。本番・ソース・cache・secret を一切触らず、所定の human-acquisition fallback task `.ai/tasks/queue/20260503-1800-w3-4-data-acquisition-human.md` を参照。**実装は仕様通り**。

ただし本タスクの**前提自体が、Codex 実行時刻 (18:29:03 JST) より前に Claude メイン側で superseded** されていた:

- 2026-05-03 18:00–18:25 (JST) に Claude メイン側で **Massive Market Data API** から GBPJPY M5 12年 (925,109 bars, 2014-01-02 04:55:00+00:00 → 2026-04-30 23:55:00+00:00) を取得
- `tools/bt/data_prep_manifest.json` に sha256=`14d4ec64c99c…` で記録済み (manifest `generated_at: 2026-05-03T09:21:43.139344+00:00`)
- active path `data/cache/massive/GBP_JPY_5m.parquet` (24.97 MB) も同 sha256 で配置済み (W3 data prep task `20260503-1715-w3-data-prep-gbpjpy-usdjpy-m5-12y` の成果物)
- 後続 `.ai/tasks/queue/20260503-1830-w3-4-rerun-c1-london-breakout-gbpjpy-12yr.md` で 12yr cache を直接使う rerun が **既に作成済**

→ Codex の HistData/Dukascopy ルートは結果的に不要だったが、**それは Codex の責任ではない** (Codex は task spec に書かれていない外部状態を知り得ない)。

## Codex 結果の品質評価

- ✅ Pre-flight network probe を 2 source 共実行、stderr/exit code を逐語転記
- ✅ `BLOCKED_NETWORK` verdict を spec の Decision Procedure に従い honest に記録
- ✅ Files Changed: `final.md` のみ (source/strategy/production/secret/tier/cache 一切 untouched)
- ✅ `data/cache/massive/GBP_JPY_5m.parquet` の 925,109 bars / 12yr coverage を **Local Observation として明示**し、「task spec が HistData/Dukascopy 取得を mandate しているため substitute せず」と判断根拠を記録 — これは spec 遵守として正しい
- ✅ 既存 fallback task `.ai/tasks/queue/20260503-1800-w3-4-data-acquisition-human.md` を recommended next として提示

## Data hygiene

- BT/Live/OANDA の混在なし
- `.env` / OANDA secrets / 本番 DB 一切 untouched
- 本番転送・lot 変更なし
- Read-only 操作のみ (curl probe のみ実行、いずれも DNS で失敗)

## Roadmap impact

- **Gate 1 (新 alpha 候補)**: 本タスク自体は寄与せず (BLOCKED)、ただし **superseder task `20260503-1830-w3-4-rerun-c1-london-breakout-gbpjpy-12yr` が queue に既存** → そちらが Scenario A/B/C verdict を出す経路
- **Gate 0 (生存)**: 本タスクは Gate 0 とは独立。並行して `20260503-1840-tier1-live-edge-audit` (Gate 0 救済の最終検証) が queue に存在
- **教訓**: マルチエージェント workflow で「メイン側のデータ準備」と「Codex sandbox の data backfill」が時間的に競合する場合、**メイン側 manifest を Codex task spec に明示 prerequisite として組み込む**べき。今回は manifest が Codex 実行時刻より早く完成していたが、Codex task は外部 source (HistData/Dukascopy) を pre-baked して書かれていた → 後続 `1830-rerun` task は manifest verification step を Step 0 に組み込んでおり、この learning は既に反映済み

## Artifacts

- Codex run report: `.ai/runs/20260503-182903-20260503-1721-w3-4-data-gbpjpy-m5-12yr-backfill/final.md`
- Superseder task (queue): `.ai/tasks/queue/20260503-1830-w3-4-rerun-c1-london-breakout-gbpjpy-12yr.md`
- Data prep manifest: `tools/bt/data_prep_manifest.json` (sha256=`14d4ec64c99c…`, n_bars=925,109)
- Data prep run report: `.ai/runs/20260503-1800-w3-data-prep-gbpjpy-m5-12y/final.md`
- Stale fallback task (now obsolete): `.ai/tasks/queue/20260503-1800-w3-4-data-acquisition-human.md`

## Cleanup recommendation

- `.ai/tasks/queue/20260503-1800-w3-4-data-acquisition-human.md` は **obsolete** (data prep 完了で human acquisition は不要) → 次セッションで `done/` に annotated archive 推奨

## Next task

ロードマップ上の最優先は **Gate 0 (生存)**。R2 strategy×instrument counterfactual が REJECT で帰還し (all-target STOP でも raw Kelly=-0.25), demotion 単独では Gate 0 復帰不可が確定。

→ **次の一手: `20260503-1840-tier1-live-edge-audit`** (queue 既存)

理由:
1. R2 REJECT が示唆する次の仮説 H4 = 「Tier 1 LIVE 戦略自体に Live で edge が残存しているか」を **5 cell 単位で実測検証** (Bonferroni m=5, BEV_WR per pair)
2. ACCEPT (2 cell 以上で Wilson_lo > BEV_WR) → Tier 1 LIVE lot ↑ + cell-level demotion の両輪で Gate 0 復帰を狙える
3. REJECT (5 cell 全て Live で edge 喪失) → BT-Live divergence 構造 audit (Path B, `bt-live-divergence.md` の 6 楽観バイアス) へ強制分岐 — このとき新 alpha 追加 (W3-4 rerun, Gate 1) は無意味

→ 並行で **`20260503-1830-w3-4-rerun-c1-london-breakout-gbpjpy-12yr`** (Gate 1) も P0 だが、**Gate 0 が cleared されない限り新 alpha は寄与しないため後続**。
