from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile

from starlette.concurrency import run_in_threadpool

from .agent import ContractAnalysisAgent
from .pdf_service import PdfReadError, extract_text
from .rag import LawRagService
from .schemas import AnalysisResponse

app = FastAPI(title="LAWZIC API", version="0.1.0")
rag = LawRagService()
agent = ContractAnalysisAgent(rag)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/internal/v1/rag/search")
def rag_search(q: str = Query(min_length=2), top_k: int = Query(default=3, ge=1, le=5)) -> dict:
    try:
        return {"query": q, "matches": rag.search(q, top_k)}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"법령 검색기를 준비하지 못했습니다: {exc}") from exc


@app.post("/internal/v1/analyze", response_model=AnalysisResponse)
async def analyze(contract_id: int = Form(...), file: UploadFile = File(...)) -> AnalysisResponse:
    if file.content_type not in {"application/pdf", "application/octet-stream"}:
        raise HTTPException(status_code=400, detail="PDF 파일만 분석할 수 있습니다.")
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="10MB 이하의 PDF만 분석할 수 있습니다.")
    try:
        text = extract_text(content)
    except PdfReadError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await run_in_threadpool(agent.analyze, contract_id, text)
