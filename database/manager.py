from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

from sqlmodel import SQLModel
from database.models import MarketNews


class DatabaseManager(object):
    def __init__(self, db_url="sqlite+aiosqlite:///./quant_data.db"):
        self.engine = create_async_engine(db_url, echo=False)
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def init_db(self):
        """初始化表结构"""
        async with self.engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)

    async def save_news(self, news: MarketNews):
        """异步保存新闻"""
        async with self.async_session() as session:
            session.add(news)
            await session.commit()

    async def get_active_symbols(self) -> List[str]:
        """获取需要同步的股票列表"""
        # 使用 SQLModel 的 select 语法...
        pass
