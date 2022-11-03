from abc import ABC, abstractmethod
from jlpyhttp.http import Response

class AuthHandler(ABC):
    @abstractmethod
    def validateAuth(self, username: str, password: str, resp: Response = None) -> bool:
        pass

    @abstractmethod
    def setPassword(self, username: str, password: str) -> None:
        pass