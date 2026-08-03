from datetime import datetime, timedelta, timezone

import finnhub
import pandas as pd
import streamlit as st
from textblob import TextBlob


class NewsEngine(object):
    _CRYPTO_NAMES = {
        "BTC": "bitcoin",
        "ETH": "ethereum",
        "SOL": "solana",
        "BNB": "binance coin",
        "XRP": "ripple",
        "DOGE": "dogecoin",
        "ADA": "cardano",
    }

    def __init__(self, symbol: str, asset_type: str = "equity"):
        _api_key = st.secrets["finnhub"]["api_key"]
        assert _api_key is not None
        self.client = finnhub.Client(api_key=_api_key)
        self.symbol = symbol
        self.asset_type = asset_type.lower()

    def _prioritize_crypto_symbol(self, df: pd.DataFrame) -> pd.DataFrame:
        """Put symbol-related stories first without hiding market-wide news."""
        base = self.symbol.split("/")[0].split(":")[-1].upper()
        terms = {base.lower()}
        if name := self._CRYPTO_NAMES.get(base):
            terms.add(name)

        searchable = pd.Series("", index=df.index, dtype="object")
        for column in ("headline", "summary", "related"):
            if column in df:
                searchable = searchable.str.cat(
                    df[column].fillna("").astype(str), sep=" "
                )
        pattern = "|".join(map(lambda term: rf"\b{term}\b", terms))
        is_relevant = searchable.str.contains(
            pattern, case=False, regex=True, na=False
        )
        df = df.copy()
        df["news_scope"] = is_relevant.map(
            {True: f"{base}-related", False: "crypto-market"}
        )
        return (
            df.assign(_relevant=is_relevant)
            .sort_values(["_relevant", "datetime"], ascending=[False, False])
            .drop(columns="_relevant")
        )

    def get_raw_news(self) -> pd.DataFrame:
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=7)

        if self.asset_type == "crypto":
            # Finnhub exposes category-level crypto news, not a guaranteed
            # pair-specific equivalent of company_news.
            news = self.client.general_news("crypto", min_id=0)
        else:
            news = self.client.company_news(
                self.symbol,
                _from=start.strftime("%Y-%m-%d"),
                to=end.strftime("%Y-%m-%d"),
            )

        if not news:
            return pd.DataFrame()
        df = pd.DataFrame(news)
        df["datetime"] = pd.to_datetime(
            df["datetime"], unit="s", utc=True, errors="coerce"
        )
        df = df.loc[df["datetime"].between(start, end)].copy()

        if self.asset_type == "crypto" and not df.empty:
            return self._prioritize_crypto_symbol(df)

        return df.sort_values(by="datetime", ascending=False)


@st.cache_data(ttl=3600)
def get_cached_news(symbol: str):
    return NewsEngine(symbol).company_news()


@st.cache_data(ttl=3600)
def fetch_and_analyze(symbol: str, asset_type: str = "equity"):
    engine = NewsEngine(symbol, asset_type=asset_type)
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

    if asset_type.lower() == "crypto":
        return df
    return df.sort_values(by="datetime", ascending=False)


if __name__ == "__main__":
    fetch_client = NewsEngine("AAPL")
    print(fetch_client.company_news())
