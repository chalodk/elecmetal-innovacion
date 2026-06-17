from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Supabase / DB
    database_url: str
    supabase_url: str
    supabase_jwt_secret: str = ""
    supabase_service_role_key: str = ""

    # OpenAI
    openai_api_key: str = ""

    # Email
    resend_api_key: str = ""
    email_from: str = "innovacion@elecmetal.cl"

    # App
    environment: str = "development"
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]


settings = Settings()
