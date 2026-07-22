from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile

from .analyzer import analyze_contract
from .pdf_service import PdfReadError, extract_text
from .rag import LawRagService
from .schemas import AnalysisResponse, LegalReference

app = FastAPI(title="LAWZIC API", version="0.1.0")
rag = LawRagService()


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
    result = analyze_contract(contract_id, text)
    try:
        for clause in result.clauses:
            query = f"{clause.title} {clause.original_text} {clause.reason}"
            matches = rag.search(query, top_k=2)
            clause.legal_references = [
                LegalReference(
                    law_name=match["law_name"],
                    article_number=match["article_number"],
                    content=match["content"],
                    source_url=match.get("source_url"),
                )
                for match in matches
            ]
        result.warnings[0] = "규칙 기반 위험 탐지와 Vector DB 법령 검색을 결합한 MVP 결과입니다."
    except Exception as exc:
        result.warnings.append(f"법령 RAG 검색을 완료하지 못했습니다: {exc}")
    return result
