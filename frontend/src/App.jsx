import { useEffect, useState } from "react";
import { api, clearToken, getToken, setToken } from "./api/client";

function Landing({ onStart }) {
  return <div className="landing">
    <nav className="landing-nav">
      <p className="brand-logo">LAWZIC</p>
      <button className="nav-login" onClick={onStart}>로그인</button>
    </nav>
    <main>
      <section className="hero">
        <div className="hero-copy">
          <p className="hero-kicker">AI CONTRACT RISK ANALYSIS</p>
          <h1>계약서의 위험을<br/><span>근거와 함께</span> 확인하세요.</h1>
          <p>LAWZIC은 계약서의 잠재적인 위험 조항을 탐지하고 관련 법령과 검토 방향을 한눈에 정리하는 AI 계약서 분석 플랫폼입니다.</p>
          <div className="hero-actions"><button onClick={onStart}>계약서 분석 시작</button><a href="#features">주요 기능 보기</a></div>
          <small>현재 MVP에서는 근로계약서 분석을 지원합니다.</small>
        </div>
        <div className="hero-panel" aria-label="LAWZIC 분석 결과 예시">
          <div className="panel-top"><span>계약서 분석 결과</span><span className="status-dot">분석 완료</span></div>
          <div className="risk-preview"><div><small>종합 위험도</small><strong>주의가 필요한 계약서</strong></div><b>72</b></div>
          <div className="preview-item"><span className="preview-icon high">!</span><div><strong>퇴직금 조항</strong><small>급여 포함 표현을 확인하세요.</small></div></div>
          <div className="preview-item"><span className="preview-icon medium">!</span><div><strong>연장근로 조항</strong><small>가산수당 기준이 불명확합니다.</small></div></div>
          <div className="law-source"><span>관련 근거</span><strong>근로기준법 · 근로자퇴직급여 보장법</strong></div>
        </div>
      </section>
      <section className="trust-row"><span>PDF 텍스트 추출</span><span>위험 조항 탐지</span><span>법령 Vector RAG</span><span>공식 원문 연결</span></section>
      <section className="landing-section" id="features">
        <div className="section-heading"><p>CORE FEATURES</p><h2>계약서 검토에 필요한 핵심 기능</h2><span>복잡한 계약 문장을 읽고 위험 요소와 확인할 근거를 구조화합니다.</span></div>
        <div className="feature-grid">
          <article><b>01</b><h3>PDF 계약서 분석</h3><p>업로드한 PDF에서 텍스트를 추출하고 검토 가능한 형태로 정리합니다.</p></article>
          <article><b>02</b><h3>위험 조항 탐지</h3><p>임금, 근로시간, 연차, 퇴직금 등 주의가 필요한 표현을 찾아냅니다.</p></article>
          <article><b>03</b><h3>법령 RAG 검색</h3><p>계약 조항과 관련된 법령을 Vector DB에서 검색해 공식 근거를 연결합니다.</p></article>
        </div>
      </section>
      <section className="process-section">
        <div className="section-heading"><p>HOW IT WORKS</p><h2>간단한 계약서 분석 과정</h2></div>
        <div className="process-row"><div><b>1</b><span>회원 로그인</span></div><i>→</i><div><b>2</b><span>PDF 업로드</span></div><i>→</i><div><b>3</b><span>AI·RAG 분석</span></div><i>→</i><div><b>4</b><span>근거 확인</span></div></div>
      </section>
      <section className="landing-cta"><p className="brand-logo">LAW<span>Z</span>IC</p><h2>놓치기 쉬운 계약 조항,<br/>지금 확인해 보세요.</h2><button onClick={onStart}>무료로 분석 시작</button></section>
    </main>
    <footer><p>LAWZIC</p><span>본 분석 결과는 참고 정보이며 법률 자문이나 법적 판단을 대체하지 않습니다.</span></footer>
  </div>;
}

function Login({ onLogin, onBack }) {
  const [signup, setSignup] = useState(false);
  const [form, setForm] = useState({ email: "", password: "", name: "" });
  const [error, setError] = useState("");
  const submit = async (event) => {
    event.preventDefault(); setError("");
    try {
      if (signup) {
        await api("/auth/signup", { method: "POST", body: JSON.stringify(form) });
        setSignup(false); return;
      }
      const data = await api("/auth/login", { method: "POST", body: JSON.stringify(form) });
      setToken(data.accessToken); onLogin(data.user);
    } catch (e) { setError(e.message); }
  };
  return <main className="auth-shell"><button className="back-home" onClick={onBack}>← 메인으로</button><section className="card auth-card">
    <p className="brand-logo">LAW<span>Z</span>IC</p><h1>{signup ? "회원가입" : "계약서 검토를 시작하세요"}</h1>
    <p className="muted">AI가 잠재적인 위험 조항과 확인할 법령을 정리합니다.</p>
    <form onSubmit={submit}>
      {signup && <label>이름<input value={form.name} onChange={e => setForm({...form, name:e.target.value})} required /></label>}
      <label>이메일<input type="email" value={form.email} onChange={e => setForm({...form, email:e.target.value})} required /></label>
      <label>비밀번호<input type="password" minLength="8" value={form.password} onChange={e => setForm({...form, password:e.target.value})} required /></label>
      {error && <p className="error">{error}</p>}<button>{signup ? "가입하기" : "로그인"}</button>
    </form>
    <button className="link" onClick={() => {setSignup(!signup);setError("");}}>{signup ? "이미 계정이 있어요" : "처음인가요? 회원가입"}</button>
  </section></main>;
}

