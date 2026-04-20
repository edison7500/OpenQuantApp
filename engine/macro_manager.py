import pandas as pd
import streamlit as st
from fredapi import Fred
import time
from typing import List, Tuple

# FRED 系列 ID 映射 - 定义在 engine 层，保持业务逻辑统一
METRICS_MAP = {
    "联邦基金利率": {
        "series_id": "FEDFUNDS",
        "unit": "%",
        "icon": "🏦",
    },
    "通胀率 (CPI)": {
        "series_id": "CPIAUCSL",
        "unit": "% YoY",
        "icon": "📊",
    },
    "美元指数": {
        "series_id": "DTWEXBGS",
        "unit": "",
        "icon": "💵",
    },
    "10 年期美债": {
        "series_id": "DGS10",
        "unit": "%",
        "icon": "📈",
    },
}


def _fetch_fred_series_with_retry(
    fred: Fred, series_id: str, limit: int = 1, max_retries: int = 3
) -> pd.Series | None:
    """从 FRED 获取数据，带重试机制"""
    for attempt in range(max_retries):
        try:
            data = fred.get_series(series_id, limit=limit)
            if not data.empty:
                return data
            return None
        except Exception:
            if attempt == max_retries - 1:
                raise
            time.sleep(0.5 * (attempt + 1))
    return None


@st.cache_data(ttl=3600)  # 缓存 1 小时，宏观数据更新频率低
def get_macro_metrics() -> List[Tuple[str, float, str, str]]:
    """
    获取并处理 FRED 宏观经济指标。
    返回列表: [(label, value, unit, icon), ...]
    """
    try:
        api_key = st.secrets["fred"]["api_key"]
        fred = Fred(api_key=api_key)
        display_data = []

        for label, config in METRICS_MAP.items():
            series_id = config["series_id"]
            data = _fetch_fred_series_with_retry(fred, series_id, limit=1)

            if data is not None:
                value = data.iloc[-1]

                # CPI 特殊处理: 计算同比变化 (YoY)
                if series_id == "CPIAUCSL":
                    cpi_data = _fetch_fred_series_with_retry(
                        fred, series_id, limit=13
                    )
                    if cpi_data is not None and len(cpi_data) >= 13:
                        current = cpi_data.iloc[-1]
                        year_ago = cpi_data.iloc[-13]
                        value = ((current - year_ago) / year_ago) * 100

                display_data.append(
                    (
                        label,
                        float(value),
                        config["unit"],
                        config["icon"],
                    )
                )
        return display_data
    except Exception:
        # 在 engine 层记录错误，但为了不中断 UI，返回空列表
        # 可以根据需要使用 logging
        return []
