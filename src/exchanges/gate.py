import asyncio
import json
import time
from typing import Dict, Any, List, Tuple

import requests
import websockets
from aiohttp import ClientSession

from src.exchanges.ws.websocket import Exchange
from src.utils.Normalizer import NormalizerSymbolsExchanges
from src.utils.logger import logger


class GateExchange(Exchange):
    def __init__(self):
        """Implementation for MEXC exchange"""
        super().__init__("GATE")
        self.ws_url = "wss://fx-ws.gateio.ws/v4/ws/usdt"
        self.rest_url = "https://api.gateio.ws/api/v4/futures/tickers"

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
            params = {"contract": symbol}
            async with self.session.get(self.rest_url, params=params) as resp:
                data = await resp.json()
                return float(data[0]['last_price'])
        except Exception as e:
            logger.error(f"Gate.io price fetch error: {e}")
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
                "time": int(time.time()),
                "channel": "futures.tickers",
                "event": "subscribe",
                "payload": symbols
            }
            await self.websocket.send(json.dumps(subscription))
            self.available_pairs.add(symbol)
        logger.info(f"{self.exchange_name} subscribed to all tickers")

    async def _process_message(self, data: Dict[str, Any]):
        """Process incoming MEXC websocket messages"""
        try:
            if data.get("event") == "update" and data.get("channel") == "futures.tickers":
                for ticker in data.get("result", []):
                    try:
                        symbol = ticker.get("contract", "").upper()
                        formatted_symbol = await NormalizerSymbolsExchanges.normalize_symbol('gate', symbol)
                        price = float(ticker.get("last", 0))
                        timestamp = data.get("time_ms", 0) / 1000

                        if formatted_symbol and price:
                            self.prices[formatted_symbol] = price
                            self.notify_price_update(formatted_symbol, price, timestamp)
                    except (ValueError, TypeError) as e:
                        logger.error(f"Ошибка обработки тикера {ticker.get('contract')}: {e}")
        except Exception as ex:
            logger.error(f"Gate process message error {ex}")
            pass

            # logger.error(f"[MEXC] Message processing failed: {ex}")
            logger.debug(f"[GATE] Raw message that failed: {json.dumps(data)}")

    @staticmethod
    def get_deposit_withdrawal_status(symbol: str) -> Tuple[bool, bool]:
        """
        Синхронная проверка статуса депозитов и withdrawals для Gate.io
        :param symbol: Символ криптовалюты (например "BTC")
        :return: (deposit_available: bool, withdrawal_available: bool)
        """
        try:
            symbol_without_usdt = NormalizerSymbolsExchanges.normalize_without_usdt_symbol(symbol)
            url = "https://api.gateio.ws/api/v4/wallet/currency_chains"
            params = {'currency': symbol_without_usdt}

            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }

            response = requests.get(url, headers=headers, params=params)

            if response.status_code != 200:
                logger.error(f"Gate.io API error: HTTP {response.status_code}")
                logger.error(f"Response: {response.text} |{response.url}")
                return False, False

            data = response.json()
            deposit_open = False
            withdrawal_open = False

            for chain in data:
                # Проверяем статус для каждой цепи
                if chain.get('is_deposit_disabled', 1) == 0:
                    deposit_open = True
                if chain.get('is_withdraw_disabled', 1) == 0:
                    withdrawal_open = True

                # Прерываем цикл если оба статуса найдены
                if deposit_open and withdrawal_open:
                    break

            return deposit_open, withdrawal_open

        except Exception as ex:
            logger.error(f"Gate deposit/withdrawal status error: {ex}")
            return False, False

    async def send_ping(self):
        await asyncio.sleep(10)
        if self.websocket:
            await self.websocket.send(json.dumps({"method": "ping"}))

    async def check_volume(self):
        """Check volume for the given symbols"""
        pass

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
