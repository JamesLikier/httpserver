import os
from jlpyhttp.http import Request, Response
from typing import Any
from hashlib import pbkdf2_hmac

class SessionHandler():
    def __init__(self):
        self.sessions = dict()
        self.sessionByteSize = 32
        self.userCookie = 'userid'
        self.sessionCookie = 'sessionid'
    
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
    def validateSession(self, userid: int = None, sessionid: str = None, req: Request = None) -> tuple[bool,int|None]:
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