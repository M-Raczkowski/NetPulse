from fastapi import FastAPI
from backend.api.measurements import router as measurements_router
from backend.api.alerts import router as alerts_router
from backend.services.scheduler import detection_loop
from contextlib import asynccontextmanager
import asyncio
import logging
from pathlib import Path
from fastapi.staticfiles import StaticFiles


@asynccontextmanager
async def lifespan(app: FastAPI):
    detection_loop_task = asyncio.create_task(detection_loop())
    yield
    detection_loop_task.cancel()
    try:
        await detection_loop_task
    except asyncio.CancelledError:
        pass


logging.basicConfig(level=logging.INFO)
app = FastAPI(title="NetPulse", lifespan=lifespan)
app.include_router(measurements_router)
app.include_router(alerts_router)
app.mount("/panel", StaticFiles(directory=Path(__file__).parent / "static", html=True))
