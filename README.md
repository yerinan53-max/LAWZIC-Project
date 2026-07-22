# LAWZIC

Agentic RAG 기반 근로계약서 위험조항 분석 플랫폼의 실행 가능한 MVP입니다.

현재 버전은 회원가입, JWT 로그인, PDF 업로드, 텍스트 추출, 규칙 기반 위험 탐지, ChromaDB 법령 검색, 분석 결과 저장과 화면 출력을 한 흐름으로 연결합니다. LLM과 LangGraph는 다음 단계에서 기존 AI 분석 모듈 안에 추가합니다.

> 분석 결과는 참고 정보이며 법률 자문이나 법적 판단을 대체하지 않습니다.

## 처리 흐름

```text
React
  → Spring Boot: 회원가입 / 로그인 / JWT 검증
  → Spring Boot: PDF 검사 / 파일 및 DB 저장
  → FastAPI: PDF 텍스트 추출 / 위험 표현 탐지 / ChromaDB 관련 법령 검색
  → Spring Boot: 분석 JSON 저장
  → React: 요약 / 위험도 / 위험 조항 표시
```

브라우저는 FastAPI를 직접 호출하지 않습니다. 인증과 계약서 소유권 검사는 Spring Boot 한 곳에서 담당합니다.

## 폴더

```text
backend/   Spring Boot + Security + JWT + JPA
ai/        FastAPI + PyMuPDF + 위험 분석
frontend/  React + Vite
docs/      설계 문서
```

## 필요한 프로그램

- Java 17
- Maven 3.9 이상
- Python 3.12 권장
- Node.js 20 이상
- MySQL 8은 선택 사항입니다. 기본 실행은 H2 파일 DB를 사용합니다.

현재 컴퓨터에서 확인된 기본 환경은 Java 17과 Python 3.10이며 Maven과 Node.js는 PATH에 없습니다. Python 코드는 3.12를 기준으로 작성했습니다.

## 1. AI 서버 실행

PowerShell:

```powershell
cd ai
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

### LangGraph Agent + Ollama LLM

AI 서버는 다음 순서의 LangGraph 워크플로로 계약서를 분석합니다.

```text
규칙 기반 사전 분석 → ChromaDB 법령 검색 → LLM 조건 분기
→ Ollama 구조화 위험 분석 → 검색 근거 검증 → 최종 리포트
```

기본 LLM은 로컬 `gemma2:2b`입니다. Ollama를 실행하고 모델을 준비하세요.

```powershell
ollama pull gemma2:2b
ollama serve
```

다른 모델을 사용하거나 LLM을 잠시 끄려면 AI 서버 실행 전에 설정합니다.

```powershell
$env:OLLAMA_MODEL="gemma2:9b"
$env:OLLAMA_BASE_URL="http://localhost:11434"
$env:LAWZIC_LLM_ENABLED="true"
```

LLM 또는 Ollama 호출에 실패하면 서비스가 중단되지 않고 규칙 기반 분석 결과로 자동 전환됩니다.

확인 주소: `http://localhost:8000/docs`, `http://localhost:8000/health`

### 법령 Vector DB 다시 만들기

```powershell
cd ai
.\.venv\Scripts\python.exe -m scripts.ingest_laws
```

현재 seed 데이터는 `ai/data/laws/labor_laws_seed.json`의 공식 법령 10개 조문입니다. Vector DB는 `ai/data/chroma`에 생성됩니다.

RAG 단독 검색은 다음 API로 확인합니다.

```text
GET http://localhost:8000/internal/v1/rag/search?q=퇴직금은 급여에 포함한다&top_k=3
```

## 2. Spring Boot 실행

새 PowerShell:

```powershell
cd backend
mvn spring-boot:run
```

기본값은 별도 설치가 필요 없는 H2 DB입니다. MySQL로 전환할 때:

```powershell
$env:DB_URL="jdbc:mysql://localhost:3306/lawzic?serverTimezone=Asia/Seoul&characterEncoding=UTF-8"
$env:DB_USERNAME="root"
$env:DB_PASSWORD="본인비밀번호"
mvn spring-boot:run -Dspring-boot.run.profiles=mysql
```

운영 또는 공개 배포 전에는 반드시 `JWT_SECRET`을 긴 무작위 값으로 변경해야 합니다.

## 3. React 실행

새 PowerShell:

```powershell
cd frontend
npm install
npm run dev
```

접속 주소: `http://localhost:5173`

## 처음 확인할 시나리오

1. 회원가입한다. 비밀번호는 8자 이상이다.
2. 로그인한다.
3. 텍스트가 들어 있는 근로계약서 PDF를 업로드한다.
4. 분석 버튼을 누른다.
5. 위험 점수, 원문 일부, 사유와 권고가 표시되는지 확인한다.

스캔 이미지 PDF는 현재 지원하지 않습니다. OCR은 후속 기능입니다.

## 코드 읽는 순서

1. `frontend/src/App.jsx`: 사용자의 클릭이 어디에서 API 요청으로 바뀌는지 확인
2. `backend/.../auth/AuthController.java`: 회원가입과 로그인 흐름 확인
3. `backend/.../config/JwtAuthenticationFilter.java`: 요청마다 JWT가 검증되는 과정 확인
4. `backend/.../contract/ContractService.java`: PDF 검증과 저장 과정 확인
5. `backend/.../analysis/AnalysisService.java`: Spring에서 FastAPI를 호출하고 결과를 저장하는 과정 확인
6. `ai/app/main.py`: FastAPI 요청 진입점 확인
7. `ai/app/pdf_service.py`: PDF 본문 추출 확인
8. `ai/app/analyzer.py`: 위험 규칙과 점수 계산 확인

## 다음 개발 순서

1. 공식 법령 seed를 전체 대상 법령으로 확대하고 자동 갱신
2. 표준근로계약서 데이터 추가
3. 검색 문맥을 포함한 LLM 구조화 응답 추가
4. PDF 추출 → 조항 분리 → 규칙 탐지 → RAG → LLM → 결과 통합을 LangGraph 노드로 변환
5. 동기 분석을 백그라운드 작업과 상태 조회 방식으로 개선

자세한 설계와 API 목록은 [docs/DESIGN.md](docs/DESIGN.md)를 참고하세요.
