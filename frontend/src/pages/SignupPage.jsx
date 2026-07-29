import { useState } from "react";
import { api } from "../api/client";
import RequiredConsentBox from "../components/RequiredConsentBox";

export default function SignupPage({ onHome, onLogin }) {
  const [form, setForm] = useState({
    email: "", password: "", passwordConfirm: "", name: "",
    termsAgreed: false, privacyAgreed: false,
  });
  const [error, setError] = useState("");

  const allAgreed = form.termsAgreed && form.privacyAgreed;

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

      <RequiredConsentBox value={form} onChange={changes => setForm({ ...form, ...changes })} />

      {error && <p className="error">{error}</p>}
      <button disabled={!allAgreed}>가입하기</button>
    </form>
    <button className="link" onClick={onLogin}>이미 계정이 있어요</button>
  </section></main>;
}
