import logging
import threading

# from typing import Any, Dict, List, Optional, Tuple
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
            last_row = backtest_data.iloc[-1] if hasattr(backtest_data, 'iloc') else backtest_data
            if isinstance(last_row, (dict,)):
                items = [f"- {k}: {fmt(v)}" for k, v in last_row.items()]
            elif hasattr(last_row, 'index'): # Series
                items = [f"- {col}: {fmt(last_row[col])}" for col in last_row.index]
            else:
                items = [f"Data: {fmt(last_row)}"]
            context_parts.append(
                "#### Backtest Performance:\n" + "\n".join(items)
            )

        # 处理基本面数据 (Financial)
        fin_data = kwargs.get("financial_data")
        if fin_data:
            items = [f"- {k}: {fmt(v)}" for k, v in fin_data.items()] if isinstance(fin_data, dict) else [f"Data: {fmt(fin_data)}"]
            context_parts.append("#### Financial Metrics:\n" + "\n".join(items))

        # 处理宏观数据 (Macro)
        macro_data = kwargs.get("macro_data")
        if macro_data:
            items = [f"- {k}: {fmt(v)}" for k, v in macro_data.items()] if isinstance(macro_data, dict) else [f"Data: {fmt(macro_data)}"]
            context_parts.append("#### Macro Environment:\n" + "\n".join(items))

        # 处理新闻数据 (News)
        news_data = kwargs.get("news_data")
        if news_data is not None and not news_data.empty:
            # 提取最新的几条新闻标题或情感得分
            recent_news = news_data.head(3)
            items = [f"- {row.get('title', 'News')}: {row.get('sentiment', 'N/A')}" for _, row in recent_news.iterrows()]
            context_parts.append("#### Recent News Sentiment:\n" + "\n".join(items))

        return "\n\n".join(context_parts)

    # @st.cache_data(show_spinner="AI 正在分析数据，请稍候...")
    def analyze_symbol(self, symbol: str, **data_kwargs) -> str:
        """增加缓存机制，避免相同数据的重复 API 调用"""
        if not self.llm:
            return "❌ AI 模块未就绪，请检查 API 配置。"

        context = self.build_ai_context(symbol, **data_kwargs)

        # prompt = (
        #     f"作为资深量化分析师，请根据以下数据对 {symbol} 进行深度逻辑推理。\n"
        #     f"要求：结论简洁、分点陈述、指出潜在风险。\n"
        #     f"根据当前 macro 逆风（权重-30%）和强劲财报（权重+50%），计算得出长期看涨概率为 65%。\n"
        #     f"请特别关注：1. 自由现金流是否足以支撑当前股息；2. 技术面 RSI 是否与宏观情绪背离。\n\n"
        #     f"--- DATA ---\n{context}\n\n--- ANALYSIS ---"
        # )
        prompt = (
            f"### 角色设定\n"
            f"你是一名严谨的资深量化策略师，擅长结合历史回测统计与多维实时指标进行决策推演。\n\n"
            f"### 任务目标\n"
            f"基于提供的数据，对 {symbol} 的长期投资价值与短期交易机会进行概率分析。分析必须遵循“证据优先”原则，结论需逻辑闭环。\n\n"
            f"### 核心评估准则 (Evaluation Rubric)\n"
            f"1. **股息安全性**：深度分析自由现金流 (FCF) 与派息比率 (Payout Ratio)，判断当前股息的可持续性及增长潜力。\n"
            f"2. **背离识别**：审视技术面 (如 RSI) 与宏观/基本面是否存在背离（例如：股价因宏观情绪下跌但 RSI 进入超卖区且财报强劲）。\n"
            f"3. **回测对齐**：若当前数据符合高胜率历史模式，请指出；若当前宏观环境异常（如极高利率），需调整历史预测的置信度。\n\n"
            f"### 输入数据 (DATA SNAPSHOT)\n"
            f"{context}\n\n"
            f"### 深度分析要求 (REQUIRED ANALYSIS)\n"
            f"1. **长期投资推理**：结合财报强劲度与宏观压力，给出长期看涨/看跌概率，并说明计算逻辑（参考权重：宏观-30%，财报+50%，股息+20%）。\n"
            f"2. **短期机会评估**：识别技术面入场点，并结合近期新闻触发词给出爆发概率。\n"
            f"3. **压力测试与反向论证**：列出在何种具体条件下（如利率维持高位、FCF骤降等）该看涨逻辑将彻底失效。\n"
            f"4. **置信度评分**：基于数据完整度与历史回测契合度，给出 1-10 分的确定性评分。\n\n"
            f"--- OUTPUT ---"
        )

        return self.complete(prompt)

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
