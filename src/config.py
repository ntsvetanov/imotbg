from pydantic_settings import BaseSettings


class AppConfig(BaseSettings):
    debug: bool = True

    mailtrap_host: str | None = None
    mailtrap_sender_email: str | None = None
    mailtrap_send_to_email: str | None = None
    mailtrap_token: str | None = None

    @property
    def is_email_configured(self) -> bool:
        return all(
            [
                self.mailtrap_host,
                self.mailtrap_sender_email,
                self.mailtrap_send_to_email,
                self.mailtrap_token,
            ]
        )


app_config = AppConfig()
