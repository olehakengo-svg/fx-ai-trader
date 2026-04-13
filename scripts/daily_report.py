#!/usr/bin/env python3
"""
FX AI Trader — セッションベース日次レポートパイプライン

使用方法:
  python3 scripts/daily_report.py              # セッション自動判定
  python3 scripts/daily_report.py pre_tokyo    # Pre-Tokyo (JST 09:00)
  python3 scripts/daily_report.py post_tokyo   # Post-Tokyo (JST 15:00)
  python3 scripts/daily_report.py post_london  # Post-London (JST 01:00)
  python3 scripts/daily_report.py post_ny      # Post-NY (JST 07:00)

環境変数:
  ANTHROPIC_API_KEY     — Claude API キー（必須）
  DISCORD_WEBHOOK_URL   — Discord送信先（必須）

セッション:
  pre_tokyo   — JST 09:00 / UTC 00:00: 前日全体総括＋本日作戦＋戦略立案
  post_tokyo  — JST 15:00 / UTC 06:00: 東京セッション総括＋ロンドン準備
  post_london — JST 01:00 / UTC 16:00: ロンドンセッション総括＋NY準備
  post_ny     — JST 07:00 / UTC 22:00: NYセッション総括＋1日の総括＋翌朝引き継ぎ

処理フロー:
  Step 1. 本番APIからデータ取得
  Step 2. Analyst  → セッション別レポート＋クオンツ見解
  Step 3. Strategy → 作戦立案（pre_tokyoのみ）
  Step 4. Discord  → レポート送信 → ユーザーが最終判断
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

FIDELITY_CUTOFF = "2026-04-08T00:00:00+00:00"
CLAUDE_MODEL = "claude-sonnet-4-6"

PRODUCTION_APIS = {
    "status": "https://fx-ai-trader.onrender.com/api/demo/status",
    "trades": f"https://fx-ai-trader.onrender.com/api/demo/trades?limit=500&date_from={FIDELITY_CUTOFF[:10]}&status=closed",
    "oanda":  "https://fx-ai-trader.onrender.com/api/oanda/status",
    "oanda_audit": "https://fx-ai-trader.onrender.com/api/oanda/audit",
    "risk":   "https://fx-ai-trader.onrender.com/api/risk/dashboard",
    "regime": "https://fx-ai-trader.onrender.com/api/market/regime",
}

# セッション時間帯（UTC）
SESSION_TIME_RANGES = {
    "pre_tokyo":   (None, None),           # 全期間（前日総括）
    "post_tokyo":  ("00:00", "06:00"),     # UTC 00:00-06:00 = JST 09:00-15:00
    "post_london": ("07:00", "16:00"),     # UTC 07:00-16:00 = JST 16:00-01:00
    "post_ny":     ("16:00", "22:00"),     # UTC 16:00-22:00 = JST 01:00-07:00
}


# ── セッション定義 ─────────────────────────────────────

SESSION_CONFIGS = {
    "pre_tokyo": {
        "label": "Pre-Tokyo Briefing",
        "emoji": "\U0001f305",
        "discord_tag": "Pre-Tokyo",
        "run_strategy_planner": True,
    },
    "post_tokyo": {
        "label": "Post-Tokyo Report",
        "emoji": "\U0001f5fc",
        "discord_tag": "Post-Tokyo",
        "run_strategy_planner": False,
    },
    "post_london": {
        "label": "Post-London Report",
        "emoji": "\U0001f3db\ufe0f",
        "discord_tag": "Post-London",
        "run_strategy_planner": False,
    },
    "post_ny": {
        "label": "Post-NY Report",
        "emoji": "\U0001f5fd",
        "discord_tag": "Post-NY",
        "run_strategy_planner": False,
    },
}

VALID_SESSIONS = set(SESSION_CONFIGS.keys())


def detect_session(override: str | None = None) -> str:
    """UTC時刻からセッションを自動判定。CLI引数でオーバーライド可能。"""
    if override and override in VALID_SESSIONS:
        return override
    hour = datetime.now(timezone.utc).hour
    # UTC 00:00 cron → pre_tokyo
    if 23 <= hour or hour < 3:
        return "pre_tokyo"
    # UTC 06:00 cron → post_tokyo
    elif 4 <= hour < 9:
        return "post_tokyo"
    # UTC 16:00 cron → post_london
    elif 14 <= hour < 19:
        return "post_london"
    # UTC 22:00 cron → post_ny
    elif 20 <= hour < 23:
        return "post_ny"
    return "pre_tokyo"


# ── セッション別アナリストプロンプト ───────────────────

SESSION_ANALYST_ADDITIONS = {
    "pre_tokyo": """
## セッション: Pre-Tokyo Briefing (JST 09:00)
前日の全セッション（東京・ロンドン・NY）を総括し、本日の準備を行ってください。

### 出力フォーマット（厳守）
1. **前日サマリー**: PnL合計、トレード数、全体WR — 簡潔に2-3行
2. **戦略別パフォーマンス**: N/WR/EV テーブル（Cutoff後、Shadow除外、XAU別枠）
3. **前日の課題と対策**: 何が問題だったか → 今日どう対処するか
4. **レジーム状況**: 現在の各ペアのレジーム＋各戦略への影響を言語化
5. **本日の注視事項**: 重要時間帯・レジーム遷移リスク
6. **OANDA転送状況**: SENT/SKIP率、block_counts主因
7. **クオンツ見解**: 最重要シグナル・構造的観察・推奨アクション
""",
    "post_tokyo": """
## セッション: Post-Tokyo Report (JST 15:00)
東京セッション（JST 09:00-15:00 / UTC 00:00-06:00）を総括してください。
tradesデータのopen_time/close_timeがUTC 00:00-06:00の範囲のトレードを東京セッションとして抽出・分析。
該当トレードがない場合は「東京セッション: トレードなし」と明記し、全体概況を簡潔に報告。
※セッション内N<5の場合、単独統計は参考値として扱い、直近3-5日の同セッション傾向も参照すること。

