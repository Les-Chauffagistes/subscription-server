from pydantic_settings import BaseSettings
from typing import Literal


class Settings(BaseSettings):
    opennode_api_key: str
    opennode_api_url: str
    callback_url: str
    auth_token: str
    server_port: int = 8080
    application_mode: Literal["DEV", "PROD"] = "DEV"
    database_url: str

    model_config = {"env_file": ".env"}


settings = Settings()  # type: ignore[call-arg]
