import os
import time
import logging
from datetime import datetime
from pathlib import Path

import streamlit as st
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv

from database.connections.arcticdb_conn import ArcticDBConnection
from database.resource import get_symbols
from notifier.tg import TelegramNotifier
from sync_engine import DataSyncEngine

load_dotenv()

# 配置日志
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / f"cron_{datetime.now().strftime('%Y%m')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("quant-cron")

# DB_PATH = os.getenv("DB_PATH")
LIBRARY_NAME = os.getenv("LIBRARY_NAME")


# ==========================================
# 1. 调度器初始化 (单例模式)
# ==========================================
@st.cache_resource
def get_scheduler():
    # 配置线程池：允许同时有 2 个抓取任务在跑
    executors = {"default": ThreadPoolExecutor(2)}
    scheduler = BackgroundScheduler(executors=executors)
    scheduler.start()
    return scheduler


# ==========================================
# 2. 定义具体的同步任务
# ==========================================
def daily_sync_job():
    logger.info("开始执行每日自动同步任务")
    engine = DataSyncEngine()
    symbols = get_symbols()
    logger.info(f"待同步标的数量：{len(symbols)}")

    success_count = 0
    for sym in symbols:
        try:
            logger.info(f"正在同步：{sym}")
            engine.sync_symbol(sym)
            success_count += 1
        except Exception as e:
            logger.error(f"同步失败 {sym}: {e}")
        time.sleep(1)

    logger.info(f"自动同步任务完成 - 成功：{success_count}/{len(symbols)}")


def daily_sync_and_scan_job():
    logger.info("开始执行每日同步 + 扫描任务")
    engine = DataSyncEngine()
    # 1. 先同步数据到 ArcticDB
    ac = st.connection("arcticdb", type=ArcticDBConnection)
    lib = ac.get_library()

    symbols = lib.list_symbols()
    logger.info(f"待扫描标的数量：{len(symbols)}")

    for sym in symbols:
        try:
            # 这里逻辑要保持幂等性：只抓取缺失的数据
            logger.info(f"正在同步：{sym}")
            engine.sync_symbol(sym)

            # 2. 从数据库读取最新数据进行扫描
            df = engine.ac.get_library(f"{LIBRARY_NAME}.min60").read(sym).data
            df.ta.rsi(append=True)  # type: ignore

            current_rsi = df["RSI_14"].iloc[-1]
            last_price = df["Close"].iloc[-1]

            # 3. 触发逻辑判断
            if current_rsi < 30:
                logger.info(f"触发 RSI 超卖信号：{sym} (RSI={current_rsi:.2f})")
                notifier = TelegramNotifier(
                    st.secrets["telegram"]["token"],
                    st.secrets["telegram"]["chat_id"],
                )
                msg = (
                    f"🚨 *RSI 超卖预警*\n"
                    f"标的：`{sym}`\n"
                    f"当前价格：`{last_price}`\n"
                    f"RSI 数值：`{current_rsi:.2f}`\n"
                    f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}"
                )
                notifier.notify(msg)
        except Exception as e:
            logger.error(f"扫描失败 {sym}: {e}")

        time.sleep(1)

    logger.info("自动同步 + 扫描任务完成")


# ==========================================
# 3. Streamlit UI 控制界面
# ==========================================
def main():
    st.set_page_config(page_title="Quant Cron", layout="wide")
    st.title("🛰️ 自动化行情同步系统")

    scheduler = get_scheduler()

    with st.sidebar:
        st.subheader("后台任务状态")

        # 检查任务是否已存在，防止重复添加
        job_id = "daily_market_sync"
        is_running = scheduler.get_job(job_id) is not None

        if not is_running:
            if st.button("开启自动同步 (每 5 分钟)"):
                scheduler.add_job(
                    daily_sync_job,
                    # daily_sync_and_scan_job,
                    "interval",
                    minutes=5,
                    id=job_id,
                    replace_existing=True,
                )
                st.success("定时同步已启动")
                st.rerun()
        else:
            if st.button("🛑 停止自动同步"):
                scheduler.remove_job(job_id)
                st.warning("定时同步已停止")
                st.rerun()

        # 显示下次运行时间
        if is_running:
            next_run = scheduler.get_job(job_id).next_run_time
            st.info(f"下次同步时间：{next_run.strftime('%H:%M:%S')}")

        if st.button("🔔 测试 Telegram 推送"):
            notifier = TelegramNotifier(
                st.secrets["telegram"]["token"],
                st.secrets["telegram"]["chat_id"],
            )
            r = notifier.notify("✅ 这是一个来自量化 Dashboard 的测试信号")
            if r:
                st.success("推送成功！请检查手机。")
            else:
                st.error("推送失败，请检查 Token 或网络。")

    # 主视觉区域：任务日志
    st.divider()
    st.subheader("📋 任务日志")

    if LOG_FILE.exists():
        with open(LOG_FILE, "r") as f:
            logs = f.read()
        st.code(logs, language="text")
    else:
        st.info("暂无日志记录")


main()
