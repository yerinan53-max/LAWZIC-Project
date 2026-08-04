import os
import re
import logging
import threading
from typing import Literal, TypedDict

from langchain_ollama import ChatOllama
from langgraph.graph import END, START, StateGraph

from .legal_issue_classifier import ClassifiedIssue, LegalIssueClassifier
from .schemas import LegalChatMessage, LegalChatResponse, LegalReference


logger = logging.getLogger(__name__)
_LLM_SLOT = threading.BoundedSemaphore(1)

LABOR_SCOPE_TERMS = {
    "근로", "근무", "노동", "회사", "사용자", "사업주", "직장", "직원", "근로자",
    "임금", "급여", "월급", "기본급", "성과급", "상여금", "수당", "최저임금",
    "공제", "체불", "감액", "삭감", "감급", "깎",
    "연장근로", "야근", "야간근로", "휴일근로", "근로시간", "휴게시간",
    "휴일", "주휴일", "연차", "휴가", "퇴직금", "퇴직급여", "퇴사", "사직",
    "해고", "징계", "감봉", "수습", "근로계약", "위약금", "손해배상",
    "육아휴직", "출산휴가", "직장 내 괴롭힘", "성희롱", "차별", "기간제", "계약직",
    "단시간근로", "파견", "산재", "산업재해", "고용보험", "실업급여", "노동조합",
    "노조", "단체협약", "채용", "외국인근로자", "노사협의회",
    "권고사직", "사직서", "퇴직 강요", "사직 강요", "부당해고", "해고예고",
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
    (("수습", "수습기간", "수습 기간", "최저임금", "최저 임금"),
     {"minimum-wage-act-5", "minimum-wage-enforcement-decree-3"}),
    (("연장근로", "연장 근로", "야근", "초과근로", "주 52시간", "주52시간"),
     {"labor-standards-act-50", "labor-standards-act-53", "labor-standards-act-56"}),
    (("야간근로", "야간 근로", "휴일근로", "휴일 근로", "가산수당", "연장수당"),
     {"labor-standards-act-56"}),
    (("임금 공제", "급여 공제", "월급 공제", "임의 공제", "임금체불", "임금 체불",
      "급여체불", "월급을 못", "임금을 못", "월급에서 빼", "급여에서 빼",
      "임금에서 빼", "지급일"),
     {"labor-standards-act-43"}),
    (("기본급", "급여 삭감", "임금 삭감", "월급 삭감", "임금 감액", "급여 감액",
      "월급 감액", "감급", "임금을 깎", "급여를 깎", "월급을 깎", "기본급을 깎"),
     {"labor-standards-act-17", "labor-standards-act-43",
      "labor-standards-act-94", "labor-standards-act-95"}),
    (("근로시간", "근무시간", "주 40시간", "1일 8시간"),
     {"labor-standards-act-50", "labor-standards-act-53"}),
    (("휴게시간", "휴식시간", "점심시간"),
     {"labor-standards-act-54"}),
    (("주휴일", "유급휴일", "공휴일"),
     {"labor-standards-act-55"}),
    (("연차", "유급휴가", "연차수당"),
     {"labor-standards-act-60"}),
    (("퇴직금", "퇴직급여", "중간정산"),
     {"retirement-benefit-act-4", "retirement-benefit-act-8"}),
    (("해고", "징계", "감봉", "정직", "전직"),
     {"labor-standards-act-23"}),
    (("권고사직", "사직서 강요", "사직 강요", "퇴직 강요", "부당해고"),
     {"labor-standards-act-23", "labor-standards-act-27", "labor-standards-act-28"}),
    (("위약금", "벌금", "손해배상 예정", "계약 불이행"),
     {"labor-standards-act-20"}),
    (("근로조건", "근로계약서", "서면 교부", "계약서 교부"),
     {"labor-standards-act-17"}),
    (("직장 내 괴롭힘", "직장내 괴롭힘", "괴롭힘 신고"),
     {"labor-standards-act-76-3"}),
)

