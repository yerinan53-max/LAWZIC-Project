import json
from pathlib import Path

import pytest

from app.legal_consultation import (
    LEGACY_EVIDENCE_CITATIONS,
    _citation_indices,
    _fallback_answer,
    _is_grounded_generated_answer,
    answer_legal_question,
    is_consultation_in_scope,
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
    citations = {(item["law_name"], item["article_number"]) for item in matches}
    for required_id in case["required_evidence_ids"]:
        assert (
            required_id in evidence_ids
            or LEGACY_EVIDENCE_CITATIONS[required_id] in citations
        )
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


def test_unseen_labor_expression_is_accepted_by_relevant_rag_result(monkeypatch):
    class SemanticWageRag:
        def search(self, query, top_k=8):
            return [{
                "evidence_id": "semantic-wage-result",
                "law_name": "근로기준법",
                "article_number": "제43조",
                "content": "임금은 근로자에게 그 전액을 지급하여야 한다.",
                "keywords": "임금|전액 지급",
                "similarity": 0.91,
                "hybrid_score": 0.88,
            }]

    question = "평가가 나쁘다고 받기로 한 돈을 줄인대요. 가능한가요?"
    assert is_labor_law_question(question, []) is False
    query, matches = search_consultation_laws(question, [], SemanticWageRag())
    assert query == question
    assert is_consultation_in_scope(question, [], matches) is True

    monkeypatch.setenv("LAWZIC_LLM_ENABLED", "false")
    result = answer_legal_question(question, [], SemanticWageRag())
    assert result.insufficient_evidence is False
    assert result.legal_references[0].article_number == "제43조"
    assert "노동법 질문만 지원합니다" not in result.answer


def test_explicit_other_legal_domain_is_rejected_even_if_rag_is_noisy():
    noisy_match = [{
        "law_name": "근로기준법",
        "article_number": "제43조",
        "content": "임금은 전액 지급하여야 한다.",
    }]
    assert is_consultation_in_scope("상속세 신고 방법을 알려주세요.", [], noisy_match) is False


def test_new_explicit_topic_does_not_inherit_previous_overtime_question(law_rag):
    history = [
        LegalChatMessage(role="user", content="연장근로는 일주일에 몇 시간까지 가능한가요?"),
        LegalChatMessage(role="assistant", content="연장근로 한도를 안내했습니다."),
    ]
    query, matches = search_consultation_laws(
        "수습기간에는 최저임금보다 적게 지급할 수 있나요?", history, law_rag,
    )
    assert "연장근로" not in query
    citations = {(item["law_name"], item["article_number"]) for item in matches}
    assert citations == {
        ("최저임금법", "제5조"),
        ("최저임금법 시행령", "제3조"),
    }


def test_severance_fallback_answers_worker_question_directly():
    matches = [
        {
            "evidence_id": "retirement-benefit-act-4",
            "law_name": "근로자퇴직급여 보장법",
            "article_number": "제4조",
            "content": "계속근로기간이 1년 미만인 근로자는 적용 대상에서 제외한다.",
        },
        {
            "evidence_id": "retirement-benefit-act-8",
            "law_name": "근로자퇴직급여 보장법",
            "article_number": "제8조",
            "content": "계속근로기간 1년에 대하여 30일분 이상의 평균임금을 지급한다.",
        },
    ]
    answer = _fallback_answer(matches, "1년을 다 못다니면 퇴직금을 못받는거예요?")
    assert answer.startswith("네.")
    assert "1년 미만" in answer
    assert "주 소정근로시간이 15시간 미만" in answer
    assert "관련어:" not in answer
    assert "[근거 1]" in answer
    assert "[근거 2]" in answer


def test_wage_deduction_fallback_starts_with_direct_conclusion():
    matches = [{
        "evidence_id": "labor-standards-act-43",
        "law_name": "근로기준법",
        "article_number": "제43조",
        "content": (
            "임금은 통화로 직접 근로자에게 그 전액을 지급하여야 한다. "
            "다만, 법령 또는 단체협약에 특별한 규정이 있는 경우에는 "
            "임금의 일부를 공제할 수 있다."
        ),
    }]
    answer = _fallback_answer(matches, "회사가 임금을 임의로 공제할 수 있나요?")
    assert answer.startswith("원칙적으로 회사는")
    assert "임의로 공제할 수 없습니다" in answer.splitlines()[0]
    assert "법령 또는 단체협약" in answer
    assert "지각" in answer
    assert "장비 파손" in answer
    assert "근로 형태와 사실관계" not in answer
    assert "[근거 1]" in answer


def test_forced_resignation_fallback_gives_actionable_steps():
    matches = [
        {"evidence_id": "x23", "law_name": "근로기준법", "article_number": "제23조", "content": "정당한 이유 없는 해고 금지"},
        {"evidence_id": "x27", "law_name": "근로기준법", "article_number": "제27조", "content": "해고 사유와 시기의 서면 통지"},
        {"evidence_id": "x28", "law_name": "근로기준법", "article_number": "제28조", "content": "부당해고 구제신청"},
    ]
    answer = _fallback_answer(
        matches, "회사에서 권고사직서를 쓰라고 강요하면 어떻게 해야 하나요?",
    )
    assert "서명하지 않는 것이 중요" in answer
    assert "증거" in answer or "기록" in answer
    assert "3개월 이내" in answer
    assert "[근거 1]" in answer
    assert "[근거 2]" in answer
    assert "[근거 3]" in answer


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
    received_prompts = []

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
            received_prompts.append(prompt)
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
    assert "먼저 결론을 한 문장으로 제시하고, 이후 법적 근거와 예외를 설명하세요." in received_prompts[0]
    assert [item.article_number for item in result.legal_references] == ["제53조"]


def test_chat_llm_has_timeout_and_falls_back_when_generation_fails(monkeypatch):
    class OvertimeRag:
        def search(self, query, top_k=8):
            return [{
                "evidence_id": "labor-standards-act-53",
                "law_name": "근로기준법",
                "article_number": "제53조",
                "content": "합의하면 연장근로는 1주 12시간을 한도로 할 수 있다.",
                "keywords": "연장근로|주 12시간",
                "similarity": 0.9,
                "hybrid_score": 0.95,
            }]

    received = {}

    class FailingLlm:
        def invoke(self, prompt):
            raise TimeoutError("slow local model")

    def create_llm(**kwargs):
        received.update(kwargs)
        return FailingLlm()

    monkeypatch.setenv("LAWZIC_LLM_ENABLED", "true")
    monkeypatch.setenv("OLLAMA_CHAT_TIMEOUT_SECONDS", "45")
    monkeypatch.setattr("app.legal_consultation.ChatOllama", create_llm)

    result = answer_legal_question(
        "연장근로는 일주일에 몇 시간까지 가능한가요?", [], OvertimeRag(),
    )

    assert received["client_kwargs"]["timeout"] == 45.0
    assert received["num_predict"] == 400
    assert "근로기준법 제53조" in result.answer
    assert result.insufficient_evidence is False
