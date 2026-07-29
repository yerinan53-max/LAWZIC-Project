from pathlib import Path

from dotenv import load_dotenv


AI_PROJECT_DIR = Path(__file__).resolve().parents[1]

# 실제 운영 환경에서 이미 설정한 환경변수를 .env 값으로 덮어쓰지 않는다.
load_dotenv(AI_PROJECT_DIR / ".env", override=False)