LEGACY_EVIDENCE_CITATIONS = {
    "labor-standards-act-17": ("근로기준법", "제17조"),
    "labor-standards-act-20": ("근로기준법", "제20조"),
    "labor-standards-act-23": ("근로기준법", "제23조"),
    "labor-standards-act-27": ("근로기준법", "제27조"),
    "labor-standards-act-28": ("근로기준법", "제28조"),
    "labor-standards-act-43": ("근로기준법", "제43조"),
    "labor-standards-act-94": ("근로기준법", "제94조"),
    "labor-standards-act-95": ("근로기준법", "제95조"),
    "labor-standards-act-50": ("근로기준법", "제50조"),
    "labor-standards-act-53": ("근로기준법", "제53조"),
    "labor-standards-act-54": ("근로기준법", "제54조"),
    "labor-standards-act-55": ("근로기준법", "제55조"),
    "labor-standards-act-56": ("근로기준법", "제56조"),
    "labor-standards-act-60": ("근로기준법", "제60조"),
    "labor-standards-act-76-3": ("근로기준법", "제76조의3"),
    "retirement-benefit-act-4": ("근로자퇴직급여 보장법", "제4조"),
    "retirement-benefit-act-8": ("근로자퇴직급여 보장법", "제8조"),
    "minimum-wage-act-5": ("최저임금법", "제5조"),
    "minimum-wage-enforcement-decree-3": ("최저임금법 시행령", "제3조"),
}

FOLLOW_UP_TERMS = (
    "그럼", "그러면", "그 경우", "그때", "앞에서", "위에서",
    "수당은", "기간은", "금액은", "한도는", "어떻게 지급",
)

WAGE_OBJECT_TERMS = ("임금", "급여", "월급", "기본급")
WAGE_DEDUCTION_ACTION_TERMS = (
    "공제", "차감", "빼", "떼", "제하", "상계", "체불", "못 받", "지급일",
)


def contextualize_legal_question(question: str, history: list[LegalChatMessage]) -> str:
    current = question.strip()
    # 현재 질문만으로 주제를 식별할 수 있으면 이전 대화를 섞지 않는다.
    # 서로 다른 질문의 법령이 합쳐지는 검색 오염을 방지한다.
    if supported_evidence_ids(current):
        return current
    if not any(term in current for term in FOLLOW_UP_TERMS):
        return current
    previous_questions = [
        item.content.strip()
        for item in history
        if item.role == "user" and item.content.strip()
    ][-1:]
    return " ".join([*previous_questions, current])


def is_labor_law_question(question: str, history: list[LegalChatMessage]) -> bool:
    context = contextualize_legal_question(question, history)
    has_labor_term = any(term in context for term in LABOR_SCOPE_TERMS)
    current_has_other_domain = any(term in question for term in OUT_OF_SCOPE_TERMS)
    return has_labor_term and not (current_has_other_domain and not any(
        term in question for term in LABOR_SCOPE_TERMS
    ))


def is_consultation_in_scope(
    question: str,
    history: list[LegalChatMessage],
    relevant_law_matches: list[dict],
) -> bool:
    """키워드 또는 실제 관련 법령 검색 결과로 상담 범위를 판정한다."""
    current_has_labor_term = any(term in question for term in LABOR_SCOPE_TERMS)
    current_has_other_domain = any(term in question for term in OUT_OF_SCOPE_TERMS)
    if current_has_other_domain and not current_has_labor_term:
        return False
    return is_labor_law_question(question, history) or bool(relevant_law_matches)


def _query_terms(text: str) -> set[str]:
    return {
        token for token in re.findall(r"[가-힣A-Za-z0-9]+", text.lower())
        if len(token) >= 2 and token not in STOPWORDS
    }


def supported_evidence_ids(query: str) -> set[str]:
    compact = re.sub(r"\s+", " ", query)
    if any(term in compact for term in ("수습", "수습기간", "수습 기간")) and any(
        term in compact for term in ("최저임금", "최저 임금", "적게", "감액", "90%")
    ):
        return {"minimum-wage-act-5", "minimum-wage-enforcement-decree-3"}
    if any(term in compact for term in WAGE_OBJECT_TERMS) and any(
        term in compact for term in WAGE_DEDUCTION_ACTION_TERMS
    ):
        return {"labor-standards-act-43"}
    wage_reduction_objects = ("임금", "급여", "월급", "기본급", "성과급", "상여금")
    wage_reduction_actions = ("깎", "삭감", "감액", "감급", "줄이", "낮추")
    if any(term in compact for term in wage_reduction_objects) and any(
        term in compact for term in wage_reduction_actions
    ):
        return {
            "labor-standards-act-17",
            "labor-standards-act-43",
            "labor-standards-act-94",
            "labor-standards-act-95",
        }
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