### 出力フォーマット（厳守）
1. **東京セッション結果**: PnL、トレード数、WR（この時間帯のみ）
2. **What Worked**: 成功トレード — 戦略名・ペア・pips・成功要因（1文）
3. **What Didn't Work**: 失敗トレード — 戦略名・ペア・pips・失敗要因（1文）
4. **戦略調整判断**: パラメータ変更の要否 → YES/NOを明確に（YESなら具体的に何を）
5. **ロンドンセッション準備**:
   - 東京→ロンドン移行でのATR/レジーム変化予測
   - 推奨戦略配分（どの戦略をどのペアで）
   - **「何もしない」が最適な場合は「NO ACTION推奨」と明記**
   - 推奨根拠（データ不足、レジーム不明瞭、DD防御発動中、etc.）
6. **クオンツ見解**: 最重要シグナル1点（簡潔に2-3行）
""",
    "post_london": """
## セッション: Post-London Report (JST 01:00)
ロンドンセッション（UTC 07:00-16:00）を総括してください。
「セッション内トレード」データがロンドン時間帯のトレードです。全期間マトリクスではなくセッション内データに集中。

### 出力フォーマット（厳守）
1. **ロンドンセッション結果**: PnL、トレード数、WR（この時間帯のみ）
2. **What Worked**: 成功トレード — 戦略名・ペア・pips・成功要因（1文）
3. **What Didn't Work**: 失敗トレード — 戦略名・ペア・pips・失敗要因（1文）
4. **東京との比較**: 東京セッションと比べてレジーム・WR・PnLがどう変化したか
5. **NYセッション準備**:
   - ロンドン→NY移行でのATR/レジーム変化予測
   - 推奨戦略配分（どの戦略をどのペアで）
   - **「何もしない」が最適な場合は「NO ACTION推奨」と明記**
6. **本日暫定結果**: 東京+ロンドン累計PnL・トレード数
7. **クオンツ見解**: 最重要シグナル1点（簡潔に2-3行）
""",
    "post_ny": """
## セッション: Post-NY Report (JST 07:00)
NYセッション（UTC 16:00-22:00）を総括し、1日の最終総括を行ってください。
「セッション内トレード」データがNY時間帯のトレードです。全期間マトリクスではなくセッション内データに集中。

### 出力フォーマット（厳守）
1. **NYセッション結果**: PnL、トレード数、WR（この時間帯のみ）
2. **What Worked**: 成功トレード — 戦略名・ペア・pips・成功要因（1文）
3. **What Didn't Work**: 失敗トレード — 戦略名・ペア・pips・失敗要因（1文）
4. **1日の総括**:
   - 東京 / ロンドン / NY の各セッションPnL比較テーブル
   - 本日合計PnL・トレード数・WR
   - 最も成績が良かった/悪かったセッション＋戦略
5. **OANDA転送状況**: 本日のSENT/SKIP率、block_counts主因
6. **翌朝への引き継ぎ**:
   - 未解決の課題（パラメータ要調整、降格候補、レジーム注視など）
   - 翌日のpre_tokyoで確認すべき事項
   - **「何もしない」が最適な場合は「NO ACTION推奨」と明記**
