

from abc import *



class Operation(metaclass=ABCMeta):
    def __init__(self):
        self._executed = False
       
    @property
    def description(self): 
        return None

    @abstractmethod
    def execute(self):
        self._executed = True

    @abstractmethod
    def reverse(self):
        self._executed = False

    def coalesce(self, other):
        '''
        If `self` can be combined with `other`, return the combination of 
        `self` and `other`, otherwise return `None`.

        An implementation of `coalesce()` may be destructive, but is not 
        required to be destructive.

        `other` is an operation that occurred before this one.
        '''

        return None


class FunctionOperation(Operation):

    def __init__(self, execute_func, reverse_func, description=None):
        super().__init__()
        self._execute_func = execute_func
        self._reverse_func = reverse_func
        self._description = description

    @property
    def description(self):
        return self._description

    def execute(self):
        super().execute()
        self._execute_func()

    def reverse(self):
        super().reverse()
        self._reverse_func()

def operation(execute, reverse, description=None):
    return FunctionOperation(execute, reverse, description)

import logging
from . import util

    
class History(object):

    def __init__(self):
        self._operations_executed = []
        self._operations_reversed = []

    def execute(self, operation):
        #print('executing')
        assert isinstance(operation, Operation)

        logging.debug(util.dump_object(operation))

        operation.execute()
        self._operations_reversed.clear()
        while self._operations_executed:
            new_operation = operation.coalesce(self._operations_executed[-1])
            if new_operation is None:
                break
            else:
                operation = new_operation
                self._operations_executed.pop()
        #print('appending operation')
        self._operations_executed.append(operation)

    def undo(self):
        self._operations_executed[-1].reverse()
        self._operations_reversed.append(self._operations_executed.pop())

    def redo(self):
        self._operations_reversed[-1].execute()
        self._operations_executed.append(self._operations_reversed.pop())
    

    @property
    def can_undo(self): return bool(self._operations_executed)

    @property
    def can_redo(self): return bool(self._operations_reversed)


    @property
    def undo_description(self):
        if self._operations_executed:
            return self._operations_executed[-1].description
        else:
            return None


    @property
    def redo_description(self):
        if self._operations_reversed:
            return self._operations_reversed[-1].description
        else:
            return None



        

__all__ = ['Operation', 'operation', 'History']
        
