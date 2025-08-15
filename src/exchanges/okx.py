import asyncio
import json
import time
from typing import Dict, Any, List, Tuple

import websockets

from src.exchanges.ws.websocket import Exchange
from src.utils.Normalizer import NormalizerSymbolsExchanges
from src.utils.logger import logger


class OkxExchange(Exchange):
    def __init__(self):
        """Implementation for OKX exchange"""
        super().__init__("OKX")
        self.ws_url = "wss://ws.okx.com:8443/ws/v5/public"
        self.rest_url = "https://www.okx.com/api/v5/market/ticker"

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
            params = {"instId": symbol}
            async with self.session.get(self.rest_url, params=params) as resp:
                data = await resp.json()
                return float(data['data'][0]['last'])
        except Exception as e:
            logger.error(f"OKX price fetch error: {e}")
            return 0.0

    async def connect(self):
        """Connect to MEXC websocket"""
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
            subscription = {
                "op": "subscribe",
                "args": [
                    {
                        "channel": "tickers",
                        "instId": symbol
                    }
                ]
            }
            await self.websocket.send(json.dumps(subscription))
            self.available_pairs.add(symbol)
        logger.info(f"{self.exchange_name} subscribed to all tickers")

    async def _process_message(self, message: str):
        """Process incoming OKX websocket messages"""
        try:
            if isinstance(message, str):
                data = json.loads(message)
            else:
                data = message

            if data.get("arg", {}).get("channel") == "tickers":
                for ticker in data.get("data", []):
                    symbol = ticker.get("instId", "").upper()
                    formatted_symbol = await NormalizerSymbolsExchanges.normalize_symbol('okx', symbol)
                    price = float(ticker.get("last", 0))
                    timestamp = int(ticker.get("ts", time.time() * 1000)) / 1000

                    # logger.info(f"OKX Price update: {symbol} - {price}")
                    if formatted_symbol and price:
                        self.prices[formatted_symbol] = price
                        self.notify_price_update(formatted_symbol, price, timestamp)
        except Exception as ex:
            pass
            logger.error(f"[OKX] Message processing failed: {ex}")

            # logger.error(f"[OKX] Message processing failed: {ex}")
            logger.debug(f"[OKX] Raw message that failed: {json.dumps(message)}")

    @staticmethod
    def get_deposit_withdrawal_status(symbol: str) -> Tuple[Any, Any]:
        """Get deposit and withdrawal status for a symbol"""
        try:
            return True, True
        except Exception as e:
            logger.error(f"OKX deposit/withdrawal status fetch error: {e}")
            return None, None

    async def send_ping(self):
        try:
            if self.websocket:
                await self.websocket.send(json.dumps({"op": "ping"}))
        except Exception as e:
            logger.warning(f"{self.exchange_name} ping error: {e}")
            await self._reconnect()

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
