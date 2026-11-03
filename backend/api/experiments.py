import os
from pathlib import Path

from fastapi import APIRouter

from backend.schemas.experiment import ExperimentResponse
from backend.services.experiments import load_experiments

RESULTS_DIR = Path(os.getenv("EXPERIMENTS_DIR", Path(__file__).resolve().parents[2] / "testbed" / "results"))

router = APIRouter(prefix="/experiments", tags=["experiments"])


@router.get("", response_model=list[ExperimentResponse])
def get_experiments():
    return load_experiments(RESULTS_DIR)
