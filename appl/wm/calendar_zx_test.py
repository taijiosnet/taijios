#!/usr/bin/env python3
"""Check the ZX Calendar against the state recorded from the Dis version.

The Dis Calendar (appl/wm/calendar.b) was recorded in a private guest with
/dev/time at 1700000006000000, the UTC timezone and the raw schedule
20231114 mark 1 "Team standup", 20231120 mark 258 "Release day": it showed a
236x165 calendar-only window and a 286x287 schedule window, the 2023/11 grid,
a red oval on 14 and a yellow diamond on 20. The date and mark rules are
checked against 28 Dis outcomes in calendar_cases.expected; this test checks
the window, its marks, the schedule file edits and the Set Time dialog.
"""
import os

from wm_app_test import BUILD, ROOT, Guest, arguments, ocr, private_display, run_model

WINDOW = (286, 287)
RED, YELLOW = (255, 0, 0), (255, 255, 0)
TIME = b'1700000006000000'
ZONE = b'UTC 0 UTC 0\n'
SCHEDULE = (b'  23   23\n20231114 1\nTeam standup'
            b'  24   24\n20231120 258\nRelease day')

# The app's client geometry: a 1-pixel border and the 32-pixel caption sit
# above a 284-wide, 253-tall calendar, whose 224-wide grid starts at x=30.
GRID_X, GRID_Y = 1 + 30, 33 + 16 + 5 + 18 + 2
CELL_W, CELL_H = 32, 13


def cell(day, first_wday):
    slot = first_wday + day - 1
    return GRID_X + (slot % 7) * CELL_W, GRID_Y + (slot // 7 + 1) * CELL_H


def window_size(image):
    pixels = image.load()
    if pixels[0, 0] != (255, 255, 255):
        return None
    width = 0
    while width < image.width and pixels[width, 0] == (255, 255, 255):
        width += 1
    height = 0
    while height < image.height and pixels[0, height] == (255, 255, 255):
        height += 1
    return width, height


def picker_red(image):
    return sum(1 for row in range(179, 197) for column in range(90, 108)
               if image.getpixel((column, row)) == RED)


def marked(image, day, first_wday, color):
    x, y = cell(day, first_wday)
    return sum(1 for row in range(y + 1, y + CELL_H - 1) for column in range(x + 2, x + CELL_W - 2)
               if image.getpixel((column, row)) == color)


def main():
    args = arguments(__doc__, 'calendar.zx')
    message = run_model('calendar', 'calendar_cases.expected', os.environ.copy())
    assert message == 'Calendar matched 28 reference cases', message
    print(message)
    work = BUILD / 'calendar-fixture'
    work.mkdir(parents=True, exist_ok=True)
    clock, zone, schedule = work / 'time', work / 'timezone', work / 'schedule'
    clock.write_bytes(TIME)
    zone.write_bytes(ZONE)
    schedule.write_bytes(SCHEDULE)
    setup = (f'bind /{clock.relative_to(ROOT).as_posix()} /dev/time; '
             f'bind /{zone.relative_to(ROOT).as_posix()} /locale/timezone; ')
    with private_display() as env, Guest(env, args, [f'/{schedule.relative_to(ROOT).as_posix()}'],
                                         setup=setup, size='640x480') as guest:
        image = guest.settled(lambda shot: shot if window_size(shot) == WINDOW else None,
                             'Calendar did not open its recorded window', timeout=30, name='calendar')
        print(f'Calendar opened the Dis window {WINDOW[0]}x{WINDOW[1]}')
        clock_text = ocr(image, (1, 34, 176, 56))
        assert clock_text == 'Tue Nov 14 22:13.26', clock_text
        print(f'Calendar showed the recorded time "{clock_text}"')
        assert marked(image, 14, 3, RED) >= 60, 'no red oval on 14'
        assert marked(image, 20, 3, YELLOW) >= 20, 'no yellow diamond on 20'
        print('Calendar drew the red oval on 14 and the yellow diamond on 20')
        body = ocr(image, (9, 202, 98, 222))
        assert body == 'Team standup', body
        print(f'Calendar showed the schedule body "{body}"')

        # Month arrows: December has neither mark, and the back arrow restores them.
        guest.click(GRID_X + 7 * CELL_W - 15, 33 + 21 + 12)
        guest.settled(lambda shot: shot if marked(shot, 14, 3, RED) == 0 else None,
                      'next month still showed November marks', timeout=10)
        guest.click(GRID_X + 7 * CELL_W - 45, 33 + 21 + 12)
        guest.settled(lambda shot: shot if marked(shot, 14, 3, RED) >= 60 else None,
                      'previous month did not restore November', timeout=10)
        print('Month arrows stepped to December and back')

        # A day without an entry starts empty; typing and Save append it to the file.
        x, y = cell(15, 3)
        guest.click(x + CELL_W // 2, y + CELL_H // 2)
        guest.settled(lambda shot: shot if picker_red(shot) == 0 else None,
                      'the selected day did not clear the mark picker', timeout=10)
        guest.run('xdotool', 'type', '--window', guest.window, '--delay', '30', 'Dentist')
        guest.click(GRID_X - 5 + 36 + 20, 33 + 141 + 14)  # Save
        guest.settled(lambda shot: shot if b'Dentist' in schedule.read_bytes() else None,
                      'Save did not write the new entry', timeout=15)
        assert b'20231115' in schedule.read_bytes(), schedule.read_bytes()
        print('Calendar saved a typed entry as 20231115')

        # Del clears the body and Save removes the record.
        guest.click(GRID_X - 5 + 16 - 16 + 1, 33 + 141 + 14)  # Del
        guest.click(GRID_X - 5 + 36 + 20, 33 + 141 + 14)  # Save
        guest.settled(lambda shot: shot if b'Dentist' not in schedule.read_bytes() else None,
                      'Del and Save did not remove the entry', timeout=15)
        print('Calendar removed the entry with Del and Save')

        # Set opens the time dialog; Cancel closes it without writing /dev/time.
        guest.click(211, 48)  # Set
        guest.settled(lambda shot: shot if shot.getpixel((19, 97)) == (0, 0, 0) else None,
                      'Set did not open the time dialog', timeout=10)
        guest.click(230, 33 + 63 + 126 - 17)  # Cancel
        guest.settled(lambda shot: shot if shot.getpixel((19, 97)) != (0, 0, 0) else None,
                      'Cancel did not close the time dialog', timeout=10)
        print('Calendar opened the Set Time dialog and closed it with Cancel')


if __name__ == '__main__':
    main()
