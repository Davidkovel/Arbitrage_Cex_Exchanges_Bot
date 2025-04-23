import asyncio
import json
from abc import abstractmethod, ABC
from typing import Dict, Any, Callable, Set, Optional, List
import websockets
from collections import defaultdict

from src.entities.entities_spread import TokenPrice
from src.utils.logger import logger


class Exchange(ABC):
    def __init__(self, exchange_name: str):
        self.exchange_name = exchange_name
        self.websocket = None
        self._running = False
        self.prices: Dict[str, float] = {}
        self.available_pairs: Set[str] = set()
        self.price_callbacks = []

    def register_price_callback(self, callback):
        """Register a callback function to be called when prices are updated"""
        self.price_callbacks.append(callback)

    def notify_price_update(self, symbol: str, price: float, timestamp: float):
        """Notify all registered callbacks about a price update"""
        for callback in self.price_callbacks:
            callback(TokenPrice(self.exchange_name, symbol, price, timestamp))

    @abstractmethod
    async def connect(self):
        pass

    @abstractmethod
    async def subscribe(self, symbols: List[str]):
        """Subscribe to market data for the given symbols"""
        pass

    @abstractmethod
    async def _process_message(self, data):
        """Process incoming websocket messages"""
        pass

    @abstractmethod
    async def send_ping(self):
        pass

    async def _keep_alive(self):
        """Поддержание соединения"""
        while self._running:
            await asyncio.sleep(10)
            await self.send_ping()

    async def _reconnect(self):
        await asyncio.sleep(5)
        logger.info(f"{self.exchange_name} attempting to reconnect...")
        await self.connect()

    async def receive_messages(self):
        """Основной цикл приема сообщений"""
        while self._running:
            try:
                message = await self.websocket.recv()
                # print('Raw data ', message)
                try:
                    # @TODO: Исправить обработка pong от bitget т.к он присылает не json а строка. Исправить надо позже
                    if message == "pong":
              #          logger.info(f"Pong received from {self.exchange_name}")
                        continue
                    data = json.loads(message)
                    await self._process_message(data)
                except json.JSONDecodeError:
                    logger.error(f"{self.exchange_name} non-JSON message: {message}")
                except Exception as ex:
                    print(message)
                    logger.error(f"{self.exchange_name} message processing error: {ex}")
            except websockets.exceptions.ConnectionClosed:
                logger.error(f"{self.exchange_name} connection closed, reconnecting...")
                await self._reconnect()
                break
            except Exception as e:
                logger.error(f"{self.exchange_name} receive error: {e}")
                # await self._reconnect()
                break

    async def close(self):
        self._running = False
        if self.websocket:
            await self.websocket.close()
            logger.info(f"{self.exchange_name} WebSocket disconnected")
