import asyncio
import json
import time
from typing import Dict, Any, List, Tuple

import websockets
from pybit.unified_trading import WebSocket

from src.exchanges.ws.websocket import Exchange
from src.utils.Normalizer import NormalizerSymbolsExchanges
from src.utils.logger import logger


class BybitExchange(Exchange):
    def __init__(self):
        """Implementation for Bybit exchange"""
        super().__init__("BYBIT")
        self.ws_url = "wss://stream.bybit.com/v5/public/linear"
        self.rest_url = "https://api.bybit.com/v5/market/tickers"
        self.ws_client = None

        self._exchange_symbols: List[str] = []
        self._subscribe_lock = asyncio.Lock()

    @property
    async def exchange_symbols(self) -> List[str]:
        """Получение списка символов (асинхронное свойство)"""
        return self._exchange_symbols.copy()  # Возвращаем копию для безопасности

    async def set_exchange_symbols(self, symbols: List[str]):
        """Установка списка символов (асинхронный метод)"""
        async with self._subscribe_lock:
            self._exchange_symbols = symbols.copy()  # Сохраняем копию списка

    async def get_last_price(self, symbol: str) -> float:
        try:
            params = {"category": "linear", "symbol": symbol}
            async with self.session.get(self.rest_url, params=params) as resp:
                data = await resp.json()
                return float(data['result']['list'][0]['lastPrice'])
        except Exception as e:
            logger.error(f"Bybit price fetch error: {e}")
            return 0.0

    async def connect(self):
        """Connect to BYBIT websocket"""
        try:
            self.websocket = await websockets.connect(self.ws_url)
            self._running = True
            logger.info(f"{self.exchange_name} connected to {self.ws_url}")
            asyncio.create_task(self._keep_alive())
            asyncio.create_task(self.receive_messages())
        except Exception as e:
            logger.error(f"{self.exchange_name} connection error: {e}")
            raise

    async def subscribe(self, symbols: List[str]):
        """Subscribe to market data for the given symbols"""
        if not symbols:
            logger.warning(f"No symbols provided for {self.exchange_name}")
            return

        for symbol in symbols:
            topic = f"tickers.{symbol}"

            subscription = {
                "op": "subscribe",
                "args": [topic]
            }

            try:
                await self.websocket.send(json.dumps(subscription))
                self.available_pairs.add(symbol)
                # logger.debug(f"Subscribed to {symbol} tickers")
            except Exception as e:
                logger.error(f"Failed to subscribe to {symbol}: {e}")

        logger.info(f"{self.exchange_name} subscribed to {len(symbols)} tickers")

    async def _process_message(self, data: Dict[str, Any]):
        """Process incoming MEXC websocket messages"""
        try:
            if data.get("topic", "").startswith("tickers."):
                data = data.get("data", {})
                symbol = data.get("symbol", "").upper()
                price = float(data.get("lastPrice", 0))
                timestamp = int(time.time() * 1000) / 1000  # Bybit doesn't provide timestamp in messag

                formatted_symbol = await NormalizerSymbolsExchanges.normalize_symbol('bybit', symbol)

                if formatted_symbol and price:
                    self.prices[formatted_symbol] = price
                    self.notify_price_update(formatted_symbol, price, timestamp)

        except Exception as e:
            logger.error(f"{self.exchange_name} error processing message: {e}")
            logger.debug(f"[Bybit] Raw message: {json.dumps(data)}")

    @staticmethod
    def get_deposit_withdrawal_status(symbol: str) -> Tuple[Any, Any]:
        """Get deposit and withdrawal status for a symbol"""
        try:
            return True, True
        except Exception as e:
            logger.error(f"Bybit deposit/withdrawal status fetch error: {e}")
            return False, False

    async def send_ping(self):
        if self.websocket:
            await self.websocket.send(json.dumps({"op": "ping"}))

    async def _reconnect(self):
        self._running = False  # Остановим receive_messages и keep_alive
        try:
            if self.websocket:
                await self.websocket.close()
        except Exception as ex:
            logger.error(f"{self.exchange_name} websocket close error: {ex}")

        await asyncio.sleep(5)
        logger.info(f"{self.exchange_name} attempting to reconnect...")
        await self.connect()
        await asyncio.sleep(4)
        await self.subscribe(self._exchange_symbols)