7. **クオンツ見解**: 本日の最重要学び1点 + 明日への示唆
""",
}


# ── API ────────────────────────────────────────────────

def fetch_json(url: str, timeout: int = 15) -> dict:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "FX-DailyReport/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        print(f"  \u26a0\ufe0f  fetch failed: {url} \u2014 {e}", file=sys.stderr)
        return {}


def call_claude(system: str, messages: list[dict], max_tokens: int = 2500) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY \u304c\u8a2d\u5b9a\u3055\u308c\u3066\u3044\u307e\u305b\u3093")

    payload = json.dumps({
        "model": CLAUDE_MODEL,
        "max_tokens": max_tokens,
        "system": system,
        "messages": messages,
    }).encode()

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=90) as r:
        resp = json.loads(r.read().decode())
    return resp["content"][0]["text"]


# ── データ前処理（lesson-raw-json-to-llm: 生JSONをLLMに渡さない） ──

def _filter_by_time(trades: list, time_from: str, time_to: str) -> list:
    """exit_timeのHH:MM部分でフィルタ。"""
    result = []
    for t in trades:
        exit_time = t.get("exit_time", "") or t.get("entry_time", "")
        if not exit_time:
            continue
        try:
            hhmm = exit_time[11:16]
            if time_from <= hhmm < time_to:
                result.append(t)
        except (IndexError, TypeError):
            continue
    return result


def _filter_today(trades: list) -> list:
    """本日のトレードのみ抽出。"""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return [t for t in trades if (t.get("exit_time", "") or "")[:10] == today]


def _build_strat_pair_table(trades: list, title: str) -> str:
    """戦略×ペア集計テーブルを生成。"""
    from collections import defaultdict
    if not trades:
        return f"### {title}\nトレードなし\n"
    strat_pair = defaultdict(lambda: {"n": 0, "wins": 0, "pnl": 0.0})
    for t in trades:
        key = (t.get("entry_type", "unknown"), t.get("instrument", "unknown"))
        strat_pair[key]["n"] += 1
        if t.get("outcome") == "WIN":
            strat_pair[key]["wins"] += 1
        strat_pair[key]["pnl"] += t.get("pnl_pips", 0)
    rows = []
    for (strat, pair), s in sorted(strat_pair.items(), key=lambda x: -x[1]["n"]):
        wr = (s["wins"] / s["n"] * 100) if s["n"] > 0 else 0
        ev = s["pnl"] / s["n"] if s["n"] > 0 else 0
        rows.append(f"| {strat} | {pair} | {s['n']} | {wr:.1f}% | {ev:+.2f} | {s['pnl']:+.1f} |")
    total_n = len(trades)
    total_pnl = sum(t.get("pnl_pips", 0) for t in trades)
    total_wins = sum(1 for t in trades if t.get("outcome") == "WIN")
    total_wr = (total_wins / total_n * 100) if total_n > 0 else 0
    return (
        f"### {title}（N={total_n}, WR={total_wr:.1f}%, PnL={total_pnl:+.1f}）\n"
        "| Strategy | Pair | N | WR% | EV | PnL |\n"
        "|---|---|---|---|---|---|\n" + "\n".join(rows) + "\n"
    )


def _build_trade_detail(trades: list, title: str, limit: int = 20) -> str:
    """トレード詳細テーブルを生成。"""
    if not trades:
        return f"### {title}\nトレードなし\n"
    rows = []
    for t in trades[-limit:]:
        rows.append(
            f"| {t.get('entry_type','')} | {t.get('instrument','')} "
            f"| {t.get('direction','')} | {t.get('outcome','')} "
            f"| {t.get('pnl_pips', 0):+.1f} | {t.get('close_reason','')} "
            f"| {t.get('spread_at_entry', 0):.1f} |"
        )
    return (
        f"### {title}（{len(trades)}件）\n"
        "| Strategy | Pair | Dir | Outcome | PnL | Reason | Spread |\n"
        "|---|---|---|---|---|---|---|\n" + "\n".join(rows) + "\n"
    )


def preprocess_bt_divergence(data: dict) -> str:
    """v8.9: BT/本番乖離テーブル — 最新BTファイルとライブデータを比較。
    戦略×ペア粒度でWR/EV乖離を計算し、>20ppを⚠️フラグ。
    """
    import os, re
    from collections import defaultdict
    bt_dir = os.path.join(os.path.dirname(__file__), "..", "knowledge-base", "raw", "bt-results")
    if not os.path.isdir(bt_dir):
        return ""
    # 最新BTファイルを検索
    # ペア別テーブル(### USD_JPY 等)を含むBTファイルを優先選択
    # "all-pairs" ファイルが最も構造化されている
    bt_files = sorted([f for f in os.listdir(bt_dir) if f.endswith(".md")], reverse=True)
    if not bt_files:
        return ""
    # all-pairs ファイルを優先、なければ最新
    bt_path = None
    for f in bt_files:
        if "all-pairs" in f or "full-audit" in f:
            bt_path = os.path.join(bt_dir, f)
            break
    if not bt_path:
        bt_path = os.path.join(bt_dir, bt_files[0])
    try:
        with open(bt_path) as f:
            bt_content = f.read()
    except Exception:
        return ""
    # BTテーブルからWR/EVを抽出 (format: | strategy | WR | EV | ...)
    bt_metrics = {}  # (strategy, pair) -> {"wr": float, "ev": float, "n": int}
    # パース: "### PAIR (Nt, WR=X%, ...)" セクション内のテーブル行
    current_pair = None
    for line in bt_content.split("\n"):
        pair_match = re.match(r"###?\s+(USD_JPY|EUR_USD|GBP_USD|EUR_JPY)\b", line)
        if pair_match:
            current_pair = pair_match.group(1)
            continue
        if current_pair and line.startswith("|") and not line.startswith("|-"):
            cols = [c.strip() for c in line.split("|")]
            if len(cols) >= 4:
                # 戦略名: **bold** マーカーを除去
                strat = cols[1].replace("**", "").strip() if len(cols) > 1 else ""
                if not strat or strat in ("Strategy", "") or strat.startswith("--"):
                    continue
                try:
                    # WR: "87.5%" or "100%" — %を除去
                    wr_str = cols[2].replace("%", "").replace("**", "").strip() if len(cols) > 2 else "0"
                    # EV: "+0.993" or "-0.047" — ★を除去
                    ev_str = re.sub(r"[★✓✗△\*]", "", cols[3]).strip() if len(cols) > 3 else "0"
                    wr = float(wr_str) if wr_str and wr_str not in ("—", "N/A") else 0
                    ev = float(ev_str) if ev_str and ev_str not in ("—", "N/A") else 0
                    bt_metrics[(strat, current_pair)] = {"wr": wr, "ev": ev, "n": 0}
                except (ValueError, IndexError):
                    continue
    if not bt_metrics:
        return ""
    # ライブデータ集計
    trades_raw = data.get("trades", {})
    trades = trades_raw.get("trades", [])
    fx_trades = [t for t in trades if t.get("is_shadow", 0) == 0
                 and "XAU" not in t.get("instrument", "")
                 and t.get("status", "").upper() == "CLOSED"]
    live_metrics = defaultdict(lambda: {"n": 0, "wins": 0, "pnl": 0.0})
    for t in fx_trades:
        key = (t.get("entry_type", "unknown"), t.get("instrument", "unknown"))
        live_metrics[key]["n"] += 1
        if t.get("outcome") == "WIN":
            live_metrics[key]["wins"] += 1
        live_metrics[key]["pnl"] += t.get("pnl_pips", 0)
    # 乖離テーブル生成
    rows = []
    for (strat, pair), bt in sorted(bt_metrics.items()):
        live = live_metrics.get((strat, pair))
        if not live or live["n"] < 3:
            continue  # ライブN<3は比較不能
        live_wr = (live["wins"] / live["n"] * 100) if live["n"] > 0 else 0
        live_ev = live["pnl"] / live["n"] if live["n"] > 0 else 0
        d_wr = bt["wr"] - live_wr
        alert = ""
        if abs(d_wr) > 30:
            alert = "🔴"
        elif abs(d_wr) > 20:
            alert = "⚠️"
        rows.append(
            f"| {strat} | {pair} | {bt['n']} | {bt['wr']:.1f}% "
            f"| {live['n']} | {live_wr:.1f}% | {d_wr:+.1f}pp | {alert} |"
        )
    if not rows:
        return ""
    return (
        f"### BT vs Live 乖離（BT file: {bt_files[0]}）\n"
        "| Strategy | Pair | N_BT | WR_BT | N_Live | WR_Live | ΔWR | Alert |\n"
        "|---|---|---|---|---|---|---|---|\n" + "\n".join(rows[:15]) + "\n"
    )


def preprocess_trades(data: dict, session: str) -> str:
    """セッション別にデータ構成を変えてLLMに渡す。

    - pre_tokyo: 全期間マトリクス + 前日詳細（1日の方針立案用）
    - post_tokyo/post_london/post_ny: セッション内データのみ + 当日累計（セッション振り返り用）
    """
    trades_raw = data.get("trades", {})
    trades = trades_raw.get("trades", [])
    if not trades:
        return "### TRADES\nトレードデータなし（API取得失敗またはトレード0件）\n"

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")

    # Shadow/XAU除外
    fx_trades = [t for t in trades if t.get("is_shadow", 0) == 0
                 and "XAU" not in t.get("instrument", "")]
    xau_trades = [t for t in trades if t.get("is_shadow", 0) == 0
                  and "XAU" in t.get("instrument", "")]

    sections = []

    if session == "pre_tokyo":
        # ── pre_tokyo: 全期間マトリクス + 前日詳細 ──
        sections.append(_build_strat_pair_table(fx_trades, "戦略×ペア マトリクス（Cutoff後全期間）"))

        yesterday_trades = [t for t in fx_trades
                           if (t.get("exit_time", "") or "")[:10] == yesterday]
        if yesterday_trades:
            sections.append(_build_strat_pair_table(yesterday_trades, f"前日（{yesterday}）戦略別"))
            sections.append(_build_trade_detail(yesterday_trades, f"前日トレード詳細"))
        else:
            sections.append(f"### 前日（{yesterday}）\nトレードなし\n")

    else:
        # ── post_tokyo / post_london / post_ny: セッション内 + 当日累計 ──
        time_range = SESSION_TIME_RANGES.get(session, (None, None))
        today_trades = _filter_today(fx_trades)

        # セッション内トレード（メインデータ）
        if time_range[0] is not None:
            session_trades = _filter_by_time(today_trades, time_range[0], time_range[1])
            sess_label = f"セッション内（本日 UTC {time_range[0]}-{time_range[1]}）"
            sections.append(_build_strat_pair_table(session_trades, sess_label))
            sections.append(_build_trade_detail(session_trades, "セッション内トレード詳細"))

        # 当日累計（参考）
        if today_trades:
            today_n = len(today_trades)
            today_pnl = sum(t.get("pnl_pips", 0) for t in today_trades)
            today_wins = sum(1 for t in today_trades if t.get("outcome") == "WIN")
            today_wr = (today_wins / today_n * 100) if today_n > 0 else 0
            sections.append(
                f"### 本日累計（参考）\n"
                f"| N | WR% | PnL(pips) |\n|---|---|---|\n"
                f"| {today_n} | {today_wr:.1f}% | {today_pnl:+.1f} |\n"
            )

        # post_ny: 東京/ロンドン/NYのセッション比較テーブル
        if session == "post_ny":
            tokyo = _filter_by_time(today_trades, "00:00", "06:00")
            london = _filter_by_time(today_trades, "07:00", "16:00")
            ny = _filter_by_time(today_trades, "16:00", "22:00")
            def _sess_stats(tl):
                n = len(tl)
                pnl = sum(t.get("pnl_pips", 0) for t in tl)
                wr = (sum(1 for t in tl if t.get("outcome") == "WIN") / n * 100) if n > 0 else 0
                return n, wr, pnl
            tn, twr, tpnl = _sess_stats(tokyo)
            ln, lwr, lpnl = _sess_stats(london)
            nn, nwr, npnl = _sess_stats(ny)
            sections.append(
                "### セッション比較（本日）\n"
                "| Session | N | WR% | PnL |\n|---|---|---|---|\n"
                f"| Tokyo (00-06) | {tn} | {twr:.1f}% | {tpnl:+.1f} |\n"
                f"| London (07-16) | {ln} | {lwr:.1f}% | {lpnl:+.1f} |\n"
                f"| NY (16-22) | {nn} | {nwr:.1f}% | {npnl:+.1f} |\n"
                f"| **Total** | **{tn+ln+nn}** | **—** | **{tpnl+lpnl+npnl:+.1f}** |\n"
            )

    # XAU別枠（全セッション共通）
    if xau_trades:
        xau_n = len(xau_trades)
        xau_pnl = sum(t.get("pnl_pips", 0) for t in xau_trades)
        sections.append(f"### XAU別枠\n| N | PnL(pips) |\n|---|---|\n| {xau_n} | {xau_pnl:+.1f} |\n")

    return "\n".join(sections)


def preprocess_oanda(data: dict) -> str:
    """OANDAステータス+約定監査を集計テーブルに変換。"""
    sections = []

    # OANDAステータス
    oanda = data.get("oanda", {})
    if oanda:
        hb = oanda.get("heartbeat", {})
        audit_sum = oanda.get("audit_summary", {})
        sections.append(
            f"### OANDA接続状況\n"
            f"| Active | NAV | Balance | Latency | Open Trades |\n"
            f"|---|---|---|---|---|\n"
            f"| {oanda.get('active', 'N/A')} "
            f"| {hb.get('nav', 'N/A')} "
            f"| {hb.get('balance', 'N/A')} "
            f"| {hb.get('latency_ms', 'N/A')}ms "
            f"| {hb.get('open_trade_count', 'N/A')} |\n"
        )
        if audit_sum:
            sections.append(
                f"### OANDA転送率\n"
                f"| Total | Live(SENT) | Demo Only(SKIP) | Live Rate |\n"
                f"|---|---|---|---|\n"
                f"| {audit_sum.get('recent_total', 0)} "
                f"| {audit_sum.get('live', 0)} "
                f"| {audit_sum.get('demo_only', 0)} "
                f"| {audit_sum.get('live_ratio', 'N/A')} |\n"
            )

    # OANDA約定監査 — block_reason集計
    audit_data = data.get("oanda_audit", {})
    audit_entries = audit_data.get("audit", [])
    if audit_entries:
        from collections import Counter
        block_reasons = Counter()
        bridge_statuses = Counter()
        for e in audit_entries:
            bridge_statuses[e.get("bridge_status", "unknown")] += 1
            reason = e.get("block_reason", "")
            if reason:
                block_reasons[reason] += 1

        # bridge_status集計
        bs_rows = [f"| {status} | {count} |" for status, count in bridge_statuses.most_common()]
        sections.append(
            "### OANDA Bridge Status\n"
            "| Status | Count |\n|---|---|\n" + "\n".join(bs_rows) + "\n"
        )

        # block_reason TOP 10
        if block_reasons:
            br_rows = [f"| {reason} | {count} |" for reason, count in block_reasons.most_common(10)]
            sections.append(
                "### OANDA Block Reasons (TOP 10)\n"
                "| Reason | Count |\n|---|---|\n" + "\n".join(br_rows) + "\n"
            )

    return "\n".join(sections) if sections else "### OANDA\nOANDAデータ取得不可\n"


def preprocess_regime(data: dict) -> str:
    """レジームデータを簡潔なテーブルに変換。"""
    regime_data = data.get("regime", {})
    if not regime_data or not regime_data.get("pairs"):
        return ""
    rows = []
    for pair, info in sorted(regime_data.get("pairs", {}).items()):
        if "error" in info:
            rows.append(f"| {pair} | ERROR | - | - | - |")
            continue
        rows.append(
            f"| {pair} | {info['regime']} "
            f"| {info.get('atr_pctile_20d', 0):.0f}% "
            f"| {info.get('sma20_slope', 0):+.5f} "
            f"| {info.get('last_close', 'N/A')} |"
        )
    return (
        "### レジーム分類\n"
        "| Pair | Regime | ATR%ile(20d) | SMA20 Slope | Last Close |\n"
        "|---|---|---|---|---|\n" + "\n".join(rows) + "\n"
    )


def preprocess_status(data: dict) -> str:
    """ステータスデータからblock_countsなど重要指標を抽出。"""
    status = data.get("status", {})
    if not status:
        return "### STATUS\nステータスデータ取得不可\n"
    sections = []

    # モード別ステータス
    modes = status.get("modes", {})
    if modes:
        mode_rows = []
        for mode_name, mode_info in sorted(modes.items()):
            running = mode_info.get("running", False)
            trades = mode_info.get("trades_count", 0)
            mode_rows.append(f"| {mode_name} | {'ON' if running else 'OFF'} | {trades} |")
        sections.append(
            "### モード別ステータス\n"
            "| Mode | Running | Trades |\n|---|---|---|\n" + "\n".join(mode_rows) + "\n"
        )

    # block_counts
    block_counts = status.get("block_counts", {})
    if block_counts:
        bc_rows = [f"| {k} | {v} |" for k, v in
                   sorted(block_counts.items(), key=lambda x: -x[1])[:15]]
        sections.append(
            "### Block Counts (TOP 15)\n"
            "| Reason | Count |\n|---|---|\n" + "\n".join(bc_rows) + "\n"
        )

    # DD防御
    dd = status.get("dd", status.get("drawdown", {}))
    if dd:
        sections.append(
            f"### DD防御\n"
            f"| DD% | Lot Mult | EQ Peak | EQ Current |\n|---|---|---|---|\n"
            f"| {dd.get('dd_pct', 'N/A')}% | {dd.get('lot_mult', 'N/A')}x "
            f"| {dd.get('eq_peak', 'N/A')} | {dd.get('eq_current', 'N/A')} |\n"
        )

    return "\n".join(sections) if sections else f"### STATUS\n{json.dumps(status, ensure_ascii=False, indent=2)[:1500]}\n"


# ── エージェントプロンプト読み込み ──────────────────────

def load_agent_prompt(name: str) -> str:
    """agents/{name}.md のフロントマター除去後の本文を返す。"""
    path = ROOT / "scripts" / "agents" / f"{name}.md"
    if not path.exists():
        path = ROOT / ".claude" / "agents" / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"agents/{name}.md が見つかりません (scripts/agents/ と .claude/agents/ を探索)")
    parts = path.read_text(encoding="utf-8").split("---")
    return (parts[2] if len(parts) >= 3 else parts[-1]).strip()


# ── KBコンテキスト読み込み ─────────────────────────────

def load_kb_context() -> str:
    """KBからTier分類・教訓・未解決事項を読み込み、レポート品質を向上させる。"""
    sections = []
    # Tier分類（index.md 先頭60行）
    index_path = ROOT / "knowledge-base" / "wiki" / "index.md"
    if index_path.exists():
        lines = index_path.read_text(encoding="utf-8").splitlines()[:60]
        sections.append("### KB: Tier\u5206\u985e\n" + "\n".join(lines))
    # 教訓（lessons/index.md 先頭20行）
    lessons_path = ROOT / "knowledge-base" / "wiki" / "lessons" / "index.md"
    if lessons_path.exists():
        lines = lessons_path.read_text(encoding="utf-8").splitlines()[:20]
        sections.append("### KB: \u904e\u53bb\u306e\u6559\u8a13\n" + "\n".join(lines))
    # 未解決事項（最新セッションログ）
    sessions_dir = ROOT / "knowledge-base" / "wiki" / "sessions"
    if sessions_dir.exists():
        session_files = sorted(sessions_dir.glob("*.md"), reverse=True)
        if session_files:
            text = session_files[0].read_text(encoding="utf-8")
            import re
            m = re.search(r'## \u672a\u89e3\u6c7a\u4e8b\u9805.*', text, re.DOTALL)
            if m:
                sections.append("### KB: \u672a\u89e3\u6c7a\u4e8b\u9805\n" + m.group()[:500])
    return "\n\n".join(sections)[:2000] if sections else ""


# ── エラー通知・自己診断 ──────────────────────────────

def send_error_notification(message: str) -> None:
    """#error-report チャンネルにパイプライン状態を通知。"""
    webhook = os.environ.get("DISCORD_ERROR_WEBHOOK_URL")
    if not webhook:
        return
    payload = json.dumps({"content": message[:1900]}).encode()
    req = urllib.request.Request(
        webhook,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "FX-KB-Monitor/1.0"},
    )
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"  \u26a0\ufe0f  Error\u901a\u77e5\u9001\u4fe1\u5931\u6557: {e}", file=sys.stderr)


