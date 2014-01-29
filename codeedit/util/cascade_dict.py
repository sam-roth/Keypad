


from collections.abc import Mapping


class CascadeDict(Mapping):
    def __init__(self):
        self.dicts = []

    def __getitem__(self, key):
        result = None
        for d in self.dicts:
            result = d.get(key)
            if result is not None:
                return result
        else:
            raise KeyError(key)
    
    def keyset(self):
        keys = set()
        for d in self.dicts:
            keys.update(d.keys())

        return keys

    def __iter__(self):
        yield from self.keyset()

    def __len__(self):
        return len(self.keyset())
