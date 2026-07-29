# LAWZIC MariaDB 설정

LAWZIC 애플리케이션은 MariaDB를 기본 데이터베이스로 사용합니다. H2는 자동화 테스트의
인메모리 DB로만 사용되며 실제 서비스 데이터는 저장하지 않습니다.

## 1. 데이터베이스와 전용 사용자 생성

관리자 PowerShell에서 MariaDB 클라이언트를 실행합니다.

```powershell
& "C:\Program Files\MariaDB 10.6\bin\mariadb.exe" -u root -p
```

`Enter password`가 표시되면 MariaDB 설치 당시 설정한 root 비밀번호를 입력합니다.
비밀번호는 화면에 표시되지 않는 것이 정상입니다.

접속 후 아래 SQL을 실행합니다. `안전한-비밀번호`는 새로 만든 강한 비밀번호로 바꿉니다.

```sql
CREATE DATABASE IF NOT EXISTS lawzic
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'lawzic'@'localhost'
  IDENTIFIED BY '안전한-비밀번호';

GRANT ALL PRIVILEGES ON lawzic.* TO 'lawzic'@'localhost';
FLUSH PRIVILEGES;
```

종료:

```sql
exit
```

## 2. 백엔드 환경변수

백엔드를 실행할 PowerShell에서 설정합니다.

```powershell
$env:DB_URL="jdbc:mariadb://localhost:3306/lawzic?useUnicode=true&characterEncoding=UTF-8"
$env:DB_USERNAME="lawzic"
$env:DB_PASSWORD="위에서-설정한-비밀번호"
```

Google OAuth 환경변수도 같은 PowerShell에 설정한 다음 백엔드를 실행합니다.

```powershell
cd "C:\Users\human-21\Documents\Final Project\backend"
..\tools\apache-maven-3.9.9\bin\mvn.cmd spring-boot:run
```

최초 실행 시 Hibernate가 필요한 테이블을 MariaDB에 생성합니다.

## 3. 배포 환경

- root 계정으로 애플리케이션을 실행하지 않습니다.
- `DB_PASSWORD`를 Git, 프론트 코드, `application.yml`에 저장하지 않습니다.
- 운영에서는 배포 플랫폼의 Secret 또는 환경변수를 사용합니다.
- 운영 전 `ddl-auto: update` 대신 Flyway 같은 명시적 스키마 마이그레이션 도구 도입을 권장합니다.

## 기존 H2 데이터

기존 파일은 `backend/data/lawzic.mv.db`에 남아 있으며 자동으로 삭제하지 않습니다.
MariaDB 전환 후 신규 데이터는 MariaDB에 저장됩니다. 기존 사용자·분석 이력을 MariaDB로
옮겨야 한다면 별도의 일회성 데이터 이관을 수행해야 합니다.
