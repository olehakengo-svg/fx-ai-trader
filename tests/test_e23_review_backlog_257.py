"""PR #257 Codex review backlog (7 件) の消化 pin — 2026-10-01, rule:R3.

各テストは「修正前のコードなら落ちる既知 NG 入力」を持つ (counterfactual 確認済み)。
いずれも network 不要・価格ファイル不要。OOS 窓の outcome は一切計算しない。

| review id  | 指摘                                          | pin |
|------------|-----------------------------------------------|-----|
| 4011713818 | Fed discovery が FOMC statement 以外を混入     | test_fed_* |
| 4011713820 | BoJ 印字日一致を公開時刻の検証と名乗る         | test_boj_* |
| 4011713826 | --refetch が discovery キャッシュを迂回しない  | test_refetch_* |
| 4011713829 | OOS_END 越えレコードを保存・manifest          | test_window_* |
| 4011810503 | Gate A median が全期間 (OOS 接触)             | test_gate_a_* |
| 4011810505 | pass-0 生存 CB を enumerate 前に強制しない     | test_evaluate_* |
| 4011810507 | 凍結辞書 sha を harness 実行時に assert しない | test_lexicon_* |
| PR #309 2 巡目 | census を価格前に / Gate A 候補ペア / DATA-BLOCKED 表示 | 末尾 3 本 |
"""
import json
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import e23_corpus_census as census_mod  # noqa: E402
import e23_corpus_fetch as fetch_mod  # noqa: E402
import e23_pass1_events as pass1_mod  # noqa: E402

BODY = "The Committee seeks to foster maximum employment and price stability. " * 8


def _fed_html(title: str, day: str = "July 30, 2014") -> str:
    return (f"<html><body><div id='article'><p>{day}</p><h3>{title}</h3>"
            f"<p>For release at 2:00 p.m. EDT</p><p>{BODY}</p></div></body></html>")


@pytest.fixture
def tmp_corpus(tmp_path, monkeypatch):
    monkeypatch.setattr(fetch_mod, "CORPUS_DIR", tmp_path / "cb_statements")
    return tmp_path / "cb_statements"


def _write(corpus: Path, rec: dict) -> None:
    path = corpus / rec["cb"] / f"{rec['date']}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rec), encoding="utf-8")


def _rec(cb: str, d: str, text: str = "x", **extra) -> dict:
    return {"cb": cb, "date": d, "text": text, "n_chars": len(text), "url": f"u/{cb}/{d}",
            "text_sha256": "0" * 64, **extra}


# ─────────────────────────── 1. Fed 文書種 (P1 4011713818) ───────────────────


def test_fed_title_identifies_fomc_statement_only():
    stmt = fetch_mod.extract_container(
        _fed_html("Federal Reserve issues FOMC statement"), fetch_mod.FED_SELECTORS)
    note = fetch_mod.extract_container(
        _fed_html("Statement Regarding Monetary Policy Implementation"),
        fetch_mod.FED_SELECTORS)
    assert fetch_mod.is_fomc_statement(stmt)
    assert not fetch_mod.is_fomc_statement(note)


def test_fed_fetch_drops_non_statement(monkeypatch, tmp_corpus):
    monkeypatch.setattr(fetch_mod, "SLEEP_SEC", 0)
    monkeypatch.setattr(fetch_mod, "discover_fed", lambda y: [
        (date(2019, 9, 18), "stmt"), (date(2019, 10, 11), "note")])
    pages = {"stmt": _fed_html("Federal Reserve issues FOMC statement"),
             "note": _fed_html("Statement Regarding Monetary Policy Implementation")}
    monkeypatch.setattr(fetch_mod, "_fetch", lambda url, **k: pages[url])
    recs = fetch_mod.fetch_fed(2019)
    assert [r["date"] for r in recs] == ["2019-09-18"]


def test_fed_loader_excludes_non_statement_without_deleting(tmp_corpus):
    stmt = fetch_mod.extract_container(
        _fed_html("Federal Reserve issues FOMC statement"), fetch_mod.FED_SELECTORS)
    note = fetch_mod.extract_container(
        _fed_html("Federal Reserve announces establishment of a temporary FIMA Repo "
                  "Facility"), fetch_mod.FED_SELECTORS)
    _write(tmp_corpus, _rec("fed", "2020-03-23", stmt))
    _write(tmp_corpus, _rec("fed", "2020-03-31", note))
    assert [r["date"] for r in fetch_mod.load_corpus()] == ["2020-03-23"]
    assert (tmp_corpus / "fed" / "2020-03-31.json").exists()   # 資産は残す
    ex = fetch_mod.corpus_exclusions()
    assert ex == [{"cb": "fed", "date": "2020-03-31", "url": "u/fed/2020-03-31",
                   "reason": "fed_not_fomc_statement"}]