def check_kb_pipeline_health() -> list[str]:
    """KB\u30d1\u30a4\u30d7\u30e9\u30a4\u30f3\u306e\u5065\u5168\u6027\u3092\u81ea\u5df1\u8a3a\u65ad\u3002

    GitHub Actions\u4e0a\u3067\u5b9f\u884c\u3055\u308c\u308b\u524d\u63d0 \u2014 \u30ea\u30dd\u30b8\u30c8\u30ea\u306b\u5b58\u5728\u3059\u308b\u30d5\u30a1\u30a4\u30eb\u304b\u3089
    \u524d\u56de\u306e\u30d1\u30a4\u30d7\u30e9\u30a4\u30f3\u6210\u5426\u3092\u63a8\u5b9a\u3059\u308b\u3002
    """
    issues = []
    today = datetime.now(timezone.utc)

    # 1. \u76f4\u8fd1\u306edaily report\u304cKB\u306b\u5b58\u5728\u3059\u308b\u304b\uff08\u5e73\u65e53\u65e5\u4ee5\u5185\uff09
    trade_logs = ROOT / "knowledge-base" / "raw" / "trade-logs"
    if trade_logs.exists():
        report_files = [
            f for f in sorted(trade_logs.glob("20*-*.md"), reverse=True)
            if f.stem not in ("analyst-memory", "analyst-memory-archive")
        ]
        if report_files:
            latest_name = report_files[0].name[:10]
            try:
                latest_date = datetime.strptime(latest_name, "%Y-%m-%d").replace(
                    tzinfo=timezone.utc
                )
                age = (today - latest_date).days
                if age > 3:
                    issues.append(
                        f"\u6700\u65b0daily report ({latest_name}) \u304c{age}\u65e5\u524d \u2014 \u30d1\u30a4\u30d7\u30e9\u30a4\u30f3\u505c\u6b62\u306e\u53ef\u80fd\u6027"
                    )
            except ValueError:
                pass
        else:
            issues.append("daily report\u30d5\u30a1\u30a4\u30eb\u304cKB\u306b0\u4ef6 \u2014 \u30d1\u30a4\u30d7\u30e9\u30a4\u30f3\u672a\u7a3c\u50cd")

    # 2. analyst-memory\u306b\u81ea\u52d5\u30a8\u30f3\u30c8\u30ea\u304c\u3042\u308b\u304b
    memory = trade_logs / "analyst-memory.md" if trade_logs.exists() else None
    if memory and memory.exists():
        content = memory.read_text(encoding="utf-8")
        has_auto = any(
            tag in content
            for tag in ("Pre-Tokyo", "Post-Tokyo", "Post-London", "(auto-daily)")
        )
        if not has_auto:
            issues.append(
                "analyst-memory\u306b\u81ea\u52d5\u30a8\u30f3\u30c8\u30ea0\u4ef6 \u2014 \u30d5\u30a3\u30fc\u30c9\u30d0\u30c3\u30af\u30eb\u30fc\u30d7\u672a\u63a5\u7d9a"
            )

    # 3. \u9031\u6b21\u76e3\u67fb\u306e\u6709\u7121
    audits = ROOT / "knowledge-base" / "raw" / "audits"
    audit_files = [
        f for f in (audits.glob("*.md") if audits.exists() else [])
        if f.name != ".gitkeep"
    ]
    if not audit_files:
        issues.append("weekly audit 0\u4ef6 \u2014 \u76e3\u67fb\u30d1\u30a4\u30d7\u30e9\u30a4\u30f3\u672a\u7a3c\u50cd")
    else:
        latest_audit = sorted(audit_files, reverse=True)[0].name[:10]
        try:
            audit_date = datetime.strptime(latest_audit, "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            )
            if (today - audit_date).days > 14:
                issues.append(
                    f"\u6700\u65b0audit ({latest_audit}) \u304c{(today - audit_date).days}\u65e5\u524d \u2014 14\u65e5\u8d85\u904e"
                )
        except ValueError:
            pass

    # 4. \u30ec\u30b8\u30fc\u30e0\u30b9\u30ca\u30c3\u30d7\u30b7\u30e7\u30c3\u30c8\u306e\u6709\u7121
    market = ROOT / "knowledge-base" / "raw" / "market-analysis"
    regime_files = [
        f for f in (market.glob("*.md") if market.exists() else [])
        if f.name != ".gitkeep"
    ]
    if not regime_files:
        issues.append("regime snapshot 0\u4ef6 \u2014 \u30ec\u30b8\u30fc\u30e0\u84c4\u7a4d\u672a\u7a3c\u50cd")

    return issues


# ── Analyst レポート ───────────────────────────────────

def run_analyst(data: dict, session: str = "pre_tokyo",
                health_warnings: list[str] | None = None) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    kb_ctx = load_kb_context()
    kb_section = f"\n\n### KB蓄積知見（Tier分類・教訓・未解決事項）\n{kb_ctx}" if kb_ctx else ""

    session_prompt = SESSION_ANALYST_ADDITIONS.get(session, SESSION_ANALYST_ADDITIONS["pre_tokyo"])

    # パイプライン健全性警告（Claudeに自己診断結果を認識させる）
    health_section = ""
    if health_warnings:
        health_section = (
            "\n\n### \u26a0\ufe0f KB PIPELINE HEALTH\uff08\u81ea\u5df1\u8a3a\u65ad\u7d50\u679c\uff09\n"
            "\u4ee5\u4e0b\u306e\u30d1\u30a4\u30d7\u30e9\u30a4\u30f3\u7570\u5e38\u3092\u691c\u51fa\u3002\u30ec\u30dd\u30fc\u30c8\u672b\u5c3e\u306e\u30af\u30aa\u30f3\u30c4\u898b\u89e3\u3067\u3053\u306e\u72b6\u614b\u304c\u30c7\u30fc\u30bf\u54c1\u8cea\u306b\u4e0e\u3048\u308b\u5f71\u97ff\u3092\u8a00\u53ca\u3059\u308b\u3053\u3068\u3002\n"
            + "\n".join(f"- {w}" for w in health_warnings)
        )

    # データ前処理（lesson-raw-json-to-llm: LLMには集計済みテーブルを渡す）
    trades_table = preprocess_trades(data, session)
    oanda_table = preprocess_oanda(data)
    regime_table = preprocess_regime(data)
    status_table = preprocess_status(data)
    bt_div_table = preprocess_bt_divergence(data)  # v8.9: BT/本番乖離

    user_msg = f"""以下は本番システムの**事前集計済みデータ**です（{now}）。
Fidelity Cutoff: {FIDELITY_CUTOFF}
※テーブルはPython側でis_shadow=0 & XAU別枠で集計済み。数値はそのまま使用可能。

{status_table}
{trades_table}
{bt_div_table}
{oanda_table}
{regime_table}{kb_section}{health_section}

---
## 分析ルール
1. 上記テーブルの数値は集計済み — 再計算不要。テーブルをそのまま引用してよい
2. テーブルにない洞察（課題分析・レジーム影響・推奨アクション）に注力すること
3. OANDAのBlock ReasonsとBridge Statusからデモ/本番の乖離を分析すること
4. 学術文献の引用は不要 — 実データに基づく判断のみ
{session_prompt}"""

    return call_claude(load_agent_prompt("analyst"), [{"role": "user", "content": user_msg}])


# ── Strategy 作戦立案（pre_tokyoのみ） ────────────────

STRATEGY_PLANNING_SUFFIX = """
---

## 作戦立案モード（自動レポート用）

上記のシニアクオンツとしての設計原則に加え、アナリストレポートを受け取ったときは
**コードは書かず**、以下の形式で「試す価値があるか」の判断材料のみを提示する。

### 出力フォーマット

**【作戦候補 #N】戦略名（仮）**
- **仮説**: 何の非効率を突くか（1文）
- **根拠**: なぜ今このデータがその機会を示しているか
- **学術的裏付け**: 著者(年) + 知見（1行）
- **失敗シナリオ**: この戦略が機能しない状況
- **摩擦試算**: spread_cost概算（閾値と比較）
- **GO基準**: 実装に進むべき条件（例: 「N=20後WR>55%」）
- **推奨優先度**: 高 / 中 / 低（理由1文）

候補は最大3件。優先度順に並べる。
候補がない（データ不足・現状の戦略で十分）場合は「現状維持推奨」と明記。
"""


def run_strategy_planner(analyst_report: str) -> str:
    system = load_agent_prompt("strategy-dev") + STRATEGY_PLANNING_SUFFIX

    user_msg = f"""以下はアナリストが生成した本日の運用レポートです。
このデータ・見解をもとに、次に試すべき戦略の作戦を立案してください。

---
{analyst_report}
---

コードは不要です。「試す価値があるか」の判断材料だけを提示してください。"""

    return call_claude(system, [{"role": "user", "content": user_msg}])


# ── Discord 送信 ──────────────────────────────────────

def send_discord_block(webhook_url: str, title: str, body: str) -> None:
    """タイトル付きブロックを Discord に分割送信する。"""
    full = f"{title}\n\n{body}"
    chunks: list[str] = []
    buf = ""
    for line in full.splitlines(keepends=True):
        if len(buf) + len(line) > 1900:
            chunks.append(buf)
            buf = line
        else:
            buf += line
    if buf:
        chunks.append(buf)

    for i, chunk in enumerate(chunks):
        suffix = f"\n*(part {i+1}/{len(chunks)})*" if len(chunks) > 1 else ""
        payload = json.dumps({"content": chunk + suffix}).encode()
        req = urllib.request.Request(
            webhook_url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "FX-AI-Trader/1.0",
            },
        )
        try:
            urllib.request.urlopen(req, timeout=10)
        except Exception as e:
            print(f"  \u26a0\ufe0f  Discord\u9001\u4fe1\u5931\u6557 (part {i+1}): {e}", file=sys.stderr)


