from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional


class MarketNews(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    symbol: str = Field(index=True)  # 关联股票代码
    timestamp: datetime = Field(index=True)
    title: str
    content: str
    source: str
    sentiment_score: Optional[float] = None  # 预留给 AI 分析
