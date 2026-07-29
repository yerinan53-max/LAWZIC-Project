from app.agent import (
    ClauseDecision, ContractAnalysisAgent, LlmDecision, _is_korean_decision,
    _is_llm_risk_candidate, _is_redundant_clause, _normalize_user_text,
)
from app.analyzer import analyze_contract


class FakeRag:
    def search(self, query: str, top_k: int = 2) -> list[dict]:
        return [{
            "evidence_id": "labor-20",
            "law_name": "근로기준법",
            "article_number": "제20조",
            "content": "사용자는 근로계약 불이행에 대한 위약금 또는 손해배상액을 예정하지 못한다.",
            "source_url": "https://example.test/law/20",
            "hybrid_score": 0.9,
        }]


class FakeStructuredLlm:
    def invoke(self, messages):
        return LlmDecision.model_validate({
            "summary": "임금과 근로시간을 정한 근로계약서입니다.",
            "overall_risk_level": "HIGH",
            "overall_score": 75,
            "clauses": [{
                "clause_type": "DAMAGES",
                "title": "위약금",
                "original_text": "퇴사 시 위약금 100만원을 지급한다.",
                "risk_level": "HIGH",
                "reason": "위약금을 미리 정한 조항일 가능성이 있습니다.",
                "recommendation": "해당 조항을 삭제하거나 실제 손해 기준으로 수정하세요.",
                "evidence_ids": ["labor-20", "not-retrieved"],
            }],
        })


class FakeLlm:
    def with_structured_output(self, schema):
        return FakeStructuredLlm()


class EnglishStructuredLlm:
    def invoke(self, messages):
        return LlmDecision.model_validate({
            "summary": "This contract contains risky clauses.",
            "overall_risk_level": "HIGH", "overall_score": 80,
            "clauses": [{
                "clause_type": "DAMAGES", "title": "Penalty",
                "original_text": "퇴사 시 위약금을 지급한다.", "risk_level": "HIGH",
                "reason": "The worker must pay a penalty.",
                "recommendation": "Remove this clause.", "evidence_ids": [],
            }],
        })


class EnglishLlm:
    def with_structured_output(self, schema):
        return EnglishStructuredLlm()


def test_graph_falls_back_when_llm_is_disabled(monkeypatch):
    monkeypatch.setenv("LAWZIC_LLM_ENABLED", "false")
    result = ContractAnalysisAgent(FakeRag()).analyze(
        1, "근로자는 임금을 매월 받으며 근로시간은 09시부터 18시까지다."
    )
    assert result.contract_id == 1
    assert "LLM 분석이 비활성화" in result.warnings[0]


def test_graph_uses_llm_and_only_accepts_retrieved_evidence(monkeypatch):
    monkeypatch.setenv("LAWZIC_LLM_ENABLED", "true")
    monkeypatch.setattr(ContractAnalysisAgent, "_llm", staticmethod(lambda: FakeLlm()))
    result = ContractAnalysisAgent(FakeRag()).analyze(
        2, "근로자는 퇴사 시 위약금 100만원을 지급한다. 임금과 근로시간은 별도로 정한다."
    )
    assert result.overall_score < 75
    assert result.clauses[0].review_required is True
    assert result.clauses[0].risk_level == "LOW"
    assert result.clauses[0].legal_references[0].article_number == "제20조"
    assert len(result.clauses[0].legal_references) == 1
    assert "AI 분석기" in result.warnings[0]


def test_graph_rejects_english_llm_output(monkeypatch):
    monkeypatch.setenv("LAWZIC_LLM_ENABLED", "true")
    monkeypatch.setattr(ContractAnalysisAgent, "_llm", staticmethod(lambda: EnglishLlm()))
    result = ContractAnalysisAgent(FakeRag()).analyze(
        3, "근로자는 임금을 받으며 퇴사 시 위약금을 지급한다. 근로시간은 09시부터 18시까지다."
    )
    assert "한국어 출력 형식" in result.warnings[0]
    assert "This" not in result.summary


def test_clause_decision_uses_default_when_recommendation_is_truncated():
    decision = LlmDecision.model_validate({
        "summary": "위험 조항이 여러 개 포함된 근로계약서입니다.",
        "overall_risk_level": "HIGH",
        "overall_score": 90,
        "clauses": [{
            "clause_type": "OVERTIME",
            "title": "연장근로",
            "original_text": "추가 근무는 무급으로 한다.",
            "risk_level": "HIGH",
            "reason": "연장근로수당이 지급되지 않을 위험이 있습니다.",
        }],
    })
    assert "다시 검토" in decision.clauses[0].recommendation


class RedundantWageStructuredLlm:
    def invoke(self, messages):
        return LlmDecision.model_validate({
            "summary": "임금과 근로시간 등이 구체적으로 정해진 근로계약서입니다.",
            "overall_risk_level": "LOW", "overall_score": 20,
            "clauses": [{
                "clause_type": "WAGE",
                "title": "임금 구성 및 지급 방법",
                "original_text": "월 임금은 기본급 2,700,000원과 식대 200,000원으로 구성한다.",
                "risk_level": "LOW",
                "reason": "임금 구성과 지급 방법이 명확하게 규정되어 있지만 산정기간을 보완해야 합니다.",
                "recommendation": "임금 지급 내용에 관한 구체적인 내용을 명확히 작성하세요.",
                "evidence_ids": [],
            }],
        })


class RedundantWageLlm:
    def with_structured_output(self, schema):
        return RedundantWageStructuredLlm()


