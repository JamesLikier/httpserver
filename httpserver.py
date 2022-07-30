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
        self.headers = defaultdict(str)
        self.body = dict()
        self.raw = b''
        self.method = ""
        self.uri = ""

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

    
    def fromsocket(sock: socket.socket):
        req = httprequest()

        clrf = b'\r\n'

        #get initial data from socket to begin parsing
        data = sock.recv(1024)
        req.raw += data

        #first line of http request is the startline
        startline,_,dataremainder = data.partition(clrf)
        req.startline = startline.decode()

        #if the rest of the request is a CLRF, we have a one line request
        if dataremainder == clrf:
            return req

        #everything until double CLRF encountered is our header section
        hsep = b': '
        header,foundsep,dataremainder = dataremainder.partition(clrf)
        while header != b'' and foundsep == clrf:
            #parse header tags
            headerkey,_,headerval = header.partition(hsep)
            req.headers[headerkey.decode()] = headerval.decode()

            #get next partition
            header,foundsep,dataremainder = dataremainder.partition(clrf)

            #if we don't find another CLRF, we need to call recv on socket again...
            if foundsep == b'':
                data = sock.recv(1024)
                req.raw += data
                header,foundsep,dataremainder = (header + data).partition(clrf)
        #header section complete
        
        #if Content-Length and Content-Type are not set, no body should be present
        if req.headers["Content-Length"] == "" or req.headers["Content-Type"] == "":
            return req
        
        #check for boundary assignment in Content-Type header
        ct = req.headers["Content-Type"]
        if ct != "":
            contenttype,foundsep,boundarydata = ct.partition("; ")
            if foundsep != "":
                #we have boundary present

                #fix Content-Type header
                req.headers["Content-Type"] = contenttype
                #set boundary header
                boundarykey,_,boundaryval = boundarydata.partition("=")
                req.headers[boundarykey] = boundaryval
        
        #now for the body of the request...

        #check Content-Length and make sure we have complete body
        contentlength = int(req.headers["Content-Length"])
        bodydata = dataremainder
        while len(bodydata) < contentlength:
            data = sock.recv(1024)
            req.raw += data
            bodydata += data
        
        #body is now ready for parsing

        if req.headers["Content-Type"] == "application/x-www-form-urlencoded":
            req.body = httprequest.parseurlencoded(bodydata)
        elif req.headers["Content-Type"] == "multipart/form-data" and req.headers["boundary"] != "":
            req.body = httprequest.parsemultipart(bodydata, req.headers["boundary"].encode())

        return req

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
        if self.handlers[r.geturi()].get(r.getmethod(),"") != "":
            self.handlers[r.geturi()][r.getmethod()](r,sock)
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