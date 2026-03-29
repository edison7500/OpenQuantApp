from datetime import datetime
from typing import List, Optional

from sqlmodel import Field, Relationship, SQLModel


# --- 1. 标的元数据模型 ---
class SymbolMeta(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}

    symbol: str = Field(primary_key=True, index=True)
    name: str
    asset_type: str = Field(default="Equity")  # Equity, crypto, index
    sector: Optional[str] = None  # 板块
    industry: Optional[str] = None  # 行业
    exchange: Optional[str] = None  # 交易所
    is_active: bool = Field(default=True)
    currency: Optional[str] = None
    updated_at: datetime = Field(default_factory=datetime.now)


# --- 2. 市场新闻与向量模型 ---
class MarketNews(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    symbol: str = Field(index=True, foreign_key="symbolmeta.symbol")
    timestamp: datetime = Field(index=True)
    title: str
    content: str
    source: str
    url: Optional[str] = None

    # 预留给 AI/Vector 的字段
    sentiment_score: Optional[float] = None  # 情感得分 (-1 到 1)
    # 存储向量数据，通常使用 BLOB 存储 Numpy 数组序列化后的数据
    # 后续配合 sqlite-vss 插件使用
    vector_embedding: Optional[bytes] = Field(
        default=None, description="Vector embedding for semantic search"
    )


# --- 3. 任务执行日志 ---
class SyncTaskLog(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    task_name: str = Field(index=True)  # 如 "arctic_ohlcv_sync"
    status: str  # success, failed
    last_run: datetime = Field(default_factory=datetime.now)
    message: Optional[str] = None  # 错误信息或统计
