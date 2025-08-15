class NormalizerSymbolsExchanges:
    @staticmethod
    async def normalize_symbol(exchange: str, symbol: str) -> str:
        """
        Normalize the symbol based on the exchange.
        """
        if exchange == "bitget":
            return symbol.replace("_", "").replace("-", "").upper()
        elif exchange == "mexc":
            return symbol.replace("_", "").replace("-", "").upper()
        elif exchange == "gate":
            return symbol.replace("_", "").replace("-", "").upper()
        elif exchange == "bingx":
            return symbol.replace("_", "").replace("-", "").upper()
        elif exchange == "bybit":
            return symbol.replace("_", "").replace("-", "").upper()
        elif exchange == "okx":
            return symbol.replace("_", "").replace("-", "").upper()
            # parts = symbol.split("-")
            # if len(parts) >= 2:
            #     return f"{parts[0]}{parts[1]}".upper()
            # return symbol.upper()

        else:
            raise ValueError(f"Unknown exchange: {exchange}")

    @staticmethod
    def normalize_without_usdt_symbol(symbol: str) -> str:
        """
        Normalize the symbol by removing 'USDT' and converting to uppercase.
        """
        if symbol.endswith("USDT"):
            return symbol[:-4].upper()
        return symbol.upper()
