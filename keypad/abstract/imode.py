
import abc
from keypad.core.attributed_string import AttributedString
from keypad.buffers.cursor import Cursor
from keypad.buffers.span import Span

class AbstractInteractionMode(metaclass=abc.ABCMeta):

    def __init__(self, bctl):
        '''
        :type bctl: keypad.control.buffer_controller.BufferController
        '''
        from keypad import options

        self.config = bctl.config
        self.buffer_controller = bctl

        self.__settings = options.GeneralSettings.from_config(self.config)

        if self.buffer_controller.interaction_mode is not None:
            self.buffer_controller.interaction_mode.detach()
            self.buffer_controller.interaction_mode = self

        v = self._view
        self.__connections = [(v.key_press,            self._on_key_press),
                              (v.mouse_down_char,      self._on_mouse_down),
                              (v.mouse_move_char,      self._on_mouse_move),
                              (v.input_method_preedit, self._on_input_method_preedit),
                              (v.input_method_commit,  self._on_input_method_commit)]


        for src, dst in self.__connections:
            src.connect(dst)

        self._show_default_modeline()
        self.__preedit_span = None

    def _show_modeline(self, text):
        if not isinstance(text, AttributedString):
            text = AttributedString(text, **dict(self.__settings.modeline_attrs))
        self._view.modelines = [text]

    @property
    def display_name(self):
        return type(self).__name__

    def _show_default_modeline(self):
        path = self.buffer_controller.path
        if path is None:
            path = '<unsaved>'
        else:
            path = str(path)
            if len(path) > 20:
                path = '…' + path[-19:]


        y, x = self._selection.pos
        loc_hint = '{0}:{1}:{2}'.format(path, y+1, x+1)

        self._show_modeline('{:<50} [{}]'.format(loc_hint, self.display_name))
        
    def show_error(self, text):
        from .application import app

        app().beep()
        self._show_modeline(AttributedString(
            text,
            bgcolor='#dc322f',
            color='#fdf6e3'
        ))
        self.controller.refresh_view()

    def detach(self):
        for src, dst in self.__connections:
            try:
                src.disconnect(dst)
            except KeyError:
                pass
        self._detach()


    # convenience properties
    @property
    def _selection(self):
        return self.buffer_controller.selection

    @property
    def _history(self):
        return self.buffer_controller.history

    @property
    def _view(self):
        return self.buffer_controller.view

    # abstract methods
    @abc.abstractmethod
    def _on_key_press(self, event):
        pass

    @abc.abstractmethod
    def _on_mouse_down(self, line, col):
        pass

    @abc.abstractmethod
    def _on_mouse_move(self, buttons, line, col):
        pass

    @abc.abstractmethod
    def _detach(self):
        pass


    # overrideable methods
    def _on_input_method_preedit(self, text):
        c = self._selection.insert_cursor
        with c.manip.history.scratchpad():
            sc = c.clone()
            sc.chirality = Cursor.Chirality.Left
            c.insert(text)
            self.__preedit_span = Span(sc, c)
            self.__preedit_span.set_attributes(lexcat='search')
        self._show_default_modeline()

    def _on_input_method_commit(self, 
                                preedit_text,
                                replace_start, replace_stop,
                                replace_text):
        c = self._selection.insert_cursor
        with c.manip.history.transaction():
            if self.__preedit_span is not None:
                self.__preedit_span.text = replace_text
                self.__preedit_span.set_attributes(lexcat=None)
                self.__preedit_span = None
            else:
                c.insert(replace_text)
        self._show_default_modeline()


