import re
from dataclasses import dataclass

from .schemas import AnalysisResponse, ChecklistItem, LegalReference, RiskClause, SemanticEvidence
from .semantic import ClauseUnit, SemanticDecision, clause_for_offset, evaluate_candidate, split_contract_clauses


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
    RiskRule("LONG_WORK_HOURS", "장시간 근로", re.compile(r"(?:매일|1일|근로시간|근무시간).{0,25}(?:0?8시.{0,12}22시|14시간|업무가 끝날 때까지|끝날 때까지)"), "HIGH",
             "계약상 근로시간이 지나치게 길거나 종료 시각이 불명확합니다.", "법정 근로시간과 연장근로 한도를 구분하고 시작·종료 시각을 명확히 정하세요.", "근로기준법", "제50조·제53조"),
    RiskRule("BREAK_DENIAL", "휴게시간 미보장", re.compile(r"(?:휴게|휴식)시간.{0,25}(?:생략|없|미부여|보장하지|회사 사정)"), "HIGH",
             "휴게시간을 생략하거나 사용자가 임의로 제한할 수 있는 문구입니다.", "근로시간 도중 법정 휴게시간을 자유롭게 이용할 수 있도록 명시하세요.", "근로기준법", "제54조"),
    RiskRule("ARBITRARY_WAGE_DEDUCTION", "임금의 임의 공제", re.compile(r"(?:지각|업무\s*실수|물품\s*손상|평가\s*미달)[\s\S]{0,90}(?:(?:임금|급여)[\s\S]{0,20})?(?:사전\s*통보\s*없이|회사(?:가)?\s*정한\s*금액)[\s\S]{0,30}(?:공제|차감)|(?:임금|급여)에서[\s\S]{0,30}(?:사전\s*통보\s*없이|임의로)[\s\S]{0,15}(?:공제|차감)"), "HIGH",
             "사용자가 정한 사유와 금액으로 임금을 임의 공제할 수 있는 문구입니다.", "임금은 전액 지급하고 공제가 필요한 경우 법령 또는 적법한 근거와 절차를 따르도록 수정하세요.", "근로기준법", "제43조"),
    RiskRule("EXCESSIVE_PROBATION_REDUCTION", "과도한 수습 감액", re.compile(r"수습.{0,50}(?:임금|급여)?.{0,20}(?:[0-8][0-9]\s*%|절반|감액)"), "HIGH",
             "수습기간 임금 감액의 폭이나 기간이 과도할 가능성이 있습니다.", "수습기간, 적용 대상, 임금 수준과 평가 기준을 관계 법령 범위에서 명확히 정하세요.", "최저임금법", "제5조"),
    RiskRule("UNPAID_OVERTIME", "무급 연장근로", re.compile(r"(?:연장근로|추가\s*(?:근로|근무)|초과\s*(?:근로|근무)).{0,40}(?:무급|지급하지|별도.{0,8}(?:지급|수당).{0,5}(?:없|않))"), "HIGH",
             "연장근로를 무급으로 처리하는 문구입니다.", "실제 연장근로시간을 기록하고 법정 가산수당을 별도로 지급하도록 수정하세요.", "근로기준법", "제56조"),
    RiskRule("UNPAID_PREMIUMS", "연장·야간·휴일수당 미지급", re.compile(r"(?:연장|야간|휴일).{0,25}(?:수당|근로).{0,40}(?:포함|지급하지|별도.{0,8}(?:지급|수당).{0,5}(?:없|않)|무급)"), "HIGH",
             "연장·야간·휴일근로의 가산수당을 지급하지 않거나 불명확하게 포괄하는 문구입니다.", "각 근로시간과 수당의 계산 기준 및 금액을 구분하여 기재하세요.", "근로기준법", "제56조"),
    RiskRule("ANNUAL_LEAVE_WAIVER", "연차 포기", re.compile(r"(?:연차|유급휴가).{0,35}(?:포기|사용할 수 없|부여하지|없으며|수당.{0,10}(?:청구|지급).{0,5}(?:없|않))"), "HIGH",
             "연차휴가 또는 미사용 연차수당을 일률적으로 포기시키는 문구입니다.", "연차유급휴가의 부여와 사용은 관계 법령에 따르도록 수정하세요.", "근로기준법", "제60조"),
    RiskRule("SEVERANCE_NONPAYMENT", "퇴직금 미지급", re.compile(r"퇴직금.{0,35}(?:포함|지급하지|별도.{0,8}지급.{0,5}(?:없|않)|없음)"), "HIGH",
             "퇴직급여를 임금에 포함하거나 별도로 지급하지 않는다는 문구입니다.", "퇴직급여의 발생 요건과 지급 방법을 임금과 구분하여 명확히 작성하세요.", "근로자퇴직급여 보장법", "제8조"),
    RiskRule("RESIGNATION_RESTRICTION", "퇴사 제한", re.compile(r"(?:퇴사|사직|계약기간\s*중).{0,35}(?:할 수 없|금지|제한|승인|허가)"), "HIGH",
             "근로자의 퇴사나 사직을 과도하게 제한하는 문구입니다.", "퇴직 의사 표시와 인수인계 절차를 관계 법령에 맞게 정하세요.", "민법", "제660조"),
    RiskRule("EXCESSIVE_PENALTY", "과도한 위약금", re.compile(r"(?:위약금|벌금).{0,20}(?:[0-9,]+\s*만?\s*원|지급|배상)|(?:[0-9,]+\s*만?\s*원).{0,15}위약금"), "HIGH",
             "근로계약 불이행에 대한 위약금 또는 손해배상액을 미리 정한 문구입니다.", "정액 위약금 조항을 삭제하고 실제 손해와 귀책 사유를 개별적으로 판단하도록 수정하세요.", "근로기준법", "제20조"),
    RiskRule("DAMAGE_SHIFTING", "손해배상 전가", re.compile(r"(?:근로자|을|갑).{0,30}(?:모든|전액|일체).{0,20}손해.{0,15}(?:배상|부담)|손해.{0,35}(?:근로자.{0,15}(?:전액|모두)|전액.{0,10}(?:배상|부담))"), "HIGH",
             "귀책 사유와 실제 손해를 따지지 않고 모든 손해를 근로자에게 전가하는 문구입니다.", "고의·과실, 인과관계와 실제 손해액을 기준으로 책임을 개별 판단하도록 수정하세요.", "근로기준법", "제20조"),
    RiskRule("DAMAGE_WAGE_DEDUCTION", "손해액의 임금 공제", re.compile(r"(?:손해|배상).{0,45}(?:임금|급여).{0,15}(?:공제|차감)|(?:임금|급여).{0,25}(?:손해|배상).{0,15}(?:공제|차감)"), "HIGH",
             "손해배상액을 임금에서 바로 공제할 수 있도록 한 문구입니다.", "임금에서 일방적으로 공제하지 않고 별도의 적법한 절차로 책임을 확정하도록 수정하세요.", "근로기준법", "제43조"),
    RiskRule("UNILATERAL_DISMISSAL", "일방적 해고", re.compile(r"(?:회사|사용자|갑).{0,35}(?:언제든지|즉시|일방적).{0,15}(?:해고|계약.{0,5}종료)|(?:사전\s*통보|예고).{0,15}(?:없이|없).*해고"), "HIGH",
             "해고 사유와 절차 없이 사용자가 일방적으로 해고할 수 있는 문구입니다.", "해고 사유, 서면 통지와 예고 절차를 관계 법령에 맞게 명시하세요.", "근로기준법", "제23조·제26조·제27조"),
    RiskRule("CLAIM_WAIVER", "민원·소송 포기 강요", re.compile(r"(?:민원|진정|소송|이의).{0,45}(?:제기하지|포기|할 수 없|문제\s*삼지|청구하지)"), "HIGH",
             "근로자의 민원·진정·소송 등 권리구제 수단을 미리 포기시키는 문구입니다.", "법적 권리구제 수단을 제한하는 문구를 삭제하세요.", "대한민국 헌법", "제27조"),
]


