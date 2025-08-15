from typing import Tuple


class DepositWithdrawalService:
    def __init__(self):
        self.exchange_handlers = {
            'mexc': self._check_mexc_status,
            'binance': self._check_binance_status,
            # ... другие биржи ...
        }

    async def get_status(self, exchange: str, symbol: str) -> Tuple[bool, bool]:
        handler = self.exchange_handlers.get(exchange.lower())
        if handler:
            return await handler(symbol)
        return False, False

    async def _check_mexc_status(self, symbol: str) -> Tuple[bool, bool]:
        # реализация для MEXC
        pass

    async def _check_binance_status(self, symbol: str) -> Tuple[bool, bool]:
        # реализация для Binance
        pass