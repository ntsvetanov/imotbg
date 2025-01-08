from pydantic_settings import BaseSettings


class AppConfig(BaseSettings):
    debug: bool = True

    mailtrap_host: str
    mailtrap_sender_email: str
    mailtrap_send_to_email: str
    mailtrap_token: str

    class Config:
        env_file = ".env"


app_config = AppConfig()
