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

  const updateAccount = async event => {
    event.preventDefault();
    setError("");
    setNotice("");
    if (form.newPassword && form.newPassword !== form.newPasswordConfirm) {
      setError("새 비밀번호와 비밀번호 확인이 일치하지 않습니다.");
      return;
    }
    setSaving(true);
    try {
      const updated = await api("/auth/me", {
        method: "PATCH",
        body: JSON.stringify({
          name: form.name,
          currentPassword: form.currentPassword,
          newPassword: form.newPassword || null,
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
      setNotice("회원정보가 수정되었습니다.");
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSaving(false);
    }
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
          <button className="secondary" onClick={onWorkspace}>계약서 분석실</button>
          <button className="secondary" onClick={onConsultation}>노동법 AI 상담</button>
          <button className="secondary" onClick={onLogout}>로그아웃</button>
        </div>
      </header>

      <main className="mypage-grid">
        <section className="card profile-card">
          <p className="hero-kicker">MY ACCOUNT</p>
          <h3>회원정보 수정</h3>
          <form onSubmit={updateAccount}>
            <label>이메일<input value={user.email} disabled /></label>
            <label>이름<input value={form.name} maxLength="50" onChange={event => setForm({ ...form, name: event.target.value })} required /></label>
            <label>현재 비밀번호<input type="password" value={form.currentPassword} onChange={event => setForm({ ...form, currentPassword: event.target.value })} autoComplete="current-password" required /></label>
            <label>새 비밀번호 <small>변경하지 않으려면 비워두세요.</small><input type="password" minLength={form.newPassword ? 8 : undefined} value={form.newPassword} onChange={event => setForm({ ...form, newPassword: event.target.value })} autoComplete="new-password" /></label>
            <label>새 비밀번호 확인<input type="password" value={form.newPasswordConfirm} onChange={event => setForm({ ...form, newPasswordConfirm: event.target.value })} autoComplete="new-password" /></label>
            {notice && <p className="success-notice">{notice}</p>}
            {error && <p className="error">{error}</p>}
            <button disabled={saving}>{saving ? "저장 중…" : "회원정보 저장"}</button>
          </form>
        </section>

        <section className="mypage-summary" aria-label="이용 현황">
          <article className="card"><small>업로드 계약서</small><strong>{contracts.length}</strong><span>건</span></article>
          <article className="card"><small>완료된 분석</small><strong>{completedCount}</strong><span>건</span></article>
          <article className="card"><small>AI 상담 이력</small><strong>{consultations.length}</strong><span>건</span></article>
        </section>

        <section className="card mypage-history">
          <div className="mypage-section-title">
            <div><h3>계약서 분석 이력</h3><p>업로드한 계약서와 분석 상태를 확인합니다.</p></div>
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
            <div><h3>노동법 AI 상담 이력</h3><p>질문과 답변, 참고 법령을 다시 확인합니다.</p></div>
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
