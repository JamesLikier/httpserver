from dataclasses import dataclass
import logging
import socket
import threading
from collections import namedtuple
from collections.abc import MutableMapping
from typing import Any
import re

StatusCode = namedtuple("StatusCode","code text")
STATUS_CODES = {
    404: StatusCode(404,"Not Found"),
    200: StatusCode(200,"OK")
}
CONTENT_TYPES = {
    "URLEnc": "application/x-www-form-urlencoded",
    "MultiPart": "multipart/form-data"
}
class IncompleteStartline(Exception):
    pass
class FormDataRequired(Exception):
    pass

def partitions(line: str | bytes, sep: str | bytes):
    start,_,end = line.partition(sep)
    while(len(start) > 0):
        yield start
        start,_,end = end.partition(sep)

class HTTPBase():
    def __init__(self,
                httpvers: str = "HTTP/1.1",
                body: str | bytes | None = None,
                headers: dict | None = None,
                cookies: dict | None = None,
                sock: socket.socket | None = None):
        self.httpvers = httpvers
        self.body = body
        self.headers = headers or dict()
        self.cookies = cookies or dict()
        self.sock = sock

    def formatStartline(self):
        raise NotImplementedError

    def formatHeaders(self):
        headerlines = [f'{k}: {v}\r\n'.encode() for k,v in self.headers.items()]
        return b''.join(headerlines)
    
    def formatCookies(self):
        raise NotImplementedError
    
    def formatBody(self):
        return self.body if isinstance(self.body, bytes) else (self.body or '').encode()
    
    def format(self):
        raise NotImplementedError

    def send(self, sock: socket.socket | None = None):
        sock = sock or self.sock
        if sock is not None:
            sock.send(self.format())

class Response(HTTPBase):
    def __init__(self,
                statuscode: StatusCode = STATUS_CODES[200],
                httpvers: str = "HTTP/1.1",
                body: str | bytes | None = None,
                headers: dict | None = None,
                cookies: dict | None = None,
                sock: socket.socket | None = None):
        super().__init__(httpvers=httpvers,
                        body=body,
                        headers=headers,
                        cookies=cookies,
                        sock=sock)
        self.statuscode = statuscode
    
    def formatStartline(self):
        return f'{self.httpvers} {self.statuscode.code} {self.statuscode.text}\r\n'.encode()

    def formatCookies(self):
        cookielines = [f'Set-Cookie: {k}={v}\r\n'.encode() for k,v in self.cookies.items()]
        return b''.join(cookielines)
    
    def format(self):
        sl = self.formatStartline()
        h = self.formatHeaders()
        if "Content-Length" not in self.headers and self.body is not None:
            h+= (f'Content-Length: {len(self.body)}\r\n').encode()
        c = self.formatCookies()
        b = self.formatBody()
        return sl + h + c + b'\r\n' + b

@dataclass
class FormData():
    name: str = ""
    value: bytes | str | None = b''
    contentType: str | None = None
    filename: str | None = None

    def asStr(self) -> str:
        if isinstance(self.value,str):
            return self.value
        elif isinstance(self.value,bytes):
            return self.value.decode()
        elif isinstance(self.value,int):
            return str(self.value)
    def asBytes(self) -> bytes:
        if isinstance(self.value,str):
            return self.value.encode()
        elif isinstance(self.value,bytes):
            return self.value
        elif isinstance(self.value,int):
            return (str(self.value)).encode()
    def asBool(self) -> bool:
        return self.asBytes() == b'True'
    def asInt(self) -> int:
        if isinstance(self.value,str):
            return int(self.value)
        elif isinstance(self.value,bytes):
            return int(self.value.decode())
        elif isinstance(self.value,int):
            return self.value
    def formatURLEnc(self) -> bytes:
        return f"{self.name}=".encode() + self.asBytes()
    def formatMultiPart(self) -> bytes:
        header = f'Content-Disposition: form-data; name="{self.name}"'
        if self.filename is not None:
            header += f'; filename="{self.filename}"'
        if self.contentType is not None:
            header += f'\r\nContent-Type: {self.contentType}'
        return header.encode() + b'\r\n\r\n' + self.asBytes()

