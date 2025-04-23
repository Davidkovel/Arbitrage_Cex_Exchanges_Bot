import asyncio
import json
from typing import Dict, Any, List

import websockets

from src.exchanges.ws.websocket import Exchange
from src.utils.logger import logger


class BitgetExchange(Exchange):
    def __init__(self):
        """Implementation for LBank exchange"""
        super().__init__("BITGET")
        self.ws_url = "wss://ws.bitget.com/v2/ws/public"

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
                    # formatted_symbol = symbol.replace("USDT", "_USDT")
                    price = float(ticker.get("lastPr", 0))
                    timestamp = int(ticker.get("ts", 0)) / 1000

                    if symbol and price:
                        self.prices[symbol] = price
                        # logger.warning(f"BITGET Price update: {symbol} - {price}")
                        self.notify_price_update(symbol, price, timestamp)

                except (ValueError, TypeError) as e:
                    logger.error(f"Error processing ticker {ticker.get('symbol')}: {e}")

            return
        except Exception as ex:
            # Todo: Тут ошибка позже надо разобраться и доделать
            #  "2025-04-22 20:14:58.889 | ERROR    | src.exchanges.bitget:_process_message:81 - [BITGET] Message processing failed: ('MEXC', 'DYDXUSDT')
            # 2025-04-22 20:14:58.889 | DEBUG    | src.exchanges.bitget:_process_message:82 - [BITGET] Raw message that failed: {"action": "snapshot", "arg": {"instType": "USDT-FUTURES", "channel": "ticker", "instId": "DYDXUSDT"}, "data": [{"instId": "DYDXUSDT", "lastPr": "0.6138", "bidPr": "0.6136", "askPr": "0.6138", "bidSz""
            #
            pass
            # logger.error(f"[BITGET] Message processing failed: {ex}")
            # logger.debug(f"[BITGET] Raw message that failed: {json.dumps(data)[:200]}")

    async def send_ping(self):
        if self.websocket:
            await self.websocket.send("ping")
