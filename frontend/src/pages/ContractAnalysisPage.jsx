import PdfEvidence from "../components/PdfEvidence";

const CHECKLIST_LABELS = {
  COMPLIANT: "정상",
  RISK: "위험",
  MISSING: "누락",
  REVIEW: "검토 필요",
};

export default function ContractAnalysisPage({
  selected, result, busy, activeLocation, question, answer, questionHistory,
  onDownloadReport, onLocation, onCloseLocation, onQuestion, onQuestionChange,
}) {
  return <section className="card result">
    <div className="result-title">
      <h3>{selected ? `${selected.filename} 분석 결과` : "분석 결과"}</h3>
      {result && <button onClick={onDownloadReport} disabled={busy}>PDF 리포트</button>}
    </div>
    {!result ? <p className="empty">계약서를 선택해 분석하면 여기에 결과가 표시됩니다.</p> : <>
      <div className={`score ${result.overall_risk_level.toLowerCase()}`}>
        <span>종합 위험도</span>
        <div className="score-values">
          <strong>{result.overall_risk_level} · {result.overall_score}점</strong>
          <small>별도 검토 필요 {result.review_required_count ?? result.clauses.filter(clause => clause.review_required).length}건</small>
        </div>
      </div>
      <h4>요약</h4><p>{result.summary}</p>
      <h4>표준근로계약서 체크리스트</h4>
      <div className="checklist">{result.checklist?.map(item => <button key={item.code} className={`check-item ${item.status.toLowerCase()}`} onClick={() => item.location && onLocation(item.location)}>
        <span>{item.status === "COMPLIANT" ? "✓" : "!"}</span>
        <div><strong>{item.title} · {CHECKLIST_LABELS[item.status] || item.status}</strong><small>{item.evidence || "계약서에서 확인되지 않음"}</small></div>
      </button>)}</div>
      <h4>확인할 조항</h4>
      {result.clauses.length === 0 ? <p>탐지된 항목이 없습니다.</p> : result.clauses.map((clause, index) => <article className="finding" key={`${clause.clause_type}-${index}`}>
        <div>
          <span className={`badge ${clause.review_required ? "review" : clause.risk_level.toLowerCase()}`}>{clause.review_required ? "검토 필요" : clause.risk_level}</span>
          <strong>{clause.title}</strong>
          {clause.location && <button className="page-chip" onClick={() => onLocation(clause.location)}>{clause.location.page}페이지 보기</button>}
        </div>
        <blockquote>{clause.original_text}</blockquote>
        <p>{clause.reason}</p>
        <small className="confidence">분석 신뢰도 {Math.round((clause.confidence ?? 1) * 100)}%
          {clause.semantic && ` · 주체 ${clause.semantic.subject || "문맥상 생략"} · 행위 ${clause.semantic.action || "불명확"} · 대상 ${clause.semantic.target || "불명확"}`}
        </small>
        <p className="recommend">권고: {clause.recommendation}</p>
        {clause.replacement_text && <div className="replacement">
          <strong>안전한 대체 문구</strong><p>{clause.replacement_text}</p>
          <button className="secondary" onClick={() => navigator.clipboard.writeText(clause.replacement_text)}>복사</button>
        </div>}
        {clause.legal_references.map((reference, referenceIndex) => <small key={referenceIndex}>
          {reference.source_url
            ? <a href={reference.source_url} target="_blank" rel="noreferrer">{reference.law_name} {reference.article_number} 공식 원문</a>
            : `${reference.law_name} ${reference.article_number}`}
        </small>)}
      </article>)}
      {activeLocation && <div className="evidence-modal">
        <button className="modal-close" onClick={onCloseLocation}>닫기</button>
        <PdfEvidence contractId={selected.id} location={activeLocation}/>
      </div>}
      <section className="qa">
        <h4>계약서에 질문하기</h4>
        <form onSubmit={onQuestion}>
          <input value={question} onChange={event => onQuestionChange(event.target.value)} placeholder="예: 야근수당은 어떻게 정해져 있어?" maxLength="500"/>
          <button disabled={busy}>질문</button>
        </form>
        {questionHistory?.length > 0 && <div className="qa-history">
          {questionHistory.map(item => <article className="answer qa-history-item" key={item.id}>
            <strong className="qa-question">질문: {item.question}</strong>
            <p>{item.response.answer}</p>
            {(item.response.contract_sources ?? []).map((source, index) => <button className="page-chip" key={index} onClick={() => onLocation(source)}>{source.page}페이지 근거</button>)}
            {(item.response.legal_references ?? []).map((law, index) => <small key={index}>{law.source_url
              ? <a href={law.source_url} target="_blank" rel="noreferrer">{law.law_name} {law.article_number}</a>
              : `${law.law_name} ${law.article_number}`}</small>)}
            <div className="warning">{item.response.warning}</div>
          </article>)}
        </div>}
      </section>
    </>}
  </section>;
}
