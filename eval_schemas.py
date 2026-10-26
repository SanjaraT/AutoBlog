"""
Schema for the independent LLM judge used by the eval harness.

"""

from pydantic import BaseModel, Field


class QualityJudgment(BaseModel):
    clarity: int = Field(..., ge=1, le=5, description="1=confusing/hard to follow, 5=exceptionally clear")
    depth: int = Field(..., ge=1, le=5, description="1=superficial/generic, 5=substantive and specific to the topic")
    structure: int = Field(..., ge=1, le=5, description="1=disorganized/repetitive, 5=logical flow, no redundancy")
    accuracy_confidence: int = Field(
        ...,
        ge=1,
        le=5,
        description="1=contains claims that seem fabricated or unsupported, 5=claims seem well-grounded",
    )
    overall: int = Field(..., ge=1, le=5, description="Holistic score: would a developer reader find this genuinely useful?")
    rationale: str = Field(..., description="2-3 sentences justifying the scores, mentioning any specific weaknesses")