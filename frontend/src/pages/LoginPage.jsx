import { useState } from "react";
import { api, setToken } from "../api/client";

export default function LoginPage({ onLogin, onHome, onSignup }) {
  const [form, setForm] = useState({email: "", password: ""});
  const [error, setError] = useState("");

  const submit = async (event) => {
    event.preventDefault();
    setError("");
    try {
      const data = await api("/auth/login", {method: "POST", body: JSON.stringify(form)});
      setToken(data.accessToken);
      onLogin(data.user);
    } catch (e) {
      setError(e.message);
    }
  };

  return <main className="auth-shell"><section className="card auth-card">
    <button className="brand-home auth-brand" onClick={onHome} aria-label="LAWZIC 메인화면으로 이동"><span className="brand-logo">LAW<span>Z</span>IC</span></button>
    <h1>로그인</h1>
    <p className="muted">AI가 잠재적인 위험 조항과 확인할 법령을 정리합니다.</p>
    <form onSubmit={submit}>
      <label>이메일<input type="email" value={form.email} onChange={e => setForm({...form, email:e.target.value})} required /></label>
      <label>비밀번호<input type="password" minLength="8" value={form.password} onChange={e => setForm({...form, password:e.target.value})} required /></label>
      {error && <p className="error">{error}</p>}<button>로그인</button>
    </form>
    <button className="link" onClick={onSignup}>처음인가요? 회원가입</button>
  </section></main>;
}
