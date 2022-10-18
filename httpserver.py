from routehandler import RouteHandler
import socket
import threading
import logging
from httphelper import Request

class Server():
    def __init__(self,addr: str, port: int, rh: RouteHandler = None):
        logging.info(f'Creating Server with {addr=},{port=}')
        self.addr = addr
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listenthread = None
        self.listening = False
        self.rh = rh or RouteHandler()
    
    def accept(self,conn):
        logging.info(f'Accepted connection from {conn[1]=}')
        sock = conn[0]
        req = Request.fromSocket(sock)
        req.socket = sock
        self.rh.dispatch(req,sock)
        sock.close()

    def listen(self):
        logging.info(f'Binding Server with {self.addr=},{self.port=}')
        self.socket.bind((self.addr, self.port))
        self.socket.listen()
        logging.info('Listening...')
        while self.listening:
            conn = self.socket.accept()
            threading.Thread(target=self.accept,args=(conn,),daemon=True).start()
        self.socket.close()

    def start(self):
        if not self.listening:
            logging.info('Starting Server')
            self.listening = True
            self.listenthread = threading.Thread(target=self.listen)
            self.listenthread.start()