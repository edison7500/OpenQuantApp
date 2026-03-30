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


def format_human_readable(num, precision=2):
    """
    将数字转换为易读格式 (K, M, B, T)
    """
    if num is None:
        return "N/A"

    # 处理千万、亿等级别 (符合金融习惯)
    for unit in ["", "K", "M", "B", "T"]:
        if abs(num) < 1000.0:
            return f"{num:.{precision}f}{unit}"
        num /= 1000.0
    return f"{num:.{precision}f}P"


def format_percentage(val):
    """带正负号的百分比"""
    return f"{val:+.2f}%"


def get_display_format(ticker_obj):
    """
    根据 ticker 的 fast_info 自动获取格式化参数
    """
    f_info = ticker_obj.fast_info
    q_type = f_info.get("quoteType", "").upper()
    raw_currency = f_info.get("currency", "USD")

    # 逻辑 1：判断是否为指数
    if q_type == "INDEX":
        return FINANCIAL_CONFIG["INDICES"]["DEFAULT"]
    # 逻辑 2：个股货币映射
    config = FINANCIAL_CONFIG["CURRENCIES"].get(raw_currency)

    # 逻辑 3：兜底逻辑（如果遇到未定义的货币代码，如 HKD）
    if not config:
        config = {"symbol": raw_currency, "unit": raw_currency, "precision": 2}

    return config


def format_value(value, config):
    # 如果数值 > 1000 且它是指数点位，强制改为 0 位精度
    if config.get("unit") == "Index" and value >= 1000:
        precision = 0
    else:
        precision = config.get("precision", 2)

    symbol = config["symbol"]
    if config["unit"] == "Index":
        return f"{value:,.{precision}f} {symbol}"
    else:
        return f"{symbol}{value:,.{precision}f}"