def filter_consultation_matches(
    query: str,
    matches: list[dict],
    issue_citations: set[tuple[str, str]] | None = None,
) -> list[dict]:
    min_hybrid = float(os.getenv("LEGAL_CHAT_MIN_HYBRID_SCORE", "0.62"))
    min_similarity = float(os.getenv("LEGAL_CHAT_MIN_SIMILARITY", "0.60"))
    query_terms = _query_terms(query)
    allowed_ids = supported_evidence_ids(query)
    accepted = []
    seen = set()
    for item in matches:
        evidence_id = item.get("evidence_id") or (
            item.get("law_name"), item.get("article_number")
        )
        allowed_citations = {
            LEGACY_EVIDENCE_CITATIONS[evidence_id]
            for evidence_id in allowed_ids
            if evidence_id in LEGACY_EVIDENCE_CITATIONS
        } | (issue_citations or set())
        item_citation = (item.get("law_name"), item.get("article_number"))
        if (allowed_ids or issue_citations) and (
            item.get("evidence_id") not in allowed_ids
            and item_citation not in allowed_citations
        ):
            continue
        seen_key = item_citation if allowed_ids else evidence_id
        if seen_key in seen:
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
        seen.add(seen_key)
        accepted.append(item)
    return accepted


def search_consultation_laws(
    question: str,
    history: list[LegalChatMessage],
    rag,
    classified_issues: list[ClassifiedIssue] | None = None,
) -> tuple[str, list[dict]]:
    query = contextualize_legal_question(question, history)
    issues = classified_issues or []
    expanded_queries = list(dict.fromkeys([
        query,
        *(expanded for selected in issues for expanded in selected.issue.queries),
    ]))
    issue_citations = {
        citation for selected in issues for citation in selected.issue.sources
    }
    try:
        found = {}
        for expanded_query in expanded_queries:
            for match in rag.search(expanded_query, top_k=8):
                key = match.get("evidence_id") or (
                    match.get("law_name"), match.get("article_number"), match.get("content")
                )
                previous = found.get(key)
                if previous is None or float(match.get("hybrid_score", 0)) > float(previous.get("hybrid_score", 0)):
                    found[key] = match
        matches = list(found.values())
        allowed_ids = supported_evidence_ids(query)
        required_citations = {
            LEGACY_EVIDENCE_CITATIONS[evidence_id]
            for evidence_id in allowed_ids
            if evidence_id in LEGACY_EVIDENCE_CITATIONS
        } | issue_citations
        if required_citations and hasattr(rag, "get_by_citations"):
            matches = rag.get_by_citations(
                required_citations, " ".join(expanded_queries),
            ) + matches
    except Exception:
        return query, []
    filtered = filter_consultation_matches(query, matches, issue_citations)
    return query, filtered[:8]


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


