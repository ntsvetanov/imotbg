import mailtrap as mt

from config import app_config
from src.logger_setup import get_logger

logger = get_logger(__name__)


class EmailClient:
    def __init__(self):
        self.sender_email = app_config.mailtrap_sender_email
        self.send_to_email = app_config.mailtrap_send_to_email
        self._client = mt.MailtrapClient(token=app_config.mailtrap_token)
        logger.debug(f"EmailClient initialized: {self.sender_email} -> {self.send_to_email}")

    def send_email(self, subject: str, text: str):
        mail = mt.Mail(
            sender=mt.Address(email=self.sender_email),
            to=[mt.Address(email=self.send_to_email)],
            subject=subject,
            text=text,
        )
        response = self._client.send(mail)
        logger.info(f"Email sent: {response}")
        return response
