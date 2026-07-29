from typing import Literal

from pydantic import BaseModel, Field


RiskLevel = Literal["HIGH", "MEDIUM", "LOW", "SAFE"]


class LegalReference(BaseModel):
    law_name: str
    article_number: str
    content: str
    source_url: str | None = None


class TextBox(BaseModel):
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    width: float = Field(gt=0, le=1)
    height: float = Field(gt=0, le=1)


class SourceLocation(BaseModel):
    page: int = Field(ge=1)
    text: str
    boxes: list[TextBox] = Field(default_factory=list)


class SemanticEvidence(BaseModel):
    subject: str | None = None
    action: str | None = None
    target: str | None = None
    negated: bool = False
    conditional: bool = False


class RiskClause(BaseModel):
    clause_type: str
    title: str
    original_text: str
    risk_level: RiskLevel
    reason: str
    recommendation: str
    replacement_text: str | None = None
    confidence: float = Field(default=1.0, ge=0, le=1)
    review_required: bool = False
    semantic: SemanticEvidence | None = None
    location: SourceLocation | None = None
    legal_references: list[LegalReference] = Field(default_factory=list)


class ChecklistItem(BaseModel):
    code: str
    title: str
    status: Literal["COMPLIANT", "RISK", "MISSING", "REVIEW"]
    evidence: str | None = None
    location: SourceLocation | None = None
    legal_reference: LegalReference


class AnalysisResponse(BaseModel):
    contract_id: int
    summary: str
    overall_risk_level: RiskLevel
    overall_score: int = Field(ge=0, le=100)
    review_required_count: int = Field(default=0, ge=0)
    clauses: list[RiskClause]
    checklist: list[ChecklistItem] = Field(default_factory=list)
    warnings: list[str]


class QuestionResponse(BaseModel):
    answer: str
    contract_sources: list[SourceLocation] = Field(default_factory=list)
    legal_references: list[LegalReference] = Field(default_factory=list)
    warning: str


class LegalChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=8000)


class LegalChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=4000)
    history: list[LegalChatMessage] = Field(default_factory=list, max_length=12)


class LegalChatResponse(BaseModel):
    answer: str
    legal_references: list[LegalReference] = Field(default_factory=list)
    warning: str
    insufficient_evidence: bool = False
