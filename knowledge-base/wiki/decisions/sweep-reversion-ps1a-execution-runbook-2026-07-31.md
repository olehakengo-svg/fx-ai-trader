# sweep_reversion_eurgbp_late — P-S1(a) 執行手順書 (トリガ成立日に読んで実行する)

**Status: 準備完了 (2026-07-31 準備セッション) — 執行待ち (unique N=8/10)**
作成: Claude 2026-07-31 / rule:R1 準備 (live 変更はトリガ成立 + 本手順のみ)
決裁根拠: [[sweep-reversion-ps1a-decision-packet-DRAFT]] 冒頭決裁記録 (user 条件付き承認 2026-07-24)

> **この文書の役割**: unique N≥10 到達日に、本手順を上から実行するだけで Option B を
> 完遂できる状態を提供する。凍結文言の一次ソースは決裁パケット。本手順と食い違ったら
> パケット側に従い、食い違いを本文書に記録する。

## 0. 執行条件 (凍結、変更禁止)

- **unique バー N≥10 ∧ spaced EV>0 → Option B 執行** (再決裁不要、user 承認済み)
- spaced EV≤0 → Option C (retire、T8 DEFER 機械規定)
- unique/spaced で EV 符号が割れたら → 機械執行せず user 再決裁 (パケット §6-2)
- 2026-09-30 に unique N<5 → retire (R2)
- ⚠️ **AMENDMENT (§2.5) 未決裁なら §3 に進まず停止** — commit 1 のみの merge は禁止

## 1. トリガ検知 (自動)

- Tier A cron `fx-ai-tier-a-gate-status` (毎日 00:20 UTC) → `tools/prereg_trigger_watch.py`
  が registry `t8-sweep-defer-decision` を評価 → Discord に 🔴 TRIGGERED 表示
- 発火は 21:16-21:47 UTC に集中するため、検知遅延は最大 ~27h

## 2. 執行条件の機械判定 (dry-run)

```bash
python3 tools/ps1a_execution_check.py
```

- verdict `OPTION_B_EXECUTE` → §2.5 → §3 へ
- verdict `OPTION_C_RETIRE` → §6 へ
- verdict `USER_REDECISION_SIGN_SPLIT` → user へ両基準テーブルを提示して停止
- 判定器は凍結文言 (三基準定義・spacing 境界 ≥3h・判定分岐・retire 期日) を
  `tests/test_ps1a_execution_check.py` の 12 pin でテスト固定済み。2026-07-31 本番
  dry-run でパケット §1.1 と完全一致を確認済み (row +2.13 / unique +3.14 / spaced +2.47)

## 2.5 ⚠️ 既知の追加ブロッカー 2 件 — AMENDMENT (user 決裁必要)

**発見 (2026-07-31 準備セッション、コード実測)**: パケット §3.2 の guard chain 宣言に
網羅漏れがあり、承認済み Option B (§3.3) をそのまま merge しても発火しない:

