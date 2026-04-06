from typing import List, Optional

import streamlit as st
from sqlmodel import Session, SQLModel, select

from database import models


class DatabaseManager(object):
    def __init__(self, conn=None) -> None:
        if conn is None:
            _conn = st.connection("quant_db", type="sql")
        else:
            _conn = conn
        self.engine = _conn.engine
        self.session = Session(self.engine)

    def init_db(self):
        """初始化表结构"""
        with self.engine.begin():
            SQLModel.metadata.create_all(self.engine)

    def save_news(self, news: models.MarketNews):
        """异步保存新闻"""
        with self.session() as session:
            session.add(news)
            session.commit()

    def create_symbolmeta(self, symbol: models.SymbolMeta):
        with self.session as session:
            session.add(symbol)
            session.commit()

    def get_active_symbols(
        self, asset_type: str = "Equity"
    ) -> Optional[List[str]]:
        """获取需要同步的股票列表"""
        # 使用 SQLModel 的 select 语法...
        with self.session as session:
            statement = (
                select(models.SymbolMeta.symbol)
                .where(
                    models.SymbolMeta.is_active,
                    models.SymbolMeta.asset_type == asset_type,
                )
                .order_by(models.SymbolMeta.symbol)
            )
            # symbols = session.exec(statement).scalars().all()
            symbols = session.exec(statement).all()

            if not symbols:
                return
            else:
                return symbols

    def get_symbol_meta(self, symbol) -> models.SymbolMeta:
        with self.session as session:
            statement = select(models.SymbolMeta).where(
                models.SymbolMeta.symbol == symbol
            )
            obj: models.SymbolMeta = (
                session.execute(statement).scalars().first()
            )

        return obj

    def get_active_symbolmetas(self) -> Optional[List[models.SymbolMeta]]:
        with self.session as session:
            statement = select(models.SymbolMeta).where(
                models.SymbolMeta.is_active,
            )
            symbolmetas = session.exec(statement).all()

            if symbolmetas:
                return symbolmetas

    def get_all_symbolmetas(self) -> Optional[List[models.SymbolMeta]]:
        """获取所有 SymbolMeta 记录（包括非活跃）"""
        with self.session as session:
            statement = select(models.SymbolMeta).order_by(
                models.SymbolMeta.symbol
            )
            return session.exec(statement).all()

    def create_symbol_meta(self, symbol_meta: models.SymbolMeta):
        """创建新的 SymbolMeta 记录"""
        with self.session as session:
            session.add(symbol_meta)
            session.commit()

    def delete_symbol(self, symbol: str):
        """删除指定的 SymbolMeta 记录"""
        with self.session as session:
            obj = session.get(models.SymbolMeta, symbol)
            if obj:
                session.delete(obj)
                session.commit()
