# LAWZIC 설계 노트

## 핵심 책임

| 구성요소 | 책임 |
|---|---|
| React | 입력, 업로드, 분석 결과 표현 |
| Spring Boot | 인증, 권한, 계약서 메타데이터, AI 서버 연동, 결과 저장 |
| FastAPI | PDF 처리, 분석 규칙, 추후 RAG·LLM·LangGraph |
| H2/MySQL | 사용자, 계약서, 분석 결과 |

## 데이터 관계

```text
users 1 ── N contracts
contracts 1 ── 0..1 analysis_results
```

현재는 AI가 반환한 구조화 JSON 전체를 `analysis_results.result_json`에 보관합니다. 분석 항목별 통계나 검색이 필요해지면 `risk_clauses` 테이블로 분리합니다.

## API

| Method | Path | 인증 | 설명 |
|---|---|---:|---|
| POST | `/api/auth/signup` | X | 회원가입 |
| POST | `/api/auth/login` | X | JWT 로그인 |
| GET | `/api/auth/me` | O | 현재 사용자 |
| POST | `/api/contracts` | O | PDF 업로드 |
| GET | `/api/contracts` | O | 내 계약서 목록 |
| GET | `/api/contracts/{id}` | O | 내 계약서 상세 |
| POST | `/api/contracts/{id}/analysis` | O | AI 분석 시작 |
| GET | `/api/contracts/{id}/analysis` | O | 저장된 분석 결과 |
| GET | `/api/contracts/{id}/analysis/status` | O | 처리 상태 |
| POST | `/internal/v1/analyze` | 내부 | FastAPI 분석 |

## 보안 결정

- 비밀번호는 BCrypt 해시만 저장합니다.
- JWT 유효기간은 기본 1시간입니다.
- 계약서 조회와 분석 때 `계약서 ID + 로그인 사용자 이메일`을 함께 조회합니다.
- 확장자뿐 아니라 PDF 매직 바이트 `%PDF`를 확인합니다.
- 저장 파일명은 UUID로 바꾸고 원래 이름과 분리합니다.
- FastAPI는 공개 사용자 인증을 담당하지 않습니다. 배포 시 내부 네트워크 또는 내부 토큰 검증을 추가해야 합니다.

## 현재 한계

- 분석 호출이 동기 방식이어서 큰 문서나 LLM 호출에는 적합하지 않습니다.
- 규칙 기반 결과이며 법령 원문 Vector DB 검색은 아직 없습니다.
- OCR, Refresh Token, 로그아웃 토큰 폐기, 파일 악성코드 검사는 후속 범위입니다.
- 위험도 점수는 법적 확률이 아니라 화면 정렬을 위한 설명 가능한 가중치입니다.

## RAG 추가 위치

`ai/app/analyzer.py`를 다음 단위로 분리합니다.

```text
extract_contract_clauses(text)
rule_scan(clauses)
retrieve_laws(clause, vector_store)
llm_analyze(clause, retrieved_laws)
aggregate_results(findings)
```

Vector DB 메타데이터에는 최소한 `law_name`, `article_number`, `effective_date`, `source_url`, `text`를 저장합니다. 법령은 글자 수가 아니라 조·항 단위로 나누는 것을 권장합니다.
