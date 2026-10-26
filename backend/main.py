from fastapi import FastAPI
from backend.api.measurements import router as measurements_router

app = FastAPI(title = "NetPulse")
app.include_router(measurements_router)


