import asyncio
import json
from typing import Dict, Any, List

import websockets

from src.exchanges.ws.websocket import Exchange
from src.utils.logger import logger


class MexcExchange(Exchange):
    def __init__(self):
        """Implementation for MEXC exchange"""
        super().__init__("MEXC")
        self.ws_url = "wss://contract.mexc.com/edge"

    async def connect(self):
        """Connect to MEXC websocket"""
        try:
            self.websocket = await websockets.connect(
                self.ws_url,
                ping_interval=15,
                ping_timeout=10,
                close_timeout=5
            )
            self._running = True
            logger.info(f"{self.exchange_name} connected to {self.ws_url}")
            asyncio.create_task(self._keep_alive())
            asyncio.create_task(self.receive_messages())
        except Exception as e:
            logger.error(f"{self.exchange_name} connection error: {e}")
            raise

    async def subscribe(self, symbols: List[str]):
        """Subscribe to market data for the given symbols"""
        if symbols is None:
            subscription = {
                "method": "sub.tickers",
                "param": {}
            }
            await self.websocket.send(json.dumps(subscription))
            logger.info(f"{self.exchange_name} subscribed to all tickers")
        else:
            for symbol in symbols:
                formatted_symbol = symbol.upper()
                self.available_pairs.add(formatted_symbol)
                subscription = {
                    "method": "sub.tickers",
                    "param": {
                        "symbol": formatted_symbol
                    }
                }
                await self.websocket.send(json.dumps(subscription))
                logger.info(f"{self.exchange_name} subscribed to {formatted_symbol}")

    async def _process_message(self, data: Dict[str, Any]):
        """Process incoming MEXC websocket messages"""
        try:
            if data.get("channel") == "pong":
                logger.debug(f"Received pong: {data.get('data')}")
                return

            if data.get("data") == "success":
                #print(data)
                logger.info(f"{self.exchange_name} Websocket subscription successful")
                return

            timestamp = data.get("ts", 0) / 1000  # Convert to seconds

            logger.debug(f"Received data successful")
            for ticker in data.get("data", []):
                try:
                    symbol = ticker.get("symbol", "").replace("_USDT", "").upper()
                    price = float(ticker.get("lastPrice", 0))

                    if symbol and price:
                        self.prices[symbol] = price
                        self.notify_price_update(symbol, price, timestamp)

                except (ValueError, TypeError) as e:
                    logger.error(f"Error processing ticker {ticker.get('symbol')}: {e}")

            return
        except Exception as ex:
            logger.error(f"Message processing failed: {ex}")
            logger.debug(f"Raw message that failed: {data}")

# Fixed
#
# import asyncio
# import json
# import websockets
# import logging
# from typing import List, Dict, Set, Any
# from abc import abstractmethod
#
# logger = logging.getLogger(__name__)
#
# class TokenPrice:
#     def __init__(self, exchange: str, symbol: str, price: float, timestamp: float):
#         self.exchange = exchange
#         self.symbol = symbol
#         self.price = price
#         self.timestamp = timestamp
#
# class MexcExchange:
#     def __init__(self):
#         self.exchange_name = "MEXC"
#         self.ws_url = "wss://contract.mexc.com/edge"
#         self.websocket = None
#         self._running = True
#         self.prices: Dict[str, float] = {}
#         self.available_pairs: Set[str] = set()
#         self.price_callbacks = []
#
#     def register_price_callback(self, callback):
#         """Register a callback function to be called when prices are updated"""
#         self.price_callbacks.append(callback)
#
#     def notify_price_update(self, symbol: str, price: float, timestamp: float):
#         """Notify all registered callbacks about a price update"""
#         for callback in self.price_callbacks:
#             callback(TokenPrice(self.exchange_name, symbol, price, timestamp))
#
#     async def connect(self):
#         """Connect to MEXC websocket"""
#         try:
#             self.websocket = await websockets.connect(self.ws_url)
#             logger.info(f"{self.exchange_name} connected to {self.ws_url}")
#             asyncio.create_task(self._keep_alive())
#             asyncio.create_task(self.receive_messages())
#         except Exception as e:
#             logger.error(f"{self.exchange_name} connection error: {e}")
#             raise
#
#     async def subscribe(self, symbols: List[str]):
#         """Subscribe to market data for the given symbols"""
#         for symbol in symbols:
#             formatted_symbol = symbol.upper()
#             self.available_pairs.add(symbol)
#             subscription = {
#                 "method": "sub.tickers",
#                 "param": {
#                     "symbol": formatted_symbol
#                 }
#             }
#
#             await self.websocket.send(json.dumps(subscription))
#             logger.info(f"{self.exchange_name} subscribed to {symbol}")
#
#     async def _process_message(self, data: Dict[str, Any]):
#         """Process incoming MEXC websocket messages"""
#         print(data)
#         if data.get("data") == "success":
#             logger.info(f"{self.exchange_name} Websocket subscription successful")
#             return
#
#         if data.get("channel") == "push.ticker":
#             timestamp = data.get("ts", 0) / 1000  # Convert to seconds
#
#             for ticker in data.get("data"):
#                 try:
#                     symbol = ticker.get("symbol", "").upper().replace("_USDT", "")
#                     price = float(ticker.get("lastPrice", 0))
#
#                     if symbol and price:
#                         self.prices[symbol] = price
#                         self.notify_price_update(symbol, price, timestamp)
#
#                 except (ValueError, AttributeError) as e:
#                     logger.error(f"Error processing ticker {ticker}: {e}")
#         else:
#             logger.debug(f"{self.exchange_name} Unhandled message type: {data}")
#
#     async def _keep_alive(self):
#         """Поддержание соединения"""
#         print('keep_alive')
#         while self._running:
#             await asyncio.sleep(10)
#             await self.send_ping()
#
#     async def send_ping(self):
#         """Отправка ping"""
#         if self.websocket:
#             await self.websocket.send(json.dumps({"method": "ping"}))
#
#     async def _reconnect(self):
#         await asyncio.sleep(5)
#         logger.info(f"{self.exchange_name} attempting to reconnect...")
#         await self.connect()
#
#     async def receive_messages(self):
#         """Основной цикл приема сообщений"""
#         print('receive_messages')
#         while self._running:
#             try:
#                 message = await self.websocket.recv()
#                 print('Raw data ', message)
#                 try:
#                     data = json.loads(message)
#                     await self._process_message(data)
#                 except json.JSONDecodeError:
#                     logger.error(f"{self.exchange_name} non-JSON message: {message}")
#             except websockets.exceptions.ConnectionClosed:
#                 logger.error(f"{self.exchange_name} connection closed, reconnecting...")
#                 await self._reconnect()
#                 break
#             except Exception as e:
#                 logger.error(f"{self.exchange_name} receive error: {e}")
#                 break
#
#     async def close(self):
#         self._running = False
#         if self.websocket:
#             await self.websocket.close()
#             logger.info(f"{self.exchange_name} WebSocket disconnected")
