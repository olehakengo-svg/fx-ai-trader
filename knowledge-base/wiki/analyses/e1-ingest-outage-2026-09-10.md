# E1 positioning ingest 停止 — Myfxbook 認証失敗 (2026-09-10, P1, rule:R3)

**状態**: 🔴 進行中 (2026-09-11T07:30Z 再実測、§7) — **復旧は user の credentials 再投入のみ** (§5)
**影響**: E1 positioning (唯一の主力供給ライン) の pre-reg §2.5 coverage budget を market-hour 毎に不可逆燃焼中
**関連**: [[e1-positioning-contrarian-prereg-2026-07-16]] / [[e1-positioning-ingest-2026-07-14]] / registry `e1-positioning-ingest-freshness`

---

## §1 タイムライン (UTC、全て実測)

| 時刻 | 事象 | 根拠 |
|---|---|---|
| 2026-09-10T06:58:44.973617Z | **最終 verified** (13 キー全て同時刻) | `/api/positioning/export?table=health_log` id=53115 (USD_JPY)、status `health.verified:*` |
| ~07:18Z (推定、[06:58:44, ~07:20] に有界) | **認証失敗開始** — 次 poll cycle (poll 1200s + jitter <120s) から `outlook: api: Wrong email/password.` | poll cadence から逆算。以後の全 cycle が同エラー |
| 08:58:44Z | **§2.2 stale cap 超過 = NA 燃焼開始** (verified age > 2h) | pre-reg §2.2 主モード定義 |
| 11:17:30Z | web service プロセス再起動 (`restarts=1`)。新プロセスでも `logins_total=0` — 認証失敗はプロセス由来でないことを確認 | status `started_at` / `last_restart_at` |
| ~14:1xZ | 反証レビューが実測: `consecutive_cycle_failures=8`、13 キー全 stale >7h | インシデント起票 |
| 14:27:24Z | 直近の失敗 cycle (`last_error` タイムスタンプ) | status `last_cycle_at` |
| 14:44:46Z | **本再実測** (§2) — 停止継続中 | `/api/positioning/status` |

## §2 現状再実測 (2026-09-10T14:44:46Z、read-only)

`GET https://fx-ai-trader.onrender.com/api/positioning/status`:

- `source=myfxbook` / `running=true` / `enabled=true` — worker 自体は生存 (heartbeat `last_cycle_at=14:27:24Z` は前進)
- `last_error = "2026-09-10T14:27:24Z outlook: api: Wrong email/password."`
- `consecutive_cycle_failures = 10` (11:17:30Z の再起動以降の 10 cycle 全滅。プロセス内 counter のため再起動でリセット — 07:18Z からの通算失敗 cycle は ~22)
- `myfxbook: configured=true / logged_in=false / logins_total=0 / requests_total=10` — **毎 cycle 1 回の login 試行が全て拒否されている**
- 13 instrument × `verified:*:outlook` 全キー = `2026-09-10T06:58:44.973617Z` (stale **27,944s ≈ 7.76h**)
- `saved_total=0` / `dedup_skips=0` (再起動以降)

**帰属**: コード/env/デプロイ由来は除外済み (myfxbook_client.py / positioning_ingest.py は 2026-07 以来無変更、env 変更を伴うデプロイなし、プロセス再起動を跨いで同一エラー)。Myfxbook サーバ側が credentials を拒否している — 候補は (a) password の失効/変更、(b) Myfxbook 側 account lockout、(c) アカウント状態変更。切り分けは user の web ログイン (§5-a) でのみ可能。

## §3 Coverage budget 会計 (pre-reg §2.5 原文の定義に忠実)

**定義の出典** (数値は全て pre-reg 原文から):
- §2.5-1 coverage gate: 各 primary ペアで burn-in 後の市場時間グリッドスロット (cutoff − h 打ち切り適用後) のうち有効 (§2.2 stale cap non-NA ∧ cycle 稼働) が **≥ 90%**。不達ペアは family から機械除外 (裁量なし)
- §2.2 stale cap (主モード): age(t) = t − last_verified_at > **2h** (市場時間) のスロットのみ NA。cycle heartbeat は継続しているため NA の源は stale cap のみ
- §2.2 市場時間: America/New_York Sun 17:00–Fri 17:00 = 夏時間で **Sun 21:00 – Fri 21:00 UTC** (評価窓は全域夏時間)
- §5 評価窓: burn-in 20 営業日 → **2026-08-13 〜 cutoff 2026-10-08** ≈ 8 週 × 120 market-h = **960 market-h**

**会計** (1 分分解能で機械計算、`scratchpad/budget.py` 相当のロジック):

