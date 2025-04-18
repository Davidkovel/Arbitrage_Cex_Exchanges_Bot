import asyncio
import aiohttp
from typing import Dict, List, Any, Optional, Callable

from src.utils.logger import logger


class ExchangeFetchSymbols:

    @staticmethod
    async def fetch_bitget_symbols(product_type: str = "umcbl") -> List[str]:
        url = "https://api.bitget.com/api/mix/v1/market/contracts"
        params = {"productType": product_type}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()

                        if data.get("code") == "00000":
                            symbols = []
                            for item in data.get("data", []):
                                base_coin = item.get("baseCoin")
                                quote_coin = item.get("quoteCoin")
                                if base_coin and quote_coin:
                                    symbol = f"{base_coin}_{quote_coin}"
                                    symbols.append(symbol)

                            logger.info(f"Fetched {len(symbols)} symbols from Bitget")
                            return symbols
                        else:
                            logger.error(f"Error in Bitget API response: {data}")
                    else:
                        logger.error(f"Bitget API request failed with status {response.status}")

        except Exception as e:
            logger.error(f"Error fetching Bitget symbols: {e}")

        return []

    @staticmethod
    async def get_all_symbols_exchange() -> Dict[str, List[str | None]]:
        """Fetch all symbols from all exchanges"""

        bitget_symbols = await ExchangeFetchSymbols.fetch_bitget_symbols()

        return {
            "bitget": bitget_symbols,
            "mexc": None
        }
