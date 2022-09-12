from enum import Enum
from collections import defaultdict, abc
from dataclasses import dataclass
import socket
import threading
import re
import logging

def partitionGen(line: str | bytes, sep: str | bytes):
    start,_,end = line.partition(sep)
    while(start != ('' if type(start) == str else b'')):
        yield start
        start,_,end = end.partition(sep)

@dataclass(frozen=True)
class formdata():
    name: str
    value: bytes
    contenttype: str = ""
    filename: str = None

    def formatUrlEnc(self):
        return f"{self.name}=".encode() + self.value
    
    def formatFormData(self):
        header = f'Content-Disposition: form-data; name="{self.name}"'
        if self.filename != None:
            header += f'; filename="{self.filename}"'
        if self.contenttype != "":
            header += f'\r\nContent-Type: {self.contenttype}'
        body = self.value

        return header.encode() + b'\r\n\r\n' + body + b'\r\n'
    
    def asStr(self):
        return self.value.decode()
    
    def asBytes(self):
        return self.value
    
    def asBool(self):
        return self.value == b'True'

    def asInt(self):
        return int(str(self.value.decode()))

class statuscodes(Enum):
    OK = (200,"OK")
    NOT_FOUND = (404,"Not Found")

@dataclass
class Header():
    def __init__(self, key: str, val: str | int):
        self.key = key
        self.val = val
    
    def asStr(self):
        return self.val if type(self.val) == str else str(self.val)
    
    def asInt(self):
        return self.val if type(self.val) == int else int(self.val)
    
    def format(self):
        return (f'{self.key}: {self.asStr()}\r\n').encode()

class HeaderList():
    def __init__(self):
        self._data = dict()
    
    def addHeader(self, key: str, val: str | int) -> None:
        self._data[key] = Header(key, val)
    
    def getHeader(self, key: str) -> Header | None:
        return self._data.get(key,None)
    
    def headers(self) -> abc.Iterator:
        for header in self._data.values():
            yield header
    
    def format(self):
        return b''.join([h.format() for h in self.headers()])

@dataclass
class CookieOption():
    def __init__(self, key: str, val: str | int):
        self.key = key
        self.val = val
    
    def format(self):
        return f'{self.key}={self.val if type(self.val) is str else str(self.val)};'

class CookieOptionList():
    def __init__(self):
        self._data = dict()

    def addOption(self, key: str, val: str | int) -> None:
        self._data[key] = CookieOption(key,val)

    def getOption(self, key: str) -> CookieOption | None:
        return self._data.get(key, None)

    def options(self) -> abc.Iterator:
        for option in self._data.values():
            yield option

    def format(self) -> str:
         return ' '.join([o.format() for o in self.options()])

class CookieFormatMode(Enum):
    REQUEST = 1
    RESPONSE = 2

@dataclass
class Cookie():
    def __init__(self, key: str, val: str | int):
        self.key = key
        self.val = val
        self.optionList = CookieOptionList()
    
    def asStr(self):
        return self.val if type(self.val) == str else str(self.val)
    
    def asInt(self):
        return self.val if type(self.val) == int else int(self.val)
    
    def setOption(self, key: str, val: str):
        self._options[key] = val
    
    def getOptions(self):
        return self._options
    
    def format(self,mode: CookieFormatMode = CookieFormatMode.RESPONSE):
        rebuiltOptions = '; '.join([option.format() for option in self.options])
        rebuiltOptions = ('; ' + rebuiltOptions) if rebuiltOptions != '' else ''
        if mode == CookieFormatMode.RESPONSE:
            return (f'Set-Cookie: {self.key}={self.asStr()}{rebuiltOptions}\r\n').encode()
        elif mode == CookieFormatMode.REQUEST:
            return (f'Cookie: {self.key}={self.asStr()}').encode()

class cookielist():
    def __init__(self):
        self._data = dict()
    
    def addCookie(self, key: str, val: str | int, **options) -> None:
        self._data[key] = Cookie(key,val,**options)
    
    def getCookie(self, key: str) -> Cookie:
        return self._data.get(key,None)
    
    def cookies(self):
        for cookie in self._data.values():
            yield cookie

    def format(self, mode: CookieFormatMode = CookieFormatMode.RESPONSE):
        if mode == CookieFormatMode.RESPONSE:
            return b''.join([c.format(mode=CookieFormatMode.RESPONSE) for c in self.cookies()])
        elif mode == CookieFormatMode.REQUEST:
            line = b';'.join([c.format(mode=CookieFormatMode.REQUEST) for c in self.cookies()])
            return (line + b'\r\n') if line != '' else line

    def fromHeader(line: str | bytes):
        cookies = cookielist()
        for cookieRaw in partitionGen(line if type(line) == str else str(line), ';'):
            key,_,val = cookieRaw.partition("=")
            cookies.addCookie(key,val)
        return cookies
    

