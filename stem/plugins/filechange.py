'''
File change monitor
'''


from stem.abstract.application import app, AbstractApplication
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
            nmt = os.path.getmtime(str(editor.path))
            last_unmodified_time[editor] = nmt
            if nmt > mt:
                editor.activate()
                res = app().message_box(editor, 
                                        'Warning: file contents have changed on disk.',
                                        ['Reload', 'Dismiss'])
                if res == 'Reload':
                    if editor.is_modified:
                        res = app().message_box(editor,
                                                'Reloading will erase your unsaved changes.',
                                                ['Cancel', 'Discard and Reload'])
                        if res != 'Cancel':
                            editor.load(editor.path)
                    else:
                        editor.load(editor.path)




def editor_created(editor):
    editor.is_modified_changed.connect(editor_modified_changed,
                                       add_sender=True)

    editor.editor_activated.connect(editor_activated,
                                    add_sender=True)


def app_created(_):
    app().editor_created.connect(editor_created)


AbstractApplication.application_created.connect(app_created)

