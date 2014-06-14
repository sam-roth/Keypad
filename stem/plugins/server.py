
from stem.api import (Plugin,
                      register_plugin,
                      interactive,
                      in_main_thread,
                      command)

from stem.control.interactive import run
from stem.core.notification_queue import in_main_thread


started = None
server = None

def server_address_file():
    from stem.options import UserConfigHome
    return UserConfigHome / 'server_address'
    
def write_server_address():
    host, port = started
    with server_address_file().open('w') as f:
        f.write('http://{host}:{port}'.format(host=host, port=port))

def start_server():
    global started
    global server
    if started is None:
        import xmlrpc.server
        import threading

        server = xmlrpc.server.SimpleXMLRPCServer(('127.0.0.1', 0), allow_none=True)

        server.register_function(in_main_thread(interactive.run), 
                                 'run')
       
        host, port = server.server_address
        path = server_address_file()
        if not path.parent.exists():
            path.parent.mkdir(parents=True)

        started = host, port
        write_server_address()

        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        server_thread = thread

def make_server_proxy():
    import xmlrpc.client
    with server_address_file().open() as f:
        server_address = f.read().strip()
    
    return xmlrpc.client.ServerProxy(server_address)
    
@register_plugin
class ServerPlugin(Plugin):
    name = 'Local Command Server'
    author = 'Sam Roth'

    @command('rewrite_server_address')
    def rewrite_server_address(self, _: object):
        write_server_address()

    def attach(self):
        start_server()

    def detach(self):
        server.shutdown()

def main():
    import argparse

    ap = argparse.ArgumentParser(description="""
        Send an interactive command to a Stem instance.
    """)
    ap.add_argument('command', help='The name of the interactive command to run.')
    ap.add_argument('args', nargs='*', help="The command's arguments.")
    
    
    args = ap.parse_args()

    prox = make_server_proxy()
    prox.run(args.command, *args.args)

if __name__ == '__main__':
    main()
