'''
Common data structures for describing automatic modifications to buffers.
'''

import abc
import pathlib
import difflib

_default = object()

class AbstractRewrite(metaclass=abc.ABCMeta):

    @abc.abstractproperty
    def orig_path(self):
        '''
        The path to the file that should be rewritten. If the file is
        unnamed, this property must be None and the file must be the
        primary file.

        :rtype: pathlib.Path
        '''

    @property
    def new_path(self):
        '''
        Return the path to which the file should be moved. If the file
        should not be moved, this is the same as orig_path.
        '''
        return self.orig_path

    @abc.abstractmethod
    def perform(self, buffer):
        '''
        Perform the rewrite. Does not write the changes to disk.

        :preconditions: Assumes that the buffer provided is the one
                        specified by the `path` property, and that there
                        is an active history transaction.
        '''


    @abc.abstractmethod
    def diff(self, buffer):
        '''
        Return a unified diff of the existing state of the file and the
        state after the modifications. This should be performed without
        modifying the buffer.
        '''

class ReplaceFileRewrite(AbstractRewrite):
    '''
    The simplest rewrite: Replace the entire file's contents.

    :param orig_path:   The path to the existing file, or None for the
                        primary file if the primary file does not yet have a path.    
    :param contents:    The new text for the file.
    :param new_path:    If provided, the path to which the file should be
                        moved.    
    '''
    def __init__(self, orig_path, contents, *, new_path=_default):
        self._orig_path = pathlib.Path(orig_path)
        self._contents = contents
        self._new_path = new_path if new_path is not _default else orig_path

    @property
    def new_path(self):
        return self._new_path

    @property
    def orig_path(self):
        return self._orig_path

    def perform(self, buffer):
        from keypad.buffers import Cursor

        begin = Cursor(buffer, (0, 0))
        end = Cursor(buffer).last_line().end()

        begin.remove_to(end)
        begin.insert(self._contents)

    def diff(self, buffer):
        diff = difflib.unified_diff(buffer.text.splitlines(),
                                    self._contents.splitlines(),
                                    fromfile=str(self.orig_path),
                                    tofile=str(self.new_path),
                                    lineterm='')

        return '\n'.join(diff)


