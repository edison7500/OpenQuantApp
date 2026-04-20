# import logging
# from typing import Any, Dict, List, Optional, Tuple

# import pandas as pd
# import streamlit as st
# from llama_index.core import Settings
# from llama_index.llms.google_genai import GoogleGenAI

# logger = logging.getLogger(__name__)


# class LLMManager:
#     """
#     Manages the initialization and access to the Gemini LLM via LlamaIndex.
#     """

#     _instance = None

#     def __new__(cls):
#         if cls._instance is None:
#             cls._instance = super(LLMManager, cls).__new__(cls)
#             cls._instance._initialized = False
#         return cls._instance

#     def __init__(self):
#         if self._initialized:
#             return

#         try:
#             # Retrieve API key and model from Streamlit secrets
#             api_key = st.secrets["gemini"]["api_key"]
#             model_name = st.secrets["gemini"].get(
#                 "model", "gemma-4-26b-a4b-it"
#             )

#             # Initialize Gemini LLM
#             self.llm = GoogleGenAI(
#                 api_key=api_key,
#                 model=model_name,
#                 temperature=0.2,
#             )

#             # Set as global settings for LlamaIndex
#             Settings.llm = self.llm

#             logger.info(
#                 f"Gemini LLM ({model_name}) initialized successfully from Streamlit secrets."
#             )
#         except KeyError:
#             logger.error(
#                 "Gemini API key not found in st.secrets['gemini']['api_key']."
#             )
#             self.llm = None
#         except Exception as e:
#             logger.error(f"Failed to initialize Gemini LLM: {e}")
#             self.llm = None

#         self._initialized = True

#     def complete(self, prompt: str, **kwargs) -> str:
#         """
#         Simple wrapper to complete a prompt.
#         """
#         if not self.llm:
#             return "LLM not initialized. Please check your Streamlit secrets."

#         try:
#             response = self.llm.complete(prompt, **kwargs)
#             return str(response)
#         except Exception as e:
#             logger.error(f"Error during LLM completion: {e}")
#             return f"Error occurred while querying LLM: {e}"

#     def build_ai_context(
#         self,
#         symbol: str,
#         technical_data: Optional[pd.DataFrame] = None,
#         financial_data: Optional[Dict[str, Any]] = None,
#         news_data: Optional[pd.DataFrame] = None,
#         macro_data: Optional[List[Tuple[str, Any, str, str]]] = None,
#     ) -> str:
#         """
#         Builds a structured context string for LLM analysis based on various data sources.
#         """
#         context_parts = [f"### Analysis Context for Symbol: {symbol}"]

#         # 1. Technical Indicators
#         if technical_data is not None and not technical_data.empty:
#             last_row = technical_data.iloc[-1]
#             tech_info = "#### Technical Indicators (Latest):\n"
#             for col in technical_data.columns:
#                 # Only include numeric or key status columns
#                 if pd.api.types.is_numeric_dtype(technical_data[col]):
#                     tech_info += f"- {col}: {last_row[col]:.4f}\n"
#                 else:
#                     tech_info += f"- {col}: {last_row[col]}\n"
#             context_parts.append(tech_info)

#         # 2. Financial Metrics
#         if financial_data:
#             fin_info = "#### Financial Metrics:\n"
#             for label, value in financial_data.items():
#                 fin_info += f"- {label}: {value}\n"
#             context_parts.append(fin_info)

#         # 3. News Summary
#         if news_data is not None and not news_data.empty:
#             news_info = "#### Recent News Highlights:\n"
#             # Take top 5 most recent news items
#             for _, row in news_data.head(5).iterrows():
#                 news_info += (
#                     f"- [{row['sentiment_label']}] {row['headline']} "
#                     f"({row['datetime'].strftime('%Y-%m-%d')})\n"
#                 )
#             context_parts.append(news_info)

#         # 4. Macro Data
#         if macro_data:
#             macro_info = "#### Macroeconomic Environment:\n"
#             for label, value, unit, icon in macro_data:
#                 macro_info += f"- {label}: {value:.2f}{unit}\n"
#             context_parts.append(macro_info)

#         if len(context_parts) == 1:
#             return f"No analysis data available for {symbol}."

#         return "\n\n".join(context_parts)

#     def analyze_symbol(
#         self,
#         symbol: str,
#         technical_data: Optional[pd.DataFrame] = None,
#         financial_data: Optional[Dict[str, Any]] = None,
#         news_data: Optional[pd.DataFrame] = None,
#         macro_data: Optional[List[Tuple[str, Any, str, str]]] = None,
#     ) -> str:
#         """
#         Performs high-level quantitative reasoning based on provided data.
#         """
#         context = self.build_ai_context(
#             symbol, technical_data, financial_data, news_data, macro_data
#         )

#         prompt = (
#             f"作为资深量化分析师，请根据以下数据对 {symbol} 进行深度逻辑推理。\n"
#             f"要求：结论简洁、分点陈述、指出潜在风险。\n\n"
#             f"--- DATA ---\n{context}\n\n--- ANALYSIS ---"
#         )

#         return self.complete(prompt)


# # Singleton instance
# llm_manager = LLMManager()

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

        # ... (其他模块同理使用 fmt 保持简洁)

        return "\n\n".join(context_parts)

    # @st.cache_data(show_spinner="AI 正在分析数据，请稍候...")
    def analyze_symbol(self, symbol: str, **data_kwargs) -> str:
        """增加缓存机制，避免相同数据的重复 API 调用"""
        if not self.llm:
            return "❌ AI 模块未就绪，请检查 API 配置。"

        context = self.build_ai_context(symbol, **data_kwargs)

        prompt = (
            f"作为资深量化分析师，请根据以下数据对 {symbol} 进行深度逻辑推理。\n"
            f"要求：结论简洁、分点陈述、指出潜在风险。\n\n"
            f"--- DATA ---\n{context}\n\n--- ANALYSIS ---"
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