REQUIRED_SECTIONS = [
    ("WAGE", "임금", ("임금", "급여", "월급"), "근로기준법", "제17조"),
    ("WORK_HOURS", "근로시간", ("근로시간", "근무시간", "시업"), "근로기준법", "제17조"),
    ("HOLIDAY", "휴일", ("휴일", "주휴일"), "근로기준법", "제17조"),
    ("ANNUAL_LEAVE", "연차", ("연차", "유급휴가"), "근로기준법", "제60조"),
]

REPLACEMENTS = {
    rule.clause_type: rule.recommendation for rule in RULES
}

CHECKLIST_RISK_TYPES = {
    "WAGE": {"ARBITRARY_WAGE_DEDUCTION", "EXCESSIVE_PROBATION_REDUCTION", "DAMAGE_WAGE_DEDUCTION"},
    "WORK_HOURS": {"LONG_WORK_HOURS", "BREAK_DENIAL", "UNPAID_OVERTIME", "UNPAID_PREMIUMS"},
    "HOLIDAY": {"UNPAID_PREMIUMS"},
    "ANNUAL_LEAVE": {"ANNUAL_LEAVE_WAIVER"},
}

RISK_WEIGHTS = {"HIGH": 8, "MEDIUM": 4, "LOW": 2, "SAFE": 0}
SIMILAR_RISK_FAMILIES = {
    "ARBITRARY_WAGE_DEDUCTION": "WAGE_DEDUCTION",
    "DAMAGE_WAGE_DEDUCTION": "WAGE_DEDUCTION",
    "WAGE_DEDUCTION": "WAGE_DEDUCTION",
}

