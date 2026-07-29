import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "../api/client";

const SUGGESTIONS = [
  "연장근로는 일주일에 몇 시간까지 가능한가요?",
  "수습기간에는 최저임금보다 적게 지급할 수 있나요?",
  "퇴직금은 어떤 조건에서 받을 수 있나요?",
  "회사가 임금을 임의로 공제할 수 있나요?",
];

function storedMessages(key) {
  try {
    const value = JSON.parse(sessionStorage.getItem(key) ?? "[]");
    return Array.isArray(value) ? value : [];
  } catch {
    return [];
  }
}

export default function LegalConsultationPage({ user, onHome, onWorkspace, onLogout }) {
  const storageKey = useMemo(() => `lawzic-legal-chat:${user.email}`, [user.email]);
  const [messages, setMessages] = useState(() => storedMessages(storageKey));
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const endRef = useRef(null);

  useEffect(() => {
    sessionStorage.setItem(storageKey, JSON.stringify(messages.slice(-30)));
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, storageKey]);

  const ask = async event => {
    event?.preventDefault();
    const current = question.trim();
    if (busy || current.length < 2) return;
    const history = messages.slice(-12).map(({ role, content }) => ({ role, content }));
    setQuestion("");
    setError("");
    setBusy(true);
    setMessages(value => [...value, { role: "user", content: current }]);
    try {
      const response = await api("/legal-consultation/messages", {
        method: "POST",
        body: JSON.stringify({ question: current, history }),
      });
      setMessages(value => [...value, {
        role: "assistant",
        content: response.answer,
        legalReferences: response.legal_references ?? [],
        warning: response.warning,
        insufficientEvidence: response.insufficient_evidence,
      }]);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  };

  const reset = () => {
    setMessages([]);
    setQuestion("");
    setError("");
    sessionStorage.removeItem(storageKey);
  };

  return <div className="consultation-shell">
    <header className="consultation-header">
      <div>
        <button className="brand-home" onClick={onHome} aria-label="LAWZIC 메인화면으로 이동"><span className="brand-logo">LA<span>WZ</span>IC</span></button>
        <h2>노동법 AI 상담</h2>
      </div>
      <div className="user">
        <button className="secondary" onClick={onWorkspace}>계약서 분석실</button>
        <button className="secondary" onClick={reset}>새 대화</button>
        <button className="secondary" onClick={onLogout}>로그아웃</button>
      </div>
    </header>

    <main className="consultation-layout">
      <aside className="consultation-guide card">
        <p className="hero-kicker">LABOR LAW RAG CHAT</p>
        <h3>노동법을 근거와 함께 확인하세요</h3>
        <p>임금, 근로시간, 휴일·휴가, 해고, 퇴직금 등 노동관계 법령 범위에서 답변합니다.</p>
        <div className="privacy-notice">
          주민등록번호, 주소, 연락처, 회사 내부정보 등 민감한 개인정보는 입력하지 마세요.
        </div>
        <strong>질문 예시</strong>
        <div className="suggestion-list">
          {SUGGESTIONS.map(item => <button key={item} className="suggestion" onClick={() => setQuestion(item)}>{item}</button>)}
        </div>
      </aside>

      <section className="chat-panel card" aria-label="노동법 AI 상담 대화">
        <div className="chat-messages">
          {messages.length === 0 && <div className="chat-empty">
            <span>LAWZIC AI</span>
            <h3>궁금한 노동법 내용을 질문해 주세요.</h3>
            <p>검색된 법령 근거가 없는 경우에는 답변을 추측하지 않고 확인이 필요하다고 안내합니다.</p>
          </div>}
          {messages.map((message, index) => <article className={`chat-message ${message.role}`} key={`${message.role}-${index}`}>
            <small>{message.role === "user" ? "나" : "LAWZIC AI"}</small>
            <div>{message.content}</div>
            {message.legalReferences?.length > 0 && <section className="chat-sources">
              <strong>관련 법령 근거</strong>
              {message.legalReferences.map((reference, sourceIndex) => <div key={`${reference.law_name}-${sourceIndex}`}>
                {reference.source_url
                  ? <a href={reference.source_url} target="_blank" rel="noreferrer">{reference.law_name} {reference.article_number} 공식 원문</a>
                  : <b>{reference.law_name} {reference.article_number}</b>}
                <p>{reference.content}</p>
              </div>)}
            </section>}
            {message.warning && <p className="chat-warning">{message.warning}</p>}
          </article>)}
          {busy && <article className="chat-message assistant pending"><small>LAWZIC AI</small><div>관련 노동법 근거를 확인하고 있습니다…</div></article>}
          <div ref={endRef}/>
        </div>
        {error && <p className="error">{error}</p>}
        <form className="chat-composer" onSubmit={ask}>
          <textarea
            value={question}
            onChange={event => setQuestion(event.target.value)}
            onKeyDown={event => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                ask(event);
              }
            }}
            placeholder="노동법 질문을 입력하세요. Shift+Enter로 줄바꿈"
            maxLength="500"
            rows="3"
          />
          <div><small>{question.length}/500</small><button disabled={busy || question.trim().length < 2}>질문 보내기</button></div>
        </form>
      </section>
    </main>
  </div>;
}
