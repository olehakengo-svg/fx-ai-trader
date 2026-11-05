# sprint 0922 close review §4 #8 — プロセス固定費: (i) wiki-daily 欠落の原因調査 (記録) / (ii) 座礁ローカル main の恒久策 3 択 (再上程) / (iii) storm_guard 状態永続化 (R3 候補、user 決裁待ち) (2026-11-05)

**位置づけ**: [[sprint-0922-close-review-2026-10-21]] §4 #8 (R3 記録 / user 上程) の消化。registry `sprint-1022-process-fixed-cost-upsubmit` (期日 11-07) を本稿で resolve。(ii) の執行 (`reset --hard`) と (iii) の採否は **user 専権** — autopilot は代行しない。
**rule:R3** (記録のみ。live/shadow/lot/凍結値 非接触)。

## (i) wiki-daily scheduled run の 10 月欠落 — 原因 = ホスト (ローカル Mac) の可用性、skill 側ではない

**データ源**: scheduled task `wiki-daily-update` (cron `47 20 * * 1-5` JST = 11:47Z 月〜金、jitter 767 s) の run 一覧 (`list_task_runs`、2026-11-05 02:10Z 取得、直近 50 run)。scheduled task 側に「発火しなかった日」のログは**存在しない** (run 一覧に行が無い = 発火記録なし)。

| 10 月営業日 (22 日) | run の有無 | status / 開始 UTC | 分類 |
|---|---|---|---|
| 10-01, 02, 05, 06, 07, 08, 13, 15 (06:35Z), 16, 20 (×2), 22, 29 (10-28 23:59Z 開始 + 12:00Z 再実行) | あり | succeeded | 正常 (12 日) ※10-02 は 15:24Z 開始で翌 09:00Z まで 17.6 h、10-08 は 15:24Z 開始 — 定刻 11:47Z から 3.6 h 遅延 |
| 10-09 (13:22Z), 10-15 (13:13Z、同日 06:35Z の成功 run とは別), 10-21 (13:23Z), 10-23 (23:57Z), 10-30 (**10-31 04:58Z** = 定刻から 17 h 遅延) | あり | **failed** — 全件 `API Error: Can't reach the API server — check your internet or DNS (ENOTFOUND)` | **遅延発火 + ネットワーク不達** (5 件、うち営業日欠落は 10-09 / 10-21 / 10-23 / 10-30 の 4 日) |
| 10-12 (月), 10-14 (水), 10-19 (月), 10-26 (月), 10-27 (火) | **なし** | 発火記録なし | **未発火** (5 日) |

**集計**: 欠落 = 未発火 5 + 失敗 4 = **9 / 22 営業日 = 41%** (close review の「9 日 / 21 日 = 43%」と件数一致、分母は暦の数え方の差)。

**原因の読み (scheduled task 側の証拠のみで判定)**:
1. 失敗 5 件の開始時刻が**全て定刻 (11:47Z ± 13 min) から外れている** (13:13Z〜翌 04:58Z) = スケジューラがホストのスリープ/オフライン明けに遅延発火し、その時点でネットワーク (DNS) が未復旧 → `ENOTFOUND` で即死。skill の内容 (KB 書き込み) には到達していない。
2. 未発火 5 日は月曜 3 / 火曜 1 / 水曜 1 — 当日の発火窓にホストが起きていなかった (スリープ/シャットダウン) と読むのが最も単純。scheduled task はローカル Mac の desktop app が走らせるため、ホストが落ちていれば発火記録自体が残らない。
3. 9 月も同型 (09-08 `Request timed out`、09-15 / 09-23 `Your computer went to sleep mid-response`、08-24 / 08-26 `ENOTFOUND`) — **「コンピュータがスリープした」を scheduler 自身が明示した例が 2 件ある**。
4. skill (SKILL.md) 側の欠陥ではない: 成功 run は 10〜20 分で完走し KB を書いている。

**帰結 (記録)**: 欠落の固定費は「ホスト可用性」に帰属。対策はスケジューラの置き場 (ローカル desktop app → クラウド routine) か、ホストのスリープ設定 (user 側) のどちらか。本稿は選択しない ((ii) の 3 択 C と同根なので併せて上程)。

## (ii) 座礁ローカル main の恒久策 3 択 — 再上程 (user 決裁、`reset --hard` は user 操作)

