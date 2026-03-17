import os
import time
from datetime import datetime

import arcticdb as adb
import streamlit as st
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv

from sync_engine import DataSyncEngine

load_dotenv()

DB_PATH = os.getenv("DB_PATH")
LIBRARY_NAME = os.getenv("LIBRARY_NAME")


# ==========================================
# 1. 调度器初始化 (单例模式)
# ==========================================
@st.cache_resource
def get_scheduler():
    # 配置线程池：允许同时有 4 个抓取任务在跑
    executors = {"default": ThreadPoolExecutor(2)}
    scheduler = BackgroundScheduler(executors=executors)
    scheduler.start()
    return scheduler


# ==========================================
# 2. 定义具体的同步任务
# ==========================================
def daily_sync_job():
    engine = DataSyncEngine()
    ac = adb.Arctic(DB_PATH)
    lib = ac.get_library(LIBRARY_NAME)

    for sym in lib.list_symbols():
        # 这里逻辑要保持幂等性：只抓取缺失的数据
        engine.sync_symbol(sym)
        time.sleep(1)
    print(f"[{datetime.now()}] 自动同步任务完成")


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
            st.info(f"下次同步时间: {next_run.strftime('%H:%M:%S')}")


main()
