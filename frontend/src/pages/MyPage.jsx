import { useEffect, useState } from "react";
import { api } from "../api/client";
import AccountDeletionButton from "../components/AccountDeletionButton";

const STATUS_LABELS = {
  UPLOADED: "분석 대기",
  PROCESSING: "분석 중",
  COMPLETED: "분석 완료",
  FAILED: "분석 실패",
};

export default function MyPage({
  user,
  onHome,
  onWorkspace,
  onConsultation,
  onOpenAnalysis,
  onUserUpdated,
  onDeleteAccount,
  onLogout,
}) {
  const [contracts, setContracts] = useState([]);
  const [consultations, setConsultations] = useState([]);
  const [form, setForm] = useState({
    name: user.name,
    currentPassword: "",
    newPassword: "",
    newPasswordConfirm: "",
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [passwordEditorOpen, setPasswordEditorOpen] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    let active = true;
    Promise.all([api("/contracts"), api("/legal-consultation/history")])
      .then(([contractItems, consultationItems]) => {
        if (!active) return;
        setContracts(contractItems);
        setConsultations(consultationItems);
      })
      .catch(requestError => {
        if (active) setError(requestError.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!notice) return undefined;
    const timeout = window.setTimeout(() => setNotice(""), 10000);
    return () => window.clearTimeout(timeout);
  }, [notice]);

  const updateAccount = async event => {
    event.preventDefault();
    setError("");
    setNotice("");
    const nameChanged = form.name.trim() !== user.name.trim();
    const passwordChangeRequested = passwordEditorOpen && Boolean(
      form.currentPassword || form.newPassword || form.newPasswordConfirm
    );
    if (!nameChanged && !passwordChangeRequested) {
      setNotice("변경된 사항이 없습니다.");
      return;
    }
    if (passwordChangeRequested && !form.currentPassword) {
      setError("현재 비밀번호를 입력하세요.");
      return;
    }
    if (passwordChangeRequested && !form.newPassword) {
      setError("새 비밀번호를 입력하세요.");
      return;
    }
    if (passwordChangeRequested && form.newPassword !== form.newPasswordConfirm) {
      setError("새 비밀번호와 비밀번호 확인이 일치하지 않습니다.");
      return;
    }
    setSaving(true);
    try {
      const updated = await api("/auth/me", {
        method: "PATCH",
        body: JSON.stringify({
          name: form.name,
          currentPassword: passwordChangeRequested ? form.currentPassword : null,
          newPassword: passwordChangeRequested ? form.newPassword : null,
        }),
      });
      onUserUpdated(updated);
      setForm(value => ({
        ...value,
        name: updated.name,
        currentPassword: "",
        newPassword: "",
        newPasswordConfirm: "",
      }));
      setPasswordEditorOpen(false);
      setNotice("회원정보가 수정되었습니다.");
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSaving(false);
    }
  };

  const togglePasswordEditor = () => {
    setPasswordEditorOpen(open => {
      if (open) {
        setForm(value => ({
          ...value,
          currentPassword: "",
          newPassword: "",
          newPasswordConfirm: "",
        }));
      }
      return !open;
    });
    setError("");
    setNotice("");
  };

  const clearConsultations = async () => {
    if (!window.confirm("저장된 노동법 AI 상담 이력을 모두 삭제할까요?")) return;
    setError("");
    setNotice("");
    try {
      await api("/legal-consultation/history", { method: "DELETE" });
      sessionStorage.removeItem(`lawzic-legal-chat:${user.email}`);
      setConsultations([]);
      setNotice("상담 이력을 삭제했습니다.");
    } catch (requestError) {
      setError(requestError.message);
    }
  };

  const completedCount = contracts.filter(item => item.status === "COMPLETED").length;

  return (
    <div className="mypage-shell">
      <header>
        <div>
          <button className="brand-home" onClick={onHome} aria-label="LAWZIC 메인화면으로 이동">
            <span className="brand-logo">LA<span>WZ</span>IC</span>
          </button>
          <h2>마이페이지</h2>
        </div>
        <div className="user">
          <span className="landing-user-name" title={`${user.name}님`}>
            <span className="landing-user-initial" aria-hidden="true">{user.name?.trim().charAt(0) || "U"}</span>
            <span className="landing-user-label">{user.name}님</span>
          </span>
          <button className="landing-nav-link" onClick={onWorkspace}>계약서 분석실</button>
          <button className="landing-nav-link" onClick={onConsultation}>노동법 AI 상담</button>
          <button className="landing-nav-link" onClick={onLogout}>로그아웃</button>
        </div>
      </header>

      <main className="mypage-grid">
        <section className="card profile-card">
          <p className="hero-kicker">MY ACCOUNT</p>
          <h3>회원정보 수정</h3>
          <form onSubmit={updateAccount}>
            <label>이메일<input value={user.email} disabled /></label>
            <label>이름<input value={form.name} maxLength="50" onChange={event => setForm({ ...form, name: event.target.value })} required /></label>
            {!passwordEditorOpen && (
              <button
                type="button"
                className="secondary profile-password-button"
                onClick={togglePasswordEditor}
                aria-controls="profile-password-fields"
              >
                비밀번호 변경
              </button>
            )}
            {passwordEditorOpen && (
              <div id="profile-password-fields" className="profile-password-fields">
                <label>현재 비밀번호<input type="password" value={form.currentPassword} onChange={event => setForm({ ...form, currentPassword: event.target.value })} autoComplete="current-password" required /></label>
                <label>새 비밀번호 <small>8자 이상 입력하세요.</small><input type="password" minLength="8" maxLength="72" value={form.newPassword} onChange={event => setForm({ ...form, newPassword: event.target.value })} autoComplete="new-password" required /></label>
                <label>새 비밀번호 확인<input type="password" minLength="8" maxLength="72" value={form.newPasswordConfirm} onChange={event => setForm({ ...form, newPasswordConfirm: event.target.value })} autoComplete="new-password" required /></label>
                <button type="button" className="secondary profile-password-cancel" onClick={togglePasswordEditor}>비밀번호 변경 취소</button>
              </div>
            )}
            {notice && <p className={`success-notice ${notice === "변경된 사항이 없습니다." ? "neutral-notice" : ""}`}>{notice}</p>}
            {error && <p className="error">{error}</p>}
            <button className="profile-save-button" disabled={saving}>{saving ? "저장 중…" : "회원정보 저장"}</button>
          </form>
        </section>

        <section className="mypage-summary" aria-label="이용 현황">
          <article className="card"><small>업로드 계약서</small><strong>{contracts.length}</strong><span>건</span></article>
          <article className="card"><small>완료된 분석</small><strong>{completedCount}</strong><span>건</span></article>
          <article className="card"><small>AI 상담 이력</small><strong>{consultations.length}</strong><span>건</span></article>
        </section>

        <section className="card mypage-history">
          <div className="mypage-section-title">
            <h3>계약서 분석 이력</h3>
            <button className="secondary" onClick={onWorkspace}>분석실로 이동</button>
          </div>
          <div className="mypage-scroll">
            {loading ? <p className="empty">이력을 불러오고 있습니다.</p> : contracts.length === 0
              ? <p className="empty">계약서 분석 이력이 없습니다.</p>
              : contracts.map(contract => (
                <article className="mypage-history-item" key={contract.id}>
                  <div>
                    <strong>{contract.filename}</strong>
                    <small>{new Date(contract.uploadedAt).toLocaleString("ko-KR")} · {STATUS_LABELS[contract.status] ?? contract.status}</small>
                  </div>
                  {contract.status === "COMPLETED" && <button className="secondary result-view-button" onClick={() => onOpenAnalysis(contract.id)}>결과 보기</button>}
                </article>
              ))}
          </div>
        </section>

        <section className="card mypage-history consultation-history">
          <div className="mypage-section-title">
            <h3>노동법 AI 상담 이력</h3>
            {consultations.length > 0 && <button className="danger-outline" onClick={clearConsultations}>상담 이력 전체 삭제</button>}
          </div>
          <div className="mypage-scroll">
            {loading ? <p className="empty">이력을 불러오고 있습니다.</p> : consultations.length === 0
              ? <p className="empty">저장된 상담 이력이 없습니다.</p>
              : consultations.map(item => (
                <details className="consultation-history-item" key={item.id}>
                  <summary><span>{item.question}</span><small>{new Date(item.createdAt).toLocaleString("ko-KR")}</small></summary>
                  <p>{item.answer}</p>
                  {item.legalReferences?.map((reference, index) => (
                    <small key={`${item.id}-${index}`}>{reference.law_name} {reference.article_number}</small>
                  ))}
                </details>
              ))}
          </div>
        </section>

        <section className="card account-danger-zone">
          <div><h3>회원 탈퇴</h3><p>계정과 계약서, 분석 결과, 상담 이력이 모두 영구적으로 삭제됩니다.</p></div>
          <AccountDeletionButton onDeleteAccount={onDeleteAccount} />
        </section>
      </main>
    </div>
  );
}
