"""
Use this file with the script in the scripts directory::

    cd scripts
    ./py2app.sh

Using this module directly will result in a non-functional app bundle due
to py2app bug #26: 
https://bitbucket.org/ronaldoussoren/py2app/issue/26/bundled-python-executable-not-working
"""

import sys
import subprocess
import os.path
sys.path.append('third-party')

from setuptools import setup

def get_qmake_var(name):
    return subprocess.getoutput('qmake -query {}'.format(name))

def get_qt_plugins():
    for dirpath, dirnames, filenames in os.walk(get_qmake_var('QT_INSTALL_PLUGINS')):
        for filename in filenames:
            if filename.endswith(('.dylib', '.so')):
                yield os.path.join(dirpath, filename)


APP = ['appmain.py']
DATA_FILES = []
OPTIONS = dict(argv_emulation=False,
               includes=['PyQt4.QtCore', 'PyQt4.QtGui', 'sip', 'keypad'],
               iconfile='resources/KeyPad.icns',
               frameworks=list(get_qt_plugins()),
               packages=['keypad', 'clang'],
               extra_scripts=['workermain.py'],
               use_pythonpath=True,
               site_packages=True,
               emulate_shell_environment=True)

if __name__ == '__main__':
    setup(name='KeyPad',
          app=APP,
          data_files=DATA_FILES,
          options={'py2app': OPTIONS},
          setup_requires=['py2app'])
    

    
