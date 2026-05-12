"""factory: env-var → broker mapping. Fails closed on partial config."""
from __future__ import annotations

from cfd_trader.broker import NullBroker
from cfd_trader.broker.mt5_remote import MT5RemoteBroker
from cfd_trader.broker.factory import (
    ENV_SHIM_SECRET,
    ENV_SHIM_URL,
    ENV_TIMEOUT_S,
    broker_status_from_env,
    build_broker_from_env,
)


def test_empty_env_returns_null_broker() -> None:
    assert isinstance(build_broker_from_env({}), NullBroker)


def test_url_only_falls_back_to_null_broker() -> None:
    """Fail-closed: if secret is missing, do NOT silently send unsigned."""
    env = {ENV_SHIM_URL: "https://mt5.example.test"}
    assert isinstance(build_broker_from_env(env), NullBroker)


def test_secret_only_falls_back_to_null_broker() -> None:
    env = {ENV_SHIM_SECRET: "x"}
    assert isinstance(build_broker_from_env(env), NullBroker)


def test_full_config_returns_mt5_remote_broker() -> None:
    env = {
        ENV_SHIM_URL: "https://mt5.example.test",
        ENV_SHIM_SECRET: "secretvalue",
    }
    b = build_broker_from_env(env)
    assert isinstance(b, MT5RemoteBroker)


def test_timeout_override_parsed() -> None:
    env = {
        ENV_SHIM_URL: "https://mt5.example.test",
        ENV_SHIM_SECRET: "s",
        ENV_TIMEOUT_S: "12.5",
    }
    b = build_broker_from_env(env)
    assert isinstance(b, MT5RemoteBroker)
    assert b._timeout_s == 12.5


def test_invalid_timeout_falls_back_to_default() -> None:
    env = {
        ENV_SHIM_URL: "https://mt5.example.test",
        ENV_SHIM_SECRET: "s",
        ENV_TIMEOUT_S: "not-a-number",
    }
    b = build_broker_from_env(env)
    assert isinstance(b, MT5RemoteBroker)
    assert b._timeout_s == MT5RemoteBroker.DEFAULT_TIMEOUT_S


def test_status_dict_when_configured_does_not_leak_secret() -> None:
    env = {
        ENV_SHIM_URL: "https://mt5.example.test",
        ENV_SHIM_SECRET: "supersecret1234",
    }
    status = broker_status_from_env(env)
    assert status["configured"] is True
    assert status["kind"] == "mt5_remote"
    assert status["shim_url"] == "https://mt5.example.test"
    # Tail only; the full secret must not appear anywhere.
    assert status["secret_tail"] == "…1234"
    assert "supersecret1234" not in str(status)


def test_status_dict_when_not_configured_reports_reason() -> None:
    assert broker_status_from_env({})["configured"] is False
    assert "not set" in broker_status_from_env({})["reason"]

    only_url = {ENV_SHIM_URL: "https://x"}
    assert broker_status_from_env(only_url)["configured"] is False
    assert ENV_SHIM_SECRET in broker_status_from_env(only_url)["reason"]
