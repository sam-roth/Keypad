


def main():
    import os.path
    thirdparty = os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir, 'third-party'))
    import sys
    sys.path.insert(0, thirdparty)
    from . import config, options
    import importlib
    importlib.import_module(options.DefaultDriverMod).main()

if __name__ == '__main__':
    main()
