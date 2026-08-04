from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response

from starlette.concurrency import run_in_threadpool

from . import config as _config
from .agent import ContractAnalysisAgent
from .document_features import create_report, enrich_locations
from .legal_consultation import LegalConsultationAgent
from .contract_rag import ContractRagService
from .question_agent import ContractQuestionAgent
from .pdf_service import PdfReadError, extract_document
from .rag import LawRagService
from .schemas import AnalysisResponse, LegalChatRequest, LegalChatResponse, QuestionResponse

app = FastAPI(title="LAWZIC API", version="1.0.0")
rag = LawRagService()
contract_rag = ContractRagService()
agent = ContractAnalysisAgent(rag)
question_agent = ContractQuestionAgent(contract_rag, rag)
legal_consultation_agent = LegalConsultationAgent(rag)


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
    await run_in_threadpool(contract_rag.ingest, contract_id, pages)
    result = await run_in_threadpool(agent.analyze, contract_id, text)
    return enrich_locations(result, pages)


@app.post("/internal/v1/question", response_model=QuestionResponse)
async def question(
    contract_id: int = Form(...), question: str = Form(..., min_length=2),
    history: str = Form("[]"), file: UploadFile | None = File(None),
) -> QuestionResponse:
    import json
    try:
        parsed_history = json.loads(history)
        if not isinstance(parsed_history, list):
            parsed_history = []
    except json.JSONDecodeError:
        parsed_history = []
    indexed = await run_in_threadpool(contract_rag.has_index, contract_id)
    if not indexed and file is not None:
        content = await file.read()
        try:
            _, pages = extract_document(content)
        except PdfReadError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        await run_in_threadpool(contract_rag.ingest, contract_id, pages)
        indexed = True
    if not indexed:
        raise HTTPException(status_code=409, detail="계약서 벡터 인덱스가 없습니다. 계약서를 다시 분석해 주세요.")
    return await run_in_threadpool(question_agent.answer, contract_id, question, parsed_history[-6:])


@app.delete("/internal/v1/contracts/{contract_id}/index", status_code=204)
async def delete_contract_index(contract_id: int) -> None:
    await run_in_threadpool(contract_rag.delete, contract_id)


@app.post("/internal/v1/legal-chat", response_model=LegalChatResponse)
async def legal_chat(request: LegalChatRequest) -> LegalChatResponse:
    return await run_in_threadpool(
        legal_consultation_agent.answer, request.question.strip(), request.history,
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
