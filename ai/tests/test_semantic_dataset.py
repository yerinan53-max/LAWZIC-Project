import json
from pathlib import Path

import pytest

from app.analyzer import analyze_contract
from app.semantic import evaluate_candidate, split_contract_clauses


DATASET = json.loads(
    (Path(__file__).parent / "data" / "semantic_contract_cases.json").read_text(encoding="utf-8")
)


@pytest.mark.parametrize("case", DATASET, ids=lambda case: case["id"])
def test_semantic_contract_dataset(case):
    result = analyze_contract(100, case["text"])
    detected = {
        clause.clause_type
        for clause in result.clauses
        if not clause.clause_type.startswith("MISSING_")
    }
    assert set(case["expected"]) <= detected
    assert set(case["absent"]).isdisjoint(detected)


def test_clause_segmentation_preserves_article_boundaries():
    text = """제1조 (업무)
근로자는 개발 업무를 수행한다.
제2조 (임금)
회사는 임금을 매월 지급한다."""
    clauses = split_contract_clauses(text)
    assert len(clauses) == 2
    assert clauses[0].heading.startswith("제1조")
    assert clauses[1].heading.startswith("제2조")


def test_semantic_extraction_identifies_subject_action_target_and_negation():
    decision = evaluate_candidate(
        "DAMAGE_WAGE_DEDUCTION",
        "회사는 확정되지 않은 손해액을 임금에서 임의로 공제하지 않는다.",
    )
    assert decision.subject == "회사"
    assert decision.action == "공제"
    assert decision.target in {"손해", "손해액"}
    assert decision.negated is True
    assert decision.confidence >= 0.9
