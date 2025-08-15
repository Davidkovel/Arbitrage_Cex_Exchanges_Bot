import asyncio
import json
from typing import Dict, Any, List, Tuple

import websockets

from src.exchanges.ws.websocket import Exchange
from src.utils.Normalizer import NormalizerSymbolsExchanges
from src.utils.logger import logger


class BitgetExchange(Exchange):
    def __init__(self):
        """Implementation for LBank exchange"""
        super().__init__("BITGET")
        self.ws_url = "wss://ws.bitget.com/v2/ws/public"
        self.rest_url = "https://api.bitget.com/api/mix/v1/market/tickers"

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

    async def get_ticker_price(self, symbol: str) -> float:
        """Get the ticker price for a symbol"""
        try:
            params = {"symbol": symbol}
            async with self.session.get(self.rest_url, params=params) as resp:
                data = await resp.json()
                return float(data['data']['last'])
        except Exception as e:
            logger.error(f"Bitget price verification failed: {e}")
            return 0.0

    async def connect(self):
        """Connect to MEXC websocket"""
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
        for symbol in symbols:
            formatted_symbol = symbol.upper().replace("_", "")
            self.available_pairs.add(formatted_symbol)
            subscription = {
                "op": "subscribe",
                "args": [
                    {
                        "instType": "USDT-FUTURES",
                        "channel": "ticker",
                        "instId": formatted_symbol
                    }
                ]
            }

            await self.websocket.send(json.dumps(subscription))
            # logger.info(f"{self.exchange_name} subscribed to {formatted_symbol}")

    async def _process_message(self, data: Dict[str, Any]):
        """Process incoming MEXC websocket messages"""
        try:
            if data == "pong":
                logger.debug(f"Received pong: {data.get('data')}")
                return

            # if data.get("data") == "success":
            #     # print(data)
            #     logger.info(f"{self.exchange_name} Websocket subscription successful")
            #     return

            # timestamp = data.get("ts", 0) / 1000  # Convert to seconds

            # logger.debug(f"Received data successful")

            for ticker in data.get("data", []):
                try:
                    symbol = ticker.get("instId", "").upper()
                    formatted_symbol = await NormalizerSymbolsExchanges.normalize_symbol('bitget', symbol)
                    price = float(ticker.get("lastPr", 0))
                    timestamp = int(ticker.get("ts", 0)) / 1000

                    if formatted_symbol and price:
                        self.prices[formatted_symbol] = price
                        # logger.warning(f"BITGET Price update: {symbol} - {price}")
                        self.notify_price_update(formatted_symbol, price, timestamp)

                except (ValueError, TypeError) as e:
                    logger.error(f"Error processing ticker {ticker.get('symbol')}: {e}")

            return
        except Exception as ex:
            logger.error(f"Bitget process message error {ex}")
            # Todo: Тут ошибка позже надо разобраться и доделать
            #  "2025-04-22 20:14:58.889 | ERROR    | src.exchanges.bitget:_process_message:81 - [BITGET] Message processing failed: ('MEXC', 'DYDXUSDT')
            # 2025-04-22 20:14:58.889 | DEBUG    | src.exchanges.bitget:_process_message:82 - [BITGET] Raw message that failed: {"action": "snapshot", "arg": {"instType": "USDT-FUTURES", "channel": "ticker", "instId": "DYDXUSDT"}, "data": [{"instId": "DYDXUSDT", "lastPr": "0.6138", "bidPr": "0.6136", "askPr": "0.6138", "bidSz""
            #
            pass
            # logger.error(f"[BITGET] Message processing failed: {ex}")
            logger.debug(f"[BITGET] Raw message that failed: {json.dumps(data)}")

    @staticmethod
    def get_deposit_withdrawal_status(symbol: str) -> Tuple[Any, Any]:
        return True, True

    async def send_ping(self):
        if self.websocket:
            await self.websocket.send("ping")

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
