from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    SQLDB_URL: str
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 5 * 60
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 7 * 24 * 60

    model_config = {
        "env_file": ".env",
        "validate_assignment": True,
        "extra": "allow",
    }

@lru_cache()
def get_settings():
    return Settings()
