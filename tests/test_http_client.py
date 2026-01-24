import pytest
from unittest.mock import patch, MagicMock
import httpx

from src.infrastructure.clients.http_client import HttpClient
from src.infrastructure.clients.browser_profiles import BROWSER_PROFILES


class TestHttpClientInit:
    def test_init_default_values(self):
        client = HttpClient()
        # Should have a User-Agent from one of the browser profiles
        assert "User-Agent" in client.headers
        assert any(profile["User-Agent"] == client.headers["User-Agent"] for profile in BROWSER_PROFILES)
        assert client.timeout.read == 30
        assert client.timeout.connect == 15.0
        assert client.max_retries == 3
        assert client.retry_delay == 2.0

    def test_init_uses_browser_profile_headers(self):
        client = HttpClient()
        # Should include standard browser headers
        assert "Accept" in client.headers
        assert "Accept-Language" in client.headers
        assert "Accept-Encoding" in client.headers
        assert "Sec-Fetch-Dest" in client.headers
        assert "Sec-Fetch-Mode" in client.headers

    def test_init_custom_values(self):
        headers = {"User-Agent": "TestBot"}
        client = HttpClient(headers=headers, timeout=60, max_retries=5, retry_delay=5.0)
        # Custom headers should override browser profile headers
        assert client.headers["User-Agent"] == "TestBot"
        # But still include other browser profile headers
        assert "Accept" in client.headers
        assert client.timeout.read == 60
        assert client.max_retries == 5
        assert client.retry_delay == 5.0


class TestHttpClientFetch:
    @pytest.fixture
    def client(self):
        return HttpClient(timeout=10)

    def test_fetch_success(self, client):
        mock_response = MagicMock()
        mock_response.text = "<html><body>Test</body></html>"

        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            result = client.fetch("https://test.com", "utf-8")

            assert result == "<html><body>Test</body></html>"
            mock_response.raise_for_status.assert_called_once()

    def test_fetch_sets_encoding(self, client):
        mock_response = MagicMock()

        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            client.fetch("https://test.com", "windows-1251")

            assert mock_response.encoding == "windows-1251"

    def test_fetch_raises_on_error(self, client):
        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.side_effect = httpx.RequestError("Connection failed")

            with pytest.raises(httpx.RequestError):
                client.fetch("https://test.com", "utf-8")


class TestHttpClientFetchJson:
    @pytest.fixture
    def client(self):
        return HttpClient(timeout=10)

    def test_fetch_json_success(self, client):
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": "test"}

        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            result = client.fetch_json("https://test.com/api")

            assert result == {"data": "test"}
            mock_response.raise_for_status.assert_called_once()

    def test_fetch_json_raises_on_error(self, client):
        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.side_effect = httpx.RequestError("Connection failed")

            with pytest.raises(httpx.RequestError):
                client.fetch_json("https://test.com/api")


class TestHttpClientWithHeaders:
    def test_fetch_with_custom_headers(self):
        custom_headers = {"Authorization": "Bearer token"}
        client = HttpClient(headers=custom_headers)

        with patch("httpx.Client") as mock_client:
            mock_response = MagicMock()
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            client.fetch("https://test.com", "utf-8")

            mock_client.assert_called_once()
            call_kwargs = mock_client.call_args.kwargs
            # Custom headers should be merged with browser profile headers
            assert call_kwargs["headers"]["Authorization"] == "Bearer token"
            assert "User-Agent" in call_kwargs["headers"]


class TestHttpClientHTTPStatusErrors:
    @pytest.fixture
    def client(self):
        return HttpClient(timeout=10)

    def test_fetch_raises_on_404(self, client):
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404 Not Found",
            request=MagicMock(),
            response=MagicMock(status_code=404),
        )

        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            with pytest.raises(httpx.HTTPStatusError):
                client.fetch("https://test.com", "utf-8")

    def test_fetch_raises_on_500(self, client):
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500 Internal Server Error",
            request=MagicMock(),
            response=MagicMock(status_code=500),
        )

        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            with pytest.raises(httpx.HTTPStatusError):
                client.fetch("https://test.com", "utf-8")

    def test_fetch_json_raises_on_404(self, client):
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404 Not Found",
            request=MagicMock(),
            response=MagicMock(status_code=404),
        )

        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            with pytest.raises(httpx.HTTPStatusError):
                client.fetch_json("https://test.com/api")

    def test_fetch_json_raises_on_500(self, client):
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500 Internal Server Error",
            request=MagicMock(),
            response=MagicMock(status_code=500),
        )

        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            with pytest.raises(httpx.HTTPStatusError):
                client.fetch_json("https://test.com/api")
