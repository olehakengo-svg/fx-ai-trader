#!/usr/bin/env python3
"""#29 S1 step 1 — Apel–Blix Grimaldi–Hull (2019) FOMC hawk/dove 辞書の逐語転記 + 凍結スコアラー.

出典 (一次資料、観測窓 2014+ に全面先行 = 標本 1993–2012、探索自由度ゼロ)
--------------------------------------------------------------------------
  Apel, M., M. Blix Grimaldi & I. Hull (2019), "How Much Information Do Monetary
  Policy Committees Disclose? Evidence from the FOMC's Minutes and Transcripts",
  Sveriges Riksbank Working Paper Series No. 381 (November 2019).
  6 Appendix, Table 4 (Inflation, p.34) / Table 5 (Economic Activity, p.35) /
  Table 6 (Employment, p.36); 本文 §2.1 (pp.6–8) と式 (1) (p.8).
  URL: https://www.riksbank.se/globalassets/media/rapporter/working-papers/2019/
       no.-381--how-much-information-do-monetary-policy-committees-disclose-evidence-from-the-fomcs-minutes-and-transcripts.pdf
  取得日: 2026-11-05 (HTTP 200、614,933 bytes、
  sha256 a5e1e048f57d9d5384ffb7ee2e785d8cbf981464b1f8ad657a2cc0679fd6f14f)。
  転記は PDF のテキスト層から x 座標で列 (TERM / HAWKISH / DOVISH) を機械判定し、
  目視で全行照合した (2026-11-05 autopilot)。

利用条件 (再利用根拠 — user 明示承認 #29-L、2026-11-03、round6 §9.1)
--------------------------------------------------------------------
  Sveriges Riksbank, "Open data – information available for re-use" (2026-11-05 取得):
  https://www.riksbank.se/en-gb/about-the-riksbank/about-the-website/open-data--information-available-for-re-use/
  原文: "The Riksbank's open data is freely available and may be further used without
  any special consent or agreement being required. Enter source, Sveriges riksbank
  and date." 同頁は re-use 対象文書として "Publications and reports — The Riksbank's
  publications are available for download at riksbank.se" を列挙し、根拠法を
  the act (2022:818) on the public sector making data available for re-use
  (EU directive 2019/1024 の国内法、旧 PSI 法 2010:566 を置換) としている。
  出所表記 (条件の履行): Source: Sveriges Riksbank, Working Paper No. 381 (2019),
  retrieved 2026-11-05.
  未確認点 (KB adhoc-scan-29-step0 §4.2 追補に同文): 法 2022:818 の条文そのものが
  WP 付録の語彙表 (著作物性) に及ぶかは一次資料 (riksdagen.se の条文) で未確認。
  user が本読みに異論を述べた時点で転記を止め、本モジュールと派生物を削除する。

凍結規則 (WP 381 §2.1 の記述を as-is で実装。変更は test_adhoc29_lexicon_abgh2019 が検知)
---------------------------------------------------------------------------------
  - 語彙は Appendix 3 表の逐語転記。**印字どおりに転記し語彙編集はしない** —
    Table 5 "consumer spending" の HAWKISH 列に `soft*` / `weak*` が印字されている
    (同列の DOVISH にも `soft*`) が、誤植の可能性を含めて印字どおり転記する
    (転記側で「直す」ことは語彙 DoF の持ち込み = C5 違反)。
  - TERM は小文字トークン列の完全一致 (`*` なし)。複数語 TERM は連続トークン。
    「Some terms are substrings of others ... We count these cases as a single
    instance」→ 同一位置では最長一致 1 件のみ ("inflation pressure" が一致したら
    "inflation" は数えない。"unemployment" は 1 トークンで "employment" と別トークン)。
    Table 4 Notes の「core inflation / inflation rate / inflation expectations は
    unigram "inflation" で拾う」もこの規則で成立する。
  - MODIFIER: `x*` = 語幹前方一致 ("all words with the same stem")、`*` なし = 完全一致。
    2 語 modifier (`edg* up` / `pick* up` / `step* up` / `turn* up`) = 先頭語の
    前方一致 + 直後トークン "up" の完全一致。`run-up/runup` = トークン "run-up" または
    "runup" の完全一致。
  - 窓: 同一文内で TERM と MODIFIER の間に **最大 7 語** (0 語 = 隣接も含む)、
    前後どちらの順序も可 ("lower inflation" / "expect inflation to be lower")。
    文境界 = `[.!?]`。
  - 計数: TERM 出現 × 窓内 MODIFIER 出現の各組合せを 1 件 (「all term–modifier
    combinations の occurrences」の字義読み)。1 件の modifier が 2 つの TERM 出現の
    窓内にあれば 2 件。WP はこの点を明示しないため、census 実行前に本規則 1 本へ凍結し
    代替規則は試さない (adhoc-scan-29-step0 §4.2「1 規則に凍結して試行しない」)。
  - NH = 1 + (hawk − dove) / (hawk + dove) (式 (1)、範囲 [0, 2]、中立 = 1)。
    hawk + dove = 0 の文書のみ **NH = 1 (中立) を代入** (step0 §4.2 の凍結規則)。
  - 本モジュールは「テキスト → カウント / スコア」のみ。価格・リターン・イベント・DB
    との結合は行わない (価格非接触)。
"""
from __future__ import annotations

