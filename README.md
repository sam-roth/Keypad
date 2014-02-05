# Stem – an editor

**Warning: This program is still very buggy and has many hardcoded options. It
is not to be used for anything serious at this point.**

Stem is a text editor written in Python with a flexible plugin system. 

## Design Principles

* **Hackability:** Unlike heavyweight IDEs such as Eclipse, Stem makes plugins
  simple plugins easy to write. There's an example on this page, and some
  larger ones in the `plugins` directory.
* **Flexibility:** Stem uses a model-view-controller architecture to isolate
  the GUI from the text editing logic, allowing for the possibility of
  additional frontends, such as a Curses frontend. 
* **Lack of Dogma:** Stem is an editor for everyone. There's no right or wrong
  way of using it.

## Plugin Example: Autoindent

This is a plugin that maintains the indentation level when moving to a new line.

```
#!python
@autoconnect(BufferController.user_changed_buffer, 
             lambda tags: tags.get('autoindent'))
def autoindent(controller, chg):
    if chg.insert.endswith('\n'):                           # user added a line
        beg_curs = Cursor(controller.buffer).move(*chg.pos) # move to the start of the inserted text
        indent = re.match(r'^\s*', beg_curs.line.text)      # find the indent of the original line
        if indent is not None:
            Cursor(controller.buffer)\                      # copy the indent to the new line
                .move(*chg.insert_end_pos)\
                .insert(indent.group(0))


```

## Screenshot ([more](https://bitbucket.org/saroth/stem/wiki/Screenshots))

![Editing Python Code](https://bitbucket.org/saroth/stem/wiki/screenshots/overview.png)

## The Name

The name of this project is likely to change in the future. "Stem" is a
metaphor for the plugin architecture used by the editor. If the core of the
editor is the stem, then the plugins are leaves.

## Installation and Running

### Dependencies

* [Python 3.3](http://www.python.org/)
* [PyQt4](http://www.riverbankcomputing.com/software/pyqt/download)
* [pathlib](https://pypi.python.org/pypi/pathlib/)

### Running

```
python3.3 -m stem.qt.driver
```

## License

Stem Text Editor  
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
