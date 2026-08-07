from __future__ import annotations

from html import escape
from pathlib import Path

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import PythonLexer


ROOT = Path(__file__).resolve().parents[2]
AI = ROOT / "ai" / "app"
OUT = ROOT / "docs" / "assets" / "code-captures"


CAPTURES = [
    {
        "file": "01-langgraph-contract-analysis",
        "title": "LangGraph · 계약서 위험 분석",
        "subtitle": "기본 분석 → 법령 검색 → 조건 분기 → LLM 분석 → 결과 검증",
        "source": AI / "agent.py",
        "ranges": [(238, 267), (272, 276)],
    },
    {
        "file": "02-langgraph-contract-question",
        "title": "LangGraph · 계약서 질의응답",
        "subtitle": "계약서별 검색 → 관련 법령 검색 → 근거 기반 답변 생성",
        "source": AI / "question_agent.py",
        "ranges": [(22, 44)],
    },
    {
        "file": "03-langgraph-legal-consultation",
        "title": "LangGraph · 노동법 AI 상담",
        "subtitle": "쟁점 분류와 법령 검색 결과에 따른 조건부 라우팅",
        "source": AI / "legal_consultation.py",
        "ranges": [(519, 550), (567, 575)],
    },
    {
        "file": "04-rag-embedding-vector-db",
        "title": "RAG · 임베딩 모델과 Vector DB",
        "subtitle": "Ko-SRoBERTa 문장 임베딩을 ChromaDB 영구 컬렉션에 저장",
        "source": AI / "rag" / "service.py",
        "ranges": [(10, 28), (38, 73)],
    },
    {
        "file": "05-rag-law-hybrid-search",
        "title": "RAG · 법령 하이브리드 검색",
        "subtitle": "벡터 의미 유사도와 법률 키워드 일치 점수를 결합",
        "source": AI / "rag" / "service.py",
        "ranges": [(159, 186)],
    },
    {
        "file": "06-rag-contract-search",
        "title": "RAG · 계약서 청킹 및 계약서별 검색",
        "subtitle": "850자 청킹·140자 중첩과 contract_id 기반 격리 검색",
        "source": AI / "contract_rag.py",
        "ranges": [(12, 18), (36, 52), (73, 92)],
    },
    {
        "file": "07-pdf-preprocessing",
        "title": "PDF 전처리 · 텍스트 및 페이지 정보 추출",
        "subtitle": "PyMuPDF로 페이지별 텍스트·좌표 정보를 추출하고 분석 가능 여부 검증",
        "source": AI / "pdf_service.py",
        "ranges": [(1, 42)],
    },
    {
        "file": "08-contract-chunking-ingest",
        "title": "계약서 청킹 · Vector DB 적재",
        "subtitle": "문장 경계를 고려한 중첩 청킹 후 계약서·페이지 메타데이터와 함께 저장",
        "source": AI / "contract_rag.py",
        "ranges": [(35, 71)],
    },
    {
        "file": "09-fallback-contract-analysis",
        "title": "Fallback · 계약서 위험 분석",
        "subtitle": "법령 근거·LLM 상태를 검사하고 규칙 기반 기본 분석으로 안전하게 전환",
        "source": AI / "agent.py",
        "ranges": [(263, 278), (306, 330)],
    },
    {
        "file": "10-fallback-contract-question",
        "title": "Fallback · 계약서 질의응답",
        "subtitle": "검색 결과 또는 LLM 응답이 없을 때 계약서·법령 근거를 직접 조합",
        "source": AI / "question_agent.py",
        "ranges": [(41, 67), (80, 107)],
    },
    {
        "file": "11-fallback-legal-consultation",
        "title": "Fallback · 노동법 AI 상담",
        "subtitle": "질문 범위·법령 근거·출처를 조건별로 검증하여 응답 경로 결정",
        "source": AI / "legal_consultation.py",
        "ranges": [(573, 622)],
    },
]


def selected_source(path: Path, ranges: list[tuple[int, int]]) -> tuple[str, int]:
    lines = path.read_text(encoding="utf-8").splitlines()
    pieces: list[str] = []
    count = 0
    for index, (start, end) in enumerate(ranges):
        if index:
            pieces.extend(["", "# ... 중간 구현 생략 ...", ""])
            count += 3
        pieces.extend(lines[start - 1:end])
        count += end - start + 1
    return "\n".join(pieces), count


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    formatter = HtmlFormatter(style="github-dark", linenos="table", cssclass="highlight")
    pygments_css = formatter.get_style_defs(".highlight")
    for capture in CAPTURES:
        code, line_count = selected_source(capture["source"], capture["ranges"])
        rendered = highlight(code, PythonLexer(), formatter)
        height = max(560, 220 + line_count * 26)
        html = f'''<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><title>{escape(capture['title'])}</title>
<style>
*{{box-sizing:border-box}}html,body{{margin:0;width:1600px;background:#eef2f6}}
body{{padding:42px 48px 48px;font-family:"Malgun Gothic","Noto Sans KR",sans-serif;color:#14263d}}
.heading{{margin:0 0 10px;font-size:34px;font-weight:700;letter-spacing:-0.5px}}
.subtitle{{margin:0 0 26px;color:#53697d;font-size:20px}}
.editor{{overflow:hidden;border:1px solid #30465e;border-radius:14px;background:#0d1117;box-shadow:0 12px 30px rgba(20,38,61,.15)}}
.bar{{display:flex;align-items:center;gap:10px;height:48px;padding:0 18px;background:#162337;border-bottom:1px solid #33445a}}
.dot{{width:12px;height:12px;border-radius:50%}}.red{{background:#ff6b6b}}.yellow{{background:#ffd166}}.green{{background:#4ecb71}}
.filename{{margin-left:10px;color:#c7d4e2;font:16px Consolas,monospace}}
.highlight{{margin:0;padding:20px 0;background:#0d1117}}
.highlight table{{width:100%;border-spacing:0}}
.highlight pre{{margin:0;font:18px/1.45 Consolas,"D2Coding",monospace;tab-size:4}}
.highlight .linenos{{width:64px;padding:0 15px 0 12px;border-right:1px solid #263445;color:#718096;text-align:right;user-select:none}}
.highlight .code{{padding:0 22px}}
{pygments_css}
</style></head><body>
<h1 class="heading">{escape(capture['title'])}</h1>
<p class="subtitle">{escape(capture['subtitle'])}</p>
<div class="editor"><div class="bar"><span class="dot red"></span><span class="dot yellow"></span><span class="dot green"></span><span class="filename">{escape(capture['source'].name)}</span></div>{rendered}</div>
</body></html>'''
        target = OUT / f"{capture['file']}.html"
        target.write_text(html, encoding="utf-8")
        print(f"{capture['file']}|{height}")


if __name__ == "__main__":
    main()
