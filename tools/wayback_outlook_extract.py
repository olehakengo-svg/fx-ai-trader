#!/usr/bin/env python3
"""
wayback_outlook_extract.py — Wayback Machine の Myfxbook Community Outlook
歴史パネル抽出 (E1 positioning pre-reg の事前登録校正サンプル)

目的:
  web.archive.org にアーカイブされた https://www.myfxbook.com/community/outlook
  スナップショットから date × symbol × long%/short% の歴史パネルを構築する。
  このパネルは **校正・記述統計専用** であり、確証検定 (confirmatory test) には
  使用禁止 (E1 pre-reg の設計入力。lookahead/survivorship の統制が無いため)。

レイアウト時代差 (実測):
  - Era A (2011〜2019 頃): 各 symbol 行の <input value="..."> tooltip 内に
      <td rowspan='3'>SYMBOL</td></tr><tr><td>Short</td><td>NN%</td><td>X Lots</td><td>P</td>...
  - Era B (2020 頃〜現在): <div id="outlookSymbolPopoverN"> 内に
      <td rowspan="2">SYMBOL</td><td>Short</td><td>NN%</td><td>X lots</td><td>P</td>...
  両者とも「symbol セル → Short 行 → Long 行」が連続ブロックなので、
  \\s* のみで連結した単一正規表現で貪欲マッチ事故 (別 symbol の % を拾う) を
  構造的に排除して抽出できる (BLOCK_RE)。

politeness:
  - 1 リクエスト毎に 2 秒 sleep (デフォルト、--sleep で変更可)
  - User-Agent 明示
  - リトライは指数バックオフで最大 3 回。429/5xx は最終的にスキップして記録
  - 連続スキップが閾値を超えたら (Wayback 側ブロックとみなし) そこで打ち切り

CLI:
  python3 tools/wayback_outlook_extract.py \\
      --out knowledge-base/raw/bt-results/e1-wayback-outlook-panel-2026-07-16.csv \\
      --cache-dir /path/to/cache [--cdx-file cdx.json] [--limit 5]
  python3 tools/wayback_outlook_extract.py --summary-only \\
      --out ...csv --summary-md ...md   # CSV から要約 md のみ再生成

モジュールトップで副作用禁止 (network/argparse/os.environ は全て main() 内)。
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, pstdev

# ── 定数 (純粋データのみ、副作用なし) ──────────────────────────────
USER_AGENT = "fx-ai-trader-research/1.0 (E1 positioning calibration; contact: goto@tctangle.co.jp)"
CDX_URL = (
    "http://web.archive.org/cdx/search/cdx"
    "?url=myfxbook.com/community/outlook&output=json"
    "&from=2011&to=2026&filter=statuscode:200"
)
SNAPSHOT_URL_TMPL = "http://web.archive.org/web/{ts}/https://www.myfxbook.com/community/outlook"

MAX_RETRIES = 3            # 指数バックオフ 3 回まで
BACKOFF_BASE_SEC = 4.0     # 4s → 8s → 16s
DEFAULT_SLEEP_SEC = 2.0    # politeness sleep (リクエスト毎)
CONSECUTIVE_FAIL_ABORT = 8 # 連続失敗でブロックとみなし打ち切り

# E1 pre-reg 対象 13 ペア (OANDA 表記から '_' を除いた myfxbook 表記)
TARGET_PAIRS = [
    "USDJPY", "EURUSD", "GBPUSD", "EURJPY", "GBPJPY", "AUDJPY", "AUDUSD",
    "NZDUSD", "USDCAD", "USDCHF", "NZDJPY", "EURAUD", "EURGBP",
]

# symbol セル → Short 行 → Long 行 (順序は Short/Long どちらが先でも可) の
# 連続ブロックを 1 マッチで取る。区切りは \s* と固定タグのみ (貪欲スパン無し)
# なので、隣接する別 symbol のセルを跨いでマッチすることは構造上できない。
# locale 対応: Wayback には localized capture が混ざる (実測: Slovak "Loty",
# Polish "Krótka"/"Pozycja długa" 等)。action/volume/positions セルは [^<] で
# 緩く取り、action は ACTION_MAP で分類、数値化は _parse_number で行う。
# 未知の action 語のブロックは不採用 (unknown_sink に記録して後で語彙を拡張)。
BLOCK_RE = re.compile(
    r"<td rowspan=['\"][23]['\"]>\s*([A-Za-z0-9!./_-]+)\s*</td>\s*(?:</tr>\s*<tr>\s*)?"
    r"<td>\s*([^<>]{1,40}?)\s*</td>\s*"
    r"<td>\s*(\d+(?:[.,]\d+)?)\s*%\s*</td>\s*"
    r"<td>\s*([^<]*?)\s*</td>\s*"
    r"<td>\s*([\d.,\s\u00a0]+?)\s*</td>\s*"
    r"</tr>\s*<tr>\s*"
    r"<td>\s*([^<>]{1,40}?)\s*</td>\s*"
    r"<td>\s*(\d+(?:[.,]\d+)?)\s*%\s*</td>\s*"
    r"<td>\s*([^<]*?)\s*</td>\s*"
    r"<td>\s*([\d.,\s\u00a0]+?)\s*</td>",
    re.S,
)

# localized action 語 → short/long 分類 (Wayback 実測分のみ。推測での追加はしない)
ACTION_MAP = {
    "short": "short",
    "long": "long",
    # Polish (wb_20110423132414 実測)
    "kr\u00f3tka": "short",
    "pozycja d\u0142uga": "long",
    # Russian (wb_20110625100603 実測、bar幅で行順検証済み)
    "короткая сделка": "short",
    "длинная сделка": "long",
    # Chinese (wb_20110902004127 実測)
    "做空": "short",
    "看涨": "long",
    # Japanese (wb_20160719142805 実測)
    "ショート": "short",
    "買い": "long",
    # Swedish (wb_20160720190300 実測)
    "kort": "short",
    "long(köp)": "long",
    # Spanish (wb_20161016110212 実測)
    "venta corta": "short",
    "larga": "long",
    # Portuguese (wb_20220427235133 実測)
    "curta": "short",
    "comprida": "long",
}

_NUM_TOKEN_RE = re.compile(r"\d[\d.,\s\u00a0]*")

# Wayback リダイレクト後 URL から実タイムスタンプを回収する
FINAL_TS_RE = re.compile(r"/web/(\d{14})")

CSV_COLUMNS = [
    "snapshot_ts_utc", "symbol", "long_pct", "short_pct",
    "total_positions", "long_positions", "short_positions",
    "long_volume_lots", "short_volume_lots",
]


# ── 純粋関数 (オフラインテスト対象) ─────────────────────────────────
def _parse_number(cell: str) -> float | None:
    """セル文言から数値を lenient に取り出す (locale 差異対応)。

    '3866.91 lots' → 3866.91 / '446.94 Loty' → 446.94 / '1,466' → 1466.0
    '56,5' (欧州小数) → 56.5 / 数値が無ければ None。
    """
    m = _NUM_TOKEN_RE.search(cell)
    if not m:
        return None
    tok = m.group(0).replace(" ", "").replace("\u00a0", "").rstrip(".,")
    if "," in tok and "." in tok:
        tok = tok.replace(",", "")          # 1,234.56 → 1234.56
    elif "," in tok:
        parts = tok.split(",")
        if len(parts) == 2 and len(parts[1]) in (1, 2):
            tok = tok.replace(",", ".")     # 56,5 → 56.5 (欧州小数)
        else:
            tok = tok.replace(",", "")      # 1,466 → 1466 (千区切り)
    try:
        return float(tok)
    except ValueError:
        return None


def parse_outlook_html(html: str, unknown_sink: set | None = None) -> list[dict]:
    """outlook ページ HTML から symbol 毎の long/short 統計を抽出する。

    返り値: [{symbol, long_pct, short_pct, long_positions, short_positions,
              long_volume_lots, short_volume_lots, total_positions}, ...]
    - Short/Long の順序に依存しない (どちらが先の時代でも可)
    - localized action 語 (Polish 等) は ACTION_MAP で分類。未知語は不採用で
      unknown_sink (渡されていれば) に記録 → 後で語彙を拡張して再パース可能
    - 両サイド 0% かつ positions 0 の「未取引 symbol」行は情報ゼロなので落とす
    - 同一 symbol が複数回マッチした場合は最初の 1 件のみ採用
    """
    rows: list[dict] = []
    seen: set[str] = set()
    for m in BLOCK_RE.finditer(html):
        symbol = m.group(1).upper()
        if symbol in seen:
            continue
        sides: dict[str, tuple[float, float | None, int]] = {}
        for act, pct, vol, pos in (m.group(2, 3, 4, 5), m.group(6, 7, 8, 9)):
            side = ACTION_MAP.get(act.strip().lower())
            if side is None:
                if unknown_sink is not None:
                    unknown_sink.add(act.strip())
                continue  # 未知の action 語 → 不採用 (語彙拡張待ち)
            pos_num = _parse_number(pos)
            if pos_num is None:
                continue  # positions が数値でない断片は不採用
            sides[side] = (
                float(pct.replace(",", ".")),
                _parse_number(vol),
                int(pos_num),
            )
        if "short" not in sides or "long" not in sides:
            continue  # 片側欠け (未知語/壊れた断片) → skip
        long_pct, long_vol, long_pos = sides["long"]
        short_pct, short_vol, short_pos = sides["short"]
        if long_pct == 0.0 and short_pct == 0.0 and long_pos + short_pos == 0:
            continue  # 未取引 symbol (EURCZK 等) は情報ゼロ
        seen.add(symbol)
        rows.append({
            "symbol": symbol,
            "long_pct": long_pct,
            "short_pct": short_pct,
            "long_positions": long_pos,
            "short_positions": short_pos,
            "long_volume_lots": long_vol,
            "short_volume_lots": short_vol,
            "total_positions": long_pos + short_pos,
        })
    return rows


def dedupe_daily_first(cdx_rows: list[list[str]]) -> list[list[str]]:
    """CDX 行 (header 除去済み) を 1 日 1 件 (その日の最初) に間引く。"""
    seen: dict[str, list[str]] = {}
    for row in cdx_rows:
        day = row[1][:8]
        if day not in seen:
            seen[day] = row
    return [seen[d] for d in sorted(seen)]


def ts14_to_iso_utc(ts14: str) -> str:
    """Wayback の 14 桁タイムスタンプ (UTC) を ISO8601 に変換する。"""
    dt = datetime.strptime(ts14, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def sign(x: float) -> int:
    return (x > 0) - (x < 0)


def build_summary_md(panel_rows: list[dict], skips: list[dict],
                     n_attempted: int, aborted_note: str = "") -> str:
    """パネルから要約統計 md を生成する (記述統計のみ)。"""
    by_year: dict[str, set[str]] = {}
    symbols: set[str] = set()
    snapshots: set[str] = set()
    for r in panel_rows:
        ts = r["snapshot_ts_utc"]
        by_year.setdefault(ts[:4], set()).add(ts)
        symbols.add(r["symbol"])
        snapshots.add(ts)

    def pctile(sorted_vals: list[float], q: float) -> float:
        # 線形補間分位点 (numpy 非依存)
        if not sorted_vals:
            return float("nan")
        idx = q * (len(sorted_vals) - 1)
        lo, hi = int(idx), min(int(idx) + 1, len(sorted_vals) - 1)
        frac = idx - lo
        return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac

    lines = [
        "# E1 Wayback Myfxbook Community Outlook 歴史パネル — 要約統計 (2026-07-16)",
        "",
        "> **注意 (必読)**: このパネルは **校正・記述統計専用。確証検定への使用禁止**",
        "> (E1 pre-reg の設計入力)。Wayback スナップショットは採取タイミングが不規則で",
        "> survivorship/選択バイアスの統制が無く、live 環境の 5 分毎スナップショットとは",
        "> 母集団が異なる。skew 閾値・持続性の事前分布の見積もりにのみ使う。",
        "",
        "- 生成: `tools/wayback_outlook_extract.py` (rule:R3, 記述統計のみ)",
        "- ソース: `http://web.archive.org/cdx/search/cdx?url=myfxbook.com/community/outlook` (2011〜2026, statuscode:200, 1日1件に間引き)",
        f"- パネル: `e1-wayback-outlook-panel-2026-07-16.csv` ({len(panel_rows)} 行)",
        "",
        "## カバレッジ",
        "",
        f"- スナップショット取得試行: {n_attempted} / 成功 (パース済): {len(snapshots)} / skip: {len(skips)}",
        f"- ユニーク symbol 数: {len(symbols)}",
        "",
        "| 年 | スナップショット数 |",
        "|---|---|",
    ]
    for y in sorted(by_year):
        lines.append(f"| {y} | {len(by_year[y])} |")

    if aborted_note:
        lines += ["", f"**打ち切り記録**: {aborted_note}"]

    if skips:
        reason_counts: dict[str, int] = {}
        for s in skips:
            key = s["reason"].split(":")[0]
            reason_counts[key] = reason_counts.get(key, 0) + 1
        lines += ["", "### skip 内訳", ""]
        for k, v in sorted(reason_counts.items(), key=lambda kv: -kv[1]):
            lines.append(f"- {k}: {v}")

    lines += [
        "",
        "## 対象 13 ペアの skew = long% − short% 分布",
        "",
        "| pair | N | min | p10 | p25 | median | p75 | p90 | max | mean | SD |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    per_pair_skews: dict[str, list[tuple[str, float]]] = {}
    for r in panel_rows:
        if r["symbol"] in TARGET_PAIRS:
            per_pair_skews.setdefault(r["symbol"], []).append(
                (r["snapshot_ts_utc"], r["long_pct"] - r["short_pct"]))
    all_skews: list[float] = []
    for pair in TARGET_PAIRS:
        obs = sorted(per_pair_skews.get(pair, []))
        vals = sorted(v for _, v in obs)
        all_skews.extend(vals)
        if not vals:
            lines.append(f"| {pair} | 0 | - | - | - | - | - | - | - | - | - |")
            continue
        lines.append(
            f"| {pair} | {len(vals)} | {vals[0]:+.0f} | {pctile(vals, .10):+.1f} | "
            f"{pctile(vals, .25):+.1f} | {pctile(vals, .50):+.1f} | {pctile(vals, .75):+.1f} | "
            f"{pctile(vals, .90):+.1f} | {vals[-1]:+.0f} | {mean(vals):+.1f} | {pstdev(vals):.1f} |")
    if all_skews:
        vals = sorted(all_skews)
        lines.append(
            f"| **ALL(13)** | {len(vals)} | {vals[0]:+.0f} | {pctile(vals, .10):+.1f} | "
            f"{pctile(vals, .25):+.1f} | {pctile(vals, .50):+.1f} | {pctile(vals, .75):+.1f} | "
            f"{pctile(vals, .90):+.1f} | {vals[-1]:+.0f} | {mean(vals):+.1f} | {pstdev(vals):.1f} |")

    lines += [
        "",
        "## skew 符号の持続性 (連続スナップショット間の符号一致率)",
        "",
        "隣接スナップショット (時系列順、間隔は不規則: 数日〜数ヶ月) で",
        "sign(skew) が一致した割合。ランダムなら ~0.5 (ゼロ skew は不一致扱い)。",
        "**間隔が不規則なため厳密な自己相関ではない — 目安のみ。**",
        "",
        "| pair | 遷移数 | 符号一致率 | 一致率(間隔≤7日のみ) | 遷移数(≤7日) |",
        "|---|---|---|---|---|",
    ]
    for pair in TARGET_PAIRS:
        obs = sorted(per_pair_skews.get(pair, []))
        if len(obs) < 2:
            lines.append(f"| {pair} | 0 | - | - | 0 |")
            continue
        match_all = total_all = 0
        match_7d = total_7d = 0
        for (ts_a, sk_a), (ts_b, sk_b) in zip(obs, obs[1:]):
            same = sign(sk_a) == sign(sk_b) and sign(sk_a) != 0
            total_all += 1
            match_all += same
            gap_days = (
                datetime.strptime(ts_b[:10], "%Y-%m-%d")
                - datetime.strptime(ts_a[:10], "%Y-%m-%d")
            ).days
            if gap_days <= 7:
                total_7d += 1
                match_7d += same
        rate_all = f"{match_all / total_all:.2f}" if total_all else "-"
        rate_7d = f"{match_7d / total_7d:.2f}" if total_7d else "-"
        lines.append(f"| {pair} | {total_all} | {rate_all} | {rate_7d} | {total_7d} |")

    lines += [
        "",
        "## 用途と禁止事項",
        "",
        "- **用途**: E1 positioning pre-reg の設計入力 (skew 閾値グリッドの校正、",
        "  持続性の事前分布、コントラリアン仮説の分布レンジ確認) — 記述統計のみ。",
        "- **禁止**: このパネルでの仮説の確証検定・エッジ判定・tier 判断。",
        "  確証検定は live 蓄積した 5 分毎スナップショット (positioning_ingest) の",
        "  out-of-sample データでのみ行う (Rule 1)。",
        "",
    ]
    return "\n".join(lines)


# ── ネットワーク層 (main() からのみ呼ばれる) ───────────────────────
def _fetch_with_backoff(url: str, sleep_sec: float) -> tuple[bytes | None, str, str]:
    """URL を取得する。返り値: (body|None, final_url, fail_reason)。

    politeness: 呼び出し毎に必ず sleep_sec 待ってからリクエスト。
    429/5xx は指数バックオフで最大 MAX_RETRIES 回。最終失敗は (None, "", reason)。
    """
    # scheme を http(s) に固定 (file:// 等の混入をコードレベルで遮断)。
    # url は定数テンプレート + CDX timestamp (数字のみ) からしか作られない。
    if not url.startswith(("http://", "https://")):
        return None, "", f"bad_scheme:{url[:30]}"
    reason = ""
    for attempt in range(MAX_RETRIES):
        time.sleep(sleep_sec)
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:  # nosemgrep: dynamic-urllib-use-detected
                return resp.read(), resp.geturl(), ""
        except urllib.error.HTTPError as e:
            reason = f"http_{e.code}"
            if e.code in (429, 500, 502, 503, 504) and attempt < MAX_RETRIES - 1:
                backoff = BACKOFF_BASE_SEC * (2 ** attempt)
                print(f"    retry {attempt + 1}/{MAX_RETRIES} after {backoff:.0f}s ({reason})",
                      file=sys.stderr)
                time.sleep(backoff)
                continue
            return None, "", reason
        except Exception as e:  # URLError / timeout / IncompleteRead 等
            reason = f"net_error:{type(e).__name__}"
            if attempt < MAX_RETRIES - 1:
                backoff = BACKOFF_BASE_SEC * (2 ** attempt)
                print(f"    retry {attempt + 1}/{MAX_RETRIES} after {backoff:.0f}s ({reason})",
                      file=sys.stderr)
                time.sleep(backoff)
                continue
            return None, "", reason
    return None, "", reason or "unknown"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument("--out", required=True, help="出力 CSV パス")
    parser.add_argument("--summary-md", default="", help="要約統計 md の出力パス (省略時は書かない)")
    parser.add_argument("--cache-dir", default="", help="HTML キャッシュディレクトリ (再実行時に再取得しない)")
    parser.add_argument("--cdx-file", default="", help="取得済み CDX JSON を使う (省略時は CDX API を叩く)")
    parser.add_argument("--sleep", type=float, default=DEFAULT_SLEEP_SEC, help="リクエスト毎の politeness sleep 秒")
    parser.add_argument("--limit", type=int, default=0, help="先頭 N スナップショットのみ (テスト用)")
    parser.add_argument("--summary-only", action="store_true",
                        help="ダウンロードせず既存 CSV から要約 md のみ再生成")
    args = parser.parse_args(argv)

    out_csv = Path(args.out)
    skip_log_path = out_csv.with_suffix(".skips.json")

    # ── summary-only モード: 既存 CSV → md 再生成のみ ──
    if args.summary_only:
        if not args.summary_md:
            print("--summary-only には --summary-md が必要", file=sys.stderr)
            return 2
        panel_rows = []
        with out_csv.open() as f:
            for row in csv.DictReader(f):
                row["long_pct"] = float(row["long_pct"])
                row["short_pct"] = float(row["short_pct"])
                panel_rows.append(row)
        skips = json.loads(skip_log_path.read_text()) if skip_log_path.exists() else []
        n_attempted = len({r["snapshot_ts_utc"] for r in panel_rows}) + len(skips)
        Path(args.summary_md).write_text(
            build_summary_md(panel_rows, skips, n_attempted), encoding="utf-8")
        print(f"summary md written: {args.summary_md}")
        return 0

    # ── CDX 取得 ──
    if args.cdx_file:
        cdx = json.loads(Path(args.cdx_file).read_text())
    else:
        body, _, reason = _fetch_with_backoff(CDX_URL, args.sleep)
        if body is None:
            print(f"CDX 取得失敗: {reason}", file=sys.stderr)
            return 1
        cdx = json.loads(body)
    cdx_rows = cdx[1:]  # 先頭は header
    selected = dedupe_daily_first(cdx_rows)
    if args.limit:
        selected = selected[: args.limit]
    print(f"CDX: {len(cdx_rows)} snapshots → daily-first {len(selected)} 件", file=sys.stderr)

    cache_dir = Path(args.cache_dir) if args.cache_dir else None
    if cache_dir:
        cache_dir.mkdir(parents=True, exist_ok=True)

    panel_rows: list[dict] = []
    skips: list[dict] = []
    seen_final_ts: set[str] = set()
    consecutive_fails = 0
    aborted_note = ""

    for i, row in enumerate(selected):
        ts = row[1]
        if not (ts.isdigit() and len(ts) == 14):
            skips.append({"ts": ts, "reason": "bad_cdx_timestamp"})
            continue
        cache_file = cache_dir / f"wb_{ts}.html" if cache_dir else None
        html: str | None = None
        final_ts = ts

        if cache_file is not None and cache_file.exists():
            html = cache_file.read_text(encoding="utf-8", errors="replace")
            # キャッシュ命名は requested ts。リダイレクト差は初回取得時に解決済み。
        else:
            url = SNAPSHOT_URL_TMPL.format(ts=ts)
            body, final_url, reason = _fetch_with_backoff(url, args.sleep)
            if body is None:
                skips.append({"ts": ts, "reason": reason})
                consecutive_fails += 1
                print(f"[{i + 1}/{len(selected)}] {ts} SKIP ({reason})", file=sys.stderr)
                if consecutive_fails >= CONSECUTIVE_FAIL_ABORT:
                    aborted_note = (
                        f"{ts} 時点で連続 {consecutive_fails} 件失敗 (直近 reason={reason}) — "
                        "Wayback 側ブロックとみなし打ち切り。パネルはその時点までの部分版。")
                    print(f"ABORT: {aborted_note}", file=sys.stderr)
                    break
                continue
            html = body.decode("utf-8", errors="replace")
            m = FINAL_TS_RE.search(final_url)
            if m:
                final_ts = m.group(1)
            if cache_file is not None:
                cache_file.write_text(html, encoding="utf-8")
        consecutive_fails = 0

        if final_ts in seen_final_ts:
            skips.append({"ts": ts, "reason": f"redirect_dup:{final_ts}"})
            continue

        unknown_actions: set = set()
        rows = parse_outlook_html(html, unknown_sink=unknown_actions)
        if not rows:
            detail = f":unknown_actions={sorted(unknown_actions)}" if unknown_actions else ""
            skips.append({"ts": ts, "reason": f"parse_empty{detail}"})
            print(f"[{i + 1}/{len(selected)}] {ts} SKIP (parse_empty{detail})", file=sys.stderr)
            continue
        seen_final_ts.add(final_ts)
        iso = ts14_to_iso_utc(final_ts)
        for r in rows:
            panel_rows.append({"snapshot_ts_utc": iso, **r})
        if (i + 1) % 25 == 0 or i == len(selected) - 1:
            print(f"[{i + 1}/{len(selected)}] {ts} ok — panel rows {len(panel_rows)}",
                  file=sys.stderr)

    # ── 出力 ──
    panel_rows.sort(key=lambda r: (r["snapshot_ts_utc"], r["symbol"]))
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        w.writeheader()
        w.writerows(panel_rows)
    skip_log_path.write_text(json.dumps(skips, indent=1), encoding="utf-8")
    print(f"panel: {len(panel_rows)} rows → {out_csv}", file=sys.stderr)
    print(f"skips: {len(skips)} → {skip_log_path}", file=sys.stderr)

    if args.summary_md:
        Path(args.summary_md).write_text(
            build_summary_md(panel_rows, skips, len(selected), aborted_note),
            encoding="utf-8")
        print(f"summary md: {args.summary_md}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
