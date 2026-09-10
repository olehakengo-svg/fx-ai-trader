# E1 positioning ingest 停止 — Myfxbook 認証失敗 (2026-09-10, P1, rule:R3)

**状態**: 🔴 進行中 (2026-09-10T15:05Z 時点) — **復旧は user の credentials 再投入のみ** (§5)
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
