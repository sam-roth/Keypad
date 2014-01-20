

import types
from ..buffers import Buffer
from ..qt.buffer_set import BufferSetView
from ..core.responder import Responder, responds
from ..core import commands
from . import behavior



class BufferSetController(Responder):
    def __init__(self, view):
        super().__init__()

        self._buffer_controllers = set()
        self._active_buffer_controller = None
        self.view = view
        view.next_responder = self

        self.view.active_tab_changed.connect(self._after_active_tab_change)

            

    def _after_active_tab_change(self, view):
        print('active tab change', view)
        if view is not None:
            self.next_responder = view.controller
            self._active_buffer_controller = view.controller
            self._after_buffer_modified_changed()
            self.view.path = view.controller.path

    def _after_buffer_modified_changed(self, val=None):
        self.view.modified = self._active_buffer_controller.is_modified
    
    @responds(commands.new_cmd)
    def open(self, path=None):
        bcontr = self.find(path) if path is not None else None
        if bcontr is None:
            from . import controller
            view = self.view.add_buffer_view()
            bcontr = controller.Controller(view, Buffer())
            bcontr.modified_was_changed.connect(self._after_buffer_modified_changed)

            if path is not None:
                with bcontr.history.ignoring():
                    bcontr.replace_from_path(path)

            self._after_active_tab_change(view)

        else:
            self.view.active_view = bcontr.view

        self.add_buffer_controller(bcontr)
        return bcontr

    @responds(commands.set_tag)
    def set_tag(self):
        tag_str = self.view.show_input_dialog('Set tags (DEBUGGING ONLY!!!). Use Python kwargs-style expression.')
        if tag_str:
            tags = eval('dict({})'.format(tag_str))
            self._active_buffer_controller.add_tags(**tags)


    
    @responds(commands.open_cmd)
    def run_open_dialog(self):
        path = self.view.run_open_dialog()
        if path:
            return self.open(path)
        else:
            return None

    def find(self, path):
        for c in self._buffer_controllers:
            print(c.path, path)
            if c.path == path:
                return c

    def add_buffer_controller(self, buffer_controller):
        self._buffer_controllers.add(buffer_controller)
        buffer_controller.buffer_set = self

    def remove_buffer_controller(self, buffer_controller):
        self._buffer_controllers.remove(buffer_controller)
        buffer_controller.buffer_set = None

    @property
    def buffer_controllers(self): return frozenset(self._buffer_controllers)
    


def main():

    import logging
    from PyQt4 import Qt
    import sys

    logging.basicConfig(level=logging.DEBUG)
    app = Qt.QApplication(sys.argv)


    
    c = BufferSetController(BufferSetView())
    c.view.raise_()
    c.view.show()

    app.exec_()

if __name__ == '__main__':
    main()
