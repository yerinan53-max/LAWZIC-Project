import fitz
from dataclasses import dataclass


class PdfReadError(ValueError):
    pass


@dataclass(frozen=True)
class PdfPage:
    number: int
    text: str
    words: list[tuple]
    width: float
    height: float


def extract_document(content: bytes) -> tuple[str, list[PdfPage]]:
    try:
        with fitz.open(stream=content, filetype="pdf") as document:
            pages = [
                PdfPage(
                    number=index + 1,
                    text=page.get_text("text"),
                    words=page.get_text("words"),
                    width=page.rect.width,
                    height=page.rect.height,
                )
                for index, page in enumerate(document)
            ]
    except Exception as exc:
        raise PdfReadError("PDF 문서를 읽을 수 없습니다.") from exc

    text = "\n".join(page.text for page in pages)
    normalized = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    if len(normalized) < 30:
        raise PdfReadError("텍스트가 없거나 너무 짧습니다. 현재 버전은 스캔 PDF를 지원하지 않습니다.")
    return normalized, pages


def extract_text(content: bytes) -> str:
    return extract_document(content)[0]
