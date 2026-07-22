import os
import re
from typing import Literal, TypedDict

from langchain_ollama import ChatOllama
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from .analyzer import analyze_contract
from .rag import LawRagService
from .schemas import AnalysisResponse, LegalReference, RiskClause, RiskLevel


class ClauseDecision(BaseModel):
    clause_type: str = Field(description="영문 대문자 위험 유형 코드")
    title: str
    original_text: str = Field(description="계약서에 실제로 존재하는 문구. 누락이면 '해당 조항 없음'")
    risk_level: RiskLevel
    reason: str
    recommendation: str
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
- 위험도는 HIGH, MEDIUM, LOW, SAFE 중 하나로 작성하세요.
- 법률 자문처럼 단정하지 말고 검토 필요성과 이유를 설명하세요.
- 전체 위험 점수는 0~100입니다.
"""


def _enabled() -> bool:
    return os.getenv("LAWZIC_LLM_ENABLED", "true").lower() in {"1", "true", "yes", "on"}


def _contract_type(text: str) -> str:
    labor_terms = ("근로자", "사용자", "임금", "근로시간", "퇴직금", "연차")
    return "EMPLOYMENT" if sum(term in text for term in labor_terms) >= 2 else "GENERAL"


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
            return {"evidence": [], "llm_error": f"법령 RAG 검색 실패: {exc}"}
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
            num_predict=1024,
        )

    def _llm_analyze(self, state: AgentState) -> dict:
        evidence_text = "\n\n".join(
            f'[{item["evidence_id"]}] {item["law_name"]} {item["article_number"]}\n{item["content"]}'
            for item in state["evidence"]
        )
        prompt = f"""계약서 유형: {state['contract_type']}

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
            return {"llm_error": f"LLM 분석 실패: {exc}"}

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
            llm_clause_types.add(item.clause_type.upper())
            references = []
            for evidence_id in dict.fromkeys(item.evidence_ids):
                evidence = evidence_by_id.get(evidence_id)
                if evidence:
                    references.append(_to_reference(evidence))
            clauses.append(RiskClause(
                clause_type=item.clause_type,
                title=item.title,
                original_text=item.original_text,
                risk_level=item.risk_level,
                reason=item.reason,
                recommendation=item.recommendation,
                legal_references=references,
            ))
        # 작은 로컬 LLM이 명백한 위험을 놓쳐도 규칙 탐지 결과가 사라지지 않도록 병합한다.
        for clause in baseline.clauses:
            if clause.clause_type.upper() not in llm_clause_types:
                clause.legal_references = _best_references(state.get("evidence", []), clause.title)
                clauses.append(clause)
        score = max(decision.overall_score, baseline.overall_score)
        level = "HIGH" if score >= 60 else "MEDIUM" if score >= 25 else "LOW" if clauses else "SAFE"
        return {"result": AnalysisResponse(
            contract_id=state["contract_id"],
            summary=decision.summary,
            overall_risk_level=level,
            overall_score=score,
            clauses=clauses,
            warnings=[
                f"LangGraph Agent와 {os.getenv('OLLAMA_MODEL', 'gemma2:2b')} LLM이 RAG 법령 근거로 생성한 결과입니다.",
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
    if not _is_korean_text(decision.summary, 8):
        return False
    return all(
        _is_korean_text(item.title)
        and _is_korean_text(item.reason, 5)
        and _is_korean_text(item.recommendation, 5)
        for item in decision.clauses
    )


def _best_references(evidence: list[dict], title: str) -> list[LegalReference]:
    matching = [item for item in evidence if title in item["content"]]
    return [_to_reference(item) for item in (matching or evidence)[:2]]
