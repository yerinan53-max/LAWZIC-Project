import os
import re
from typing import TypedDict

from langchain_ollama import ChatOllama
from langgraph.graph import END, START, StateGraph

from .contract_rag import ContractRagService
from .rag import LawRagService
from .schemas import LegalReference, QuestionResponse, SourceLocation


class QuestionState(TypedDict, total=False):
    contract_id: int
    question: str
    history: list[dict]
    contract_evidence: list[dict]
    law_evidence: list[dict]
    answer: str


class ContractQuestionAgent:
    def __init__(self, contracts: ContractRagService, laws: LawRagService):
        self.contracts = contracts
        self.laws = laws
        graph = StateGraph(QuestionState)
        graph.add_node("retrieve_contract", self._retrieve_contract)
        graph.add_node("retrieve_laws", self._retrieve_laws)
        graph.add_node("generate_answer", self._generate_answer)
        graph.add_edge(START, "retrieve_contract")
        graph.add_edge("retrieve_contract", "retrieve_laws")
        graph.add_edge("retrieve_laws", "generate_answer")
        graph.add_edge("generate_answer", END)
        self.graph = graph.compile()

    def _retrieve_contract(self, state: QuestionState) -> dict:
        return {"contract_evidence": self.contracts.search(
            state["contract_id"], state["question"], top_k=4,
        )}

    def _retrieve_laws(self, state: QuestionState) -> dict:
        try:
            return {"law_evidence": self.laws.search(state["question"], top_k=3)}
        except Exception:
            return {"law_evidence": []}

    @staticmethod
    def _fallback(state: QuestionState) -> str:
        contracts = state.get("contract_evidence", [])
        laws = state.get("law_evidence", [])
        if not contracts and not laws:
            return "질문과 관련된 계약서 조항이나 법령 근거를 찾지 못했습니다. 질문을 조금 더 구체적으로 입력해 주세요."
        lines = []
        if contracts:
            lines.append("계약서에서 확인된 내용:\n" + "\n".join(
                f'- {item["text"]}' for item in contracts[:2]
            ))
        if laws:
            lines.append("관련 법령 근거:\n" + "\n".join(
                f'- {item["law_name"]} {item["article_number"]}: {item["content"]}'
                for item in laws[:2]
            ))
        return "\n\n".join(lines)

    def _generate_answer(self, state: QuestionState) -> dict:
        if not state.get("contract_evidence") and not state.get("law_evidence"):
            return {"answer": self._fallback(state)}
        contract_context = "\n\n".join(
            f'[계약서 {item["page"]}페이지 / {item["chunk_id"]}]\n{item["text"]}'
            for item in state.get("contract_evidence", [])
        )
        law_context = "\n\n".join(
            f'[{item["evidence_id"]}] {item["law_name"]} {item["article_number"]}\n{item["content"]}'
            for item in state.get("law_evidence", [])
        )
        history = "\n".join(
            f'{"사용자" if item.get("role") == "user" else "AI"}: {item.get("content", "")}'
            for item in state.get("history", [])[-6:]
        )
        prompt = f"""당신은 LAWZIC 계약서 질의응답 Agent입니다.
검색된 계약서 원문과 법령 근거만 사용하여 한국어로 답하세요.
계약서에 실제로 적힌 내용과 법령상 일반 원칙을 명확히 구분하세요.
근거가 부족하면 추측하지 말고 부족하다고 말하세요.

[이전 질문 이력]
{history or "없음"}

[현재 질문]
{state["question"]}

[계약서 검색 결과]
{contract_context or "없음"}

[법령 검색 결과]
{law_context or "없음"}
"""
        try:
            generated = ChatOllama(
                model=os.getenv("OLLAMA_MODEL", "gemma2:2b"),
                base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
                temperature=0, num_predict=900,
            ).invoke(prompt).content.strip()
            if len(re.findall(r"[가-힣]", generated)) >= 8:
                return {"answer": generated}
        except Exception:
            pass
        return {"answer": self._fallback(state)}

    def answer(self, contract_id: int, question: str, history: list[dict]) -> QuestionResponse:
        state = self.graph.invoke({
            "contract_id": contract_id, "question": question, "history": history,
        })
        return QuestionResponse(
            answer=state["answer"],
            contract_sources=[SourceLocation(
                page=item["page"], text=item["text"], boxes=[],
            ) for item in state.get("contract_evidence", [])],
            legal_references=[LegalReference(
                law_name=item["law_name"], article_number=item["article_number"],
                content=item["content"], source_url=item.get("source_url"),
            ) for item in state.get("law_evidence", [])],
            warning="계약서와 검색된 법령에 근거한 참고 답변이며 법률 자문을 대체하지 않습니다.",
        )
