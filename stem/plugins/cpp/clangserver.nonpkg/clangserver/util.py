

def first(xs):
    it = iter(xs)
    try:
        return next(it)
    except StopIteration:
        raise IndexError(0)
