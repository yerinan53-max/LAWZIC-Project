import json
from pathlib import Path

import pytest

from app.legal_consultation import (
    _citation_indices,
    _is_grounded_generated_answer,
    answer_legal_question,
    is_labor_law_question,
    search_consultation_laws,
)
from app.rag import LawRagService
from app.schemas import LegalChatMessage


CASES = json.loads(
    (Path(__file__).parent / "data" / "legal_consultation_cases.json").read_text(encoding="utf-8")
)


@pytest.fixture(scope="module")
def law_rag():
    return LawRagService()


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["id"])
def test_consultation_scope_and_required_sources(case, law_rag):
    history = [LegalChatMessage.model_validate(item) for item in case["history"]]
    assert is_labor_law_question(case["question"], history) is case["in_scope"]
    if not case["in_scope"]:
        return
    _, matches = search_consultation_laws(case["question"], history, law_rag)
    evidence_ids = {item["evidence_id"] for item in matches}
    assert set(case["required_evidence_ids"]) <= evidence_ids
    if not case["required_evidence_ids"]:
        assert matches == []


def test_low_relevance_law_is_removed_before_llm(monkeypatch):
    class IrrelevantRag:
        def search(self, query, top_k=8):
            return [{
                "evidence_id": "labor-standards-act-43",
                "law_name": "근로기준법",
                "article_number": "제43조",
                "content": "임금 지급에 관한 조문",
                "keywords": "임금|지급",
                "similarity": 0.30,
                "hybrid_score": 0.45,
            }]

    monkeypatch.setenv("LAWZIC_LLM_ENABLED", "true")
    result = answer_legal_question("임금 공제 기준이 궁금합니다.", [], IrrelevantRag())
    assert result.insufficient_evidence is True
    assert result.legal_references == []


def test_generated_answer_must_use_valid_grounded_citations():
    matches = [
        {
            "content": "임금은 근로자에게 전액 지급하여야 한다.",
            "keywords": "임금|전액|지급",
        },
        {
            "content": "휴게시간은 근로자가 자유롭게 이용할 수 있다.",
            "keywords": "휴게시간|자유",
        },
    ]
    grounded = "임금은 원칙적으로 근로자에게 전액 지급해야 합니다. [근거 1]"
    ungrounded = "회사는 언제든 임금을 절반만 지급할 수 있습니다. [근거 2]"
    no_citation = "임금은 원칙적으로 전액 지급해야 합니다."
    assert _is_grounded_generated_answer(grounded, matches) is True
    assert _is_grounded_generated_answer(ungrounded, matches) is False
    assert _is_grounded_generated_answer(no_citation, matches) is False
    assert _citation_indices("[근거 2] [근거 1] [근거 2] [근거 99]", 2) == [2, 1]


def test_response_exposes_only_sources_actually_cited_by_model(monkeypatch):
    class TwoLawRag:
        def search(self, query, top_k=8):
            return [
                {
                    "evidence_id": "labor-standards-act-50",
                    "law_name": "근로기준법",
                    "article_number": "제50조",
                    "content": "1주 근로시간은 40시간을 초과할 수 없다.",
                    "keywords": "근로시간|주 40시간",
                    "similarity": 0.8,
                    "hybrid_score": 0.9,
                },
                {
                    "evidence_id": "labor-standards-act-53",
                    "law_name": "근로기준법",
                    "article_number": "제53조",
                    "content": "합의하면 연장근로는 1주 12시간을 한도로 할 수 있다.",
                    "keywords": "연장근로|주 12시간",
                    "similarity": 0.85,
                    "hybrid_score": 0.95,
                },
            ]

    class CitedLlm:
        def invoke(self, prompt):
            class Response:
                content = "연장근로는 합의가 있는 경우 1주 12시간 한도입니다. [근거 2]"
            return Response()

    monkeypatch.setenv("LAWZIC_LLM_ENABLED", "true")
    monkeypatch.setattr(
        "app.legal_consultation.ChatOllama", lambda **kwargs: CitedLlm(),
    )
    result = answer_legal_question(
        "연장근로는 일주일에 몇 시간까지 가능한가요?", [], TwoLawRag(),
    )
    assert [item.article_number for item in result.legal_references] == ["제53조"]
