from typing import Optional

from pydantic_settings import BaseSettings


class AppConfig(BaseSettings):
    debug: bool = True

    mailtrap_host: Optional[str] = None
    mailtrap_sender_email: Optional[str] = None
    mailtrap_send_to_email: Optional[str] = None
    mailtrap_token: Optional[str] = None

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
