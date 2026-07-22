import re
from dataclasses import dataclass

from .schemas import AnalysisResponse, LegalReference, RiskClause


@dataclass(frozen=True)
class RiskRule:
    clause_type: str
    title: str
    pattern: re.Pattern[str]
    level: str
    reason: str
    recommendation: str
    law_name: str
    article: str


RULES = [
    RiskRule("SEVERANCE_PAY", "퇴직금", re.compile(r"퇴직금.{0,20}(포함|지급하지|없음)"), "HIGH",
             "퇴직급여를 임금에 미리 포함하거나 지급하지 않는다는 표현은 별도 검토가 필요합니다.",
             "퇴직급여의 발생 요건과 지급 방법을 임금 조항과 구분하여 명확히 작성하세요.",
             "근로자퇴직급여 보장법", "제8조"),
    RiskRule("DAMAGES", "손해배상", re.compile(r"(손해|위약).{0,30}(전액|배상|위약금)"), "HIGH",
             "근로계약 불이행에 대한 위약금이나 손해배상액을 미리 정한 것으로 해석될 가능성이 있습니다.",
             "실제 발생한 손해와 책임 범위를 개별적으로 판단하도록 문구를 수정하세요.",
             "근로기준법", "제20조"),
    RiskRule("PROBATION", "수습기간", re.compile(r"수습.{0,30}(감액|[0-8][0-9]%|해고)"), "MEDIUM",
             "수습기간의 임금 또는 해고 조건이 근로자에게 불리할 수 있습니다.",
             "수습 기간, 임금 수준, 평가 기준을 구체적으로 명시하고 관련 기준을 확인하세요.",
             "최저임금법", "제5조"),
    RiskRule("OVERTIME", "연장근로", re.compile(r"(연장|야간|휴일).{0,30}(포함|별도.*없|무급)"), "HIGH",
             "연장·야간·휴일근로 가산임금이 포괄적으로 포함되거나 제외된 표현일 수 있습니다.",
             "근로시간과 각 수당의 계산 기준 및 금액을 구분하여 기재하세요.",
             "근로기준법", "제56조"),
]


REQUIRED_SECTIONS = [
    ("WAGE", "임금", ("임금", "급여", "월급"), "근로기준법", "제17조"),
    ("WORK_HOURS", "근로시간", ("근로시간", "근무시간", "시업"), "근로기준법", "제17조"),
    ("HOLIDAY", "휴일", ("휴일", "주휴일"), "근로기준법", "제17조"),
    ("ANNUAL_LEAVE", "연차", ("연차", "유급휴가"), "근로기준법", "제60조"),
]


def _context(text: str, start: int, end: int, radius: int = 70) -> str:
    return text[max(0, start - radius): min(len(text), end + radius)].replace("\n", " ").strip()


def analyze_contract(contract_id: int, text: str) -> AnalysisResponse:
    findings: list[RiskClause] = []
    for rule in RULES:
        match = rule.pattern.search(text)
        if match:
            findings.append(RiskClause(
                clause_type=rule.clause_type, title=rule.title,
                original_text=_context(text, match.start(), match.end()),
                risk_level=rule.level, reason=rule.reason, recommendation=rule.recommendation,
                legal_references=[LegalReference(law_name=rule.law_name, article_number=rule.article,
                                                  content="공식 법령 원문과 최신 시행일을 반드시 다시 확인하세요.")],
            ))

    for code, title, keywords, law, article in REQUIRED_SECTIONS:
        if not any(keyword in text for keyword in keywords):
            findings.append(RiskClause(
                clause_type=f"MISSING_{code}", title=f"{title} 조항 누락 가능성", original_text="해당 표현을 찾지 못했습니다.",
                risk_level="MEDIUM", reason=f"계약서에서 {title} 관련 내용을 찾지 못했습니다.",
                recommendation=f"{title} 조건이 명시되어 있는지 원문을 확인하세요.",
                legal_references=[LegalReference(law_name=law, article_number=article,
                                                  content="근로조건 명시 의무와 관련된 조문을 확인하세요.")],
            ))

    high_count = sum(item.risk_level == "HIGH" for item in findings)
    medium_count = sum(item.risk_level == "MEDIUM" for item in findings)
    score = min(100, high_count * 30 + medium_count * 15)
    level = "HIGH" if score >= 60 else "MEDIUM" if score >= 25 else "LOW" if findings else "SAFE"
    preview = re.sub(r"\s+", " ", text)[:240]
    summary = f"계약서에서 추출한 주요 내용: {preview}{'…' if len(text) > 240 else ''}"
    return AnalysisResponse(
        contract_id=contract_id, summary=summary, overall_risk_level=level, overall_score=score,
        clauses=findings,
        warnings=["현재 MVP는 규칙 기반 분석 결과입니다.", "본 결과는 법률 자문이나 법적 판단을 대체하지 않습니다."],
    )
