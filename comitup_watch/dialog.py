
import curses
import re
import time
import sys
import _curses
from abc import ABC, abstractmethod
from curses import wrapper, newpad, newwin, doupdate, KEY_RESIZE, is_term_resized, resizeterm, start_color, color_pair
from curses.panel import new_panel, update_panels
from enum import Enum
from typing import List, Optional, TYPE_CHECKING


if TYPE_CHECKING:
    from curses.panel import _Curses_Panel

class Message(Enum):
    NOT_IMPLEMENTED = "Not Implemented"
    INVALID_INPUT = "Invalid Input"

class Context(ABC):
    def __init__(self, display: "Display"):
        self.display = display

    @abstractmethod
    def _process_char(self, char: int) -> None:
        pass

    def handle_char(self, char: int) -> None:
        self._process_char(char)




class MainContext(Context):

    def _process_char(self, char: int) -> None:
        letter = chr(char).lower()
        if letter == "q":
            sys.exit(0)
        elif letter in "cl":
            self.display.push_context(MessageContext(self.display, Message.NOT_IMPLEMENTED))
        else:
            self.display.push_context(MessageContext(self.display, Message.INVALID_INPUT))

class MessageContext(Context):
    def __init__(self, display, message):
        super().__init__(display)

        self.message(message)

    def _process_char(self, char: int) -> None:
        self.display.pop_context()

        self.end_message()


    def message(self, message: Message) -> None:

        dialog_width = 30
        rows, cols = self.display.stdscr.getmaxyx()

        self.messagewin: Optional[_curses._CursesWindow] = newwin(
            5,
            dialog_width,
            int((rows - 5)/2),
            int((cols - dialog_width)/2),
        )
        self.messagewin.erase()
        self.messagewin.box()

        padding = int((dialog_width - len(message.name))/2)
        self.messagewin.addstr(2, padding, message.name)

        self.messagepan: Optional[_Curses_Panel] = new_panel(self.messagewin)
        self.messagepan.top()

        update_panels()
        self.display.stdscr.refresh()


    def end_message(self) -> None:
        self.messagepan = self.messagewin = None

        update_panels()
        self.display.stdscr.refresh()

class Display:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.pad = newpad(150, 150)
        self.pad.move(3, 0)


        self.headerwin = None
        self.headerpan = None
        self.footerwin = None
        self.footerpan = None
        self.bodywin = None
        self.bodypan = None


        self.body = [""]

        self.contexts = [MainContext(self)]

    def make_footer(self, rows: int, cols: int) -> None:
    
        self.footerwin = newwin(3, cols, rows - 3, 0)
        self.footerwin.erase()
    
        self.footerwin.addstr(0, 0, "-" * (cols-1))
        self.footerwin.addstr(2, 0, "-" * (cols-1))
    
        text = "(Q)uit    (C)onnect    (L)ocate"
        textstart = int((cols - len(text)) / 2)
        if textstart > 0:
            self.footerwin.addstr(1, textstart, text)
    
        self.footerpan = new_panel(self.footerwin)
        self.footerpan.top()
    

    def make_header(self, rows: int, cols: int) -> None:

        self.headerwin = newwin(3, cols, 0, 0)
        self.headerwin.erase()
    
        self.headerwin.addstr(0, 0, "-" *  (cols-1))
        self.headerwin.addstr(2, 0, "-" *  (cols-1))
    
        text = "COMITUP-WATCH"
        textstart = int((cols - len(text)) / 2)
        if textstart > 0:
            self.headerwin.addstr(1, textstart, text)
    
        self.headerpan = new_panel(self.headerwin)
        self.headerpan.top()


    def make_body(self, rows: int, cols: int) -> None:
        self.bodywin = newwin(rows - 3 - 3, cols, 3, 0)
        self.bodywin.erase()

        self.set_body()
    
        self.bodypan = new_panel(self.bodywin)
        self.bodypan.top()

    def make_display(self) -> None:
        maxy, maxx = self.stdscr.getmaxyx()
        self.stdscr.clear()

        self.make_body(maxy, maxx)
        self.make_header(maxy, maxx)
        self.make_footer(maxy, maxx)

        update_panels()
        self.stdscr.refresh()
        doupdate()

    def set_body(self, body: List[str] = None) -> None:
        if body:
            self.body = body

        self.bodywin.clear()
        rows, cols = self.bodywin.getmaxyx()

        trunc = self.body[:rows]
        trunc = [x[:cols-1] for x in trunc]

        max_row = max([len(x) for x in trunc])

        blank_rows = int((rows - len(trunc)) / 2)
        blank_cols = int((cols - max_row) / 2)

        for row, text in enumerate(trunc, max(0, blank_rows)):
            self.bodywin.addstr(row, blank_cols, text, curses.A_STANDOUT)

        update_panels()
        doupdate()

#     def strlen(self, text: str) -> int:

    def handle_char(self, char: int) -> None:
        self.contexts[-1].handle_char(char)



    def push_context(self, context: Context) -> None:
        self.contexts.append(context)

    def pop_context(self) -> None:
        self.contexts.pop()




def cmain(stdscr):
    start_color()
    stdscr.clear()


    display = Display(stdscr)
    display.make_display()


    # display.set_body(["foo"])


    text = []
    for i in range(0, 9):
        v = i-10
        # stdscr.addstr(i, 0, '10 divided by {} is {}'.format(v, 10/v))
        # display.bodywin.addstr(i, 0, '10 divided by {} is {}'.format(v, 10/v))
        text.append('10 divided by {} is {}'.format(v, 10/v))

    display.set_body(text)
    # display.message(Message.NOT_IMPLEMENTED)


    update_panels()
    doupdate()
    stdscr.refresh()


    while True:
        char = stdscr.getch()
        if char == KEY_RESIZE:
            y, x = stdscr.getmaxyx()
            stdscr.clear()
            display.make_display()

        display.handle_char(char)


wrapper(cmain)