| 項目 | h=4h combo | h=24h combo |
|---|---|---|
| 分母 (960 − h censoring) | 956.0h | 936.0h |
| 10% NA 許容 (budget) | **95.6h** | **93.6h** |
| 既往 debit: Render Disk 満杯 08-23〜08-26 ([[disk-full-write-outage-2026-08-26]]、registry 記載値) | −54.6h | −54.6h |
| 本 incident: NA 開始 08:58:44Z → 14:44:46Z | −5.78h | −5.78h |
| **残 budget (14:44:46Z 時点)** | **35.2h** | **33.2h** |

**燃焼レート**: 金曜クローズ (09-11T21:00Z) まで 1 market-h/実時間 h で連続燃焼 → 週末 (Sat–Sun 21:00Z) は停止 → 日曜 21:00Z 再開。

**breach 予測 (停止継続時)**: 全 6 primary ペアが同時に coverage < 90% を割る時刻 =
- h=24h combo: **2026-09-13T23:57Z** (JST 09-14 08:57)
- h=4h combo: **2026-09-14T01:57Z** (JST 09-14 10:57)

**breach の帰結** (機械): §2.5-1 で 6 primary 全ペア機械除外 → 残 0 < 4 ペア → §2.5-3 family gate = **verdict 4 週 postpone** (look 非消費、1 回限り、cutoff/verdict/窓終端を同幅スライド)。first look **2026-10-15 → ~2026-11-12**。E1 は唯一の主力供給ライン ([[shortest-path-decision-memo-2026-07-10]] — 内部母集団枯渇の三重確認により供給は外部仮説のみ) のため **M1 経路 ~4 週遅延**。2 回目の不達は DEFERRED (user 裁定)。

**併走する §2.5-2 (stale gap)**: 単一連続欠測 > 24h (市場時間) は当該区間を解析除外 — 本 incident は **2026-09-11T08:59Z** に到達する (停止継続時)。除外日 > 評価窓 20% (≈8 日) で当該ペア除外。§2.5-2 の区間除外が coverage 分母から外れるかは原文に明記がない — **verdict 時の機械判定に委ね、ここでは解釈を加えない** (盛らない原則)。

**盛らないための注記**: 上記は「budget = 分母の 10%」の単純会計で、既往の細かい stale gap (registry 実測: 48 日で 2h 超 gap は disk 事故 1 回のみ、それ以外 p99 < 2h) を 0 と置いている。実際の残 budget はこれよりわずかに小さい可能性がある (方向は breach 前倒し側)。逆に、NA 開始を「認証失敗開始 07:18Z」でなく stale cap 定義どおり 08:58:44Z としているのは原文準拠 (07:18Z 起点で数えると燃焼を 1.67h 過大計上する)。

## §4 なぜ 7h+ 無言だったか (検知経路の解剖) と修理

| 経路 | 状態 (incident 時点) | 検知遅延 |
|---|---|---|
| Render ログ `[positioning] FETCH FAILED` (毎 cycle) | 書かれていたが**読み手なし** (「書ける/読める/意味を持つ」の 1 段目止まり — C1 write-only と同型) | ∞ |
| registry `e1-positioning-ingest-freshness` (verified age > 2h, 機械評価) | 稼働中だが経路は `quant_gate_status.py` → `prereg_trigger_watch` の **daily cron 00:20 UTC のみ** | 最悪 ~24h (本件は ~17h) |
| `scripts/anomaly_watcher.py` (15 分 cron + Discord) | `/api/positioning/status` を**見ていない** (WATCHED_PATHS は取引系 4 本のみ) | 盲点 |

**修理 (本 PR)**:
1. **lockout 防止 backoff** (`modules/positioning_ingest.py` + `modules/myfxbook_client.py`): 認証失敗 (`is_auth_failure` — session 失効/transport とは分類分離) で login リトライを exponential backoff (1800s × 2^n、**上限 6h**)。連続 4 回で長期 pause を明示ログで宣言 (以後 6h 毎 1 回のみ再試行 — 復旧検知経路は残す)。**認証成功で即通常化**。backoff skip 中も heartbeat は書き、verified:* は書かない (鮮度検知を殺さない)。counterfactual テスト済み (`test_auth_failure_backoff_counterfactual` — 配線を殺すと fail)。
2. **fail-loud 化** (`scripts/anomaly_watcher.py`): `/api/positioning/status` を WATCHED_PATHS に追加し、`positioning_auth_failed` (Discord 毎時) / `positioning_stale` (6h バケット) / `positioning_freshness_missing` (記録のみ) を新設。検知遅延 ~17h → **~15 分**。読み手の存在 (main 配線 / 通知バケット / event line) をテストで pin。
3. **live 取引経路 非接触の確認** (全数 grep): `positioning_ingest` / `myfxbook_client` の参照元は `app.py` (起動フック + read-only API)、`modules/demo_db.py` (schema 冪等作成のみ)、`modules/market_data_ingest.py` (docstring のパターン言及のみ)。`demo_trader.py` / `oanda_bridge.py` / `modules/strategies/` からの参照ゼロ。positioning は E1 データ収集専用で、発注・シグナル・Kelly に一切関与しない。

