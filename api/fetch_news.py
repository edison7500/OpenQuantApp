from datetime import datetime, timedelta

import finnhub
import pandas as pd
import streamlit as st
from textblob import TextBlob


class NewsEngine(object):
    def __init__(self, symbol: str):
        _api_key = st.secrets["finnhub"]["api_key"]
        assert _api_key is not None
        self.client = finnhub.Client(api_key=_api_key)
        self.symbol = symbol

    def get_raw_news(self) -> pd.DataFrame:

        end = datetime.now()
        start = end - timedelta(days=7)

        news = self.client.company_news(
            self.symbol,
            _from=start.strftime("%Y-%m-%d"),
            to=end.strftime("%Y-%m-%d"),
        )

        if not news:
            return pd.DataFrame()
        df = pd.DataFrame(news)
        df["datetime"] = pd.to_datetime(df["datetime"], unit="s")

        return df.sort_values(by="datetime", ascending=False)


@st.cache_data(ttl=3600)
def get_cached_news(symbol: str):
    return NewsEngine(symbol).company_news()


@st.cache_data(ttl=3600)
def fetch_and_analyze(symbol: str):
    engine = NewsEngine(symbol)
    df = engine.get_raw_news()

    if df.empty:
        return df

    # 执行情感分析 (Polarity: -1 极负, 1 极正)
    def get_sentiment(text):
        analysis = TextBlob(text)
        score = analysis.sentiment.polarity
        if score > 0.1:
            return "Positive 🟢", score
        elif score < -0.1:
            return "Negative 🔴", score
        return "Neutral ⚪", score

    # 应用分析到标题
    df[["sentiment_label", "sentiment_score"]] = df["headline"].apply(
        lambda x: pd.Series(get_sentiment(x))
    )

    df["datetime"] = pd.to_datetime(df["datetime"], unit="s")
    return df.sort_values(by="datetime", ascending=False)


if __name__ == "__main__":
    fetch_client = NewsEngine("AAPL")
    print(fetch_client.company_news())
