
from ..             import util
from ..core         import errors, Signal

from contextlib     import contextmanager
import warnings
import re
import functools
import logging

class HistoryCoalescencePolicy(object):
    WordRegex = re.compile(r'^(\w*|[^\w]*)$') # A word is either all word chars or no word chars.
    Skip = 5 # number of changesets to skip before coalescing
    def __init__(self):
        pass

    @staticmethod
    def _coalesce_changeset(x, y):
        if len(x) != 1 or len(y) != 1:
            return None
        else:
            return x[0].coalesce(y[0])

    def coalesce(self, changesets):
        processed = changesets[-self.Skip:]
        del changesets[-self.Skip:]

        if len(changesets) >= 2:
            proposed = self._coalesce_changeset(changesets[-1], changesets[-2])
            if proposed:
                text = proposed.insert or proposed.remove
                if self.WordRegex.match(text):
                    del changesets[-2:]
                    changesets.append([proposed])

        changesets.extend(processed)

        return changesets

        
class BufferHistory(object):
    def __init__(self, buff):
        '''
        :type change: keypad.buffer.Buffer
        '''

        self._ignore_changes = False
        self._transaction_changes = None
        self._changesets = []
        self._changesets_reversed = []
        self._clear_at_end_of_transaction = False
        self._coalesce_policy = HistoryCoalescencePolicy()

        self._scratchpad = []
        self._scratchpad_active = False

        self.buff = buff
        buff.history = self
        self.buff.text_modified.connect(self._on_buffer_text_modified)


    def _begin_transaction(self):

        if self._transaction_changes is not None:
            raise RuntimeError('Transaction already in progress.')
        
        
        self._transaction_changes = []


    @contextmanager
    def scratchpad(self):
        '''
        Use the scratchpad for things like automatic indentation adjustments. It is combined with the next or current
        transaction, so that indentation adjustments don't create undo history or erase redo history.

        The scratchpad is also temporarily rolled back upon saving the buffer, preventing saving of unused indentation.
        '''
        was_active = self._scratchpad_active
        self._scratchpad_active = True
        try:
            yield
        finally:
            self._scratchpad_active = was_active


    def _on_buffer_text_modified(self, change):
        '''
        :type change: keypad.buffer.TextModification
        '''

        if self._ignore_changes: return

        if self._scratchpad_active and (self._transaction_changes is None 
                                        or not self._transaction_changes):
            self._scratchpad.append(change)
        else:
            if self._transaction_changes is None:
                warnings.warn('Buffer modified outside of transaction.')

                with self.transaction():
                    self._transaction_changes.append(change)
            else:
                self._transaction_changes.append(change)

    
    def _commit_transaction(self):
        did_anything = False
        if self._clear_at_end_of_transaction:
            self._clear_at_end_of_transaction = False
            self._changesets.clear()
            self._changesets_reversed.clear()
            self._scratchpad = []
            did_anything = True
        elif self._transaction_changes:
            # flush the scratchpad changes with the user-created changes
            self._changesets.append(self._scratchpad + self._transaction_changes)
            self._scratchpad = []
            self._changesets_reversed.clear()
            did_anything = True

        self._transaction_changes = None
        self._changesets = self._coalesce_policy.coalesce(self._changesets)
        self.transaction_committed()
        if did_anything:
            self.changes_committed()

    @Signal
    def transaction_committed(self):
        pass

    @Signal
    def changes_committed(self):
        pass
    
    @contextmanager
    def ignoring(self):
        self._ignore_changes = True
        try:
            yield
        finally:
            self._ignore_changes = False
        self.transaction_committed()


    def _rollback_scratchpad(self):
        with self.ignoring():
            scratch = self._scratchpad
            self._scratchpad = []
            self._scratchpad_active = False
            for item in reversed(scratch):
                self.buff.reverse(item)
            return scratch

    @contextmanager
    def suppress_scratchpad(self):
        '''
        Context manager that temporarily undoes all changes on the scratchpad.
        Use this when saving a file to avoid saving "scratch" changes that are just
        there to keep the cursor in the right place.
        '''
        scratch_active = self._scratchpad_active
        scratch = self._rollback_scratchpad()
        try:
            yield
        finally:
            # replay the scratchpad
            self._scratchpad_active = scratch_active
            with self.scratchpad():
                for chg in scratch:
                    self.buff.execute(chg)



    def undo(self):
        # rollback scratchpad changes, since they may interfere with undo
        self._rollback_scratchpad()

        if not self._changesets:
            raise errors.CantUndoError("Can't undo.")

        cs = self._changesets[-1]

        with self.ignoring():
            for chg in reversed(cs):
                self.buff.reverse(chg)

        self._changesets.pop()
        self._changesets_reversed.append(cs)
        self.transaction_committed()

        return cs

    def redo(self):
        # rollback scratchpad changes, since they will interfere with redo
        self._rollback_scratchpad()

        if not self._changesets_reversed:
            raise errors.CantRedoError("Can't redo.")

        cs = self._changesets_reversed[-1]
        with self.ignoring():
            for chg in cs:
                self.buff.execute(chg)
        self._changesets_reversed.pop()
        self._changesets.append(cs)
        self.transaction_committed()
        
        return cs
    
    def clear(self):
        '''
        Clear the buffer history at the end of the transaction.
        '''

        with self.rec_transaction():
            self._clear_at_end_of_transaction = True

    @contextmanager
    def transaction(self):
        self._begin_transaction()
        try:
            yield 
        finally:
            self._commit_transaction()

    
    @contextmanager
    def rec_transaction(self):
        if self._transaction_changes is not None:
            yield
        else:
            with self.transaction():
                yield


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
     
