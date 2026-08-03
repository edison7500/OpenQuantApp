from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol

import httpx

FEAR_GREED_URL = "https://api.alternative.me/fng/"


class FearGreedError(RuntimeError):
    """Raised when the Alternative.me index response is unusable."""


class HttpClient(Protocol):
    def get(self, url: str, **kwargs: Any) -> httpx.Response:
        """Send an HTTP GET request."""


@dataclass(frozen=True)
class FearGreedObservation:
    value: int
    classification: str
    observation_date: str
    source: str = "Alternative.me"
    scope: str = "Bitcoin market"


class FearGreedClient:
    """Client for Alternative.me's daily Crypto Fear & Greed Index."""

    def __init__(
        self,
        *,
        timeout: float = 15.0,
        http_client: HttpClient | None = None,
    ) -> None:
        self._timeout = timeout
        self._http_client = http_client or httpx

    def get_latest(self) -> FearGreedObservation:
        try:
            response = self._http_client.get(
                FEAR_GREED_URL,
                params={"limit": 1, "format": "json"},
                timeout=self._timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise FearGreedError(f"贪婪指数请求失败: {exc}") from exc

        metadata = (
            payload.get("metadata") if isinstance(payload, dict) else None
        )
        api_error = (
            metadata.get("error") if isinstance(metadata, dict) else None
        )
        rows = payload.get("data") if isinstance(payload, dict) else None
        if api_error:
            raise FearGreedError(f"Alternative.me 返回错误: {api_error}")
        if not isinstance(rows, list) or not rows:
            raise FearGreedError("Alternative.me 响应缺少 data")

        row = rows[0]
        try:
            value = int(row["value"])
            classification = str(row["value_classification"])
            timestamp = int(row["timestamp"])
        except (KeyError, TypeError, ValueError) as exc:
            raise FearGreedError("Alternative.me 响应字段无效") from exc

        if not 0 <= value <= 100:
            raise FearGreedError(f"贪婪指数超出 0-100 范围: {value}")

        observation_date = (
            datetime.fromtimestamp(timestamp, tz=timezone.utc)
            .date()
            .isoformat()
        )
        return FearGreedObservation(
            value=value,
            classification=classification,
            observation_date=observation_date,
        )
