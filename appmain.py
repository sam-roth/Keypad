
import os.path

from keypad.__main__ import main
from keypad.core.processmgr import client
from PyQt4 import Qt

for lpath in list(Qt.QApplication.libraryPaths()):
    Qt.QApplication.removeLibraryPath(lpath)
Qt.QApplication.addLibraryPath(Qt.QApplication.applicationDirPath() + '/../PlugIns')
# print('PLUGIN PATH', Qt.QLibraryInfo.location(Qt.QLibraryInfo.PluginsPath))
# print('APP DIR PATH', Qt.QLibraryInfo.location(Qt.QLibraryInfo.PrefixPath))

here = os.path.abspath(os.path.dirname(__file__))
client.INTERPRETER_OVERRIDE = os.path.join(here, os.path.pardir, 'MacOS', 'workermain')
client.USE_SMOD = False


if __name__ == '__main__':
    main()



