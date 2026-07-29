from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response

from starlette.concurrency import run_in_threadpool

from .agent import ContractAnalysisAgent
from .document_features import answer_legal_question, answer_question, create_report, enrich_locations
from .pdf_service import PdfReadError, extract_document
from .rag import LawRagService
from .schemas import AnalysisResponse, LegalChatRequest, LegalChatResponse, QuestionResponse

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
        text, pages = extract_document(content)
    except PdfReadError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    result = await run_in_threadpool(agent.analyze, contract_id, text)
    return enrich_locations(result, pages)


@app.post("/internal/v1/question", response_model=QuestionResponse)
async def question(question: str = Form(..., min_length=2), file: UploadFile = File(...)) -> QuestionResponse:
    content = await file.read()
    try:
        _, pages = extract_document(content)
    except PdfReadError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await run_in_threadpool(answer_question, question, pages, rag)


@app.post("/internal/v1/legal-chat", response_model=LegalChatResponse)
async def legal_chat(request: LegalChatRequest) -> LegalChatResponse:
    return await run_in_threadpool(
        answer_legal_question, request.question.strip(), request.history, rag,
    )


@app.post("/internal/v1/report")
async def report(
    filename: str = Form(...),
    analysis_json: str = Form(...),
) -> Response:
    try:
        result = AnalysisResponse.model_validate_json(analysis_json)
        content = await run_in_threadpool(create_report, result, filename)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"리포트를 생성할 수 없습니다: {exc}") from exc
    return Response(
        content=content, media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="lawzic-analysis-report.pdf"'},
    )
