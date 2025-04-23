import asyncio
import json
import sys
import platform
from typing import Dict, Any, List
from venv import logger

from src.commons.fetch_symbols import ExchangeFetchSymbols
from src.exchanges.bitget import BitgetExchange
from src.exchanges.mexc import MexcExchange
from src.services.find_spread_service import SpreadService

if platform.system() == 'Windows':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


async def main():
    service = SpreadService(min_spread_percent=1.0)

    mexc = MexcExchange()
    bitget = BitgetExchange()

    service.add_exchange(mexc)
    service.add_exchange(bitget)

    try:
        await service.start()

        while True:
            await asyncio.sleep(6)
    except KeyboardInterrupt:
        logger.info("Stopping service...")
        await service.stop()
    except Exception as ex:
        logger.error(f"Error in main: {ex}")


# async def test():
#     w = MexcExchange()
#     await w.connect()
#     await w.subscribe(['BTC_USDT'])
#
#     for _ in range(55):
#         if 'BTC' in w.prices:
#             print(f"Current BTC price: {w.prices['BTC']}")
#         await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
