import fitz


class PdfReadError(ValueError):
    pass


def extract_text(content: bytes) -> str:
    try:
        with fitz.open(stream=content, filetype="pdf") as document:
            text = "\n".join(page.get_text("text") for page in document)
    except Exception as exc:
        raise PdfReadError("PDF 문서를 읽을 수 없습니다.") from exc

    normalized = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    if len(normalized) < 30:
        raise PdfReadError("텍스트가 없거나 너무 짧습니다. 현재 버전은 스캔 PDF를 지원하지 않습니다.")
    return normalized
