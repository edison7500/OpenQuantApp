from __future__ import annotations

from typing import Any, Protocol

import httpx
import pandas as pd

SOSOVALUE_BASE_URL = "https://api.sosovalue.xyz"
SOSOVALUE_HISTORY_PATH = "/openapi/v2/etf/historicalInflowChart"


class SoSoValueError(RuntimeError):
    """Raised when SoSoValue cannot return usable ETF flow data."""


class HttpClient(Protocol):
    def post(self, url: str, **kwargs: Any) -> httpx.Response:
        """Send an HTTP POST request."""


class SoSoValueClient:
    """Small client for SoSoValue's US spot-ETF history endpoint."""

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = SOSOVALUE_BASE_URL,
        timeout: float = 15.0,
        http_client: HttpClient | None = None,
    ) -> None:
        if not api_key.strip():
            raise ValueError("SoSoValue API key 不能为空")
        self._api_key = api_key.strip()
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._http_client = http_client or httpx

    def get_historical_inflows(
        self, etf_type: str = "us-btc-spot"
    ) -> pd.DataFrame:
        """Return daily aggregate ETF flows in ascending date order."""
        if etf_type not in {"us-btc-spot", "us-eth-spot"}:
            raise ValueError(f"不支持的 ETF 类型: {etf_type}")

        try:
            response = self._http_client.post(
                f"{self._base_url}{SOSOVALUE_HISTORY_PATH}",
                headers={
                    "x-soso-api-key": self._api_key,
                    "Content-Type": "application/json",
                },
                json={"type": etf_type},
                timeout=self._timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise SoSoValueError(f"SoSoValue 请求失败: {exc}") from exc

        if not isinstance(payload, dict) or payload.get("code") != 0:
            message = payload.get("msg") if isinstance(payload, dict) else None
            raise SoSoValueError(message or "SoSoValue 返回了错误状态")

        data = payload.get("data")
        if isinstance(data, list):
            rows = data
        elif isinstance(data, dict):
            rows = data.get("list")
        else:
            rows = None
        if not isinstance(rows, list):
            raise SoSoValueError("SoSoValue 响应缺少 ETF 历史数据列表")

        frame = pd.DataFrame.from_records(rows)
        source_columns = {
            "date": "Date",
            "totalNetInflow": "NetInflowUSD",
            "totalValueTraded": "ValueTradedUSD",
            "totalNetAssets": "NetAssetsUSD",
            "cumNetInflow": "CumulativeNetInflowUSD",
        }
        if frame.empty:
            return pd.DataFrame(
                columns=list(source_columns.values())[1:]
            ).rename_axis("Date")

        missing = source_columns.keys() - frame.columns
        if missing:
            fields = ", ".join(sorted(missing))
            raise SoSoValueError(f"SoSoValue 响应缺少字段: {fields}")

        frame = frame[list(source_columns)].rename(columns=source_columns)
        frame["Date"] = pd.to_datetime(frame["Date"], errors="coerce")
        value_columns = list(source_columns.values())[1:]
        for column in value_columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")

        frame = frame.dropna(subset=["Date", "NetInflowUSD"])
        return frame.set_index("Date").sort_index()
