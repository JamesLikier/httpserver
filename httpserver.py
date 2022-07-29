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
        self.headers = dict()
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
        d = dict()
        data = data.decode()

        bsep = "&"
        kvsep = "="
        p = data.partition(bsep)
        while p[1] != "":
            kvp = p[0].partition(kvsep)
            d[kvp[0]] = kvp[2]
            p = p[2].partition(bsep)
        kvp = p[0].partition(kvsep)
        d[kvp[0]] = kvp[2]

        return d

    def parsemultipart(data: bytes, bsep: bytes):
        sep = b'\r\n'
        hsep = b': '
        asep = b'; '
        bsep = b'--' + bsep

        blocks = dict()
        p = data.partition(bsep)
        while p[1] == bsep:
            if p[0] != b'':
                #headers for form data should be present before body
                #first 2 bytes should be sep, so we can get rid of them
                bp = p[0][2:].partition(sep)
                block = dict()

                #headers continue until two sep encountered
                while bp[0] != b'':
                    #parse header
                    #content-disposition can contain ';'
                    hp = bp[0].partition(hsep)
                        
                    #if we have the arg sep (asep) in our header line, we need to parse this line further
                    if asep in hp[2]:
                        ap = hp[2].partition(asep)

                        #first part is assigned to header
                        block[hp[0].decode()] = ap[0].decode()

                        #any further args can be assigned to their own variable
                        ap = ap[2].partition(asep)
                        while ap[1] != b'':
                            avp = ap[0].decode().partition('=')
                            if avp[1] != '':
                                block[avp[0]] = avp[2].strip('"')
                            ap = ap[2].partition(asep)
                        #get the last trailing arg
                        avp = ap[0].decode().partition('=')
                        if avp[1] != '':
                            block[avp[0]] = avp[2].strip('"')
                    #no arg sep found, just assign to header
                    else:
                        block[hp[0].decode()] = hp[2].decode()
                    
                    bp = bp[2].partition(sep)

                #left with body
                block["value"] = bp[2][:-2]

                #add block to blocks dict
                blocks[block.get("name","")] = block
            p = p[2].partition(bsep)

        return blocks

    
    def fromsocket(sock: socket.socket):
        r = httprequest()

        clrf = b'\r\n'

        #get initial data from socket to begin parsing
        data = sock.recv(1024)
        r.raw += data

        #first line of http request is the startline
        p = data.partition(clrf)
        r.startline = p[0].decode()

        #if the rest of the request is a CLRF, we have a one line request
        if p[2] == clrf:
            return r

        #everything until double CLRF encountered is our header section
        hsep = b': '
        p = p[2].partition(clrf)
        while p[0] != b'' and p[1] == clrf:
            #parse header tags
            hp = p[0].partition(hsep)
            r.headers[hp[0].decode()] = hp[2].decode()

            #get next partition
            p = p[2].partition(clrf)

            #if we don't find another CLRF, we need to call recv on socket again...
            if p[1] == b'':
                data = sock.recv(1024)
                r.raw += data
                p = (p[0] + data).partition(clrf)
        #header section complete
        
        #if Content-Length and Content-Type are not set, no body should be present
        if r.headers.get("Content-Length","") == "" or r.headers.get("Content-Type","") == "":
            return r
        
        #check for boundary assignment in Content-Type header
        ct = r.headers.get("Content-Type","")
        if ct != "":
            ctp = ct.partition("; ")
            if ctp[1] != "":
                #we have boundary present

                #fix Content-Type header
                r.headers["Content-Type"] = ctp[0]
                #set boundary header
                ctp = ctp[2].partition("=")
                r.headers[ctp[0]] = ctp[2]
        
        #now for the body of the request...

        #check Content-Length and make sure we have complete body
        cl = int(r.headers.get("Content-Length",""))
        bodydata = p[2]
        while len(bodydata) < cl:
            data = sock.recv(1024)
            r.raw += data
            bodydata += data
        
        #body is now ready for parsing

        if r.headers["Content-Type"] == "application/x-www-form-urlencoded":
            r.body = httprequest.parseurlencoded(bodydata)
        elif r.headers["Content-Type"] == "multipart/form-data" and r.headers.get("boundary","") != "":
            r.body = httprequest.parsemultipart(bodydata, r.headers["boundary"].encode())

        return r

class httpserver():

    def __init__(self, addr: str, port: int):
        self.addr = addr
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listenthread = threading.Thread(target=serverloop,args=(self,))
        self.listening = False
        self.handlers = dict()

    def start(self):
        if not self.listening:
            self.listening = True
            self.listenthread.start()
            
    
    def stop(self):
        if self.listening:
            self.listening = False

    def register(self, method: str, uri: str):
        def inner(func):
            if self.handlers.get(uri, None) == None:
                self.handlers[uri] = dict()

            p = method.partition(",")
            self.handlers[uri][p[0]] = func
            while p[1] != "":
                p = p[2].partition(",")
                self.handlers[uri][p[0]] = func
        return inner
    
    def dispatch(self, r: httprequest, sock: socket):
        if self.handlers.get(r.geturi(),"") != "" and self.handlers[r.geturi()].get(r.getmethod(),"") != "":
            self.handlers[r.geturi()][r.getmethod()](r,sock)
        else:
            if self.handlers.get("404","") != "":
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