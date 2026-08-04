import os
import re
import logging
from typing import Literal, TypedDict

from langchain_ollama import ChatOllama
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from .analyzer import (
    analyze_contract, calculate_verified_risk, deduplicate_findings, is_negated_risk_text,
    reconcile_checklist_findings,
)
from .rag import LawRagService
from .schemas import AnalysisResponse, LegalReference, RiskClause, RiskLevel, SemanticEvidence
from .semantic import evaluate_candidate

logger = logging.getLogger(__name__)

class ClauseDecision(BaseModel):
    clause_type: str = Field(description="영문 대문자 위험 유형 코드")
    title: str
    original_text: str = Field(description="계약서에 실제로 존재하는 문구. 누락이면 '해당 조항 없음'")
    risk_level: RiskLevel
    reason: str
    recommendation: str = "해당 조항을 원문 및 관련 법령과 함께 다시 검토하세요."
    replacement_text: str | None = Field(default=None, description="계약서에 바로 적용할 수 있는 안전한 대체 조항")
    evidence_ids: list[str] = Field(default_factory=list)


class LlmDecision(BaseModel):
    summary: str = Field(description="핵심 계약 조건을 포함한 3~5문장 요약")
    overall_risk_level: RiskLevel
    overall_score: int = Field(ge=0, le=100)
    clauses: list[ClauseDecision] = Field(default_factory=list)


class AgentState(TypedDict, total=False):
    contract_id: int
    text: str
    contract_type: str
    baseline: AnalysisResponse
    evidence: list[dict]
    llm_decision: LlmDecision
    llm_error: str
    result: AnalysisResponse


SYSTEM_PROMPT = """당신은 LAWZIC의 계약서 위험 분석 AI입니다.
계약서와 검색된 법령 근거만 사용해 분석하세요.
- summary, title, reason, recommendation 등 사용자가 읽는 모든 문장은 반드시 한국어로만 작성하세요.
- 영어 문장이나 영어 제목을 절대 출력하지 마세요. clause_type 코드만 영문 대문자로 작성하세요.
- 계약서에 없는 문구를 인용하지 마세요.
- 법령 근거는 제공된 evidence_id만 선택하세요. 근거가 없으면 빈 배열로 두세요.
- 불리하거나 모호한 조항, 필수 조건 누락 가능성을 찾으세요.
- 계약서에 이미 충분히 명시된 사항을 다시 명시하라고 권고하지 마세요.
- 원문이 법적 요구사항을 충족하면 위험 조항으로 만들지 마세요.
- clauses 배열에는 실제 위험 또는 불리한 가능성이 있는 조항만 넣으세요. 계약서 종류, 업무 내용, 정상적으로 보장된 근로조건은 clauses에 넣지 마세요.
- 계약서에서 확인되는 서로 다른 위험 조항을 누락하지 말고 작성하세요. 같은 위험의 중복만 합치세요.
- 위험 조항에는 원문의 의미를 보완하는 구체적인 한국어 대체 문구를 작성하세요.
- 위험도는 높음, 중간, 낮음, 안전 중 하나로 작성하세요.
- 법률 자문처럼 단정하지 말고 검토 필요성과 이유를 설명하세요.
- 전체 위험 점수는 0~100입니다.
"""

EXPLICIT_RISK_MARKERS = (
    "무급", "지급하지", "지급하지 않는다", "임금에 포함", "급여에 포함",
    "임금에서 공제", "급여에서 공제", "위약금", "손해 전액", "전액 배상",
    "감액", "언제든지 해고", "즉시 해고", "일방적으로", "포기한다",
)

ADVERSE_RISK_MARKERS = (
    "위험", "불리", "위반", "누락", "미지급", "무급", "불명확", "모호",
    "과도", "제한", "강요", "공제", "차감", "포기", "위약금", "손해배상",
    "즉시 해고", "일방적 해고", "보장되지", "사용할 수 없", "지급하지",
)


def _checklist_item(baseline: AnalysisResponse, code: str):
    return next((item for item in baseline.checklist if item.code == code), None)


def _clause_category(item: ClauseDecision) -> str | None:
    value = f"{item.clause_type} {item.title} {item.original_text} {item.reason} {item.recommendation}".lower()
    title = item.title.lower()
    categories = [
        ("WAGE", ("임금", "급여", "기본급", "식대")),
        ("WORK_HOURS", ("근로시간", "근무시간", "휴게시간", "연장근로", "야간근로")),
        ("ANNUAL_LEAVE", ("연차", "유급휴가")),
        ("HOLIDAY", ("주휴일", "유급휴일", "휴일")),
        ("SEVERANCE_NONPAYMENT", ("퇴직금", "퇴직급여")),
        ("TERMINATION", ("해고", "계약 종료", "계약의 종료")),
    ]
    for code, terms in categories:
        if any(term in title for term in terms):
            return code
    for code, terms in categories:
        if any(term in value for term in terms):
            return code
    return None