DEDUCTION_RISK_TYPES = {
    "ARBITRARY_WAGE_DEDUCTION", "DAMAGE_WAGE_DEDUCTION", "WAGE_DEDUCTION",
}


def _normalized_source(value: str) -> str:
    return re.sub(r"[^0-9A-Za-z가-힣]", "", value).lower()


def deduplicate_findings(findings: list[RiskClause]) -> list[RiskClause]:
    """같은 원문에서 파생된 유사 위험은 가장 확실한 한 건만 유지한다."""
    unique: dict[tuple[str, str], RiskClause] = {}
    order: list[tuple[str, str]] = []
    for item in findings:
        family = SIMILAR_RISK_FAMILIES.get(item.clause_type.upper(), item.clause_type.upper())
        source = _normalized_source(item.original_text)
        key = (family, source if not item.clause_type.startswith("MISSING_") else item.clause_type)
        previous = unique.get(key)
        if previous is None:
            unique[key] = item
            order.append(key)
            continue
        previous_rank = (
            not previous.review_required,
            RISK_WEIGHTS.get(previous.risk_level, 0),
            previous.confidence,
        )
        current_rank = (
            not item.review_required,
            RISK_WEIGHTS.get(item.risk_level, 0),
            item.confidence,
        )
        if current_rank > previous_rank:
            unique[key] = item
    return [unique[key] for key in order]


def calculate_verified_risk(findings: list[RiskClause]) -> tuple[int, str, int]:
    """검토 필요를 제외한 검증 조항만으로 점수와 등급을 계산한다."""
    review_count = sum(item.review_required for item in findings)
    score = min(
        100,
        sum(
            RISK_WEIGHTS.get(item.risk_level, 0)
            for item in findings
            if not item.review_required
        ),
    )
    level = "HIGH" if score >= 60 else "MEDIUM" if score >= 25 else "LOW" if score > 0 else "SAFE"
    return score, level, review_count

SAFE_DEDUCTION_PATTERN = re.compile(
    r"(?:임금|급여)[^.\n]{0,45}(?:공제|차감)\s*"
    r"(?:하지\s*않|하지\s*아니|하지\s*못|할\s*수\s*없|하지\s*않도록)"
)


def is_negated_risk_text(clause_type: str, text: str) -> bool:
    """위험 키워드를 금지하는 안전 문장을 실제 위험으로 뒤집지 않는다."""
    normalized_type = clause_type.upper()
    compact = re.sub(r"\s+", " ", text)
    looks_like_deduction = (
        normalized_type in DEDUCTION_RISK_TYPES
        or ("공제" in compact and any(term in compact for term in ("임금", "급여", "손해")))
    )
    return looks_like_deduction and SAFE_DEDUCTION_PATTERN.search(compact) is not None


def _first_actionable_match(
    rule: RiskRule, text: str, units: list[ClauseUnit],
) -> tuple[re.Match[str], SemanticDecision] | None:
    for match in rule.pattern.finditer(text):
        evidence = _context(text, match.start(), match.end())
        unit = clause_for_offset(units, match.start())
        semantic = evaluate_candidate(rule.clause_type, unit.text or evidence)
        if not semantic.negated and not is_negated_risk_text(rule.clause_type, evidence):
            return match, semantic
    return None


SECTION_SIGNALS = {
    "WAGE": ("기본급", "월 임금", "임금 산정", "지급방법", "계좌로 지급", "지급한다"),
    "WORK_HOURS": ("소정근로", "1일", "1주", "시부터", "시까지", "휴게시간", "휴게"),
    "HOLIDAY": ("주휴일", "매주 일요일", "유급휴일", "근로자의 날", "휴일을 보장"),
    "ANNUAL_LEAVE": ("연차 유급휴가", "제60조", "부여", "휴가를 사용"),
}

