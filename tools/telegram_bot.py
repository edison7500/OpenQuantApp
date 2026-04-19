import logging
from datetime import datetime

import streamlit as st

from database.connections.arcticdb_conn import ArcticDBConnection
from notifier.tg import TelegramNotifier
from sync_engine import DataSyncEngine

logger = logging.getLogger("quant-cron")


def main():
    st.set_page_config(page_title="Telegram 通知机器人", layout="wide")
    st.title("🔔 Telegram 通知机器人")

    with st.sidebar:
        st.subheader("通知设置")

        # 测试推送
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

        st.divider()

        # RSI 扫描任务控制
        st.subheader("RSI 扫描任务")
        job_id = "rsi_scan_job"
        scheduler = st.session_state.get("scheduler")

        if scheduler:
            is_running = scheduler.get_job(job_id) is not None

            if not is_running:
                if st.button("开启 RSI 扫描 (每 5 分钟)"):
                    from tools.cron import daily_sync_and_scan_job

                    scheduler.add_job(
                        daily_sync_and_scan_job,
                        "interval",
                        minutes=5,
                        id=job_id,
                        replace_existing=True,
                    )
                    st.success("RSI 扫描已启动")
                    st.rerun()
            else:
                if st.button("🛑 停止 RSI 扫描"):
                    scheduler.remove_job(job_id)
                    st.warning("RSI 扫描已停止")
                    st.rerun()

            if is_running:
                next_run = scheduler.get_job(job_id).next_run_time
                st.info(f"下次扫描时间：{next_run.strftime('%H:%M:%S')}")

    # 主视觉区域：通知说明
    st.markdown("""
    ### 功能说明

    **Telegram 通知机器人** 负责监控市场机会并发送实时预警。

    #### 当前支持的预警类型：
    - 🚨 **RSI 超卖预警**: 当标的 RSI_14 < 30 时触发
    - 📊 **RSI 超买预警**: 当标的 RSI_14 > 70 时触发（待实现）
    - 💥 **爆量突破预警**: 当成交量异常放大时触发（待实现）

    #### 工作流程：
    1. 从 ArcticDB 读取最新行情数据
    2. 计算 RSI 等技术指标
    3. 检测触发条件
    4. 通过 Telegram Bot 发送预警消息
    """)

    st.divider()
    st.subheader("📋 通知日志")

    # 显示最近的预警记录（可以从日志文件过滤）
    LOG_DIR = st.session_state.get("log_dir")
    if LOG_DIR:
        import os
        log_file = LOG_DIR / f"cron_{datetime.now().strftime('%Y%m')}.log"
        if log_file.exists():
            with open(log_file, "r") as f:
                all_logs = f.read()
            # 过滤出 RSI 相关的日志
            rsi_logs = "\n".join(
                line for line in all_logs.split("\n") if "RSI" in line or "超卖" in line or "超买" in line
            )
            if rsi_logs.strip():
                st.code(rsi_logs, language="text")
            else:
                st.info("暂无 RSI 预警记录")
        else:
            st.info("暂无日志记录")
    else:
        st.info("日志目录未配置")


if __name__ == "__main__":
    main()
