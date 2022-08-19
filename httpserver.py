from difflib import Match
from enum import Enum
from collections import defaultdict
from dataclasses import dataclass
import socket
import time
import threading
import re

@dataclass(frozen=True)
class formdata():
    name: str
    value: bytes
    contenttype: str = ""
    filename: str = None

    def formatUrlEnc(self):
        return f"{self.name}=".encode() + self.value.encode()
    
    def formatFormData(self):
        header = f'Content-Disposition: form-data; name="{self.name}"'
        if self.filename != None:
            header += f'; filename="{self.filename}"'
        if self.contenttype != "":
            header += f'\r\nContent-Type: {self.contenttype}'
        body = self.value

        return header.encode() + b'\r\n\r\n' + body + b'\r\n'

class statuscodes(Enum):
    OK = (200,"OK")
    NOT_FOUND = (404,"Not Found")
    NOT_DEFINED = (-1,"Not Defined")

class httpresponse():
    def __init__(self, httpvers = "HTTP/1.1", statuscode = statuscodes.OK, body = b'', headers=None):
        self.httpvers = httpvers
        self.statuscode = statuscode
        self.body = body
        self.headers = headers if headers != None else dict()
    
    def format(self):
        startline = self.httpvers.encode() + f' {self.statuscode.value[0]} {self.statuscode.value[1]}\r\n'.encode()
        if self.headers.get(b'Content-Length',None) == None:
            self.headers[b'Content-Length'] = str(len(self.body)).encode()
        rebuiltHeaders = [k+b': '+v for k,v in self.headers.items()]

        return startline + b'\r\n'.join(rebuiltHeaders) + b'\r\n\r\n' + self.body

    def send(self, sock: socket.socket):
        sock.send(self.format())

class httpform():
    def __init__(self, contenttype="", boundary=b'', data=None):
        self.contenttype = contenttype
        self.boundary = boundary
        if data == None:
            self.data = dict()
        else:
            self.data = data
        
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
        data = data.decode()

        bsep = "&"
        kvsep = "="

        keyvalpair,foundsep,remainder = data.partition(bsep)
        while foundsep != "":
            key,_,val = keyvalpair.partition(kvsep)
            parsed[key] = formdata(key,val)
            keyvalpair,foundsep,remainder = remainder.partition(bsep)
        key,_,val = keyvalpair.partition(kvsep)
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
    def __init__(self,method="",uri="",httpvers="HTTP/1.1",headers=None,body=b'',form=None,raw=b''):
        self.method = method
        self.uri = uri
        self.httpvers = httpvers
        self.body = body
        if headers == None:
            self.headers = defaultdict(bytes)
        else:
            self.headers = headers
        self.form = form if form != None else httpform()
        self.raw = raw
    
    def format(self):
        if self.raw != b'':
            return self.raw

        lines = []
        lines.append(f"{self.method} {self.uri} {self.httpvers}".encode())
        lines.append(b'\r\n')
        for k,v in self.headers.items():
            lines.append(f"{k}: ".encode() + v + b'\r\n')
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

        #the rest are http headers
        headers = defaultdict(bytes)
        while headerbytes != b'':
            headerlinebytes,_,headerbytes = headerbytes.partition(clrf)
            headerkey,_,headerval = headerlinebytes.partition(headersep)
            headers[headerkey.decode()] = headerval

        #assign our properties from parsed values
        method,_,reststartline = startline.partition(" ")
        uri,_,httpvers = reststartline.partition(" ")
        contenttype,_,boundary = headers["Content-Type"].partition(b'; boundary=')

        #next, handle the form data from body
        form = None
        if contenttype == b"multipart/form-data":
            form = httpform.parsemultipart(bodybytes, boundary)
        elif contenttype == b"application/x-www-form-urlencoded":
            form = httpform.parseurlencoded(bodybytes)
        
        return httprequest(method=method,uri=uri,httpvers=httpvers,headers=headers,body=bodybytes,form=form,raw=databytes)

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

    def default404(req: httprequest, match: Match, sock: socket.socket):
        resp = httpresponse(statuscodes.NOT_FOUND)
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

        #app handlers next
        for uriRegex in self.handlers.keys():
            uriRegex: re
            match = uriRegex.match(r.uri)
            if match:
                handler = self.handlers[uriRegex].get(r.method,None)
                break
        
        if handler == None: handler = self.handler404

        print(f"Dispatching {r.uri}")
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