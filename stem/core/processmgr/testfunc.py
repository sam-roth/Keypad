
def say_hello(s):
    print('Hello, world!')
    
    return 'ok'

    
def raise_exc(s):
    raise RuntimeError('error')
    
def make_qcoreapp(s):
    from PyQt4 import Qt
    import sys
    
    app = Qt.QCoreApplication(sys.argv)
    s.app = app
    
    return app.applicationPid()
    