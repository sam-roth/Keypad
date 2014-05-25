
from ..control.interactive import interactive
from .application import app, AbstractWindow, AbstractApplication
from .editor import AbstractEditor
import pathlib
import os.path

@interactive('new')
def open_new_editor(win: AbstractWindow):
    ed = app().new_editor()
    win.add_editor(ed)

@interactive('e', 'edit')
def edit(win: AbstractWindow, path: 'Path', line=None, col=None):
    line = int(line) if line is not None else None
    col = int(col) if col is not None else None
    
    path = pathlib.Path(os.path.expanduser(str(path)))
    ed = app().find_editor(path)
    if ed is not None:
        ed.activate()
    else:
        ed = app().new_editor()
        ed.load(path)
        win.add_editor(ed)
        
    if line is not None:
        ed.buffer_controller.selection.move(line=line)
    if col is not None:
        ed.buffer_controller.selection.move(col=col)
    ed.buffer_controller.refresh_view()

@interactive('gq', 'gquit', 'gui_quit')
def gui_quit(ed: AbstractEditor):
    app().close(ed)

@interactive('gwr', 'gwrite', 'gui_write')
def gui_write(ed: AbstractEditor):
    path = app().get_save_path(ed)
    if path is not None:
        ed.save(path)

@interactive('gsv', 'gsave', 'gui_save')
def gui_save(ed: AbstractEditor):
    if ed.path is None:
        ed.path = app().get_save_path(ed)
    if ed.path is not None:
        ed.save(ed.path)

@interactive('gqa', 'gquitall', 'gui_quit_all')
def gui_quit_all(win: AbstractWindow):
    win.close()

@interactive('next_tab')
def next_tab(win: AbstractWindow, n=1):
    n = int(n)
    
    if n > 0:
        for _ in range(n):
            win.next_tab()
    else:
        for _ in range(-n):
            win.prev_tab()


