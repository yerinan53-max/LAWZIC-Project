import { useEffect, useRef, useState } from "react";
import { api, apiBlob } from "../api/client";

export default function useContractWorkspace() {
  const [contracts, setContracts] = useState([]);
  const [selected, setSelected] = useState(null);
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [activeLocation, setActiveLocation] = useState(null);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState(null);
  const [questionHistory, setQuestionHistory] = useState([]);
  const [analyzingId, setAnalyzingId] = useState(null);
  const [pendingFile, setPendingFile] = useState(null);
  const [loaded, setLoaded] = useState(false);
  const analysisRun = useRef(0);

  const loadQuestionHistory = async contractId => {
    const items = await api(`/contracts/${contractId}/analysis/questions`);
    setQuestionHistory(items);
  };

  const load = () => api("/contracts")
    .then(setContracts)
    .catch(e => setError(e.message))
    .finally(() => setLoaded(true));
  useEffect(() => {
    load();
  }, []);

  const selectFiles = files => {
    const selectedFiles = Array.from(files ?? []);
    setError("");
    if (selectedFiles.length !== 1) {
      setPendingFile(null);
      setError("PDF 파일을 한 개만 선택하세요.");
      return false;
    }
    const file = selectedFiles[0];
    const hasPdfName = file.name.toLowerCase().endsWith(".pdf");
    const hasPdfType = !file.type || file.type === "application/pdf";
    if (!hasPdfName || !hasPdfType) {
      setPendingFile(null);
      setError("PDF 파일만 선택할 수 있습니다.");
      return false;
    }
    if (file.size <= 0) {
      setPendingFile(null);
      setError("비어 있는 파일은 업로드할 수 없습니다.");
      return false;
    }
    if (file.size > 10 * 1024 * 1024) {
      setPendingFile(null);
      setError("10MB 이하의 PDF 파일만 선택할 수 있습니다.");
      return false;
    }
    setPendingFile(file);
    return true;
  };

  const clearPendingFile = () => {
    if (busy || analyzingId !== null) return;
    setPendingFile(null);
    setError("");
  };

  const analyzePending = async () => {
    if (!pendingFile) return false;
    setBusy(true);
    setError("");
    let uploaded;
    try {
      const body = new FormData();
      body.append("file", pendingFile);
      uploaded = await api("/contracts", {method: "POST", body});
      setPendingFile(null);
      await load();
    } catch (e) {
      setError(e.message);
      return false;
    } finally {
      setBusy(false);
    }
    return await analyze(uploaded) ? uploaded : false;
  };

  const analyze = async (contract) => {
    const run = ++analysisRun.current;
    setSelected(contract);
    setResult(null);
    setAnalyzingId(contract.id);
    setError("");
    try {
      await api(`/contracts/${contract.id}/analysis`, {method: "POST"});
      await load();
      while (analysisRun.current === run) {
        await new Promise(resolve => setTimeout(resolve, 900));
        const status = await api(`/contracts/${contract.id}/analysis/status`);
        if (status.status === "COMPLETED") {
          setResult(await api(`/contracts/${contract.id}/analysis`));
          await loadQuestionHistory(contract.id);
          await load();
          return true;
        }
        if (status.status === "FAILED") {
          throw new Error("AI 분석을 완료하지 못했습니다. AI 서버와 Ollama 상태를 확인하세요.");
        }
        if (status.status === "CANCELLED" || status.status === "UPLOADED") {
          await load();
          return false;
        }
      }
    } catch (e) {
      if (analysisRun.current === run) setError(e.message);
      return false;
    } finally {
      if (analysisRun.current === run) setAnalyzingId(null);
    }
  };

  const cancelAnalysis = async (contract) => {
    setError("");
    try {
      await api(`/contracts/${contract.id}/analysis/cancel`, {method: "POST"});
      ++analysisRun.current;
      setAnalyzingId(null);
      setResult(null);
      await load();
    } catch (e) {
      setError(e.message === "서버 처리 중 오류가 발생했습니다."
        ? "분석 취소 요청에 실패했습니다. 백엔드를 재시작한 뒤 다시 시도하세요."
        : e.message);
      await load();
    }
  };

  const viewResult = async (contract) => {
    setSelected(contract);
    setResult(null);
    setAnswer(null);
    setQuestionHistory([]);
    setBusy(true);
    setError("");
    try {
      const [analysisResult] = await Promise.all([
        api(`/contracts/${contract.id}/analysis`),
        loadQuestionHistory(contract.id),
      ]);
      setResult(analysisResult);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const ask = async (event) => {
    event.preventDefault();
    if (!selected || question.trim().length < 2) return;
    setBusy(true);
    setError("");
    setAnswer(null);
    try {
      const submittedQuestion = question.trim();
      const response = await api(`/contracts/${selected.id}/analysis/questions`, {
        method: "POST", body: JSON.stringify({question}),
      });
      setAnswer(response);
      setQuestion("");
      setQuestionHistory(value => [...value, {
        id: `new-${Date.now()}`,
        question: submittedQuestion,
        response,
        createdAt: new Date().toISOString(),
      }]);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const downloadReport = async () => {
    setBusy(true);
    setError("");
    try {
      const blob = await apiBlob(`/contracts/${selected.id}/analysis/report`);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "LAWZIC-analysis-report.pdf";
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const deleteContract = async (contract) => {
    if (!window.confirm(`'${contract.filename}' 계약서를 삭제할까요? PDF 파일과 분석 결과가 모두 삭제됩니다.`)) return false;
    setBusy(true);
    setError("");
    try {
      await api(`/contracts/${contract.id}`, {method: "DELETE"});
      if (selected?.id === contract.id) {
        setSelected(null);
        setResult(null);
        setAnswer(null);
        setQuestionHistory([]);
      }
      await load();
      return true;
    } catch (e) {
      setError(e.message);
      return false;
    } finally {
      setBusy(false);
    }
  };

  return {
    contracts, selected, result, busy, error, activeLocation, question, answer, questionHistory,
    analyzingId, pendingFile, loaded, setActiveLocation, setQuestion,
    selectFiles, clearPendingFile, analyzePending, analyze, cancelAnalysis,
    viewResult, ask, downloadReport, deleteContract,
  };
}
