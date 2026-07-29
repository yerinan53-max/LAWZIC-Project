export default function ContractHistoryPage({
  contracts, busy, analyzingId, onViewFile, onViewResult, onAnalyze, onCancel, onDelete,
}) {
  return <section className="card list">
    <h3>분석 이력</h3>
    <div className="contract-list">{contracts.length === 0
      ? <p className="empty">업로드한 계약서가 없습니다.</p>
      : contracts.map(contract => <article className="contract" key={contract.id}>
        <div className="contract-info">
          <button type="button" className="contract-file-link" onClick={() => onViewFile(contract)}>{contract.filename}</button>
          <small>{new Date(contract.uploadedAt).toLocaleString("ko-KR")} · {contract.status} · ID {contract.id}</small>
        </div>
        <div className="contract-actions">
          {contract.status === "COMPLETED" && <button className="secondary result-view-button" onClick={() => onViewResult(contract)} disabled={busy || analyzingId !== null}>결과 보기</button>}
          {analyzingId === contract.id || contract.status === "PROCESSING"
            ? <><button disabled>처리 중…</button><button className="cancel-button" onClick={() => onCancel(contract)}>분석 취소</button></>
            : <button onClick={() => onAnalyze(contract)} disabled={busy || analyzingId !== null}>{contract.status === "COMPLETED" ? "재분석" : "분석"}</button>}
          <button className="danger-outline" onClick={() => onDelete(contract)} disabled={busy || analyzingId !== null || contract.status === "PROCESSING"}>계약서 삭제</button>
        </div>
      </article>)}
    </div>
  </section>;
}
