from collections import defaultdict
from typing import Any, Dict

from src.utils.logger import logger


class PriceAggregator:
    def __init__(self):
        self.prices = defaultdict(dict)  # {'BTC': {'MEXC': 50000, 'Bybit': 50100}}
        self.threshold = 0.01  # 1% спред

    def update_price(self, exchange: str, data: Dict[str, Any]):
        print(data)
        symbol = data['symbol']
        price = float(data['data'].get('price') or data['data'].get('last_price') or 0)

        if not price:
            return

        self.prices[symbol][exchange] = price
        self._check_spread(symbol)

    def _check_spread(self, symbol: str):
        if symbol not in self.prices or len(self.prices[symbol]) < 2:
            return

        prices = self.prices[symbol]
        min_price = min(prices.values())
        max_price = max(prices.values())

        if min_price == 0:
            return

        spread = (max_price - min_price) / min_price

        if spread >= self.threshold:
            logger.warning(f"Spread alert for {symbol}: {spread * 100:.2f}%")
            for exchange, price in prices.items():
                logger.warning(f"{exchange}: {price}")