def _fallback_answer(matches: list[dict], query: str = "") -> str:
    evidence_indices = {
        item.get("evidence_id"): index
        for index, item in enumerate(matches, start=1)
    }
    citation_indices = {
        (item.get("law_name"), item.get("article_number")): index
        for index, item in enumerate(matches, start=1)
    }
    wage_payment_rule = citation_indices.get(("근로기준법", "제43조"))
    wage_object = any(term in query for term in WAGE_OBJECT_TERMS)
    wage_deduction_action = any(term in query for term in WAGE_DEDUCTION_ACTION_TERMS)
    if wage_payment_rule and wage_object and wage_deduction_action:
        return (
            "원칙적으로 회사는 법령이나 단체협약상 근거 없이 근로자의 임금을 "
            f"임의로 공제할 수 없습니다. [근거 {wage_payment_rule}]\n"
            "근로기준법 제43조는 임금을 근로자에게 전액 지급하도록 정하고 있으며, "
            "법령 또는 단체협약에 특별한 규정이 있는 경우에만 임금 일부를 공제할 수 "
            f"있도록 예외를 두고 있습니다. [근거 {wage_payment_rule}]\n"
            "따라서 지각, 업무상 실수, 회사 장비 파손이나 손해 발생 등을 이유로 회사가 "
            "손해액을 일방적으로 정해 월급에서 바로 빼는 경우에는 위 전액 지급 원칙에 "
            f"위반되는지 검토해야 합니다. [근거 {wage_payment_rule}]\n"
            "실제 공제 명목, 금액, 적용된 법령 또는 단체협약 조항과 근로자의 의사에 "
            "반해 일방적으로 처리됐는지를 확인하는 것이 중요합니다."
        )
    dismissal_rule = citation_indices.get(("근로기준법", "제23조"))
    written_notice = citation_indices.get(("근로기준법", "제27조"))
    remedy = citation_indices.get(("근로기준법", "제28조"))
    if any(term in query for term in ("권고사직", "사직서 강요", "사직 강요", "퇴직 강요")):
        lines = [
            "권고사직은 근로자가 동의해야 성립하므로, 퇴직 의사가 없다면 사직서를 작성하거나 "
            "서명하지 않는 것이 중요합니다.",
            "회사의 요구 내용과 거부 의사를 문자·이메일로 남기고, 면담 기록·녹음·메신저 등 "
            "강요 정황을 보관하세요.",
        ]
        if dismissal_rule:
            lines.append(
                "회사가 근로자의 의사와 무관하게 근로관계를 종료하면 명칭이 권고사직이더라도 "
                f"실질적으로 해고인지 검토해야 하며, 정당한 이유 없는 해고는 제한됩니다. [근거 {dismissal_rule}]"
            )
        if written_notice:
            lines.append(
                "실제로 해고한다면 해고 사유와 시기를 서면으로 통지해 달라고 요청하세요. "
                f"[근거 {written_notice}]"
            )
        if remedy:
            lines.append(
                "부당해고라고 판단되면 해고가 있었던 날부터 3개월 이내에 노동위원회에 "
                f"구제를 신청할 수 있습니다. [근거 {remedy}]"
            )
        return "\n".join(lines)
    retirement_rule = (
        evidence_indices.get("retirement-benefit-act-4")
        or citation_indices.get(("근로자퇴직급여 보장법", "제4조"))
    )
    retirement_amount = (
        evidence_indices.get("retirement-benefit-act-8")
        or citation_indices.get(("근로자퇴직급여 보장법", "제8조"))
    )
    if retirement_rule and any(term in query for term in ("1년", "못 다니", "못다니", "퇴직금", "퇴직급여")):
        answer = (
            "네. 원칙적으로 계속근로기간이 1년 미만이면 법에서 정한 퇴직급여 지급 대상에서 "
            f"제외됩니다. 또한 4주간 평균하여 1주 소정근로시간이 15시간 미만인 경우도 제외됩니다. "
            f"[근거 {retirement_rule}]"
        )
        if retirement_amount:
            answer += (
                "\n반대로 계속근로기간이 1년 이상이고 주 소정근로시간 요건을 충족하면, "
                "계속근로기간 1년에 대해 30일분 이상의 평균임금을 기준으로 퇴직금을 산정합니다. "
                f"[근거 {retirement_amount}]"
            )
        answer += "\n근무기간은 일반적으로 입사일부터 퇴직일까지의 계속근로기간을 기준으로 확인해야 합니다."
        return answer

    probation_law = (
        evidence_indices.get("minimum-wage-act-5")
        or citation_indices.get(("최저임금법", "제5조"))
    )
    probation_rate = (
        evidence_indices.get("minimum-wage-enforcement-decree-3")
        or citation_indices.get(("최저임금법 시행령", "제3조"))
    )
    if probation_law and probation_rate:
        return (
            "원칙적으로 수습기간에도 최저임금 이상을 지급해야 합니다. 다만 1년 이상의 "
            "근로계약을 체결한 수습 근로자는 수습 시작일부터 3개월 이내에 한해 시간급 "
            f"최저임금의 90%를 적용할 수 있습니다. [근거 {probation_law}] "
            f"[근거 {probation_rate}]\n"
            "고용노동부장관이 고시한 단순노무직에는 이 감액 특례가 적용되지 않습니다."
        )

    lines = ["관련 법령을 기준으로 보면 다음과 같습니다."]
    for index, item in enumerate(matches, start=1):
        lines.append(
            f"{item['content']} ({item['law_name']} {item['article_number']}) [근거 {index}]"
        )
    lines.append("구체적인 적용 여부는 근로 형태와 사실관계를 추가로 확인해야 합니다.")
    return "\n".join(lines)


