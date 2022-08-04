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
    filename: str = ""

class statuscodes(Enum):
    OK = (200,"OK")
    NOT_FOUND = (404,"Not Found")
    NOT_DEFINED = (-1,"Not Defined")

class httpresponse():
    def __init__(self, statuscode = statuscodes.NOT_DEFINED, body = b''):
        self.statuscode = statuscode
        self.body = body
    
    def format(self):
        b = "HTTP/1.1 ".encode()
        b += (str(self.statuscode.value[0]) + " ").encode()
        b += (self.statuscode.value[1] + "\r\n").encode()
        b += ("Content-Length: " + str(len(self.body)) + "\r\n\r\n").encode()
        b += self.body
        return b

    def send(self, sock: socket.socket):
        sock.send(self.format())

class httprequest():
    def __init__(self):
        self.startline = ""
        self.headers = defaultdict(bytes)
        self.body = dict()
        self.raw = b''
        self.method = ""
        self.uri = ""
        self.contenttype = ""
        self.contentlength = 0
        self.boundary = b''

    def parseurlencoded(data: bytes) -> dict:
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

        return parsed

    def parsemultipart(data: bytes, boundary: bytes):
        clrf = b'\r\n'
        boundary = b'--' + boundary

        blocks = dict()
        blockbytes,foundboundary,bodybytesremainder = data.partition(boundary)
        while foundboundary == boundary:
            headername = ""
            filename = ""
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

        return blocks

    def frombytes(data: bytes):
        clrf = b'\r\n'
        headersep = b': '
        headerend = clrf+clrf
        req = httprequest()
        req.raw = data
        headerdata,_,bodydata = data.partition(headerend)

        #first line of header is the startline
        startline,_,headerdata = headerdata.partition(clrf)
        req.startline = startline.decode()

        #the rest are http headers
        while headerdata != b'':
            header,_,headerdata = headerdata.partition(clrf)
            headerkey,_,headerval = header.partition(headersep)
            req.headers[headerkey.decode()] = headerval

        #assign our properties from parsed values
        req.contentlength = int(req.headers["Content-Length"] if req.headers["Content-Length"] != b'' else 0)
        req.method,_,reststartline = req.startline.partition(" ")
        req.uri,_,_ = reststartline.partition(" ")
        req.contenttype,_,req.boundary = req.headers["Content-Type"].partition(b'; boundary=')
        req.contenttype = req.contenttype.decode()

        #next, handle the body
        if req.contenttype == "multipart/form-data":
            req.body = httprequest.parsemultipart(bodydata, req.boundary)
        elif req.contenttype == "application/x-www-form-urlencoded":
            req.body = httprequest.parseurlencoded(bodydata)
        
        return req

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

    def start(self):
        if not self.listening:
            self.listening = True
            self.listenthread.start()
            
    
    def stop(self):
        if self.listening:
            self.listening = False

    def register(self, methods: tuple, uri: str):
        def inner(func):
            for method in methods:
                self.handlers[uri][method] = func
        return inner
    
    def registerstatic(self, uri: str):
        def inner(func):
            self.statichandlers[uri] = func
        return inner
    
    def dispatch(self, r: httprequest, sock: socket):
        #check static handlers first
        for uri in self.statichandlers.keys():
            if r.uri.startswith(uri):
                self.statichandlers[uri](r,sock)

        #app handlers next
        if self.handlers[r.uri].get(r.method,"") != "":
            self.handlers[r.uri][r.method](r,sock)
        else:
            if self.handlers["404"].get("GET", None) != None:
                self.handlers["404"](r,sock)
            else:
                resp = httpresponse(statuscodes.NOT_FOUND)
                sock.send(resp.format())


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