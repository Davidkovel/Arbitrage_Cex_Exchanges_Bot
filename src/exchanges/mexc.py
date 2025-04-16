import json
from typing import Dict, Any, Callable

from src.exchanges.exchange import Exchange
from src.exchanges.ws.websocket import ExchangeWebSocketBase
from src.utils.logger import logger


class MexcWebSocket(ExchangeWebSocketBase):
    def __init__(self, callback: Callable[[str, Dict[str, Any]], None]):
        self.sub_msg = {
            "method": "sub.ticker",
            "param": {
                "symbol": "RADAR_USDT"
            }
        }

        super().__init__(callback)
        self.uri = "wss://contract.mexc.com/edge"
        self.exchange_name = "MEXC"


    async def run(self):
        await self.run_websocket()

    #
    # async def subscribe_ticker(self):
    #     """Подписка на тикер с проверкой формата"""
    #     sub_msg = {
    #         "method": "sub.ticker",
    #         "param": {
    #             "symbol": "RADAR_USDT"
    #         }
    #     }
    #
    #     try:
    #         await self.websocket.send(json.dumps(sub_msg))
    #     except Exception as e:
    #         logger.error(f"{self.exchange_name} subscribe error: {e}")

    def _process_message(self, data: Dict[str, Any]):
        if 'data' in data:
            # Нормализация символа (удаление _USDT если есть)
            symbol = data['data'].get('symbol', '').replace('_USDT', '')
            self.callback(self.exchange_name, {'symbol': symbol, 'data': data['data']})
