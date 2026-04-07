from typing import List, Optional

from database import models
from database.news_manager import NewsManager
from database.symbol_manager import SymbolManager


class DatabaseManager(object):
    """
    数据库管理器 - 组合 SymbolManager 和 NewsManager
    为向后兼容保留的薄封装
    """

    def __init__(self, conn=None) -> None:
        self.symbol = SymbolManager(conn)
        self.news = NewsManager(conn)

    def init_db(self):
        """初始化表结构"""
        self.symbol.init_db()
        self.news.init_db()

    # === Symbol 代理方法 (向后兼容) ===

    def get_active_symbols(
        self, asset_type: str = "Equity"
    ) -> Optional[List[str]]:
        """获取活跃的股票代码列表"""
        return self.symbol.get_active_symbols(asset_type)

    def get_symbol_meta(self, symbol) -> Optional[models.SymbolMeta]:
        """获取单个标的元数据"""
        return self.symbol.get_symbol_meta(symbol)

    def get_active_symbolmetas(self) -> Optional[List[models.SymbolMeta]]:
        """获取所有活跃的标的元数据"""
        return self.symbol.get_active_symbolmetas()

    def get_all_symbolmetas(self) -> Optional[List[models.SymbolMeta]]:
        """获取所有标的元数据（包括非活跃）"""
        return self.symbol.get_all_symbolmetas()

    def create_symbol_meta(self, symbol_meta: models.SymbolMeta):
        """创建新的标的元数据记录"""
        self.symbol.create_symbol_meta(symbol_meta)

    def update_symbol_meta(self, symbol_meta: models.SymbolMeta):
        """更新标的元数据记录"""
        self.symbol.update_symbol_meta(symbol_meta)

    def delete_symbol(self, symbol: str):
        """删除指定的标的元数据记录"""
        self.symbol.delete_symbol(symbol)

    # === News 代理方法 (向后兼容) ===

    def save_news(self, news: models.MarketNews):
        """保存新闻"""
        self.news.save_news(news)
