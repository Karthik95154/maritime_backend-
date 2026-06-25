import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    api_v1_str: str = "/api/v1"
    project_name: str = "Maritime Inspection API"
    
    # MongoDB Config
    MONGODB_URL: str
    DATABASE_NAME: str = "maritime_inspection"
    
    # Security Config
    jwt_secret_key: str = "your-secret-key-for-dev"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 10080
    
    # File Paths
    upload_folder: str = "uploads"
    output_folder: str = "outputs/sessions"

    # Pipeline Orchestration URLs
    COMBINED_AI_URL: str = ""
    UNIQUE_DEFECT_URL: str = ""
    AREA_URL: str = ""
    COST_URL: str = ""
    REPORT_URL: str = ""
    BASE_BACKEND_URL: str = "https://your-backend-ngrok.app"

    # Microservice Registry JSON
    microservices_json: str = ""
    microservices_config_path: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

os.makedirs(settings.upload_folder, exist_ok=True)
os.makedirs(settings.output_folder, exist_ok=True)
