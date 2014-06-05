
import sys
import os
import os.path

if sys.path and not sys.path[0]:
    del sys.path[0]

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), # stem/core/processmgr
                                                os.pardir,                 # stem/core
                                                os.pardir,                 # stem/
                                                os.pardir)))

from stem.core.processmgr.server import main
main()





