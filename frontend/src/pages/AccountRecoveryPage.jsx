import { useState } from "react";
import { api } from "../api/client";

export default function AccountRecoveryPage({ initialMode, onHome, onLogin }) {
  const [mode, setMode] = useState(initialMode === "password" ? "password" : "id");
  const [form, setForm] = useState({ name: "", email: "", code: "", password: "", confirm: "" });
  const [codeSent, setCodeSent] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [sending, setSending] = useState(false);

  const submit = async event => {
    event.preventDefault();
    setMessage("");
    setError("");
    setSending(true);
    try {
      const response = await api(mode === "id" ? "/auth/find-login-id" : "/auth/password-reset/request", {
        method: "POST",
        body: JSON.stringify(mode === "id" ? form : { email: form.email }),
      });
      setMessage(response.message);
      if (mode === "password") setCodeSent(true);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSending(false);
    }
  };

  const resetPassword = async event => {
    event.preventDefault();
    setMessage("");
    setError("");
    if (form.password !== form.confirm) {
      setError("새 비밀번호와 비밀번호 확인이 일치하지 않습니다.");
      return;
    }
    setSending(true);
    try {
      const response = await api("/auth/password-reset/confirm", {
        method: "POST",
        body: JSON.stringify({ email: form.email, code: form.code, newPassword: form.password }),
      });
      setMessage(response.message);
      setForm(value => ({ ...value, code: "", password: "", confirm: "" }));
      setCodeSent(false);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSending(false);
    }
  };

  const changeMode = nextMode => {
    setMode(nextMode);
    setMessage("");
    setError("");
    setCodeSent(false);
  };

  return <main className="auth-shell"><section className="card auth-card">
    <button className="brand-home auth-brand" onClick={onHome} aria-label="LAWZIC 메인화면으로 이동"><span className="brand-logo">LAW<span>Z</span>IC</span></button>
    <div className="recovery-tabs">
      <button className={mode === "id" ? "active" : ""} onClick={() => changeMode("id")}>아이디 찾기</button>
      <button className={mode === "password" ? "active" : ""} onClick={() => changeMode("password")}>비밀번호 찾기</button>
    </div>
    <h1>{mode === "id" ? "가입 이메일 찾기" : "비밀번호 재설정"}</h1>
    <p className="muted">{mode === "id"
      ? "가입할 때 입력한 이름과 이메일로 계정을 확인합니다."
      : "가입 이메일로 10분 동안 유효한 6자리 인증번호를 보냅니다."}</p>
    {!codeSent ? <form onSubmit={submit}>
      {mode === "id" && <label>이름<input value={form.name} maxLength="50" onChange={event => setForm({ ...form, name: event.target.value })} required /></label>}
      <label>이메일<input type="email" value={form.email} onChange={event => setForm({ ...form, email: event.target.value })} autoComplete="email" required /></label>
      {message && <p className="success-notice">{message}</p>}
      {error && <p className="error">{error}</p>}
      <button disabled={sending}>{sending ? "요청 중…" : mode === "id" ? "이메일로 안내 받기" : "인증번호 받기"}</button>
    </form> : <form onSubmit={resetPassword}>
      <label>이메일<input type="email" value={form.email} disabled /></label>
      <label>6자리 인증번호<input inputMode="numeric" pattern="[0-9]{6}" maxLength="6" value={form.code} onChange={event => setForm({ ...form, code: event.target.value.replace(/\D/g, "") })} autoComplete="one-time-code" required /></label>
      <label>새 비밀번호<input type="password" minLength="8" maxLength="72" value={form.password} onChange={event => setForm({ ...form, password: event.target.value })} autoComplete="new-password" required /></label>
      <label>새 비밀번호 확인<input type="password" minLength="8" maxLength="72" value={form.confirm} onChange={event => setForm({ ...form, confirm: event.target.value })} autoComplete="new-password" required /></label>
      {message && <p className="success-notice">{message}</p>}
      {error && <p className="error">{error}</p>}
      <button disabled={sending}>{sending ? "변경 중…" : "비밀번호 변경"}</button>
      <button type="button" className="secondary" onClick={() => { setCodeSent(false); setMessage(""); setError(""); }}>인증번호 다시 받기</button>
    </form>}
    <button className="link" onClick={onLogin}>로그인으로 돌아가기</button>
  </section></main>;
}
