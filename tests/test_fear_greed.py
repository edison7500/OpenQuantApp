from __future__ import annotations

import httpx
import pytest

from api.fear_greed import FearGreedClient, FearGreedError


class FakeResponse:
    def __init__(self, payload, status_code: int = 200) -> None:
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            request = httpx.Request("GET", "https://example.test")
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError(
                "failed", request=request, response=response
            )

    def json(self):
        return self.payload


class FakeClient:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.calls = []

    def get(self, url: str, **kwargs):
        self.calls.append((url, kwargs))
        return self.response


def test_get_latest_normalizes_observation_and_request():
    fake = FakeClient(
        FakeResponse(
            {
                "data": [
                    {
                        "value": "33",
                        "value_classification": "Fear",
                        "timestamp": "1785628800",
                    }
                ],
                "metadata": {"error": None},
            }
        )
    )

    result = FearGreedClient(http_client=fake).get_latest()

    assert result.value == 33
    assert result.classification == "Fear"
    assert result.observation_date == "2026-08-02"
    assert result.source == "Alternative.me"
    _, kwargs = fake.calls[0]
    assert kwargs["params"] == {"limit": 1, "format": "json"}


@pytest.mark.parametrize(
    "payload",
    [
        {"data": [], "metadata": {"error": None}},
        {"data": [], "metadata": {"error": "rate limited"}},
        {
            "data": [
                {
                    "value": "invalid",
                    "value_classification": "Fear",
                    "timestamp": "1785628800",
                }
            ],
            "metadata": {"error": None},
        },
        {
            "data": [
                {
                    "value": "101",
                    "value_classification": "Greed",
                    "timestamp": "1785628800",
                }
            ],
            "metadata": {"error": None},
        },
    ],
)
def test_rejects_api_errors_and_invalid_observations(payload):
    client = FearGreedClient(http_client=FakeClient(FakeResponse(payload)))

    with pytest.raises(FearGreedError):
        client.get_latest()


def test_wraps_http_error():
    client = FearGreedClient(
        http_client=FakeClient(FakeResponse({}, status_code=503))
    )

    with pytest.raises(FearGreedError, match="请求失败"):
        client.get_latest()
