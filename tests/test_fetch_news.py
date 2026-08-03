from datetime import datetime, timezone

from api.fetch_news import NewsEngine


class FakeFinnhubClient:
    def __init__(self, news):
        self.news = news
        self.categories = []

    def general_news(self, category, min_id=0):
        self.categories.append((category, min_id))
        return self.news

    def company_news(self, *args, **kwargs):
        raise AssertionError("crypto news must not use company_news")


def test_crypto_news_uses_category_feed_and_prioritizes_symbol():
    now = int(datetime.now(timezone.utc).timestamp())
    client = FakeFinnhubClient(
        [
            {
                "headline": "Broad digital asset update",
                "summary": "Market overview",
                "datetime": now,
            },
            {
                "headline": "Bitcoin adoption grows",
                "summary": "BTC-related development",
                "datetime": now - 1,
            },
        ]
    )
    engine = object.__new__(NewsEngine)
    engine.client = client
    engine.symbol = "BTC/USDT"
    engine.asset_type = "crypto"

    result = engine.get_raw_news()

    assert client.categories == [("crypto", 0)]
    assert result.iloc[0]["headline"] == "Bitcoin adoption grows"
    assert result.iloc[0]["news_scope"] == "BTC-related"
    assert result.iloc[1]["news_scope"] == "crypto-market"
