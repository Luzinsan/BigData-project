from pydantic_settings import BaseSettings
from typing import List, Optional


class Settings(BaseSettings):
    DB_NAME: str = 'dbname'
    DB_USER: str = 'postgres'
    DB_PASSWORD: str = 'password'
    DB_HOST: str = 'localhost'
    DB_PORT: int = 5432

    class Config:
        env_file = ".env"


configs = Settings()