## §5 user 復旧手順 (資格情報は user のみが触る)

**(a) 生死判別**: https://www.myfxbook.com に **web ブラウザでログイン**して切り分ける:
   - ログイン成功 → API 側 password が古い/違う (Myfxbook のアカウント設定で API 用 password を確認)
   - 「wrong email/password」→ password 失効/変更済み → (b) へ
   - lockout 系メッセージ → 時間を置いて再試行 (ingest 側は backoff 済みで悪化させない)
   - ⚠️ web 側でも失敗を連打しない (lockout 悪化)

**(b) 必要なら password reset**: Myfxbook の "Forgot password" から再設定。

**(c) Render env 再投入**: Render dashboard → web service **`srv-d6va1of5r7bs73en10vg`** (fx-ai-trader) → Environment → **`MYFXBOOK_PASSWORD`** を新しい値に更新 (email も変えた場合は `MYFXBOOK_EMAIL` も) → Save changes (自動 redeploy。redeploy で backoff 状態もリセットされ、初回 cycle から即 login 試行)。

**(d) 復旧確認** (redeploy 完了 ~3-4 分後):
```bash
# 受け入れ確認 (login + outlook 1 回、rate limit を 2 req 消費)
curl -s "https://fx-ai-trader.onrender.com/api/positioning/probe?run=1&source=myfxbook"
# → {"configured": true, "login_ok": true, "outlook_ok": true, ...} なら復旧

# 定常確認 (次 cycle ~20 分以内に verified が前進する)
curl -s "https://fx-ai-trader.onrender.com/api/positioning/status" | python3 -c "
import json,sys; d=json.load(sys.stdin)
print('logged_in:', d['myfxbook']['logged_in'])
print('last_error:', d['last_error'])
print('verified USD_JPY:', d['health'].get('verified:USD_JPY:outlook'))"
```
復旧後、anomaly_watcher の `positioning_auth_failed` / `positioning_stale` は次 run (≤15 分) から自然消灯する。

## §6 クオンツ判断の記録

- **Rule 3 (Immediate)**: 構造バグ (監視盲点) + 不可逆な budget 燃焼への防御。365 日 BT 不要 — 本 doc が code/math derivation。
- **動機**: データ駆動 (registry 実測 + status API 実測 + pre-reg 原文の機械会計)。感情由来の項目なし。
- **backoff は budget を守らない** ことを明記する: budget 燃焼は認証が直るまで続き、backoff はそれを止めない。backoff の目的は user の復旧可能性 (lockout 回避) の保全のみ。budget の救済は user の (a)〜(c) だけ。
- 4 原則との整合: positioning は取引パス外 (原則 1 に非接触)。Shadow/LIVE データ蓄積系のクリーン性を守る修理 (最重要目標「クリーンデータ蓄積が最優先」に直結)。

---

## §7 追記 — 2026-09-11 follow-up 調査 (rule:R3)

**状態**: 🔴 停止継続中 (2026-09-11T07:30Z 実測、verified age 24.5h)。復旧条件は §5 のまま (user credentials 再投入のみ)。worker は auth backoff pause 中 (`auth_paused=true`、次回自動 login 試行 = **10:46:37Z**、以後 6h 毎)。

### 7a. 停止境界の精密化 (§1 の推定を Render ログ実測で置換)

§1 は「~07:18Z (推定、[06:58:44, ~07:20] に有界)」としていたが、web service ログの全数突合で確定:

| 時刻 (UTC) | 事象 | 根拠 |
|---|---|---|
| 09-10T06:58:45Z | **最後の login 成功** — PR #231 デプロイ (instance kzb7k) の初回 cycle、`cycle done saved=12` | Render ログ 06:58:45.041Z |
| 09-10T07:06:03Z | **最初の login 失敗** — PR #232 デプロイ (instance j5974) の初回 cycle、`FETCH FAILED ... Wrong email/password.` | Render ログ 07:06:03.389Z |

この間に client 側の login 試行はゼロ (成功した kzb7k session は生きたまま)、code/env 変更もゼロ。つまり **credentials の無効化は 7.3 分の窓 (06:58:45–07:06:03 UTC = JST 09-10 15:58–16:06) にサーバ側で発生**した。以後 09-11T06:46:37Z (直近試行) まで全 login が同一エラー。なお §1 の NA 燃焼開始 08:58:44Z (stale cap 定義準拠) は不変。

