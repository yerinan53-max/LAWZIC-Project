import { useState } from "react";
import { api, oauthLoginUrl, setToken } from "../api/client";

export default function LoginPage({ onLogin, onHome, onSignup, onRecovery }) {
  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState("");

  const submit = async event => {
    event.preventDefault();
    setError("");
    try {
      const data = await api("/auth/login", { method: "POST", body: JSON.stringify(form) });
      setToken(data.accessToken);
      onLogin(data.user);
    } catch (requestError) {
      setError(requestError.message);
    }
  };

  return <main className="auth-shell"><section className="card auth-card">
    <button className="brand-home auth-brand" onClick={onHome} aria-label="LAWZIC 메인화면으로 이동"><span className="brand-logo">LAW<span>Z</span>IC</span></button>
    <h1>로그인</h1>
    <p className="muted">AI가 잠재적인 위험 조항과 관련 법령을 정리합니다.</p>
    <form onSubmit={submit}>
      <label>이메일<input type="email" value={form.email} onChange={event => setForm({ ...form, email: event.target.value })} autoComplete="email" required /></label>
      <label>비밀번호<input type="password" minLength="8" value={form.password} onChange={event => setForm({ ...form, password: event.target.value })} autoComplete="current-password" required /></label>
      {error && <p className="error">{error}</p>}
      <button>로그인</button>
    </form>
    <div className="social-login-divider"><span>또는</span></div>
    <div className="social-login-buttons">
      <a className="social-login google" href={oauthLoginUrl("google")}><b>G</b> Google로 계속하기</a>
      <a className="social-login naver" href={oauthLoginUrl("naver")}><b>N</b> 네이버로 계속하기</a>
    </div>
    <div className="auth-links">
      <button className="link" onClick={() => onRecovery("id")}>아이디 찾기</button>
      <span>·</span>
      <button className="link" onClick={() => onRecovery("password")}>비밀번호 찾기</button>
    </div>
    <button className="link" onClick={onSignup}>처음인가요? 회원가입</button>
  </section></main>;
}