import hashlib
import json
import re

# ─── 凍結語彙: WP 381 Appendix Tables 4–6 の逐語転記 ─────────────────────────
# 構造: (table, (terms...), (hawkish modifiers...), (dovish modifiers...))
# 行順・綴り・`*` の有無は印字どおり。TERM 列で同一 modifier ブロックを共有する
# 2 語 (Table 4 "consumer prices"/"inflation"、Table 5 "economic activity"/
# "economic growth") は 1 エントリに束ねる (印字レイアウトどおり)。
DICTIONARY: tuple[tuple[str, tuple[str, ...], tuple[str, ...], tuple[str, ...]], ...] = (
    (
        "Table 4: Inflation",
        ("consumer prices", "inflation"),
        ("accelerat*", "boost*", "elevated", "escalat*", "high*", "increas*", "jump*",
         "pickup", "rise*", "rose", "rising", "run-up/runup", "strong*", "surg*", "up*"),
        ("decelerat*", "declin*", "decreas*", "down*", "drop*", "fall*", "fell", "low*",
         "muted", "reduc*", "slow*", "stable", "subdued", "weak*", "contained"),
    ),
    (
        "Table 4: Inflation",
        ("inflation pressure",),
        ("accelerat*", "boost*", "build*", "elevat*", "emerg*", "great*", "height*",
         "high*", "increas*", "intensif*", "mount*", "pickup", "rise", "rose", "rising",
         "stok*", "strong*", "sustain*"),
        ("abat*", "contain*", "dampen*", "decelerat*", "declin*", "decreas*", "dimin*",
         "eas*", "fall*", "fell", "low*", "moderat*", "reced*", "reduc*", "subdued",
         "temper*"),
    ),
    (
        "Table 5: Economic Activity",
        ("consumer spending",),
        # ⚠ 印字どおり: HAWKISH 列に soft* / weak* (誤植の可能性、編集しない)
        ("accelerat*", "edg* up", "expan*", "increas*", "pick* up", "pickup", "soft*",
         "strength*", "strong*", "weak*"),
        ("contract*", "decelerat*", "decreas*", "drop*", "retrench*", "slow*", "slugg*",
         "soft*", "subdued"),
    ),
    (
        "Table 5: Economic Activity",
        ("economic activity", "economic growth"),
        ("accelerat*", "buoyant", "edg* up", "expan*", "increas*", "high*", "pick* up",
         "pickup", "rise*", "rose", "rising", "step* up", "strength*", "strong*", "upside"),
        ("contract*", "curtail*", "decelerat*", "declin*", "decreas*", "downside", "drop",
         "fall*", "fell", "low*", "moderat*", "slow*", "slugg*", "weak*"),
    ),
    (
        "Table 5: Economic Activity",
        ("resource utilization",),
        ("high*", "increas*", "rise", "rising", "rose", "tight*"),
        ("declin*", "fall*", "fell", "loose*", "low*"),
    ),
    (
        "Table 6: Employment",
        ("employment",),
        ("expand*", "gain*", "improv*", "increas*", "pick* up", "pickup", "rais*", "rise*",
         "rising", "rose", "strength*", "turn* up"),
        ("slow*", "declin*", "reduc*", "weak*", "deteriorat*", "shrink*", "shrank", "fall*",
         "fell", "drop*", "contract*", "sluggish"),
    ),
    (
        "Table 6: Employment",
        ("labor market",),
        ("strain*", "tight*"),
        ("eased", "easing", "loos*", "soft*", "weak*"),
    ),
    (
        "Table 6: Employment",
        ("unemployment",),
        ("declin*", "fall*", "fell", "low*", "reduc*"),
        ("elevat*", "high", "increas*", "ris*", "rose*"),
    ),
)

WINDOW_WORDS = 7           # WP 381 §2.1: "separated by up to seven words within the same sentence"
NEUTRAL_NH = 1.0           # 式 (1) の h = d の値; h + d = 0 のみ代入 (step0 §4.2)

