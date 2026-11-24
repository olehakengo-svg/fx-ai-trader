"""Sentry 初期化の fail-open ブート (rule:R3、2026-11-24).

なぜ分離したか — 2026-11-24 10:22Z、PR #384 (docs + registry のみ) の Render
deploy で ``pip install -r requirements.txt`` が **sentry-sdk 3.0.0** (2026-11-23
公開) を引き、``app.py`` 冒頭の ``sentry_sdk.init(profiles_sample_rate=...)`` が
``TypeError: Unknown option 'profiles_sample_rate'`` で gunicorn を exit 1 させた。
Render は deploy を ``update_failed`` にして前ビルド (PR #382) を再起動したので
本番は生き残ったが、(a) 市場開場中 (10:21:38Z SIGTERM → 10:22:5xZ 復帰) に
engine が ~80 秒落ち、(b) 修理するまで**以後の全 deploy が同じ理由で失敗する**
構造だった。CI は ``SENTRY_DSN`` が空なので init 経路を通らず、検知できない。

設計:
- 監視 (Sentry) は取引エンジンの**付属物**であり、その初期化失敗で本体を
  落としてはならない (fail-open)。``init`` は TypeError を「未知オプション」と
  読んで当該 kwarg を外し再試行し、それ以外の例外は記録して諦める。
- 依存側の恒久策は ``requirements.txt`` の上限 pin (``sentry-sdk[flask]<3``)。
  本モジュールは pin が外れた/緩んだ日の二重防御で、pin の代替ではない。
- 本番 (Render) の挙動は変えない: 2.x では従来どおり全 kwarg で 1 回で init
  が通る。
"""
from __future__ import annotations

import os
import re
from typing import Any, Callable, Mapping

_UNKNOWN_OPTION_PAT = re.compile(r"Unknown option '([^']+)'")

# sentry-sdk 3.x で削除/改名されたことが分かっている kwarg。TypeError の本文から
# 名前が取れないときの fallback 順序 (先頭から 1 つずつ外す)。
_DROPPABLE_IN_ORDER = ("profiles_sample_rate", "traces_sample_rate", "send_default_pii")


def build_kwargs(environ: Mapping[str, str], dsn: str, integrations: list[Any]) -> dict[str, Any]:
    """app.py が渡していた kwargs をそのまま組み立てる (値の既定は従来どおり)。"""
    return {
        "dsn": dsn,
        "integrations": integrations,
        "environment": environ.get("SENTRY_ENV", "production" if environ.get("RENDER") else "local"),
        "release": environ.get("RENDER_GIT_COMMIT", "unknown")[:12],
        "traces_sample_rate": float(environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
        "profiles_sample_rate": float(environ.get("SENTRY_PROFILES_SAMPLE_RATE", "0.0")),
        "send_default_pii": False,
    }


def _unknown_option(exc: BaseException, kwargs: Mapping[str, Any]) -> str | None:
    m = _UNKNOWN_OPTION_PAT.search(str(exc))
    if m and m.group(1) in kwargs:
        return m.group(1)
    for k in _DROPPABLE_IN_ORDER:
        if k in kwargs:
            return k
    return None


def init(init_fn: Callable[..., Any], kwargs: Mapping[str, Any],
         log: Callable[[str], Any] = print, max_retries: int = 3) -> dict[str, Any]:
    """``init_fn(**kwargs)`` を fail-open で呼ぶ。

    戻り値 = 実際に使った kwargs (``{}`` = 諦めた)。TypeError は「未知オプション」
    と読み、該当 kwarg を外して最大 ``max_retries`` 回まで再試行する。それ以外の
    例外は記録して ``{}`` を返す (本体は続行)。
    """
    current = dict(kwargs)
    for _ in range(max_retries + 1):
        try:
            init_fn(**current)
            return current
        except TypeError as exc:
            bad = _unknown_option(exc, current)
            if bad is None:
                log(f"[sentry_boot] init gave up (TypeError without droppable option): {exc}")
                return {}
            log(f"[sentry_boot] dropping unsupported option {bad!r} and retrying: {exc}")
            current.pop(bad, None)
        except Exception as exc:  # noqa: BLE001 — 監視の初期化失敗で本体を落とさない
            log(f"[sentry_boot] init gave up: {type(exc).__name__}: {exc}")
            return {}
    log("[sentry_boot] init gave up: retry budget exhausted")
    return {}


def boot(environ: Mapping[str, str] | None = None, log: Callable[[str], Any] = print) -> dict[str, Any]:
    """app.py 冒頭から呼ぶ入口。DSN が無ければ何もしない (CI / local と同じ)。"""
    env = os.environ if environ is None else environ
    dsn = (env.get("SENTRY_DSN") or "").strip()
    if not dsn:
        return {}
    try:
        import sentry_sdk  # noqa: PLC0415 — optional dependency
        from sentry_sdk.integrations.flask import FlaskIntegration  # noqa: PLC0415
    except ImportError:
        return {}
    return init(sentry_sdk.init, build_kwargs(env, dsn, [FlaskIntegration()]), log=log)
