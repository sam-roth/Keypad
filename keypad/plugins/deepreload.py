
import importlib
import pathlib
import imp
import sys
import weakref
import types

from keypad import api
from keypad.abstract.application import AbstractApplication
from keypad.abstract import asyncmsg
from keypad.core.plugin import unregister_plugin
from keypad.util.path import search_upwards, same_file
from keypad.control.command_line_interaction import writer as cmdline_writer

@api.register_plugin
class DeepReloadPlugin(api.Plugin):
    name = 'Deep Reload'
    author = 'Sam Roth'
    version = '2014.07'

    def attach(self):
        pass


    def detach(self):
        pass

    def _unsaved_err(self):
        targ = self.app.find_object(asyncmsg.AbstractMessageBarTarget)
        if not targ: return

        mbar = asyncmsg.MessageBar(title='This file must be saved before its contents '
                                         'can be reloaded.',
                                   choices=['Save', 'Dismiss'])

        @mbar.add_callback
        def callback(result):
            if result == 'Save':
                api.interactive.run('gsave')

        targ.show_message_bar(mbar)


    @api.command('reload', 'rel')
    def reload(self, 
               bctl: api.BufferController,
               modulepath=None):

        '''
        : rel[oad] [module-name]

        Hot-reload a module, or the module being edited if no module is specified.
        
        THIS COMMAND IS AS UNSAFE AS A FORD PINTO WITH A LOOSE FLOORMAT. IT MAY
        MAKE THE EDITOR UNUSABLE UNTIL IT IS RESTARTED.

        As you might expect, hot-reloading can have unexpected side effects.  One
        of these unexpected effects (that you should expect) is that singleton
        instances will get wiped out. This command performs a bit of housekeeping
        to ensure that the AbstractApplication instance survives the jump.
        Additionally, it unloads all of the plugins and reloads them, ensuring that
        new command definitions are propagated.

        It is provided because use of this command can make plugin development much
        faster. Just make sure to save your work before using it.
        '''

        if modulepath is None and (not bctl.path or bctl.is_modified):
            self._unsaved_err()
            return

        extra_path = None
        if modulepath is None:
            modroot = find_modroot(bctl.path)
            if modroot == bctl.path:
                modulepath = bctl.path.stem
            else:
                modroot_parents = [x.stem for x in modroot.parents if x.stem]
                path_parents = [x.stem for x in reversed(bctl.path.parents) if x.stem]
                hier = path_parents[len(modroot_parents)-1:]
                modulepath = '.'.join(hier + [bctl.path.stem])

            # We'll use this for setting the system path.
            extra_path = pathlib.Path(modroot).absolute().parent
            if any(same_file(extra_path, p)
                   for p in sys.path):
                extra_path = None



        app = self.app
        conf_root = api.Config.root
        reloaded_dict = {}
        try:
            if extra_path is not None:
                extra_path = str(extra_path)
                sys.path.insert(0, extra_path)
            root = importlib.import_module(modulepath)
            superreload(root, old_objects=reloaded_dict)
        finally:
            if extra_path is not None:
                sys.path.remove(extra_path)
            # it's very bad for this to get wiped out ;)
            AbstractApplication._instance = app
            api.Config.root = conf_root

        cmdline_writer.write('Reloaded {} objects:\n'.format(len(reloaded_dict)) +
                             '\n'.join('    {} {}'.format(*item) for item in reloaded_dict.keys()))

        for refs in reloaded_dict.values():
            for ref in refs:
                v = ref()
                if v is not None and issubclass(v, api.Plugin):
                    app.remove_plugin(v)
                    unregister_plugin(v)
                

        app.update_plugins()



def find_modroot(module):
    '''
    Find the root package __init__.py for the given module path.

    >>> find_modroot('keypad/api.py')
    PosixPath('keypad/__init__.py')
    >>> find_modroot('keypad/buffers/buffer.py')
    PosixPath('keypad/__init__.py')

    '''
    module = pathlib.Path(module)

    path = module
    for path in search_upwards(module, '__init__.py'):
        pass

    return path






PY3 = True

# The following code was taken from IPython.


