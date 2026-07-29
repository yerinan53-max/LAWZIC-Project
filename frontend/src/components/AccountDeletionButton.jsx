import { useState } from "react";

const CONFIRMATION = "회원 탈퇴";

export default function AccountDeletionButton({ onDeleteAccount }) {
  const [open, setOpen] = useState(false);
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const close = () => {
    if (busy) return;
    setOpen(false);
    setPassword("");
    setConfirmation("");
    setError("");
  };

  const submit = async event => {
    event.preventDefault();
    if (confirmation !== CONFIRMATION || !password) return;
    setBusy(true);
    setError("");
    try {
      await onDeleteAccount(password);
    } catch (requestError) {
      setError(requestError.message);
      setBusy(false);
    }
  };

  return <>
    <button className="account-delete-trigger" onClick={() => setOpen(true)}>회원 탈퇴</button>
    {open && <div className="account-modal" role="dialog" aria-modal="true" aria-labelledby="account-delete-title">
      <section className="card account-delete-card">
        <span className="danger-kicker">ACCOUNT DELETION</span>
        <h2 id="account-delete-title">회원 탈퇴</h2>
        <p>탈퇴하면 다음 데이터가 모두 영구적으로 삭제되며 복구할 수 없습니다.</p>
        <ul>
          <li>계정과 로그인 정보</li>
          <li>업로드한 계약서 PDF</li>
          <li>계약서 분석 결과와 분석 이력</li>
          <li>브라우저에 저장된 노동법 상담 기록</li>
        </ul>
        <form onSubmit={submit}>
          <label>현재 비밀번호
            <input
              type="password"
              value={password}
              onChange={event => setPassword(event.target.value)}
              autoComplete="current-password"
              required
            />
          </label>
          <label>확인을 위해 <strong>{CONFIRMATION}</strong>를 입력하세요.
            <input
              value={confirmation}
              onChange={event => setConfirmation(event.target.value)}
              placeholder={CONFIRMATION}
              autoComplete="off"
              required
            />
          </label>
          {error && <p className="error">{error}</p>}
          <div className="account-delete-actions">
            <button type="button" className="secondary" onClick={close} disabled={busy}>취소</button>
            <button
              className="delete-account-confirm"
              disabled={busy || !password || confirmation !== CONFIRMATION}
            >{busy ? "탈퇴 처리 중…" : "모든 데이터 삭제 및 탈퇴"}</button>
          </div>
        </form>
      </section>
    </div>}
  </>;
}
