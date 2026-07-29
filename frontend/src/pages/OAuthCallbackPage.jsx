import { useEffect, useState } from "react";
import { api, setToken } from "../api/client";
import RequiredConsentBox from "../components/RequiredConsentBox";

export default function OAuthCallbackPage({ ticket, providerError, onLogin, onHome }) {
  const [status, setStatus] = useState(null);
  const [form, setForm] = useState({ email: "", password: "" });
  const [consents, setConsents] = useState({ termsAgreed: false, privacyAgreed: false });
  const [error, setError] = useState(providerError || "");
  const [busy, setBusy] = useState(Boolean(ticket));

  const finish = data => {
    setToken(data.accessToken);
    onLogin(data.user);
  };

  useEffect(() => {
    if (!ticket || providerError) {
      setBusy(false);
      if (!providerError) setError("유효한 소셜 로그인 티켓이 없습니다.");
      return;
    }
    api("/auth/oauth/ticket", { method: "POST", body: JSON.stringify({ ticket }) })
      .then(info => {
        setStatus(info);
        if (info.linkingRequired || info.consentRequired) {
          setBusy(false);
          return null;
        }
        return api("/auth/oauth/exchange", { method: "POST", body: JSON.stringify({ ticket }) });
      })
      .then(data => {
        if (data) finish(data);
      })
      .catch(requestError => {
        setError(requestError.message);
        setBusy(false);
      });
  }, [ticket, providerError]);

  const link = async event => {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      finish(await api("/auth/oauth/link", {
        method: "POST",
        body: JSON.stringify({ ticket, email: form.email, password: form.password }),
      }));
    } catch (requestError) {
      setError(requestError.message);
      setBusy(false);
    }
  };

  const register = async event => {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      finish(await api("/auth/oauth/register", {
        method: "POST",
        body: JSON.stringify({ ticket, ...consents }),
      }));
    } catch (requestError) {
      setError(requestError.message);
      setBusy(false);
    }
  };

  return <main className="auth-shell"><section className="card auth-card">
    <button className="brand-home auth-brand" onClick={onHome} aria-label="LAWZIC 메인화면으로 이동"><span className="brand-logo">LAW<span>Z</span>IC</span></button>
    <h1>소셜 로그인</h1>
    {busy && <p className="muted">안전하게 로그인 정보를 확인하고 있습니다.</p>}
    {status?.linkingRequired && <>
      <p className="privacy-notice">{status.maskedEmail}과 같은 이메일의 기존 LAWZIC 계정이 있습니다. 자동으로 합치지 않으며, 기존 비밀번호 확인 후 {status.provider} 계정을 연결합니다.</p>
      <form onSubmit={link}>
        <label>기존 계정 이메일<input type="email" value={form.email} onChange={event => setForm({ ...form, email: event.target.value })} required /></label>
        <label>기존 계정 비밀번호<input type="password" value={form.password} onChange={event => setForm({ ...form, password: event.target.value })} autoComplete="current-password" required /></label>
        <button disabled={busy}>확인하고 계정 연결</button>
      </form>
    </>}
    {status?.consentRequired && <>
      <p className="privacy-notice">소셜 계정 인증이 완료되었습니다. LAWZIC 신규 가입을 위해 필수 약관에 동의해 주세요.</p>
      <form onSubmit={register}>
        <RequiredConsentBox value={consents} onChange={changes => setConsents({ ...consents, ...changes })} />
        <button disabled={busy || !consents.termsAgreed || !consents.privacyAgreed}>동의하고 가입</button>
      </form>
    </>}
    {error && <p className="error">{error}</p>}
    {!busy && !status?.linkingRequired && !status?.consentRequired && <button className="link" onClick={onHome}>메인으로 돌아가기</button>}
  </section></main>;
}
