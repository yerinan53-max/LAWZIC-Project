import { useState } from "react";
import { api } from "../api/client";

const CONSENT_ITEMS = [
  {
    key: "termsAgreed",
    title: "LAWZIC 서비스 이용약관",
    body: "LAWZIC은 근로계약서 분석과 노동법 AI 상담을 보조적으로 제공합니다. 분석 결과는 법률 자문을 대체하지 않으며, 중요한 의사결정은 전문가의 검토가 필요합니다. 이용자는 타인의 개인정보가 포함된 문서를 적법한 권한 없이 업로드해서는 안 됩니다.",
  },
  {
    key: "privacyAgreed",
    title: "개인정보 수집 및 이용",
    body: "수집 항목: 이름, 이메일, 암호화된 비밀번호, 서비스 이용 기록, 업로드한 계약서와 분석·상담 이력\n이용 목적: 회원 식별, 로그인, 계약서 분석, AI 상담, 계정 복구 및 서비스 운영\n보유 기간: 회원 탈퇴 시까지. 다만 관계 법령에 따라 보존할 의무가 있는 정보는 해당 기간 동안 분리 보관\n동의 거부 권리: 동의를 거부할 수 있으나 필수 정보이므로 회원가입과 서비스 이용이 제한됩니다.",
  },
];

export default function SignupPage({ onHome, onLogin }) {
  const [form, setForm] = useState({
    email: "", password: "", passwordConfirm: "", name: "",
    termsAgreed: false, privacyAgreed: false,
  });
  const [error, setError] = useState("");

  const allAgreed = form.termsAgreed && form.privacyAgreed;
  const toggleAll = checked => setForm(value => ({
    ...value, termsAgreed: checked, privacyAgreed: checked,
  }));

  const submit = async event => {
    event.preventDefault();
    setError("");
    if (form.password !== form.passwordConfirm) {
      setError("비밀번호 확인이 일치하지 않습니다.");
      return;
    }
    if (!allAgreed) {
      setError("필수 약관에 모두 동의해야 가입할 수 있습니다.");
      return;
    }
    try {
      const { passwordConfirm, ...request } = form;
      await api("/auth/signup", { method: "POST", body: JSON.stringify(request) });
      onLogin();
    } catch (requestError) {
      setError(requestError.message);
    }
  };

  return <main className="auth-shell"><section className="card auth-card signup-card">
    <button className="brand-home auth-brand" onClick={onHome} aria-label="LAWZIC 메인화면으로 이동"><span className="brand-logo">LAW<span>Z</span>IC</span></button>
    <h1>회원가입</h1>
    <p className="muted">계정을 만들고 계약서 분석을 시작하세요.</p>
    <form onSubmit={submit}>
      <label>이름<input value={form.name} maxLength="50" onChange={event => setForm({ ...form, name: event.target.value })} autoComplete="name" required /></label>
      <label>이메일<input type="email" value={form.email} onChange={event => setForm({ ...form, email: event.target.value })} autoComplete="email" required /></label>
      <label>비밀번호<input type="password" minLength="8" maxLength="72" value={form.password} onChange={event => setForm({ ...form, password: event.target.value })} autoComplete="new-password" required /></label>
      <label>비밀번호 확인<input type="password" minLength="8" maxLength="72" value={form.passwordConfirm} onChange={event => setForm({ ...form, passwordConfirm: event.target.value })} autoComplete="new-password" required /></label>

      <section className="consent-box">
        <label className="consent-all"><input type="checkbox" checked={allAgreed} onChange={event => toggleAll(event.target.checked)} /><span>필수 항목 전체 동의</span></label>
        {CONSENT_ITEMS.map(item => <details className="consent-item" key={item.key}>
          <summary>
            <label onClick={event => event.stopPropagation()}>
              <input type="checkbox" checked={form[item.key]} onChange={event => setForm({ ...form, [item.key]: event.target.checked })} />
              <span><b>필수</b> {item.title}</span>
            </label>
            <span>내용 보기</span>
          </summary>
          <p>{item.body}</p>
        </details>)}
      </section>

      {error && <p className="error">{error}</p>}
      <button disabled={!allAgreed}>가입하기</button>
    </form>
    <button className="link" onClick={onLogin}>이미 계정이 있어요</button>
  </section></main>;
}
