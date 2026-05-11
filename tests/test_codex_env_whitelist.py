from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INJECTOR = ROOT / "tools" / "codex_env_inject.sh"


def run_inject(tmp_path: Path, command: str) -> subprocess.CompletedProcess[str]:
    env = {"PATH": os.environ.get("PATH", "")}
    script = "\n".join(
        [
            "set -euo pipefail",
            f"export CODEX_ENV_ROOT={shlex.quote(str(tmp_path))}",
            f"export CODEX_ENV_WHITELIST_FILE={shlex.quote(str(tmp_path / 'whitelist.txt'))}",
            f"export CODEX_ENV_FILE={shlex.quote(str(tmp_path / '.env'))}",
            f"source {shlex.quote(str(INJECTOR))}",
            command,
        ]
    )
    return subprocess.run(
        ["bash", "-c", script],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def write_env_files(tmp_path: Path, whitelist: str, env_text: str) -> None:
    (tmp_path / "whitelist.txt").write_text(whitelist, encoding="utf-8")
    (tmp_path / ".env").write_text(env_text, encoding="utf-8")


def test_whitelist_key_in_env_is_exported(tmp_path: Path) -> None:
    write_env_files(tmp_path, "MASSIVE_API_KEY\n", "MASSIVE_API_KEY=allowed-value\n")

    result = run_inject(tmp_path, 'printf "%s" "${MASSIVE_API_KEY-}"')

    assert result.returncode == 0
    assert result.stdout == "allowed-value"
    assert "[codex-env] injected: MASSIVE_API_KEY" in result.stderr


def test_non_whitelist_key_in_env_is_not_exported(tmp_path: Path) -> None:
    write_env_files(
        tmp_path,
        "MASSIVE_API_KEY\n",
        "MASSIVE_API_KEY=allowed-value\nOANDA_API_TOKEN=must-not-leak\n",
    )

    result = run_inject(tmp_path, 'if printenv OANDA_API_TOKEN; then exit 3; fi')

    assert result.returncode == 0
    assert "must-not-leak" not in result.stdout
    assert "must-not-leak" not in result.stderr


def test_whitelist_key_missing_from_env_is_noop(tmp_path: Path) -> None:
    write_env_files(tmp_path, "MASSIVE_API_KEY\n", "OTHER_KEY=value\n")

    result = run_inject(tmp_path, 'printf "%s" "${MASSIVE_API_KEY-unset}"')

    assert result.returncode == 0
    assert result.stdout == "unset"
    assert "injected: MASSIVE_API_KEY" not in result.stderr


def test_missing_whitelist_file_is_noop(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("MASSIVE_API_KEY=allowed-value\n", encoding="utf-8")

    result = run_inject(tmp_path, 'printf "%s" "ok"')

    assert result.returncode == 0
    assert result.stdout == "ok"
    assert result.stderr == ""


def test_missing_env_file_is_noop(tmp_path: Path) -> None:
    (tmp_path / "whitelist.txt").write_text("MASSIVE_API_KEY\n", encoding="utf-8")

    result = run_inject(tmp_path, 'printf "%s" "ok"')

    assert result.returncode == 0
    assert result.stdout == "ok"
    assert result.stderr == ""


def test_malformed_whitelist_lines_warn_and_skip(tmp_path: Path) -> None:
    write_env_files(
        tmp_path,
        "SOME-KEY\n1KEY\nGOOD_KEY\n",
        "SOME-KEY=bad\n1KEY=bad\nGOOD_KEY=good\n",
    )

    result = run_inject(
        tmp_path,
        'printf "%s:%s:%s" "${SOME_KEY-unset}" "${KEY1-unset}" "${GOOD_KEY-}"',
    )

    assert result.returncode == 0
    assert result.stdout == "unset:unset:good"
    assert "WARN: ignoring malformed whitelist key 'SOME-KEY'" in result.stderr
    assert "WARN: ignoring malformed whitelist key '1KEY'" in result.stderr
    assert "bad" not in result.stdout
    assert "bad" not in result.stderr


def test_secret_value_is_not_logged(tmp_path: Path) -> None:
    secret = "SECRET_VALUE_SHOULD_NOT_APPEAR"
    write_env_files(tmp_path, "MASSIVE_API_KEY\n", f"MASSIVE_API_KEY={secret}\n")

    result = run_inject(tmp_path, 'printf "%s" "done"')

    assert result.returncode == 0
    assert result.stdout == "done"
    assert secret not in result.stderr
    assert "len=30" in result.stderr