### 7b. 帰属の絞り込み (統制実験 + 消去法)

| 仮説 | 判定 | 根拠 (全て 2026-09-11 実測) |
|---|---|---|
| Render プロセス停止 | ❌ 除外 | worker 生存 (heartbeat `last_cycle_at` 前進、self-heal 正常)、複数 restart/デプロイを跨いで同一エラー |
| Disk 満杯 / DB 書込み停止 | ❌ 除外 | `positioning_health` heartbeat 書込み継続、`db_error=null` |
| ベンダー側 API 全面障害 / API 仕様変更 | ❌ 除外 | **統制実験**: garbage credentials で `login.json` → HTTP 200 + `{"error":true,"message":"Wrong email/password."}` (本番と同一文言・同一形状) = API は正常稼働し、本番エラーは「認証拒否」の正規応答。web 検索でも 09-10 のマス障害/仕様変更報告なし |
| rate limit (100 req/24h) | ❌ ほぼ除外 | 停止前 24h の実測リクエスト = cycle done 71 行 (outlook 71 req) + login 数回 ≈ **<80 < 100** (ログ全数計数)。かつ 24h 窓 block なら 09-11T07:06Z までに解除のはずが onset+23.7h (06:46:37Z) で失敗継続。onset+27.7h の自動試行 (10:46:37Z) が成功した場合のみこの分岐が復活 |
| **credentials のサーバ側無効化 / account lock** | ⭕ 残存 (唯一) | 上記消去法。内訳: (a) password 失効/変更 — user 自身の変更 or Myfxbook 強制 reset、(b) account lock/suspension — datacenter IP からの機械的 login パターンの abuse 判定。**06:58:45Z の新 instance (新 egress IP) login 直後に無効化された時刻相関は (b) を示唆**するが、web ログインなしに判別不能 |

**§5-(a) への追加手順**: user は web ログイン試行の前に、**メール受信箱で 09-10 15:58–16:06 JST 前後の Myfxbook からのメール** (security alert / forced password reset / verification 要求) を確認すること — (a)/(b) の判別が最速で付き、web 側の失敗連打 (lockout 悪化) も避けられる。

### 7c. Budget 会計の更新 (§3 の方法を延長、2026-09-11T07:30Z 時点)

| 項目 | h=4h combo | h=24h combo |
|---|---|---|
| §3 時点 (09-10T14:44:46Z) の残 budget | 35.2h | 33.2h |
| 追加燃焼 (14:44:46Z → 09-11T07:30Z、全域 market-h) | −16.75h | −16.75h |
| **残 budget (09-11T07:30Z)** | **18.5h** | **16.5h** |

- 金曜クローズ (09-11T21:00Z) まで放置した場合の週末持ち越し残 = **5.0h / 3.0h**
- **§2.5-2 連続欠測 24h 到達: 2026-09-11T08:58:44Z (本追記の ~1.5h 後)** — 以後この区間は解析除外に転化し、除外日数が評価窓 20% (≈8 日) の当該ペア除外カウントへ積み上がり始める
- breach 予測は §3 から不変 (停止が中断なく継続のため): **h=24h 2026-09-13T23:57Z / h=4h 2026-09-14T01:57Z** → 6 primary 全機械除外 → family verdict **4 週 postpone** (first look 10-15 → ~11-12) = M1 経路 ~4 週遅延
- **実務デッドライン: 日曜市場再開 2026-09-13T21:00Z (JST 月曜 09-14 06:00) までに §5 (a)〜(c) 完了**。それ以降は数時間で breach。金曜クローズ前の復旧なら残 budget を最大 ~18h 温存できる

### 7d. 通知経路の live 検証 (PR #243 修理の「読み手」確認)

anomaly_watcher (cron `fx-ai-tier-c-anomaly`, */15) が `positioning_auth_failed` + `positioning_stale` を毎 run 発火中と実測 (09-11T05:30〜07:30Z の 9 run 連続で event line 出力、`oldest_verified_age_hours` が単調増加)。検知・通知経路は生きている — **残る律速は user アクションのみ**。

### 7e. 本追記のクオンツ判断記録

- **Rule 3**: インシデント帰属の精密化 + budget 会計更新のみ。コード変更ゼロ、live 挙動不変。
- 重複修理なし確認: backoff / fail-loud / runbook は PR #243 で完了済み ([[trigger-watch-gap-audit-2026-09-10]] の「修復済みか先に確認」教訓を適用)。本追記は §1 の推定精緻化・§2 帰属候補の消去法完遂・§3 会計の時点更新のみを行った。
