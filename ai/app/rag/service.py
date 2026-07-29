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
        return self.model.encode(
            input,
            batch_size=int(os.getenv("EMBEDDING_BATCH_SIZE", "128")),
            normalize_embeddings=True,
            show_progress_bar=False,
        ).tolist()

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
    COLLECTION_NAME = "lawzic_labor_laws_v2"

    def __init__(self, base_dir: Path | None = None):
        project_dir = base_dir or Path(__file__).resolve().parents[2]
        self.data_path = Path(os.getenv(
            "LAW_CORPUS_PATH",
            project_dir / "data" / "laws" / "labor_law_corpus.json",
        ))
        self.manifest_path = Path(os.getenv(
            "LAW_MANIFEST_PATH",
            project_dir / "data" / "laws" / "labor_law_manifest.json",
        ))
        self.db_path = Path(os.getenv("CHROMA_DB_PATH", project_dir / "data" / "chroma"))
        self.model_name = os.getenv("EMBEDDING_MODEL", "jhgan/ko-sroberta-multitask")
        self._collection = None
        self._client = None
        self._ready = False
        self._lock = Lock()

    def _get_collection(self):
        if self._collection is not None:
            return self._collection
        with self._lock:
            if self._collection is None:
                client = chromadb.PersistentClient(path=str(self.db_path))
                self._client = client
                embedding = SentenceTransformerEmbedding(self.model_name)
                self._collection = client.get_or_create_collection(
                    name=self.COLLECTION_NAME,
                    embedding_function=embedding,
                    metadata={"hnsw:space": "cosine", "corpus_sha256": self._corpus_hash()},
                )
        return self._collection

    def _corpus_hash(self) -> str:
        if not self.manifest_path.exists():
            return "missing"
        manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        return str(manifest.get("corpus_sha256", "unknown"))

    def _load_records(self) -> list[dict]:
        if not self.data_path.exists():
            raise RuntimeError(
                "운영 법령 corpus가 없습니다. "
                "`python -m scripts.sync_laws --oc <인증값> --ingest`를 먼저 실행하세요."
            )
        records = json.loads(self.data_path.read_text(encoding="utf-8"))
        if not records:
            raise RuntimeError("운영 법령 corpus가 비어 있습니다.")
        return records

    def ingest(self, force: bool = False) -> int:
        collection = self._get_collection()
        records = self._load_records()
        if force and collection.count():
            collection.delete(ids=collection.get()["ids"])
        documents = [self._document(record) for record in records]
        if not force and collection.count():
            existing = collection.get(include=["documents"])
            existing_documents = dict(zip(existing["ids"], existing["documents"]))
            pending = [
                (record, document)
                for record, document in zip(records, documents)
                if existing_documents.get(record["id"]) != document
            ]
            records = [item[0] for item in pending]
            documents = [item[1] for item in pending]
        if not records:
            collection.modify(metadata={"corpus_sha256": self._corpus_hash()})
            return collection.count()
        metadatas = []
        for record in records:
            metadata = {
                key: (value if value is not None else "")
                for key, value in record.items()
                if key not in {"id", "text"}
            }
            metadata["legal_text"] = record["text"]
            metadatas.append(metadata)
        batch_size = 500
        for start in range(0, len(records), batch_size):
            end = start + batch_size
            collection.upsert(
                ids=[record["id"] for record in records[start:end]],
                documents=documents[start:end],
                metadatas=metadatas[start:end],
            )
            print(f"법령 임베딩 적재: {min(end, len(records))}/{len(records)}")
        collection.modify(metadata={"corpus_sha256": self._corpus_hash()})
        return collection.count()

    def remove_legacy_collection(self) -> None:
        client = self._client or chromadb.PersistentClient(path=str(self.db_path))
        try:
            client.delete_collection("lawzic_labor_laws")
        except Exception:
            pass

    def ensure_ready(self) -> int:
        if not self._ready:
            collection = self._get_collection()
            expected_hash = self._corpus_hash()
            current_hash = (collection.metadata or {}).get("corpus_sha256")
            if current_hash != expected_hash:
                raise RuntimeError(
                    "법령 corpus와 ChromaDB 버전이 다릅니다. "
                    "`python -m scripts.ingest_laws`로 다시 적재하세요."
                )
            count = self.ingest()
            self._ready = True
            return count
        return self._get_collection().count()

    def search(self, query: str, top_k: int = 3) -> list[dict]:
        if not query.strip():
            return []
        self.ensure_ready()
        collection = self._get_collection()
        candidate_count = min(collection.count(), max(top_k * 3, 10))
        result = collection.query(query_texts=[query], n_results=candidate_count)
        matches = []
        for evidence_id, document, metadata, distance in zip(
            result["ids"][0], result["documents"][0], result["metadatas"][0], result["distances"][0]
        ):
            metadata = dict(metadata)
            legal_text = metadata.pop("legal_text", document)
            similarity = max(0.0, 1.0 - float(distance))
            keyword_hits = sum(
                1 for term in set(query.split())
                if len(term) >= 2 and term in " ".join((
                    str(metadata.get("law_name", "")),
                    str(metadata.get("title", "")),
                    legal_text,
                ))
            )
            hybrid_score = similarity + min(0.3, keyword_hits * 0.15)
            matches.append({"evidence_id": evidence_id, **metadata, "content": legal_text,
                            "distance": round(float(distance), 4),
                            "similarity": round(similarity, 4), "hybrid_score": round(hybrid_score, 4)})
        matches.sort(key=lambda match: match["hybrid_score"], reverse=True)
        return matches[:top_k]

    def get_by_citations(
        self, citations: set[tuple[str, str]], query: str = "",
    ) -> list[dict]:
        self.ensure_ready()
        collection = self._get_collection()
        query_terms = {term for term in query.split() if len(term) >= 2}
        matches = []
        for law_name, article_number in citations:
            result = collection.get(
                where={"$and": [
                    {"law_name": {"$eq": law_name}},
                    {"article_number": {"$eq": article_number}},
                ]},
                include=["documents", "metadatas"],
            )
            candidates = []
            for evidence_id, document, metadata in zip(
                result["ids"], result["documents"], result["metadatas"],
            ):
                metadata = dict(metadata)
                legal_text = metadata.pop("legal_text", document)
                overlap = sum(term in legal_text for term in query_terms)
                candidates.append((overlap, {
                    "evidence_id": evidence_id,
                    **metadata,
                    "content": legal_text,
                    "distance": 0.0,
                    "similarity": 1.0,
                    "hybrid_score": 1.0,
                }))
            if candidates:
                matches.append(max(candidates, key=lambda item: item[0])[1])
        return matches

    @staticmethod
    def _document(record: dict) -> str:
        path = record.get("provision_path", record["article_number"])
        return f'{record["law_name"]} {path} {record.get("title", "")}\n{record["text"]}'
