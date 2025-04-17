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
            self.websocket = await websockets.connect(self.ws_url)
            logger.info(f"{self.exchange_name} connected to {self.ws_url}")
            asyncio.create_task(self._keep_alive())
            asyncio.create_task(self.receive_messages())
        except Exception as e:
            logger.error(f"{self.exchange_name} connection error: {e}")
            raise

    async def subscribe(self, symbols: List[str]):
        """Subscribe to market data for the given symbols"""
        for symbol in symbols:
            formatted_symbol = symbol.upper()
            self.available_pairs.add(symbol)
            subscription = {
                "method": "sub.tickers",
                "param": {
                    "symbol": formatted_symbol
                }
            }

            await self.websocket.send(json.dumps(subscription))
            logger.info(f"{self.exchange_name} subscribed to {symbol}")

    async def _process_message(self, data: Dict[str, Any]):
        print(data)
        """Process incoming MEXC websocket messages"""
        if data.get("data") == "success":
            logger.info(f"{self.exchange_name} Websocket subscription successful")
            return

        if data.get("channel") == "push.ticker":
            timestamp = data.get("ts", 0) / 1000  # Convert to seconds

            for ticker in data.get("data"):
                try:
                    symbol = ticker.get("symbol", "").upper().replace("_USDT", "")
                    price = float(ticker.get("lastPrice", 0))

                    if symbol and price:
                        self.prices[symbol] = price
                        self.notify_price_update(symbol, price, timestamp)

                except (ValueError, AttributeError) as e:
                    logger.error(f"Error processing ticker {ticker}: {e}")
        else:
            logger.debug(f"{self.exchange_name} Unhandled message type: {data}")
