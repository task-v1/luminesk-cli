import httpx
import pytest

from luminesk.utils.http import get_json_object_with_retries, request_with_retries


def test_request_with_retries_returns_final_error_response_open() -> None:
    class FakeResponse:
        is_success = False
        status_code = 503

        def __init__(self) -> None:
            self.closed = False

        def close(self) -> None:
            self.closed = True

    class FakeClient:
        def request(self, method: str, url: str) -> FakeResponse:
            return FakeResponse()

    response = request_with_retries(
        FakeClient(),
        "GET",
        "https://example.com/status",
        attempts=1,
        retry_on_status=True,
    )

    assert response.status_code == 503
    assert not response.closed


def test_get_json_object_with_retries_rejects_non_object_payload() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=["not", "an", "object"], request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler))

    with pytest.raises(ValueError, match="JSON response is not an object"):
        get_json_object_with_retries(client, "https://example.com/data")
