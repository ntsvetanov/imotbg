import sys
from unittest.mock import MagicMock, patch

import pytest


class TestEmailClientInit:
    def test_init_sets_sender_email(self):
        mock_mt = MagicMock()
        mock_config = MagicMock()
        mock_config.mailtrap_sender_email = "sender@test.com"
        mock_config.mailtrap_send_to_email = "recipient@test.com"
        mock_config.mailtrap_token = "test-token"

        with patch.dict(sys.modules, {"mailtrap": mock_mt}):
            with patch("src.config.app_config", mock_config):
                # Need to reload/reimport to pick up the patched modules
                from src.infrastructure.clients.email_client import EmailClient

                client = EmailClient()
                assert client.sender_email == "sender@test.com"

    def test_init_sets_send_to_email(self):
        mock_mt = MagicMock()
        mock_config = MagicMock()
        mock_config.mailtrap_sender_email = "sender@test.com"
        mock_config.mailtrap_send_to_email = "recipient@test.com"
        mock_config.mailtrap_token = "test-token"

        with patch.dict(sys.modules, {"mailtrap": mock_mt}):
            with patch("src.config.app_config", mock_config):
                from src.infrastructure.clients.email_client import EmailClient

                client = EmailClient()
                assert client.send_to_email == "recipient@test.com"

    def test_init_creates_mailtrap_client_with_token(self):
        mock_mt = MagicMock()
        mock_config = MagicMock()
        mock_config.mailtrap_sender_email = "sender@test.com"
        mock_config.mailtrap_send_to_email = "recipient@test.com"
        mock_config.mailtrap_token = "test-token-123"

        with patch.dict(sys.modules, {"mailtrap": mock_mt}):
            with patch("src.config.app_config", mock_config):
                from src.infrastructure.clients.email_client import EmailClient

                # Clear cache to force reimport
                if "src.infrastructure.clients.email_client" in sys.modules:
                    del sys.modules["src.infrastructure.clients.email_client"]

                EmailClient()
                mock_mt.MailtrapClient.assert_called_with(token="test-token-123")


class TestEmailClientSendEmail:
    @pytest.fixture
    def mock_setup(self):
        mock_mt = MagicMock()
        mock_config = MagicMock()
        mock_config.mailtrap_sender_email = "sender@test.com"
        mock_config.mailtrap_send_to_email = "recipient@test.com"
        mock_config.mailtrap_token = "test-token"
        return mock_mt, mock_config

    def test_send_email_creates_mail_with_correct_subject(self, mock_setup):
        mock_mt, mock_config = mock_setup

        with patch.dict(sys.modules, {"mailtrap": mock_mt}):
            with patch("src.config.app_config", mock_config):
                if "src.infrastructure.clients.email_client" in sys.modules:
                    del sys.modules["src.infrastructure.clients.email_client"]

                from src.infrastructure.clients.email_client import EmailClient

                client = EmailClient()
                client.send_email("Test Subject", "Test body")

                mock_mt.Mail.assert_called_once()
                call_kwargs = mock_mt.Mail.call_args.kwargs
                assert call_kwargs["subject"] == "Test Subject"

    def test_send_email_creates_mail_with_correct_text(self, mock_setup):
        mock_mt, mock_config = mock_setup

        with patch.dict(sys.modules, {"mailtrap": mock_mt}):
            with patch("src.config.app_config", mock_config):
                if "src.infrastructure.clients.email_client" in sys.modules:
                    del sys.modules["src.infrastructure.clients.email_client"]

                from src.infrastructure.clients.email_client import EmailClient

                client = EmailClient()
                client.send_email("Test Subject", "Test body content")

                call_kwargs = mock_mt.Mail.call_args.kwargs
                assert call_kwargs["text"] == "Test body content"

    def test_send_email_creates_mail_with_sender_address(self, mock_setup):
        mock_mt, mock_config = mock_setup

        with patch.dict(sys.modules, {"mailtrap": mock_mt}):
            with patch("src.config.app_config", mock_config):
                if "src.infrastructure.clients.email_client" in sys.modules:
                    del sys.modules["src.infrastructure.clients.email_client"]

                from src.infrastructure.clients.email_client import EmailClient

                client = EmailClient()
                client.send_email("Subject", "Body")

                mock_mt.Address.assert_any_call(email="sender@test.com")

    def test_send_email_creates_mail_with_recipient_address(self, mock_setup):
        mock_mt, mock_config = mock_setup

        with patch.dict(sys.modules, {"mailtrap": mock_mt}):
            with patch("src.config.app_config", mock_config):
                if "src.infrastructure.clients.email_client" in sys.modules:
                    del sys.modules["src.infrastructure.clients.email_client"]

                from src.infrastructure.clients.email_client import EmailClient

                client = EmailClient()
                client.send_email("Subject", "Body")

                mock_mt.Address.assert_any_call(email="recipient@test.com")

    def test_send_email_calls_client_send(self, mock_setup):
        mock_mt, mock_config = mock_setup
        mock_client_instance = MagicMock()
        mock_mt.MailtrapClient.return_value = mock_client_instance
        mock_mail = MagicMock()
        mock_mt.Mail.return_value = mock_mail

        with patch.dict(sys.modules, {"mailtrap": mock_mt}):
            with patch("src.config.app_config", mock_config):
                if "src.infrastructure.clients.email_client" in sys.modules:
                    del sys.modules["src.infrastructure.clients.email_client"]

                from src.infrastructure.clients.email_client import EmailClient

                client = EmailClient()
                client.send_email("Subject", "Body")

                mock_client_instance.send.assert_called_once_with(mock_mail)

    def test_send_email_returns_response(self, mock_setup):
        mock_mt, mock_config = mock_setup
        mock_client_instance = MagicMock()
        mock_mt.MailtrapClient.return_value = mock_client_instance
        expected_response = {"success": True, "message_id": "123"}
        mock_client_instance.send.return_value = expected_response

        with patch.dict(sys.modules, {"mailtrap": mock_mt}):
            with patch("src.config.app_config", mock_config):
                if "src.infrastructure.clients.email_client" in sys.modules:
                    del sys.modules["src.infrastructure.clients.email_client"]

                from src.infrastructure.clients.email_client import EmailClient

                client = EmailClient()
                result = client.send_email("Subject", "Body")

                assert result == expected_response


