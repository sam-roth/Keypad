

from .api import *

from .plugins import pycomplete
from .plugins.cpp import completer, syntax
from .plugins import cmdline_history
from .plugins.qprint import pageview
from .plugins.semantics import syntax
from .plugins import indent





submenu(0, 'File')

menu(1,
     'File/New',
     'new',
     keybinding=Keys.ctrl.n)
     
menu(2,    
     'File/Open',
     'gui_edit',
     keybinding=Keys.ctrl.o)
     
menu(3,    
     'File/Save',
     'gui_save',
     keybinding=Keys.ctrl.s)
menu(4,
     'File/Close',
     'gui_quit',
     keybinding=Keys.ctrl.w)

submenu(1, 'Edit')

menu(0,
     'Edit/Undo',
     'undo',
     keybinding=Keys.ctrl.z)
menu(1,
     'Edit/Redo',
     'redo',
     keybinding=Keys.ctrl.shift.z)
menu(2,
     'Edit/Copy',
     'clipboard_copy',
     keybinding=Keys.ctrl.c)
     
menu(3,    
     'Edit/Paste',
     'clipboard_paste',
     keybinding=Keys.ctrl.v)

menu(4,    
     'Edit/Complete',
     'complete',
     keybinding=Keys.meta.space)

menu(5,
     'Edit/Indent',
     'indent_block',
     keybinding=Keys.tab)
menu(5.1,
     'Edit/Dedent',
     'indent_block',
     -1,
     keybinding=Keys.shift.tab)
menu(5.2,
     'Edit/Align New Line',
     'newline_aligned',
     keybinding=Keys.ctrl.return_)
menu(5.5,
     'Edit/Toggle Comment',
      'comment_toggle',
      keybinding=Keys.ctrl.slash)


submenu(2, 'Window')

menu(0,
     'Window/Activate Commandline',
      'activate_cmdline',
      keybinding=Keys.ctrl.semicolon)
menu(1,
     'Window/Select Next Tab',
     'next_tab',
     1,
     keybinding=Keys.ctrl.braceright)
menu(2,
     'Window/Select Previous Tab',
     'next_tab',
     -1,
     keybinding=Keys.ctrl.braceleft)


