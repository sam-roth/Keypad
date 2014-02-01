

class Msg(object):
    def __call__(self, conn):
        abstract


class HelloMsg(Msg):
    def __call__(self, conn):
        print 'Hello, world!'

class ExitMsg(Msg):
    def __call__(self, conn):
        import sys
        print 'exit'
        sys.exit()


hello_msg = HelloMsg()

