

from stem.control.interactive import run
from stem.core.notification_queue import in_main_thread


started = False

def server_address_file():
    from stem.options import UserConfigHome
    return UserConfigHome / 'server_address'
    
def start_server():
    global started
    if not started:
        import xmlrpc.server
        import threading
        #global server
        server = xmlrpc.server.SimpleXMLRPCServer(('127.0.0.1', 0), allow_none=True)
        server.register_function(in_main_thread(run), 'run')
       
        host, port = server.server_address
        with server_address_file().open('w') as f:
            f.write('http://{host}:{port}'.format(**locals()))

        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        

def make_server_proxy():
    import xmlrpc.client
    with server_address_file().open() as f:
        server_address = f.read().strip()
    
    return xmlrpc.client.ServerProxy(server_address)
    

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
