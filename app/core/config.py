from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    """
    Application settings, loaded from environment variables and the .env file.
    """
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # MySQL database settings
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str

    # Ollama settings
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    # If not set, the best locally installed model is picked automatically.
    OLLAMA_MODEL: Optional[str] = None

    def _database_url(self, driver: str) -> URL:
        return URL.create(
            drivername=driver,
            username=self.DB_USER,
            password=self.DB_PASSWORD,
            host=self.DB_HOST,
            port=self.DB_PORT,
            database=self.DB_NAME,
            query={"charset": "utf8mb4"},
        )

    @property
    def SYNC_DATABASE_URL(self) -> URL:
        return self._database_url("mysql+mysqlconnector")

    @property
    def ASYNC_DATABASE_URL(self) -> URL:
        return self._database_url("mysql+aiomysql")


settings = Settings()
