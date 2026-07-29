import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ClauseUnit:
    heading: str | None
    text: str
    start: int
    end: int


@dataclass(frozen=True)
class SemanticDecision:
    subject: str | None
    action: str | None
    target: str | None
    negated: bool
    conditional: bool
    confidence: float
    clause_text: str


ACTION_TERMS = {
    "LONG_WORK_HOURS": ("근로", "근무"),
    "BREAK_DENIAL": ("생략", "미부여", "보장"),
    "ARBITRARY_WAGE_DEDUCTION": ("공제", "차감"),
    "EXCESSIVE_PROBATION_REDUCTION": ("감액", "지급"),
    "UNPAID_OVERTIME": ("지급", "무급"),
    "UNPAID_PREMIUMS": ("지급", "포함"),
    "ANNUAL_LEAVE_WAIVER": ("포기", "사용", "부여", "청구"),
    "SEVERANCE_NONPAYMENT": ("지급", "포함"),
    "RESIGNATION_RESTRICTION": ("퇴사", "사직"),
    "EXCESSIVE_PENALTY": ("위약금", "벌금", "지급"),
    "DAMAGE_SHIFTING": ("배상", "부담"),
    "DAMAGE_WAGE_DEDUCTION": ("공제", "차감"),
    "UNILATERAL_DISMISSAL": ("해고", "종료"),
    "CLAIM_WAIVER": ("제기", "포기", "청구"),
}

TARGET_TERMS = {
    "LONG_WORK_HOURS": ("근로시간", "근무시간"),
    "BREAK_DENIAL": ("휴게시간", "휴식시간"),
    "ARBITRARY_WAGE_DEDUCTION": ("임금", "급여"),
    "EXCESSIVE_PROBATION_REDUCTION": ("수습", "임금", "급여"),
    "UNPAID_OVERTIME": ("연장근로", "추가 근무", "수당"),
    "UNPAID_PREMIUMS": ("연장", "야간", "휴일", "수당"),
    "ANNUAL_LEAVE_WAIVER": ("연차", "유급휴가", "연차수당"),
    "SEVERANCE_NONPAYMENT": ("퇴직금", "퇴직급여"),
    "RESIGNATION_RESTRICTION": ("퇴사", "사직"),
    "EXCESSIVE_PENALTY": ("위약금", "벌금"),
    "DAMAGE_SHIFTING": ("손해", "손해액"),
    "DAMAGE_WAGE_DEDUCTION": ("손해", "임금", "급여"),
    "UNILATERAL_DISMISSAL": ("근로자", "계약"),
    "CLAIM_WAIVER": ("민원", "진정", "소송", "이의"),
}

ACTORS = ("회사", "사용자", "갑", "근로자", "을")
CONDITIONS = ("경우", "때", "시 ", "한 경우", "발생하면", "필요한 경우", "다만")

# 이 행위를 하지 않는다는 표현이 안전 의미가 되는 위험 유형만 지정한다.
SAFE_NEGATION_ACTIONS = {
    "BREAK_DENIAL": ("생략", "미부여", "보장하지"),
    "ARBITRARY_WAGE_DEDUCTION": ("공제", "차감"),
    "EXCESSIVE_PROBATION_REDUCTION": ("감액",),
    "EXCESSIVE_PENALTY": ("위약금", "벌금", "부과"),
    "DAMAGE_SHIFTING": ("배상", "부담"),
    "DAMAGE_WAGE_DEDUCTION": ("공제", "차감"),
    "UNILATERAL_DISMISSAL": ("해고", "종료"),
}


def split_contract_clauses(text: str) -> list[ClauseUnit]:
    headings = list(re.finditer(r"(?m)^제\s*\d+\s*조[^\n]*", text))
    if not headings:
        return [
            ClauseUnit(None, match.group().strip(), match.start(), match.end())
            for match in re.finditer(r"[^.\n]+(?:\.|$)", text)
            if match.group().strip()
        ]
    units: list[ClauseUnit] = []
    if headings[0].start() > 0:
        prefix = text[:headings[0].start()].strip()
        if prefix:
            units.append(ClauseUnit(None, prefix, 0, headings[0].start()))
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        units.append(ClauseUnit(
            heading.group().strip(),
            re.sub(r"\s+", " ", text[heading.start():end]).strip(),
            heading.start(),
            end,
        ))
    return units


def clause_for_offset(units: list[ClauseUnit], offset: int) -> ClauseUnit:
    return next((unit for unit in units if unit.start <= offset < unit.end), units[-1])


def _first_term(text: str, terms: tuple[str, ...]) -> str | None:
    matches = [(text.find(term), term) for term in terms if term in text]
    return min(matches, default=(0, None), key=lambda item: item[0])[1]


def _safe_negation(clause_type: str, text: str) -> bool:
    for action in SAFE_NEGATION_ACTIONS.get(clause_type, ()):
        if re.search(
            rf"{re.escape(action)}\s*(?:하지\s*않|하지\s*아니|하지\s*못|할\s*수\s*없|하지\s*않도록)",
            text,
        ):
            return True
    return False


def evaluate_candidate(clause_type: str, clause_text: str) -> SemanticDecision:
    compact = re.sub(r"\s+", " ", clause_text).strip()
    subject = _first_term(compact, ACTORS)
    action = _first_term(compact, ACTION_TERMS.get(clause_type, ()))
    target = _first_term(compact, TARGET_TERMS.get(clause_type, ()))
    conditional = any(term in compact for term in CONDITIONS)
    negated = _safe_negation(clause_type, compact)
    confidence = 0.35
    confidence += 0.15 if subject else 0
    confidence += 0.25 if action else 0
    confidence += 0.20 if target else 0
    confidence += 0.05 if conditional else 0
    if negated:
        confidence = max(confidence, 0.9)
    return SemanticDecision(
        subject=subject,
        action=action,
        target=target,
        negated=negated,
        conditional=conditional,
        confidence=min(1.0, round(confidence, 2)),
        clause_text=compact,
    )
