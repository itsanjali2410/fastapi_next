from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    
    # Enable .env loading
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    
    # --- JWT ---
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # default = 8 days
    
    # --- Database ---
    MONGO_URL: str
    DB_NAME: str


settings = Settings()