def _requirements_satisfied(category: str, baseline: AnalysisResponse, text: str, item: ClauseDecision) -> bool:
    compact = re.sub(r"\s+", " ", text)
    checklist_codes = {
        "WAGE": "WAGE", "WORK_HOURS": "WORK_HOURS",
        "HOLIDAY": "HOLIDAY", "ANNUAL_LEAVE": "ANNUAL_LEAVE",
    }
    checklist_code = checklist_codes.get(category)
    if checklist_code:
        check = _checklist_item(baseline, checklist_code)
        if check is None or check.status != "COMPLIANT":
            return False

    item_text = f"{item.title} {item.reason} {item.recommendation}"
    if category == "WAGE":
        return (
            any(term in compact for term in ("기본급", "월 임금", "월 급여"))
            and any(term in compact for term in ("산정기간", "산정 기간", "계산방법"))
            and "지급" in compact
            and any(term in compact for term in ("계좌", "현금", "지급방법"))
        )
    if category == "WORK_HOURS":
        if any(term in item_text for term in ("연장근로", "야간근로", "가산임금", "가산수당")):
            return (
                "합의" in compact
                and any(term in compact for term in ("가산임금", "가산수당"))
                and "실제 근로시간" in compact
            )
        return (
            "근로시간" in compact
            and "시부터" in compact and "시까지" in compact
            and "휴게시간" in compact
        )
    if category == "HOLIDAY":
        return any(term in compact for term in ("주휴일", "매주 일요일", "유급휴일"))
    if category == "ANNUAL_LEAVE":
        return (
            any(term in compact for term in ("연차 유급휴가", "연차유급휴가"))
            and any(term in compact for term in ("제60조", "관계 법령"))
            and "부여" in compact
        )
    if category == "SEVERANCE_NONPAYMENT":
        return (
            "퇴직급여" in compact and "관계 법령" in compact
            and "지급" in compact and any(term in compact for term in ("지급기한", "지급 기한"))
        )
    if category == "TERMINATION":
        return (
            any(term in compact for term in ("계약의 종료", "계약 종료", "해고"))
            and "관계 법령" in compact and "절차" in compact
            and "서면" in compact
        )
    return False


def _is_redundant_clause(item: ClauseDecision, baseline: AnalysisResponse, text: str) -> bool:
    if is_negated_risk_text(item.clause_type, item.original_text):
        return True
    quoted = item.original_text.replace(" ", "")
    if any(marker.replace(" ", "") in quoted for marker in EXPLICIT_RISK_MARKERS):
        return False
    category = _clause_category(item)
    if category is None:
        return False
    generic_advice = any(
        term in f"{item.reason} {item.recommendation}"
        for term in ("명확", "구체적", "기재", "작성", "보완", "규정", "필요")
    )
    return generic_advice and _requirements_satisfied(category, baseline, text, item)


def _is_llm_risk_candidate(item: ClauseDecision, baseline: AnalysisResponse) -> bool:
    if is_negated_risk_text(item.clause_type, item.original_text):
        return False
    if any(
        clause.clause_type.upper() == item.clause_type.upper()
        for clause in baseline.clauses
    ):
        return True
    candidate_text = f"{item.title} {item.original_text} {item.reason}"
    category = _clause_category(item)
    if category in {"WAGE", "WORK_HOURS", "HOLIDAY", "ANNUAL_LEAVE"} and "누락" in candidate_text:
        check = _checklist_item(baseline, category)
        return check is not None and check.status == "MISSING"
    return any(marker in candidate_text for marker in ADVERSE_RISK_MARKERS)


def _enabled() -> bool:
    return os.getenv("LAWZIC_LLM_ENABLED", "true").lower() in {"1", "true", "yes", "on"}


def _contract_type(text: str) -> str:
    labor_terms = ("근로자", "사용자", "임금", "근로시간", "퇴직금", "연차")
    return "EMPLOYMENT" if sum(term in text for term in labor_terms) >= 2 else "GENERAL"


def _contract_type_label(contract_type: str) -> str:
    return {
        "EMPLOYMENT": "근로계약서",
        "GENERAL": "일반계약서",
    }.get(contract_type.upper(), "계약서")


def _normalize_user_text(value: str) -> str:
    replacements = {
        r"\bemployment\b": "근로계약서",
        r"\bgeneral\b": "일반계약서",
    }
    normalized = value
    for pattern, replacement in replacements.items():
        normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)
    return normalized


