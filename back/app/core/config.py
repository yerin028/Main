from pydantic import computed_field  # 여러 환경변수 값을 조합해서 database_url을 계산하기 위해 사용합니다.
from pydantic_settings import BaseSettings, SettingsConfigDict  # env 파일 값을 Python 설정 객체로 읽기 위해 사용합니다.


class Settings(BaseSettings):
    # MySQL 서버 주소입니다.
    # env 파일에 DB_HOST 값이 있으면 그 값으로 덮어씁니다.
    db_host: str = "localhost"

    # MySQL 접속 사용자명입니다.
    # env 파일에 MYSQL_USER 값이 있으면 그 값으로 덮어씁니다.
    mysql_user: str = "root"

    # MySQL 접속 비밀번호입니다.
    # 실제 비밀번호는 env 파일에 두고 코드에는 기본값만 둡니다.
    mysql_password: str = "password"

    # 연결할 MySQL 데이터베이스 이름입니다.
    # env 파일에 MYSQL_DB 값이 있으면 그 값으로 덮어씁니다.
    mysql_db: str = "with"

    # 국립수어원/문화공공데이터 API 호출에 사용하는 서비스 키입니다.
    # sync endpoint에서 외부 API 요청을 보낼 때 사용합니다.
    sign_api_service_key: str = ""

    @computed_field
    @property
    def database_url(self) -> str:
        # SQLAlchemy가 MySQL에 연결할 때 사용하는 최종 DB 접속 문자열을 만듭니다.
        # 예: mysql+pymysql://user:password@host:3306/dbname
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.db_host}:3306/{self.mysql_db}"
        )

    # 설정값을 읽을 env 파일 후보입니다.
    # 팀 환경에 따라 .env, env, back/env 중 존재하는 파일에서 값을 읽습니다.
    model_config = SettingsConfigDict(
        env_file=(".env", "env", "back/env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


# 다른 파일에서 from app.core.config import settings 로 가져다 쓰는 전역 설정 객체입니다.
settings = Settings()
