"""family A statement_ladder — FROZEN signal-side detector (台帳 #27).

🔒 Frozen 2026-09-18 by
   knowledge-base/wiki/decisions/family-a-statement-ladder-prereg-2026-08-19.md §10
   (adversarial verification: .../family-a-adversarial-verification-2026-09-18.md).

Scope discipline (pre-reg §0): this module is **label-free and price-free**.
It reads only `lexicon_scores.csv` (the pinned lexicon v1 scorer output,
tools/mof_statements_lexicon.py @ PR #194 commit 569dbe3f) and emits the
signal state series, the rearmed event list and the armed-day mask.
It must never import intervention labels or price data — the joint
statement x label measurement lives in the pass-2 harness, gated on the
pass-1 gates computed here.

Frozen parameters (design argument only, never data-calibrated):
    T = 5   business days  carry-forward of the last conference level
    R = 20  business days  rearm window, measured event-to-event
                           (minimum separation R+1 = 21 bd > H, so the
                            per-event hit windows partition cleanly)
    H = 20  business days  hit horizon (arming window per event)
    primary trigger: X_d >= 4

Frozen level remap (adversarial finding A-1): ladder level 5 as scored by
lexicon v1 mixes *leading* language (rate check) with *retrospective /
generic* narration of interventions that already happened
(介入を実施/行った/行い/いたし/行う, 平衡操作を実施).  Retrospective L5 is
outcome-side language, not a ladder rung: counting it would hand the
detector the answer.  A conference whose only >=5 evidence is retrospective
is demoted to the highest non-retrospective level it matched.
"""
from __future__ import annotations

import csv
import datetime as _dt
from dataclasses import dataclass

try:  # hard requirement: the frozen calendar must be reproducible
    import jpholiday
except ImportError as exc:  # pragma: no cover - environment guard
    raise ImportError(
        "family_a_ladder_detector requires jpholiday (requirements.txt) — "
        "the frozen detector pins the Tokyo business-day calendar"
    ) from exc

# --- frozen constants -------------------------------------------------------
T_CARRY_BD = 5
R_REARM_BD = 20
H_HORIZON_BD = 20
TRIGGER_LEVEL = 4

#: L5 phrases that are *leading* (talk before act) — stay at level 5.
L5_LEADING = ("レートチェック",)
#: L5 phrases that narrate an intervention already taken, or speak of
#: intervention in the abstract — outcome-side, demoted (adversarial A-1).
L5_RETROSPECTIVE = (
    "介入を実施",
    "介入を行い",
    "介入を行った",
    "介入をいたし",
    "介入を行う",
    "平衡操作を実施",
)

DEFAULT_SCORES_CSV = "data/external/mof_statements/lexicon_scores.csv"


# --- Tokyo business-day calendar -------------------------------------------
def is_business_day(day: _dt.date) -> bool:
    if day.weekday() >= 5:
        return False
    if jpholiday.is_holiday(day):
        return False
    # 年末年始休 (12/31-1/3) — 官庁御用納め/御用始め
    if (day.month, day.day) in ((12, 29), (12, 30), (12, 31), (1, 2), (1, 3)):
        return False
    return True


def business_days(start: _dt.date, end: _dt.date) -> list[_dt.date]:
    out, d = [], start
    step = _dt.timedelta(days=1)
    while d <= end:
        if is_business_day(d):
            out.append(d)
        d += step
    return out


# --- level remap ------------------------------------------------------------
def _parse_matches(matched_phrases: str) -> dict[int, list[str]]:
    out: dict[int, list[str]] = {}
    for tok in (matched_phrases or "").split(";"):
        tok = tok.strip()
        if not tok or ":" not in tok:
            continue
        lv_s, phrases = tok.split(":", 1)
        if not (lv_s.startswith("L") and lv_s[1:].isdigit()):
            continue
        out.setdefault(int(lv_s[1:]), []).extend(p for p in phrases.split("/") if p)
    return out


def effective_level(max_level: int, matched_phrases: str) -> int:
    """Frozen remap: demote retrospective-only L5 to its highest talk level."""
    if max_level < 5:
        return max_level
    m = _parse_matches(matched_phrases)
    l5 = m.get(5, [])
    if any(any(lead in p for lead in L5_LEADING) for p in l5):
        return 5
    lower = [lv for lv in m if lv <= 4]
    return max(lower) if lower else 0


# --- series construction ----------------------------------------------------
@dataclass(frozen=True)
class DetectorOutput:
    days: list[_dt.date]
    level: dict[_dt.date, int]
    events: list[_dt.date]
    armed: set


def load_conference_levels(path: str = DEFAULT_SCORES_CSV) -> dict[_dt.date, int]:
    """date -> effective (remapped) conference level; same-day max if repeated."""
    levels: dict[_dt.date, int] = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            day = _dt.date.fromisoformat(row["date"])
            lv = effective_level(int(row["max_level"]), row.get("matched_phrases", ""))
            levels[day] = max(levels.get(day, 0), lv)
    return levels


def build(
    start: _dt.date,
    end: _dt.date,
    conference_levels: dict[_dt.date, int] | None = None,
    scores_csv: str = DEFAULT_SCORES_CSV,
) -> DetectorOutput:
    """Build the frozen signal state series, event list and armed mask."""
    conf = load_conference_levels(scores_csv) if conference_levels is None else conference_levels
    days = business_days(start, end)
    level: dict[_dt.date, int] = {}
    carry_lv, carry_age = 0, 0
    for d in days:
        if d in conf:
            carry_lv, carry_age = conf[d], 0
        else:
            carry_age += 1
            if carry_age > T_CARRY_BD:
                carry_lv, carry_age = 0, 0
        level[d] = carry_lv

    # Rearm is defined on the *event* series, not on the level series
    # (adversarial finding A-2): looking back over carried level>=4 days would
    # make the effective refractory period R + T = 25 bd and could merge two
    # genuinely distinct episodes sitting at the 30-calendar-day gap boundary.
    events: list[_dt.date] = []
    last_event_idx: int | None = None
    for i, d in enumerate(days):
        if level[d] < TRIGGER_LEVEL:
            continue
        if last_event_idx is not None and (i - last_event_idx) <= R_REARM_BD:
            continue
        events.append(d)
        last_event_idx = i

    armed: set = set()
    idx = {d: i for i, d in enumerate(days)}
    for e in events:
        i = idx[e]
        for x in days[i : i + H_HORIZON_BD + 1]:
            armed.add(x)
    return DetectorOutput(days=days, level=level, events=events, armed=armed)


# --- pass-1 gates (label-free) ---------------------------------------------
GATE_A_MAX_ARMED_FRACTION = 0.25
GATE_B_MIN_EVENTS = 5
GATE_B_MIN_DISTINCT_YEARS = 2


def pass1_gates(out: DetectorOutput) -> dict:
    n_days = len(out.days)
    frac = (len(out.armed) / n_days) if n_days else 0.0
    years = {d.year for d in out.events}
    gate_a = frac <= GATE_A_MAX_ARMED_FRACTION
    gate_b = len(out.events) >= GATE_B_MIN_EVENTS and len(years) >= GATE_B_MIN_DISTINCT_YEARS
    return {
        "n_business_days": n_days,
        "n_events": len(out.events),
        "event_years": sorted(years),
        "armed_fraction": frac,
        "gate_a_specificity": gate_a,
        "gate_b_supply": gate_b,
        "pass2_unlocked": bool(gate_a and gate_b),
    }
