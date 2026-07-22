from app.agent import ContractAnalysisAgent, LlmDecision


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
    assert result.overall_score == 75
    assert result.clauses[0].legal_references[0].article_number == "제20조"
    assert len(result.clauses[0].legal_references) == 1
    assert "LangGraph Agent" in result.warnings[0]
