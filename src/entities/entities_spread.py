from dataclasses import dataclass


@dataclass
class TokenPrice:
    """Class to store token price information"""
    exchange: str
    symbol: str
    price: float
    timestamp: float

    def __str__(self):
        return f"{self.exchange} {self.symbol}: {self.price}"


@dataclass
class SpreadOpportunity:
    """Class to store spread opportunity information"""
    base_token: str
    buy_exchange: str
    buy_price: float
    sell_exchange: str
    sell_price: float
    spread_percent: float
    timestamp: float

    def __str__(self):
        return (f"Spread Opportunity: {self.base_token} - "
                f"Buy on {self.buy_exchange} at {self.buy_price}, "
                f"Sell on {self.sell_exchange} at {self.sell_price}, "
                f"Spread: {self.spread_percent:.2f}%")