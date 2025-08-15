import asyncio
import time

import aiohttp
from typing import Dict, List, Any, Optional, Callable

from Tools.scripts.nm2def import symbols
from pycares import symbol

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
    async def fetch_lbank_symbols() -> List[str]:
        url = "https://api.lbkex.com/v2/currencyPairs.do"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()

                        if data.get("msg") == "Success":
                            symbols = []
                            for item in data.get("data", []):
                                symbol = item.upper()
                                symbols.append(symbol)

                            logger.info(f"Fetched {len(symbols)} symbols from LBank")
                            return symbols
                        else:
                            logger.error(f"Error in Bitget API response: {data}")
                    else:
                        logger.error(f"Bitget API request failed with status {response.status}")

        except Exception as e:
            logger.error(f"Error fetching Bitget symbols: {e}")

        return []

    @staticmethod
    async def fetch_gate_symbols() -> List[str]:
        url = "https://api.gateio.ws/api/v4/futures/usdt/contracts"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()

                        symbols = []
                        for item in data:
                            symbol = item.get("name").upper()
                            symbols.append(symbol)

                        logger.info(f"Fetched {len(symbols)} symbols from Gate")
                        return symbols
                    else:
                        logger.error(f"Gate API request failed with status {response.status}")


        except Exception as e:
            logger.error(f"Error fetching gate symbols: {e}")

        return []

    @staticmethod
    async def fetch_bybit_symbols() -> List[str]:
        url = "https://api.bybit.com/v5/market/tickers"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        params = {"category": "linear"}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as response:
                    # logger.info(f"Response from bybit: {response}")
                    if response.status == 200:
                        json_data = await response.json()
                        symbols = []
                        for item in json_data.get("result", {}).get("list", []):
                            symbol = item.get("symbol")
                            if symbol:
                                symbols.append(symbol.upper())

                        logger.info(f"Fetched {len(symbols)} symbols from Bybit")
                        return symbols
                    else:
                        logger.error(f"BingX API request failed with status {response.status}")

        except Exception as e:
            logger.error(f"Error fetching BingX symbols: {e}")

        return []

    @staticmethod
    async def fetch_okx_symbols() -> List[str]:
        url = "https://www.okx.com/api/v5/public/mark-price"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        params = {"instType": "SWAP"}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as response:
                    # logger.info(f"Response from OKX: {response}")
                    if response.status == 200:
                        json_data = await response.json()
                        symbols = []
                        for item in json_data.get("data", []):
                            #"instId":"BTC-USDT-SWAP",
                            symbol = item.get("instId")
                            if symbol:
                                symbols.append(symbol.upper())

                        logger.info(f"Fetched {len(symbols)} symbols from Okx")
                        return symbols
                    else:
                        logger.error(f"Okx API request failed with status {response.status}")

        except Exception as e:
            logger.error(f"Error fetching Okx symbols: {e}")

        return []

    @staticmethod
    async def fetch_binx_symbols() -> List[str]:
        url = "https://open-api.bingx.com/openApi/cswap/v1/market/contracts"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        params = {"timestamp": int(time.time() * 1000)}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as response:
                    # logger.info(f"Response from BingX: {response}")
                    if response.status == 200:
                        json_data = await response.json()
                        symbols = []
                        print(json_data)
                        for item in json_data.get("data", []):
                            symbol = item.get("symbol")
                            if symbol:
                                symbols.append(symbol.upper())

                        logger.info(f"Fetched {len(symbols)} symbols from BingX")
                        return symbols
                    else:
                        logger.error(f"Bybit API request failed with status {response.status}")

        except Exception as e:
            logger.error(f"Error fetching Bybit symbols: {e}")

        return []

    @staticmethod
    async def get_all_symbols_exchange() -> Dict[str, List[str | None]]:
        """Fetch all symbols from all exchanges"""

        bitget_symbols = await ExchangeFetchSymbols.fetch_bitget_symbols()
        lbank_symbols = await ExchangeFetchSymbols.fetch_lbank_symbols()
        gate_symbols = await ExchangeFetchSymbols.fetch_gate_symbols()
        bybit_symbols = await ExchangeFetchSymbols.fetch_bybit_symbols()
        okx_symbols = await ExchangeFetchSymbols.fetch_okx_symbols()
        # bingx_symbols = await ExchangeFetchSymbols.fetch_binx_symbols()


        return {
            "bitget": bitget_symbols,
            "lbank": lbank_symbols,
            "gate": gate_symbols,
            "bybit": bybit_symbols,
            "okx": okx_symbols,
            "bingx": None,
            "mexc": None
        }
