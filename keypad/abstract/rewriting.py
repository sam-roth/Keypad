'''
Common data structures for describing automatic modifications to buffers.
'''

import abc
import pathlib
import difflib

from keypad.buffers import Buffer
from keypad.core import Signal

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


def _make_diff(old, new, fromfile, tofile):
    diff = difflib.unified_diff(old.splitlines(),
                                new.splitlines(),
                                fromfile=str(fromfile),
                                tofile=str(tofile),
                                lineterm='')

    return '\n'.join(diff)


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
        return _make_diff(buffer.text,
                          self._contents,
                          self.orig_path,
                          self.new_path)

#         diff = difflib.unified_diff(buffer.text.splitlines(),
#                                     self._contents.splitlines(),
#                                     fromfile=str(self.orig_path),
#                                     tofile=str(self.new_path),
#                                     lineterm='')
#
#         return '\n'.join(diff)
class ModificationRewrite(AbstractRewrite):
    '''
    Rewrite that performs a saved list of
    `~keypad.buffers.buffer.TextModification`s.

    Use a `RewriteBuilder` to create an instance of this class.
    '''

    def __init__(self, mods, diff, new_path, orig_path, *,
                 _use_RewriteBuilder_to_create_this=False):

        if not _use_RewriteBuilder_to_create_this:
            raise RuntimeError('Use RewriteBuilder to create an instance of '
                               'this class')

        self._mods = mods
        self._diff = diff
        self._new_path = new_path
        self._orig_path = orig_path

    @property
    def new_path(self):
        return self._new_path

    @property
    def orig_path(self):
        return self._orig_path

    def diff(self, buffer):
        return self._diff

    def perform(self, buffer):
        for mod in self._mods:
            buffer.execute(mod)






class RewriteBuilder(Buffer):
    '''
    Buffer subclass that generates a ModificationRewrite as changes are
    made.
    '''
    def __init__(self, buffer, path=None):
        '''
        :type buffer: keypad.buffers.Buffer
        '''
        super().__init__()

        self._orig_text = buffer.text
        self._mods = []

        self.insert((0, 0), self._orig_text)
        self.text_modified.connect(self._on_text_modified)
        self.path = path


    def _on_text_modified(self, modification):
        '''
        :type modification: keypad.buffers.buffer.TextModification
        '''
        self._mods.append(modification)

    @classmethod
    def from_path(cls, path, *, codec_errors='strict'):
        buff = Buffer()
        buff.append_from_path(path, codec_errors=codec_errors)
        return cls(buff, path)

    @classmethod
    def from_text(cls, text, path=None):
        buff = Buffer.from_text(text)
        return cls(buff, path)

    def build(self):
        return ModificationRewrite(self._mods,
                                   _make_diff(self._orig_text, self.text, self.path, self.path),
                                   self.path,
                                   self.path,
                                   _use_RewriteBuilder_to_create_this=True)
        

