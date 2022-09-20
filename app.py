import httpserver
import socket
from re import Match

s = httpserver.Server("localhost",80)

@s.register(["GET","POST"],"/$")
def root(req: httpserver.Request, match: Match, sock: socket.socket):
    with open("main.html","rb") as f:
        resp = httpserver.Response()
        resp.body = f.read()
        resp.send(sock)

@s.register(["GET","POST"],"/cookies$")
def cookies(req: httpserver.Request, match: Match, sock: socket.socket):
    with open("cookies.html","rb") as f:
        resp = httpserver.Response()
        if req.method == "POST":
            cname = req.form["cname"].asStr()
            cval = req.form["cval"].asStr()
            resp.cookies[cname] = cval
        resp.body = f.read()
        resp.body = resp.body.replace(b'@placeholder',('<br>'.join([f'{k}: {v}' for k,v in req.cookies.items()])).encode())
        resp.send(sock)

@s.register(("GET","POST"),"/multipart\?raw$")
def multipartraw(req: httpserver.Request, match: Match, sock: socket.socket):
    with open("multipartform.html","rb") as f:
        resp = httpserver.Response()
        resp.body = f.read().replace(b'@placeholder', str(req.raw).encode())
        resp.send(sock)

@s.register(("GET","POST"),"/multipart\?body$")
def multipartbody(req: httpserver.Request, match: Match, sock: socket.socket):
    with open("multipartform.html","rb") as f:
        resp = httpserver.Response()
        resp.body = f.read().replace(b'@placeholder',str(req.formatBody()).encode())
        resp.send(sock)

@s.register(("GET","POST"),"/multipart/form$")
def multipartform(req: httpserver.Request, match: Match, sock: socket.socket):
    with open("multipartform.html","rb") as f:
        resp = httpserver.Response()
        resp.body = f.read().replace(b'@placeholder',b'')
        resp.send(sock)

@s.register(("GET","POST"),"/multipart/format/form$")
def multipartbody(req: httpserver.Request, match: Match, sock: socket.socket):
    with open("multipartform.html","rb") as f:
        resp = httpserver.Response()
        lines = []
        lines.append(b'<br/>')
        lines.append(req.form.format())
        lines.append(b'<br/>')
        lines.append(b'<br/>')
        lines.append(req.body)
        lines.append(b'<br/>')
        lines.append(b'<br/>')
        lines.append(str(req.body == req.form.format()).encode())
        resp.body = f.read().replace(b'@placeholder',str(b''.join(lines)).encode())
        resp.send(sock)

@s.register(("GET","POST"),"/multipart/format$")
def multipartformat(req: httpserver.Request, match: Match, sock: socket.socket):
    with open("multipartform.html","rb") as f:
        resp = httpserver.Response()
        lines = []
        lines.append(b'<br/>')
        lines.append(req.format())
        lines.append(b'<br/>')
        lines.append(b'<br/>')
        lines.append(req.raw)
        lines.append(b'<br/>')
        lines.append(b'<br/>')
        lines.append(str(req.raw == req.format()).encode())
        resp.body = f.read().replace(b'@placeholder',str(b''.join(lines)).encode())
        resp.send(sock)

@s.register(("GET","POST"),"/urlenc\?form$")
def urlencform(req: httpserver.Request, match: Match, sock: socket.socket):
    with open("urlencform.html","rb") as f:
        resp = httpserver.Response()
        lines = []
        lines.append(b'<br/>')
        lines.append(req.form.format())
        lines.append(b'<br/>')
        lines.append(b'<br/>')
        lines.append(req.body)
        lines.append(b'<br/>')
        lines.append(b'<br/>')
        lines.append(str(req.body == req.form.format()).encode())
        resp.body = f.read().replace(b'@placeholder',str(b''.join(lines)).encode())
        resp.send(sock)

@s.register(("GET","POST"),"/urlenc$")
def urlenc(req: httpserver.Request, match: Match, sock: socket.socket):
    with open("urlencform.html","rb") as f:
        resp = httpserver.Response()
        resp.body = f.read().replace(b'@placeholder',str(req.raw).encode())
        resp.send(sock)

@s.register(("GET","POST"),"/urlenc/format$")
def urlencformat(req: httpserver.Request, match: Match, sock: socket.socket):
    with open("urlencform.html","rb") as f:
        resp = httpserver.Response()
        lines = []
        lines.append(b"<br/>")
        lines.append(req.format())
        lines.append(b"<br/>")
        lines.append(b"<br/>")
        lines.append(req.raw)
        lines.append(b"<br/>")
        lines.append(b"<br/>")
        lines.append(str(req.raw == req.format()).encode())
        resp.body = f.read().replace(b'@placeholder',str(b''.join(lines)).encode())
        resp.send(sock)

@s.registerstatic("/static/.*")
def static(req: httpserver.Request, match: Match, sock: socket.socket):
    resp = httpserver.Response()
    try:
        if req.uri.find("./") > -1:
            raise Exception
        with open("."+req.uri, "rb") as f:
            resp.body = f.read()
    except:
        resp.statuscode = httpserver.STATUS_CODES[404]
    resp.send(sock)

print("Starting server...\n")
s.start()
s.listenthread.join()