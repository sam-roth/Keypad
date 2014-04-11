
if __name__ == '__main__':
    import sys
    # remove empty curent directory entry from path
    sys.path = [entry for entry in list(sys.path) if entry]
    from .server import main
    main()