from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ocean_api_token: str = ""
    prospeo_api_key: str = ""
    eazyreach_api_key: str = ""
    eazyreach_base_url: str = "https://api.eazyreach.app"

    brevo_api_key: str = ""
    brevo_sender_email: str = ""
    brevo_sender_name: str = "Outreach"

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_base_url: str | None = None

    product_pitch: str = Field(
        default="We help B2B teams automate outbound with AI voice agents."
    )

    request_delay_seconds: float = 0.5
    max_retries: int = 3


@lru_cache
def get_settings() -> Settings:
    return Settings()
