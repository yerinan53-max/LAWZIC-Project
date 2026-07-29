# Google·Naver 소셜 로그인 설정

LAWZIC은 OAuth 2.0 Authorization Code 흐름을 백엔드에서 처리합니다. 제공자의 액세스 토큰은
프론트엔드나 LAWZIC JWT에 포함하지 않습니다. 콜백 완료 후 2분짜리 일회용 티켓을 발급하고,
프론트엔드가 해당 티켓을 LAWZIC JWT로 교환합니다. 티켓 원문은 DB에 저장하지 않습니다.

## 환경변수

```text
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
NAVER_CLIENT_ID=...
NAVER_CLIENT_SECRET=...
FRONTEND_URL=http://localhost:5173
```

운영 환경에서는 `FRONTEND_URL`과 OAuth 애플리케이션의 서비스 URL을 HTTPS 주소로 설정합니다.
Client Secret은 프론트 코드나 Git 저장소에 넣지 않습니다.

## 제공자 콘솔 Redirect URI

로컬 개발:

```text
Google: http://localhost:8080/login/oauth2/code/google
Naver:  http://localhost:8080/login/oauth2/code/naver
```

배포 시에는 `http://localhost:8080` 부분을 실제 백엔드 HTTPS 도메인으로 바꿉니다.

Google은 `openid profile email`, 네이버는 `name email`만 요청합니다. 네이버 개발자센터에서
이메일 제공 권한을 사용하도록 설정해야 합니다.

## 계정 병합 정책

- `provider + providerUserId`를 소셜 계정의 고유 식별자로 사용합니다.
- 이메일이 같은 기존 일반 계정을 자동 병합하지 않습니다.
- 기존 비밀번호를 다시 확인한 경우에만 소셜 계정을 연결합니다.
- 신규 소셜 사용자는 필수 이용약관과 개인정보 수집·이용에 동의한 뒤 계정이 생성됩니다.
- 소셜 전용 계정이 비밀번호가 필요한 작업을 수행하려면 이메일 비밀번호 재설정으로 비밀번호를 설정할 수 있습니다.