def test_fed_committed_corpus_known_contaminants_excluded():
    """既知 NG 入力 = コミット済みコーパスの非 statement 4 件 (review が名指しした 3 件 + 1)."""
    dates = {r["date"] for r in fetch_mod.load_corpus() if r["cb"] == "fed"}
    for bad in ("2019-10-11", "2020-03-31", "2020-08-27", "2025-08-22"):
        assert bad not in dates, f"fed/{bad} は FOMC statement ではない"
    # 緊急会合の statement (2020-03 の 3 本) は FOMC statement なので残る
    assert {"2020-03-03", "2020-03-15", "2020-03-23"} <= dates


# ─────────────────────────── 2. BoJ V3 (P1 4011713820) ───────────────────────


def _cov(cb: str, **extra) -> list[dict]:
    text = "Inflation remains high. High inflation persists." * 2
    return [{"cb": cb, "date": f"{y}-{m:02d}-15", "text": text, "n_chars": len(text),
             **extra} for y in range(2014, 2024) for m in range(1, 9)]


def test_boj_printed_date_match_is_not_release_time_attestation():
    """印字日一致 (旧 same_day_attested=True) だけでは V3 gate を通さない (fail-closed)."""
    docs = _cov("fed") + _cov("ecb") + _cov("boj", same_day_attested=True)
    c = census_mod.census(docs)
    assert "boj" not in c["surviving_cbs"]
    assert c["boj_v3"]["printed_date_match"] == c["boj_v3"]["n"] == 80
    assert c["boj_v3"]["release_time_verified"] == 0


def test_boj_release_time_verified_positive_control():
    docs = _cov("fed") + _cov("ecb") + _cov("boj", release_time_verified=True)
    assert "boj" in census_mod.census(docs)["surviving_cbs"]


def test_boj_fetch_marks_release_time_unverified(monkeypatch, tmp_corpus):
    monkeypatch.setattr(fetch_mod, "SLEEP_SEC", 0)
    monkeypatch.setattr(fetch_mod, "discover_boj", lambda y: [
        (date(2023, 9, 22), "https://www.boj.or.jp/en/k230922a.htm")])
    html = (f"<html><body><main>Statement on Monetary Policy September 22, 2023 "
            f"Bank of Japan {BODY}</main></body></html>")
    monkeypatch.setattr(fetch_mod, "_fetch", lambda url, **k: html)
    (rec,) = fetch_mod.fetch_boj(2023)
    assert rec["printed_date_matches_meeting"] is True
    assert rec["release_time_verified"] is False
    assert "same_day_attested" not in rec


# ─────────────────────────── 3. --refetch (P2 4011713826) ────────────────────


def test_refetch_bypasses_date_cache(monkeypatch, tmp_corpus):
    monkeypatch.setattr(fetch_mod, "SLEEP_SEC", 0)
    monkeypatch.setattr(fetch_mod, "discover_fed", lambda y: [(date(2019, 9, 18), "s")])
    monkeypatch.setattr(fetch_mod, "_fetch", lambda url, **k: _fed_html(
        "Federal Reserve issues FOMC statement"))
    monkeypatch.setattr(fetch_mod, "_cached_date", lambda cb, d: True)
    assert fetch_mod.fetch_fed(2019) == []
    assert len(fetch_mod.fetch_fed(2019, refetch=True)) == 1


def test_refetch_bypasses_boe_url_cache(monkeypatch, tmp_corpus):
    monkeypatch.setattr(fetch_mod, "SLEEP_SEC", 0)
    url = "https://www.bankofengland.co.uk/x/2019/may-2019"
    monkeypatch.setattr(fetch_mod, "discover_boe", lambda y: [("may", url)])
    monkeypatch.setattr(fetch_mod, "_cached_urls", lambda: {url})
    page = ("<html><body><main>Published on 2 May 2019 Monetary Policy Summary, May "
            f"2019 {BODY} Minutes of the Monetary Policy Committee x</main></body></html>")
    monkeypatch.setattr(fetch_mod, "_fetch", lambda u, **k: page)
    assert fetch_mod.fetch_boe(2019) == []
    (rec,) = fetch_mod.fetch_boe(2019, refetch=True)
    assert rec["date"] == "2019-05-02"


def test_refetch_flag_reaches_fetchers(monkeypatch, tmp_corpus):
    seen = []
    monkeypatch.setattr(fetch_mod, "FETCHERS", {
        "fed": lambda year, refetch=False: seen.append(refetch) or []})
    fetch_mod.main(["--cb", "fed", "--years", "2019", "--refetch"])
    assert seen == [True]


# ─────────────────────────── 4. 窓境界 (P2 4011713829) ───────────────────────


