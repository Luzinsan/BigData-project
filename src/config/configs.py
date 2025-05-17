from pydantic_settings import BaseSettings
from typing import List, Optional


class Settings(BaseSettings):
    """
    Settings for the project.
    """
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_PORT: int
    
    SCRIPTS_DIR: str = 'src/app/scripts/'
    DATA_DIR: str = 'data/'

    class Config:
        env_file = ".env"


settings = Settings()