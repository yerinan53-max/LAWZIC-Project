const REQUIRED_CONSENTS = [
  {
    key: "termsAgreed",
    title: "LAWZIC 서비스 이용약관",
    sections: [
      ["1. 서비스의 목적", "LAWZIC은 근로계약서의 위험 조항 분석, 관련 법령 출처 제공, 계약서 기반 질문·답변 및 노동법 AI 상담 기능을 제공합니다."],
      ["2. AI 분석의 성격", "분석 결과와 상담 답변은 법률 검토를 돕기 위한 참고 정보이며 변호사·노무사의 법률 자문이나 행정기관·법원의 판단을 대체하지 않습니다. 중요한 의사결정 전에는 전문가의 확인이 필요합니다."],
      ["3. 이용자의 의무", "이용자는 계약서를 업로드할 적법한 권한을 보유해야 하며, 타인의 개인정보나 영업비밀을 무단으로 업로드하거나 서비스를 불법적인 목적으로 이용해서는 안 됩니다."],
      ["4. 서비스 이용 제한", "시스템 공격, 비정상적인 자동 요청, 타인의 계정 도용 또는 관계 법령 위반이 확인되면 서비스 이용이 제한될 수 있습니다."],
      ["5. 데이터와 계정", "회원은 마이페이지에서 분석·상담 이력을 확인하고 삭제할 수 있으며, 회원 탈퇴 시 관계 법령상 보존 의무가 있는 경우를 제외하고 계정 관련 데이터가 삭제됩니다."],
    ],
  },
  {
    key: "privacyAgreed",
    title: "개인정보 수집 및 이용",
    sections: [
      ["수집 항목", "필수: 이름, 이메일, 암호화된 비밀번호(일반 가입 시), 소셜 로그인 제공자와 제공자 사용자 식별값\n서비스 이용 과정: 업로드한 계약서, 분석 결과, AI 상담 질문·답변, 접속 및 이용 기록"],
      ["수집·이용 목적", "회원 식별과 로그인, 소셜 계정 연결, 계정 복구, 계약서 분석, AI 상담, 분석·상담 이력 제공, 서비스 보안과 오류 대응을 위해 이용합니다."],
      ["보유 및 이용 기간", "회원 탈퇴 시까지 보유한 후 삭제합니다. 다만 관계 법령에서 일정 기간 보존을 요구하는 정보는 해당 기간 동안 다른 정보와 분리하여 보관합니다."],
      ["제3자 제공 및 처리", "원칙적으로 동의 없이 개인정보를 제3자에게 제공하지 않습니다. 서비스 운영상 외부 처리업체를 이용하거나 국외 이전이 발생하는 경우에는 관련 법령에 따라 별도로 고지합니다."],
      ["동의 거부 권리", "개인정보 수집·이용 동의를 거부할 수 있습니다. 다만 위 정보는 회원 식별과 서비스 제공에 필요한 필수 정보이므로 동의하지 않으면 회원가입과 LAWZIC 서비스 이용이 제한됩니다."],
    ],
  },
];

export default function RequiredConsentBox({ value, onChange }) {
  const allAgreed = value.termsAgreed && value.privacyAgreed;
  const updateAll = checked => onChange({
    termsAgreed: checked,
    privacyAgreed: checked,
  });

  return <section className="consent-box">
    <label className="consent-all">
      <input type="checkbox" checked={allAgreed} onChange={event => updateAll(event.target.checked)} />
      <span>필수 항목 전체 동의</span>
    </label>
    {REQUIRED_CONSENTS.map(item => <details className="consent-item" key={item.key}>
      <summary>
        <label onClick={event => event.stopPropagation()}>
          <input
            type="checkbox"
            checked={value[item.key]}
            onChange={event => onChange({ [item.key]: event.target.checked })}
          />
          <span><b>필수</b> {item.title}</span>
        </label>
        <span>내용 보기</span>
      </summary>
      <div className="consent-content">
        {item.sections.map(([heading, content]) => <section key={heading}>
          <strong>{heading}</strong>
          <p>{content}</p>
        </section>)}
      </div>
    </details>)}
  </section>;
}
