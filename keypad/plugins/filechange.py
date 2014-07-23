'''
File change monitor
'''

from keypad.api import Plugin, register_plugin
from keypad.abstract.asyncmsg import AbstractMessageBarTarget, MessageBar
from keypad.abstract.application import (app, 
                                         AbstractApplication,
                                         MessageBoxKind)
from weakref import WeakKeyDictionary

import time
import os.path

last_unmodified_time = WeakKeyDictionary()

def editor_modified_changed(editor):
    if not editor.is_modified and editor.path is not None:
        last_unmodified_time[editor] = os.path.getmtime(str(editor.path))

def editor_activated(editor):
    if editor.path is not None:
        try:
            mt = last_unmodified_time[editor]
        except KeyError:
            pass
        else:
            if not editor.path.exists():
                # mark the buffer as modified, since the contents no longer reflect the last-saved state
                editor.buffer_controller.is_modified = True
                # prevent message from appearing more than once
                del last_unmodified_time[editor]
                _show_erased_warning(editor)
            else:
                nmt = os.path.getmtime(str(editor.path))
                last_unmodified_time[editor] = nmt
                if nmt > mt:
                    editor.activate()
                    if isinstance(editor, AbstractMessageBarTarget):
                        _show_message_bar(editor)
                    else:
                        _show_message_box(editor)

def _show_message_bar(editor):
    RELOAD, DISMISS, CANCEL, DISCARD = 'Reload', 'Dismiss', 'Cancel', 'Discard and Reload'

    mbar = MessageBar(title='File contents have changed on disk.', 
                      choices=[RELOAD, DISMISS])
    def first_callback(result):
        if result == RELOAD:
            if editor.is_modified:
                mbar = MessageBar(title='Reloading will erase your unsaved changes.',
                                  choices=[CANCEL, DISCARD])
                def second_callback(result):
                    if result == DISCARD:
                        editor.load(editor.path)

                mbar.add_callback(second_callback)
                editor.show_message_bar(mbar)
            else:
                editor.load(editor.path)
    mbar.add_callback(first_callback)
    editor.show_message_bar(mbar)

def _show_erased_warning(editor):
    if isinstance(editor, AbstractMessageBarTarget):
        editor.show_message_bar(MessageBar(title='This file has been deleted.', 
                                           choices=['Dismiss']))
    else:
        app().message_box(parent=editor, 
                          text='This file has been deleted.',
                          choices=['Dismiss'],
                          kind=MessageBoxKind.warning)


def _show_message_box(editor):
    res = app().message_box(editor, 
                            'File contents have changed on disk.',
                            ['Reload', 'Dismiss'],
                            kind=MessageBoxKind.warning)
    if res == 'Reload':
        if editor.is_modified:
            res = app().message_box(editor,
                                    'Reloading will erase your unsaved changes.',
                                    ['Cancel', 'Discard and Reload'],
                                    kind=MessageBoxKind.warning)
            if res != 'Cancel':
                editor.load(editor.path)
        else:
            editor.load(editor.path)




def editor_created(editor):
    editor.is_modified_changed.connect(editor_modified_changed,
                                       add_sender=True)

    editor.editor_activated.connect(editor_activated,
                                    add_sender=True)

    editor.saved.connect(editor_modified_changed, add_sender=True)


@register_plugin
class FileChangePlugin(Plugin):
    name = 'File Change Monitor'
    author = 'Sam Roth'

    def attach(self):
        self.app.editor_created.connect(editor_created)

    def detach(self):
        self.app.editor_created.disconnect(editor_created)

