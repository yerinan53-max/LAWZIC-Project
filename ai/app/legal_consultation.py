import os
import re

from langchain_ollama import ChatOllama

from .schemas import LegalChatMessage, LegalChatResponse, LegalReference


LABOR_SCOPE_TERMS = {
    "근로", "근무", "노동", "회사", "사용자", "사업주", "직장", "직원", "근로자",
    "임금", "급여", "월급", "수당", "최저임금", "공제", "체불",
    "연장근로", "야근", "야간근로", "휴일근로", "근로시간", "휴게시간",
    "휴일", "주휴일", "연차", "휴가", "퇴직금", "퇴직급여", "퇴사", "사직",
    "해고", "징계", "감봉", "수습", "근로계약", "위약금", "손해배상",
}
OUT_OF_SCOPE_TERMS = {
    "상속", "상속세", "이혼", "양육권", "부동산", "임대차", "교통사고", "형사",
    "폭행", "사기", "세금", "소득세", "법인세", "특허", "저작권",
}
STOPWORDS = {
    "어떻게", "가능한가요", "있나요", "인가요", "되나요", "대해서", "관련", "질문",
    "회사", "근로자", "사용자", "경우", "그리고", "그러면", "그럼",
}
CONSULTATION_TOPICS = (
    (("연장근로", "연장 근로", "야근", "초과근로", "주 52시간", "주52시간"),
     {"labor-standards-act-50", "labor-standards-act-53", "labor-standards-act-56"}),
    (("야간근로", "야간 근로", "휴일근로", "휴일 근로", "가산수당", "연장수당"),
     {"labor-standards-act-56"}),
    (("임금 공제", "급여 공제", "월급 공제", "임의 공제", "임금체불", "임금 체불",
      "급여체불", "월급을 못", "임금을 못", "지급일"),
     {"labor-standards-act-43"}),
    (("근로시간", "근무시간", "주 40시간", "1일 8시간"),
     {"labor-standards-act-50", "labor-standards-act-53"}),
    (("휴게시간", "휴식시간", "점심시간"),
     {"labor-standards-act-54"}),
    (("주휴일", "유급휴일", "공휴일"),
     {"labor-standards-act-55"}),
    (("연차", "유급휴가", "연차수당"),
     {"labor-standards-act-60"}),
    (("퇴직금", "퇴직급여", "중간정산"),
     {"retirement-benefit-act-8"}),
    (("해고", "징계", "감봉", "정직", "전직"),
     {"labor-standards-act-23"}),
    (("위약금", "벌금", "손해배상 예정", "계약 불이행"),
     {"labor-standards-act-20"}),
    (("근로조건", "근로계약서", "서면 교부", "계약서 교부"),
     {"labor-standards-act-17"}),
)


def contextualize_legal_question(question: str, history: list[LegalChatMessage]) -> str:
    previous_questions = [
        item.content.strip()
        for item in history
        if item.role == "user" and item.content.strip()
    ][-2:]
    return " ".join([*previous_questions, question.strip()])


def is_labor_law_question(question: str, history: list[LegalChatMessage]) -> bool:
    context = contextualize_legal_question(question, history)
    has_labor_term = any(term in context for term in LABOR_SCOPE_TERMS)
    current_has_other_domain = any(term in question for term in OUT_OF_SCOPE_TERMS)
    return has_labor_term and not (current_has_other_domain and not any(
        term in question for term in LABOR_SCOPE_TERMS
    ))


def _query_terms(text: str) -> set[str]:
    return {
        token for token in re.findall(r"[가-힣A-Za-z0-9]+", text.lower())
        if len(token) >= 2 and token not in STOPWORDS
    }


def supported_evidence_ids(query: str) -> set[str]:
    compact = re.sub(r"\s+", " ", query)
    if any(term in compact for term in ("임금", "급여", "월급")) and any(
        term in compact for term in ("공제", "차감", "체불", "못 받", "지급일")
    ):
        return {"labor-standards-act-43"}
    overtime_terms = ("연장근로", "연장 근로", "야근", "초과근로")
    if any(term in compact for term in overtime_terms):
        if any(term in compact for term in ("수당", "임금", "가산", "지급")):
            return {"labor-standards-act-56"}
        if any(term in compact for term in ("몇 시간", "한도", "가능", "주 52", "주52")):
            return {"labor-standards-act-50", "labor-standards-act-53"}
    supported = set()
    for terms, evidence_ids in CONSULTATION_TOPICS:
        if any(term in compact for term in terms):
            supported |= evidence_ids
    return supported


def filter_consultation_matches(query: str, matches: list[dict]) -> list[dict]:
    min_hybrid = float(os.getenv("LEGAL_CHAT_MIN_HYBRID_SCORE", "0.62"))
    min_similarity = float(os.getenv("LEGAL_CHAT_MIN_SIMILARITY", "0.60"))
    query_terms = _query_terms(query)
    allowed_ids = supported_evidence_ids(query)
    if not allowed_ids:
        return []
    accepted = []
    seen = set()
    for item in matches:
        evidence_id = item.get("evidence_id") or (
            item.get("law_name"), item.get("article_number")
        )
        if item.get("evidence_id") not in allowed_ids:
            continue
        if evidence_id in seen:
            continue
        keywords = {
            keyword.strip().lower()
            for keyword in item.get("keywords", "").split("|")
            if keyword.strip()
        }
        content_terms = _query_terms(
            " ".join([
                item.get("title", ""),
                item.get("law_name", ""),
                item.get("article_number", ""),
                item.get("content", ""),
            ])
        )
        term_overlap = query_terms & (keywords | content_terms)
        keyword_overlap = any(keyword in query.lower() for keyword in keywords)
        hybrid_score = float(item.get("hybrid_score", 0))
        similarity = float(item.get("similarity", 0))
        if hybrid_score < min_hybrid:
            continue
        if not term_overlap and not keyword_overlap and similarity < min_similarity:
            continue
        seen.add(evidence_id)
        accepted.append(item)
    return accepted


