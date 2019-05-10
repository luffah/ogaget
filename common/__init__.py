#!/usr/bin/env python3
import re
import curses
import os

def choose(files, title, curses=True):
    if len(files) == 1:
        return files[0]
    else:
        pretty_files = [os.path.split(f.replace('%20', ' ').replace('%27',
                                                                    "'").replace('%21', ''))[-1]
                        for f in files]
        if curses:
            return files[FuzzySelector().get(pretty_files, title)]
        else:
            print('\n'.join([
                "%d : %s" % (idx+1, n)
                for (idx, n) in enumerate(pretty_files)
            ]))
            idx = None
            while not isinstance(idx, int):
                try:
                    idx = int(input('i (1 =< i =< %s) ? ' % len(files)))
                except ValueError:
                    print('give number or hit Ctrl+c')
            return files[idx-1]


class FuzzySelector(object):
    BG = [curses.A_NORMAL, curses.A_REVERSE, curses.A_UNDERLINE]

    def move(self, i):
        self.visible_idx = min(max(self.visible_idx + i, 0),
                               len(self.suggestions) - 1)
        self.idx = self.suggestions[self.visible_idx][0]

    def update(self, options):
        matched = []
        self.suggestions = list(enumerate(options))
        if self.input:
            regex = re.compile('.*?'.join(self.input))
            for idx, l in self.suggestions:
                match = regex.search(l, re.IGNORECASE)
                if match:
                    matched.append(
                        (len(match.group()), match.start(), l, idx))
        if matched:
            self.suggestions = [(idx, l) for _, _, l, idx in sorted(matched)]
        self.idx = self.suggestions[0][0]

    def redraw(self, screen):
        screen.clear()
        y = 1  # first line
        max_y, max_x = screen.getmaxyx()
        max_y -= 2
        max_x -= 2

        def _draw_lines(lines):
            nonlocal y
            for l, attridx in lines:
                if y > max_y:
                    return
                screen.addnstr(y, 1,
                               l[max(0, len(l)-max_x):], max_x,
                               self.BG[attridx])
                y += 1

        if self.title:
            _draw_lines((l, 0) for l in self.title.split('\n'))

        _draw_lines([('>' + self.input + '█', 2)])
        _draw_lines([
            (l, int(idx == self.idx))
            for idx, l in self.suggestions
        ][int(self.visible_idx/(max_y-2))*(max_y-2):])

        screen.refresh()

    def curse_ui(self, screen):
        curses.use_default_colors()
        curses.curs_set(0)

        self.input = ''
        self.update(self.items)
        self.idx = 0
        self.visible_idx = 0

        while True:
            self.redraw(screen)
            c = screen.getch()
            if c in (curses.KEY_ENTER, ord('\n'), ord('\r')):
                return self.idx
            elif c == curses.KEY_UP:
                self.move(-1)
            elif c == curses.KEY_DOWN:
                self.move(1)
            elif c in (curses.KEY_LEFT, curses.KEY_RIGHT):
                pass
            else:
                if c == curses.KEY_BACKSPACE:
                    self.input = self.input[:-1]
                else:
                    self.input += chr(c)
                self.update(self.items)

    def get(self, items, title=None):
        self.title = title
        self.items = items
        return curses.wrapper(self.curse_ui)
