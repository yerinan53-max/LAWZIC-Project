from app.analyzer import analyze_contract
from app.document_features import answer_legal_question, create_report, enrich_locations
from app.pdf_service import PdfPage
from app.schemas import LegalChatMessage


def test_enriches_clause_and_checklist_locations_and_creates_report():
    text = "근로계약서\n임금은 매월 지급한다.\n근로시간은 09시부터 18시까지다.\n퇴직금은 월 급여에 포함한다."
    page = PdfPage(
        number=1, text=text, width=595, height=842,
        words=[
            (40, 40, 100, 55, "근로계약서", 0, 0, 0),
            (40, 70, 75, 85, "임금은", 1, 0, 0),
            (40, 100, 100, 115, "근로시간은", 2, 0, 0),
            (40, 130, 85, 145, "퇴직금은", 3, 0, 0),
            (90, 130, 125, 145, "월", 3, 0, 1),
            (130, 130, 165, 145, "급여에", 3, 0, 2),
            (170, 130, 220, 145, "포함한다.", 3, 0, 3),
        ],
    )
    result = enrich_locations(analyze_contract(1, text), [page])
    clause = next(item for item in result.clauses if item.clause_type == "SEVERANCE_NONPAYMENT")
    assert clause.location.page == 1
    assert clause.location.boxes
    report = create_report(result, "sample.pdf")
    assert report.startswith(b"%PDF")
    assert len(report) > 1000


def test_location_uses_contiguous_target_words_instead_of_page_wide_keywords():
    text = """제1조 업무
근로자는 개발 업무를 수행한다.
제2조 근로시간
근로시간은 09시부터 18시까지로 한다.
제3조 임금
임금은 매월 지급한다."""
    page = PdfPage(
        number=1, text=text, width=600, height=800,
        words=[
            (20, 20, 60, 35, "제1조", 0, 0, 0),
            (20, 45, 70, 60, "근로자는", 0, 1, 0),
            (75, 45, 110, 60, "개발", 0, 1, 1),
            (20, 200, 60, 215, "제2조", 1, 0, 0),
            (65, 200, 125, 215, "근로시간", 1, 0, 1),
            (20, 225, 90, 240, "근로시간은", 1, 1, 0),
            (95, 225, 145, 240, "09시부터", 1, 1, 1),
            (150, 225, 205, 240, "18시까지로", 1, 1, 2),
            (210, 225, 250, 240, "한다.", 1, 1, 3),
            (20, 600, 60, 615, "제3조", 2, 0, 0),
            (20, 625, 65, 640, "임금은", 2, 1, 0),
        ],
    )
    from app.document_features import locate_text
    location = locate_text("제2조 근로시간 근로시간은 09시부터 18시까지로 한다.", [page])
    assert location is not None
    assert location.boxes
    assert all(box.y < 0.35 for box in location.boxes)
    assert all(box.height < 0.05 for box in location.boxes)


class LegalRag:
    def __init__(self, matches):
        self.matches = matches

    def search(self, query, top_k=5):
        return self.matches


def test_legal_chat_returns_law_sources_without_contract(monkeypatch):
    monkeypatch.setenv("LAWZIC_LLM_ENABLED", "false")
    rag = LegalRag([{
        "evidence_id": "labor-standards-act-53",
        "law_name": "근로기준법",
        "article_number": "제53조",
        "content": "연장근로의 제한에 관한 조문",
        "source_url": "https://example.test/law/53",
        "keywords": "연장근로|근로시간",
        "similarity": 0.8,
        "hybrid_score": 0.9,
    }])
    result = answer_legal_question(
        "연장근로는 몇 시간까지 가능한가요?",
        [LegalChatMessage(role="user", content="근로시간이 궁금해요.")],
        rag,
    )
    assert result.insufficient_evidence is False
    assert result.legal_references[0].article_number == "제53조"
    assert "근로기준법" in result.answer


def test_legal_chat_does_not_guess_when_no_law_source(monkeypatch):
    monkeypatch.setenv("LAWZIC_LLM_ENABLED", "false")
    result = answer_legal_question("상속세가 궁금합니다.", [], LegalRag([]))
    assert result.insufficient_evidence is True
    assert result.legal_references == []
    assert "노동법 질문만 지원합니다" in result.answer