def _replacement_text(item: ClauseDecision, baseline_match: RiskClause | None) -> str | None:
    """Prefer vetted clause language and never expose duplicated advice as a replacement."""
    if baseline_match and baseline_match.replacement_text:
        return baseline_match.replacement_text
    if not item.replacement_text:
        return None
    replacement = _normalize_user_text(item.replacement_text).strip()
    recommendation = _normalize_user_text(item.recommendation).strip()
    return replacement if replacement != recommendation else None


def _contains_internal_contract_code(value: str) -> bool:
    return re.search(r"\b(?:EMPLOYMENT|GENERAL)\b", value, flags=re.IGNORECASE) is not None


def _search_queries(text: str, baseline: AnalysisResponse) -> list[str]:
    queries = [f"{item.title} {item.original_text} {item.reason}" for item in baseline.clauses]
    paragraphs = [re.sub(r"\s+", " ", value).strip() for value in re.split(r"\n+|(?=제\s*\d+\s*조)", text)]
    queries.extend(value for value in paragraphs if len(value) >= 15)
    return queries[:12] or [text[:1000]]


class ContractAnalysisAgent:
    def __init__(self, rag: LawRagService):
        self.rag = rag
        builder = StateGraph(AgentState)
        builder.add_node("prepare", self._prepare)
        builder.add_node("retrieve_laws", self._retrieve_laws)
        builder.add_node("llm_analyze", self._llm_analyze)
        builder.add_node("finalize", self._finalize)
        builder.add_edge(START, "prepare")
        builder.add_edge("prepare", "retrieve_laws")
        builder.add_conditional_edges(
            "retrieve_laws", self._route_after_retrieval,
            {"llm": "llm_analyze", "fallback": "finalize"},
        )
        builder.add_edge("llm_analyze", "finalize")
        builder.add_edge("finalize", END)
        self.graph = builder.compile()

    @staticmethod
    def _prepare(state: AgentState) -> dict:
        return {
            "contract_type": _contract_type(state["text"]),
            "baseline": analyze_contract(state["contract_id"], state["text"]),
        }

    def _retrieve_laws(self, state: AgentState) -> dict:
        found: dict[str, dict] = {}
        try:
            for query in _search_queries(state["text"], state["baseline"]):
                for match in self.rag.search(query, top_k=2):
                    found[match["evidence_id"]] = match
        except Exception as exc:
            logger.warning("법령 RAG 검색 실패 (%s)", type(exc).__name__)
            return {"evidence": [], "llm_error": "일부 법령 검색을 사용할 수 없어 기본 분석으로 완료했습니다."}
        evidence = sorted(found.values(), key=lambda item: item["hybrid_score"], reverse=True)[:8]
        return {"evidence": evidence}

    @staticmethod
    def _route_after_retrieval(state: AgentState) -> Literal["llm", "fallback"]:
        return "llm" if _enabled() and state.get("evidence") else "fallback"

    @staticmethod
    def _llm() -> ChatOllama:
        return ChatOllama(
            model=os.getenv("OLLAMA_MODEL", "gemma2:2b"),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            temperature=0,
            num_predict=2400,
        )

    def _llm_analyze(self, state: AgentState) -> dict:
        evidence_text = "\n\n".join(
            f'[{item["evidence_id"]}] {item["law_name"]} {item["article_number"]}\n{item["content"]}'
            for item in state["evidence"]
        )
        prompt = f"""계약서 유형: {_contract_type_label(state['contract_type'])}

[계약서]
{state['text'][:16000]}

[검색된 법령 근거]
{evidence_text[:12000]}

위 자료를 비교하여 계약서를 구조적으로 분석하세요."""
        try:
            structured_llm = self._llm().with_structured_output(LlmDecision)
            decision = structured_llm.invoke([
                ("system", SYSTEM_PROMPT), ("human", prompt)
            ])
            if not _is_korean_decision(decision):
                decision = structured_llm.invoke([
                    ("system", SYSTEM_PROMPT),
                    ("human", "이전 응답에 영어가 포함되어 사용할 수 없습니다. 모든 설명과 제목을 반드시 한국어로 작성하세요.\n\n" + prompt),
                ])
            if not _is_korean_decision(decision):
                return {"llm_error": "LLM이 한국어 출력 형식을 지키지 않아 한국어 규칙 분석으로 전환했습니다."}
            return {"llm_decision": decision}
        except Exception as exc:
            # 구조화 출력 파싱 예외에는 모델의 전체 생성문이 포함될 수 있으므로
            # API 응답이나 저장 결과에 예외 원문을 절대 넣지 않는다.
            logger.warning("LLM 구조화 분석 실패 (%s)", type(exc).__name__)
            return {"llm_error": "AI 심층 분석을 완료하지 못해 기본 분석으로 안전하게 전환했습니다."}

    @staticmethod
    def _finalize(state: AgentState) -> dict:
        baseline = state["baseline"]
        decision = state.get("llm_decision")
        evidence_by_id = {item["evidence_id"]: item for item in state.get("evidence", [])}
        if decision is None:
            for clause in baseline.clauses:
                clause.legal_references = _best_references(state.get("evidence", []), clause.title)
            warning = state.get("llm_error") or "LLM 분석이 비활성화되어 규칙 기반 결과를 반환했습니다."
            baseline.warnings = [warning, "본 결과는 법률 자문이나 법적 판단을 대체하지 않습니다."]
            return {"result": baseline}

        clauses = []
        llm_clause_types = set()
        for item in decision.clauses:
            if (
                _is_redundant_clause(item, baseline, state["text"])
                or not _is_llm_risk_candidate(item, baseline)
            ):
                logger.info("검증되지 않은 LLM 항목 제거: %s", item.title)
                continue
            llm_clause_types.add(item.clause_type.upper())
            references = []
            for evidence_id in dict.fromkeys(item.evidence_ids):
                evidence = evidence_by_id.get(evidence_id)
                if evidence:
                    references.append(_to_reference(evidence))
            baseline_match = next(
                (base for base in baseline.clauses
                 if base.clause_type.upper() == item.clause_type.upper()),
                None,
            )
            semantic = evaluate_candidate(item.clause_type.upper(), item.original_text)
            confidence = baseline_match.confidence if baseline_match else min(0.65, semantic.confidence)
            review_required = baseline_match.review_required if baseline_match else True
            clauses.append(RiskClause(
                clause_type=item.clause_type,
                title=_normalize_user_text(item.title),
                original_text=item.original_text,
                risk_level="LOW" if review_required else baseline_match.risk_level,
                reason=_normalize_user_text(item.reason),
                recommendation=_normalize_user_text(item.recommendation),
                confidence=confidence,
                review_required=review_required,
                semantic=baseline_match.semantic if baseline_match else SemanticEvidence(
                    subject=semantic.subject, action=semantic.action, target=semantic.target,
                    negated=semantic.negated, conditional=semantic.conditional,
                ),
                replacement_text=_replacement_text(item, baseline_match),
                legal_references=references,
            ))
        # 작은 로컬 LLM이 명백한 위험을 놓쳐도 규칙 탐지 결과가 사라지지 않도록 병합한다.
        for clause in baseline.clauses:
            if clause.clause_type.upper() not in llm_clause_types:
                clause.legal_references = _best_references(state.get("evidence", []), clause.title)
                clauses.append(clause)
        clauses = reconcile_checklist_findings(
            deduplicate_findings(clauses), baseline.checklist,
        )
        score, level, review_count = calculate_verified_risk(clauses)
        return {"result": AnalysisResponse(
            contract_id=state["contract_id"],
            summary=_normalize_user_text(decision.summary),
            overall_risk_level=level,
            overall_score=score,
            review_required_count=review_count,
            clauses=clauses,
            checklist=baseline.checklist,
            warnings=[
                "AI 분석기가 검색된 법령 근거와 계약서 원문을 비교해 생성한 결과입니다.",
                "본 결과는 법률 자문이나 법적 판단을 대체하지 않습니다.",
            ],
        )}

    def analyze(self, contract_id: int, text: str) -> AnalysisResponse:
        state = self.graph.invoke({"contract_id": contract_id, "text": text})
        return state["result"]


def _to_reference(item: dict) -> LegalReference:
    return LegalReference(
        law_name=item["law_name"], article_number=item["article_number"],
        content=item["content"], source_url=item.get("source_url"),
    )


def _is_korean_text(value: str, minimum: int = 2) -> bool:
    return len(re.findall(r"[가-힣]", value)) >= minimum


def _is_korean_decision(decision: LlmDecision) -> bool:
    if not _is_korean_text(decision.summary, 8) or _contains_internal_contract_code(decision.summary):
        return False
    return all(
        _is_korean_text(item.title)
        and _is_korean_text(item.reason, 5)
        and _is_korean_text(item.recommendation, 5)
        and not _contains_internal_contract_code(
            f"{item.title} {item.reason} {item.recommendation} {item.replacement_text or ''}"
        )
        for item in decision.clauses
    )


def _best_references(evidence: list[dict], title: str) -> list[LegalReference]:
    matching = [item for item in evidence if title in item["content"]]
    return [_to_reference(item) for item in (matching or evidence)[:2]]
