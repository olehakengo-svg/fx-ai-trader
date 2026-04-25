#!/usr/bin/env python3
"""
EDGE.md Linter — validates the cell-aware routing manifest.

Spec: knowledge-base/wiki/manifests/SPEC.md

Usage:
    python3 tools/edge_md_lint.py knowledge-base/wiki/manifests/EDGE.md
    python3 tools/edge_md_lint.py --check ...   # exit 1 on errors (CI/pre-commit)
    python3 tools/edge_md_lint.py --format json ...

Rules:
    E1 broken-source         — source_prereg/source_result wikilink not found
    E2 expired               — expires_at < now
    E3 routing-status-mismatch — illegal routing × status × bonferroni combo
    E4 cell-validity         — cell not in v6 enumerated set
    E5 strategy-validity     — strategy not in _FORCE_DEMOTED ∪ QUALIFIED_TYPES
    W1 stale                 — edges_updated_at older than 30 days
    W2 source-divergence     — numeric fields not corroborated by source_result
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

_PROJECT_ROOT = Path(os.path.dirname(os.path.abspath(__file__))).parent
sys.path.insert(0, str(_PROJECT_ROOT))

# Reuse parsers from tier_integrity_check
from tools.tier_integrity_check import _parse_simple_set, _parse_frozenset

DEMO_TRADER = _PROJECT_ROOT / "modules" / "demo_trader.py"
ANALYSES_DIR = _PROJECT_ROOT / "knowledge-base" / "wiki" / "analyses"

# v6 cell space (Regime × Vol × Session) — see SPEC.md
ACTIVE_REGIMES = {
    "R0",  # excluded but accept for cell name validity
    "R1_trend_up", "R2_trend_down",
    "R3_range_tight", "R4_range_wide",
    "R5_breakout", "R6_reversal",
}
VOL_BUCKETS = {"V_low", "V_mid", "V_high"}
SESSIONS = {"Asia", "London", "NY", "Off"}

VALID_STATUS = {"SURVIVOR", "CANDIDATE", "REJECT", "REJECT_CANDIDATE"}
VALID_ROUTING = {"NONE", "BLOCK", "KELLY_HALF", "KELLY_FULL"}

STALE_DAYS = 30


# ─────────────────────────────────────────────────────────────────
# Parsing
# ─────────────────────────────────────────────────────────────────


def _extract_yaml_block(text: str) -> str:
    """Extract the first ```yaml ... ``` fenced block, or top-level --- ... ---.

    SPEC allows YAML inside a fenced block (Markdown convention) OR as front
    matter. Try fenced first (richer prose convention), then front matter.
    """
    # Fenced ```yaml ... ```
    m = re.search(r"```yaml\s*\n(.*?)\n```", text, re.DOTALL)
    if m:
        return m.group(1)
    # Front matter --- ... ---
    m = re.match(r"---\s*\n(.*?)\n---", text, re.DOTALL)
    if m:
        return m.group(1)
    return ""


def _yaml_load(text: str):
    """Try pyyaml first, fall back to a tiny purpose-built parser.

    The fallback supports the constrained subset used by EDGE.md:
      - top-level scalars (string, int, float, bool, null)
      - top-level "key: []" empty list
      - top-level "edges:" followed by a list of mappings (one mapping per
        "  - key: value" block, continuation lines indented by 4 spaces)
    """
    try:
        import yaml  # type: ignore
        return yaml.safe_load(text)
    except ImportError:
        return _minimal_yaml_load(text)


_BOOL_MAP = {"true": True, "false": False, "yes": True, "no": False}


def _coerce_scalar(s: str):
    s = s.strip()
    # Strip optional inline comment
    if "#" in s and not (s.startswith('"') or s.startswith("'")):
        s = s.split("#", 1)[0].rstrip()
    if s == "":
        return None
    # YAML 1.2 only: 'null' and '~' are null. Bare uppercase NONE/Null are strings.
    if s in ("null", "~"):
        return None
    if s.lower() in _BOOL_MAP:
        return _BOOL_MAP[s.lower()]
    # Quoted string
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        return s[1:-1]
    # Inline list "[]" or "[a, b]"
    if s.startswith("[") and s.endswith("]"):
        inner = s[1:-1].strip()
        if not inner:
            return []
        return [_coerce_scalar(x) for x in inner.split(",")]
    # Numeric
    try:
        if "." in s or "e" in s or "E" in s:
            return float(s)
        return int(s)
    except ValueError:
        return s


def _minimal_yaml_load(text: str):
    """Parse the constrained EDGE.md YAML subset."""
    lines = text.split("\n")
    result = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.rstrip()
        if not stripped or stripped.lstrip().startswith("#"):
            i += 1
            continue
        # Top-level "key: value" or "key:" (block follows)
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$", stripped)
        if not m:
            i += 1
            continue
        key, val = m.group(1), m.group(2)
        if val == "":
            # Block follows: either list of mappings (- ...) or nested map
            block = []
            i += 1
            while i < len(lines):
                ln = lines[i]
                if ln.strip() == "" or ln.lstrip().startswith("#"):
                    i += 1
                    continue
                # End of block when indent drops back to 0 with a key-like line
                if not ln.startswith(" ") and not ln.startswith("-"):
                    break
                if ln.lstrip().startswith("- "):
                    # New list item — gather subsequent indented continuation lines
                    item_text = ln.lstrip()[2:]
                    item = {}
                    # First line of item may have "key: value"
                    mm = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$", item_text)
                    if mm:
                        item[mm.group(1)] = _coerce_scalar(mm.group(2))
                    i += 1
                    while i < len(lines):
                        ln2 = lines[i]
                        if ln2.strip() == "" or ln2.lstrip().startswith("#"):
                            i += 1
                            continue
                        if ln2.startswith("    ") or ln2.startswith("\t"):
                            cont = ln2.lstrip()
                            mm2 = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$", cont)
                            if mm2:
                                item[mm2.group(1)] = _coerce_scalar(mm2.group(2))
                            i += 1
                        else:
                            break
                    block.append(item)
                else:
                    # Not handled (nested map without "-"); skip
                    i += 1
            result[key] = block
        else:
            result[key] = _coerce_scalar(val)
            i += 1
    return result


def _resolve_wikilink(link: str) -> Optional[Path]:
    """[[name]] or [[path/name]] -> file under knowledge-base/wiki/."""
    if not isinstance(link, str):
        return None
    m = re.match(r"\s*\[\[(.+?)\]\]\s*", link)
    if not m:
        return None
    target = m.group(1).strip()
    # Strip optional alias: [[name|alias]]
    target = target.split("|", 1)[0].strip()
    # Try multiple resolutions: analyses/<name>.md, manifests/<name>.md, plain
    candidates = [
        ANALYSES_DIR / f"{target}.md",
        _PROJECT_ROOT / "knowledge-base" / "wiki" / f"{target}.md",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def _parse_iso(s: str) -> Optional[datetime]:
    if not isinstance(s, str):
        return None
    s2 = s.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s2)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


# ─────────────────────────────────────────────────────────────────
# Strategy validity (reuse demo_trader parsing)
# ─────────────────────────────────────────────────────────────────


def _load_known_strategies() -> set:
    src = DEMO_TRADER.read_text()
    forced = _parse_simple_set(src, "_FORCE_DEMOTED")
    # QUALIFIED_TYPES is a frozenset literal in app.py / demo_trader; try both.
    qualified = _parse_simple_set(src, "QUALIFIED_TYPES")
    if not qualified:
        qualified = _parse_frozenset(src, "QUALIFIED_TYPES")
    if not qualified:
        # Fall back to scanning app.py
        app_py = _PROJECT_ROOT / "app.py"
        if app_py.exists():
            asrc = app_py.read_text()
            qualified = _parse_frozenset(asrc, "QUALIFIED_TYPES")
            if not qualified:
                qualified = _parse_simple_set(asrc, "QUALIFIED_TYPES")
    return forced | qualified


# ─────────────────────────────────────────────────────────────────
# Linter
# ─────────────────────────────────────────────────────────────────


def lint(path: Path) -> dict:
    text = path.read_text()
    yaml_text = _extract_yaml_block(text)
    if not yaml_text:
        return {
            "findings": [{"severity": "error", "rule": "E0", "path": str(path),
                          "message": "no YAML block found (expected ```yaml fenced block or front matter)"}],
            "summary": {"errors": 1, "warnings": 0, "info": 0},
        }

    try:
        data = _yaml_load(yaml_text) or {}
    except Exception as e:
        return {
            "findings": [{"severity": "error", "rule": "E0", "path": str(path),
                          "message": f"YAML parse error: {e}"}],
            "summary": {"errors": 1, "warnings": 0, "info": 0},
        }

    findings = []

    # Top-level fields
    edges = data.get("edges", [])
    if not isinstance(edges, list):
        findings.append({"severity": "error", "rule": "E0",
                         "message": "edges must be a list"})
        edges = []

    updated_at_str = data.get("edges_updated_at")
    updated_at = _parse_iso(updated_at_str) if updated_at_str else None
    now = datetime.now(timezone.utc)
    if updated_at and (now - updated_at) > timedelta(days=STALE_DAYS):
        findings.append({
            "severity": "warning", "rule": "W1",
            "message": f"edges_updated_at is {(now - updated_at).days} days old (>{STALE_DAYS})",
        })

    # Per-edge checks
    known_strategies = _load_known_strategies()
    seen = set()
    for i, edge in enumerate(edges):
        if not isinstance(edge, dict):
            findings.append({"severity": "error", "rule": "E0",
                             "message": f"edges[{i}] is not a mapping"})
            continue
        loc = f"edges[{i}] {edge.get('strategy', '?')}×{edge.get('cell', '?')}"

        # Duplicate
        key = (edge.get("strategy"), edge.get("cell"))
        if key in seen:
            findings.append({"severity": "error", "rule": "E0",
                             "message": f"{loc}: duplicate (strategy, cell) pair"})
        seen.add(key)

        # E5 strategy-validity
        s = edge.get("strategy")
        if known_strategies and s not in known_strategies:
            findings.append({
                "severity": "error", "rule": "E5",
                "message": f"{loc}: strategy '{s}' not in _FORCE_DEMOTED ∪ QUALIFIED_TYPES",
            })

        # E4 cell-validity
        c = edge.get("cell", "")
        parts = c.split("__")
        if len(parts) != 3:
            findings.append({"severity": "error", "rule": "E4",
                             "message": f"{loc}: cell '{c}' must have 3 parts joined by '__'"})
        else:
            r, v, sess = parts
            if r not in ACTIVE_REGIMES:
                findings.append({"severity": "error", "rule": "E4",
                                 "message": f"{loc}: regime '{r}' not in {sorted(ACTIVE_REGIMES)}"})
            if v not in VOL_BUCKETS:
                findings.append({"severity": "error", "rule": "E4",
                                 "message": f"{loc}: vol '{v}' not in {sorted(VOL_BUCKETS)}"})
            if sess not in SESSIONS:
                findings.append({"severity": "error", "rule": "E4",
                                 "message": f"{loc}: session '{sess}' not in {sorted(SESSIONS)}"})

        # status / routing values
        status = edge.get("status")
        routing = edge.get("routing")
        bonf = edge.get("bonferroni_passed", False)
        if status not in VALID_STATUS:
            findings.append({"severity": "error", "rule": "E0",
                             "message": f"{loc}: status '{status}' not in {sorted(VALID_STATUS)}"})
        if routing not in VALID_ROUTING:
            findings.append({"severity": "error", "rule": "E0",
                             "message": f"{loc}: routing '{routing}' not in {sorted(VALID_ROUTING)}"})

        # E3 routing-status-mismatch
        if routing == "BLOCK" and status != "REJECT":
            findings.append({"severity": "error", "rule": "E3",
                             "message": f"{loc}: routing=BLOCK requires status=REJECT (got {status})"})
        if routing in ("KELLY_HALF", "KELLY_FULL") and status != "SURVIVOR":
            findings.append({"severity": "error", "rule": "E3",
                             "message": f"{loc}: routing={routing} requires status=SURVIVOR (got {status})"})
        if status in ("SURVIVOR", "REJECT") and not bonf:
            findings.append({"severity": "error", "rule": "E3",
                             "message": f"{loc}: status={status} requires bonferroni_passed=true"})

        # E1 broken-source
        for field in ("source_prereg", "source_result"):
            link = edge.get(field, "")
            if not link:
                findings.append({"severity": "error", "rule": "E1",
                                 "message": f"{loc}: {field} missing"})
                continue
            resolved = _resolve_wikilink(link)
            if resolved is None:
                findings.append({"severity": "error", "rule": "E1",
                                 "message": f"{loc}: {field} '{link}' does not resolve"})

        # E2 expired
        exp_str = edge.get("expires_at")
        exp = _parse_iso(exp_str) if exp_str else None
        if exp is not None and exp < now:
            findings.append({"severity": "error", "rule": "E2",
                             "message": f"{loc}: expires_at {exp_str} < now"})

        # W2 source-divergence (best-effort: just check that source_result file
        # mentions the strategy & cell)
        sr_link = edge.get("source_result", "")
        sr_path = _resolve_wikilink(sr_link)
        if sr_path is not None:
            try:
                content = sr_path.read_text()
                if s and s not in content:
                    findings.append({
                        "severity": "warning", "rule": "W2",
                        "message": f"{loc}: source_result file does not mention strategy '{s}'",
                    })
                if c and c not in content:
                    findings.append({
                        "severity": "warning", "rule": "W2",
                        "message": f"{loc}: source_result file does not mention cell '{c}'",
                    })
            except Exception:
                pass

    summary = {
        "errors": sum(1 for f in findings if f["severity"] == "error"),
        "warnings": sum(1 for f in findings if f["severity"] == "warning"),
        "info": sum(1 for f in findings if f["severity"] == "info"),
        "edges_count": len(edges),
    }
    return {"findings": findings, "summary": summary}


def _format_text(report: dict, path: str) -> str:
    out = [f"EDGE.md lint report for {path}"]
    s = report["summary"]
    out.append(f"  edges: {s.get('edges_count', 0)}  "
               f"errors: {s['errors']}  warnings: {s['warnings']}  info: {s['info']}")
    for f in report["findings"]:
        sev = f["severity"].upper()
        out.append(f"  [{sev}] {f.get('rule','?')}: {f['message']}")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file", nargs="?",
                    default=str(_PROJECT_ROOT / "knowledge-base" / "wiki"
                                / "manifests" / "EDGE.md"))
    ap.add_argument("--check", action="store_true",
                    help="exit 1 on errors (CI/pre-commit)")
    ap.add_argument("--format", choices=("text", "json"), default="text")
    args = ap.parse_args()

    path = Path(args.file)
    if not path.exists():
        print(f"error: {path} not found", file=sys.stderr)
        return 1

    report = lint(path)

    if args.format == "json":
        print(json.dumps(report, indent=2, default=str))
    else:
        print(_format_text(report, str(path)))

    if args.check and report["summary"]["errors"] > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
