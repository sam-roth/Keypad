

from .signal import Signal
from .key import Keys


class Command(object):

    _instances = set()

    def __init__(self, name, keybinding=None, menu_hier='Commands'):
        self.name = name
        self.keybinding = keybinding
        self.menu_hier = menu_hier
        Command._instances.add(self)

    
    @classmethod
    def instances(cls):
        return frozenset(cls._instances)

    def __repr__(self):
        return 'Command(name=%r, keybinding=%r, menu_hier=%r)' % (self.name, self.keybinding, self.menu_hier)

    

new_cmd                     = Command('New',                Keys.ctrl.n,            menu_hier='File')
open_cmd                    = Command('Open',               Keys.ctrl.o,            menu_hier='File')
save_cmd                    = Command('Save',               Keys.ctrl.s,            menu_hier='File')


set_tag                     = Command('Set Tag',            Keys.ctrl.shift.t,      menu_hier='Buffer')


