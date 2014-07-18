
import html

import yaml
from PyQt4 import Qt as qt

from keypad import credits
from keypad import api

from .qt_util import Autoresponder


class AboutDialog(Autoresponder, qt.QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)

        self._browser = qt.QTextBrowser()

        layout = qt.QVBoxLayout(self)

        def label(text):
            lbl = qt.QLabel(text)
            lbl.setAlignment(qt.Qt.AlignCenter)
            layout.addWidget(lbl)
            return lbl

        label('<b>Stem</b>')

        layout.addWidget(self._browser)
        label('<small>Copyright 2014 Sam Roth</small>')
        self._browser.setText(self._create_markup())
        self._browser.setOpenExternalLinks(True)
        self._browser.setFont(qt.QFont('Helvetica'))

    def _create_markup(self):
        parts = []

        start = '''
        <b>Stem Text Editor</b><br>
        Copyright &copy; 2014 Sam Roth.

        <p>
        This program is free software: you can redistribute it and/or modify it under
        the terms of the GNU General Public License as published by the Free Software
        Foundation, either version 3 of the License, or (at your option) any later
        version.
        </p>

        <p>
        This program is distributed in the hope that it will be useful, but WITHOUT ANY
        WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
        PARTICULAR PURPOSE.  See the GNU General Public License for more details.
        </p>

        <p>
        You should have received a copy of the GNU General Public License along with
        this program.  If not, see
        <a href="http://www.gnu.org/licenses/">http://www.gnu.org/licenses/</a>.
        </p>

        <p><b>This software uses the following libraries:</b></p>
        '''
        parts.append(start)

        sort = 'Library Author Link License'.split()

        for doc in yaml.load_all(credits.credits):
            parts.append('<hr><p><dl>')
            for k in sort:
                v = doc.pop(k, None)
                if v:
                    if k == 'Link':
                        html_val = '<a href="{0}">{0}</a>'.format(html.escape(v))
                    else:
                        html_val = '<pre>' + html.escape(v) + '</pre>'
                    parts.append('<dt>' + html.escape(k) + '</dt><dd>' + html_val + '</dd>')

            for k, v in doc.items():
                parts.append('<dt>' + html.escape(k) + '</dt><dd><pre>' +
                             html.escape(v) + '</pre></dd>')
            parts.append('</dl></p>')
        return ''.join(parts)



# Overload gui_quit so that it recognizes the about dialog. This allows for pressing
# Cmd-W to close the dialog.
@api.interactive('gui_quit')
def gui_quit(dlg: AboutDialog):
    dlg.close()


