import json
from pathlib import Path

import pytest

from app.analyzer import calculate_verified_risk, deduplicate_findings, analyze_contract
from app.schemas import RiskClause


CASES = json.loads(
    (Path(__file__).parent / "data" / "risk_grade_contract_cases.json").read_text(encoding="utf-8")
)


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["id"])
def test_representative_contract_risk_grade(case):
    result = analyze_contract(100, case["text"])
    assert result.overall_risk_level == case["expected_level"]
    assert result.review_required_count == sum(item.review_required for item in result.clauses)


def _finding(clause_type, original_text, *, review_required=False, level="HIGH"):
    return RiskClause(
        clause_type=clause_type,
        title=clause_type,
        original_text=original_text,
        risk_level="LOW" if review_required else level,
        reason="테스트 판단 이유",
        recommendation="테스트 권고",
        review_required=review_required,
        confidence=0.6 if review_required else 0.95,
    )


def test_review_items_are_counted_separately_and_do_not_raise_score():
    findings = [_finding("LLM_ONLY", "문맥이 불완전한 조항", review_required=True)]
    score, level, review_count = calculate_verified_risk(findings)
    assert (score, level, review_count) == (0, "SAFE", 1)


def test_similar_risks_from_the_same_source_are_scored_once():
    source = "회사는 손해배상액을 근로자의 임금에서 바로 공제할 수 있다."
    findings = [
        _finding("ARBITRARY_WAGE_DEDUCTION", source),
        _finding("DAMAGE_WAGE_DEDUCTION", source),
    ]
    unique = deduplicate_findings(findings)
    score, level, review_count = calculate_verified_risk(unique)
    assert len(unique) == 1
    assert (score, level, review_count) == (8, "LOW", 0)
