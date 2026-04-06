from typing import List, Optional

import streamlit as st
from sqlmodel import Session, SQLModel, select

from database import models


class SymbolManager(object):
    """SymbolMeta 模型的管理器"""

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

    def get_active_symbols(
        self, asset_type: str = "Equity"
    ) -> Optional[List[str]]:
        """获取活跃的股票代码列表"""
        with self.session as session:
            statement = (
                select(models.SymbolMeta.symbol)
                .where(
                    models.SymbolMeta.is_active,
                    models.SymbolMeta.asset_type == asset_type,
                )
                .order_by(models.SymbolMeta.symbol)
            )
            symbols = session.exec(statement).all()

            if not symbols:
                return
            return symbols

    def get_symbol_meta(self, symbol) -> Optional[models.SymbolMeta]:
        """获取单个标的元数据"""
        with self.session as session:
            statement = select(models.SymbolMeta).where(
                models.SymbolMeta.symbol == symbol
            )
            return session.execute(statement).scalars().first()

    def get_active_symbolmetas(self) -> Optional[List[models.SymbolMeta]]:
        """获取所有活跃的标的元数据"""
        with self.session as session:
            statement = select(models.SymbolMeta).where(
                models.SymbolMeta.is_active,
            )
            return session.exec(statement).all()

    def get_all_symbolmetas(self) -> List[models.SymbolMeta]:
        """获取所有标的元数据（包括非活跃）"""
        with self.session as session:
            statement = select(models.SymbolMeta).order_by(
                models.SymbolMeta.symbol
            )
            return session.exec(statement).all()

    def create_symbol_meta(self, symbol_meta: models.SymbolMeta):
        """创建新的标的元数据记录"""
        with self.session as session:
            session.add(symbol_meta)
            session.commit()

    def delete_symbol(self, symbol: str):
        """删除指定的标的元数据记录"""
        with self.session as session:
            obj = session.get(models.SymbolMeta, symbol)
            if obj:
                session.delete(obj)
                session.commit()
