import httpserver
import socket

f = open("form.html", "r")
form = f.read().encode()
f.close()

s = httpserver.httpserver("localhost",80)

@s.register("GET,POST","/")
def root(req: httpserver.httprequest, sock: socket.socket):
    resp = httpserver.httpresponse()
    resp.body = form
    resp.statuscode = 200
    resp.send(sock)

print("Starting server...\n")
s.start()