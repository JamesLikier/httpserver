import httpserver
from httphelper import Request, Response, STATUS_CODES
from sessionhandler import SessionHandler
from re import Match
import logging

logging.basicConfig(filename="logfile",filemode="w",level=logging.DEBUG)
s = httpserver.Server("localhost",80)

@s.rh.register(["GET","POST"],"/$")
def root(req: Request, match: Match, resp: Response, session, sessionHandler: SessionHandler):
    with open("main.html","rb") as f:
        resp.body = f.read()
        resp.send()

@s.rh.register(["GET","POST"],"/cookies$")
def cookies(req: Request, match: Match, resp: Response, session, sessionHandler: SessionHandler):
    with open("cookies.html","rb") as f:
        if req.method == "POST":
            cname = req.form["cname"].asStr()
            cval = req.form["cval"].asStr()
            resp.cookies[cname] = cval
        resp.body = f.read()
        resp.body = resp.body.replace(b'@placeholder',('<br>'.join([f'{k}: {v}' for k,v in req.cookies.items()])).encode())
        resp.send()

@s.rh.register(("GET","POST"),"/multipart\?raw$")
def multipartraw(req: Request, match: Match, resp: Response, session, sessionHandler: SessionHandler):
    with open("multipartform.html","rb") as f:
        resp.body = f.read().replace(b'@placeholder', str(req.raw).encode())
        resp.send()

@s.rh.register(("GET","POST"),"/multipart\?body$")
def multipartbody(req: Request, match: Match, resp: Response, session, sessionHandler: SessionHandler):
    with open("multipartform.html","rb") as f:
        resp.body = f.read().replace(b'@placeholder',str(req.formatBody()).encode())
        resp.send()

@s.rh.register(("GET","POST"),"/multipart/form$")
def multipartform(req: Request, match: Match, resp: Response, session, sessionHandler: SessionHandler):
    with open("multipartform.html","rb") as f:
        resp.body = f.read().replace(b'@placeholder',b'')
        resp.send()

@s.rh.register(("GET","POST"),"/multipart/format/form$")
def multipartbody(req: Request, match: Match, resp: Response, session, sessionHandler: SessionHandler):
    with open("multipartform.html","rb") as f:
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
        resp.send()

@s.rh.register(("GET","POST"),"/multipart/format$")
def multipartformat(req: Request, match: Match, resp: Response, session, sessionHandler: SessionHandler):
    with open("multipartform.html","rb") as f:
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
        resp.send()

@s.rh.register(("GET","POST"),"/urlenc\?form$")
def urlencform(req: Request, match: Match, resp: Response, session, sessionHandler: SessionHandler):
    with open("urlencform.html","rb") as f:
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
        resp.send()

@s.rh.register(("GET","POST"),"/urlenc$")
def urlenc(req: Request, match: Match, resp: Response, session, sessionHandler: SessionHandler):
    with open("urlencform.html","rb") as f:
        resp.body = f.read().replace(b'@placeholder',str(req.raw).encode())
        resp.send()

@s.rh.register(("GET","POST"),"/urlenc/format$")
def urlencformat(req: Request, match: Match, resp: Response, session, sessionHandler: SessionHandler):
    with open("urlencform.html","rb") as f:
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
        resp.send()

@s.rh.registerstatic("/static/.*")
def static(req: Request, match: Match, resp: Response, session, sessionHandler: SessionHandler):
    try:
        if req.uri.find("./") > -1:
            raise Exception
        with open("."+req.uri, "rb") as f:
            resp.body = f.read()
    except:
        resp.statuscode = STATUS_CODES[404]
    resp.send()

print("Starting server...\n")
s.start()
s.listenthread.join()