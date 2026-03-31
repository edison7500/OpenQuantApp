# 核心配置文件
FINANCIAL_CONFIG = {
    "CURRENCIES": {
        "USD": {"symbol": "$", "unit": "USD", "precision": 2},
        "JPY": {"symbol": "¥", "unit": "JPY", "precision": 0},
        "CNY": {"symbol": "¥", "unit": "CNY", "precision": 2},
        "EUR": {"symbol": "€", "unit": "EUR", "precision": 2},
        "GBP": {"symbol": "£", "unit": "GBP", "precision": 2},
        "GBp": {
            "symbol": "p",
            "unit": "GBp",
            "divisor": 100,
            "precision": 2,
        },  # 特殊处理：英分
    },
    "INDICES": {
        "DEFAULT": {
            "symbol": "pts",
            "unit": "Index",
            "precision": 2,
        },  # 指数通常显示为“点”
        "SPECIAL_CASES": {
            "^N225": {"precision": 0},  # 日经 225：0 位
            "^DJI": {"precision": 0},  # 道琼斯：通常也看整数
            "^IXIC": {"precision": 2},  # 纳斯达克：通常保留 2 位
        },
    },
}
