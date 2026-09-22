# Lesson: pre-fork サーバの master で import 時スレッドが DB を触ると、fork した worker の DB が永久ハングする (2026-09-22)

**発見日**: 2026-09-22 | **修正**: PR (rule:R3) — DailyReview を serving process へ defer + `/healthz/http` health check | 詳細: [[http-blind-fork-poisoning-2026-09-22]]

## 何が起きたか
- Render の gunicorn は app.py を **master で import** し直後に worker を fork する。`DemoTrader.__init__` が import 時に起動する DailyReviewEngine は UTC 0 時台起動で**即座に**全件スキャン + 204 MB backup を master で走らせ、fork がその最中に落ちた。
- 子 (HTTP worker) は SQLite のプロセス共有 mutex を locked のまま継承 → **DB を触る全ルートが永久ハング**。`HEAD /` だけ 200。gunicorn `--timeout` は発火せず (main thread は notify 継続)、Render は TCP 疎通しか見ない → **3h19m〜3h31m × 3 回** (09-12 / 09-15 / 09-22)。master 側エンジンは全期間 tick していた。

## なぜ見逃したか
1. **同じ fork 問題を network 層で 2026-07-16 に直していた** ([[e1-positioning-ingest-2026-07-14]] §11) が、「import 時に起動する thread は禁忌」を **network thread に限定**して読んだ。DB thread は対称の反対側だった (MEMORY `feedback_check_the_symmetric_side_2026_09_19` の 3 例目)。
2. 「engine は生きている (tick 前進)」を「サービスは生きている」と読んだ。engine 生存と HTTP 生存は**別の estimand**で、しかも**別プロセス**だった。
3. 0 時台起動 7 件中 3 件の確率事象。「直後に 200 が返った」1 件で安心し、並べて見なかった。
4. 外部監視は `api_unreachable` (全滅) しか持たず、**read-timeout (接続成立・無応答) と connection error (不達) を区別しなかった**。読み手 (daily report の LLM) は材料なしに「無料 tier のスリープ」と原因を捏造した。

## 教訓
- **pre-fork サーバの master では import 時スレッドを一切起動しない** — network も DB も。起動は serving process の request 経路 (heartbeat / heal) に一本化する。「resource の種類が違うから別問題」は同型再発の温床。
- **HTTP 層の生死はプロセス生存・エンジン生存と別に測る**。gunicorn gthread の `--timeout` はハンドラ滞留を検知しない。HTTP health check (DB を 1 回開くプローブ) が無いと数時間盲目になる。
- **外部の読み手に渡せるのは失敗クラスだけ**。「unreachable, cause unknown (ReadTimeout)」と書く。原因は観測から導けないなら書かせない (生成器側で規則 + 出力後検査)。
- **確率的事象は起動条件で層別して並べる** (0 時台 / それ以外)。1 件の反例では棄却できない。
