from blessed import Terminal
from typing import List, Tuple, Dict
from enum import Enum
import curses

class stuff:
    """ General constants for the game and stuff """
    
    term = Terminal()
    
    screen = curses.initscr()
    curses.start_color()

    def get_screen_height() -> int:
        return stuff.screen.getmaxyx()[0]

    def get_screen_width() -> int:
        return stuff.screen.getmaxyx()[1]
    