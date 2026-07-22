import json
import os
from pathlib import Path
from threading import Lock

import chromadb
from sentence_transformers import SentenceTransformer


class SentenceTransformerEmbedding:
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.model = SentenceTransformer(model_name, local_files_only=True)

    def __call__(self, input: list[str]) -> list[list[float]]:
        return self.model.encode(input, normalize_embeddings=True).tolist()

    def embed_query(self, input: list[str]) -> list[list[float]]:
        return self(input)

    @staticmethod
    def name() -> str:
        return "lawzic_sentence_transformer"

    def get_config(self) -> dict:
        return {"model_name": self.model_name}

    @staticmethod
    def build_from_config(config: dict) -> "SentenceTransformerEmbedding":
        return SentenceTransformerEmbedding(config["model_name"])


class LawRagService:
    COLLECTION_NAME = "lawzic_labor_laws"

    def __init__(self, base_dir: Path | None = None):
        project_dir = base_dir or Path(__file__).resolve().parents[2]
        self.data_path = project_dir / "data" / "laws" / "labor_laws_seed.json"
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
                embedding = SentenceTransformerEmbedding(self.model_name)
                self._collection = client.get_or_create_collection(
                    name=self.COLLECTION_NAME,
                    embedding_function=embedding,
                    metadata={"hnsw:space": "cosine"},
                )
        return self._collection

    def ingest(self, force: bool = False) -> int:
        collection = self._get_collection()
        records = json.loads(self.data_path.read_text(encoding="utf-8"))
        if force and collection.count():
            collection.delete(ids=collection.get()["ids"])
        documents = [self._document(record) for record in records]
        metadatas = []
        for record in records:
            metadata = {key: value for key, value in record.items() if key not in {"id", "text", "keywords"}}
            metadata["keywords"] = "|".join(record.get("keywords", []))
            metadatas.append(metadata)
        collection.upsert(ids=[record["id"] for record in records], documents=documents, metadatas=metadatas)
        return collection.count()

    def ensure_ready(self) -> int:
        collection = self._get_collection()
        return collection.count() or self.ingest()

    def search(self, query: str, top_k: int = 3) -> list[dict]:
        if not query.strip():
            return []
        self.ensure_ready()
        collection = self._get_collection()
        candidate_count = min(collection.count(), max(top_k * 3, 10))
        result = collection.query(query_texts=[query], n_results=candidate_count)
        matches = []
        for document, metadata, distance in zip(result["documents"][0], result["metadatas"][0], result["distances"][0]):
            similarity = max(0.0, 1.0 - float(distance))
            keyword_hits = sum(1 for keyword in metadata.get("keywords", "").split("|") if keyword and keyword in query)
            hybrid_score = similarity + min(0.3, keyword_hits * 0.15)
            matches.append({**metadata, "content": document, "distance": round(float(distance), 4),
                            "similarity": round(similarity, 4), "hybrid_score": round(hybrid_score, 4)})
        matches.sort(key=lambda match: match["hybrid_score"], reverse=True)
        return matches[:top_k]

    @staticmethod
    def _document(record: dict) -> str:
        keywords = ", ".join(record.get("keywords", []))
        return f'{record["law_name"]} {record["article_number"]} {record["title"]}\n관련어: {keywords}\n{record["text"]}'
