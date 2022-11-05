from abc import ABC, abstractmethod
from jlpyhttp.http import Response

class AuthHandler(ABC):
    @abstractmethod
    def validateAuth(self, username: str, password: str) -> tuple[bool,int]:
        pass

    @abstractmethod
    def setPassword(self, username: str, password: str) -> None:
        pass