| # | ゲート | 内容 | 帰結 |
|---|---|---|---|
| 第3 | `gbp_asia_flash_crash` (v8.6 静的、UTC 21-06 × "GBP" in instrument) | cell の LATE 窓 (21-24 UTC) を **100% 内包**。sweep は shadow-eligible 集合 (FORCE_DEMOTED/SENTINEL/trendline-v2) 外 → **hard block (_block + return、行も残らない)** | live fill 0 再演。さらに HTF exemption で rescue 経路が外れるため **shadow 蓄積まで消滅** (4原則#3 違反 + 撤退監視の母数消滅) |
| 第4 | 静的 per-pair spread limit (`EUR_GBP: 1.5p`) + spread/TP 比 gate (20%) | LATE rollover 実測 quoted spread は **5.4〜16.6p (rescued shadow 全 8 発火が超過、中央値 6.6p)**。TP=6×ATR は tail-cap 設計のため比 gate も構造的に全 block | 同上 (hard block) |

T8 期 (06-12〜07-06) にこれらが観測されなかったのは、上流 HTF Hard Block が emit を
100% 削っており下流ゲートが一度もテストされていないため。

**AMENDMENT 実装 (draft branch commit 2 = `dfec4343`、user 決裁待ち)**:
1. `_GBP_ASIA_FLASH_CRASH_EXEMPT_CELLS = {("sweep_reversion_eurgbp_late", "EUR_GBP")}` —
   HTF exemption と同一の estimand 論 (12.4y grid pre-reg にアジア時間フィルタは存在せず、
   cell 定義が全部ブロック帯内 = gate 維持は発火 0 の恒久化)。GBP フラッシュクラッシュ
   tail は 1000u 固定 + SL −4×ATR + 動的 spread_sl_gate が防御
2. 専用 spread cap **10.0p** ([[weekend-gap-stage2-execution-prereg-2026-07-24]] §2.2 の
   専用 cap 前例と同型・同値) — cap 内 = live 送信 / cap 超過 = **shadow row 記録 (分母保存)**。
   静的 limit と比 gate は本 cell のみ置換、**動的 spread_sl_gate (spread/SL>35%) は維持** —
   worst tail (16.6p 級) は cap + 動的の二段遮断。実測 8 発火中 7 が cap 内
3. blast radius = この 1 cell のみ。ゲート本体・他戦略は不変 (CLAUDE.md 原則3 の
   LIVE 側 winning-location フィルタ設計は他戦略に対し維持)。cap 経路は
   `_sweep_reversion_eurgbp_live_eligible` に連動 — pin 再無効化 (R2 stop) で自動不活性化

**執行時の分岐**:
- user が AMENDMENT を承認済み → commit 1+2 を含む PR で執行 (§3)
- 未決裁 → **執行を停止し、本セクション + パケット §8.1 を添えて user に決裁を求める**

## 3. Option B 執行 (単一 PR、パケット §3.3)

前提: §2 verdict = OPTION_B_EXECUTE ∧ §2.5 AMENDMENT 決裁済み

1. draft branch `draft/ps1a-option-b-20260731` (origin push 済み) を main に rebase
   (`prereg-trigger-registry.json` が conflict したら draft 側の t8-sweep エントリ置換を採る)
2. registry `t8-sweep-defer-decision` の `resolved: "EXECUTION-DATE-TBD"` を執行日に更新
3. パケット §6-1: 本番 API 再取得で §1.1/§1.3 テーブルを更新、Status を FINAL 化、
   `ps1a_execution_check.py --json` の出力を判定記録として貼付
4. 初週再ゲート pre-reg を LOCK — §5 のテンプレを decisions/ 新規文書に確定 (発効日 = merge 日)
5. PR 作成 → **Codex review 必須** (LOCK 文書と同型) → CI green 確認
6. `gh pr merge N --merge --admin` (単独コマンド形)
7. deploy 確認 (Render ログ):
   - `[DTE] HTF_HARD_BLOCK` の blocked list に sweep が**現れない**こと (exemption 実効)
   - block_counts: `order_min_spacing` / `gbp_asia_flash_crash` / `spread_wide` /
     `spread_sl_gate` の sweep 行を観測 (`/api/demo/status` block_counts_per_strategy)
   - 初回発火時: `[SHIELD] SWEEP_REVERSION_EURGBP bypass` → OANDA fill (1000u) →
     `ps1a-sweep-live-withdrawal-watch` が live N を計上
8. KB 反映: `python3 tools/sync_kb_index.py --write` + `python3 tools/tier_integrity_check.py --write`
   → `--check` で ERROR=0
9. MEMORY 更新: `project_t8_week1_gate_breach` に執行完了を追記

## 4. Draft branch の内容 (実装・テスト済み、マージ禁止)

branch: `draft/ps1a-option-b-20260731` (origin push 済み)

| commit | 内容 | 決裁状態 |
|---|---|---|
| `8272f994` (commit 1) | §3.3-1〜4: order 層 12-bar min-spacing (専用 reason key `order_min_spacing`、hydration 3h、違反は shadow 降格) / HTF exemption (`DaytradeEngine.HTF_HARD_BLOCK_EXEMPT_CELLS`) / pin 解除 + テスト追随 / registry 置換 (`ps1a-sweep-live-withdrawal-watch`) / pin tests `tests/test_ps1a_option_b_gates.py` | ✅ 承認済みスコープ (2026-07-24) |
| `dfec4343` (commit 2) | §2.5 AMENDMENT: gbp_asia cell 免除 + 専用 spread cap 10.0p + 比 gate 置換 / pin tests `tests/test_ps1a_late_window_amendment.py` | ⚠️ **user 決裁待ち** |

両 commit とも pre-commit full pytest green + check.py 9/9 通過。

## 5. 初週再ゲート pre-reg テンプレ (執行日に LOCK)

- **ゲート①' 頻度帯**: spaced 基準 0.3〜2.6 件/週 (12y band)。下割れ 2 週連続 = live 翻訳
  失敗として R2 stop 再発動。上割れ = min-spacing 故障疑いで forensic
- **ゲート②' spread 実測**: live fill の entry/exit spread 記録。**摩擦が最大リスク**
  (パケット §4-1: 実測 RT ≈ 4.0p 中央値 〜 9p worst vs BT 仮定 1.5p)。live N≥5 で
  実測 RT 摩擦中央値 > 7p なら R2 stop
- **ゲート③' time-stop 執行検証**: 43200s wall-clock time-stop が実際に発火するか
  (≥24h で MFE/MAE 反転のため「12h で必ず切る」は死守 — パケット §2.5)。金曜 entry は
  weekend 跨ぎ estimand 乖離のため別セグメント集計 (パケット §4-9)
- **ゲート④(改)**: 同一 (entry_type, instrument, signal, bar_ts) の **unflagged** DB insert
  2 件以上 → 即停止 (T8 LOCKED 済み。文言明確化提案はパケット §4-8)
- **LOCK Withdrawal triggers 5 項** (live N≥10 EV<0 / N≥20 WR<42% / 累積 DD>100p /
  regime 反転 / 30 日 fire 0 → forensic) は継続有効 — trigger 1 は registry
  `ps1a-sweep-live-withdrawal-watch` が機械監視
- **AMENDMENT 固有の観測項目**: `PS1A_SWEEP_SPREAD_SKIP` (cap 超過 shadow) の頻度 —
  cap 内比率が実測 7/8 から大きく乖離したら spread regime 変化として報告

## 6. Option C (retire) 経路

spaced EV≤0 の場合のみ。draft branch は使わず:
1. registry `t8-sweep-defer-decision` を resolved 化 (resolution に EV 実測を記録)
2. 戦略カード + パケットに retire 判定を追記 (Status FINAL)
3. `HTF_BLOCK_SHADOW_RESCUE` からの sweep 除去 (shadow 蓄積終了) は 4原則#3 と衝突する
   ため user に確認 — rescue 残置 = コストゼロで regime 反転の将来検証余地を残す選択肢あり

## 7. 監視の現況 (2026-07-31 実測)

- `t8-sweep-defer-decision`: WATCHING N=8/10 (undercount 修正済み経路で正常報告、
  Tier A cron → Discord 配線を確認済み)
- 最終発火 2026-07-15 (準備時点で 15.1 日前)。**2026-08-14 まで発火 0 が続くと LOCK
  Withdrawal trigger 5 (30 日 fire 0) の forensic 発動** — `ps1a_execution_check.py` が
  `zero_fire_forensic_alert` で自動警告する
- spaced EV 現況: **+2.47 p/t (>0)** — 今 N=10 に到達すれば Option B 側
- 発火頻度の解釈: 期待 3-4 件/月、直近 16 日ゼロは Poisson で P≈15% (lumpy の範囲内)。
  エッジの 2021+ regime 集中 (LOCK Caveat) を踏まえ、trigger 5 は kill でなく forensic
