


def main():
    from . import config, options
    import importlib
    importlib.import_module(options.DefaultDriverMod).main()

if __name__ == '__main__':
    main()
