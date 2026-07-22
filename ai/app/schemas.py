from typing import Literal

from pydantic import BaseModel, Field


RiskLevel = Literal["HIGH", "MEDIUM", "LOW", "SAFE"]


class LegalReference(BaseModel):
    law_name: str
    article_number: str
    content: str
    source_url: str | None = None


class RiskClause(BaseModel):
    clause_type: str
    title: str
    original_text: str
    risk_level: RiskLevel
    reason: str
    recommendation: str
    legal_references: list[LegalReference] = Field(default_factory=list)


class AnalysisResponse(BaseModel):
    contract_id: int
    summary: str
    overall_risk_level: RiskLevel
    overall_score: int = Field(ge=0, le=100)
    clauses: list[RiskClause]
    warnings: list[str]
