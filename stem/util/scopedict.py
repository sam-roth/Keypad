


def keysplit(k):
    if isinstance(k, str):
        return tuple(k.split('.'))
    else:
        return k

_sentinel = object()
def most_specific(d, key, keysplit=keysplit, default=_sentinel):
    ks = keysplit(key)
    for i in range(len(ks)):
        subkey = ks[:len(ks) - i]
        result = d.get(subkey, _sentinel)
        if result is not _sentinel:
            return result
    else:
        if default is _sentinel:
            raise KeyError(key)
        else:
            return default

def splitkeys(d, keysplit=keysplit):
    return {keysplit(k): v for (k, v) in d.items()}




