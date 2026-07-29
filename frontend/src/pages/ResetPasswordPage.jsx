import { useState } from "react";
import { api } from "../api/client";

export default function ResetPasswordPage({ token, onHome, onLogin }) {
  const [form, setForm] = useState({ password: "", confirm: "" });
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const submit = async event => {
    event.preventDefault();
    setError("");
    if (!token) {
      setError("재설정 토큰이 없습니다. 비밀번호 찾기를 다시 진행하세요.");
      return;
    }
    if (form.password !== form.confirm) {
      setError("비밀번호 확인이 일치하지 않습니다.");
      return;
    }
    setSaving(true);
    try {
      const response = await api("/auth/password-reset/confirm", {
        method: "POST",
        body: JSON.stringify({ token, newPassword: form.password }),
      });
      setMessage(response.message);
      setForm({ password: "", confirm: "" });
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSaving(false);
    }
  };

  return <main className="auth-shell"><section className="card auth-card">
    <button className="brand-home auth-brand" onClick={onHome} aria-label="LAWZIC 메인화면으로 이동"><span className="brand-logo">LAW<span>Z</span>IC</span></button>
    <h1>새 비밀번호 설정</h1>
    <p className="muted">8자 이상의 새 비밀번호를 입력하세요.</p>
    <form onSubmit={submit}>
      <label>새 비밀번호<input type="password" minLength="8" maxLength="72" value={form.password} onChange={event => setForm({ ...form, password: event.target.value })} autoComplete="new-password" required /></label>
      <label>새 비밀번호 확인<input type="password" minLength="8" maxLength="72" value={form.confirm} onChange={event => setForm({ ...form, confirm: event.target.value })} autoComplete="new-password" required /></label>
      {message && <p className="success-notice">{message}</p>}
      {error && <p className="error">{error}</p>}
      <button disabled={saving || Boolean(message)}>{saving ? "변경 중…" : "비밀번호 변경"}</button>
    </form>
    <button className="link" onClick={onLogin}>로그인으로 이동</button>
  </section></main>;
}
