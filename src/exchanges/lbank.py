import asyncio
import json
import time
from typing import Dict, Any, List, Tuple

import websockets

from src.exchanges.ws.websocket import Exchange
from src.utils.logger import logger


class LBankExchange(Exchange):
    def __init__(self):
        """Implementation for LBANK exchange"""
        super().__init__("LBANK")
        self.ws_url = "wss://www.lbkex.net/ws/V2/"
        self._running = False

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

    async def connect(self):
        """Connect to LBANK websocket"""
        try:
            self.websocket = await websockets.connect(
                self.ws_url,
                ping_interval=None,  # Отключаем авто-ping, используем свой
                ping_timeout=None,
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
        if not symbols:
            logger.warning(f"No symbols provided for {self.exchange_name}")
            return

        for symbol in symbols:
            try:
                # LBANK использует формат "BTC_USDT"
                formatted_symbol = symbol.replace("-", "_").upper()
                subscription = {
                    "action": "subscribe",
                    "subscribe": "tick",
                    "pair": formatted_symbol
                }
                await self.websocket.send(json.dumps(subscription))
                self.available_pairs.add(formatted_symbol)
                # logger.info(f"{self.exchange_name} subscribed to {formatted_symbol}")
            except Exception as e:
                logger.error(f"Subscription error for {symbol}: {e}")

    async def _process_message(self, data: Dict[str, Any]):
        """Process incoming LBANK websocket messages"""
        try:
            # Обработка pong-сообщений
            if data.get("action") == "pong":
                return

            # Обработка тиков
            if data.get("type") == "tick":
                tick_data = data.get("tick", {})
                symbol = data.get("pair", "").replace("_", "").upper()  # BTC_USDT -> BTC
                price = float(tick_data.get("latest", 0))
                timestamp = self._parse_lbank_time(data.get("TS"))

                if symbol and price:
                    self.prices[symbol] = price
                    self.notify_price_update(symbol, price, timestamp)

        except Exception as ex:
            pass
            logger.error(f"[LBANK] Message processing failed: {ex}")
            logger.debug(f"[LBANK] Raw message: {json.dumps(data)}")

    def _parse_lbank_time(self, time_str: str) -> float:
        """Convert LBANK time format to timestamp"""
        try:
            from datetime import datetime
            dt = datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%S.%f")
            return dt.timestamp()
        except:
            return time.time()

    @staticmethod
    def get_deposit_withdrawal_status(symbol: str) -> Tuple[Any, Any]:
        pass

    async def send_ping(self):
        """Send ping to LBANK"""
        if self.websocket:
            await self.websocket.send(json.dumps({"action": "ping"}))

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

    # async def _keep_alive(self):
    #     """Keep connection alive"""
    #     while self._running:
    #         await asyncio.sleep(10)
    #         await self.send_ping()
