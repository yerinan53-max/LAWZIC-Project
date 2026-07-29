import { useEffect, useRef } from "react";
import { useNavigate, useParams } from "react-router-dom";
import ContractAnalysisPage from "./ContractAnalysisPage";
import ContractHistoryPage from "./ContractHistoryPage";
import PdfUploadPage from "./PdfUploadPage";
import useContractWorkspace from "../hooks/useContractWorkspace";

export default function ContractWorkspacePage({user, onLogout, onHome, onConsultation, onMyPage}) {
  const { contractId } = useParams();
  const navigate = useNavigate();
  const routedContract = useRef(null);
  const workspace = useContractWorkspace();

  useEffect(() => {
    if (!contractId || !workspace.loaded || routedContract.current === contractId) return;
    const contract = workspace.contracts.find(item => String(item.id) === contractId);
    if (!contract || contract.status !== "COMPLETED") {
      navigate("/contracts", { replace: true });
      return;
    }
    routedContract.current = contractId;
    workspace.viewResult(contract);
  }, [contractId, workspace.loaded, workspace.contracts, navigate]);

  const analyze = async contract => {
    const completed = await workspace.analyze(contract);
    if (completed) {
      routedContract.current = String(contract.id);
      navigate(`/contracts/${contract.id}/analysis`);
    }
  };

  const analyzePending = async () => {
    const completedContract = await workspace.analyzePending();
    if (completedContract?.id) {
      routedContract.current = String(completedContract.id);
      navigate(`/contracts/${completedContract.id}/analysis`);
    }
  };

  const viewResult = contract => {
    navigate(`/contracts/${contract.id}/analysis`);
  };

  const deleteContract = async contract => {
    const deleted = await workspace.deleteContract(contract);
    if (deleted && String(contract.id) === contractId) {
      routedContract.current = null;
      navigate("/contracts", { replace: true });
    }
  };

  return <div className="app-shell">
    <header>
      <div>
        <button className="brand-home" onClick={onHome} aria-label="LAWZIC 메인화면으로 이동"><span className="brand-logo">LA<span>WZ</span>IC</span></button>
        <h2>계약서 분석실</h2>
      </div>
      <div className="user"><span>{user?.name ?? user?.email}님</span><button className="secondary" onClick={onConsultation}>법률 AI 상담</button><button className="secondary" onClick={onMyPage}>마이페이지</button><button className="secondary" onClick={onLogout}>로그아웃</button></div>
    </header>
    <main className="grid">
      <PdfUploadPage
        busy={workspace.busy}
        pendingFile={workspace.pendingFile}
        analyzingId={workspace.analyzingId}
        error={workspace.error}
        onFilesSelected={workspace.selectFiles}
        onClear={workspace.clearPendingFile}
        onAnalyze={analyzePending}
      />
      <ContractHistoryPage
        contracts={workspace.contracts}
        busy={workspace.busy}
        analyzingId={workspace.analyzingId}
        onViewResult={viewResult}
        onAnalyze={analyze}
        onCancel={workspace.cancelAnalysis}
        onDelete={deleteContract}
      />
      <ContractAnalysisPage
        selected={workspace.selected}
        result={workspace.result}
        busy={workspace.busy}
        activeLocation={workspace.activeLocation}
        question={workspace.question}
        answer={workspace.answer}
        onDownloadReport={workspace.downloadReport}
        onLocation={workspace.setActiveLocation}
        onCloseLocation={() => workspace.setActiveLocation(null)}
        onQuestion={workspace.ask}
        onQuestionChange={workspace.setQuestion}
      />
    </main>
  </div>;
}
