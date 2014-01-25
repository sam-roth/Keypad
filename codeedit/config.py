

from .api import *



submenu(0, 'File')

menu(0,     'File/New',     'new',          keybinding=Keys.ctrl.n)
menu(10,    'File/Open',    'gui_edit',     keybinding=Keys.ctrl.o)
menu(20,    'File/Save',    'write',        keybinding=Keys.ctrl.s)


submenu(30, 'Window')

menu(0,     'Activate Commandline', 'activate_cmdline', keybinding=Keys.ctrl.semicolon)


