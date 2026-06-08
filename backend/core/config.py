"""
Application configuration using Pydantic Settings.

All settings can be overridden via environment variables or a .env file.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central application configuration.

    Attributes:
        DATABASE_URL: SQLAlchemy-compatible database connection string.
        SECRET_KEY: Signing key for JWTs – MUST be changed in production.
        ALGORITHM: JWT signing algorithm.
        ACCESS_TOKEN_EXPIRE_MINUTES: Lifetime of access tokens in minutes.
        REFRESH_TOKEN_EXPIRE_DAYS: Lifetime of refresh tokens in days.
        CORS_ORIGINS: Comma-separated list of allowed CORS origins.
        LOG_LEVEL: Python logging level name.
        ENVIRONMENT: Runtime environment tag (development / staging / production).
        INFERENCE_MODE: Default inference mode – "image" or "landmark".
        MODEL_PATH: Filesystem path to the trained Keras model.
        CLASS_NAMES_PATH: Filesystem path to the JSON file mapping indices to class names.
        MODEL_BACKBONE: Default model backbone identifier.
    """

    DATABASE_URL: str = "sqlite:///./gesture_recognition.db"
    SECRET_KEY: str = "change-me-in-production-use-openssl-rand-hex-32"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"
    LOG_LEVEL: str = "INFO"
    ENVIRONMENT: str = "development"
    INFERENCE_MODE: str = "image"  # image or landmark
    MODEL_PATH: str = "models/best_model.keras"
    CLASS_NAMES_PATH: str = "models/class_names.json"
    MODEL_BACKBONE: str = "cnn"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
