import json
import math
import os
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LegalIssue:
    issue_id: str
    title: str
    description: str
    examples: tuple[str, ...]
    queries: tuple[str, ...]
    sources: tuple[tuple[str, str], ...]

    @property
    def embedding_text(self) -> str:
        return " ".join((self.title, self.description, *self.examples, *self.queries))


@dataclass(frozen=True)
class ClassifiedIssue:
    issue: LegalIssue
    score: float


def _tokens(text: str) -> set[str]:
    stopwords = {"어떻게", "되나요", "있나요", "인가요", "회사", "근로자", "경우"}
    return {
        token for token in re.findall(r"[가-힣A-Za-z0-9]+", text.lower())
        if len(token) >= 2 and token not in stopwords
    }


def _cosine(left: list[float], right: list[float]) -> float:
    # 현재 임베딩은 정규화되어 있지만 다른 구현과의 호환성을 위해 분모도 계산한다.
    numerator = sum(a * b for a, b in zip(left, right))
    denominator = math.sqrt(sum(a * a for a in left)) * math.sqrt(sum(b * b for b in right))
    return numerator / denominator if denominator else 0.0


class LegalIssueClassifier:
    def __init__(self, rag, catalog_path: Path | None = None):
        project_dir = Path(__file__).resolve().parents[1]
        path = catalog_path or Path(os.getenv(
            "LEGAL_ISSUE_CATALOG_PATH", project_dir / "data" / "legal_issues.json",
        ))
        records = json.loads(path.read_text(encoding="utf-8"))
        self.issues = tuple(LegalIssue(
            issue_id=item["id"],
            title=item["title"],
            description=item["description"],
            examples=tuple(item.get("examples", [])),
            queries=tuple(item.get("queries", [])),
            sources=tuple(tuple(source) for source in item.get("sources", [])),
        ) for item in records)
        self.rag = rag
        self._issue_embeddings: list[list[float]] | None = None

    def _semantic_scores(self, question: str) -> list[float]:
        if not hasattr(self.rag, "embed_texts"):
            return [0.0] * len(self.issues)
        try:
            if self._issue_embeddings is None:
                self._issue_embeddings = self.rag.embed_texts([
                    issue.embedding_text for issue in self.issues
                ])
            question_embedding = self.rag.embed_texts([question])[0]
            return [_cosine(question_embedding, vector) for vector in self._issue_embeddings]
        except Exception:
            return [0.0] * len(self.issues)

    def classify(self, question: str) -> list[ClassifiedIssue]:
        semantic_scores = self._semantic_scores(question)
        question_terms = _tokens(question)
        candidates = []
        for issue, semantic in zip(self.issues, semantic_scores):
            issue_terms = _tokens(issue.embedding_text)
            overlap = len(question_terms & issue_terms)
            lexical = overlap / max(1, min(len(question_terms), 5))
            phrase_match = any(
                phrase in question or question in phrase
                for phrase in (*issue.examples, *issue.queries)
            )
            score = max(semantic, min(1.0, lexical * 0.75 + (0.25 if phrase_match else 0.0)))
            candidates.append(ClassifiedIssue(issue=issue, score=round(score, 4)))

        candidates.sort(key=lambda item: item.score, reverse=True)
        if not candidates:
            return []
        threshold = float(os.getenv("LEGAL_ISSUE_MIN_SCORE", "0.48"))
        best = candidates[0].score
        selected = [
            item for item in candidates
            if item.score >= threshold and item.score >= best - 0.10
        ][:3]
        return selected
