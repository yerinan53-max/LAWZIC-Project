import { useState } from "react";
import { api } from "../api/client";

export default function SignupPage({ onHome, onLogin }) {
  const [form, setForm] = useState({email: "", password: "", name: ""});
  const [error, setError] = useState("");

  const submit = async (event) => {
    event.preventDefault();
    setError("");
    try {
      await api("/auth/signup", {method: "POST", body: JSON.stringify(form)});
      onLogin();
    } catch (e) {
      setError(e.message);
    }
  };

  return <main className="auth-shell"><section className="card auth-card">
    <button className="brand-home auth-brand" onClick={onHome} aria-label="LAWZIC 메인화면으로 이동"><span className="brand-logo">LAW<span>Z</span>IC</span></button>
    <h1>회원가입</h1>
    <p className="muted">계정을 만들고 계약서 분석을 시작하세요.</p>
    <form onSubmit={submit}>
      <label>이름<input value={form.name} onChange={e => setForm({...form, name:e.target.value})} required /></label>
      <label>이메일<input type="email" value={form.email} onChange={e => setForm({...form, email:e.target.value})} required /></label>
      <label>비밀번호<input type="password" minLength="8" value={form.password} onChange={e => setForm({...form, password:e.target.value})} required /></label>
      {error && <p className="error">{error}</p>}<button>가입하기</button>
    </form>
    <button className="link" onClick={onLogin}>이미 계정이 있어요</button>
  </section></main>;
}
