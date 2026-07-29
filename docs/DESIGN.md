# LAWZIC 설계 노트

## 핵심 책임

| 구성요소 | 책임 |
|---|---|
| React | 입력, 업로드, 분석 결과 표현 |
| Spring Boot | 인증, 권한, 계약서 메타데이터, AI 서버 연동, 결과 저장 |
| FastAPI | PDF 처리, 의미 기반 위험 분석, RAG·LLM·LangGraph |
| MariaDB | 사용자, 계약서, 분석 결과와 상담 이력 |

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

## 의미 기반 분석 파이프라인

```text
PDF 텍스트 추출
→ 제N조 기준 조항 분리
→ 규칙으로 위험 후보 생성
→ 주체·행위·대상·조건·부정 여부 추출
→ 안전한 부정문 제거
→ 의미 요소 충족도 기반 신뢰도 계산
→ ChromaDB 법령 검색 및 LLM 분석
→ 규칙 결과와 LLM 결과 상호검증
→ 위험 / 검토 필요 / 정상 결과 통합
```

규칙과 의미 구조가 모두 확인된 항목만 확정 위험으로 표시합니다. LLM만 탐지했거나
주체·행위·대상이 충분히 확인되지 않는 항목은 `review_required=true`와 함께 `검토 필요`로
표시하고 위험 점수 반영 비중을 낮춥니다. `공제하지 않는다`처럼 위험 행위를 금지하는 문장은
부정문 검증 단계에서 제외합니다.

정상·위험 표현 데이터는 `ai/tests/data/semantic_contract_cases.json`에 누적합니다. 새로운
표현에서 오탐 또는 미탐이 발견되면 개별 계약서에만 맞춘 코드를 추가하지 않고 데이터셋 사례와
의미 추출 규칙을 함께 보완합니다. 분류 모델 파인튜닝은 충분한 검수 데이터가 축적된 후 별도
평가셋을 분리해 진행합니다.

## 배포 전 남은 점검

- 스캔 이미지 PDF용 OCR
- Refresh Token과 로그아웃 토큰 폐기
- 업로드 파일 악성코드 검사
- 운영 스케줄러에서 공식 법령 동기화 작업의 실행 주기와 실패 알림 설정
- 운영 환경의 작업 큐와 다중 인스턴스 분석 취소 동기화
- 위험도 점수는 법적 확률이 아니라 설명 가능한 우선순위 점수임
