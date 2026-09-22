"""Forward daily collector for the MoF communication-modality corpus.

Run by .github/workflows/mof-statements-daily.yml (daily, JST 06:30); can also
be run locally. Collection only — same discipline boundary as
tools/mof_statements_ingest.py (no price data, no joint measurement).

Steps are executed with per-source isolation: every source is attempted, and
only *hard* failures raise (at the end, after all sources ran). GDELT is a
*soft* source — it re-fetches its full range every run, so a single failure
carries no information and must not abort the primary corpus collection.

Steps:
  1. interventions  — refetch the official history CSV + monthly aggregate
     pages (self-healing full rewrite; picks up new quarterly disclosures).
  2. conferences    — fetch current + previous month pages, append any new
     my{YYYYMMDD}.html transcripts to conferences/{YYYYMM}.jsonl.
  3. score          — regenerate lexicon_scores.csv over the whole corpus.
  4. rss            — MoF news.rss, FX-related items appended to rss_items.csv
     (dedup by link).
  5. gdelt          — refetch timelinevol series (full range, overwrite).
"""
import csv
import datetime as dt
import json
import os
import time

try:
    from tools import mof_statements_ingest as ing
except ImportError:  # executed as a script from inside tools/
    import mof_statements_ingest as ing


def run_conferences_recent() -> dict:
    """Fetch only the current and previous month pages (forward increment)."""
    today = dt.date.today()
    prev = (today.replace(day=1) - dt.timedelta(days=1))
    wanted = {f"{prev:%Y%m}", f"{today:%Y%m}"}
    n_new = 0
    for month in sorted(wanted):
        time.sleep(ing.SLEEP_MOF)
        body = ing.fetch_optional(ing.CONF_PAGE.format(name=f"{month}.html"))
        if body is None:
            # MoF sometimes never creates the month index (2023-10..12,
            # 2026-01..04) while transcripts exist as unlinked orphans —
            # fall back to day-probing so forward collection cannot go blind
            n_new += ing.probe_month_days(month)
            continue
        names = ing.extract_conf_links(ing.decode_mof(body))
        have = ing._existing_conf_names(month)
        for name in [n for n in names if n not in have]:
            time.sleep(ing.SLEEP_MOF)
            url = ing.CONF_PAGE.format(name=name)
            html = ing.decode_mof(ing.fetch(url))
            ing._store_conference(month, name, html, source="online", source_url=url)
            n_new += 1
    print(f"[daily-conf] months={sorted(wanted)} new={n_new}")
    return {"months": sorted(wanted), "new": n_new}


def run_rss() -> dict:
    """Append new FX-related MoF news items to rss_items.csv."""
    xml_text = ing.decode_mof(ing.fetch(ing.NEWS_RSS))
    fx_items = ing.filter_fx_items(ing.parse_rss_items(xml_text))
    path = os.path.join(ing.OUT_DIR, "rss_items.csv")
    seen = set()
    if os.path.exists(path):
        with open(path, newline="") as f:
            seen = {r["link"] for r in csv.DictReader(f)}
    new_items = [it for it in fx_items if it["link"] not in seen]
    if new_items or not os.path.exists(path):
        write_header = not os.path.exists(path)
        with open(path, "a", newline="") as f:
            w = csv.writer(f)
            if write_header:
                w.writerow(["first_seen_utc", "pub_date", "title", "link"])
            now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            for it in new_items:
                w.writerow([now, it["pub_date"], it["title"], it["link"]])
    print(f"[daily-rss] fx_items={len(fx_items)} new={len(new_items)}")
    return {"fx_items": len(fx_items), "new": len(new_items)}


# ソース分類 (2026-09-17, rule:R3)。
#   hard = 失敗を終端で raise する (family A forward corpus の一次供給)
#   soft = 警告のみ。全範囲を毎回再取得する派生系列で、次回 run が完全に自己修復する
#          ため 1 日の失敗に情報価値が無い。GDELT は runner IP に対する 429 が
#          慢性的 (2026-09-03..16 で 8/20 run) で、hard 扱いだと本体を道連れにする。
#
# ⚠️ 2026-09-19 (rule:R3、PR #261 Codex P2 の消化): **ソース名だけで soft を
# 決めてはいけない**。同じ `run_gdelt` から出る例外には
#   (a) 429 / timeout        → 翌 run で自己修復する = soft
#   (b) `unexpected GDELT response` → 上流の恒久変更の署名 = hard
#   (c) 書込み失敗 (OSError) → 環境障害 = hard
# があり、旧実装は (b)(c) も soft に落として `main()` を exit 0 にしていたため
# workflow の `Notify failure` が走らず、CSV が無期限に stale で残りうる。
# 判定は `ing.is_transient_fetch_error()` に集約 (**列挙に無い形状は hard** =
# fail-closed。上流がエラー表現を変えたら過剰 alert 側に倒れる)。
_SOFT_SOURCES = {"gdelt"}


def _is_soft(name: str, exc: BaseException) -> bool:
    """soft = 「soft 候補ソース」かつ「自己修復が見込める例外形状」の両方。"""
    return name in _SOFT_SOURCES and ing.is_transient_fetch_error(exc)

_STEPS = (
    ("interventions", lambda: ing.run_interventions(check=False)),
    ("conferences", run_conferences_recent),
    ("score", ing.run_score),
    ("rss", run_rss),
    ("gdelt", ing.run_gdelt),
)


def main():
    """各ソースを隔離実行する (per-source isolation)。

    2026-09-17 以前は dict literal で 5 ソースを直列評価していたため、最後段の
    GDELT が 429 で raise すると **先に成功していた 4 ソースの成果ごと** プロセスが
    落ち、workflow の commit step (当時 `if: success()` 相当) が走らず runner の
    ephemeral disk ごと破棄されていた。実害は観測済み: 2026-09-16 の run 35163419350 は
    `[daily-conf] new=1` (my20260915.html) / `[daily-rss] new=1` / `[score] 512 conferences`
    まで到達してから 429 で全破棄し、repo 側は 511 conferences のまま取り残された。

    本関数は全ソースを試行してから終端で hard 失敗のみ raise する。部分成果は
    workflow 側の `if: !cancelled()` commit step が永続化する。
    """
    summary = {}
    hard_failed, soft_failed = [], []
    for name, fn in _STEPS:
        try:
            summary[name] = fn()
        except Exception as exc:  # noqa: BLE001 — 隔離が目的
            soft = _is_soft(name, exc)
            (soft_failed if soft else hard_failed).append(name)
            summary[name] = {"error": f"{type(exc).__name__}: {exc}",
                             "classified": "soft" if soft else "hard"}
            print(f"[daily-{name}] FAILED ({'soft' if soft else 'hard'}): {exc}")

    print("[daily-summary]", json.dumps(summary, ensure_ascii=False))
    if soft_failed:
        print(f"⚠️ soft sources failed (自己修復・アラート対象外): {soft_failed}")
    if hard_failed:
        raise RuntimeError(
            "hard sources failed: " + ", ".join(hard_failed)
            + " — 部分成果は commit 済み (if: !cancelled())。要調査"
        )
    return summary


if __name__ == "__main__":
    main()
