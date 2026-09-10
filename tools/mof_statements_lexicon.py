"""Lexicon ladder + conference-transcript parser for MoF FX verbal intervention.

Pure text processing — no network, no price data, no side effects at import
(this module doubles as a library for tools/mof_statements_ingest.py,
tools/mof_statements_daily.py and tests/test_mof_statements_lexicon.py).

Ladder design (ordered severity, Gnabo-style talk/act discretization):
  1 watch      為替市場の動向を注視 (baseline monitoring language)
  2 concern    過度な変動・急速な変動・一方的な動き・憂慮・緊張感
  3 readiness  あらゆる選択肢を排除しない・適切な対応・万全な対応・投機への言及
  4 resolute   断固たる措置/対応 (imminent-action language)
  5 action     介入実施・平衡操作・レートチェックへの明示的言及 (talk+act)

Scoring discipline:
  - Only minister-side text (opening statements + answers) is scored.
    Journalists routinely quote ladder phrases in questions; counting them
    would inflate scores (see tests).
  - FX relevance flows from the exchange: an answer to an FX question is
    FX-relevant even when it does not repeat 「為替」.
  - 「コメントを差し控える」 is recorded as a separate no_comment flag, not a
    ladder level (no-comment spikes during actual intervention windows are
    themselves informative, but they are not escalation language).

Boundary (MoF #4 pre-reg cross-LOCK): this module never touches price data or
intervention-day labels. Joint statement x intervention x price measurement is
prohibited until its own pre-registration (see
knowledge-base/wiki/analyses/mof-communication-data-infrastructure.md).
"""
import re

# ---------------------------------------------------------------------------
# Ladder lexicon (ordered; higher level = closer to action)
# ---------------------------------------------------------------------------
LADDER = [
    (1, "watch", [
        r"注視",
        r"動向を(?:しっかり|よく|注意深く)?(?:と)?見守",
    ]),
    (2, "concern", [
        r"過度な変動",
        r"過度の変動",
        r"急速な変動",
        r"急激な変動",
        r"一方的な(?:動き|変動)",
        r"行き過ぎた動き",
        r"憂慮",
        r"望ましくない",
        r"緊張感",
    ]),
    (3, "readiness", [
        r"あらゆる選択肢",
        r"選択肢を排除(?:せず|しない|することなく)",
        r"適切(?:な|に)対応",
        r"万全(?:の|な)対応",
        r"必要な対応",
        r"投機的?(?:な動き)?",
    ]),
    (4, "resolute", [
        r"断固",
        r"毅然",
    ]),
    (5, "action", [
        r"介入を(?:実施|行(?:い|った|う)|いたし)",
        r"平衡操作を実施",
        r"レートチェック",
    ]),
]

# FX-relevance keywords (block/exchange level)
FX_KEYWORDS = re.compile(
    r"為替|円安|円高|円相場|介入|平衡操作|ドル円|通貨|投機|変動"
)

NO_COMMENT = re.compile(
    r"コメント(?:は|を)?(?:いたし|し)?(?:ません|ない)"
    r"|コメント(?:は|を)?差し控え"
    r"|(?:お答え|回答)(?:は|を)?(?:いたし|し)?(?:ません|ない|差し控え|控え)"
    r"|申し上げ(?:ることは)?(?:できない|できません)"
    r"|述べることはできない"
)

# 令和/平成 date, both half-width and full-width parentheses appear across years
_WAREKI = re.compile(r"(令和|平成)(\d+|元)年\s*(\d+)\s*月\s*(\d+)\s*日")
_URL_DATE = re.compile(r"my(20\d{6})\.html?")
_TITLE = re.compile(r"<title>([^<]*)</title>", re.I)
_MINISTER = re.compile(r"([一-鿿]{1,6})財務大臣")
_ZAIMUKAN = re.compile(r"([一-鿿]{1,6})財務官")


def wareki_to_iso(era: str, year: str, month: int, day: int) -> str:
    yy = 1 if year == "元" else int(year)
    base = 2018 if era == "令和" else 1988
    return f"{base + yy:04d}-{month:02d}-{day:02d}"


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def score_minister_text(text: str) -> dict:
    """Score one minister-side text against the ladder.

    Returns {level: int (0 = no FX ladder language), matches: {level: [phrase]},
    no_comment: bool}. Ladder phrases only count when the text (or its exchange
    context — handled by score_conference) is FX-relevant; this function itself
    requires FX relevance in the text for level>0 unless caller overrides via
    fx_context=True semantics in score_conference.
    """
    return _score_text(text, fx_context=bool(FX_KEYWORDS.search(text)))


