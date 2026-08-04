export default function HomePage({ onStart, onConsultation, onMyPage, onHome, user }) {
  return <div className="landing">
    <nav className="landing-nav">
      <button className="brand-home landing-brand" onClick={onHome} aria-label="LAWZIC 메인화면 새로고침"><span className="brand-logo">LAW<span>Z</span>IC</span></button>
      <div className="landing-nav-actions">
        {user && <button className="landing-user-name" onClick={onMyPage} title="마이페이지로 이동" aria-label={`${user.name}님의 마이페이지로 이동`}>
          <span className="landing-user-initial" aria-hidden="true">{user.name?.trim().charAt(0) || "U"}</span>
          <span className="landing-user-label">{user.name}님</span>
        </button>}
        {user && <button className="landing-nav-link" onClick={onMyPage}>마이페이지</button>}
        <button className="landing-nav-link" onClick={onConsultation}>법률 AI 상담</button>
        <button className="landing-nav-link" onClick={onStart}>{user ? "계약서 분석실" : "로그인"}</button>
      </div>
    </nav>
    <main>
      <section className="hero">
        <div className="hero-copy">
          <p className="hero-kicker">AI CONTRACT RISK ANALYSIS</p>
          <h1><span className="hero-title-line">계약서의 위험을</span><span className="hero-title-line accent">근거와 함께</span><span className="hero-title-line">확인하세요.</span></h1>
          <p>LAWZIC은 계약서의 잠재적인 위험 조항을 탐지하고 관련 법령과 검토 방향을 한눈에 정리하는 AI 계약서 분석 플랫폼입니다.</p>
          <div className="hero-actions"><button onClick={onStart}>계약서 분석 시작</button><button className="secondary" onClick={onConsultation}>노동법 AI 상담</button><a href="#features">주요 기능 보기</a></div>
          <small>LAWZIC은 텍스트가 포함된 근로계약서 PDF 분석을 지원합니다.</small>
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
          <article><b>04</b><h3>노동법 AI 상담</h3><p>계약서 없이도 임금, 근로시간, 해고와 퇴직금에 관한 질문을 법령 근거와 함께 확인합니다.</p></article>
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