def search_consultation_laws(
    question: str, history: list[LegalChatMessage], rag,
) -> tuple[str, list[dict]]:
    query = contextualize_legal_question(question, history)
    try:
        matches = rag.search(query, top_k=8)
    except Exception:
        return query, []
    return query, filter_consultation_matches(query, matches)


def _reference(item: dict) -> LegalReference:
    return LegalReference(
        law_name=item["law_name"],
        article_number=item["article_number"],
        content=item["content"],
        source_url=item.get("source_url"),
    )


def _citation_indices(answer: str, reference_count: int) -> list[int]:
    indices = []
    for value in re.findall(r"\[근거\s*(\d+)\]", answer):
        index = int(value)
        if 1 <= index <= reference_count and index not in indices:
            indices.append(index)
    return indices


def _is_grounded_generated_answer(answer: str, matches: list[dict]) -> bool:
    indices = _citation_indices(answer, len(matches))
    if not indices or len(re.findall(r"[가-힣]", answer)) < 8:
        return False
    factual_segments = [
        segment.strip()
        for segment in re.split(r"(?<=[.!?])\s+(?!\[근거)|\n+", answer)
        if len(re.findall(r"[가-힣]", segment)) >= 5
    ]
    if not factual_segments:
        return False
    for segment in factual_segments:
        segment_indices = _citation_indices(segment, len(matches))
        if not segment_indices:
            return False
        cited_terms = set()
        for index in segment_indices:
            cited_terms |= _query_terms(matches[index - 1].get("content", ""))
            cited_terms |= _query_terms(matches[index - 1].get("keywords", ""))
        segment_terms = _query_terms(re.sub(r"\[근거\s*\d+\]", "", segment))
        if len(segment_terms & cited_terms) < 2:
            return False
    return True


def _fallback_answer(matches: list[dict]) -> str:
    lines = ["검색된 노동관계 법령에서 다음 내용을 확인할 수 있습니다."]
    for index, item in enumerate(matches, start=1):
        lines.append(
            f"- {item['law_name']} {item['article_number']}: "
            f"{item['content']} [근거 {index}]"
        )
    lines.append("구체적인 적용 여부는 근로형태와 사업장 상황을 추가로 확인해야 합니다.")
    return "\n".join(lines)


def answer_legal_question(
    question: str, history: list[LegalChatMessage], rag,
) -> LegalChatResponse:
    warning = "검색된 노동관계 법령에 근거한 참고 답변이며 법률 자문이나 법적 판단을 대체하지 않습니다."
    if not is_labor_law_question(question, history):
        return LegalChatResponse(
            answer=(
                "현재 상담은 임금, 근로시간, 휴일·휴가, 해고, 퇴직금 등 "
                "대한민국 노동법 질문만 지원합니다."
            ),
            legal_references=[],
            warning=warning,
            insufficient_evidence=True,
        )

    search_query, matches = search_consultation_laws(question, history, rag)
    if not matches:
        return LegalChatResponse(
            answer=(
                "질문과 충분히 관련된 노동관계 법령 근거를 찾지 못했습니다. "
                "사실관계와 쟁점을 조금 더 구체적으로 입력하거나 전문가에게 확인해 주세요."
            ),
            legal_references=[],
            warning=warning,
            insufficient_evidence=True,
        )

    law_context = "\n".join(
        f"[근거 {index}] {item['law_name']} {item['article_number']}: {item['content']}"
        for index, item in enumerate(matches, start=1)
    )
    answer = _fallback_answer(matches)
    used_matches = matches
    if os.getenv("LAWZIC_LLM_ENABLED", "true").lower() in {"1", "true", "yes", "on"}:
        conversation = "\n".join(
            f"{'사용자' if item.role == 'user' else '상담 AI'}: {item.content}"
            for item in history[-8:]
        )
        prompt = f"""당신은 대한민국 노동법 정보를 안내하는 LAWZIC 상담 AI입니다.
아래 검색된 법령 근거만 사용하여 한국어로 답하세요.
법령 근거에 없는 사실, 판례, 숫자 또는 절차를 추측하지 마세요.
각 사실 설명 문장 끝에 반드시 사용한 [근거 N]을 표시하세요.
사용하지 않은 근거는 인용하지 마세요.
구체적인 적용 조건과 추가로 확인할 사실을 구분하고 법률 자문처럼 단정하지 마세요.

[검색에 사용한 대화 문맥]
{search_query}

[이전 대화]
{conversation or "없음"}

[현재 질문]
{question}

[검색된 법령 근거]
{law_context}
"""
        try:
            generated = ChatOllama(
                model=os.getenv("OLLAMA_MODEL", "gemma2:2b"),
                base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
                temperature=0,
                num_predict=800,
            ).invoke(prompt).content.strip()
            if _is_grounded_generated_answer(generated, matches):
                cited = _citation_indices(generated, len(matches))
                answer = generated
                used_matches = [matches[index - 1] for index in cited]
        except Exception:
            pass

    return LegalChatResponse(
        answer=answer,
        legal_references=[_reference(item) for item in used_matches],
        warning=warning,
        insufficient_evidence=False,
    )
