import unittest
from httpserver import STATUS_CODES,StatusCode
from httpserver import HTTPBase
from httpserver import Response
from httpserver import Request, Form, FormData, CONTENT_TYPES
from httpserver import IncompleteStartline

class TestSTATUSCODES(unittest.TestCase):
    def test_STATUSCODES(self):
        sc = STATUS_CODES.get(404,None)
        self.assertIsNotNone(sc)
        self.assertEqual(sc.code,404)
        self.assertEqual(sc.text,"Not Found")

        sc = STATUS_CODES.get(200,None)
        self.assertIsNotNone(sc)
        self.assertEqual(sc.code,200)
        self.assertEqual(sc.text,"OK")

class TestHTTPBase(unittest.TestCase):
    def test_init(self):
        b = HTTPBase()
        self.assertEqual(b.httpvers,"HTTP/1.1")
        self.assertIsNone(b.body)
        self.assertIsInstance(b.headers,dict)
        self.assertIsInstance(b.cookies,dict)
        self.assertIsNone(b.sock)
        params = {
            "body": None,
            "headers": None,
            "cookies": None,
            "sock": None
        }
        b = HTTPBase(**params)
        self.assertEqual(b.httpvers,"HTTP/1.1")
        self.assertIsNone(b.body)
        self.assertIsInstance(b.headers,dict)
        self.assertIsInstance(b.cookies,dict)
        self.assertIsNone(b.sock)
    def test_formatStartline(self):
        b = HTTPBase()
        self.assertRaises(Exception,b.formatStartline)
    def test_formatHeaders(self):
        b = HTTPBase()
        formattedBytes = b.formatHeaders()
        self.assertEqual(formattedBytes,b'')

        b.headers["test"] = "value"
        formattedBytes = b.formatHeaders()
        self.assertEqual(formattedBytes,b'test: value\r\n')

        b.headers["test2"] = 2
        formattedBytes = b.formatHeaders()
        self.assertEqual(formattedBytes,b'test: value\r\ntest2: 2\r\n')
    def test_formatCookies(self):
        b = HTTPBase()
        self.assertRaises(NotImplementedError,b.formatCookies)
    def test_formatBody(self):
        b = HTTPBase()
        self.assertEqual(b.formatBody(),b'')

        b.body = "test"
        self.assertEqual(b.formatBody(),b'test')
        
        b.body = b'test2'
        self.assertEqual(b.formatBody(),b'test2')
    def test_format(self):
        b = HTTPBase()
        self.assertRaises(NotImplementedError,b.format)
class TestResponse(unittest.TestCase):
    def test_init(self):
        r = Response()
        self.assertEqual(r.statuscode,STATUS_CODES[200])
    def test_formatStartline(self):
        r = Response()
        self.assertEqual(r.formatStartline(),b'HTTP/1.1 200 OK\r\n')

        r = Response(statuscode=STATUS_CODES[404])
        self.assertEqual(r.formatStartline(),b'HTTP/1.1 404 Not Found\r\n')

        r = Response(statuscode=StatusCode(9999,"test"))
        self.assertEqual(r.formatStartline(),b'HTTP/1.1 9999 test\r\n')
    def test_formatCookies(self):
        r = Response()
        self.assertEqual(r.formatCookies(),b'')

        r.cookies["key"] = "val"
        cl = b'Set-Cookie: key=val\r\n'
        self.assertEqual(r.formatCookies(),cl)

        r.cookies["key2"] = 2
        cl = b'Set-Cookie: key=val\r\nSet-Cookie: key2=2\r\n'
        self.assertEqual(r.formatCookies(),cl)
    def test_format(self):
        r = Response()
        testline = r.formatStartline() + b'\r\n'
        self.assertEqual(r.format(),testline)
        
        params = {
            "headers": {"header1": "headerval"},
            "cookies": {"cookie1": "cookieval"},
            "body": b'test'
        }
        r = Response(**params)
        startline = b'HTTP/1.1 200 OK\r\n'
        headers = b'header1: headerval\r\n'
        cookies = b'Set-Cookie: cookie1=cookieval\r\n'
        body = b'test'
        contentlength = (f'Content-Length: {len(body)}\r\n').encode()
        testline = startline + headers + contentlength + cookies + b'\r\n' + body
        self.assertEqual(r.format(),testline)
