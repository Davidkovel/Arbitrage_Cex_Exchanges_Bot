from abc import abstractmethod, ABC

class Exchange(ABC):
    @abstractmethod
    async def get_futures_price(self, symbol: str):
        pass

