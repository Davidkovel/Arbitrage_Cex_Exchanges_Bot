import asyncio
import json
import time
import uuid
from typing import Dict, Any, List, Tuple

import websockets

from src.exchanges.ws.websocket import Exchange
from src.utils.logger import logger


class BingXExchange(Exchange):
    def __init__(self):
        """Implementation for MEXC exchange"""
        super().__init__("BINGX")
        self.ws_url = "wss://open-api-swap.bingx.com/swap-market"

        self._exchange_symbols: List[str] = []
        self._subscribe_lock = asyncio.Lock()

    @property
    async def exchange_symbols(self) -> List[str]:
        """Получение списка символов (асинхронное свойство)"""
        return self._exchange_symbols.copy()  # Возвращаем копию для безопасности

    async def set_exchange_symbols(self, symbols: List[str]):
        """Установка списка символов (асинхронный метод)"""
        if symbols is None:
            return
        async with self._subscribe_lock:
            self._exchange_symbols = symbols.copy()  # Сохраняем копию списка

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
        if not symbols:
            logger.warning(f"No symbols provided for {self.exchange_name}")
            return

        for symbol in symbols:
            data_type = f"{symbol}@lastPrice"
            subscription = {
                "id": str(uuid.uuid4()),
                "reqType": "sub",
                "dataType": data_type
            }
            await self.websocket.send(json.dumps(subscription))
            self.available_pairs.add(symbol)
        logger.info(f"{self.exchange_name} subscribed to: {symbols}")

    async def _process_message(self, data: Dict[str, Any]):
        try:
            if data.get("e") == "lastPrice":
                symbol = data.get("s")  # e.g., BTC-USD
                price = float(data.get("p"))
                timestamp = int(data.get("E")) / 1000

                if symbol and price:
                    self.prices[symbol] = price
                    self.notify_price_update(symbol, price, timestamp)
        except Exception as ex:
            logger.error(f"Bingx error processing message {ex}")
            pass
            # logger.error(f"[BINGX] Message processing failed: {ex}")
            logger.debug(f"[BINGX] Raw message: {json.dumps(data)}")

    @staticmethod
    def get_deposit_withdrawal_status(symbol: str) -> Tuple[Any, Any]:
        return True, True

    async def send_ping(self):
        if self.websocket:
            await self.websocket.send(json.dumps({"method": "ping"}))

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
