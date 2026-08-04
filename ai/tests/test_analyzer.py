from app.analyzer import REPLACEMENTS, RULES, analyze_contract


def test_detects_severance_and_missing_sections():
    text = "근로계약서 임금은 매월 25일 지급한다. 근로시간은 09시부터 18시까지다. 퇴직금은 월 급여에 포함한다."
    result = analyze_contract(1, text)
    assert result.overall_score > 0
    assert any(item.clause_type == "SEVERANCE_NONPAYMENT" for item in result.clauses)
    assert any(item.clause_type == "MISSING_HOLIDAY" for item in result.clauses)
    assert next(item for item in result.clauses if item.clause_type == "SEVERANCE_NONPAYMENT").replacement_text
    assert next(item for item in result.checklist if item.code == "WAGE").status == "COMPLIANT"
    assert next(item for item in result.checklist if item.code == "HOLIDAY").status == "MISSING"


def test_replacements_are_contract_clauses_not_repeated_recommendations():
    recommendations = {rule.clause_type: rule.recommendation for rule in RULES}

    assert REPLACEMENTS.keys() == recommendations.keys()
    assert all(
        replacement != recommendations[clause_type]
        for clause_type, replacement in REPLACEMENTS.items()
    )
    assert "근로자의 손해배상 책임은" in REPLACEMENTS["DAMAGE_SHIFTING"]
    assert not REPLACEMENTS["DAMAGE_SHIFTING"].endswith("하세요.")


def test_holiday_checklist_prefers_actual_holiday_clause_over_payday_reference():
    text = """근로계약서
제2조 (근로시간)
근로시간은 09시부터 18시까지로 한다.
제4조 (임금)
월 임금은 기본급 2,700,000원이며 매월 25일 계좌로 지급한다. 지급일이 휴일인 경우에는 그 전 영업일에 지급한다.
제6조 (휴일)
주휴일은 매주 일요일로 하며 관계 법령에서 정한 유급휴일을 보장한다.
제7조 (연차 유급휴가)
연차 유급휴가는 근로기준법 제60조에 따라 부여한다.
"""
    result = analyze_contract(2, text)
    holiday = next(item for item in result.checklist if item.code == "HOLIDAY")
    assert holiday.status == "COMPLIANT"
    assert holiday.evidence.startswith("제6조 (휴일)")
    assert "주휴일은 매주 일요일" in holiday.evidence
    assert "지급일이 휴일" not in holiday.evidence


def test_payday_holiday_reference_does_not_satisfy_holiday_section():
    text = """근로계약서
제2조 (근로시간)
근로시간은 09시부터 18시까지로 한다.
제4조 (임금)
임금은 매월 25일 지급하며 지급일이 휴일인 경우에는 그 전 영업일에 지급한다.
제7조 (연차 유급휴가)
연차 유급휴가는 관계 법령에 따라 부여한다.
"""
    result = analyze_contract(3, text)
    holiday = next(item for item in result.checklist if item.code == "HOLIDAY")
    assert holiday.status == "MISSING"
    assert holiday.evidence is None


