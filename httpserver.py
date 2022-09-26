from routehandler import RouteHandler
import logging
import socket
import threading
from httphelper import Request

class Server():
    def __init__(self,addr: str, port: int, rh: RouteHandler = None):
        self.addr = addr
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listenthread = None
        self.listening = False
        self.rh = rh or RouteHandler()
    
    def accept(self,conn):
        sock = conn[0]
        req = Request.fromSocket(sock)
        req.socket = sock
        self.rh.dispatch(req,sock)
        sock.close()

    def listen(self):
        self.socket.bind((self.addr, self.port))
        self.socket.listen()
        while self.listening:
            conn = self.socket.accept()
            threading.Thread(target=self.accept,args=(conn,),daemon=True).start()
        self.socket.close()

    def start(self):
        if not self.listening:
            self.listening = True
            self.listenthread = threading.Thread(target=self.listen)
            self.listenthread.start()