def _complete_contract_text():
    return """근로계약서
제2조 (근로시간)
근로시간은 09시부터 18시까지이며 휴게시간은 12시부터 13시까지로 한다.
제4조 (임금)
월 임금은 기본급 2,700,000원과 식대 200,000원으로 구성한다. 임금 산정기간은 매월 1일부터 말일까지이며 매월 25일 근로자 명의 계좌로 지급한다.
제5조 (연장·야간근로)
연장근로와 야간근로는 사전에 합의하며 가산임금은 실제 근로시간에 따라 지급한다.
제6조 (휴일)
주휴일은 매주 일요일로 한다.
제7조 (연차 유급휴가)
연차 유급휴가는 근로기준법 제60조에 따라 부여한다.
제9조 (퇴직급여)
퇴직급여는 관계 법령에 따라 산정하여 법정 지급기한 내에 지급한다.
제10조 (계약의 종료)
계약의 종료와 해고는 관계 법령과 정당한 절차에 따르며 사유와 시기를 서면으로 통지한다.
"""


def test_post_verifier_removes_recommendation_already_satisfied_by_contract(monkeypatch):
    monkeypatch.setenv("LAWZIC_LLM_ENABLED", "true")
    monkeypatch.setattr(ContractAnalysisAgent, "_llm", staticmethod(lambda: RedundantWageLlm()))
    result = ContractAnalysisAgent(FakeRag()).analyze(4, _complete_contract_text())
    assert result.clauses == []
    assert result.overall_score == 0
    assert result.overall_risk_level == "SAFE"


def test_post_verifier_keeps_explicit_wage_deduction_risk():
    text = _complete_contract_text() + "\n회사 물품 손상 시 손해액을 임금에서 공제한다."
    baseline = analyze_contract(5, text)
    item = ClauseDecision.model_validate({
        "clause_type": "WAGE_DEDUCTION",
        "title": "임금 공제",
        "original_text": "회사 물품 손상 시 손해액을 임금에서 공제한다.",
        "risk_level": "HIGH",
        "reason": "임금에서 손해액을 직접 공제하는 내용은 검토가 필요합니다.",
        "recommendation": "임금 공제 문구를 삭제하고 손해 책임을 별도로 판단하세요.",
    })
    assert _is_redundant_clause(item, baseline, text) is False


def test_post_verifier_removes_negated_wage_deduction_false_positive():
    text = _complete_contract_text() + "\n회사는 확정되지 않은 손해액을 임금에서 임의로 공제하지 않는다."
    baseline = analyze_contract(6, text)
    item = ClauseDecision.model_validate({
        "clause_type": "WAGE_DEDUCTION",
        "title": "임금의 임의 공제",
        "original_text": "회사는 확정되지 않은 손해액을 임금에서 임의로 공제하지 않는다.",
        "risk_level": "HIGH",
        "reason": "손해액을 임금에서 공제하는 내용은 검토가 필요합니다.",
        "recommendation": "임금에서 손해액을 공제하지 않도록 수정하세요.",
    })
    assert _is_redundant_clause(item, baseline, text) is True


def test_internal_contract_type_is_never_exposed_to_user_text():
    assert _normalize_user_text("이 계약서는 employment 유형입니다.") == "이 계약서는 근로계약서 유형입니다."
    decision = LlmDecision.model_validate({
        "summary": "이 계약서는 employment 유형으로 작성된 근로계약서입니다.",
        "overall_risk_level": "SAFE",
        "overall_score": 0,
        "clauses": [],
    })
    assert _is_korean_decision(decision) is False


def test_llm_summary_and_compliant_clause_are_not_risk_candidates():
    baseline = analyze_contract(7, _complete_contract_text())
    contract_summary = ClauseDecision.model_validate({
        "clause_type": "CONTRACT_TYPE",
        "title": "근로계약서",
        "original_text": "근로계약서",
        "risk_level": "LOW",
        "reason": "본 계약서는 1년 기간제 근로계약입니다.",
        "recommendation": "해당 조항을 원문 및 관련 법령과 함께 다시 검토하세요.",
    })
    compliant_break = ClauseDecision.model_validate({
        "clause_type": "BREAK_TIME",
        "title": "휴게시간",
        "original_text": "휴게시간은 12시부터 13시까지로 한다.",
        "risk_level": "LOW",
        "reason": "본 계약서는 1시간의 휴게시간을 보장합니다.",
        "recommendation": "해당 조항을 원문 및 관련 법령과 함께 다시 검토하세요.",
    })
    assert _is_llm_risk_candidate(contract_summary, baseline) is False
    assert _is_llm_risk_candidate(compliant_break, baseline) is False


def test_llm_cannot_restore_missing_holiday_when_checklist_has_indirect_evidence():
    text = """근로계약서
제4조 근무시간
월요일~금요일 09:00~18:00 (휴게 12:00~13:00)
임금은 기본급 2,800,000원으로 매월 지급한다.
연차휴가는 관계 법령에 따른다.
"""
    baseline = analyze_contract(8, text)
    missing_holiday = ClauseDecision.model_validate({
        "clause_type": "MISSING_HOLIDAY",
        "title": "휴일 조항 누락",
        "original_text": "해당 표현을 찾지 못했습니다.",
        "risk_level": "MEDIUM",
        "reason": "계약서에서 휴일 관련 내용이 누락되었습니다.",
        "recommendation": "휴일을 명확하게 기재하세요.",
    })

    assert next(item for item in baseline.checklist if item.code == "HOLIDAY").status == "REVIEW"
    assert _is_llm_risk_candidate(missing_holiday, baseline) is False
