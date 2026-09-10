# T8 P-S1(a) 執行即応化 readiness 監査 + zero-fire forensic (2026-09-10/11, rule:R3)

- 実施: Claude (P13 実装タスク、worktree agent)
- 対象: `draft/ps1a-option-b-20260731` (執行ペイロード) / sweep_reversion_eurgbp_late × EUR_GBP LATE 窓の 28 日 zero-fire
- 制約遵守: EV 値は本 doc に一切引用しない (親タスク指示 — 登録済み評価経路 `tools/ps1a_execution_check.py` の verdict / N / 日付のみ使用)。forensic は読み取りのみ (本番への書込み・設定変更なし)

---

## §1 draft ブランチの main 追随再解決 — 完了 ✅

### 結果
- `draft/ps1a-option-b-20260731`: `fc81db8b` → **`99e3560d`** に push 更新済み (fast-forward、第1親 = 旧 draft head fc81db8b、第2親 = origin/main b08f874d)
- **main へのマージはしていない** (トリガ成立まで禁止のまま。本更新は「成立日に即マージできる状態の維持」のみ)
- 検証: `pytest tests/ -q` **3267 passed / 0 failed** + `scripts/check.py` 全10チェック通過 (draft 側 merge commit 上で実施)

### conflict 解決 4 ファイル
| ファイル | 解決 |
|---|---|
| `modules/demo_trader.py` | **両立形** (下記) |
| `knowledge-base/wiki/decisions/prereg-trigger-registry.json` | main 現行 (2026-08-17 繰り延べ期日 10-28 等) をベースに draft 差分のみ適用: `t8-sweep-defer-decision` を resolved 化 (active=false、resolved="EXECUTION-DATE-TBD" — merge 時に執行日へ更新) + 後継 `ps1a-sweep-live-withdrawal-watch` 追加 |
| `tests/test_prereg_trigger_watch.py` | draft の執行後 pin を採用し、main の新 pin (mode / n_floor / deadline 2026-10-28) を raw エントリ側 assertion に統合 |
| `knowledge-base/wiki/sessions/2026-08-03-session.md` | union (main が draft 寄与 fc81db8b の行を既に包含 → main 側採用) |