class httpresponse():
    def __init__(self, httpvers = "HTTP/1.1", statuscode = statuscodes.OK, body = b'', headers=None, cookies=None):
        self.httpvers = httpvers
        self.statuscode = statuscode
        self.body = body
        self.headers = headers if headers is not None else headerlist()
        self.cookies = cookies if cookies is not None else cookielist()
    
    def format(self):
        startline = self.httpvers.encode() + f' {self.statuscode.value[0]} {self.statuscode.value[1]}\r\n'.encode()

        ##find our Content-Length header
        clHeader = self.headers.getHeader("Content-Length")
        contentLength = clHeader.val if clHeader is not None else None
        ## if we don't find it, add it and set it to our body length
        if contentLength == None:
            self.headers.addHeader("Content-Length",len(self.body))
        rebuiltHeaders = self.headers.format()
        rebuiltCookies = self.cookies.format(mode=CookieFormatMode.RESPONSE)

        bodybytes = self.body if type(self.body) == bytes else self.body.encode()

        return startline + rebuiltHeaders + rebuiltCookies + b'\r\n' + bodybytes

    def send(self, sock: socket.socket):
        sock.send(self.format())

class httpform():
    def __init__(self, contenttype="", boundary=b'', data=None):
        self.contenttype = contenttype
        self.boundary = boundary
        self.data = defaultdict(lambda: formdata("UNDEFINED",b''), data if data != None else dict())
        
    def format(self):
        if self.contenttype == "multipart/form-data":
            start = self.boundary + b'\r\n'
            end = self.boundary+b'--\r\n'
            data = []
            for k,v in self.data.items():
                v: formdata
                data.append(v.formatFormData())
            return start + (self.boundary+b'\r\n').join(data) + end
        elif self.contenttype == "application/x-www-form-urlencoded":
            data = []
            for k,v in self.data.items():
                v: formdata
                data.append(v.formatUrlEnc())
            return b'&'.join(data)
        else:
            return b''
    
    def parseurlencoded(data: bytes):
        contenttype = "application/x-www-form-urlencoded"
        parsed = dict()

        bsep = b"&"
        kvsep = b"="

        keyvalpair,foundsep,remainder = data.partition(bsep)
        while foundsep != b"":
            key,_,val = keyvalpair.partition(kvsep)
            key = key.decode()
            parsed[key] = formdata(key,val)
            keyvalpair,foundsep,remainder = remainder.partition(bsep)
        key,_,val = keyvalpair.partition(kvsep)
        key = key.decode()
        parsed[key] = formdata(key,val)

        return httpform(contenttype=contenttype,data=parsed)

    def parsemultipart(data: bytes, boundary: bytes):
        formcontenttype = "multipart/form-data"
        clrf = b'\r\n'
        boundary = b'--' + boundary

        blocks = dict()
        blockbytes,foundboundary,bodybytesremainder = data.partition(boundary)
        while foundboundary == boundary:
            headername = ""
            filename = None
            contenttype = ""
            #if blockbytes == b'', then we have encountered the intial boundary
            if blockbytes == b'':
                blockbytes,foundboundary,bodybytesremainder = bodybytesremainder.partition(boundary)
                continue

            #headers continue until double CLRF
            headerbytes,_,bodybytes = blockbytes.partition(clrf + clrf)
            #trim \r\n from bodybytes
            bodybytes = bodybytes[:-2]

            #treat headerbytes as string
            header = headerbytes.decode()

            #find all header values (ie key: val)
            matches = re.findall("([\S]+): ([^;]+)",header)
            for k,v in matches:
                if "Content-Type" in k:
                    contenttype = v

            #find all attributes (ie key=val)
            matches = re.findall("([\S]+)=\"?([^\";]*)\"?",header)
            for k,v in matches:
                if "name" == k:
                    headername = v
                elif "filename" == k:
                    filename = v

            fd = formdata(headername,bodybytes,contenttype=contenttype,filename=filename)
            blocks[headername] = fd

            blockbytes,foundboundary,bodybytesremainder = bodybytesremainder.partition(boundary)

        return httpform(contenttype=formcontenttype,boundary=boundary,data=blocks)

