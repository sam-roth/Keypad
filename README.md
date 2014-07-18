# Keypad Text Editor

**See the [developer documentation](http://saroth.bitbucket.org/stemdoc/html/).**

**Warning: This program still has many bugs. It is not to be used for anything 
serious at this point.**


Keypad is a text editor written in Python with a flexible plugin system. It was formerly 
known as Stem.

## Design Principles

* **Hackability:** Unlike heavyweight IDEs such as Eclipse, Keypad makes simple
  plugins easy to write. 
* **Flexibility:** Keypad uses a model-view-controller architecture to isolate
  the GUI from the text editing logic, allowing for the possibility of
  additional user interfaces. For instance, it would be possible to build 
  a Curses frontend.
* **Lack of Dogma:** While Keypad is optimized for a certain style of text editing,
  it can be easily modified to suport others.

## Screenshot ([more](https://bitbucket.org/saroth/keypad/wiki/Screenshots))

![Editing Python Code](https://bitbucket.org/saroth/keypad/wiki/screenshots/overview.png)

## Installation and Running

### Core Dependencies

* [Python >= 3.3](http://www.python.org/)
* [PyQt4](http://www.riverbankcomputing.com/software/pyqt/download)
* Either [pathlib](https://pypi.python.org/pypi/pathlib/) or Python 3.4
* Either [enum34](https://pypi.python.org/pypi/enum34) or Python 3.4

### Dependencies of Included Plugins

#### C++ Completion

* [Clang 3.3](http://clang.llvm.org)

**Note:** In order to use Clang for code completion, you may need to add a file
to your `PYTHONPATH` with the name `stemrc.py` and the following contents,
substituting the path with one appropriate for your system.

```
#!python
import pathlib
import keypad.plugins.cpp.options
keypad.plugins.cpp.options.ClangLibrary = pathlib.Path('/Library/Developer/CommandLineTools/usr/lib/libclang.dylib')
```


#### Python Completion

* [Jedi](http://jedi.jedidjah.ch/en/latest/)


### Running

```
python3.3 -m keypad
```

## License

Keypad Text Editor  
Copyright © 2014 Sam Roth.

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE.  See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
this program.  If not, see
[http://www.gnu.org/licenses/](http://www.gnu.org/licenses/).
