
import os.path

SockFilePath = os.path.expanduser('~/.clangserver_sock')

def get():
    '''
    Get the address of the current sockfile if it exists, otherwise return None.
    '''

    try:    
        with open(SockFilePath, 'r') as f:
            return f.read().strip()
    except IOError:
        return None

def set(addr):
    '''
    Set the address in the sockfile.
    '''
    with open(SockFilePath, 'w') as f:
        f.write(addr)