if PY3:
    func_attrs = ['__code__', '__defaults__', '__doc__',
                  '__closure__', '__globals__', '__dict__']
else:
    func_attrs = ['func_code', 'func_defaults', 'func_doc',
                  'func_closure', 'func_globals', 'func_dict']


def update_function(old, new):
    """Upgrade the code object of a function"""
    for name in func_attrs:
        try:
            setattr(old, name, getattr(new, name))
        except (AttributeError, TypeError):
            pass


def update_class(old, new):
    """Replace stuff in the __dict__ of a class, and upgrade
    method code objects"""
    for key in list(old.__dict__.keys()):
        old_obj = getattr(old, key)

        try:
            new_obj = getattr(new, key)
        except AttributeError:
            # obsolete attribute: remove it
            try:
                delattr(old, key)
            except (AttributeError, TypeError):
                pass
            continue

        if update_generic(old_obj, new_obj): continue

        try:
            setattr(old, key, getattr(new, key))
        except (AttributeError, TypeError):
            pass # skip non-writable attributes


def update_property(old, new):
    """Replace get/set/del functions of a property"""
    update_generic(old.fdel, new.fdel)
    update_generic(old.fget, new.fget)
    update_generic(old.fset, new.fset)


def isinstance2(a, b, typ):
    return isinstance(a, typ) and isinstance(b, typ)


UPDATE_RULES = [
    (lambda a, b: isinstance2(a, b, type),
     update_class),
    (lambda a, b: isinstance2(a, b, types.FunctionType),
     update_function),
    (lambda a, b: isinstance2(a, b, property),
     update_property),
]


if PY3:
    UPDATE_RULES.extend([(lambda a, b: isinstance2(a, b, types.MethodType),
                          lambda a, b: update_function(a.__func__, b.__func__)),
                        ])
else:
    UPDATE_RULES.extend([(lambda a, b: isinstance2(a, b, types.ClassType),
                          update_class),
                         (lambda a, b: isinstance2(a, b, types.MethodType),
                          lambda a, b: update_function(a.__func__, b.__func__)),
                        ])


def update_generic(a, b):
    for type_check, update in UPDATE_RULES:
        if type_check(a, b):
            update(a, b)
            return True
    return False


class StrongRef(object):
    def __init__(self, obj):
        self.obj = obj
    def __call__(self):
        return self.obj


def superreload(module, reload=imp.reload, old_objects={}):
    """Enhanced version of the builtin reload function.

    superreload remembers objects previously in the module, and

    - upgrades the class dictionary of every old class in the module
    - upgrades the code object of every old function and method
    - clears the module's namespace before reloading

    """

    # collect old objects in the module
    for name, obj in list(module.__dict__.items()):
        if not hasattr(obj, '__module__') or obj.__module__ != module.__name__:
            continue
        key = (module.__name__, name)
        try:
            old_objects.setdefault(key, []).append(weakref.ref(obj))
        except TypeError:
            # weakref doesn't work for all types;
            # create strong references for 'important' cases
            if not PY3 and isinstance(obj, types.ClassType):
                old_objects.setdefault(key, []).append(StrongRef(obj))

    # reload module
    try:
        # clear namespace first from old cruft
        old_dict = module.__dict__.copy()
        old_name = module.__name__
        module.__dict__.clear()
        module.__dict__['__name__'] = old_name
        module.__dict__['__loader__'] = old_dict['__loader__']
    except (TypeError, AttributeError, KeyError):
        pass

    try:
        module = reload(module)
    except:
        # restore module dictionary on failed reload
        module.__dict__.update(old_dict)
        raise

    # iterate over all objects and update functions & classes
    for name, new_obj in list(module.__dict__.items()):
        key = (module.__name__, name)
        if key not in old_objects: continue

        new_refs = []
        for old_ref in old_objects[key]:
            old_obj = old_ref()
            if old_obj is None: continue
            new_refs.append(old_ref)
            update_generic(old_obj, new_obj)

        if new_refs:
            old_objects[key] = new_refs
        else:
            del old_objects[key]

    return module


# end of IPython code




