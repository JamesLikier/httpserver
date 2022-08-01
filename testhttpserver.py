import httpserver
import socket

s = httpserver.httpserver("localhost",80)

@s.register(("GET","POST"),"/")
def root(req: httpserver.httprequest, sock: socket.socket):
    with open("main.html","r") as f:
        resp = httpserver.httpresponse()
        resp.body = f.read().encode()
        resp.statuscode = 200
        resp.send(sock)

@s.register(("GET","POST"),"/multipart?raw")
def multipartraw(req: httpserver.httprequest, sock: socket.socket):
    with open("multipartform.html","r") as f:
        resp = httpserver.httpresponse()
        resp.body = f.read().encode().replace(b'@placeholder', str(req.raw).encode())
        resp.statuscode = 200
        resp.send(sock)

@s.register(("GET","POST"),"/multipart?body")
def multipartraw(req: httpserver.httprequest, sock: socket.socket):
    with open("multipartform.html","r") as f:
        resp = httpserver.httpresponse()
        resp.body = f.read().encode().replace(b'@placeholder',str(req.body).encode())
        resp.statuscode = 200
        resp.send(sock)

@s.registerstatic("/static/")
def static(req: httpserver.httprequest, sock: socket.socket):
    resp = httpserver.httpresponse()
    print(req.uri)
    try:
        with open("."+req.uri, "rb") as f:
            resp.body = f.read()
            resp.statuscode = 200
    except:
        print(f'{req.uri} NOT FOUND')
        resp.statuscode = 404
    resp.send(sock)

print("Starting server...\n")
s.start()