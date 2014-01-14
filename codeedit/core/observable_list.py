
import collections.abc
from .signal import Signal

class ObservableList(collections.abc.MutableSequence):

    @Signal
    def items_will_change(self, slice_, value): 
        pass

    @Signal
    def items_did_change(self, slice_): 
        pass

    
    @Signal
    def will_remove_items(self, slice_):
        pass

    @Signal
    def did_remove_items(self, slice_):
        pass


    @Signal
    def will_insert_items(self, index, items):
        pass

    @Signal
    def did_insert_items(self, index, items):
        pass




    def __init__(self, items=[]):
        self._data = list(items)

    def __getitem__(self, slice_):
        return self._data.__getitem__(slice_)

    def __setitem__(self, slice_, value):
        self.items_will_change(slice_, value)
        self._data.__setitem__(slice_, value) 
        self.items_did_change(slice_)

    def __delitem__(self, slice_):
        self.will_remove_items(slice_)
        self._data.__delitem__(slice_)
        self.did_remove_items(slice_)

    
    def __len__(self):
        return self._data.__len__()

    def insert(self, index, object_):
        l = [object_]
        self.will_insert_items(index, l)
        self._data.insert(index, object_)
        self.did_insert_items(index, l)

    def extend(self, iterable):
        items = list(iterable)
        idx = len(self)
        self.will_insert_items(idx, items)
        self._data.extend(items)
        self.did_insert_items(idx, items)