SECTION_TITLE_ALIASES = {
    "WORK_HOURS": ("근로시간", "근무시간", "소정근로시간"),
}

SECTION_NEGATIVE_SIGNALS = {
    "HOLIDAY": ("지급일이 휴일", "지급일이 공휴일", "휴일인 경우 그 전", "휴일인 경우에는 그 전"),
}

TIME_RANGE_PATTERN = re.compile(
    r"(?:[01]?\d|2[0-3])(?:\s*시|\s*:\s*[0-5]\d)"
    r"\s*(?:부터|~|～|-|–|—)\s*"
    r"(?:[01]?\d|2[0-3])(?:\s*시|\s*:\s*[0-5]\d)"
)
WEEKDAY_WORK_PATTERN = re.compile(
    r"(?:월요일|월)\s*(?:부터|~|～|-|–|—)\s*(?:금요일|금)"
    r"|주\s*5\s*일"
)


def _context(text: str, start: int, end: int, radius: int = 70) -> str:
    line_start = text.rfind("\n", max(0, start - 300), start)
    line_end = text.find("\n", end, min(len(text), end + 300))
    if line_start >= 0 and line_end >= 0:
        line = text[line_start + 1:line_end].strip()
        if re.match(r"제\s*\d+\s*조", line):
            next_end = text.find("\n", line_end + 1, min(len(text), line_end + 500))
            if next_end >= 0:
                return f"{line} {text[line_end + 1:next_end].strip()}"
        return line
    sentence_start = max(text.rfind(mark, max(0, start - radius), start) for mark in (".", "다.", "요."))
    sentence_end_candidates = [text.find(mark, end, min(len(text), end + radius)) for mark in (".", "다.", "요.")]
    sentence_end_candidates = [value for value in sentence_end_candidates if value >= 0]
    from_index = sentence_start + 1 if sentence_start >= 0 else max(0, start - radius)
    to_index = min(sentence_end_candidates) + 1 if sentence_end_candidates else min(len(text), end + radius)
    return re.sub(r"\s+", " ", text[from_index:to_index]).strip()


def _document_segments(text: str) -> list[str]:
    """조항 제목부터 다음 조항 전까지를 하나의 근거 후보로 묶는다."""
    headings = list(re.finditer(r"(?m)^제\s*\d+\s*조[^\n]*", text))
    segments = []
    if headings:
        if headings[0].start() > 0:
            segments.extend(line.strip() for line in text[:headings[0].start()].splitlines() if line.strip())
        for index, heading in enumerate(headings):
            end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
            segment = re.sub(r"\s+", " ", text[heading.start():end]).strip()
            if segment:
                segments.append(segment)
    else:
        segments = [
            value.strip()
            for value in re.split(r"\n+|(?<=[.!?])\s+", text)
            if value.strip()
        ]
    return segments


def _best_section_evidence(
    text: str, code: str, title: str, keywords: tuple[str, ...],
) -> str | None:
    candidates = []
    for order, segment in enumerate(_document_segments(text)):
        matched = [keyword for keyword in keywords if keyword in segment]
        if not matched:
            continue
        heading = segment[:80]
        score = len(matched) * 2
        title_aliases = SECTION_TITLE_ALIASES.get(code, (title,))
        if any(re.search(rf"제\s*\d+\s*조[^\n]{{0,30}}{re.escape(alias)}", heading) for alias in title_aliases):
            score += 20
        if code == "WORK_HOURS" and TIME_RANGE_PATTERN.search(segment):
            score += 12
        score += sum(4 for signal in SECTION_SIGNALS.get(code, ()) if signal in segment)
        score -= sum(15 for signal in SECTION_NEGATIVE_SIGNALS.get(code, ()) if signal in segment)
        # 동점이면 문서에서 먼저 나온 조항을 선택한다.
        candidates.append((score, -order, segment))
    if not candidates:
        return None
    score, _, evidence = max(candidates, key=lambda item: (item[0], item[1]))
    # 단순 우연 언급만 있는 문장은 필수 조항의 근거로 인정하지 않는다.
    return evidence if score >= 3 else None


def _indirect_holiday_evidence(text: str) -> str | None:
    """근무일 범위는 휴일의 간접 근거지만 유급 주휴일을 확정하는 근거는 아니다."""
    for segment in _document_segments(text):
        if WEEKDAY_WORK_PATTERN.search(segment):
            return segment
    return None


