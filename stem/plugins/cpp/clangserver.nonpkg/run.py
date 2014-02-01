

#import clangserver_pathsetup
import logging

import clangserver
import clangserver.net.rpcserver
import clangserver.net.rpcclient

import sys

logging.basicConfig(level=logging.DEBUG)

if sys.argv[1].startswith('http'):
    clangserver.net.rpcserver.main()
else:
    clangserver.net.rpcclient.main()

#clangserver.listmethods.main()
