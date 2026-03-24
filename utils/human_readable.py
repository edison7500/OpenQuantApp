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
