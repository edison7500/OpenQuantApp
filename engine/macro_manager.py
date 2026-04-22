from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Tuple

import streamlit as st
from fredapi import Fred

# 1. 增强配置映射，支持不同的计算类型
METRICS_MAP = {
    "实际 GDP": {
        "series_id": "GDPC1",
        "unit": "% QoQ (Annualized)",
        "icon": "🏢",
        "calc": "growth_rate",  # 季度环比年化增长率
    },
    "消费者价格指数 (CPI)": {
        "series_id": "CPIAUCSL",
        "unit": "% YoY",
        "icon": "📊",
        "calc": "yoy",
    },
    "核心 PCE 通胀": {
        "series_id": "PCEPILFE",  # 剔除食品和能源，美联储的核心锚点
        "unit": "% YoY",
        "icon": "🎯",
        "calc": "yoy",
    },
    "生产价格指数 (PPI)": {
        "series_id": "PPIACO",
        "unit": "% YoY",
        "icon": "🏭",
        "calc": "yoy",
    },
    "联邦基金利率": {
        "series_id": "FEDFUNDS",
        "unit": "%",
        "icon": "🏦",
        "calc": "latest",
    },
    # "消费者价格指数 (CPI)": {
    #     "series_id": "CPIAUCSL",
    #     "unit": "% YoY",
    #     "icon": "📊",
    #     "calc": "yoy",
    # },
    "美元指数": {
        "series_id": "DTWEXBGS",
        "unit": "",
        "icon": "💵",
        "calc": "latest",
    },
    "10 年期美债": {
        "series_id": "DGS10",
        "unit": "%",
        "icon": "📈",
        "calc": "latest",
    },
    "VIX 恐慌指数": {
        "series_id": "VIXCLS",
        "unit": "",
        "icon": "😱",
        "calc": "latest",
    },
}


# def _fetch_single_metric(
#     fred: Fred, label: str, config: Dict[str, Any]
# ) -> Tuple[str, float, str, str] | None:
#     """单个指标的获取逻辑，封装逻辑以便并行调用"""
#     series_id = config["series_id"]

#     try:
#         # 如果是 YoY 计算，至少需要 13 个月的数据
#         limit = 13 if config["calc"] == "yoy" else 1

#         # 复用你的重试逻辑（此处简略，建议保留原有的 _fetch_fred_series_with_retry）
#         data = fred.get_series(series_id, limit=limit)

#         if data is None or data.empty:
#             return None

#         if config["calc"] == "yoy" and len(data) >= 13:
#             current = data.iloc[-1]
#             year_ago = data.iloc[-13]
#             value = ((current - year_ago) / year_ago) * 100
#         else:
#             value = data.iloc[-1]

#         return (label, float(value), config["unit"], config["icon"])
#     except Exception as e:
#         # 单个指标失败不影响整体，静默处理或记录日志
#         return None


def _fetch_single_metric(
    fred: Fred, label: str, config: Dict[str, Any]
) -> Tuple[str, float, str, str] | None:
    series_id = config["series_id"]
    calc_type = config["calc"]

    try:
        # 根据计算类型确定获取的数据量
        # YoY 需要 13 个月，季度环比需要至少 2 个季度
        fetch_limit = 13 if calc_type == "yoy" else 5
        data = fred.get_series(series_id, limit=fetch_limit)

        if data is None or data.empty:
            return None

        value = 0.0

        if calc_type == "yoy" and len(data) >= 13:
            # 同比计算：(当前 / 去年同期 - 1) * 100
            current = data.iloc[-1]
            year_ago = data.iloc[-13]
            value = ((current / year_ago) - 1) * 100

        elif calc_type == "growth_rate" and len(data) >= 2:
            # 季度环比年化增长率计算 (常用于 GDP)
            # 公式: ((本季/上季)^4 - 1) * 100
            current = data.iloc[-1]
            prev = data.iloc[-2]
            value = ((pow(current / prev, 4)) - 1) * 100

        else:
            # 默认取最新值
            value = data.iloc[-1]

        return (label, float(value), config["unit"], config["icon"])
    except Exception:
        return None


@st.cache_data(ttl=3600)
def get_macro_metrics() -> List[Tuple[str, float, str, str]]:
    """
    使用线程池并行获取 FRED 宏观经济指标。
    """
    # 1. 预检 Secrets
    if "fred" not in st.secrets or "api_key" not in st.secrets["fred"]:
        st.error("未找到 FRED API Key。请在 .streamlit/secrets.toml 中配置。")
        return []

    try:
        fred = Fred(api_key=st.secrets["fred"]["api_key"])
        results = []

        # 2. 使用线程池并行请求 API
        with ThreadPoolExecutor(max_workers=len(METRICS_MAP)) as executor:
            # 提交所有任务
            future_to_label = {
                executor.submit(
                    _fetch_single_metric, fred, label, config
                ): label
                for label, config in METRICS_MAP.items()
            }

            for future in future_to_label:
                result = future.result()
                if result:
                    results.append(result)

        return results
    except Exception as e:
        st.error(f"获取宏观数据时发生意外错误: {e}")
        return []


# 在 Streamlit UI 中调用的示例
# metrics = get_macro_metrics()
# for label, val, unit, icon in metrics:
#     st.metric(label=f"{icon} {label}", value=f"{val:.2f} {unit}")
