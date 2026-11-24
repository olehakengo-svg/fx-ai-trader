"""sentry_boot の fail-open pin (rule:R3、2026-11-24).

再現した事故: sentry-sdk 3.0.0 (2026-11-23 公開) が `profiles_sample_rate` を
削除 → `sentry_sdk.init(...)` が `TypeError: Unknown option 'profiles_sample_rate'`
→ gunicorn exit 1 → Render deploy `update_failed` (PR #384、2026-11-24 10:22Z)。
CI は SENTRY_DSN が空で init 経路を通らないので、ここで init_fn を差し替えて
経路そのものを pin する。
"""
from __future__ import annotations

import inspect
import os
import re

import pytest

from modules import sentry_boot

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _env(**over):
    base = {"SENTRY_DSN": "https://k@o.ingest.sentry.io/1", "RENDER": "true",
            "RENDER_GIT_COMMIT": "3df2981d4e4be5cdc92aff4e16b768a08b372cc7"}
    base.update(over)
    return base


# --------------------------------------------------------------------------- init()
def test_unknown_profiles_option_is_dropped_and_init_succeeds():
    """3.0.0 の実エラー本文をそのまま再現: 1 回目 TypeError → kwarg を外して 2 回目で通る。"""
    calls = []

    def fake_init(**kw):
        calls.append(dict(kw))
        if "profiles_sample_rate" in kw:
            raise TypeError("Unknown option 'profiles_sample_rate'")

    logs = []
    kwargs = sentry_boot.build_kwargs(_env(), "dsn", [])
    used = sentry_boot.init(fake_init, kwargs, log=logs.append)
    assert len(calls) == 2
    assert "profiles_sample_rate" in calls[0] and "profiles_sample_rate" not in calls[1]
    assert used == calls[1] and used["traces_sample_rate"] == 0.1 and used["dsn"] == "dsn"
    assert any("dropping unsupported option 'profiles_sample_rate'" in m for m in logs)


def test_sdk_2x_path_is_unchanged_single_call():
    """2.x では従来どおり 1 回で全 kwarg が渡る (本番挙動を変えない)。"""
    calls = []
    kwargs = sentry_boot.build_kwargs(_env(SENTRY_PROFILES_SAMPLE_RATE="0.25"), "dsn", ["flask"])
    used = sentry_boot.init(lambda **kw: calls.append(dict(kw)), kwargs)
    assert len(calls) == 1 and used == kwargs
    assert used["profiles_sample_rate"] == 0.25 and used["integrations"] == ["flask"]
    assert used["release"] == "3df2981d4e4b" and used["environment"] == "production"


def test_typeerror_without_option_name_falls_back_in_fixed_order():
    """本文からオプション名が取れない TypeError でも、既知の候補を順に外して試す。"""
    seen = []

    def fake_init(**kw):
        seen.append(set(kw))
        if "profiles_sample_rate" in kw or "traces_sample_rate" in kw:
            raise TypeError("init() got an unexpected keyword argument")

    used = sentry_boot.init(fake_init, sentry_boot.build_kwargs(_env(), "dsn", []))
    assert "profiles_sample_rate" not in used and "traces_sample_rate" not in used
    assert "send_default_pii" in used  # 必要以上には外さない
    assert len(seen) == 3


def test_non_typeerror_is_logged_and_swallowed():
    """ネットワーク/設定由来の例外でも本体 (取引エンジン) を落とさない = fail-open。"""
    def fake_init(**kw):
        raise RuntimeError("DSN unreachable")

    logs = []
    used = sentry_boot.init(fake_init, sentry_boot.build_kwargs(_env(), "dsn", []), log=logs.append)
    assert used == {} and any("gave up" in m and "RuntimeError" in m for m in logs)


def test_retry_budget_is_bounded():
    """常に TypeError を返す init でも無限ループしない。"""
    def fake_init(**kw):
        raise TypeError("Unknown option 'dsn'")

    logs = []
    used = sentry_boot.init(fake_init, {"dsn": "x"}, log=logs.append, max_retries=2)
    assert used == {} and logs[-1].startswith("[sentry_boot] init gave up")


# --------------------------------------------------------------------------- boot()
def test_boot_is_noop_without_dsn():
    assert sentry_boot.boot({"RENDER": "true"}) == {}
    assert sentry_boot.boot({"SENTRY_DSN": "   "}) == {}


# --------------------------------------------------------------------------- pins
def test_requirements_pins_sentry_sdk_below_3():
    """恒久策の一次防御 = 上限 pin。緩めるときは本 test と app の kwargs を 3.x API で見直す。"""
    with open(os.path.join(ROOT, "requirements.txt"), encoding="utf-8") as f:
        lines = [ln.strip() for ln in f if ln.strip().lower().startswith("sentry-sdk")]
    assert len(lines) == 1, lines
    spec = lines[0].split("#", 1)[0].strip()
    assert re.search(r"<\s*3(\.0(\.0)?)?\b", spec), spec


def test_app_kwargs_are_accepted_by_installed_sdk_or_droppable():
    """インストール済み sentry-sdk の init シグネチャと kwargs を突合する。

    2.x: 全 kwarg が受理される。3.x に上げた日: 受理されない kwarg は
    `_DROPPABLE_IN_ORDER` に載っていなければ本 test が落ちる (= 黙って本番で
    TypeError にならない)。
    """
    pytest.importorskip("sentry_sdk")
    from sentry_sdk.consts import ClientConstructor

    params = set(inspect.signature(ClientConstructor.__init__).parameters)
    kwargs = sentry_boot.build_kwargs(_env(), "dsn", [])
    unsupported = {k for k in kwargs if k not in params}
    assert unsupported <= set(sentry_boot._DROPPABLE_IN_ORDER), unsupported
