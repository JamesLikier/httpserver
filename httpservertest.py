import unittest
from httpserver import Header

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