'''
This module loads user configuration from ``keypadrc`` as well
as providing basic built-in configuration.
'''

import os

if not os.environ.get('STEM_NO_RC') and not os.environ.get('KEYPAD_NO_RC'):

    for mod in ['stemrc', 'keypadrc']:
        try:
            exec('import {}'.format(mod))
        except ImportError as exc:
            if exc.name != mod:
                import traceback
                traceback.print_exc()


from .api import *

import pathlib


import keypad.plugins
load_plugins(keypad.plugins.__path__, 'keypad.plugins.')

import platform 


if platform.system() == 'Darwin':
    PortCtrl        = Keys.meta
    PortDiamond     = Keys.ctrl
    PortMeta        = Keys.ctrl
else:
    PortCtrl        = Keys.ctrl
    PortDiamond     = Keys.ctrl
    PortMeta        = Keys.meta




menu(0, 'File')

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

menu(1, 'Edit')

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

menu(5.5,
     'Edit/Toggle Comment',
      'comment_toggle',
      keybinding=Keys.ctrl.slash)


menu(6,
     'Edit/Find',
     'set_cmdline', 'f ',
     keybinding=Keys.ctrl.f)

menu(7, 
     'Edit/Move to Opening Brace',
     'open_brace',
     keybinding=Keys.ctrl.nine)

menu(7.1,
     'Edit/Move to Closing Brace',
     'close_brace',
     keybinding=Keys.ctrl.zero)

menu(8,
     'Edit/Move to Previous Position',
     'previous_cursor_position',
     keybinding=Keys.ctrl.bracketleft)

menu(8,
     'Edit/Move to Next Position',
     'next_cursor_position',
     keybinding=Keys.ctrl.bracketright)

    
menu(2, 'Window')

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

menu(3, 'View')
menu(0, 'View/Increase Font Size', 'adjust_font_size', 1, keybinding=Keys.ctrl.plus)
menu(1, 'View/Decrease Font Size', 'adjust_font_size', -1, keybinding=Keys.ctrl.minus)

menu(4, 'Semantics')

menu(0, 'Semantics/Find Declaration', 'find_declaration', keybinding=Keys.shift.f3)
menu(1, 'Semantics/Find Definition',  'find_definition', keybinding=Keys.f3)
menu(2, 'Semantics/Show Diagnostic', 'show_diagnostics', keybinding=Keys.f2)

