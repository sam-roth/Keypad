

from .api import *



submenu(0, 'File')

menu(0,     'File/New',     'new',          keybinding=Keys.ctrl.n)
menu(10,    'File/Open',    'gui_edit',     keybinding=Keys.ctrl.o)
menu(20,    'File/Save',    'write',        keybinding=Keys.ctrl.s)

submenu(10, 'Edit')

menu(0,     'Edit/Undo',    'undo',             keybinding=Keys.ctrl.z)
menu(0,     'Edit/Redo',    'redo',             keybinding=Keys.ctrl.shift.z)
menu(10,    'Edit/Copy',    'clipboard_copy',   keybinding=Keys.ctrl.c)
menu(20,    'Edit/Paste',   'clipboard_paste',  keybinding=Keys.ctrl.v)


submenu(30, 'Window')

menu(0,     'Activate Commandline', 'activate_cmdline', keybinding=Keys.ctrl.semicolon)


