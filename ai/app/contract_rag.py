import os
import re
from pathlib import Path
from threading import Lock

import chromadb

from .pdf_service import PdfPage
from .rag.service import SentenceTransformerEmbedding


class ContractRagService:
    COLLECTION_NAME = "lawzic_contract_chunks_v1"

    def __init__(self, base_dir: Path | None = None):
        project_dir = base_dir or Path(__file__).resolve().parents[1]
        self.db_path = Path(os.getenv("CHROMA_DB_PATH", project_dir / "data" / "chroma"))
        self.model_name = os.getenv("EMBEDDING_MODEL", "jhgan/ko-sroberta-multitask")
        self._collection = None
        self._lock = Lock()

    def _get_collection(self):
        if self._collection is not None:
            return self._collection
        with self._lock:
            if self._collection is None:
                client = chromadb.PersistentClient(path=str(self.db_path))
                self._collection = client.get_or_create_collection(
                    name=self.COLLECTION_NAME,
                    embedding_function=SentenceTransformerEmbedding(self.model_name),
                    metadata={"hnsw:space": "cosine"},
                )
        return self._collection

    @staticmethod
    def _chunks(page: PdfPage, size: int = 850, overlap: int = 140) -> list[str]:
        text = re.sub(r"\s+", " ", page.text).strip()
        if not text:
            return []
        chunks = []
        start = 0
        while start < len(text):
            end = min(len(text), start + size)
            if end < len(text):
                boundary = max(text.rfind(". ", start, end), text.rfind("다. ", start, end))
                if boundary > start + size // 2:
                    end = boundary + 2
            chunks.append(text[start:end].strip())
            if end >= len(text):
                break
            start = max(start + 1, end - overlap)
        return chunks

    def ingest(self, contract_id: int, pages: list[PdfPage]) -> int:
        collection = self._get_collection()
        self.delete(contract_id)
        records = [
            (f"contract-{contract_id}-page-{page.number}-chunk-{index}", chunk, page.number, index)
            for page in pages
            for index, chunk in enumerate(self._chunks(page))
        ]
        if not records:
            return 0
        collection.upsert(
            ids=[item[0] for item in records],
            documents=[item[1] for item in records],
            metadatas=[{
                "contract_id": int(contract_id), "page": item[2], "chunk_index": item[3],
            } for item in records],
        )
        return len(records)

    def search(self, contract_id: int, query: str, top_k: int = 4) -> list[dict]:
        if not query.strip():
            return []
        collection = self._get_collection()
        existing = collection.get(where={"contract_id": {"$eq": int(contract_id)}}, limit=1)
        if not existing["ids"]:
            return []
        result = collection.query(
            query_texts=[query], n_results=top_k,
            where={"contract_id": {"$eq": int(contract_id)}},
        )
        return [
            {
                "chunk_id": chunk_id,
                "text": document,
                "page": int(metadata["page"]),
                "similarity": round(max(0.0, 1.0 - float(distance)), 4),
            }
            for chunk_id, document, metadata, distance in zip(
                result["ids"][0], result["documents"][0],
                result["metadatas"][0], result["distances"][0],
            )
        ]

    def has_index(self, contract_id: int) -> bool:
        result = self._get_collection().get(
            where={"contract_id": {"$eq": int(contract_id)}}, limit=1,
        )
        return bool(result["ids"])

    def delete(self, contract_id: int) -> None:
        self._get_collection().delete(where={"contract_id": {"$eq": int(contract_id)}})
