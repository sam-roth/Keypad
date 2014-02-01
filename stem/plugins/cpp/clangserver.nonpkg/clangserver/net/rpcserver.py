
from SimpleXMLRPCServer import SimpleXMLRPCServer
from xmlrpclib import ServerProxy

import threading
from .. import server_methods
import sys

def exit():
    global rpcserv
    threading.Thread(target=lambda: rpcserv.shutdown()).start()

def main():
    global rpcserv
    #rpcserv = rs = SimpleXMLRPCServer(('127.0.0.1', 38474), allow_none=True)
    
    address_callback_server = ServerProxy(sys.argv[1])

    rpcserv = rs = SimpleXMLRPCServer(('127.0.0.1', 0), allow_none=True)
    address_callback_server.use_address(rpcserv.server_address)

    rs.register_instance(server_methods.ServerMethods(), allow_dotted_names=True)
    rs.register_function(exit)
    rs.register_introspection_functions()

    rs.serve_forever()

