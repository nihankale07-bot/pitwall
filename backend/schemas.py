
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, ConfigDict


# ============================================================
# OPTIMIZATION REQUEST
# ============================================================

class OptimizeRequest(BaseModel):

    model_config = ConfigDict(extra="forbid")

    session_key: int = Field(gt=0)
    target_driver: int = Field(gt=0)
    decision_lap: int = Field(gt=0)
    race_length: Optional[int] = Field(default=None, gt=1)

    track_mode: Literal["causal", "replay"] = "causal"

    pit_loss: float = Field(default=22.0, ge=0)
    max_stops: int = Field(default=2, ge=0)
    max_candidates: int = Field(default=95, gt=0)


# ============================================================
# OPTIMIZATION RESPONSE
# ============================================================

class OptimizationResponse(BaseModel):

    session_key: int
    target_driver: int
    decision_lap: int
    race_length: int
    track_mode: str

    model: Dict[str, Any]

    recommendation: Dict[str, Any]

    ranking: List[Dict[str, Any]]

    best_replay: Dict[str, Any]

    projected_classification: Optional[List[Dict[str, Any]]] = None