class Form(MutableMapping):
    def __init__(self, contentType: str = CONTENT_TYPES["URLEnc"],
                boundary: bytes | str | None = None):
        self.contentType = contentType
        self.boundary = boundary
        self._data = dict()
    def __getitem__(self,key) -> Any:
        return self._data[key]
    def __setitem__(self,key,value):
        if not isinstance(value,FormData):
            raise FormDataRequired
        self._data[key] = value
    def __delitem__(self,key):
        del self._data[key]
    def __iter__(self):
        return iter(self._data)
    def __len__(self) -> int:
        return len(self._data)
    def boundaryAsBytes(self) -> bytes:
        if isinstance(self.boundary,str):
            return self.boundary.encode()
        else:
            return self.boundary
    def fromURLEncStr(data: str) -> 'Form':
        f = Form(contentType=CONTENT_TYPES["URLEnc"])
        for part in partitions(data,'&'):
            k,_,v = part.partition('=')
            f[k] = FormData(name=k,value=v)
        return f
    def fromMultiPartBytes(data: bytes, boundary: bytes | str) -> 'Form':
        boundary = boundary if isinstance(boundary,bytes) else boundary.encode()
        f = Form(contentType=CONTENT_TYPES["MultiPart"],
                boundary=boundary)
        ##per http spec, boundary is preceeded with "--"
        boundary = b'--' + boundary
        CRLF = b'\r\n'

        _,_,data = data.partition(boundary)
        ##per http spec, boundary must always be preceeded with CRLF,
        ##and that the CRLF should be included as part of the boundary
        for part in partitions(data,CRLF+boundary):
            ##per http spec, terminal boundary has trailing "--" in addition
            ##to preceeding "--"
            if part.startswith(b'--'):
                ##we have found our terminal boundary
                break
            ##per http spec, header is signaled as ending with double CRLF.  Body is optional.
            header,_,body = part.partition(CRLF+CRLF)
            ##per http spec, headers are in USASCII encoding.
            header = header.decode()

            match: re.Match
            match = re.search('Content-Disposition: form-data;\s?name="([^"]*)"',header)
            name = match.group(1) if match is not None else ""

            match = re.search('filename="([^"]*)"',header)
            filename = match.group(1) if match is not None else None

            match = re.search('Content-Type: ([^;\r\n]+)',header)
            contenttype = match.group(1) if match is not None else None

            f[name] = FormData(name=name,value=body,contentType=contenttype,filename=filename)
        return f
    def format(self) -> bytes:
        if self.contentType == CONTENT_TYPES['URLEnc']:
            return b'&'.join([fd.formatURLEnc() for fd in self._data.values()])
        elif self.contentType == CONTENT_TYPES['MultiPart']:
            boundary = b'--' + self.boundaryAsBytes()
            data = b''
            if len(self._data) > 0:
                data = boundary + b'\r\n' + (b'\r\n' + boundary + b'\r\n').join([fd.formatMultiPart() for fd in self._data.values()]) + b'\r\n' + boundary + b'--\r\n'
            return data
        return b''

