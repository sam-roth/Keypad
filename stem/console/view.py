


import curses
from collections import namedtuple

import math

from .. import signal
from ..key import *

KeyEvent = namedtuple('KeyEvent', 'key text')


keymap = {
    curses.KEY_BACKSPACE: key.backspace,
    curses.KEY_LEFT: key.left,
    curses.KEY_RIGHT: key.right,
    curses.KEY_DOWN: key.down,
    curses.KEY_UP: key.up,
    curses.KEY_NPAGE: key.pagedown,
    curses.KEY_PPAGE: key.pageup,
    curses.KEY_HOME: key.home,
    curses.KEY_END: key.end,
    curses.KEY_SLEFT: shift.left,
    curses.KEY_SRIGHT: shift.right,
    curses.KEY_SHOME: shift.home,
    curses.KEY_SEND: shift.end,
    curses.KEY_SF: shift.down,
    curses.KEY_SR: shift.up
}


color_memo = {}
curses_colors = []

def create_colors():
    for color in range(8):
        r, g, b = curses.color_content(color)
        scale = 256/1000
        curses_colors.append((color, (r*scale, g*scale, b*scale)))

def html2rgb(color):
    try:
        if len(color) == 4:
            r = int(color[1], 16)
            g = int(color[2], 16)
            b = int(color[3], 16)

            r |= r << 8
            g |= g << 8
            b |= b << 8

            return  r, g, b
        else:
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:],  16)
            return r, g, b
    except ValueError as orig:
        raise ValueError('Invalid RGB literal: {!r}'.format(color)) from orig

def normalize_rgb(color):
    r, g, b = color
    
    mag = math.sqrt(r**2 + g**2 + b**2)
    if abs(mag) < 0.1:
        mag = 1
    return r/mag, g/mag, b/mag

def rgbdist_sq(color1, color2):
    r1, g1, b1 = normalize_rgb(color1)
    r2, g2, b2 = normalize_rgb(color2)

    return (r2-r1)**2 + (g2-g1)**2 + (b2-b1)**2

import random
def translate_color(color):
    global color_memo
    if color is None: return None
    try:
        return color_memo[0]
    except KeyError:
        if not curses_colors:
            create_colors()
        color_rgb = html2rgb(color)
        
        code, dist = max(((c, rgbdist_sq(color_rgb, rgb)) for (c, rgb) in curses_colors),
                          key=lambda x:x[1])
        
        color_memo[color] = random.randrange(8)
        return code



def put_attributed_text(win, line, col, astr):
    color = None
    for chunk, deltas in astr.iterchunks():
        color = deltas.get('color', color)
        if color is None:
            color = '#0000FF' if (line % 2) == 0 else '#FFFFFF'

        r, g, b = html2rgb(color)
        cidx = int((r/255) * 5*36 + (g/255) * 5*6 + (b/255) * 5) + 16

        #curses_attr = #curses.color_pair(translate_color(color))
        #curses_attr = curses.color_pair(1)
        curses.putp(b'\033[38;5;' + bytes(str(cidx), encoding='utf8') + b'm') #curses.tparm(curses.tigetstr('sgr'), 38, 5, cidx))
        win.addstr(line, col, chunk[:curses.COLS - col])

        col += len(chunk)

        if col >= curses.COLS:
            break
        
    

g_stdscr = None
cur_msg = ''



def message(*parts):
    global cur_msg
    cur_msg = ' '.join(map(str, parts))[-160:]
    if g_stdscr is None:
        print(cur_msg)
    else:
        g_stdscr.addstr(curses.LINES-5, 0, cur_msg)


def make_key_event(curses_key, bstate):
    if curses_key in ('\x7f',):
        curses_key = curses.KEY_BACKSPACE


    mods = 0
    if bstate & curses.BUTTON_SHIFT:
        mods |= Modifiers.Shift


    if isinstance(curses_key, str):
        text = curses_key
        key_ = ord(curses_key)
        message('normal', text, key_)
        return KeyEvent(SimpleKeySequence(0, key_), text)
    else:
        # TODO
        text = ''
        key_ = keymap.get(curses_key)
        message('special', key_, curses_key, bstate)
        if key_ is None:
            key_ = key.escape
        return KeyEvent(key_, text)
        


class TextView(object):
    class MouseButtons:
        Left   = 1
        Middle = 2
        Right  = 4

    def __init__(self, stdscr):
        self.stdscr = stdscr
        self._lines = []
        self.start_line = 0
        self.update_plane_size()
        self.cursor_pos = 0, 0

        global g_stdscr
        g_stdscr = stdscr

    def full_redraw(self): 
        self.stdscr.clear()
        height, width = self.plane_size
        for linenum, line in enumerate(self._lines[self.start_line:], self.start_line):
            if linenum >= height:
                break
            
            put_attributed_text(self.stdscr, linenum, 0, line)
            #self.stdscr.addstr(linenum, 0, line.text[:width])
        message(cur_msg)
        self.cursor_pos = self.cursor_pos

    @property
    def cursor_pos(self):
        return self._cursor_pos

    @cursor_pos.setter
    def cursor_pos(self, value):
        self._cursor_pos = value
        y, x = value
        self.stdscr.move(y,x)


    def partial_redraw(self): 
        self.full_redraw()

    def scroll_to_line(self, line): 
        pass

    def update_plane_size(self): 
        self._plane_size = (curses.LINES-5, curses.COLS)

    def map_to_plane(self, x, y): 
        pass


    @property
    def lines(self): 
        return self._lines

    @lines.setter
    def lines(self, value): 
        self._lines = value
        self.update_plane_size()

    @property
    def plane_size(self): 
        return self._plane_size
    
    @property
    def tab_width(self): 
        return 8

    @signal.Signal
    def plane_size_changed(self, width, height): pass

    @signal.Signal
    def scrolled(self, start_line): pass

    @signal.Signal
    def mouse_down_char(self, line, col): pass

    @signal.Signal
    def mouse_move_char(self, buttons, line, col): pass

    @signal.Signal
    def key_press(self, event): pass



class Application(object):

    def __enter__(self):
        self.stdscr = curses.initscr()
        curses.noecho()
        curses.cbreak()
        #curses.start_color()
        self.stdscr.keypad(True)
        self.running = True

        assert curses.can_change_color()
        return self

    @signal.Signal
    def keystroke(self, event): 
        pass

    def quit(self):
        self.running = False

    def run(self):
        while self.running:
            ch = self.stdscr.get_wch()
            try:
                *_, bstate = curses.getmouse()
            except curses.error:
                #message('error in getmouse()')
                bstate =0 
            try:
                self.keystroke(make_key_event(ch, bstate))
            except KeyboardInterrupt:
                raise
            except AssertionError:
                raise
            except:
                import traceback
                message(traceback.format_exc())
                


    def __exit__(self, exc_type, exc_val, exc_tb):
        curses.nocbreak()
        self.stdscr.keypad(False)
        curses.echo()
        curses.endwin()    

        return False # don't suppress exceptions

    


def main(stdscr):
    pass


if __name__ == '__main__':
    curses.wrapper(main)


