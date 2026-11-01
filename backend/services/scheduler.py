from backend.db.session import AsyncSessionLocal
import logging
import asyncio
from backend.services.engine import run_detection

logger = logging.getLogger(__name__)


async def detection_loop(interval_seconds: int = 60) -> None:
    while True:
        try:
            async with AsyncSessionLocal() as db:
                await run_detection(db)
        except Exception:
            logger.exception("detection run failed")
        await asyncio.sleep(interval_seconds)
