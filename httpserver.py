from collections import defaultdict
import socket
import time
import threading

class httpresponse():
    statuscodes = {
        0: "Not Defined",
        404: "Not Found", 
        200: "OK"
        }

    def __init__(self, statuscode = 0, body = b''):
        self.statuscode = statuscode
        self.body = body
    
    def format(self):
        b = "HTTP/1.1 ".encode()
        b += (str(self.statuscode) + " ").encode()
        b += (httpresponse.statuscodes[self.statuscode] + "\r\n").encode()
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

    def getmethod(self):
        if self.method == "":
            if self.startline != "":
                self.method = self.startline.partition(" ")[0]
        return self.method
    
    def geturi(self):
        if self.uri == "":
            if self.startline != "":
                self.uri = self.startline.partition(" ")[2].partition(" ")[0]
        return self.uri

    def parseurlencoded(data: bytes) -> dict:
        parsed = dict()
        data = data.decode()

        bsep = "&"
        kvsep = "="

        keyvalpair,foundsep,remainder = data.partition(bsep)
        while foundsep != "":
            key,_,val = keyvalpair.partition(kvsep)
            parsed[key] = val
            keyvalpair,foundsep,remainder = remainder.partition(bsep)
        key,_,val = keyvalpair.partition(kvsep)
        parsed[key] = val

        return parsed

    def parsemultipart(data: bytes, bsep: bytes):
        clrf = b'\r\n'
        hsep = b': '
        asep = b'; '
        bsep = b'--' + bsep

        blocks = dict()
        blockbytes,foundbodysep,bodybytesremainder = data.partition(bsep)
        while foundbodysep == bsep:
            #if blockbytes == b'', then we have encountered the intial bsep
            if blockbytes != b'':
                block = dict()

                #first 2 bytes should be CLRF, so we can get rid of them
                blockbytes = blockbytes[2:]

                #headers for form data should be present before body
                headerbytes,foundheaderblocksep,blockbytesremainder = blockbytes.partition(clrf)

                #header will be empty when 2 CLRF are encountered, indicating end of headers
                while headerbytes != b'':
                    #parse header
                    #content-disposition can contain ';'
                    header,foundheadersep,headerremainder = headerbytes.partition(hsep)
                        
                    #if we have the arg sep (asep) in our header line, we need to parse this line further
                    if asep in headerremainder:
                        headerval,foundargsep,headerremainder = headerremainder.partition(asep)

                        #first part is assigned to header
                        block[header.decode()] = headerval.decode()

                        #any further args can be assigned to their own variable
                        headerval,foundargsep,headerremainder = headerremainder.partition(asep)
                        while foundargsep != b'':
                            argkey,foundassignsep,argval = headerval.decode().partition('=')
                            if foundassignsep != '':
                                block[argkey] = argval.strip('"')
                            headerval,foundargsep,headerremainder = headerremainder.partition(asep)
                        #the last arg will be found in headerval
                        argkey,foundassignsep,argval = headerval.decode().partition('=')
                        if foundassignsep != '':
                            block[argkey] = argval.strip('"')
                    #no arg sep found, just assign to header
                    else:
                        block[header.decode()] = headerremainder.decode()
                    
                    headerbytes,foundheadersep,blockbytesremainder = blockbytesremainder.partition(clrf)

                #left with body, trim CLRF from the end
                block["value"] = blockbytesremainder[:-2]

                #add block to blocks dict
                blocks[block.get("name","")] = block
            blockbytes,foundbodysep,bodybytesremainder = bodybytesremainder.partition(bsep)

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
    
    def dispatch(self, r: httprequest, sock: socket):
        if self.handlers[r.uri].get(r.method,"") != "":
            self.handlers[r.uri][r.method](r,sock)
        else:
            if self.handlers["404"].get("GET", None) != None:
                self.handlers["404"](r,sock)
            else:
                resp = httpresponse(404)
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