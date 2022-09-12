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

class TestFormData(unittest.TestCase):
    def test_init(self):
        raise Exception
    def test_formatURLEnc(self):
        raise Exception
    def test_formatMultiPart(self):
        raise Exception
    def test_asStr(self):
        raise Exception
    def test_asBytes(self):
        raise Exception
    def test_asBool(self):
        raise Exception
    def test_asInt(self):
        raise Exception
    
class TestForm(unittest.TestCase):
    def test_init(self):
        raise Exception
    def test_addAndGetField(self):
        raise Exception
    def test_fromURLEncStr(self):
        raise Exception
    def test_fromMultiPartBytes(self):
        raise Exception
    def test_format(self):
        raise Exception