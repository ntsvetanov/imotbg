import pytest
from unittest.mock import patch, MagicMock
import httpx

from src.infrastructure.clients.http_client import HttpClient


class TestHttpClientInit:
    def test_init_default_values(self):
        client = HttpClient()
        assert client.headers is None
        assert client.timeout == 10

    def test_init_custom_values(self):
        headers = {"User-Agent": "TestBot"}
        client = HttpClient(headers=headers, timeout=30)
        assert client.headers == headers
        assert client.timeout == 30


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
        headers = {"Authorization": "Bearer token"}
        client = HttpClient(headers=headers)

        with patch("httpx.Client") as mock_client:
            mock_response = MagicMock()
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            client.fetch("https://test.com", "utf-8")

            mock_client.assert_called_once()
            call_kwargs = mock_client.call_args.kwargs
            assert call_kwargs["headers"] == headers


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
