import os
import sqlite3
from jlpyhttp.httphelper import Request, Response
from jlpyutil.SQLiteHelper import *
from typing import Any
from hashlib import pbkdf2_hmac

class SessionHandler():
    def __init__(self, srq: SQLRequestQueue = None, salt: bytes = None):
        self.sessions = dict()
        self.sessionByteSize = 32
        self.userCookie = 'userid'
        self.sessionCookie = 'sessionid'
        self.salt = salt
        self.srq = srq
    
    def setPassword(self, username: str, password: str) -> None:
        if self.srq is None:
            return None
        hashedPassword = pbkdf2_hmac('sha256',password.encode(),self.salt,500_000)
        @SQLTransaction
        def query(cur: sqlite3.Cursor):
            cur.execute("""
                INSERT INTO auth (employeeid, password)
                VALUES ((SELECT employeeid FROM employee WHERE username = ?), ?)
                ON CONFLICT (employeeid)
                DO UPDATE SET (password) = ?
            """,(username,hashedPassword,hashedPassword))
            return None
        r = self.srq.createRequestor()
        r.request(query)
    
    def authUser(self, username: str, password: str, resp: Response = None) -> bool:
        if self.srq is None:
            return False
        @SQLTransaction
        def query(cur: sqlite3.Cursor):
            cur.execute("""
                SELECT password, employeeid
                FROM auth
                WHERE employeeid = (SELECT employeeid FROM employee WHERE username = ?)
            """,(username,))
            return cur.fetchone()
        r = self.srq.createRequestor()
        result = r.request(query)
        if result:
            storedPassword = result[0]
            eid = result[1]
            hashedPassword = pbkdf2_hmac('sha256',password.encode(),self.salt,500_000)
            if storedPassword == hashedPassword:
                self.createSession(eid,resp=resp)
                return True
        return False

    ##returns sessionid: str
    def createSession(self, userid: int, resp: Response = None, d: dict = None) -> Response | str:
        sid = os.urandom(self.sessionByteSize).hex()
        self.sessions[userid] = sid
        uCookie = f'{userid}; Path=/'
        sCookie = f'{sid}; Path=/'
        if resp is not None:
            resp.cookies[self.userCookie] =  uCookie
            resp.cookies[self.sessionCookie] = sCookie
        elif d is not None:
            d[self.userCookie] = uCookie
            d[self.sessionCookie] = sCookie
        return resp or sid or d

    ##returns Tuple(valid: bool, userid: int)
    def validateSession(self, userid: int = None, sessionid: str = None, req: Request = None) -> Any:
        userid = userid or int(req.cookies.get(self.userCookie,'') or -1)
        sessionid = sessionid or req.cookies.get(self.sessionCookie,'')

        storedSession = self.sessions.get(userid,'')
        if storedSession == '':
            return False, None
        if storedSession == sessionid:
            return True, userid
        return False, None
    
    ##invalide session and set cookies if Response is supplied
    def invalidateSession(self, userid: int = None, req: Request = None, resp: Response = None) -> Response | None:
        userid = userid or int(req.cookies.get(self.userCookie,'') or -1)
        self.sessions[userid] = ''
        if resp is not None:
            resp.cookies[self.userCookie] = '; Path=/'
            resp.cookies[self.sessionCookie] = '; Path=/'
        return resp
    
    def resetAdminPassword(self):
        self.setPassword("admin","password")