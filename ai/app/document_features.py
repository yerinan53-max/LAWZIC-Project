import io
import os
import re
from collections import defaultdict
from difflib import SequenceMatcher
from html import escape
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, CondPageBreak
from langchain_ollama import ChatOllama

from .pdf_service import PdfPage
from .schemas import (
    AnalysisResponse, LegalReference, QuestionResponse, SourceLocation, TextBox,
)
from .legal_consultation import answer_legal_question


def _plain(value: str) -> str:
    return re.sub(r"\s+", "", value)


def _word_token(value: str) -> str:
    return re.sub(r"[^가-힣A-Za-z0-9]", "", value).lower()


def _matching_words(query: str, page: PdfPage) -> list[tuple]:
    query_words = [
        _word_token(value)
        for value in re.findall(r"[가-힣A-Za-z0-9]+", query)
        if _word_token(value)
    ]
    page_words = [_word_token(str(word[4])) for word in page.words]
    if not query_words or not page_words:
        return []

    match = SequenceMatcher(None, page_words, query_words, autojunk=False).find_longest_match(
        0, len(page_words), 0, len(query_words)
    )
    if match.size >= 2:
        return page.words[match.a:match.a + match.size]

    # 토큰화 차이로 연속 일치가 짧으면 페이지 전체가 아니라 가장 관련도 높은 한 줄만 선택한다.
    query_set = set(query_words)
    lines: dict[tuple[int, int], list[tuple]] = defaultdict(list)
    for word in page.words:
        lines[(int(word[5]), int(word[6]))].append(word)
    ranked = sorted(
        lines.values(),
        key=lambda line: sum(
            token in query_set or any(token in query_token or query_token in token for query_token in query_set)
            for token in (_word_token(str(word[4])) for word in line)
            if token
        ),
        reverse=True,
    )
    if not ranked:
        return []
    best = ranked[0]
    score = sum(
        token in query_set or any(token in query_token or query_token in token for query_token in query_set)
        for token in (_word_token(str(word[4])) for word in best)
        if token
    )
    return best if score >= 1 else []


def locate_text(query: str, pages: list[PdfPage]) -> SourceLocation | None:
    if not query or "찾지 못했습니다" in query or "해당 조항 없음" in query:
        return None
    compact_query = _plain(query)
    tokens = [item for item in re.findall(r"[가-힣A-Za-z0-9]+", query) if len(item) >= 2]
    page = next((item for item in pages if compact_query[:18] in _plain(item.text)), None)
    if page is None:
        page = max(pages, key=lambda item: sum(token in item.text for token in tokens), default=None)
    if page is None or not any(token in page.text for token in tokens):
        return None

    matching = _matching_words(query, page)
    boxes = []
    if matching:
        lines: dict[tuple[int, int], list[tuple]] = defaultdict(list)
        for word in matching:
            lines[(int(word[5]), int(word[6]))].append(word)
        for line_words in lines.values():
            x0 = min(float(word[0]) for word in line_words)
            y0 = min(float(word[1]) for word in line_words)
            x1 = max(float(word[2]) for word in line_words)
            y1 = max(float(word[3]) for word in line_words)
            boxes.append(TextBox(
                x=max(0, x0 / page.width), y=max(0, y0 / page.height),
                width=min(1, (x1 - x0) / page.width), height=min(1, (y1 - y0) / page.height),
            ))
    return SourceLocation(page=page.number, text=query, boxes=boxes)


def enrich_locations(result: AnalysisResponse, pages: list[PdfPage]) -> AnalysisResponse:
    for clause in result.clauses:
        clause.location = locate_text(clause.original_text, pages)
    for item in result.checklist:
        item.location = locate_text(item.evidence or "", pages)
    return result


def answer_question(question: str, pages: list[PdfPage], rag) -> QuestionResponse:
    terms = [item for item in re.findall(r"[가-힣A-Za-z0-9]+", question) if len(item) >= 2]
    ranked = sorted(
        pages,
        key=lambda page: sum(page.text.count(term) for term in terms),
        reverse=True,
    )
    sources = []
    for page in ranked[:2]:
        lines = [line.strip() for line in page.text.splitlines() if any(term in line for term in terms)]
        if lines:
            excerpt = " ".join(lines[:3])[:500]
            location = locate_text(excerpt, pages)
            if location:
                sources.append(location)
    try:
        matches = rag.search(question, top_k=3)
    except Exception:
        matches = []
    laws = [
        LegalReference(
            law_name=item["law_name"], article_number=item["article_number"],
            content=item["content"], source_url=item.get("source_url"),
        )
        for item in matches
    ]
    context = "\n".join(f"- {item.text}" for item in sources)
    law_context = "\n".join(f"- {item.law_name} {item.article_number}: {item.content}" for item in laws)
    answer = "계약서에서 질문과 직접 관련된 문구를 찾지 못했습니다."
    if sources:
        answer = f"계약서 원문을 기준으로 확인되는 내용은 다음과 같습니다.\n{context}"
    if laws:
        answer += f"\n\n관련 법령 근거:\n{law_context}"
    if os.getenv("LAWZIC_LLM_ENABLED", "true").lower() in {"1", "true", "yes", "on"} and (sources or laws):
        prompt = f"""다음 계약서 원문과 법령 근거만 사용하여 질문에 한국어로 답하세요.
근거에 없는 사실은 추측하지 말고, 계약서 내용과 일반적인 법령 설명을 구분하세요.

[질문]
{question}

[계약서 원문]
{context}

[법령 근거]
{law_context}
"""
        try:
            generated = ChatOllama(
                model=os.getenv("OLLAMA_MODEL", "gemma2:2b"),
                base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
                temperature=0, num_predict=700,
            ).invoke(prompt).content.strip()
            if len(re.findall(r"[가-힣]", generated)) >= 8:
                answer = generated
        except Exception:
            pass
    return QuestionResponse(
        answer=answer,
        contract_sources=sources,
        legal_references=laws,
        warning="계약서와 검색된 법령에 근거한 참고 답변이며 법률 자문을 대체하지 않습니다.",
    )


