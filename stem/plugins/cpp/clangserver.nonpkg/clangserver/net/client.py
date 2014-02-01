

from multiprocessing import connection as mpc
from . import sockfile, msgs

class Client(object):
    def __init__(self):
        addr = sockfile.get()
        self._client = mpc.Client(addr)

    
    def sendMsg(self, msg):
        self._client.send(msg)

def main():
    client = Client()
    client.sendMsg(msgs.ExitMsg())
