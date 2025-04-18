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
        if symbols is None:
            subscription = {
              "op":"subscribe",
              "args":[
                {
                    "instType": "USDT-FUTURES",
                    "channel": "ticker",
                    "instId": "BTCUSDT"
                }
              ]
            }
            await self.websocket.send(json.dumps(subscription))
            logger.info(f"{self.exchange_name} subscribed to all tickers")
        else:
            for symbol in symbols:
                formatted_symbol = symbol.upper().replace("_", "")
                self.available_pairs.add(formatted_symbol)
                subscription = {
                  "op":"subscribe",
                  "args":[
                    {
                      "instType":"USDT-FUTURES",
                      "channel":"ticker",
                      "instId": formatted_symbol
                    }
                  ]
                }
            await self.websocket.send(json.dumps(subscription))
            logger.info(f"{self.exchange_name} subscribed to {formatted_symbol}")

    async def _process_message(self, data: Dict[str, Any]):
        print(data)
        """Process incoming MEXC websocket messages"""
        try:
            if data.get("channel") == "pong":
                logger.debug(f"Received pong: {data.get('data')}")
                return

            # if data.get("data") == "success":
            #     # print(data)
            #     logger.info(f"{self.exchange_name} Websocket subscription successful")
            #     return

            # timestamp = data.get("ts", 0) / 1000  # Convert to seconds

            logger.debug(f"Received data successful")
            for ticker in data.get("data", []):
                try:
                    symbol = ticker.get("instId", "").upper()
                    price = float(ticker.get("lastPr", 0))
                    timestamp = int(ticker.get("ts", 0)) / 1000

                    if symbol and price:
                        self.prices[symbol] = price
                        self.notify_price_update(symbol, price, timestamp)

                except (ValueError, TypeError) as e:
                    logger.error(f"Error processing ticker {ticker.get('symbol')}: {e}")

            return
        except Exception as ex:
            logger.error(f"Message processing failed: {ex}")
            logger.debug(f"Raw message that failed: {data}")
