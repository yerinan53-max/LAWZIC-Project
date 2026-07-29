import { useEffect, useState } from "react";
import { apiBlob } from "../api/client";

export default function OriginalPdfModal({ contract, onClose }) {
  const [url, setUrl] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (!contract?.id) return undefined;
    let active = true;
    let objectUrl = "";

    apiBlob(`/contracts/${contract.id}/file`)
      .then(blob => {
        objectUrl = URL.createObjectURL(blob);
        if (active) setUrl(objectUrl);
      })
      .catch(error => {
        if (active) setError(error.message);
      });

    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [contract?.id]);

  useEffect(() => {
    const closeOnEscape = event => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [onClose]);

  if (!contract) return null;

  return <div className="original-pdf-modal" role="dialog" aria-modal="true" aria-labelledby="original-pdf-title" onMouseDown={event => {
    if (event.target === event.currentTarget) onClose();
  }}>
    <section className="original-pdf-panel">
      <header className="original-pdf-header">
        <div>
          <small>업로드 원본</small>
          <h3 id="original-pdf-title">{contract.filename}</h3>
        </div>
        <div className="original-pdf-actions">
          {url && <a className="pdf-action-link" href={url} target="_blank" rel="noreferrer">새 탭에서 보기</a>}
          {url && <a className="pdf-action-link" href={url} download={contract.filename}>다운로드</a>}
          <button type="button" className="secondary" onClick={onClose}>닫기</button>
        </div>
      </header>
      <div className="original-pdf-body">
        {!url && !error && <p className="empty">PDF를 불러오고 있습니다.</p>}
        {error && <p className="error">{error}</p>}
        {url && <iframe src={url} title={`${contract.filename} 원본 PDF`}/>}
      </div>
    </section>
  </div>;
}
