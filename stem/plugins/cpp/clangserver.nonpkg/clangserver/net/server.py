
from multiprocessing import connection as mpc
import threading
import msgs


class ConnectionThd(threading.Thread):
    def __init__(self, server, conn):
        '''
        :type conn: multiprocessing.connection.ConnectionWrapper
        '''
        super(ConnectionThd, self).__init__()
        self.server = server
        self.daemon = True
        self._conn = conn
        self._stopped = False
        
    def run(self):
        while not self._stopped:
            try:
                
                msg = self._conn.recv()
            except EOFError:
                return

            if isinstance(msg, msgs.Msg):
                msg(self)
            else:
                print 'unknown message:', msg

    
    def stop(self):
        self._stopped = True

    
    def send(self, msg):
        self._conn.send(msg)



from . import sockfile

class ServerThd(threading.Thread):
    def __init__(self):
        self._srv = mpc.Listener()
        self._conns = []
        sockfile.set(self._srv.address)
    
    def run(self):
        while True:
            self._srv
            raw_conn = self._srv.accept()
            conn = ConnectionThd(self, raw_conn)
            self._conns.append(conn)
            conn.start()
            

    def stop(self):

        for thread in self._conns:
            thread.stop()
            



def main():
    svr = ServerThd()
    svr.run()


if __name__ == '__main__':
    main()

