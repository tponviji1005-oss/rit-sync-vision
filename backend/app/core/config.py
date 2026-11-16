"""
RIT Sync Vision - Core Configuration Settings
"""

import os
from pathlib import Path
from typing import Optional
from pydantic import model_validator

# Path to the repository root where .env is located
ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
ENV_FILE = ROOT_DIR / ".env"

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict

    class Settings(BaseSettings):
        # Application Settings
        APP_ENV: str = "development"
        DEBUG: bool = True
        SECRET_KEY: str = "change-this-secret-key-in-production"

        # Server Settings
        BACKEND_HOST: str = "0.0.0.0"
        BACKEND_PORT: int = 8000

        # Database Settings
        DATABASE_URL: str = "sqlite:///./storage/database/rit_sync_vision.db"

        # Storage Paths
        STORAGE_DIR: str = "./storage"
        FACE_TEMPLATES_DIR: str = "./storage/face_templates"
        TEMP_DIR: str = "./storage/temporary"

        # AI Engine / Camera Configuration
        CAMERA_RTSP_STREAM_URL: str = ""
        CONFIDENCE_THRESHOLD: float = 0.65
        DETECTION_MODEL_PATH: str = "ai_engine/models/"

        model_config = SettingsConfigDict(
            env_file=str(ENV_FILE) if ENV_FILE.exists() else None,
            env_file_encoding="utf-8",
            extra="ignore",
        )

        @model_validator(mode="after")
        def validate_production_secret(self):
            # SEC-03: Block startup in production if secret key is the insecure default
            if (
                self.APP_ENV.lower() == "production"
                and self.SECRET_KEY == "change-this-secret-key-in-production"
            ):
                raise ValueError(
                    "Insecure SECRET_KEY: Default secret key cannot be used in production environment."
                )
            return self

except ImportError:
    from pydantic import BaseModel

    class Settings(BaseModel):
        # Application Settings
        APP_ENV: str = "development"
        DEBUG: bool = True
        SECRET_KEY: str = "change-this-secret-key-in-production"

        # Server Settings
        BACKEND_HOST: str = "0.0.0.0"
        BACKEND_PORT: int = 8000

        # Database Settings
        DATABASE_URL: str = "sqlite:///./storage/database/rit_sync_vision.db"

        # Storage Paths
        STORAGE_DIR: str = "./storage"
        FACE_TEMPLATES_DIR: str = "./storage/face_templates"
        TEMP_DIR: str = "./storage/temporary"

        # AI Engine / Camera Configuration
        CAMERA_RTSP_STREAM_URL: str = ""
        CONFIDENCE_THRESHOLD: float = 0.65
        DETECTION_MODEL_PATH: str = "ai_engine/models/"

        @model_validator(mode="after")
        def validate_production_secret(self):
            # SEC-03: Block startup in production if secret key is the insecure default
            if (
                self.APP_ENV.lower() == "production"
                and self.SECRET_KEY == "change-this-secret-key-in-production"
            ):
                raise ValueError(
                    "Insecure SECRET_KEY: Default secret key cannot be used in production environment."
                )
            return self

        def __init__(self, **kwargs):
            data = {}
            if ENV_FILE.exists():
                try:
                    from dotenv import dotenv_values
                    env_vals = dotenv_values(str(ENV_FILE))
                    for k, v in env_vals.items():
                        if v is not None:
                            data[k] = v
                except Exception:
                    pass

            for k in type(self).model_fields.keys():
                if k in os.environ:
                    data[k] = os.environ[k]

            data.update(kwargs)
            super().__init__(**data)


settings = Settings()
