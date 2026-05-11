#!/usr/bin/env bash

if [[ -z "${ROOT:-}" ]]; then
  ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fi

inject_codex_whitelist_env() {
  local root="${CODEX_ENV_ROOT:-$ROOT}"
  local whitelist_file="${CODEX_ENV_WHITELIST_FILE:-$root/tools/codex-env-whitelist.txt}"
  local env_file="${CODEX_ENV_FILE:-$root/.env}"

  if [[ ! -f "$whitelist_file" ]]; then return 0; fi
  if [[ ! -f "$env_file" ]]; then return 0; fi

  local line key val
  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line%%#*}"
    key="$(printf "%s" "$line" | tr -d '[:space:]')"
    [[ -z "$key" ]] && continue

    if ! [[ "$key" =~ ^[A-Z_][A-Z0-9_]*$ ]]; then
      echo "[codex-env] WARN: ignoring malformed whitelist key '$key'" >&2
      continue
    fi

    val="$(
      awk -v key="$key" '
        index($0, key "=") == 1 {
          val = substr($0, length(key) + 2)
        }
        END {
          if (val != "") print val
        }
      ' "$env_file" | sed -e 's/^"//;s/"$//' -e "s/^'//;s/'\$//"
    )"
    if [[ -n "$val" ]]; then
      export "$key=$val"
      echo "[codex-env] injected: $key (len=${#val})" >&2
    fi
  done < "$whitelist_file"
}

if [[ "${CODEX_ENV_INJECT_DISABLE_AUTO:-0}" != "1" ]]; then
  inject_codex_whitelist_env
fi
