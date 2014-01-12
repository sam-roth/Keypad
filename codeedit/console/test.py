import curses, _curses



def main(stdscr):
    return type(stdscr)

print(curses.wrapper(main))
