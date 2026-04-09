import streamlit as st
from sqlmodel import Session, SQLModel

from database import models


class NewsManager(object):
    """MarketNews 模型的管理器"""

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
        """保存新闻"""
        with self.session as session:
            session.add(news)
            session.commit()