def test_window_save_rejects_post_oos_end(tmp_corpus):
    assert fetch_mod.save(_rec("fed", "2026-07-29"), refetch=False) is False
    assert not (tmp_corpus / "fed" / "2026-07-29.json").exists()
    assert fetch_mod.save(_rec("fed", "2026-06-17"), refetch=False) is True


def test_window_loader_and_manifest_drop_post_oos_end(tmp_corpus):
    _write(tmp_corpus, _rec("boj", "2026-06-16"))
    _write(tmp_corpus, _rec("boj", "2026-07-31"))        # 既にコミットされた窓外ファイル
    _write(tmp_corpus, _rec("boe", "2026-12-01", "", missing_reason="x"))
    assert [r["date"] for r in fetch_mod.load_corpus()] == ["2026-06-16"]
    m = fetch_mod.write_manifest()
    assert m["n_docs_total"] == 1
    assert list(m["per_cb"]["boj"]["docs"]) == ["2026-06-16"]
    assert {(e["cb"], e["date"]) for e in m["excluded"]} == {
        ("boj", "2026-07-31"), ("boe", "2026-12-01")}


def test_window_committed_corpus_has_no_post_oos_records():
    """既知 NG 入力 = コミット済み fed 2026-07-29 / boj 2026-07-31 / boe 2026-09..12."""
    for r in fetch_mod.load_corpus():
        assert fetch_mod.EXPLORE_START.isoformat() <= r["date"] <= \
            fetch_mod.OOS_END.isoformat(), r["cb"] + "/" + r["date"]


def test_window_committed_manifest_matches_loader():
    m = json.loads((fetch_mod.CORPUS_DIR / "manifest.json").read_text(encoding="utf-8"))
    assert m["n_docs_total"] == len(fetch_mod.load_corpus())
    assert all(d <= fetch_mod.OOS_END.isoformat()
               for cb in m["per_cb"].values() for d in cb["docs"])


# ─────────────────────────── 5. Gate A explore 限定 (P1 4011810503) ──────────


def _weekdays(start: date, end: date) -> list[date]:
    out, d = [], start
    while d <= end:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out


def test_gate_a_ignores_oos_window_moves():
    """explore 窓は |fwd5| ≈ 5 pips、OOS 窓は 500 pips。median は explore 側だけで決まる."""
    valid = _weekdays(date(2022, 1, 3), date(2025, 12, 31))
    closes, px = {}, 1.0
    for d in valid:
        px += 0.0001 if d <= fetch_mod.EXPLORE_END else 0.0100
        closes[d] = px
    g = pass1_mod.unconditional_fwd5(valid, closes, "EUR_USD")
    assert g["median_abs_fwd5_pips"] == pytest.approx(5.0)
    assert g["gate_a_pass"] is False
    assert g["window"] == ["2014-01-01", "2023-12-31"]


# ─────────────────────────── 6. 生存 CB 強制 (P2 4011810505) ─────────────────


def _alt_docs(cb: str, years, day: int) -> list[dict]:
    texts = ("higher inflation and stronger growth.", "lower inflation and weaker growth.")
    out, i = [], 0
    for y in years:
        for m in range(1, 9):
            t = texts[i % 2]
            out.append({"cb": cb, "date": f"{y}-{m:02d}-{day:02d}", "text": t,
                        "n_chars": len(t), "release_time_verified": True})
            i += 1
    return out


@pytest.fixture
def d1_flat():
    valid = _weekdays(date(2014, 1, 1), date(2024, 2, 28))
    closes = {d: 1.0 for d in valid}
    return {p: (valid, closes) for p in pass1_mod.PAIRS}


GATE_A_ALL_PASS = {p: {"gate_a_pass": True} for p in pass1_mod.PAIRS}


def test_evaluate_drops_cb_failing_pass0_coverage(d1_flat):
    years = range(2014, 2024)
    docs = (_alt_docs("fed", years, 6) + _alt_docs("boe", years, 13)
            + _alt_docs("boj", [2023], 20))            # boj = 被覆 1/10 年 → 除外
    out = pass1_mod.evaluate(docs, d1_flat, GATE_A_ALL_PASS)
    assert out["pass0"]["surviving_cbs"] == ["fed", "boe"]
    cbs = {e["cb"] for e in out["enumeration"]["events"]}
    assert "boj" not in cbs and cbs == {"fed", "boe"}
    assert out["enumeration"]["n_docs_explore_usable"] == 160


def test_evaluate_data_blocked_does_not_enumerate(d1_flat):
    docs = _alt_docs("fed", range(2014, 2024), 6) + _alt_docs("boj", [2023], 20)
    out = pass1_mod.evaluate(docs, d1_flat, GATE_A_ALL_PASS)
    assert out["verdict"] == "DATA-BLOCKED"
    assert out["enumeration"] is None
    assert out["gate_b"] is None                    # 未評価 (UNDERPOWERED と混同しない)


