import { useEffect, useRef, useState } from "react";

function fileSize(size) {
  if (size < 1024 * 1024) return `${Math.max(1, Math.round(size / 1024))}KB`;
  return `${(size / (1024 * 1024)).toFixed(1)}MB`;
}

export default function PdfUploadPage({
  busy, pendingFile, analyzingId, error, onFilesSelected, onClear, onAnalyze,
}) {
  const [dragging, setDragging] = useState(false);
  const dragDepth = useRef(0);
  const inputRef = useRef(null);
  const disabled = busy || analyzingId !== null;

  useEffect(() => {
    const preventFileOpen = event => {
      if (Array.from(event.dataTransfer?.types ?? []).includes("Files")) {
        event.preventDefault();
      }
    };
    window.addEventListener("dragover", preventFileOpen);
    window.addEventListener("drop", preventFileOpen);
    return () => {
      window.removeEventListener("dragover", preventFileOpen);
      window.removeEventListener("drop", preventFileOpen);
    };
  }, []);

  const chooseFiles = files => {
    onFilesSelected(files);
    if (inputRef.current) inputRef.current.value = "";
  };

  const enter = event => {
    event.preventDefault();
    if (disabled) return;
    dragDepth.current += 1;
    setDragging(true);
  };

  const leave = event => {
    event.preventDefault();
    if (disabled) return;
    dragDepth.current = Math.max(0, dragDepth.current - 1);
    if (dragDepth.current === 0) setDragging(false);
  };

  const drop = event => {
    event.preventDefault();
    event.stopPropagation();
    dragDepth.current = 0;
    setDragging(false);
    if (!disabled) chooseFiles(event.dataTransfer.files);
  };

  return <section className="card upload">
    <h3>계약서 업로드</h3>
    <p className="muted">텍스트가 포함된 10MB 이하 근로계약서 PDF를 선택하세요.</p>

    <div
      className={`pdf-drop-zone${dragging ? " dragging" : ""}${disabled ? " disabled" : ""}`}
      onDragEnter={enter}
      onDragOver={event => event.preventDefault()}
      onDragLeave={leave}
      onDrop={drop}
      onClick={() => !disabled && inputRef.current?.click()}
      onKeyDown={event => {
        if (!disabled && (event.key === "Enter" || event.key === " ")) {
          event.preventDefault();
          inputRef.current?.click();
        }
      }}
      role="button"
      tabIndex={disabled ? -1 : 0}
      aria-disabled={disabled}
      aria-label="PDF 파일 선택 또는 드래그앤드롭"
    >
      <span className="drop-icon" aria-hidden="true">PDF</span>
      <strong>{dragging ? "여기에 PDF를 놓으세요" : "PDF를 끌어다 놓으세요"}</strong>
      <small>또는 클릭해서 파일 선택 · PDF 한 개 · 최대 10MB</small>
      <input
        ref={inputRef}
        hidden
        type="file"
        accept="application/pdf,.pdf"
        onChange={event => chooseFiles(event.target.files)}
        disabled={disabled}
      />
    </div>

    {pendingFile && <div className="upload-ready">
      <div>
        <small>분석 대기</small>
        <strong>{pendingFile.name}</strong>
        <span>{fileSize(pendingFile.size)}</span>
      </div>
      <div className="upload-ready-actions">
        <button className="secondary" onClick={event => {
          event.stopPropagation();
          inputRef.current?.click();
        }} disabled={disabled}>파일 변경</button>
        <button className="danger-outline" onClick={onClear} disabled={disabled}>선택 취소</button>
        <button onClick={onAnalyze} disabled={disabled}>
          {busy ? "업로드 중…" : analyzingId !== null ? "분석 중…" : "분석하기"}
        </button>
      </div>
    </div>}
    {error && <p className="error">{error}</p>}
  </section>;
}
