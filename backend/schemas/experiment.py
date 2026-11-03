from pydantic import BaseModel, AwareDatetime


class ExperimentEvent(BaseModel):
    ts_utc: AwareDatetime
    event: str
    agent: str | None = None
    scenario: str | None = None
    repeat: int | None = None


class ExperimentResponse(BaseModel):
    name: str
    agents: list[str]
    started_utc: AwareDatetime
    finished_utc: AwareDatetime | None
    scenarios: list[str]
    repeats: int
    events: list[ExperimentEvent]
