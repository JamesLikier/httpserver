import unittest
from httpserver import Header, HeaderList, CookieOption

class TestHeader(unittest.TestCase):
    def test_init(self):
        ## no args should cause exception for missing args
        self.assertRaises(Exception,Header)

        ## only key should cause exception for missing args
        self.assertRaises(Exception,Header,kwargs={"key":"test"})
        self.assertRaises(Exception,Header,kwargs={"val":"1"})

        ## test proper creation
        key = "test"
        val = "1"
        h = Header(key=key,val=val)
        self.assertEqual(h.key,key)
        self.assertEqual(h.val,val)

        key = "test"
        val = 1
        h = Header(key=key,val=val)
        self.assertEqual(h.key,key)
        self.assertEqual(h.val,val)

    def test_asStr(self):
        key = "test"
        val = "1"
        h = Header(key=key, val=val)
        self.assertEqual(h.asStr(),val)
    
        key = "test"
        val = 1
        h = Header(key=key, val=val)
        self.assertEqual(h.asStr(),str(val))

    def test_asInt(self):
        key = "test"
        val = "1"
        h = Header(key=key, val=val)
        self.assertEqual(h.asInt(),int(val))
    
        key = "test"
        val = 1
        h = Header(key=key, val=val)
        self.assertEqual(h.asInt(),val)

    def test_format(self):
        key = "test"
        val = 1
        h = Header(key=key, val=val)
        expected = f'{key}: {val}\r\n'.encode()
        self.assertEqual(h.format(),expected)

        key = "test"
        val = "1"
        h = Header(key=key, val=val)
        expected = f'{key}: {val}\r\n'.encode()
        self.assertEqual(h.format(),expected)

        key = "test"
        val = "1; boundary=val"
        h = Header(key=key, val=val)
        expected = f'{key}: {val}\r\n'.encode()
        self.assertEqual(h.format(),expected)

class TestHeaderList(unittest.TestCase):
    def test_init(self):
        hl = HeaderList()
        self.assertIsNotNone(hl._data)

    def test_addAndGetHeader(self):
        hl = HeaderList()
        hl.addHeader("testkey","testval")
        hl.addHeader("testkey2",1)

        h = hl.getHeader("testkey")
        self.assertEqual(h.key,"testkey")
        self.assertEqual(h.val,"testval")

        h = hl.getHeader("testkey2")
        self.assertEqual(h.key,"testkey2")
        self.assertEqual(h.val,1)

        h = hl.getHeader("doesnotexist")
        self.assertIsNone(h)

    def test_headers(self):
        hl = HeaderList()
        
        contents = [h for h in hl.headers()]
        self.assertEqual(len(contents),0)

        hl.addHeader("k1","one")
        hl.addHeader("k2",2)

        contents = [h for h in hl.headers()]
        self.assertEqual(len(contents),2)

    def test_format(self):
        hl = HeaderList()

        formatBytes = hl.format()
        self.assertEqual(formatBytes,b'')

        hl.addHeader("k1","one")
        formatBytes = hl.format()
        self.assertEqual(formatBytes,b'k1: one\r\n')

        hl.addHeader("k2",2)
        formatBytes = hl.format()
        self.assertEqual(formatBytes,b'k1: one\r\nk2: 2\r\n')

        hl.addHeader("k3","3; op=val")
        formatBytes = hl.format()
        self.assertEqual(formatBytes,b'k1: one\r\nk2: 2\r\nk3: 3; op=val\r\n')

class TestCookieOption(unittest.TestCase):
    def test_init(self):
        self.assertRaises(Exception,CookieOption)
        self.assertRaises(Exception,CookieOption,key="key")
        self.assertRaises(Exception,CookieOption,val="val")

        key = "key"
        val = "val"
        co = CookieOption(key,val)
        self.assertEqual(co.key,key)
        self.assertEqual(co.val,val)

        key = "key"
        val = 1
        co = CookieOption(key,val)
        self.assertEqual(co.key,key)
        self.assertEqual(co.val,val)

    def test_format(self):
        key = "key"
        val = "val"
        co = CookieOption(key,val)
        self.assertEqual(co.format(),f'{key}={val}')

        key = "key"
        val = 1
        co = CookieOption(key,val)
        self.assertEqual(co.format(),f'{key}={val}')