"""Run one retention batch using the configured server database."""

from __future__ import annotations

import argparse
import asyncio
import json

from mental_health_api.config import Settings
from mental_health_api.database.engine import create_engine, create_session_factory
from mental_health_api.privacy.retention_worker import RetentionWorker


async def _run_once() -> int:
    settings = Settings()
    engine = create_engine(settings)
    factory = create_session_factory(engine)
    try:
        async with factory() as session:
            report = await RetentionWorker(session).run_once()
        print(json.dumps({**report.__dict__, "total_deleted": report.total_deleted}, sort_keys=True))
        return 0
    finally:
        await engine.dispose()


async def _run(interval_seconds: int, once: bool) -> int:
    while True:
        await _run_once()
        if once:
            return 0
        await asyncio.sleep(interval_seconds)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval-seconds", type=int, default=300)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    if args.interval_seconds < 30:
        parser.error("interval must be at least 30 seconds")
    return asyncio.run(_run(args.interval_seconds, args.once))


if __name__ == "__main__":
    raise SystemExit(main())
