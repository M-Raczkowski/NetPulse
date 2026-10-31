from fastapi import FastAPI
from backend.api.measurements import router as measurements_router
from backend.api.alerts import router as alerts_router

app = FastAPI(title="NetPulse")
app.include_router(measurements_router)
app.include_router(alerts_router)