_SENT_SPLIT = re.compile(r"[.!?]")
_TOKEN = re.compile(r"[a-z]+(?:-[a-z]+)*")


def dictionary_sha256() -> str:
    """凍結語彙の指紋 (canonical JSON)。test が hex を pin する。"""
    payload = json.dumps(DICTIONARY, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _compile_term_index() -> list[tuple[tuple[str, ...], int]]:
    """(term tokens, entry index) を最長一致優先 (トークン数降順) で返す。"""
    out: list[tuple[tuple[str, ...], int]] = []
    for idx, (_t, terms, _h, _d) in enumerate(DICTIONARY):
        for term in terms:
            out.append((tuple(term.split()), idx))
    out.sort(key=lambda x: -len(x[0]))
    return out


_TERM_INDEX = _compile_term_index()


def _modifier_match(tokens: list[str], i: int, spec: str) -> int:
    """位置 i で modifier spec が一致すれば消費トークン数、不一致なら 0。"""
    if spec == "run-up/runup":
        return 1 if tokens[i] in ("run-up", "runup") else 0
    parts = spec.split()
    if len(parts) == 2:                       # "edg* up" 型
        first, second = parts
        if i + 1 >= len(tokens):
            return 0
        ok_first = tokens[i].startswith(first[:-1]) if first.endswith("*") else tokens[i] == first
        return 2 if ok_first and tokens[i + 1] == second else 0
    if spec.endswith("*"):
        return 1 if tokens[i].startswith(spec[:-1]) else 0
    return 1 if tokens[i] == spec else 0


def _find_terms(tokens: list[str]) -> list[tuple[int, int, int]]:
    """文内の TERM 出現 [(start, end_exclusive, entry_idx)] — 同一位置は最長一致 1 件。"""
    found: list[tuple[int, int, int]] = []
    i = 0
    while i < len(tokens):
        hit = None
        for term_toks, idx in _TERM_INDEX:
            n = len(term_toks)
            if tuple(tokens[i:i + n]) == term_toks:
                hit = (i, i + n, idx)
                break
        if hit is None:
            i += 1
        else:
            found.append(hit)
            i = hit[1]
    return found


def _find_modifiers(tokens: list[str], specs: tuple[str, ...]) -> list[tuple[int, int, str]]:
    """文内の modifier 出現 [(start, end_exclusive, spec)]。"""
    out: list[tuple[int, int, str]] = []
    for i in range(len(tokens)):
        for spec in specs:
            n = _modifier_match(tokens, i, spec)
            if n:
                out.append((i, i + n, spec))
    return out


def _within_window(t0: int, t1: int, m0: int, m1: int) -> bool:
    """TERM [t0,t1) と MODIFIER [m0,m1) の間の語数が WINDOW_WORDS 以下 (重なりは不可)。"""
    if m0 >= t1:
        return (m0 - t1) <= WINDOW_WORDS
    if t0 >= m1:
        return (t0 - m1) <= WINDOW_WORDS
    return False


def count_combinations(text: str) -> dict:
    """凍結 term–modifier 組合せの計数.

    戻り値 = {"hawk": int, "dove": int,
              "matches": [(polarity, term, modifier_spec, table), ...]}
    """
    hawk = dove = 0
    matches: list[tuple[str, str, str, str]] = []
    for sentence in _SENT_SPLIT.split(text.lower()):
        tokens = _TOKEN.findall(sentence)
        if not tokens:
            continue
        for t0, t1, idx in _find_terms(tokens):
            table, _terms, hawk_specs, dove_specs = DICTIONARY[idx]
            term = " ".join(tokens[t0:t1])
            for m0, m1, spec in _find_modifiers(tokens, hawk_specs):
                if _within_window(t0, t1, m0, m1):
                    hawk += 1
                    matches.append(("h", term, spec, table))
            for m0, m1, spec in _find_modifiers(tokens, dove_specs):
                if _within_window(t0, t1, m0, m1):
                    dove += 1
                    matches.append(("d", term, spec, table))
    return {"hawk": hawk, "dove": dove, "matches": matches}


def net_hawkishness(text: str) -> float:
    """WP 381 式 (1): NH = 1 + (hawk − dove)/(hawk + dove)。hawk + dove = 0 → NEUTRAL_NH。"""
    c = count_combinations(text)
    tot = c["hawk"] + c["dove"]
    if tot == 0:
        return NEUTRAL_NH
    return 1.0 + (c["hawk"] - c["dove"]) / tot


def delta_net_hawkishness(text_t: str, text_prev: str) -> float:
    """同一 CB の連続声明の差分 ΔNH (census の |ΔNH| > τ、τ = 0 の素材)。"""
    return net_hawkishness(text_t) - net_hawkishness(text_prev)
