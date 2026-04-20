import streamlit as st
import pandas as pd
from llama_index.core import Document, SummaryIndex
from llama_index.llms.gemini import Gemini
from llama_index.core import Settings
import logging
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


class LLMManager:
    """
    Manages the initialization and access to the Gemini LLM via LlamaIndex.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LLMManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        try:
            # Retrieve API key and model from Streamlit secrets
            api_key = st.secrets["gemini"]["api_key"]
            model_name = st.secrets["gemini"].get(
                "model", "models/gemini-1.5-pro"
            )

            # Initialize Gemini LLM
            self.llm = Gemini(
                api_key=api_key,
                model_name=model_name,
            )

            # Set as global settings for LlamaIndex
            Settings.llm = self.llm

            logger.info(
                f"Gemini LLM ({model_name}) initialized successfully from Streamlit secrets."
            )
        except KeyError:
            logger.error(
                "Gemini API key not found in st.secrets['gemini']['api_key']."
            )
            self.llm = None
        except Exception as e:
            logger.error(f"Failed to initialize Gemini LLM: {e}")
            self.llm = None

        self._initialized = True

    def complete(self, prompt: str, **kwargs) -> str:
        """
        Simple wrapper to complete a prompt.
        """
        if not self.llm:
            return "LLM not initialized. Please check your Streamlit secrets."

        try:
            response = self.llm.complete(prompt, **kwargs)
            return str(response)
        except Exception as e:
            logger.error(f"Error during LLM completion: {e}")
            return f"Error occurred while querying LLM: {e}"

    def build_ai_context(
        self,
        symbol: str,
        technical_data: Optional[pd.DataFrame] = None,
        financial_data: Optional[Dict[str, Any]] = None,
        news_data: Optional[pd.DataFrame] = None,
        macro_data: Optional[List[Tuple[str, Any, str, str]]] = None,
    ) -> str:
        """
        Builds a structured context string for LLM analysis based on various data sources.
        """
        context_parts = [f"### Analysis Context for Symbol: {symbol}"]

        # 1. Technical Indicators
        if technical_data is not None and not technical_data.empty:
            last_row = technical_data.iloc[-1]
            tech_info = "#### Technical Indicators (Latest):\n"
            for col in technical_data.columns:
                # Only include numeric or key status columns
                if pd.api.types.is_numeric_dtype(technical_data[col]):
                    tech_info += f"- {col}: {last_row[col]:.4f}\n"
                else:
                    tech_info += f"- {col}: {last_row[col]}\n"
            context_parts.append(tech_info)

        # 2. Financial Metrics
        if financial_data:
            fin_info = "#### Financial Metrics:\n"
            for label, value in financial_data.items():
                fin_info += f"- {label}: {value}\n"
            context_parts.append(fin_info)

        # 3. News Summary
        if news_data is not None and not news_data.empty:
            news_info = "#### Recent News Highlights:\n"
            # Take top 5 most recent news items
            for _, row in news_data.head(5).iterrows():
                news_info += (
                    f"- [{row['sentiment_label']}] {row['headline']} "
                    f"({row['datetime'].strftime('%Y-%m-%d')})\n"
                )
            context_parts.append(news_info)

        # 4. Macro Data
        if macro_data:
            macro_info = "#### Macroeconomic Environment:\n"
            for label, value, unit, icon in macro_data:
                macro_info += f"- {label}: {value:.2f}{unit}\n"
            context_parts.append(macro_info)

        if len(context_parts) == 1:
            return f"No analysis data available for {symbol}."

        return "\n\n".join(context_parts)

    def analyze_symbol(
        self,
        symbol: str,
        technical_data: Optional[pd.DataFrame] = None,
        financial_data: Optional[Dict[str, Any]] = None,
        news_data: Optional[pd.DataFrame] = None,
        macro_data: Optional[List[Tuple[str, Any, str, str]]] = None,
    ) -> str:
        """
        Performs high-level quantitative reasoning based on provided data.
        """
        context = self.build_ai_context(
            symbol, technical_data, financial_data, news_data, macro_data
        )

        system_prompt = (
            "作为资深量化分析师，请结合财务、新闻和宏观数据，"
            "对该标的给出简短的逻辑推理结论。"
        )

        full_prompt = f"{system_prompt}\n\n{context}"
        return self.complete(full_prompt)


# Singleton instance
llm_manager = LLMManager()
