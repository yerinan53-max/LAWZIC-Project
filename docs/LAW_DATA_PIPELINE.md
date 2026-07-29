# LAWZIC 공식 법령 데이터 파이프라인

LAWZIC의 운영 RAG는 국가법령정보센터 국가법령정보 공동활용 Open API의 현행
법령 본문을 사용한다. 수동으로 선별한 일부 조문 파일은 운영 데이터로 사용하지 않는다.

## 데이터 흐름

```text
노동관계 법령 카탈로그
→ 현행 법령 목록 API에서 정확한 법령 ID 확인
→ 현행 법령 본문 API 호출
→ 조·항·호·목 단위 레코드 생성
→ 법령명·법령 ID·조문 경로·시행일·공포일·소관부처·출처 저장
→ corpus SHA-256과 수집 시각을 매니페스트에 기록
→ 전체 임베딩 생성
→ ChromaDB 운영 컬렉션 적재
```

공식 API 가이드는 다음 두 API를 기준으로 한다.

- 현행법령 목록: `lawSearch.do?target=eflaw`
- 현행법령 본문: `lawService.do?target=eflaw`

## 최초 구축 및 법령 갱신

국가법령정보 공동활용 사이트에서 API 활용 신청 후 인증값을 환경변수로 설정한다.

```powershell
cd "C:\Users\human-21\Documents\Final Project\ai"
$env:LAW_OPEN_API_OC="발급받은 인증값"
.\.venv\Scripts\python.exe -m scripts.sync_laws --ingest
```

이 명령은 매번 국가법령정보센터의 현행 법령을 조회한다. corpus 내용이 변경되면
매니페스트 해시가 바뀌며 ChromaDB를 새 데이터로 재적재한다.

운영 환경에서는 배포 파이프라인이나 작업 스케줄러에서 매일 1회 실행한다. API에
짧은 시간 동안 과도한 요청을 보내지 않도록 법령별 순차 호출을 사용한다.

## 생성 파일

- `labor_law_catalog.json`: 수집 대상 법령명
- `labor_law_corpus.json`: 조·항·호·목 단위 공식 법령 레코드
- `labor_law_manifest.json`: 수집 출처, 시각, 법령 수, 레코드 수, corpus 해시
- `ai/data/chroma`: 임베딩 Vector DB

각 레코드는 다음 메타데이터를 포함한다.

```text
법령 ID와 법령 일련번호
법령명과 법령 종류
소관 부처
조·항·호·목 번호 및 전체 경로
조문 제목과 본문
시행일과 공포일
제·개정 구분
국가법령정보센터 출처 URL
```

## 무결성 보호

AI 서버는 매니페스트의 `corpus_sha256`과 ChromaDB 컬렉션의 해시를 비교한다.
두 버전이 다르면 오래된 Vector DB로 상담하지 않고 재적재 명령을 안내한다.

운영 corpus가 없거나 비어 있어도 소수의 내장 샘플로 자동 대체하지 않는다. 이 정책은
데이터 누락을 숨긴 채 불완전한 법률 상담을 제공하는 것을 방지한다.