def _score_text(text: str, fx_context: bool) -> dict:
    matches: dict[int, list] = {}
    if fx_context:
        for level, _name, patterns in LADDER:
            hits = []
            for pat in patterns:
                for m in re.finditer(pat, text):
                    hits.append(m.group(0))
            if hits:
                matches[level] = sorted(set(hits))
    level = max(matches) if matches else 0
    return {
        "level": level,
        "matches": matches,
        "no_comment": bool(NO_COMMENT.search(text)) and fx_context,
    }


def score_conference(blocks: list) -> dict:
    """Aggregate one conference into a score row.

    blocks: [{role: opening|question|answer, text: str}, ...] in page order.
    Minister-side roles (opening/answer) are scored; FX relevance is inherited
    from the preceding question when the answer itself lacks FX keywords.
    """
    max_level = 0
    n_fx_blocks = 0
    all_matches: dict[int, list] = {}
    no_comment = False
    question_fx = False
    for b in blocks:
        role, text = b.get("role"), b.get("text", "")
        if role == "question":
            question_fx = bool(FX_KEYWORDS.search(text))
            continue
        if role not in ("opening", "answer"):
            continue
        fx_context = bool(FX_KEYWORDS.search(text)) or (role == "answer" and question_fx)
        if not fx_context:
            continue
        r = _score_text(text, fx_context=True)
        n_fx_blocks += 1
        no_comment = no_comment or r["no_comment"]
        max_level = max(max_level, r["level"])
        for lv, hits in r["matches"].items():
            all_matches.setdefault(lv, [])
            all_matches[lv] = sorted(set(all_matches[lv]) | set(hits))
    return {
        "max_level": max_level,
        "n_fx_blocks": n_fx_blocks,
        "matches": all_matches,
        "no_comment": no_comment,
    }


# ---------------------------------------------------------------------------
# Conference HTML parsing
# ---------------------------------------------------------------------------
_SECTION_OPENING = "【冒頭発言】"
_SECTION_QA = "【質疑応答】"
_Q_MARK = re.compile(r"^[（(]?問[）)]\s*")
_A_MARK = re.compile(r"^[（(]?答[）)]\s*")
_END_MARK = re.compile(r"^（以上）|^\(以上\)")
_FOOTER = re.compile(r"Copyright|サイトマップ|ページの先頭|財務省の政策|関連リンク")


def _html_to_lines(html: str) -> list:
    body = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    body = re.sub(r"<br\s*/?>", "\n", body, flags=re.I)
    body = re.sub(r"</?(p|div|h\d|li|tr|table)[^>]*>", "\n", body, flags=re.I)
    text = re.sub(r"<[^>]+>", "", body)
    text = text.replace("　", " ").replace("&nbsp;", " ")
    return [ln.strip() for ln in text.split("\n") if ln.strip()]


def parse_conference_html(html: str, url: str = "") -> dict:
    """Parse one MoF press-conference page into {date, title, minister, blocks}.

    Works on both live mof.go.jp pages and WARP `id_` raw captures (identical
    original markup). Returns blocks=[] when the page has no 問/答 structure —
    callers must treat that as a parse failure, not an empty conference.
    """
    title_m = _TITLE.search(html)
    title = title_m.group(1).strip() if title_m else ""
    date = None
    wm = _WAREKI.search(title)
    if wm:
        date = wareki_to_iso(wm.group(1), wm.group(2), int(wm.group(3)), int(wm.group(4)))
    else:
        um = _URL_DATE.search(url)
        if um:
            s = um.group(1)
            date = f"{s[:4]}-{s[4:6]}-{s[6:8]}"
    minister_m = _MINISTER.search(title)
    if minister_m:
        minister = minister_m.group(1)
    else:
        # non-minister pages that still carry FX-relevant remarks
        # (神田/三村財務官 単独・共同会見、G7 議長会見 等)
        zk = _ZAIMUKAN.search(title)
        minister = f"{zk.group(1)}(財務官)" if zk else ""

    lines = _html_to_lines(html)
    blocks = []
    role = None  # outside transcript until a section marker or 問）
    for ln in lines:
        if _SECTION_OPENING in ln:
            role = "opening"
            continue
        if _SECTION_QA in ln:
            role = None
            continue
        if _END_MARK.search(ln):
            break
        if _Q_MARK.match(ln):
            blocks.append({"role": "question", "text": _Q_MARK.sub("", ln)})
            role = "question"
            continue
        if _A_MARK.match(ln):
            blocks.append({"role": "answer", "text": _A_MARK.sub("", ln)})
            role = "answer"
            continue
        if role is None:
            continue
        if _FOOTER.search(ln):
            role = None
            continue
        # continuation line of the current block
        if blocks and blocks[-1]["role"] == role:
            blocks[-1]["text"] += " " + ln
        elif role == "opening":
            blocks.append({"role": "opening", "text": ln})
    return {"date": date, "title": title, "minister": minister, "url": url, "blocks": blocks}
