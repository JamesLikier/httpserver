import logging
from enum import Enum

class StatusCode(Enum):
    OK = (200,'OK')
    NOT_FOUND = (404,'Not Found')