# ── PR #309 review (2 巡目) ──────────────────────────────────────────────────


def test_run_data_blocked_never_opens_prices(monkeypatch, tmp_path):
    """P2 4151240546: DATA-BLOCKED は pass-1 非解錠 — 価格を開く前に返す."""
    docs = _alt_docs("fed", range(2014, 2024), 6)          # 生存 1 CB
    monkeypatch.setattr(pass1_mod, "load_corpus", lambda: docs)

    def _boom(*a, **k):
        raise AssertionError("DATA-BLOCKED なのに価格ファイルを開いた")
    monkeypatch.setattr(pass1_mod, "build_d1", _boom)
    out = pass1_mod.run(tmp_path, False)
    assert out["verdict"] == "DATA-BLOCKED"
    assert out["gate_a"] == {} and out["price_sources"] == {}


def test_gate_a_candidate_pairs_come_from_surviving_cbs(d1_flat):
    """P2 4151240550: fed+boe 生存で EUR/GBP が Gate A 不通過なら、JPY が通っても FAMILY_KILL."""
    years = range(2014, 2024)
    docs = _alt_docs("fed", years, 6) + _alt_docs("boe", years, 13)
    gate_a = {"EUR_USD": {"gate_a_pass": False}, "GBP_USD": {"gate_a_pass": False},
              "USD_JPY": {"gate_a_pass": True}}
    out = pass1_mod.evaluate(docs, d1_flat, gate_a)
    assert out["gate_a_candidate_pairs"] == ["EUR_USD", "GBP_USD"]
    assert out["gate_a_surviving_pairs"] == []
    assert out["verdict"] == "FAMILY_KILL"


def test_render_data_blocked_does_not_claim_underpowered(d1_flat):
    """P2 4151240553: DATA-BLOCKED の報告に「UNDERPOWERED」を併記しない."""
    docs = _alt_docs("fed", range(2014, 2024), 6)
    md = pass1_mod.render_md(pass1_mod.evaluate(docs, d1_flat, GATE_A_ALL_PASS), "x")
    assert "DATA-BLOCKED" in md
    assert "未達 = UNDERPOWERED" not in md
    assert "未評価" in md


# ─────────────────────────── 7. 凍結辞書 sha 実行時 assert (P2 4011810507) ──


def test_lexicon_runtime_assert_rejects_tampered_file(tmp_path):
    tampered = tmp_path / "lex.py"
    tampered.write_bytes(fetch_mod.LEXICON_PATH.read_bytes() + b"\n# extra stem\n")
    with pytest.raises(SystemExit):
        fetch_mod.assert_frozen_lexicon(tampered)
    assert fetch_mod.assert_frozen_lexicon() == fetch_mod.LEXICON_SHA256


def test_lexicon_assert_runs_before_price_load(monkeypatch, tmp_path):
    tampered = tmp_path / "lex.py"
    tampered.write_bytes(b"HAWKISH_ADJ_STEMS = ()\n")
    monkeypatch.setattr(fetch_mod, "LEXICON_PATH", tampered)

    def _boom(*a, **k):
        raise AssertionError("価格を開く前に辞書照合で止まるべき")
    monkeypatch.setattr(pass1_mod, "build_d1", _boom)
    with pytest.raises(SystemExit):
        pass1_mod.run(tmp_path, False)
    with pytest.raises(SystemExit):
        census_mod.census([])


def test_lexicon_pin_matches_test_pin():
    from tests.test_e23_corpus_harness import PINNED_SHA
    assert fetch_mod.LEXICON_SHA256 == PINNED_SHA


def test_collision_void_uses_excluded_cb_dates(d1_flat):
    """PR #309 3 巡目 P2 4151283577: Fed が被覆不足で除外されても Fed/ECB 同日の ECB は void."""
    years = range(2014, 2024)
    ecb = _alt_docs("ecb", years, 6)
    fed = _alt_docs("fed", [2023], 6)                      # 被覆 1/10 年 → 除外、日付は ECB と同日
    boe = _alt_docs("boe", years, 13)
    out = pass1_mod.evaluate(ecb + fed + boe, d1_flat, GATE_A_ALL_PASS)
    assert out["pass0"]["surviving_cbs"] == ["ecb", "boe"]
    ev = out["enumeration"]["events"]
    assert not any(e["cb"] == "ecb" and e["statement_date"].startswith("2023") for e in ev)
    # 2023 の ECB 8 本のうち 1 月分は前年 8 月から >120 日で staleness void が先に当たる
    assert out["enumeration"]["voids"].get("ecb:fed_ecb_same_day") == 7
    assert all(e["cb"] in {"ecb", "boe"} for e in ev)