### semantic 衝突の両立形 (P-S1(a) 免除 × PR #180 rescue の併存)
- **gate 判定**は draft の `_gbp_asia_flash_crash_blocked()` に集約 — `_GBP_ASIA_FLASH_CRASH_EXEMPT_CELLS` (sweep×EUR_GBP、AMENDMENT user 承認 2026-08-03) は gate 自体を通過 = live 経路
- **gate に落ちた場合の分岐**は PR #180 の `_GBP_ASIA_SHADOW_RESCUE_CELLS` を維持 — rescue cell は rowless hard block ではなく shadow 退避 (is_shadow=1、OANDA 送信なし)
- 効果: 免除が将来 pin 等で無効化されても rescue が **backstop** となり、P-S1(a) トリガ分母の silent 枯渇 (2026-08-12 forensic の 4 イベント消失) を再発させない = **rescue 経路を落とさない (4原則#3 準拠)**
- テスト層の同衝突: `tests/test_gbp_asia_shadow_rescue.py` の旧 pin (「rescue cell はゾーン内で必ず shadow」) は AMENDMENT と非両立のため、(1) 免除 cell はゾーン内で live、(2) 免除を monkeypatch で外すと rescue backstop が shadow 退避、の 2 テストに更新 (backstop の実在を統合レベルで pin)
- 併せて確認: AMENDMENT の cell-scoped spread cap (10.0p、cap 超過 = shadow row で分母保存) が merge 後コードで静的 1.5p gate / spread_guard を `_ps1a_sweep_entry` で正しく回避すること、`htf_hard_block_exempt` (app.py / DaytradeEngine) が生存していることを grep + pin テストで確認済み

---

## §2 zero-fire forensic (読み取りのみ) — 判別: **経路故障 (構造バグ)、市場要因ではない** 🔴

### §2.1 登録済み評価経路の出力 (`tools/ps1a_execution_check.py --json`、2026-09-10 実行)
- verdict: **WAITING** — unique N=9/10 (トリガ待ち)
- last_fire: 2026-08-12T21:16Z / days_since_last_fire: 28.1
- zero_fire_forensic_alert: false (閾値 30 日、あと ~2 日で発火)
- ※ stats の EV 値は本 doc に引用しない (親指示)

### §2.2 市場イベントは来ている (candidate funnel、C1 テーブル)
`/api/demo/evaluated-candidates?strategy=sweep_reversion_eurgbp_late` (行は **HTF Hard Block 通過後**に記録される):
- 直近 7 日: candidates 102 (全 BUY) / selected 76
- 直近 29 日のイベント日 (select_best 通過): **4 日** — 08-20 (104 cand)、09-01 (47 cand、bar 21:15)、09-07 (50 cand / sel 24、bar 21:45)、09-09 (52 cand、bar 21:15)
- 4 独立バーのイベント ≈ 歴史的 unique 発火レート (9 イベント/40 日) と整合 — **シグナル生成・エンジン生存・選抜は全て正常**

### §2.3 死因の直接証拠 (Render 本番ログ、web service srv-d6va1of5r7bs73en10vg)
**2026-09-09 21:17:47Z** (bar 21:15 イベント) の同一 emit のログ連鎖:
```
[SHADOW] GBP Asia bypass: sweep_reversion_eurgbp_late (flash crash zone → shadow)   ← PR #180 rescue 正常動作
[SHADOW] BUY TREND_BEAR block: sweep_reversion_eurgbp_late conf=65 → shadow
[MTF_MONITOR] EUR_GBP entry=sweep_reversion_eurgbp_late signal=BUY mtf=range_tight
[SENTINEL_BLOCK_DIAG] sweep_reversion_eurgbp_late blocked at: spread_wide(5.7pip>1.5)  ← ここで rowless 死
```
**2026-09-01 21:16-21:17Z** も同一連鎖: `GBP Asia bypass → shadow` 直後に `spread_wide(9.4pip>1.5)` / `spread_wide(8.2pip>1.5)`。

機構 (origin/main 現行コード、demo_trader.py 静的 spread gate):
```python
if _spread_pips > _spread_limit and not _is_shadow_eligible and not _wg_entry:
    _block(f"spread_wide(...)")   # → return (rowless)
```
gate の判定は `_is_shadow_eligible` (**集合ベース**、sweep は集合外) であって `_is_shadow` (rescue が立てたフラグ) ではない。**gbp_asia rescue で shadow 退避済みの emit も、この下流 gate が rowless hard block する** — 2026-07-31 に発見済みの「第4 estimand ブロッカー」(静的 per-pair limit EUR_GBP 1.5p vs LATE rollover 実測 5-17p) が main に現存し、rescue (第3ブロッカー修復、PR #180) の効果を無効化している。

副次ブロッカー: 09-09 21:16:40Z に `score_gate(misalign:BUY,-0.26)` で一部 emit が先に消えている (09-07 の sel 24/50 も同因の可能性)。これは market-state 依存の既設 gate で、主因ではない。

補足 (観測面の注意): `/api/demo/block-counts` は in-memory でプロセス再起動でリセットされるため、翌日読むと前夜 LATE 窓の block が見えないことがある。恒久記録は Render ログの `SENTINEL_BLOCK_DIAG` 行と C1 テーブル。

### §2.4 帰結 — トリガ計数の silent 枯渇は 08-12 以降も継続 + 構造的デッドロック
1. t8 トリガ分母 (unique N、**DB 行ベース**) は 08-12 以降 4 イベントを全て取りこぼした。1 件でも行になっていれば unique N=10 → **TRIGGERED** だった蓋然性が高い (4 件は独立バー)
2. **デッドロック構造**: 第4ブロッカーの修正 (cell-scoped spread cap、cap 超過 = shadow row で分母保存) は draft にのみ存在 → draft の merge はトリガ成立が条件 → トリガは第4ブロッカーが分母を殺しているため成立し得ない (LATE rollover spread が 1.5p を下回る稀な瞬間を除く)
3. これは 2026-08-17 user 決裁 (計数器故障 07-16〜08-12 の 28 日分を期日繰り延べ 09-30→10-28) と**同型の故障が別の層で継続**している状態。retire 判定 (10-28 に N<5) は N=9 で抵触しないが、**執行トリガ (N>=10) は現行 main のままでは事実上到達不能**

### §2.5 判別まとめ
| 仮説 | 判定 | 根拠 |
|---|---|---|
| 市場要因 (イベント不発) | ❌ 棄却 | 29 日で 4 イベント日、candidate 253 行が select_best 通過 |
| エンジン/経路の生存故障 | ❌ 棄却 | mode thread 稼働、rescue ログ・選抜ログ・block 診断とも正常出力 |
| gbp_asia gate の退行 | ❌ 棄却 | PR #180 rescue は全イベントで正常動作 (bypass ログ) |
| **第4ブロッカー (静的 spread_wide 1.5p) の rowless kill** | ✅ **確定** | 09-01 / 09-09 のログ連鎖で直接観測 (5.7p / 8.2p / 9.4p > 1.5p)。修正は draft にのみ存在 |

---

## §3 registry 追記の提案 (registry 編集はしない — 親が適用)

`t8-sweep-defer-decision` の `message` 末尾に追記する提案文:

> 【2026-09-11 追記】draft/ps1a-option-b-20260731 は origin/main (b08f874d) と再解決済み (99e3560d、conflict 4 ファイル解消・pin 3267 green) — トリガ成立日に即マージ可能状態。⚠️ 同日 forensic (raw/audits/t8-ps1a-readiness-2026-09-10.md): LATE 窓 28 日 zero-fire は市場要因ではなく第4ブロッカー (静的 spread_wide 1.5p が gbp_asia rescue 後の行書込みを rowless kill) の継続 — 08-12 以降 4 イベント (08-20/09-01/09-07/09-09) が全て計数漏れ。本トリガの unique N は現行 main のままでは実質増えない (修正は draft 側 AMENDMENT にのみ存在 = デッドロック)。08-17 繰り延べ決裁と同型につき、計数救済 or 執行条件の再解釈は user 決裁事項。

(補足: 上記デッドロックの解消手段は user 決裁マターのため本監査では執行しない。選択肢の整理 — (a) ログ/C1 で観測された 4 イベントの計数救済 + 期日再繰り延べ、(b) AMENDMENT のうち「shadow row 記録」部分のみの先行切り出し (live 送信なし、分母保存のみ = 4原則#3 修理として R3 相当)、(c) 現状維持で 10-28 期日到達を待つ — は親セッション/user に委ねる)

---

## §4 検証記録
- draft merge commit: `99e3560d` (`Merge origin/main into draft/ps1a-option-b-20260731 — 執行即応化の再解決 (rule:R3)`)
- push: `fc81db8b..99e3560d  ps1a-draft-sync-20260911 -> draft/ps1a-option-b-20260731` (2026-09-11 JST)
- テスト: `python3 -m pytest tests/ -q` → 3267 passed, 17 skipped, 1 xfailed / `python3 scripts/check.py` → 全10チェック通過 (pre-push hook でも再実行され通過)
- forensic データソース: tools/ps1a_execution_check.py (登録済み評価経路) / /api/demo/evaluated-candidates (C1) / /api/demo/block-counts / Render logs (srv-d6va1of5r7bs73en10vg、2026-09-01・09-09 の LATE 窓)
