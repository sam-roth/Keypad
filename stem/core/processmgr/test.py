

from .client import ServerProxy, AsyncServerProxy
import pickle
from . import testfunc




if __name__ == '__main__':
    from .server import ShutdownMessage
    from PyQt4 import Qt
    import sys
    app = Qt.QCoreApplication(sys.argv)
    import time
    sp = AsyncServerProxy()
    with sp:
        f = sp.submit(testfunc.say_hello)
        print(f.result())
#         f = sp.run_async(testfunc.raise_exc)
#         print(f.result())        
        
        print(sp.submit(testfunc.make_qcoreapp).result())
        
#         sp.send(testfunc.raise_exc)

#     pickle.dump(testfunc.say_hello, sp.fout)
#     sp.fout.flush()
#     pickle.load(sp.fin)
#     pickle.dump(ShutdownMessage(), sp.fout)
#     sp.fout.flush()
    