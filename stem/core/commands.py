

from .command   import Command
from .key       import Keys

new_cmd                     = Command('New',                Keys.ctrl.n,            menu_hier='File')
open_cmd                    = Command('Open',               Keys.ctrl.o,            menu_hier='File')
save_cmd                    = Command('Save',               Keys.ctrl.s,            menu_hier='File')

set_cmd                     = Command('Set')

activate_cmdline            = Command('Activate Commandline', Keys.ctrl.semicolon,  menu_hier='Tools')

set_trace                   = Command('Set Trace',          Keys.ctrl.alt.meta.t,   menu_hier='Debug')

set_tag                     = Command('Set Tag',            Keys.ctrl.shift.t,      menu_hier='Buffer')

