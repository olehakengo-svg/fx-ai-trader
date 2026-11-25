"""requirements.txt の上限 pin を機械で固定する (rule:R3、2026-11-25).

背景: 2026-11-24、`sentry-sdk[flask]>=2.0.0` (上限なし) が PyPI 公開 25 時間後の
3.0.0 を Render build で解決し、docs-only PR の deploy が `update_failed` になった
([[lesson-unbounded-dep-pin-deploy-fail-2026-11-24]])。下限だけの行は
「PyPI の公開タイミングで本番の版が決まる」宣言なので、全行に上限を付け、
上限 = 本番が最後に解決した版の次メジャーであることをここで pin する。

棚卸し表: knowledge-base/wiki/analyses/runtime-dep-upper-bound-audit-2026-11-25.md
"""
from __future__ import annotations

import importlib.metadata
import os
import re

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REQ_PATH = os.path.join(ROOT, "requirements.txt")

# Render build bld-dc2mis6q1p3s73dkjmi0 (2026-11-24T10:40:20Z、Python 3.11.0) の
# 「Successfully installed」行から転記した、本番が最後に解決した版。
# 上限 pin を上げる PR は、新しい build log の値でこの表も更新する。
RENDER_RESOLVED_2026_11_24 = {
    "flask": "3.1.3",
    "gunicorn": "27.0.1",
    "yfinance": "1.8.0",
    "pandas": "3.1.1",
    "pyarrow": "26.0.1",
    "numpy": "2.4.6",
    "scipy": "1.17.1",
    "ta": "0.11.0",
    "requests": "2.34.2",
    "pytest": "9.2.0",
    "flake8": "7.5.0",
    "sentry-sdk": "2.76.0",
    "jpholiday": "1.0.3",
    "apscheduler": "3.11.3",
    "python-dotenv": "1.2.4",
}

_LINE_RE = re.compile(
    r"^(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)(?P<extras>\[[^\]]+\])?"
    r"(?P<spec>[^#]*)$"
)


def _requirement_lines():
    with open(REQ_PATH, encoding="utf-8") as f:
        for raw in f:
            line = raw.split("#", 1)[0].strip()
            if not line:
                continue
            m = _LINE_RE.match(line)
            assert m, f"unparseable requirement line: {raw!r}"
            name = m.group("name").lower().replace("_", "-")
            spec = m.group("spec").replace(" ", "")
            yield name, spec, raw.rstrip("\n")


def _upper_major(spec: str):
    m = re.search(r"<(\d+)(?:\.\d+)*(?![.\d])", spec)
    return int(m.group(1)) if m else None


def _lower_version(spec: str):
    m = re.search(r">=(\d+(?:\.\d+)*)", spec)
    return m.group(1) if m else None


def _vtuple(v: str):
    return tuple(int(x) for x in re.findall(r"\d+", v)[:3])


def test_every_runtime_line_has_an_exclusive_upper_bound():
    """`>=` だけの行を 1 本も残さない (sentry-sdk 3.0.0 型の再発防止)。"""
    missing = [raw for _, spec, raw in _requirement_lines()
               if _upper_major(spec) is None]
    assert not missing, f"lines without '<N' upper bound: {missing}"


def test_upper_bound_is_next_major_above_last_render_resolution():
    """上限 = 本番が最後に解決した版の次メジャー (= 解決結果が変わらない R3 pin)。"""
    seen = set()
    for name, spec, raw in _requirement_lines():
        assert name in RENDER_RESOLVED_2026_11_24, (
            f"{name} is not in the audit table; "
            "add it with the Render build value")
        seen.add(name)
        resolved = _vtuple(RENDER_RESOLVED_2026_11_24[name])
        upper = _upper_major(spec)
        assert upper == resolved[0] + 1, (
            f"{raw}: upper bound <{upper} must be "
            f"resolved major {resolved[0]} + 1")
        lower = _lower_version(spec)
        assert lower is not None, f"{raw}: lower bound '>=' missing"
        assert _vtuple(lower) <= resolved, (
            f"{raw}: lower bound above resolved version")
    diff = seen ^ set(RENDER_RESOLVED_2026_11_24)
    assert not diff, f"audit table and requirements.txt disagree: {diff}"


def test_installed_versions_satisfy_the_pins_where_installed():
    """この環境に入っている版が pin の範囲内にある (CI = Render と同じ fresh resolve)。"""
    checked = 0
    for name, spec, raw in _requirement_lines():
        try:
            installed = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            continue
        upper = _upper_major(spec)
        lower = _lower_version(spec)
        iv = _vtuple(installed)
        assert iv[0] < upper, (
            f"{raw}: installed {installed} violates upper bound")
        assert iv >= _vtuple(lower), (
            f"{raw}: installed {installed} below lower bound")
        checked += 1
    if checked == 0:
        pytest.skip("no requirement is installed in this interpreter")
