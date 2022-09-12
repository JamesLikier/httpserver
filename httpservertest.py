import unittest
from httpserver import StatusCode

class TestStatusCode(unittest.TestCase):
    def test_StatusCode(self):
        raise Exception

class TestHTTPBase(unittest.TestCase):
    def test_init(self):
        raise Exception
    def test_formatHeaders(self):
        raise Exception

class TestResponse(unittest.TestCase):
    def test_init(self):
        raise Exception
    def test_formatCookies(self):
        raise Exception
    def test_format(self):
        raise Exception

class TestRequest(unittest.TestCase):
    def test_init(self):
        raise Exception
    def test_formatCookies(self):
        raise Exception
    def test_format(self):
        raise Exception
    def test_fromBytes(self):
        raise Exception
    def test_fromSocket(self):
        raise Exception