def test_detects_all_requested_severe_contract_risks():
    text = """근로계약서
제2조 (근로시간 및 휴게) 근로시간은 매일 08시부터 22시까지로 한다. 업무가 끝날 때까지 추가로 근무해야 하며 휴게시간은 회사 사정에 따라 생략할 수 있다.
제3조 (임금 및 임의 공제) 월 임금은 1,500,000원으로 한다. 지각, 업무 실수, 회사 물품 손상 또는 평가 미달 시 회사가 정한 금액을 임금에서 사전 통보 없이 공제한다.
제4조 (수습기간) 수습기간은 6개월이며 수습 중 임금은 약정 월급의 50%만 지급한다. 평가 결과와 관계없이 회사가 언제든 즉시 해고할 수 있다.
제5조 (연장ㆍ야간ㆍ휴일근로) 연장근로, 야간근로 및 휴일근로 수당은 월 임금에 모두 포함한다. 추가 근무는 무급이며 별도 수당은 지급하지 않는다.
제6조 (휴일 및 연차 포기) 주휴일은 회사가 필요할 때 취소할 수 있다. 근로자는 연차 유급휴가를 사용하지 않으며 미사용 연차수당도 청구하지 않는다.
제7조 (퇴직금 미지급) 퇴직금은 월 급여에 포함한다. 회사는 별도의 퇴직금을 지급하지 않는다.
제8조 (퇴사 제한과 위약금) 근로자는 계약기간 중 퇴사할 수 없다. 위약금 10,000,000원을 지급하고 모든 손해를 전액 배상한다.
제9조 (손해배상) 고의나 과실 여부와 관계없이 근로자가 손해 전액을 배상하며 회사는 해당 금액을 임금에서 공제할 수 있다.
제10조 (일방적 해고 및 이의 포기) 회사는 사전 통보 없이 근로자를 즉시 해고할 수 있다. 근로자는 민원ㆍ진정ㆍ소송을 제기하지 않는다."""
    result = analyze_contract(10, text)
    detected = {item.clause_type for item in result.clauses}
    expected = {
        "LONG_WORK_HOURS", "BREAK_DENIAL", "ARBITRARY_WAGE_DEDUCTION",
        "EXCESSIVE_PROBATION_REDUCTION", "UNPAID_OVERTIME", "UNPAID_PREMIUMS",
        "ANNUAL_LEAVE_WAIVER", "SEVERANCE_NONPAYMENT", "RESIGNATION_RESTRICTION",
        "EXCESSIVE_PENALTY", "DAMAGE_SHIFTING", "DAMAGE_WAGE_DEDUCTION",
        "UNILATERAL_DISMISSAL", "CLAIM_WAIVER",
    }
    assert expected <= detected
    assert all(item.status == "RISK" for item in result.checklist)


def test_safe_wage_deduction_prohibition_is_not_reported_as_risk():
    text = """근로계약서
제2조 (근로시간) 소정근로시간은 09시부터 18시까지이며 휴게시간은 12시부터 13시까지로 한다.
제4조 (임금) 월 임금은 기본급 2,900,000원이며 매월 25일 계좌로 지급한다.
제6조 (휴일) 주휴일은 매주 일요일로 한다.
제7조 (연차 유급휴가) 연차 유급휴가는 근로기준법 제60조에 따라 부여한다.
제13조 (손해배상) 회사는 확정되지 않은 손해액을 임금에서 임의로 공제하지 않는다."""
    result = analyze_contract(11, text)
    detected = {item.clause_type for item in result.clauses}
    assert "ARBITRARY_WAGE_DEDUCTION" not in detected
    assert "DAMAGE_WAGE_DEDUCTION" not in detected
    assert next(item for item in result.checklist if item.code == "WAGE").status == "COMPLIANT"


def test_real_wage_deduction_is_still_reported_after_safe_sentence():
    text = """회사는 확정되지 않은 손해액을 임금에서 임의로 공제하지 않는다.
다만 회사 물품 손상 시 회사가 정한 금액을 임금에서 사전 통보 없이 공제한다."""
    result = analyze_contract(12, text)
    detected = {item.clause_type for item in result.clauses}
    assert "ARBITRARY_WAGE_DEDUCTION" in detected


def test_work_schedule_alias_and_weekdays_are_not_reported_as_complete_omissions():
    text = """근로계약서
제4조 근무시간
월요일~금요일 09:00~18:00 (휴게 12:00~13:00)
임금은 기본급 2,800,000원으로 매월 지급한다.
제7조 연차휴가
연차휴가는 관계 법령에 따른다.
"""
    result = analyze_contract(13, text)
    checklist = {item.code: item for item in result.checklist}
    detected = {item.clause_type for item in result.clauses}

    assert checklist["WORK_HOURS"].status == "COMPLIANT"
    assert "제4조 근무시간" in checklist["WORK_HOURS"].evidence
    assert checklist["HOLIDAY"].status == "REVIEW"
    assert "월요일~금요일" in checklist["HOLIDAY"].evidence
    assert "MISSING_WORK_HOURS" not in detected
    assert "MISSING_HOLIDAY" not in detected
    assert result.review_required_count == 1
