
from ..             import util
from ..core         import errors

from contextlib     import contextmanager
import warnings



class BufferHistory(object):
    def __init__(self, buff):
        '''
        :type change: codeedit.buffer.Buffer
        '''

        self._ignore_changes = False
        self._transaction_changes = None
        self._changesets = []
        self._changesets_reversed = []
        self.buff = buff

        self.buff.text_modified.connect(self._on_buffer_text_modified)


    def _begin_transaction(self):

        if self._transaction_changes is not None:
            raise RuntimeError('Transaction already in progress.')
        
        
        self._transaction_changes = []

    
    def _on_buffer_text_modified(self, change):
        '''
        :type change: codeedit.buffer.TextModification
        '''

        if self._ignore_changes: return

        if self._transaction_changes is None:
            warnings.warn('Buffer modified outside of transaction.')

            with self.transaction():
                self._transaction_changes.append(change)
        else:
            self._transaction_changes.append(change)

    
    def _commit_transaction(self):
        if self._transaction_changes:
            self._changesets.append(self._transaction_changes)
            self._changesets_reversed.clear()
        self._transaction_changes = None

    
    @contextmanager
    def ignoring(self):
        self._ignore_changes = True
        try:
            yield
        finally:
            self._ignore_changes = False


    
    def undo(self):
        if not self._changesets:
            raise errors.CantUndoError("Can't undo.")

        cs = self._changesets[-1]

        with self.ignoring():
            for chg in reversed(cs):
                self.buff.reverse(chg)

        self._changesets.pop()
        self._changesets_reversed.append(cs)

    def redo(self):
        if not self._changesets_reversed:
            raise errors.CantRedoError("Can't redo.")

        cs = self._changesets_reversed[-1]
        with self.ignoring():
            for chg in cs:
                self.buff.execute(chg)
        self._changesets_reversed.pop()
        self._changesets.append(cs)

    
    def clear(self):
        self._changesets.clear()
        self._changesets_reversed.clear()


    @contextmanager
    def transaction(self):
        self._begin_transaction()
        try:
            yield 
        finally:
            self._commit_transaction()



def main():
    from . import buffer 

    buff = buffer.Buffer()
    hist = BufferHistory(buff)

    with hist.transaction():
        buff.insert((0,0), 'Hello,\n')
        buff.insert((1,0), 'world!')

    with hist.transaction():
        buff.insert((0,5), '\n!!!\n')

    print(buff.dump())

    hist.undo()

    print(buff.dump())

    hist.redo()
    print(buff.dump())

    hist.undo()

    print(buff.dump())

    hist.undo()
    print(buff.dump())


if __name__ == '__main__':
    main()
     
