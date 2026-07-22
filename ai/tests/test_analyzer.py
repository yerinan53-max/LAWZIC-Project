from app.analyzer import analyze_contract


def test_detects_severance_and_missing_sections():
    text = "근로계약서 임금은 매월 25일 지급한다. 근로시간은 09시부터 18시까지다. 퇴직금은 월 급여에 포함한다."
    result = analyze_contract(1, text)
    assert result.overall_score > 0
    assert any(item.clause_type == "SEVERANCE_PAY" for item in result.clauses)
    assert any(item.clause_type == "MISSING_HOLIDAY" for item in result.clauses)