class TestEmailClientEdgeCases:
    @pytest.fixture
    def mock_setup(self):
        mock_mt = MagicMock()
        mock_config = MagicMock()
        mock_config.mailtrap_sender_email = "sender@test.com"
        mock_config.mailtrap_send_to_email = "recipient@test.com"
        mock_config.mailtrap_token = "test-token"
        return mock_mt, mock_config

    def test_send_email_with_empty_subject(self, mock_setup):
        mock_mt, mock_config = mock_setup

        with patch.dict(sys.modules, {"mailtrap": mock_mt}):
            with patch("src.config.app_config", mock_config):
                if "src.infrastructure.clients.email_client" in sys.modules:
                    del sys.modules["src.infrastructure.clients.email_client"]

                from src.infrastructure.clients.email_client import EmailClient

                client = EmailClient()
                client.send_email("", "Body")

                call_kwargs = mock_mt.Mail.call_args.kwargs
                assert call_kwargs["subject"] == ""

    def test_send_email_with_empty_text(self, mock_setup):
        mock_mt, mock_config = mock_setup

        with patch.dict(sys.modules, {"mailtrap": mock_mt}):
            with patch("src.config.app_config", mock_config):
                if "src.infrastructure.clients.email_client" in sys.modules:
                    del sys.modules["src.infrastructure.clients.email_client"]

                from src.infrastructure.clients.email_client import EmailClient

                client = EmailClient()
                client.send_email("Subject", "")

                call_kwargs = mock_mt.Mail.call_args.kwargs
                assert call_kwargs["text"] == ""

    def test_send_email_with_long_text(self, mock_setup):
        mock_mt, mock_config = mock_setup

        with patch.dict(sys.modules, {"mailtrap": mock_mt}):
            with patch("src.config.app_config", mock_config):
                if "src.infrastructure.clients.email_client" in sys.modules:
                    del sys.modules["src.infrastructure.clients.email_client"]

                from src.infrastructure.clients.email_client import EmailClient

                client = EmailClient()
                long_text = "A" * 10000
                client.send_email("Subject", long_text)

                call_kwargs = mock_mt.Mail.call_args.kwargs
                assert call_kwargs["text"] == long_text

    def test_send_email_with_special_characters(self, mock_setup):
        mock_mt, mock_config = mock_setup

        with patch.dict(sys.modules, {"mailtrap": mock_mt}):
            with patch("src.config.app_config", mock_config):
                if "src.infrastructure.clients.email_client" in sys.modules:
                    del sys.modules["src.infrastructure.clients.email_client"]

                from src.infrastructure.clients.email_client import EmailClient

                client = EmailClient()
                special_text = "Special chars: <>&\"' \n\t\r"
                client.send_email("Subject with <html>", special_text)

                call_kwargs = mock_mt.Mail.call_args.kwargs
                assert call_kwargs["subject"] == "Subject with <html>"
                assert call_kwargs["text"] == special_text

    def test_send_email_with_unicode_characters(self, mock_setup):
        mock_mt, mock_config = mock_setup

        with patch.dict(sys.modules, {"mailtrap": mock_mt}):
            with patch("src.config.app_config", mock_config):
                if "src.infrastructure.clients.email_client" in sys.modules:
                    del sys.modules["src.infrastructure.clients.email_client"]

                from src.infrastructure.clients.email_client import EmailClient

                client = EmailClient()
                unicode_text = "Cyrillic: Здравей, Emoji: 😀, Chinese: 中文"
                client.send_email("Unicode subject: България", unicode_text)

                call_kwargs = mock_mt.Mail.call_args.kwargs
                assert call_kwargs["subject"] == "Unicode subject: България"
                assert call_kwargs["text"] == unicode_text
