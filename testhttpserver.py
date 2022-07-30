import httpserver
import socket

s = httpserver.httpserver("localhost",80)

@s.register("GET,POST","/")
def root(req: httpserver.httprequest, sock: socket.socket):
    with open("main.html","r") as f:
        resp = httpserver.httpresponse()
        resp.body = f.read().encode()
        resp.statuscode = 200
        resp.send(sock)

@s.register("GET,POST","/multipart?raw")
def multipartraw(req: httpserver.httprequest, sock: socket.socket):
    with open("multipartform.html","r") as f:
        resp = httpserver.httpresponse()
        resp.body = f.read().encode().replace(b'@placeholder', req.raw)
        resp.statuscode = 200
        resp.send(sock)

@s.register("GET,POST","/multipart?body")
def multipartraw(req: httpserver.httprequest, sock: socket.socket):
    with open("multipartform.html","r") as f:
        resp = httpserver.httpresponse()
        resp.body = f.read().encode().replace(b'@placeholder',str(req.body).encode())
        resp.statuscode = 200
        resp.send(sock)

print("Starting server...\n")
s.start()