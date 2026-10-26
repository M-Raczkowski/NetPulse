from pydantic import BaseModel, Field, AwareDatetime, model_validator


class MeasurementBase(BaseModel):
    agent_id: str = Field(min_length = 1, max_length = 100 )
    target: str = Field(min_length = 1, max_length = 500)
    timestamp_utc: AwareDatetime
    window_seconds: int = Field(gt=0)
    packets_sent: int = Field(gt=0)
    packets_received: int = Field(ge=0)
    rtt_avg_ms: float | None = Field(default = None, ge=0)
    rtt_min_ms: float | None = Field(default = None, ge=0)
    rtt_max_ms: float | None = Field(default = None, ge=0)
    jitter_ms: float | None = Field(default = None, ge=0)
    throughput_mbps: float | None = Field(default = None, ge=0)


class MeasurementCreate(MeasurementBase):
    @model_validator(mode="after")
    def check_received_not_above_sent(self):
        if self.packets_received > self.packets_sent:
            raise ValueError("packets received cannot be greater than packets sent")
        return self

class MeasurementResponse(MeasurementBase):
    id: int
    model_config = {"from_attributes": True}