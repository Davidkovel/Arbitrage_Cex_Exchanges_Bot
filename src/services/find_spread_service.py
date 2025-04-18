from collections import defaultdict
from typing import Any, Dict, Tuple, List
import asyncio

from attr import dataclass

from src.entities.entities_spread import TokenPrice, SpreadOpportunity
from src.exchanges.ws.websocket import Exchange
from src.utils.logger import logger


class SpreadFinder:
    """Class to track token prices and find spread opportunities"""

    def __init__(self, min_spread_percent: float = 1.0):
        self.token_prices: Dict[Tuple[str, str], TokenPrice] = {}  # (exchange, symbol) -> TokenPrice
        self.min_spread_percent = min_spread_percent
        self.spread_callbacks = []

    def register_spread_callback(self, callback):
        """Register a callback function to be called when a spread opportunity is found"""
        self.spread_callbacks.append(callback)

    def price_update(self, price_data: TokenPrice):
        """Process a price update and check for spread opportunities"""
        # Update the price in our tracking dictionary
        key = (price_data.exchange, price_data.symbol)
        self.token_prices[key] = price_data

        # Check for spread opportunities with this symbol
        self._check_spreads(price_data.symbol)

    def _check_spreads(self, symbol: str):
        """Check for spread opportunities for a specific symbol"""
        # Find all exchanges that have this symbol
        exchanges_with_symbol = [
            exchange for (exchange, s), price_data in self.token_prices.items()
            if s == symbol
        ]

        if len(exchanges_with_symbol) < 2:
            return  # Need at least two exchanges for a spread

        # Find the best buy (lowest price) and best sell (highest price)
        buy_exchange = None
        buy_price = float('inf')
        sell_exchange = None
        sell_price = 0

        for exchange in exchanges_with_symbol:
            price_data = self.token_prices.get((exchange, symbol))
            if not price_data:
                continue

            if price_data.price < buy_price:
                buy_price = price_data.price
                buy_exchange = exchange

            if price_data.price > sell_price:
                sell_price = price_data.price
                sell_exchange = exchange

        # Calculate spread
        if buy_exchange and sell_exchange and buy_exchange != sell_exchange:
            spread_percent = ((sell_price - buy_price) / buy_price) * 100

            if spread_percent >= self.min_spread_percent:
                # We found a viable spread opportunity
                opportunity = SpreadOpportunity(
                    base_token=symbol,
                    buy_exchange=buy_exchange,
                    buy_price=buy_price,
                    sell_exchange=sell_exchange,
                    sell_price=sell_price,
                    spread_percent=spread_percent,
                    timestamp=max(
                        self.token_prices[(buy_exchange, symbol)].timestamp,
                        self.token_prices[(sell_exchange, symbol)].timestamp
                    )
                )

                # Notify all registered callbacks
                for callback in self.spread_callbacks:
                    callback(opportunity)


class SpreadService:
    """Main service class to orchestrate the spread finding process"""

    def __init__(self, min_spread_percent: float = 1.0):
        self.exchanges: Dict[str, Exchange] = {}
        self.spread_finder = SpreadFinder(min_spread_percent)
        self.running = False

        # Register the default callback for spread opportunities
        self.spread_finder.register_spread_callback(self._on_spread_opportunity)

    def add_exchange(self, exchange: Exchange):
        """Add an exchange to the service"""
        self.exchanges[exchange.exchange_name] = exchange
        # Register the price update callback
        exchange.register_price_callback(self.spread_finder.price_update)

    def _on_spread_opportunity(self, opportunity: SpreadOpportunity):
        """Default callback for when a spread opportunity is found"""
        logger.info(f"Found spread opportunity: {opportunity}")
        # You could implement additional logic here:
        # - Store opportunity in a database
        # - Send a notification
        # - Place trades automatically

    async def start(self, symbols: List[str] | None = None):
        """Start the spread service"""
        if self.running:
            return

        self.running = True

        # Connect to all exchanges
        connect_tasks = []
        for exchange in self.exchanges.values():
            connect_tasks.append(exchange.connect())

        await asyncio.gather(*connect_tasks)

        # Subscribe to all symbols
        subscribe_tasks = []
        for exchange in self.exchanges.values():
            subscribe_tasks.append(exchange.subscribe(symbols))

        await asyncio.gather(*subscribe_tasks)

        # Start receiving messages from all exchanges
        receive_tasks = []
        for exchange in self.exchanges.values():
            receive_tasks.append(exchange.receive_messages())

        # Run all tasks concurrently
        await asyncio.gather(*receive_tasks)

    async def stop(self):
        """Stop the spread service"""
        self.running = False
        close_tasks = []
        for exchange in self.exchanges.values():
            close_tasks.append(exchange.close())

        await asyncio.gather(*close_tasks)
