import asyncio
import hashlib
import hmac
import json
import os
import time
from typing import Dict, Any, List, Tuple

import requests
import websockets
from dotenv import load_dotenv

from src.exchanges.ws.websocket import Exchange
from src.utils.Normalizer import NormalizerSymbolsExchanges
from src.utils.logger import logger

load_dotenv()


class MexcApiConfig:
    API_KEY = os.getenv("MEXC_API_KEY")
    API_SECRET = os.getenv("MEXC_API_SECRET")


class MexcExchange(Exchange, MexcApiConfig):
    def __init__(self):
        """Implementation for MEXC exchange"""
        super().__init__("MEXC")
        self.ws_url = "wss://contract.mexc.com/edge"
        self.rest_url = "https://contract.mexc.com/api/v1/contract/ticker"
        self._exchange_symbols: List[str] = []  # Приватный атрибут для хранения символов
        self._subscribe_lock = asyncio.Lock()  # Блокировка для безопасного доступа

        API_KEY = os.getenv("MEXC_API_KEY")
        API_SECRET = os.getenv("MEXC_API_SECRET")

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

    async def get_last_price(self, symbol: str) -> float:
        try:
            params = {"symbol": symbol}
            async with self.session.get(self.rest_url, params=params) as resp:
                data = await resp.json()
                return float(data['data']['lastPrice'])
        except Exception as e:
            logger.error(f"MEXC price fetch error: {e}")
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
                # logger.debug(f"Received pong: {data.get('data')}")
                return

            if data.get("data") == "success":
                # print(data)
                logger.info(f"{self.exchange_name} Websocket subscription successful")
                return

            timestamp = data.get("ts", 0) / 1000  # Convert to seconds

            # logger.debug(f"Received data successful")
            for ticker in data.get("data", []):
                try:
                    symbol = ticker.get("symbol", "").upper()
                    formatted_symbol = await NormalizerSymbolsExchanges.normalize_symbol('mexc', symbol)
                    price = float(ticker.get("lastPrice", 0))

                    if formatted_symbol and price:
                        self.prices[formatted_symbol] = price
                        # logger.warning(f"MEXC Price update: {symbol} - {price}")
                        self.notify_price_update(formatted_symbol, price, timestamp)

                except (ValueError, TypeError) as e:
                    logger.error(f"[MEXC] Error processing ticker {ticker.get('symbol')}: {e}")
                    logger.debug(f"[MEXC] Raw message: {json.dumps(data)}")

            return
        except Exception as ex:
            # Todo: Тут также ошибка как и с bitget биржа
            pass

            logger.error(f"[MEXC] Message processing failed: {ex}")
            # logger.debug(f"[MEXC] Raw message that failed: {json.dumps(data)[:200]}")

    @staticmethod
    def get_deposit_withdrawal_status(symbol: str) -> Tuple[Any, Any]:
        try:
            symbol = NormalizerSymbolsExchanges.normalize_without_usdt_symbol(symbol)

            api_key = os.getenv("MEXC_API_KEY")
            api_secret = os.getenv("MEXC_SECRET_KEY")

            if not api_key or not api_secret:
                raise ValueError("MEXC API credentials not configured")

            base_url = "https://api.mexc.com"
            endpoint = "/api/v3/capital/config/getall"
            timestamp = int(time.time() * 1000)

            # Create signature
            query_string = f"timestamp={timestamp}"
            signature = hmac.new(
                api_secret.encode('utf-8'),
                query_string.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()

            # Build request URL
            url = f"{base_url}{endpoint}?{query_string}&signature={signature}"

            headers = {
                "X-MEXC-APIKEY": api_key,
                "Accept": "application/json",
                "Content-Type": "application/json"
            }

            # Make authenticated request
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code != 200:
                logger.error(f"MEXC API error: HTTP {response.status_code} - {response.text}")
                return False, False

            data = response.json()

            # Find coin information
            coin_info = next(
                (coin for coin in data if coin.get("coin", "").upper() == symbol.upper()),
                None
            )

            if not coin_info or "networkList" not in coin_info:
                return False, False

            # Check deposit/withdrawal status across all networks
            network_list = coin_info["networkList"]
            deposit_available = any(net.get("depositEnable", False) for net in network_list)
            withdraw_available = any(net.get("withdrawEnable", False) for net in network_list)

            logger.debug(f"MEXC deposit/withdrawal status for {symbol}: {deposit_available}, {withdraw_available} ")
            return deposit_available, withdraw_available

        except Exception as e:
            print(f"Error checking status for {symbol}: {str(e)}")
            return False, False

    @staticmethod
    def check_token_exists(symbol: str):
        try:
            url = f"https://api.mexc.com/api/v3/ticker/price?symbol={symbol.upper()}"
            headers = {'Accept': 'application/json'}

            response = requests.get(url, headers=headers, timeout=5)

            # Успешный ответ - токен существует
            if response.status_code == 200:
                try:
                    data = response.json()
                    if 'price' in data:  # Проверяем наличие цены в ответе
                        return True
                except ValueError:
                    pass

            # Обработка ошибки "invalid symbol"
            if response.status_code == 400:
                try:
                    error_data = response.json()
                    if error_data.get('code') == -1121:
                        return False
                except ValueError:
                    pass

            logger.warning(f"MEXC token check failed for {symbol}: HTTP {response.status_code} | {response.text}")
            return False

        except requests.exceptions.RequestException as ex:
            logger.error(f"Network error checking token {symbol}: {str(ex)}")
            return False
        except Exception as ex:
            logger.error(f"Unexpected error checking token {symbol}: {str(ex)}")
            return False

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
