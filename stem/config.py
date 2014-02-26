
try:
    import stemrc
except ImportError:
    pass


from .api import *

import pathlib


import stem.plugins
load_plugins(stem.plugins.__path__, 'stem.plugins.')

import platform 


if platform.system() == 'Darwin':
    PortCtrl        = Keys.meta
    PortDiamond     = Keys.ctrl
    PortMeta        = Keys.ctrl
else:
    PortCtrl        = Keys.ctrl
    PortDiamond     = Keys.ctrl
    PortMeta        = Keys.meta



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

menu(1.5,
     'Edit/Cut',
     'clipboard_cut',
     keybinding=Keys.ctrl.x)

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
     keybinding=PortCtrl.space)

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

menu(5.3,
     'Edit/Dedent or Backspace',
     'dedent_or_backspace',
     keybinding=Keys.backspace.optional(Keys.shift))

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


submenu(3, 'Semantics')

menu(0, 'Semantics/Find Declaration', 'find_declaration', keybinding=Keys.shift.f3)
menu(1, 'Semantics/Find Definition',  'find_definition', keybinding=Keys.f3)



import stem.plugins.server
stem.plugins.server.start_server()