def reconcile_checklist_findings(
    findings: list[RiskClause], checklist: list[ChecklistItem],
) -> list[RiskClause]:
    """체크리스트 근거와 모순되는 '조항 누락' 결과가 최종 리포트에 섞이지 않게 한다."""
    checks = {item.code: item for item in checklist}
    reconciled = []
    for finding in findings:
        if finding.clause_type.startswith("MISSING_"):
            code = finding.clause_type.removeprefix("MISSING_")
            check = checks.get(code)
            if check is not None and (check.evidence is not None or check.status != "MISSING"):
                continue
        reconciled.append(finding)
    return deduplicate_findings(reconciled)


def analyze_contract(contract_id: int, text: str) -> AnalysisResponse:
    findings: list[RiskClause] = []
    clause_units = split_contract_clauses(text)
    for rule in RULES:
        candidate = _first_actionable_match(rule, text, clause_units)
        if candidate:
            match, semantic = candidate
            review_required = semantic.confidence < 0.75
            findings.append(RiskClause(
                clause_type=rule.clause_type, title=rule.title,
                original_text=_context(text, match.start(), match.end()),
                risk_level="LOW" if review_required else rule.level,
                reason=rule.reason, recommendation=rule.recommendation,
                replacement_text=REPLACEMENTS.get(rule.clause_type),
                confidence=semantic.confidence,
                review_required=review_required,
                semantic=SemanticEvidence(
                    subject=semantic.subject, action=semantic.action, target=semantic.target,
                    negated=semantic.negated, conditional=semantic.conditional,
                ),
                legal_references=[LegalReference(law_name=rule.law_name, article_number=rule.article,
                                                  content="공식 법령 원문과 최신 시행일을 반드시 다시 확인하세요.")],
            ))

    section_evidence = {
        code: _best_section_evidence(text, code, title, keywords)
        for code, title, keywords, _, _ in REQUIRED_SECTIONS
    }
    indirect_sections: set[str] = set()
    if section_evidence["HOLIDAY"] is None:
        indirect_holiday = _indirect_holiday_evidence(text)
        if indirect_holiday is not None:
            section_evidence["HOLIDAY"] = indirect_holiday
            indirect_sections.add("HOLIDAY")
    for code, title, keywords, law, article in REQUIRED_SECTIONS:
        if section_evidence[code] is None:
            findings.append(RiskClause(
                clause_type=f"MISSING_{code}", title=f"{title} 조항 누락 가능성", original_text="해당 표현을 찾지 못했습니다.",
                risk_level="MEDIUM", reason=f"계약서에서 {title} 관련 내용을 찾지 못했습니다.",
                recommendation=f"{title} 조건이 명시되어 있는지 원문을 확인하세요.",
                legal_references=[LegalReference(law_name=law, article_number=article,
                                                  content="근로조건 명시 의무와 관련된 조문을 확인하세요.")],
            ))

    findings = deduplicate_findings(findings)
    risk_types = {item.clause_type for item in findings if not item.review_required}
    review_types = {item.clause_type for item in findings if item.review_required}
    checklist = []
    for code, title, keywords, law, article in REQUIRED_SECTIONS:
        evidence = section_evidence[code]
        status = (
            "MISSING" if evidence is None
            else "RISK" if risk_types & CHECKLIST_RISK_TYPES.get(code, set())
            else "REVIEW" if code in indirect_sections or review_types & CHECKLIST_RISK_TYPES.get(code, set())
            else "COMPLIANT"
        )
        checklist.append(ChecklistItem(
            code=code, title=title, status=status,
            evidence=evidence,
            legal_reference=LegalReference(
                law_name=law, article_number=article, content="표준근로계약서 필수 확인 항목입니다."
            ),
        ))
    findings = reconcile_checklist_findings(findings, checklist)
    score, level, clause_review_count = calculate_verified_risk(findings)
    review_count = clause_review_count + sum(item.status == "REVIEW" for item in checklist)
    preview = re.sub(r"\s+", " ", text)[:240]
    summary = f"계약서에서 추출한 주요 내용: {preview}{'…' if len(text) > 240 else ''}"
    return AnalysisResponse(
        contract_id=contract_id, summary=summary, overall_risk_level=level, overall_score=score,
        review_required_count=review_count,
        clauses=findings, checklist=checklist,
        warnings=["계약서 원문과 관련 법령을 함께 확인한 자동 분석 결과입니다.", "본 결과는 법률 자문이나 법적 판단을 대체하지 않습니다."],
    )
