from app.rag import LawRagService


if __name__ == "__main__":
    service = LawRagService()
    count = service.ingest(force=False)
    service.remove_legacy_collection()
    print(f"LAWZIC 운영 법령 Vector DB 적재 완료: {count}개 조·항·호")
