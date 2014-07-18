import abc
from ..control import BufferController
from ..buffers import Buffer
from .application import app, AbstractApplication
from ..control.interactive import interactive
from ..core import Signal
import logging

class AbstractEditor(metaclass=abc.ABCMeta):


    def __init__(self, view, config):
        self.__view = view
        self.__buffer = Buffer()
        self.__buffer_controller = BufferController(None,
                                                    view,
                                                    self.__buffer,
                                                    True,
                                                    config)

        self.buffer_controller.modified_was_changed.connect(self.__modified_changed)
        self.buffer_controller.path_changed.connect(self.path_changed)
        self.config = config
        
    @Signal
    def editor_activated(self):
        pass

        
    def __modified_changed(self, value):
        self.is_modified_changed()

    @abc.abstractmethod
    def activate(self):
        '''
        Bring this editor to the front and give it focus.
        '''

    @property
    def buffer_controller(self):
        return self.__buffer_controller

    @abc.abstractmethod
    def kill(self):
        '''
        Immediately close the editor without prompting the user.
        '''

    @property
    def is_modified(self):
        '''
        Returns True iff the editor's contents reflect the last-saved state.
        '''
        r = self.__buffer_controller.is_modified
        return r

    @Signal
    def is_modified_changed(self):
        pass

    @Signal
    def saved(self):
        pass

    @Signal
    def path_changed(self):
        pass

    @property
    def path(self):
        '''
        Returns the current path of the file that this editor will save to, or None
        if there is no such file.
        '''
        return self.__buffer_controller.path

    @path.setter
    def path(self, value):
        if value is not None:
            import pathlib
            value = pathlib.Path(value)
            
        self.__buffer_controller.add_tags(path=value)


    def save(self, path, *, codec_errors='strict', prompt_on_error=True):
        '''
        Save the file to the path given.
        '''
        try:
            self.__buffer_controller.write_to_path(path, codec_errors=codec_errors)
        except UnicodeEncodeError as exc:
            if not prompt_on_error:
                raise
            res = app().message_box(self,
                                    'This buffer contains non-plaintext characters: ' + str(exc),
                                    ['Write As-Is', 'DELETE Unknown Characters', 'Cancel'],
                                    kind=AbstractApplication.MessageBoxKind.warning)
            if res == 'Write As-Is':
                self.__buffer_controller.write_to_path(ed.path, codec_errors='surrogateescape')
            elif res == 'DELETE Unknown Characters':
                self.__buffer_controller.write_to_path(ed.path, codec_errors='ignore')
            else:
                raise
        except OSError as exc:
            if not prompt_on_error:
                raise
            res = app().message_box(self,
                                    'An error occurred while trying to save the file: ' + str(exc),
                                    ['Cancel (the file will remain open)'],
                                    kind=AbstractApplication.MessageBoxKind.warning)
            raise

        self.saved()
        
    def load(self, path, *, codec_errors='strict'):
        '''
        Load the file from the path given.
        '''
        from ..core.notification_queue import run_in_main_thread

        with self.__buffer_controller.history.transaction():
            self.__buffer_controller.replace_from_path(path, create_new=True, codec_errors=codec_errors)
            self.__buffer_controller.history.clear()

        self.__buffer_controller.is_modified = False


@interactive('gui_save', 'gsave', 'gsv')
def gui_save(ed: AbstractEditor):
    from .application import app
    app().save(ed)

