from __future__ import annotations

from html import escape
from pathlib import Path

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import JavaLexer, PythonLexer


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "assets" / "troubleshooting-code"


def lines(path: Path, start: int, end: int) -> str:
    source = path.read_text(encoding="utf-8").splitlines()
    return "\n".join(source[start - 1:end])


CAPTURES = [
    {
        "file": "01-analysis-cancel-500-solution",
        "title": "분석 취소 API 500 오류 해결",
        "subtitle": "기존 DB 상태값과 호환되도록 취소 상태를 UPLOADED로 복귀",
        "blocks": [
            (
                "Contract.java · 상태 모델",
                lines(ROOT / "backend/src/main/java/com/lawzic/api/contract/Contract.java", 16, 16)
                + "\n\n"
                + lines(ROOT / "backend/src/main/java/com/lawzic/api/contract/Contract.java", 43, 46),
                JavaLexer(),
            ),
            (
                "AnalysisService.java · 취소 처리",
                lines(ROOT / "backend/src/main/java/com/lawzic/api/analysis/AnalysisService.java", 91, 104),
                JavaLexer(),
            ),
        ],
    },
    {
        "file": "02-recommendation-replacement-solution",
        "title": "권고·안전한 대체 문구 중복 해결",
        "subtitle": "검증된 대체 조항을 우선하고 동일 문장은 출력 단계에서 제거",
        "blocks": [
            (
                "analyzer.py · 실제 계약 조항 분리",
                lines(ROOT / "ai/app/analyzer.py", 59, 78),
                PythonLexer(),
            ),
            (
                "agent.py · 중복 방어 처리",
                lines(ROOT / "ai/app/agent.py", 216, 224),
                PythonLexer(),
            ),
        ],
    },
    {
        "file": "03-consultation-scope-solution",
        "title": "노동법 질문 범위 오판 해결",
        "subtitle": "키워드뿐 아니라 RAG 법령 검색 결과까지 포함해 상담 범위를 판정",
        "blocks": [
            (
                "legal_consultation.py · 검색 근거 기반 범위 판정",
                lines(ROOT / "ai/app/legal_consultation.py", 132, 142),
                PythonLexer(),
            ),
            (
                "legal_consultation.py · LangGraph 조건 분기",
                lines(ROOT / "ai/app/legal_consultation.py", 572, 586),
                PythonLexer(),
            ),
        ],
    },
]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    formatter = HtmlFormatter(style="github-dark", linenos=False, cssclass="highlight")
    pygments_css = formatter.get_style_defs(".highlight")

    for capture in CAPTURES:
        rendered_blocks = []
        for label, code, lexer in capture["blocks"]:
            rendered_blocks.append(
                f'<section class="editor"><div class="bar">'
                f'<span class="dot red"></span><span class="dot yellow"></span>'
                f'<span class="dot green"></span><span class="filename">{escape(label)}</span>'
                f'</div>{highlight(code, lexer, formatter)}</section>'
            )

        html = f'''<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><title>{escape(capture['title'])}</title>
<style>
*{{box-sizing:border-box}}html,body{{margin:0;width:1600px;background:#f3f6f8}}
body{{padding:42px 52px 48px;font-family:"Malgun Gothic","Noto Sans KR",sans-serif;color:#14263d}}
.eyebrow{{margin:0 0 8px;color:#47718f;font-size:17px;font-weight:700;letter-spacing:2px}}
h1{{margin:0 0 8px;font-size:36px;letter-spacing:-1px}}
.subtitle{{margin:0 0 24px;color:#5b6f80;font-size:20px}}
.editor{{margin-top:18px;overflow:hidden;border:1px solid #31475e;border-radius:12px;background:#0d1117;box-shadow:0 10px 24px rgba(20,38,61,.13)}}
.bar{{display:flex;align-items:center;gap:9px;height:44px;padding:0 16px;background:#172337;border-bottom:1px solid #33445a}}
.dot{{width:11px;height:11px;border-radius:50%}}.red{{background:#ff6b6b}}.yellow{{background:#ffd166}}.green{{background:#4ecb71}}
.filename{{margin-left:8px;color:#d0dbe6;font:16px Consolas,"D2Coding",monospace}}
.highlight{{margin:0;padding:16px 24px;background:#0d1117}}
.highlight pre{{margin:0;white-space:pre-wrap;font:17px/1.42 Consolas,"D2Coding",monospace;tab-size:4}}
{pygments_css}
</style></head><body>
<p class="eyebrow">LAWZIC TROUBLESHOOTING</p>
<h1>{escape(capture['title'])}</h1>
<p class="subtitle">{escape(capture['subtitle'])}</p>
{''.join(rendered_blocks)}
</body></html>'''
        (OUT / f"{capture['file']}.html").write_text(html, encoding="utf-8")
        print(capture["file"])


if __name__ == "__main__":
    main()