# ── KB保存 ────────────────────────────────────────────

def save_to_kb(date_str: str, analyst_report: str,
               strategy_report: str | None, session: str) -> None:
    """レポートをKBに自動保存（セッション別ファイル名）。"""
    kb_dir = ROOT / "knowledge-base" / "raw" / "trade-logs"
    kb_dir.mkdir(parents=True, exist_ok=True)
    path = kb_dir / f"{date_str}-{session}.md"

    config = SESSION_CONFIGS[session]
    content = f"# {config['label']}: {date_str}\n\n## Analyst Report\n{analyst_report}\n"
    if strategy_report:
        content += f"\n## Strategy Planning\n{strategy_report}\n"

    try:
        path.write_text(content, encoding="utf-8")
        print(f"\U0001f4dd KB\u4fdd\u5b58: {path.relative_to(ROOT)}")
    except Exception as e:
        print(f"  \u26a0\ufe0f  KB\u4fdd\u5b58\u5931\u6557: {e}", file=sys.stderr)


def update_analyst_memory(date_str: str, analyst_report: str,
                          session: str) -> None:
    """Analystレポートの要約をanalyst-memoryに追記（永続的フィードバックループ）。

    Renderのエフェメラルディスクでは _append_analyst_note() の結果が消失するため、
    GitHub Actions上で動くこの関数がanalyst-memoryの唯一の永続的更新経路となる。
    """
    memory_path = ROOT / "knowledge-base" / "raw" / "trade-logs" / "analyst-memory.md"
    if not memory_path.exists():
        return

    # レポートから要約を抽出
    summary_lines = []
    for line in analyst_report.splitlines():
        line_s = line.strip()
        if line_s and (line_s.startswith("- ") or line_s.startswith("* ")
                       or "WR" in line_s or "EV" in line_s or "PnL" in line_s
                       or "\u63a8\u5968" in line_s or "\u8b66\u544a" in line_s
                       or "\u6ce8\u610f" in line_s or "NO ACTION" in line_s):
            summary_lines.append(line_s)
        if len(summary_lines) >= 8:
            break

    if not summary_lines:
        summary_lines = [analyst_report[:300].replace("\n", " ")]

    config = SESSION_CONFIGS[session]
    entry = f"\n### {date_str} ({config['label']})\n" + "\n".join(summary_lines) + "\n"

    try:
        with open(memory_path, "r", encoding="utf-8") as f:
            content = f.read()

        # "## アナリストノート" セクションの末尾（## Related の直前）に挿入
        related_marker = "\n## Related"
        if related_marker in content:
            idx = content.index(related_marker)
            content = content[:idx] + entry + content[idx:]
        else:
            content += entry

        with open(memory_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"\U0001f4dd Analyst Memory\u66f4\u65b0: {date_str} ({session})")
    except Exception as e:
        print(f"  \u26a0\ufe0f  Analyst Memory\u66f4\u65b0\u5931\u6557: {e}", file=sys.stderr)