class httprequest():
    def __init__(self,method="",uri="",httpvers="HTTP/1.1",headers=None,cookies=None,body=b'',form=None,raw=b''):
        self.method = method
        self.uri = uri
        self.httpvers = httpvers
        self.body = body
        self.headers = headers if headers is not None else headerlist()
        self.cookies = cookies if cookies is not None else cookielist()
        self.form = form if form is not None else httpform()
        self.raw = raw
        logging.debug(b"Raw Request: " + self.raw)
    
    def format(self):
        if self.raw != b'':
            return self.raw

        lines = []
        lines.append(f"{self.method} {self.uri} {self.httpvers}".encode())
        lines.append(b'\r\n')
        lines.append(self.headers.format())
        if self.headers.getHeader("Cookie") is None:
            lines.append(self.cookies.format(mode=CookieFormatMode.REQUEST))
        lines.append(b'\r\n')
        if self.body != b'':
            lines.append(self.body)
        elif self.form != None:
            self.form: httpform
            lines.append(self.form.format())
        lines.append(b'\r\n')

        return b''.join(lines)

    def send(self, sock: socket.socket):
        sock.send(self.format())

    def frombytes(databytes: bytes):
        clrf = b'\r\n'
        headersep = b': '
        headerend = clrf+clrf
        headerbytes,_,bodybytes = databytes.partition(headerend)

        #first line of header is the startline
        startlinebytes,_,headerbytes = headerbytes.partition(clrf)
        startline = startlinebytes.decode()

        #the rest are http headers, treat as ascii
        headerstr = headerbytes.decode()
        headers = headerlist()
        while headerstr != '':
            headerline,_,headerstr = headerstr.partition('\r\n')
            headerkey,_,headerval = headerline.partition(': ')
            headers.addHeader(headerkey,headerval)
        cookies = None
        cookieHeader = headers.getHeader("Cookie")
        if cookieHeader is not None:
            cookies = cookielist.fromHeader(cookieHeader.val)

        #assign our properties from parsed values
        method,_,reststartline = startline.partition(" ")
        uri,_,httpvers = reststartline.partition(" ")
        contentTypeHeader = headers.getHeader("Content-Type")
        contentType = ''
        boundary = ''
        if contentTypeHeader is not None:
            contentType,_,boundary = contentTypeHeader.val.partition('; boundary=')

        #next, handle the form data from body
        form = None
        if contentType == "multipart/form-data":
            form = httpform.parsemultipart(bodybytes, boundary.encode())
        elif contentType == "application/x-www-form-urlencoded":
            form = httpform.parseurlencoded(bodybytes)
        
        return httprequest(method=method,uri=uri,httpvers=httpvers,headers=headers,cookies=cookies,body=bodybytes,form=form,raw=databytes)

    def fromsocket(sock: socket.socket):
        clrf = b'\r\n'
        headerend = b'\r\n\r\n'
        recvsize = 1024

        data = sock.recv(recvsize)

        #http headers continue until two CLRF

        #if we cannot find two CLRF in our data and len(data) is recvsize,
        #we need to call recv again
        headerendindex = data.find(headerend)
        while headerendindex == -1:
            data += sock.recv(recvsize)
            headerendindex = data.find(headerend)
        
        marker = b'Content-Length: '
        begin = data.find(marker)

        #no Content-Length was found, so we do not have a body to receive
        if begin == -1:
            return httprequest.frombytes(data)

        #Content-Length was found, make sure we receive body data
        end = data.find(clrf,begin)
        contentlength = int(data[begin+len(marker):end].decode())
        
        bodystartindex = headerendindex + len(headerend)
        while (len(data) - bodystartindex) < contentlength:
            data += sock.recv(recvsize)

        return httprequest.frombytes(data)
    
class httpserver():

    def __init__(self, addr: str, port: int):
        self.addr = addr
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listenthread = threading.Thread(target=serverloop,args=(self,))
        self.listening = False
        self.handlers = defaultdict(dict)
        self.statichandlers = dict()
        self.handler404 = httpserver.default404

    def start(self):
        if not self.listening:
            self.listening = True
            self.listenthread.start()
            
    def stop(self):
        if self.listening:
            self.listening = False

    def default404(req: httprequest, match: re.Match, sock: socket.socket):
        resp = httpresponse(statuscode=statuscodes.NOT_FOUND)
        sock.send(resp.format())

    def register(self, methods: tuple, uri: str):
        def inner(func):
            for method in methods:
                self.handlers[re.compile(uri)][method] = func
        return inner
    
    def registerstatic(self, uri: str):
        def inner(func):
            self.statichandlers[re.compile(uri)] = func
        return inner
    
    def dispatch(self, r: httprequest, sock: socket):
        #check static handlers first
        handler = None
        match = None
        for uriRegex in self.statichandlers.keys():
            uriRegex: re
            match = uriRegex.match(r.uri)
            if match:
                handler = self.statichandlers[uriRegex]
                break
        if match == None:
            #app handlers next
            for uriRegex in self.handlers.keys():
                uriRegex: re
                match = uriRegex.match(r.uri)
                if match:
                    handler = self.handlers[uriRegex].get(r.method,None)
                    break
        
        if handler == None: handler = self.handler404

        logging.info(f"Dispatching {r.method}:{r.uri}")
        handler(r,match,sock)

def acceptloop(*args, **kwargs):
    server: httpserver
    sock: socket.socket

    server = args[0]
    sock = args[1][0]
    r = httprequest.fromsocket(sock)
    server.dispatch(r,sock)

    sock.close()

def serverloop(*args, **kwargs):
    server: httpserver
    server = args[0]
    server.socket.bind((server.addr,server.port))
    server.socket.listen()
    while server.listening:
        c = server.socket.accept()
        threading.Thread(target=acceptloop,args=(server,c),daemon=True).start()
    server.socket.close()