def _build_grounded_response(
    question: str,
    history: list[LegalChatMessage],
    search_query: str,
    matches: list[dict],
) -> LegalChatResponse:
    warning = "검색된 노동관계 법령에 근거한 참고 답변이며 법률 자문이나 법적 판단을 대체하지 않습니다."
    law_context = "\n".join(
        f"[근거 {index}] {item['law_name']} {item['article_number']}: {item['content']}"
        for index, item in enumerate(matches, start=1)
    )
    answer = _fallback_answer(matches, search_query)
    used_matches = matches
    llm_enabled = os.getenv("LAWZIC_LLM_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
    # CPU 기반 Ollama에 여러 상담 요청을 쌓지 않는다. 슬롯이 사용 중이면
    # 이미 검증한 RAG 법령으로 만든 대체 답변을 즉시 반환한다.
    use_llm = llm_enabled and _LLM_SLOT.acquire(blocking=False)
    if not llm_enabled:
        logger.info("상담 LLM 비활성화: 검증된 RAG 대체 답변 사용")
    elif not use_llm:
        logger.info("상담 LLM 슬롯 사용 중: 검증된 RAG 대체 답변 사용")
    if use_llm:
        conversation = "\n".join(
            f"{'사용자' if item.role == 'user' else '상담 AI'}: {item.content}"
            for item in history[-8:]
        )
        prompt = f"""당신은 대한민국 노동법 정보를 안내하는 LAWZIC 상담 AI입니다.
아래 검색된 법령 근거만 사용하여 한국어로 답하세요.
먼저 결론을 한 문장으로 제시하고, 이후 법적 근거와 예외를 설명하세요.
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
                num_predict=int(os.getenv("OLLAMA_CHAT_NUM_PREDICT", "280")),
                keep_alive=os.getenv("OLLAMA_KEEP_ALIVE", "15m"),
                client_kwargs={
                    "timeout": float(os.getenv("OLLAMA_CHAT_TIMEOUT_SECONDS", "120")),
                },
            ).invoke(prompt).content.strip()
            if _is_grounded_generated_answer(generated, matches):
                cited = _citation_indices(generated, len(matches))
                answer = generated
                used_matches = [matches[index - 1] for index in cited]
            else:
                logger.warning(
                    "상담 LLM 답변 근거 검증 탈락: answer_length=%d, valid_citations=%s",
                    len(generated),
                    _citation_indices(generated, len(matches)),
                )
        except Exception as exc:
            logger.warning(
                "상담 LLM 호출 실패, RAG 근거 답변으로 전환: %s: %s",
                type(exc).__name__,
                exc,
            )
        finally:
            _LLM_SLOT.release()

    return LegalChatResponse(
        answer=answer,
        legal_references=[_reference(item) for item in used_matches],
        warning=warning,
        insufficient_evidence=False,
    )


class LegalConsultationState(TypedDict, total=False):
    question: str
    history: list[LegalChatMessage]
    search_query: str
    classified_issues: list[ClassifiedIssue]
    matches: list[dict]
    response: LegalChatResponse


class LegalConsultationAgent:
    """노동법 상담의 분류·검색·검증·응답을 실행하는 LangGraph 워크플로."""

    WARNING = "검색된 노동관계 법령에 근거한 참고 답변이며 법률 자문이나 법적 판단을 대체하지 않습니다."

    def __init__(self, rag):
        self.rag = rag
        self.classifier = LegalIssueClassifier(rag)
        builder = StateGraph(LegalConsultationState)
        builder.add_node("prepare", self._prepare)
        builder.add_node("classify_issues", self._classify_issues)
        builder.add_node("retrieve_laws", self._retrieve_laws)
        builder.add_node("out_of_scope", self._out_of_scope)
        builder.add_node("insufficient_evidence", self._insufficient_evidence)
        builder.add_node("generate_answer", self._generate_answer)
        builder.add_node("verify_sources", self._verify_sources)
        builder.add_edge(START, "prepare")
        builder.add_edge("prepare", "classify_issues")
        builder.add_edge("classify_issues", "retrieve_laws")
        builder.add_conditional_edges(
            "retrieve_laws", self._route_after_retrieval,
            {
                "out_of_scope": "out_of_scope",
                "insufficient": "insufficient_evidence",
                "answer": "generate_answer",
            },
        )
        builder.add_edge("out_of_scope", END)
        builder.add_edge("insufficient_evidence", END)
        builder.add_edge("generate_answer", "verify_sources")
        builder.add_edge("verify_sources", END)
        self.graph = builder.compile()

    @staticmethod
    def _prepare(state: LegalConsultationState) -> dict:
        return {
            "search_query": contextualize_legal_question(
                state["question"], state.get("history", []),
            ),
        }

    def _classify_issues(self, state: LegalConsultationState) -> dict:
        return {
            "classified_issues": self.classifier.classify(state["search_query"]),
        }

    def _retrieve_laws(self, state: LegalConsultationState) -> dict:
        search_query, matches = search_consultation_laws(
            state["question"], state.get("history", []), self.rag,
            state.get("classified_issues", []),
        )
        return {"search_query": search_query, "matches": matches}

    @staticmethod
    def _route_after_retrieval(
        state: LegalConsultationState,
    ) -> Literal["out_of_scope", "insufficient", "answer"]:
        question = state["question"]
        history = state.get("history", [])
        matches = state.get("matches", [])
        issues = state.get("classified_issues", [])
        current_has_labor_term = any(term in question for term in LABOR_SCOPE_TERMS)
        current_has_other_domain = any(term in question for term in OUT_OF_SCOPE_TERMS)
        if current_has_other_domain and not current_has_labor_term:
            return "out_of_scope"
        if not (is_labor_law_question(question, history) or issues or matches):
            return "out_of_scope"
        return "answer" if matches else "insufficient"

    @classmethod
    def _out_of_scope(cls, _state: LegalConsultationState) -> dict:
        return {"response": LegalChatResponse(
            answer=(
                "현재 상담은 임금, 근로시간, 휴일·휴가, 해고, 퇴직금 등 "
                "대한민국 노동법 질문만 지원합니다."
            ),
            legal_references=[], warning=cls.WARNING, insufficient_evidence=True,
        )}

    @classmethod
    def _insufficient_evidence(cls, _state: LegalConsultationState) -> dict:
        return {"response": LegalChatResponse(
            answer=(
                "질문과 충분히 관련된 노동관계 법령 근거를 찾지 못했습니다. "
                "사실관계와 쟁점을 조금 더 구체적으로 입력하거나 전문가에게 확인해 주세요."
            ),
            legal_references=[], warning=cls.WARNING, insufficient_evidence=True,
        )}

    @staticmethod
    def _generate_answer(state: LegalConsultationState) -> dict:
        return {"response": _build_grounded_response(
            state["question"], state.get("history", []),
            state["search_query"], state["matches"],
        )}

    @classmethod
    def _verify_sources(cls, state: LegalConsultationState) -> dict:
        response = state["response"]
        # 생성 답변에서 실제 인용한 번호만 _build_grounded_response가 이미 선별한다.
        # 이 노드는 잘못된 빈 출처 성공 응답이 외부로 나가지 않도록 최종 불변식을 보장한다.
        if not response.legal_references:
            return cls._insufficient_evidence(state)
        return {"response": response}

    def answer(
        self, question: str, history: list[LegalChatMessage],
    ) -> LegalChatResponse:
        state = self.graph.invoke({"question": question, "history": history})
        return state["response"]


def answer_legal_question(
    question: str, history: list[LegalChatMessage], rag,
) -> LegalChatResponse:
    """기존 호출부와 테스트를 위한 호환 함수."""
    return LegalConsultationAgent(rag).answer(question, history)