def save_regime_to_kb(date_str: str, regime_data: dict) -> None:
    """市場レジームスナップショットをKBに自動保存。"""
    if not regime_data or not regime_data.get("pairs"):
        return
    kb_dir = ROOT / "knowledge-base" / "raw" / "market-analysis"
    kb_dir.mkdir(parents=True, exist_ok=True)
    path = kb_dir / f"{date_str}-regime.md"

    lines = [f"# Market Regime: {date_str}\n"]
    lines.append(f"**Timestamp**: {regime_data.get('ts', 'N/A')}\n")
    lines.append("## Pair Regime Classification")
    lines.append("| Pair | Regime | ATR%ile(5d) | ATR%ile(20d) | SMA20 Slope | Range(5d) | Last Close |")
    lines.append("|------|--------|-------------|-------------|-------------|-----------|------------|")

    for pair, info in sorted(regime_data.get("pairs", {}).items()):
        if "error" in info:
            lines.append(f"| {pair} | ERROR | - | - | - | - | {info['error']} |")
            continue
        lines.append(
            f"| {pair} | **{info['regime']}** "
            f"| {info['atr_pctile_5d']:.0f}% "
            f"| {info['atr_pctile_20d']:.0f}% "
            f"| {info['sma20_slope']:+.4f} "
            f"| {info['range_5d']:.4f} "
            f"| {info['last_close']} |"
        )

    lines.append("")
    lines.append("## Related")
    lines.append("- [[edge-pipeline]]")
    lines.append("- [[changelog]]")
    lines.append("")

    try:
        path.write_text("\n".join(lines), encoding="utf-8")
        print(f"\U0001f4dd Regime KB\u4fdd\u5b58: {path.relative_to(ROOT)}")
    except Exception as e:
        print(f"  \u26a0\ufe0f  Regime KB\u4fdd\u5b58\u5931\u6557: {e}", file=sys.stderr)