**現状**: 2026-11-03 の user 指示 `reset --hard` で main は origin と同期 (540 behind / 3 ahead を解消)。しかし wiki-daily は**ローカル main で走る**ため、次の構造は不変: (a) ローカル main が origin より遅れていると hook 直コミットが push できず座礁 (救済 PR が autopilot の固定費 = 30 日で 8 本 ≈ 4 セッション、close review §4 #8) / (b) 2026-11-05 02:10Z 時点でも wiki-daily (01:44Z 開始、進行中) がローカル main に 6 ファイル未コミット編集を積んでいる (push できるかは run 終了時の origin との差で決まる)。

| 案 | 内容 | 利点 | 欠点 | 執行主体 |
|---|---|---|---|---|
| **A: pull-first fail-fast** | wiki-daily SKILL.md 冒頭に `git -C <repo> pull --ff-only origin main` を置き、ff できなければ**書かずに終了** (座礁物を作らない)。末尾の hook commit/push は現状維持 | 変更最小 (SKILL.md 1 行 + 終了条件)。座礁物がゼロになる | ff 不能日は wiki-daily が丸ごと欠落 (ただし現状も座礁 = 事実上欠落)。ローカル main に user の未コミット作業があると pull が止まる | Claude (SKILL.md 編集は autopilot 可) |
| **B: worktree 実行** | wiki-daily を `git worktree add .worktrees/wiki-daily-<date> origin/main` で走らせ、成果物を branch + PR にして autopilot が union マージ | ローカル main に依存しない。救済 PR が「通常 PR」に置き換わり差分照合が不要 | PR 1 本/日が増える (Codex レビューは docs-only なら即マージ可)。hook の直コミット経路を worktree 向けに調整 | Claude |
| **C: クラウド routine 化** | wiki-daily を scheduled cloud agent (routine) に移し、常に origin/main の fresh checkout から走らせる | (i) のホスト可用性問題も同時に解消 (41% 欠落 → 0 が期待値)。座礁は構造的に消える | 実行環境の secrets (`.env` 相当、OANDA/Render 読み取り) をクラウド側に置く必要 = user 設定。費用発生の可能性 | **user** (環境・費用) + Claude (routine 定義) |

**Claude 推奨 (拘束しない)**: **C** が (i)(ii) を同時に解く唯一の案。C の準備 (secrets) が重いなら **A を即日** (autopilot が SKILL.md を編集、R3) → C を追って。B は A より重く C より効果が小さい。**無回答 = A を次 run で実施** (可逆、SKILL.md 1 行)。

## (iii) `storm_guard` 状態の永続化 — enforce とは別の R3 候補 (user 決裁待ちに置く)

- **事象**: `storm_guard` の per-trade 状態 (sent_total / confirmed_sl / breaker 窓 / totals) は in-process のみで、**code deploy・env 変更の再起動ごとに消える**。観測 7 例 (10-16 / 10-20 ×2 / 10-30 / 11-03 ×2 / 11-04) — storm #3 の 46,098 送信も status 上から消滅し、累計は Render ログ / OANDA transactions にしか残らない ([[../analyses/storm-guard-design-2026-09-22]] §7.4)。
- **影響**: **readout の分母のみ** (guard の防御動作そのものには影響しない: enforce ON 後の初 live trail #1347030 は再起動直後の fresh 状態でも dead-band 65 skip / 送信 5 / 喪失 0 で機能、§7.5)。restored trade (再起動時に open 中の live 建玉) は seed `broker` で baseline を再取得するため fail-open 窓も短い。
- **R3 候補 (起案のみ、code は書かない)**: per-trade 状態と totals を KV (DD 台帳と同じ store) に逐次保存し、起動時に復元。影響範囲 = bridge の状態管理のみ、lot/シグナル/閾値 非接触。コスト ≈ code PR 1 本 (review gate 必須、live 経路)。
- **上程**: 「readout 分母の連続性」のためだけに live 経路 PR を 1 本使うかは user 判断。**無回答 = 起案しない** (現状維持、readout は「再起動後 epoch」として読み続ける)。

## registry

- `sprint-1022-process-fixed-cost-upsubmit` (11-07) → **resolve** (本稿 = (i) 調査記録 + (ii)(iii) 上程文)。
- 新規なし (user 返答待ち項目は本稿の「無回答 = …」既定で自走する: (ii) A は次 run、(iii) は起案しない)。