class TestRequest(unittest.TestCase):
    def test_init(self):
        r = Request()
        self.assertEqual(r.method,"")
        self.assertEqual(r.uri,"")
        self.assertIsInstance(r.form,Form)
        self.assertEqual(r.raw,None)

        params = {
            "method": "GET",
            "uri": "/test/path",
            "form": Form()
        }
        r = Request(**params)
        self.assertEqual(r.method,"GET")
        self.assertEqual(r.uri,"/test/path")
        self.assertIsInstance(r.form,Form)
    def test_formatStartline(self):
        r = Request()
        self.assertRaises(IncompleteStartline,r.formatStartline)

        r = Request(method="GET",uri="/test/path")
        testline = b'GET /test/path HTTP/1.1\r\n'
        self.assertEqual(r.formatStartline(),testline)
    def test_formatCookies(self):
        r = Request()
        self.assertEqual(r.formatCookies(),b'')
        r.cookies["TestCookie"] = "value"
        testline = b'Cookie: TestCookie=value;\r\n'
        self.assertEqual(r.formatCookies(),testline)
        r.cookies["cookie2"] = 5
        testline = b'Cookie: TestCookie=value; cookie2=5;\r\n'
        self.assertEqual(r.formatCookies(),testline)
    def test_formatBody(self):
        r = Request()
        self.assertEqual(r.formatBody(),b'')
        r.body = b'test'
        self.assertEqual(r.formatBody(),b'test')
        ##formatBody should use body over form, if both are not None
        r.form["key"] = FormData(name="key",value="value")
        self.assertEqual(r.formatBody(),b'test')

        r = Request()
        r.form["key"] = FormData(name="key",value="value")
        self.assertEqual(r.formatBody(),b"key=value")
        r.form["key2"] = FormData(name="key2",value="2")
        self.assertEqual(r.formatBody(),b"key=value&key2=2")
    def test_format(self):
        r = Request()
        self.assertRaises(IncompleteStartline,r.format)

        params = {
            "method": "GET",
            "uri": "/test/path",
        }
        r = Request(**params)
        testline = b'GET /test/path HTTP/1.1\r\n\r\n'
        self.assertEqual(r.format(),testline)

        params = {
            "method": "GET",
            "uri": "/test/path",
            "headers": {"header1": "headerval"},
            "cookies": {"cookie1": "cookieval"},
            "body": "testbody"
        }
        r = Request(**params)
        startline = b'GET /test/path HTTP/1.1\r\n'
        headers = b'header1: headerval\r\n'
        cookies = b'Cookie: cookie1=cookieval;\r\n'
        body = b'testbody'
        contentlength = (f'Content-Length: {len(body)}\r\n').encode()
        testline = startline + headers + contentlength + cookies + b'\r\n' + body
        self.assertEqual(r.format(),testline)
    def test_fromBytes(self):
        startline = b'GET /test/path HTTP/1.1\r\n'
        headers = b'header1: headerval\r\n'
        cookies = b'Cookie: cookie1=cookieval;\r\n'
        body = b'testbody'
        contentlength = (f'Content-Length: {len(body)}\r\n').encode()
        testline = startline + headers + contentlength + cookies + b'\r\n' + body
        r = Request.fromBytes(testline)
        self.assertEqual(r.method,"GET")
        self.assertEqual(r.uri,"/test/path")
        self.assertEqual(r.httpvers,"HTTP/1.1")
        self.assertEqual(r.headers["header1"],"headerval")
        self.assertEqual(r.cookies["cookie1"],"cookieval")
        self.assertEqual(r.body,body)

class TestFormData(unittest.TestCase):
    def test_init(self):
        fd = FormData()
        self.assertEqual(fd.name,"")
        self.assertEqual(fd.value,b'')
        self.assertEqual(fd.contentType,None)
        self.assertEqual(fd.filename,None)
    def test_formatURLEnc(self):
        fd = FormData(name="testFormName",value=b'testFormValue')
        testline = b'testFormName=testFormValue'
        self.assertEqual(fd.formatURLEnc(),testline)
    def test_formatMultiPart(self):
        fd = FormData(name="testFormName",value=b'testFormValue')
        testline = b'Content-Disposition: form-data; name="testFormName"\r\n\r\ntestFormValue'
        self.assertEqual(fd.formatMultiPart(),testline)

        fd = FormData(name="testFormName",value=b'testFormValue',
                    contentType="test/ContentType",filename="testFilename.txt")
        testline = b'Content-Disposition: form-data;'
        testline += b' name="testFormName"; filename="testFilename.txt"\r\n'
        testline += b'Content-Type: test/ContentType\r\n\r\ntestFormValue'
        self.assertEqual(fd.formatMultiPart(),testline)
    
class TestForm(unittest.TestCase):
    def test_init(self):
        f = Form()
        self.assertEqual(f.contentType,CONTENT_TYPES["URLEnc"])
        self.assertEqual(f.boundary,None)
    def test_fromURLEncStr(self):
        data = "name=value"
        f = Form.fromURLEncStr(data)
        self.assertEqual(f["name"].asStr(),'value')

        data = "name=value&name2=value2"
        f = Form.fromURLEncStr(data)
        self.assertEqual(f["name"].asStr(),'value')
        self.assertEqual(f["name2"].asStr(),'value2')
    def test_fromMultiPartBytes(self):
        boundary = b'##'
        databoundary = b'--'+boundary
        data = databoundary + b'\r\n'
        data += b'Content-Disposition: form-data; name="arg1"\r\n\r\n'
        data += b'value1'
        data += b'\r\n' + databoundary + b'\r\n'
        data += b'Content-Disposition: form-data; name="arg2"; filename="name.txt"\r\n'
        data += b'Content-Type: plain/text\r\n\r\n'
        data += b'value2'
        data += b'\r\n' + databoundary + b'--\r\n'
        f = Form.fromMultiPartBytes(data,boundary)
        self.assertEqual(f["arg1"].asStr(),"value1")
        self.assertEqual(f["arg1"].contentType,None)
        self.assertEqual(f["arg1"].filename,None)
        self.assertEqual(f["arg2"].asStr(),"value2")
        self.assertEqual(f["arg2"].contentType,"plain/text")
        self.assertEqual(f["arg2"].filename,"name.txt")
    def test_format(self):
        f = Form(contentType=CONTENT_TYPES["URLEnc"])
        fd = FormData(name="testName",value=b'testValue')
        f[fd.name] = fd
        fd2 = FormData(name="testName2",value=b'testValue2')
        f[fd2.name] = fd2
        testline = fd.formatURLEnc() + b'&' + fd2.formatURLEnc()
        self.assertEqual(f.format(),testline)
        ##todo: contentType=CONTENT_TYPES["MultiPart"]
        f.contentType = CONTENT_TYPES["MultiPart"]
        f.boundary = b'##'
        f2 = Form.fromMultiPartBytes(f.format(),f.boundary)
        self.assertEqual(f["testName"].name,f2["testName"].name)
        self.assertEqual(f["testName"].value,f2["testName"].value)
        self.assertEqual(f["testName2"].name,f2["testName2"].name)
        self.assertEqual(f["testName2"].value,f2["testName2"].value)