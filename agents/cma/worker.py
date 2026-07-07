"""Self-hosted tool worker. Runs on YOUR machine; executes all agent tool calls
(bash/read/write/edit/glob/grep) locally with workdir = this repo checkout.

Run this FIRST and keep it running, in its own terminal:
    export ANTHROPIC_ENVIRONMENT_KEY=sk-ant-oat01-...   # Console -> environment page
    export ANTHROPIC_ENVIRONMENT_ID=env_...             # from setup.sh
    python agents/cma/worker.py
"""
import asyncio
import os

from anthropic import AsyncAnthropic
from anthropic.lib.environments import EnvironmentWorker

WORKDIR = os.environ.get("FXAI_WORKDIR", "/Users/jg-n-012/test/fx-ai-trader")


async def main() -> None:
    key = os.environ["ANTHROPIC_ENVIRONMENT_KEY"]
    async with AsyncAnthropic(auth_token=key) as client:
        await EnvironmentWorker(
            client,
            environment_id=os.environ["ANTHROPIC_ENVIRONMENT_ID"],
            environment_key=key,
            workdir=WORKDIR,
            # The file tools (read/write/edit/glob) confine to workdir and
            # REJECT absolute paths when unrestricted_paths=False (the default).
            # Agents emit absolute paths by convention, so every Write/Edit was
            # rejected and the dev agent fell back to bash heredocs. bash here is
            # already unrestricted and workdir is this repo on the user's own
            # machine, so confining only the file tools adds no real safety —
            # enable absolute paths so read/write/edit work natively.
            unrestricted_paths=True,
        ).run()


if __name__ == "__main__":
    asyncio.run(main())
