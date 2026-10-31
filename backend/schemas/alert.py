from pydantic import BaseModel, AwareDatetime


class AlertResponse(BaseModel):
    id: int
    agent_id: str
    target: str
    metric: str
    detector: str
    opened_at: AwareDatetime
    closed_at: AwareDatetime | None
    value_at_open: float | None
    model_config = {"from_attributes": True}