function Dashboard({ user, onLogout }) {
  const [contracts, setContracts] = useState([]);
  const [selected, setSelected] = useState(null);
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const load = () => api("/contracts").then(setContracts).catch(e => setError(e.message));
  useEffect(() => {
    load();
  }, []);

  const upload = async (event) => {
    const file = event.target.files[0]; if (!file) return;
    setBusy(true); setError("");
    try 
    { const body = new FormData(); 
      body.append("file", file); 
      await api("/contracts", {method:"POST", body}); 
      await load(); 
    }
    catch(e) 
    { setError(e.message); 

    } finally { 
      setBusy(false); 
      event.target.value = ""; 
    }
  };
  const analyze = async (contract) => {

    setSelected(contract); 
    setResult(null); 
    setBusy(true); 
    setError("");

    try {
       setResult(await api(`/contracts/${contract.id}/analysis`, {method:"POST"})); 
       await load(); 
      }
    catch(e) {
       setError(e.message); 
      } finally {
         setBusy(false);
        }
  };

  const deleteContract = async (contract) => {
    if (!window.confirm(`'${contract.filename}' 계약서를 삭제할까요? PDF 파일과 분석 결과가 모두 삭제됩니다.`)) return;
    setBusy(true);
    setError("");
    try {
      await api(`/contracts/${contract.id}`, {method:"DELETE"});
      if (selected?.id === contract.id) {
        setSelected(null);
        setResult(null);
      }
      await load();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  return <div className="app-shell"><header><div><p className="brand-logo">LAW<span>Z</span>IC</p><h2>계약서 분석실</h2></div><div className="user"><span>{user?.name ?? user?.email}님</span><button className="secondary" onClick={onLogout}>로그아웃</button></div></header>
    <main className="grid"><section className="card upload"><h3>계약서 업로드</h3><p className="muted">현재 MVP는 근로계약서를 분석합니다. 텍스트가 포함된 10MB 이하 PDF를 선택하세요.</p><label className="upload-button">{busy ? "처리 중…" : "PDF 선택"}<input hidden type="file" accept="application/pdf,.pdf" onChange={upload} disabled={busy}/></label>{error && <p className="error">{error}</p>}</section>
    <section className="card list"><h3>분석 이력</h3>{contracts.length === 0 ? <p className="empty">업로드한 계약서가 없습니다.</p> : contracts.map(c => <article className="contract" key={c.id}><div><strong>{c.filename}</strong><small>{new Date(c.uploadedAt).toLocaleString("ko-KR")} · {c.status}</small></div><div className="contract-actions"><button onClick={() => analyze(c)} disabled={busy}>{c.status === "COMPLETED" ? "재분석" : "분석"}</button><button className="danger-outline" onClick={() => deleteContract(c)} disabled={busy || c.status === "PROCESSING"}>계약서 삭제</button></div></article>)}</section>
    <section className="card result"><h3>{selected ? `${selected.filename} 분석 결과` : "분석 결과"}</h3>{!result ? <p className="empty">계약서를 선택해 분석하면 여기에 결과가 표시됩니다.</p> : <><div className={`score ${result.overall_risk_level.toLowerCase()}`}><span>종합 위험도</span><strong>{result.overall_risk_level} · {result.overall_score}점</strong></div><h4>요약</h4><p>{result.summary}</p><h4>확인할 조항</h4>{result.clauses.length === 0 ? <p>탐지된 항목이 없습니다.</p> : result.clauses.map((c,i) => <article className="finding" key={i}><div><span className={`badge ${c.risk_level.toLowerCase()}`}>{c.risk_level}</span><strong>{c.title}</strong></div><blockquote>{c.original_text}</blockquote><p>{c.reason}</p><p className="recommend">권고: {c.recommendation}</p>{c.legal_references.map((r,j)=><small key={j}>{r.source_url ? <a href={r.source_url} target="_blank" rel="noreferrer">{r.law_name} {r.article_number} 공식 원문</a> : `${r.law_name} ${r.article_number}`}</small>)}</article>)}<div className="warning">{result.warnings.join(" ")}</div></>}</section></main></div>;
}

export default function App() {
  const [user, setUser] = useState(null);
  const [authOpen, setAuthOpen] = useState(false);
  const [checking, setChecking] = useState(Boolean(getToken()));
  useEffect(() => {
    if (!getToken()) { setChecking(false); return; }
    api("/auth/me").then(setUser).catch(clearToken).finally(() => setChecking(false));
  }, []);
  if (checking) return <main className="loading-screen"><p className="brand-logo">LAW<span>Z</span>IC</p><span>사용자 정보를 확인하고 있습니다.</span></main>;
  if (user) return <Dashboard user={user} onLogout={() => {clearToken();setUser(null);setAuthOpen(false);}}/>;
  if (authOpen) return <Login onLogin={setUser} onBack={() => setAuthOpen(false)}/>;
  return <Landing onStart={() => setAuthOpen(true)}/>;
}