class Request(HTTPBase):
    def __init__(self,
                method: str = "",
                uri: str = "",
                form: Form | None = None,
                raw: bytes | None = None,
                httpvers: str = "HTTP/1.1",
                body: str | bytes | None = None,
                headers: dict | None = None,
                cookies: dict | None = None,
                sock: socket.socket | None = None):
        super().__init__(httpvers=httpvers,
                        body=body,
                        headers=headers,
                        cookies=cookies,
                        sock = sock)
        self.method = method
        self.uri = uri
        self.form = form or Form()
        self.raw = raw
    
    def formatStartline(self) -> bytes:
        if self.method == '' or self.uri == '':
            raise IncompleteStartline
        return (f'{self.method} {self.uri} {self.httpvers}\r\n').encode()

    def formatCookies(self) -> bytes:
        fcookies = ' '.join([f'{k}={v};' for k,v in self.cookies.items()])
        if len(fcookies) > 0:
            return (f'Cookie: {fcookies}\r\n').encode()
        return b''
    
    def formatBody(self) -> bytes:
        body = self.body or self.form or None
        if body is not None:
            if isinstance(body,bytes):
                return body
            elif isinstance(body,str):
                return body.encode()
            elif isinstance(body,Form):
                return body.format()
        return b''
    
    def format(self) -> bytes:
        sl = self.formatStartline()
        h = self.formatHeaders()
        c = self.formatCookies()
        b = self.formatBody()
        cl = b''
        if 'Content-Length' not in self.headers and len(b) > 0:
            cl = (f'Content-Length: {len(b)}\r\n').encode()
        return sl + h + cl + c + b'\r\n' + b
    
    def fromBytes(data: bytes) -> 'Request':
        ##per http spec, header and bytes are separated by 2 CRLF
        headerbytes,_,bodybytes = data.partition(b'\r\n\r\n')

        ##per http spec, header is in USASCII encoding
        headerstr = headerbytes.decode()

        ##per http spec, first line is always startline
        startline,_,headerstr = headerstr.partition('\r\n')
        m = re.match("([^\s]+) ([^\s]+) ([^\s]+)",startline)
        method = m.group(1)
        uri = m.group(2)
        httpvers = m.group(3)

        ##per http spec, the rest of this section is all headers
        headers = dict()
        cookies = dict()
        for h in partitions(headerstr,'\r\n'):
            hkey,_,hval = h.partition(': ')
            if hkey == "Cookie":
                for c in partitions(hval,'; '):
                    c = c.strip(';')
                    ckey,_,cval = c.partition('=')
                    cookies[ckey] = cval
            else:
                headers[hkey] = hval
        form = None
        if 'Content-Type' in headers:
            m = re.match("([^;]+);\s?boundary=(.*)",headers["Content-Type"])
            if m is not None:
                ct = m.group(1)
                b = m.group(2)
                if ct == CONTENT_TYPES['MultiPart']:
                    form = Form.fromMultiPartBytes(bodybytes,b)
            elif headers['Content-Type'] == CONTENT_TYPES['URLEnc']:
                form = Form.fromURLEncStr(bodybytes.decode())
        body = bodybytes
        
        return Request(method=method,uri=uri,httpvers=httpvers,headers=headers,
                        cookies=cookies,body=body,form=form,raw=data)

    def fromSocket(sock: socket.socket) -> 'Request':
        recvsize = 1024
        data = sock.recv(recvsize)
        ##per http spec, headers continue until 2 CRLF
        hsepIndex = data.find(b'\r\n\r\n')
        ##while we don't find 2 CRLF in our data, get more data
        while hsepIndex == -1:
            data += sock.recv(recvsize)
            hsepIndex = data.find(b'\r\n\r\n')
        m = re.search(b'Content-Length: ([^\r\n]+)',data)
        if m is not None:
            cl = int(m.group(1))
            while((len(data) - (hsepIndex + 4)) < cl):
                data += sock.recv(recvsize)
        return Request.fromBytes(data)

class Server():
    def __init__(self,addr: str, port: int):
        self.addr = addr
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listenthread = None
        self.listening = False
        self.handlers = dict()
        self.statichandlers = dict()
        self.handler404 = Server.handler404

    def handler404(req: Request, match: re.Match, sock: socket.socket):
        resp = Response(sock=sock)
        resp.statuscode = STATUS_CODES[404]
        resp.send()
    
    def register404(self,func):
        self.handler404 = func
        return func
    
    def register(self, methods: list, uriRegex: str):
        def inner(func):
            for method in methods:
                if method not in self.handlers:
                    self.handlers[method] = dict()
                self.handlers[method][re.compile(uriRegex)] = func
            return func
        return inner
    
    def registerstatic(self, uriRegex: str):
        def inner(func):
            self.statichandlers[re.compile(uriRegex)] = func
            return func
        return inner

    def dispatch(self, req: Request, sock: socket.socket):
        handler = None
        m = None
        if req.method in self.handlers:
            for uriRegex in self.handlers[req.method].keys():
                uriRegex: re.Pattern
                m = uriRegex.match(req.uri)
                if m is not None:
                    handler = self.handlers[req.method][uriRegex]
                    break
        if handler is None:
            for uriRegex in self.statichandlers.keys():
                uriRegex: re.Pattern
                m = uriRegex.match(req.uri)
                if m is not None:
                    handler = self.statichandlers[uriRegex]
                    break
        handler = handler or Server.handler404
        handler(req, m, sock)

    def accept(self,conn):
        sock = conn[0]
        req = Request.fromSocket(sock)
        req.socket = sock
        self.dispatch(req,sock)
        sock.close()

    def listen(self):
        self.socket.bind((self.addr, self.port))
        self.socket.listen()
        while self.listening:
            conn = self.socket.accept()
            threading.Thread(target=self.accept,args=(conn,),daemon=True).start()
        self.socket.close()

    def start(self):
        if not self.listening:
            self.listening = True
            self.listenthread = threading.Thread(target=self.listen)
            self.listenthread.start()