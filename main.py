import asyncio
import json
from typing import Dict, Any
from venv import logger

from src.exchanges.mexc import MexcExchange
from src.exchanges.ws.websocket import Exchange
from src.services.find_spread_service import SpreadService


async def main():
    service = SpreadService(min_spread_percent=0.5)

    mexc = MexcExchange()
    # bybit = BybitWebSocket(callback)  # Реализовать аналогично
    # gate = GateWebSocket(callback)    # Реализовать аналогично
    service.add_exchange(mexc)

    pairs = ['BTC_USDT', 'ETH_USDT', 'SOL_USDT']

    try:
        await service.start(pairs)

        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping service...")
        await service.stop()
    except Exception as ex:
        logger.error(f"Error in main: {ex}")



async def test():
    w = MexcExchange()
    await w.connect()
    await w.subscribe(['BTC_USDT'])

    for _ in range(55):
        if 'BTC' in w.prices:
            print(f"Current BTC price: {w.prices['BTC']}")
        await asyncio.sleep(1)
if __name__ == "__main__":
    asyncio.run(test())
