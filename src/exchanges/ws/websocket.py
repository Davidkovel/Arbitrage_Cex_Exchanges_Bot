import asyncio
import json
from typing import Dict, Any, Callable, Set, Optional
import websockets
from collections import defaultdict

from src.utils.logger import logger


class ExchangeWebSocketBase:
    def __init__(self, callback: Callable[[str, Dict[str, Any]], None]):
        self.uri = "wss://contract.mexc.com/edge"
        self.websocket = None
        self.subscriptions = set()
        self._running = False
        self.callback = callback
        self.exchange_name = "base"

    async def connect(self):
        """Установка соединения с WebSocket"""
        try:
            self.websocket = await websockets.connect(
                self.uri,
                ping_interval=15,
                ping_timeout=10,
                close_timeout=5
            )
            self._running = True
            logger.info(f"{self.exchange_name} WebSocket connected successfully")
            asyncio.create_task(self._keep_alive())
            asyncio.create_task(self._receive_messages())
        except Exception as e:
            logger.error(f"{self.exchange_name} connection error: {e}")
            await self._reconnect()

    async def run_websocket(self):
        """Запуск WebSocket клиента"""
        if self._running:
            return

        self._running = True
        try:
            await self.connect()
            await self.subscribe_ticker()

            print("WebSocket started successfully")

        except Exception as e:
            self._running = False
            raise

    async def _keep_alive(self):
        """Поддержание соединения"""
        while self._running:
            await asyncio.sleep(10)
            await self.send_ping()

    async def send_ping(self):
        """Отправка ping"""
        if self.websocket:
            await self.websocket.send(json.dumps({"method": "ping"}))

    async def _reconnect(self):
        """Переподключение с задержкой"""
        await asyncio.sleep(5)
        logger.info(f"{self.exchange_name} attempting to reconnect...")
        await self.connect()

    async def subscribe_ticker(self, symbol: str):
        """Абстрактный метод подписки на тикер"""
        sub_msg = {
            "method": "sub.ticker",
            "param": {
                "symbol": symbol
            }
        }

        try:
            await self.websocket.send(json.dumps(sub_msg))
        except Exception as e:
            logger.error(f"{self.exchange_name} subscribe error: {e}")

    async def _receive_messages(self):
        """Основной цикл приема сообщений"""
        while self._running:
            try:
                message = await self.websocket.recv()
                print(message)
                try:
                    data = json.loads(message)
                    self._process_message(data)
                except json.JSONDecodeError:
                    logger.error(f"{self.exchange_name} non-JSON message: {message}")
            except websockets.exceptions.ConnectionClosed:
                logger.error(f"{self.exchange_name} connection closed, reconnecting...")
                await self._reconnect()
                break
            except Exception as e:
                logger.error(f"{self.exchange_name} receive error: {e}")
                #await self._reconnect()
                break

    # def _process_message(self, data: Dict[str, Any]):
    #     """Обработка полученного сообщения"""
    #     if data["data"] == "sucess":
    #         print("Success")

    async def get_price_coin_futures(self, data: Dict[str, Any]):
        """Получение цены монеты"""
        if 'data' in data:
            # Нормализация символа (удаление _USDT если есть)
            symbol = data['data'].get('symbol', '').replace('_USDT', '')
            last_price = data['data'].get('lastPrice')
            self.callback(self.exchange_name, {'symbol': symbol, 'lastPrice': last_price})

    async def disconnect(self):
        """Корректное отключение"""
        self._running = False
        if self.websocket:
            await self.websocket.close()
            logger.info(f"{self.exchange_name} WebSocket disconnected")
