from app.rag import LawRagService


if __name__ == "__main__":
    count = LawRagService().ingest(force=True)
    print(f"LAWZIC 법령 Vector DB 적재 완료: {count}개 조문")
