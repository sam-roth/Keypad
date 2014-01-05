

import collections
import inspect

class ImmutableListView(collections.Sequence):
    def __init__(self, list_):
        self._list =  list_

    def __len__(self):
        return len(self._list)

    def __getitem__(self, i):
        return self._list[i]


