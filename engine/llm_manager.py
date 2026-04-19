import streamlit as st
from llama_index.llms.gemini import Gemini
from llama_index.core import Settings
import logging

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
            # Retrieve API key from Streamlit secrets
            api_key = st.secrets["gemini"]["api_key"]

            # Initialize Gemini LLM
            self.llm = Gemini(
                api_key=api_key,
                model_name="models/gemini-1.5-pro",
            )

            # Set as global settings for LlamaIndex
            Settings.llm = self.llm

            logger.info(
                "Gemini LLM initialized successfully from Streamlit secrets."
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


# Singleton instance
llm_manager = LLMManager()
