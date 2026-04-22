import logging
import threading

# import pandas as pd
import streamlit as st
from llama_index.core import Settings
from llama_index.llms.google_genai import GoogleGenAI

logger = logging.getLogger(__name__)


class LLMManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(LLMManager, cls).__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialize_llm()
        self._initialized = True

    def _initialize_llm(self):
        try:
            # 优先从 secrets 读取，增加默认值保护
            gemini_config = st.secrets.get("gemini", {})
            api_key = gemini_config.get("api_key")
            model_name = gemini_config.get(
                "model", "gemma-4-26b-a4b-it"
            )  # 建议使用最新模型名称

            if not api_key:
                raise ValueError("Gemini API key is missing in secrets.")

            self.llm = GoogleGenAI(
                api_key=api_key,
                model=model_name,
                temperature=0.2,  # 量化分析建议更低的随机性
            )
            Settings.llm = self.llm
            logger.info(f"Gemini LLM ({model_name}) initialized.")
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            self.llm = None

    # def get_vbt_analysis(self, technical_data) -> dict:
    #     """利用 vectorbt 分析资产的风险指标"""
    #     try:
    #         import vectorbt as vbt

    #         if technical_data is None or technical_data.empty:
    #             return {}

    #         # 确保有 close 列
    #         if "close" not in technical_data.columns:
    #             logger.warning(
    #                 "technical_data does not contain 'close' column for VBT analysis"
    #             )
    #             return {}

    #         close = technical_data["close"]
    #         # 简单的持有策略用于分析资产本身的风险属性
    #         pf = vbt.Portfolio.from_holdings(close)
    #         stats = pf.stats()

    #         return {
    #             "Max Drawdown [%]": stats.get("Max Drawdown [%]"),
    #             "Sharpe Ratio": stats.get("Sharpe Ratio"),
    #             "Calmar Ratio": stats.get("Calmar Ratio"),
    #             "Total Return [%]": stats.get("Total Return [%]"),
    #             "Win Rate [%]": stats.get("Win Rate [%]"),
    #             "Volatility [%]": stats.get("Annualized Volatility [%]"),
    #         }
    #     except Exception as e:
    #         logger.error(f"VBT Analysis Error: {e}")
    #         return {}
    def get_vbt_analysis(self, technical_data) -> dict:
        """利用 vectorbt 深入剖析资产风险（CRO 专用版）"""
        try:
            import vectorbt as vbt

            if (
                technical_data is None
                or technical_data.empty
                or "close" not in technical_data.columns
            ):
                return {}

            close = technical_data["close"]

            # 使用 Benchmark 模式（买入持有）评估资产原始风险
            pf = vbt.Portfolio.from_holdings(close, init_cash=10000)
            stats = pf.stats()

            # 提取对 CRO 决策最关键的量化维度
            return {
                "Max Drawdown [%]": stats.get("Max Drawdown [%]"),
                "Max Drawdown Duration": str(
                    stats.get("Max Drawdown Duration")
                ),  # 转换成字符串方便 LLM 理解
                "Sharpe Ratio": stats.get("Sharpe Ratio"),
                "Sortino Ratio": stats.get(
                    "Sortino Ratio"
                ),  # 专门衡量下行风险
                "Calmar Ratio": stats.get("Calmar Ratio"),  # 收益/回撤比
                "Annualized Return [%]": stats.get("Annualized Return [%]"),
                "Annualized Volatility [%]": stats.get(
                    "Annualized Volatility [%]"
                ),
                "Expectancy": stats.get(
                    "Expectancy"
                ),  # 期望收益，判断这是否是一场‘赢面’更大的博弈
            }
        except Exception as e:
            logger.error(f"VBT Analysis Error: {e}")
            return {}

    def build_ai_context(self, symbol: str, **kwargs) -> str:
        """优化后的上下文构建，增加了对数值的格式化处理"""
        context_parts = [f"### Analysis Context for {symbol}"]

        # 定义一个简单的格式化助手
        def fmt(val):
            if isinstance(val, (int, float)):
                return f"{val:,.2f}"
            return str(val)

        # 处理各部分数据 (示例：Technical)
        tech_data = kwargs.get("technical_data")
        if tech_data is not None and not tech_data.empty:
            last_row = tech_data.iloc[-1]
            items = [
                f"- {col}: {fmt(last_row[col])}" for col in tech_data.columns
            ]
            context_parts.append(
                "#### Technical Indicators:\n" + "\n".join(items)
            )

        # 处理回测数据 (Backtest)
        backtest_data = kwargs.get("backtest_data")
        if backtest_data is not None and not backtest_data.empty:
            # 回测数据通常是汇总指标，取最后一行或整体
            last_row = (
                backtest_data.iloc[-1]
                if hasattr(backtest_data, "iloc")
                else backtest_data
            )
            if isinstance(last_row, (dict,)):
                items = [f"- {k}: {fmt(v)}" for k, v in last_row.items()]
            elif hasattr(last_row, "index"):  # Series
                items = [
                    f"- {col}: {fmt(last_row[col])}" for col in last_row.index
                ]
            else:
                items = [f"Data: {fmt(last_row)}"]
            context_parts.append(
                "#### Backtest Performance:\n" + "\n".join(items)
            )

        # 处理量化风险分析 (VBT)
        vbt_data = kwargs.get("vbt_analysis")
        if vbt_data:
            items = [f"- {k}: {fmt(v)}" for k, v in vbt_data.items()]
            context_parts.append(
                "#### VectorBT Risk Analysis:\n" + "\n".join(items)
            )

        # 处理基本面数据 (Financial)
        fin_data = kwargs.get("financial_data")
        if fin_data:
            items = (
                [f"- {k}: {fmt(v)}" for k, v in fin_data.items()]
                if isinstance(fin_data, dict)
                else [f"Data: {fmt(fin_data)}"]
            )
            context_parts.append(
                "#### Financial Metrics:\n" + "\n".join(items)
            )

        # 处理宏观数据 (Macro)
        macro_data = kwargs.get("macro_data")
        if macro_data:
            items = (
                [f"- {k}: {fmt(v)}" for k, v in macro_data.items()]
                if isinstance(macro_data, dict)
                else [f"Data: {fmt(macro_data)}"]
            )
            context_parts.append(
                "#### Macro Environment:\n" + "\n".join(items)
            )

        # 处理新闻数据 (News)
        news_data = kwargs.get("news_data")
        if news_data is not None and not news_data.empty:
            # 提取最新的几条新闻标题或情感得分
            recent_news = news_data.head(3)
            items = [
                f"- {row.get('title', 'News')}: {row.get('sentiment', 'N/A')}"
                for _, row in recent_news.iterrows()
            ]
            context_parts.append(
                "#### Recent News Sentiment:\n" + "\n".join(items)
            )

        return "\n\n".join(context_parts)

    # @st.cache_data(show_spinner="AI 正在分析数据，请稍候...")
    def analyze_symbol(self, symbol: str, **data_kwargs):
        """增加缓存机制，避免相同数据的重复 API 调用"""
        if not self.llm:
            return "❌ AI 模块未就绪，请检查 API 配置。"

        # 集成 VectorBT 风险分析
        tech_data = data_kwargs.get("technical_data")
        vbt_analysis = self.get_vbt_analysis(tech_data)
        data_kwargs["vbt_analysis"] = vbt_analysis

        context = self.build_ai_context(symbol, **data_kwargs)
        prompt = (
            f"### 角色设定\n"
            f"你现在是该资产的【首席风险官 (CRO)】。你拥有极度审慎的思维，拒绝乐观主义。你的格言是：'利润会照顾好自己，我的工作是管理亏损。'\n\n"  # 强化性格特征
            f"### 任务目标\n"
            f"基于 VectorBT 的量化回测报告，对 {symbol} 进行生存能力压力测试。请穿透数据，寻找隐藏在年化收益背后的‘归零风险’。\n\n"
            f"### CRO 核心评估逻辑\n"
            f"1. **回撤质量 (DD Quality)**：分析 VBT 中的 Max Drawdown。不要只看百分比，要结合 **Max Drawdown Duration (回撤持续时长)**。长期无法回补的回撤比深度回撤更具毁灭性。\n"  # 增加时长维度
            f"2. **收益的‘毒性’评估**：审视 Sharpe。如果波动率（Volatility）极高而 Sharpe 仅在 1 左右，判定为‘低质量收益’。重点查看 **Calmar 比率**，若 < 1.0，视为潜在风险过载。\n"
            f"3. **肥尾效应 (Fat-tail Risk)**：在 VBT 数据中寻找极端负收益分布。在极端 1% 的情况下，该资产是否具有破产属性？\n"
            f"4. **基本面与量化的‘背离’**：对比 context 中的现金流(FCF)与价格波动。是否存在‘财务虚弱但价格虚高’的背离？\n\n"
            f"### 输入数据 (VECTORBT & FUNDAMENTALS)\n"
            f"{context}\n\n"
            f"### CRO 深度报告要求 (严格按以下结构输出)\n"
            f"1. **【风险定性】**：量化风险等级（低/中/高/极高），必须引用至少 3 个 VBT 核心指标作为证据。\n"
            f"2. **【最差情景模拟】**：若发生类似 2008 年或 2020 年的流动性枯竭，预测该资产的 **期望最大跌幅** 及 **存活概率**。\n"
            f"3. **【防御性对冲】**：给出具体操作建议。例如：建议设置多少比例的硬性止损？需要何种负相关资产进行对冲？\n"
            f"4. **【CRO 最终判决】**：\n"
            f"   - 判定：[立即撤离 / 减持观望 / 谨慎持有 / 风险可控]\n"
            f"   - 风险警示分：X/10（分数越高代表越可能出现永久性资本损失）。\n"
            f"   - 一句话警告：给投资者最刺耳的一句忠告。\n\n"
            f"--- OUTPUT ---"
        )

        return self.complete(prompt)

    def stream_complete(self, prompt: str, **kwargs):
        try:
            response = self.llm.stream_complete(prompt, **kwargs)
            for token in response:
                yield token
        except Exception as e:
            logger.error(f"LLM Streaming Error: {e}")
            yield f"分析调用失败: {str(e)}"

    def complete(self, prompt: str, **kwargs) -> str:
        try:
            # 使用 stream=False 确保返回完整字符串，或者根据需求改为 stream=True
            response = self.llm.complete(prompt, **kwargs)
            return str(response)
        except Exception as e:
            logger.error(f"LLM Error: {e}")
            return f"分析调用失败: {str(e)}"


# 单例导出
llm_manager = LLMManager()
