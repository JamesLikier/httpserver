import httpserver
import socket

f = open("form.html", "r")
form = f.read().encode()
f.close()

def root(req: httpserver.httprequest, sock: socket.socket):
    resp = httpserver.httpresponse()
    resp.body = form
    resp.statuscode = 200
    resp.send(sock)

s = httpserver.httpserver("localhost",80)
s.register("GET","/",root)
s.register("POST","/",root)

print("Starting server...\n")
s.start()