# ── main ──────────────────────────────────────────────

def main() -> int:
    # セッション判定（CLI引数 or UTC時刻自動判定）
    cli_arg = sys.argv[1] if len(sys.argv) > 1 else None
    session = detect_session(cli_arg)
    config = SESSION_CONFIGS[session]

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    webhook = os.environ.get("DISCORD_WEBHOOK_URL")
    steps_total = 4 if config["run_strategy_planner"] else 3

    print(f"\U0001f4cb Session: {config['label']} ({session})")

    # Step 1: データ取得
    print(f"\U0001f50d [1/{steps_total}] \u672c\u756aAPI\u304b\u3089\u30c7\u30fc\u30bf\u53d6\u5f97\u4e2d...")
    data = {k: fetch_json(url) for k, url in PRODUCTION_APIS.items()}
    failed = [k for k, v in data.items() if not v]
    if failed:
        print(f"  \u26a0\ufe0f  \u53d6\u5f97\u5931\u6557: {', '.join(failed)}")

    # Step 1.5: KBパイプライン自己診断
    health_warnings = check_kb_pipeline_health()
    if health_warnings:
        print(f"\u26a0\ufe0f  KB Pipeline Issues ({len(health_warnings)}\u4ef6):")
        for w in health_warnings:
            print(f"    - {w}")
        send_error_notification(
            f"\u26a0\ufe0f **KB Pipeline Health** ({config['label']} {date_str})\n"
            + "\n".join(f"- {w}" for w in health_warnings)
        )

    # Step 2: アナリストレポート（セッション別）
    print(f"\U0001f4ca [2/{steps_total}] {config['label']} \u2014 \u30ec\u30dd\u30fc\u30c8\u751f\u6210\u4e2d...")
    try:
        analyst_report = run_analyst(data, session, health_warnings)
    except Exception as e:
        print(f"  \u274c Analyst \u30a8\u30e9\u30fc: {e}", file=sys.stderr)
        return 1

    # Step 3: 作戦立案（pre_tokyoのみ）
    strategy_report = None
    if config["run_strategy_planner"]:
        print(f"\U0001f9e0 [3/{steps_total}] Strategy \u2014 \u4f5c\u6226\u7acb\u6848\u4e2d...")
        try:
            strategy_report = run_strategy_planner(analyst_report)
        except Exception as e:
            print(f"  \u26a0\ufe0f  Strategy \u30a8\u30e9\u30fc\uff08\u30b9\u30ad\u30c3\u30d7\uff09: {e}", file=sys.stderr)
            strategy_report = "\u26a0\ufe0f \u4f5c\u6226\u7acb\u6848\u306e\u751f\u6210\u306b\u5931\u6557\u3057\u307e\u3057\u305f\u3002"

    # KB自動保存
    kb_saved = []
    save_to_kb(date_str, analyst_report, strategy_report, session)
    kb_saved.append(f"trade-logs/{date_str}-{session}.md")

    # レジームスナップショットKB保存（pre_tokyoのみ — 1日1回で十分）
    if session == "pre_tokyo":
        save_regime_to_kb(date_str, data.get("regime", {}))
        kb_saved.append(f"market-analysis/{date_str}-regime.md")

    # Analyst Memory更新
    update_analyst_memory(date_str, analyst_report, session)
    kb_saved.append("trade-logs/analyst-memory.md")

    # KB保存結果を #error-report に通知
    send_error_notification(
        f"\u2705 **KB Save** ({config['label']} {date_str})\n"
        + "\n".join(f"- {f}" for f in kb_saved)
    )

    # Discord送信 or 標準出力
    send_step = steps_total
    analyst_header = f"{config['emoji']} **\u3010{config['discord_tag']} {date_str}\u3011**"

    if not webhook:
        print("\n" + "=" * 60)
        print(analyst_header)
        print(analyst_report)
        if strategy_report:
            strategy_header = f"\U0001f9e0 **\u3010\u4f5c\u6226\u7acb\u6848 {date_str}\u3011** \u2014 GO/NO-GO \u306f\u3042\u306a\u305f\u304c\u5224\u65ad"
            print("\n" + "=" * 60)
            print(strategy_header)
            print(strategy_report)
        print("=" * 60)
        print("\n\u26a0\ufe0f  DISCORD_WEBHOOK_URL \u672a\u8a2d\u5b9a \u2014 \u6a19\u6e96\u51fa\u529b\u306b\u51fa\u529b\u3057\u307e\u3057\u305f")
        return 0

    print(f"\U0001f4e8 [{send_step}/{steps_total}] Discord \u306b\u9001\u4fe1\u4e2d...")
    send_discord_block(webhook, analyst_header, analyst_report)
    if strategy_report:
        strategy_header = f"\U0001f9e0 **\u3010\u4f5c\u6226\u7acb\u6848 {date_str}\u3011** \u2014 GO/NO-GO \u306f\u3042\u306a\u305f\u304c\u5224\u65ad"
        send_discord_block(webhook, strategy_header, strategy_report)
    print("\u2705 \u5b8c\u4e86")
    return 0


if __name__ == "__main__":
    sys.exit(main())
