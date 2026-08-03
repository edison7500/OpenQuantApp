from __future__ import annotations

import httpx
import pandas as pd
import pytest

from api.sosovalue import SoSoValueClient, SoSoValueError


class FakeResponse:
    def __init__(self, payload, status_code: int = 200) -> None:
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            request = httpx.Request("POST", "https://example.test")
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

    def post(self, url: str, **kwargs):
        self.calls.append((url, kwargs))
        return self.response


def test_history_request_and_normalization():
    fake = FakeClient(
        FakeResponse(
            {
                "code": 0,
                "data": {
                    "list": [
                        {
                            "date": "2026-08-01",
                            "totalNetInflow": "1200000",
                            "totalValueTraded": 3000000,
                            "totalNetAssets": 5000000,
                            "cumNetInflow": 9000000,
                        },
                        {
                            "date": "2026-07-31",
                            "totalNetInflow": -400000,
                            "totalValueTraded": 2000000,
                            "totalNetAssets": 4500000,
                            "cumNetInflow": 7800000,
                        },
                    ]
                },
            }
        )
    )

    result = SoSoValueClient(
        "secret", http_client=fake
    ).get_historical_inflows()

    assert result.index.tolist() == list(
        pd.to_datetime(["2026-07-31", "2026-08-01"])
    )
    assert result["NetInflowUSD"].tolist() == [-400000, 1200000]
    _, kwargs = fake.calls[0]
    assert kwargs["headers"]["x-soso-api-key"] == "secret"
    assert kwargs["json"] == {"type": "us-btc-spot"}


def test_history_accepts_current_direct_data_list():
    row = {
        "date": "2026-07-31",
        "totalNetInflow": -265372778.16,
        "totalValueTraded": 2670568746.29,
        "totalNetAssets": 76293563503.2954,
        "cumNetInflow": 51324507916.308,
    }
    client = SoSoValueClient(
        "secret",
        http_client=FakeClient(FakeResponse({"code": 0, "data": [row]})),
    )

    result = client.get_historical_inflows()

    assert len(result) == 1
    assert result.index[0] == pd.Timestamp("2026-07-31")
    assert result.iloc[0]["NetInflowUSD"] == pytest.approx(-265372778.16)


def test_rejects_empty_api_key():
    with pytest.raises(ValueError, match="API key"):
        SoSoValueClient("  ")


@pytest.mark.parametrize(
    "payload",
    [
        {"code": 1, "msg": "invalid key"},
        {"code": 0, "data": {}},
        {"code": 0, "data": {"list": [{"date": "2026-08-01"}]}},
    ],
)
def test_rejects_error_or_invalid_schema(payload):
    client = SoSoValueClient(
        "secret", http_client=FakeClient(FakeResponse(payload))
    )

    with pytest.raises(SoSoValueError):
        client.get_historical_inflows()


def test_wraps_http_errors():
    client = SoSoValueClient(
        "secret", http_client=FakeClient(FakeResponse({}, status_code=401))
    )

    with pytest.raises(SoSoValueError, match="请求失败"):
        client.get_historical_inflows()