def _font() -> str:
    name = "LawzicKorean"
    if name in pdfmetrics.getRegisteredFontNames():
        return name
    candidates = [
        os.getenv("LAWZIC_REPORT_FONT", ""),
        r"C:\Windows\Fonts\malgun.ttf",
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    ]
    path = next((item for item in candidates if item and Path(item).exists()), None)
    if not path:
        return "Helvetica"
    pdfmetrics.registerFont(TTFont(name, path))
    return name


def create_report(result: AnalysisResponse, filename: str) -> bytes:
    output = io.BytesIO()
    font = _font()
    styles = getSampleStyleSheet()
    title = ParagraphStyle("LawzicTitle", parent=styles["Title"], fontName=font, textColor=colors.HexColor("#15243A"))
    heading = ParagraphStyle(
        "LawzicHeading", parent=styles["Heading2"], fontName=font,
        textColor=colors.HexColor("#15243A"), spaceBefore=14, spaceAfter=8,
    )
    body = ParagraphStyle("LawzicBody", parent=styles["BodyText"], fontName=font, leading=17, wordWrap="CJK")
    cell = ParagraphStyle("LawzicCell", parent=body, fontSize=8, leading=12, wordWrap="CJK")
    cell_header = ParagraphStyle(
        "LawzicCellHeader", parent=cell, textColor=colors.white, alignment=0,
    )
    field_label = ParagraphStyle(
        "LawzicFieldLabel", parent=body, fontSize=9, leading=14,
        textColor=colors.HexColor("#15243A"),
    )
    field_value = ParagraphStyle(
        "LawzicFieldValue", parent=body, fontSize=9, leading=15,
        textColor=colors.HexColor("#20262E"),
    )
    small = ParagraphStyle("LawzicSmall", parent=body, fontSize=8, textColor=colors.HexColor("#68727D"))
    document = SimpleDocTemplate(output, pagesize=A4, rightMargin=42, leftMargin=42, topMargin=46, bottomMargin=46)
    story = [
        Paragraph("LAWZIC 계약서 분석 리포트", title),
        Paragraph(escape(filename), body), Spacer(1, 14),
        Table(
            [
                ["종합 위험도", result.overall_risk_level],
                ["위험 점수", f"{result.overall_score} / 100"],
                ["별도 검토 필요", f"{result.review_required_count}건"],
            ],
            colWidths=[110, 360],
            style=TableStyle([
                ("FONTNAME", (0, 0), (-1, -1), font), ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EEF2F4")),
                ("GRID", (0, 0), (-1, -1), .5, colors.HexColor("#D8D4CA")), ("PADDING", (0, 0), (-1, -1), 8),
            ]),
        ),
        Paragraph("요약", heading), Paragraph(escape(result.summary), body),
        Paragraph("표준근로계약서 체크리스트", heading),
    ]
    checklist = [[
        Paragraph("항목", cell_header),
        Paragraph("상태", cell_header),
        Paragraph("확인 근거", cell_header),
    ]]
    status_labels = {"COMPLIANT": "정상", "RISK": "위험", "MISSING": "누락", "REVIEW": "검토 필요"}
    for item in result.checklist:
        checklist.append([
            Paragraph(escape(item.title), cell),
            Paragraph(status_labels.get(item.status, escape(item.status)), cell),
            Paragraph(escape(item.evidence or "계약서에서 확인되지 않음"), cell),
        ])
    story.append(Table(checklist, colWidths=[82, 68, 320], repeatRows=1, style=TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font), ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#15243A")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), .4, colors.HexColor("#D8D4CA")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ])))
    story.extend([PageBreak(), Paragraph("위험조항 및 수정 제안", title)])
    for index, clause in enumerate(result.clauses, 1):
        page = f" - {clause.location.page}페이지" if clause.location else ""
        fields = [
            ("원문:", clause.original_text),
            ("판단 이유:", clause.reason),
            ("분석 신뢰도:", f"{round(clause.confidence * 100)}%{' · 검토 필요' if clause.review_required else ''}"),
            ("권고:", clause.recommendation),
        ]
        if clause.replacement_text:
            fields.append(("대체 문구:", clause.replacement_text))
        field_rows = [
            [Paragraph(label, field_label), Paragraph(escape(value), field_value)]
            for label, value in fields
        ]
        clause_table = Table(field_rows, colWidths=[72, 398], hAlign="LEFT", style=TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), font),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EEF2F4")),
            ("BOX", (0, 0), (-1, -1), .5, colors.HexColor("#D8D4CA")),
            ("INNERGRID", (0, 0), (-1, -1), .35, colors.HexColor("#E4E1DA")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ]))
        clause_block = [
            Paragraph(f"{index}. [{escape(clause.risk_level)}] {escape(clause.title)}{escape(page)}", heading),
            clause_table,
        ]
        for reference in clause.legal_references:
            clause_block.append(Paragraph(
                f"출처: {escape(reference.law_name)} {escape(reference.article_number)}", small
            ))
        clause_block.append(Spacer(1, 10))
        story.append(CondPageBreak(120))
        story.extend(clause_block)
    story.extend([Spacer(1, 18), Paragraph(" ".join(result.warnings), small)])
    document.build(story)
    return output.getvalue()
