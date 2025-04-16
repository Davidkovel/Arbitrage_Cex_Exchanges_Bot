import asyncio
import json
from typing import Dict, Any

from src.exchanges.mexc import MexcWebSocket
from src.services.find_spread_service import PriceAggregator


async def main():
    aggregator = PriceAggregator()

    mexc = MexcWebSocket(callback)
    # bybit = BybitWebSocket(callback)  # Реализовать аналогично
    # gate = GateWebSocket(callback)    # Реализовать аналогично

    await mexc.connect()
    # await bybit.connect()
    # await gate.connect()

    pairs = ['BTC_USDT', 'ETH_USDT', 'SOL_USDT']  # и другие интересующие пары

    for pair in pairs:
        await mexc.subscribe_ticker(pair)
        # await bybit.subscribe_ticker(pair)
        # await gate.subscribe_ticker(pair)


    aggregator.run_find_spread_service()

    # await bybit.subscribe_ticker(pair)
    # await gate.subscribe_ticker(pair)


async def test_main():
    def callback(exchange, data):
        print(f"\n--- Получены данные от {exchange} ---")
        print("Символ:", data['symbol'])
        print("Данные:", json.dumps(data['data'], indent=2))
        print("--- Конец данных ---\n")

    mexc = MexcWebSocket(callback)

    try:
        print("Попытка подключения...")

        await mexc.run_websocket()

        # Ждем данные в течение 30 секунд
        print("Ожидание данных (30 сек)...")
        await asyncio.sleep(30)

    except Exception as e:
        print("Ошибка в test_main:", e)
    finally:
        print("Отключение...")
        await mexc.disconnect()


if __name__ == "__main__":
    print("Запуск теста...")
    asyncio.run(main())





# import asyncio
# import json
# from typing import Dict, Any, Callable, Set, Optional
# import websockets
# from collections import defaultdict
#
# from src.utils.logger import logger
#
#
# class ExchangeWebSocketBase:
#     def __init__(self):
#         self.uri = "wss://contract.mexc.com/edge"
#         self.websocket = None
#         self.subscriptions = set()
#         self._running = False
#         self.exchange_name = "base"
#
#
#     async def connect(self):
#         """Установка соединения с WebSocket"""
#         try:
#             self.websocket = await websockets.connect(
#                 self.uri,
#             )
#             self._running = True
#             logger.info(f"{self.exchange_name} WebSocket connected successfully")
#             asyncio.create_task(self._keep_alive())
#             asyncio.create_task(self._receive_messages())
#         except Exception as e:
#             logger.error(f"{self.exchange_name} connection error: {e}")
#             await self._reconnect()
#
#     async def run_websocket(self):
#         """Запуск WebSocket клиента"""
#         if self._running:
#             return
#
#         self._running = True
#         try:
#             await self.connect()
#             await self.subscribe_ticker()
#
#             print("WebSocket started successfully")
#
#         except Exception as e:
#             self._running = False
#             raise
#
#     async def _keep_alive(self):
#         """Поддержание соединения"""
#         while self._running:
#             await asyncio.sleep(10)
#             await self.send_ping()
#
#     async def send_ping(self):
#         """Отправка ping"""
#         if self.websocket:
#             await self.websocket.send(json.dumps({"method": "ping"}))
#
#     async def _reconnect(self):
#         """Переподключение с задержкой"""
#         await asyncio.sleep(5)
#         logger.info(f"{self.exchange_name} attempting to reconnect...")
#         await self.connect()
#
#     async def subscribe_ticker(self):
#         """Абстрактный метод подписки на тикер"""
#         sub_msg = {
#             "method": "sub.tickers",
#             "param": {
#                 "symbol": "RADAR_USDT"
#             }
#         }
#
#
#         try:
#             await self.websocket.send(json.dumps(sub_msg))
#         except Exception as e:
#             logger.error(f"{self.exchange_name} subscribe error: {e}")
#
#     async def _receive_messages(self):
#         """Основной цикл приема сообщений"""
#         while self._running:
#             try:
#                 message = await self.websocket.recv()
#                 print(message)
#                 try:
#                     data = json.loads(message)
#                     self._process_message(data)
#                 except json.JSONDecodeError:
#                     logger.error(f"{self.exchange_name} non-JSON message: {message}")
#             except websockets.exceptions.ConnectionClosed:
#                 logger.error(f"{self.exchange_name} connection closed, reconnecting...")
#                 await self._reconnect()
#                 break
#             except Exception as e:
#                 logger.error(f"{self.exchange_name} receive error: {e}")
#                 await self._reconnect()
#                 break
#
#     def _process_message(self, data: Dict[str, Any]):
#         """Обработка сообщения от биржи"""
#         raise NotImplementedError
#
#     async def disconnect(self):
#         """Корректное отключение"""
#         self._running = False
#         if self.websocket:
#             await self.websocket.close()
#             logger.info(f"{self.exchange_name} WebSocket disconnected")
#
# async def te():
#     d = ExchangeWebSocketBase()
#     await d.run_websocket()
#     while True:
#         await asyncio.sleep(1)
#         print("Waiting...")
#
# asyncio.run(te())