"""Test the nethack parser module"""

import unittest

import parser
import screen

class TestParser(unittest.TestCase):
    """Test the nethack parser object"""

    def setUp(self):
        """Fixture is the Parser, we also pull out the screen object for
           convenience/brevity in tests."""
        self.parser = parser.Parser()
        self.screen = self.parser.screen

    def test_cursor(self): # pylint: disable=too-many-statements
        """Test all the escape sequences and characters that move the cursor."""
        self.assertEqual(self.screen.cursor_x, 1)
        self.assertEqual(self.screen.cursor_y, 1)

        self.parser.parse_bytes(b'\x1b[B')
        self.assertEqual(self.screen.cursor_x, 1)
        self.assertEqual(self.screen.cursor_y, 2)

        self.parser.parse_bytes(b'\x1b[B'*2)
        self.assertEqual(self.screen.cursor_x, 1)
        self.assertEqual(self.screen.cursor_y, 4)

        self.parser.parse_bytes(b'\x1b[ 5 B')
        self.assertEqual(self.screen.cursor_x, 1)
        self.assertEqual(self.screen.cursor_y, 9)

        self.parser.parse_bytes(b'\x1b[ A')
        self.assertEqual(self.screen.cursor_x, 1)
        self.assertEqual(self.screen.cursor_y, 8)

        self.parser.parse_bytes(b'\x1b[2 A')
        self.assertEqual(self.screen.cursor_x, 1)
        self.assertEqual(self.screen.cursor_y, 6)

        self.parser.parse_bytes(b'\x1b[50A') # clamp at top
        self.assertEqual(self.screen.cursor_x, 1)
        self.assertEqual(self.screen.cursor_y, 1)

        self.parser.parse_bytes(b'\x1b[26B') # clamp at bottom
        self.assertEqual(self.screen.cursor_x, 1)
        self.assertEqual(self.screen.cursor_y, 24)

        self.parser.parse_bytes(b'\x1b[ 10 C')
        self.assertEqual(self.screen.cursor_x, 11)
        self.assertEqual(self.screen.cursor_y, 24)

        self.parser.parse_bytes(b'\x1b[C')
        self.assertEqual(self.screen.cursor_x, 12)
        self.assertEqual(self.screen.cursor_y, 24)

        self.parser.parse_bytes(b'\n') # clamp at bottom
        self.assertEqual(self.screen.cursor_x, 12)
        self.assertEqual(self.screen.cursor_y, 24)

        self.parser.parse_bytes(b'\x1b[12A') # clamp at top
        self.assertEqual(self.screen.cursor_x, 12)
        self.assertEqual(self.screen.cursor_y, 12)

        self.parser.parse_bytes(b'\n')
        self.assertEqual(self.screen.cursor_x, 12)
        self.assertEqual(self.screen.cursor_y, 13)

        self.parser.parse_bytes(b'\n\n\n')
        self.assertEqual(self.screen.cursor_x, 12)
        self.assertEqual(self.screen.cursor_y, 16)

        self.parser.parse_bytes(b'\x1b[D')
        self.assertEqual(self.screen.cursor_x, 11)
        self.assertEqual(self.screen.cursor_y, 16)

        self.parser.parse_bytes(b'\x1b[ 3 D')
        self.assertEqual(self.screen.cursor_x, 8)
        self.assertEqual(self.screen.cursor_y, 16)

        self.parser.parse_bytes(b'\x1b[ 20 D') # clamp at left
        self.assertEqual(self.screen.cursor_x, 1)
        self.assertEqual(self.screen.cursor_y, 16)

        self.parser.parse_bytes(b'abcdefg')
        self.assertEqual(self.screen.cursor_x, 8)
        self.assertEqual(self.screen.cursor_y, 16)

        self.parser.parse_bytes(b'\x1b[E')
        self.assertEqual(self.screen.cursor_x, 1)
        self.assertEqual(self.screen.cursor_y, 17)

        self.parser.parse_bytes(b'\x1b[ 76 G')
        self.assertEqual(self.screen.cursor_x, 76)
        self.assertEqual(self.screen.cursor_y, 17)

        self.parser.parse_bytes(b'\x1b[3E')
        self.assertEqual(self.screen.cursor_x, 1)
        self.assertEqual(self.screen.cursor_y, 20)

        self.parser.parse_bytes(b'\x1b[ 79 G')
        self.assertEqual(self.screen.cursor_x, 79)
        self.assertEqual(self.screen.cursor_y, 20)

        self.parser.parse_bytes(b'123456789') # clamp at right
        self.assertEqual(self.screen.cursor_x, 80)
        self.assertEqual(self.screen.cursor_y, 20)

        self.parser.parse_bytes(b'\x1b[3F')
        self.assertEqual(self.screen.cursor_x, 1)
        self.assertEqual(self.screen.cursor_y, 17)

        self.parser.parse_bytes(b'\x1b[F')
        self.assertEqual(self.screen.cursor_x, 1)
        self.assertEqual(self.screen.cursor_y, 16)

        self.parser.parse_bytes(b'\x1b[20F') # clamp at top
        self.assertEqual(self.screen.cursor_x, 1)
        self.assertEqual(self.screen.cursor_y, 1)

        self.parser.parse_bytes(b'\x1b[30E') # clamp at bottom
        self.assertEqual(self.screen.cursor_x, 1)
        self.assertEqual(self.screen.cursor_y, 24)

        self.parser.parse_bytes(b'\x1b[ 400 G') # clamp on right
        self.assertEqual(self.screen.cursor_x, 80)
        self.assertEqual(self.screen.cursor_y, 24)

        self.parser.parse_bytes(b'\x1b[ 0 G') # clamp on left
        self.assertEqual(self.screen.cursor_x, 1)
        self.assertEqual(self.screen.cursor_y, 24)

        self.parser.parse_bytes(b'\x1b[ 10 ; 8 H')
        self.assertEqual(self.screen.cursor_x, 10)
        self.assertEqual(self.screen.cursor_y, 8)

        self.parser.parse_bytes(b'\x1b[H')
        self.assertEqual(self.screen.cursor_x, 1)
        self.assertEqual(self.screen.cursor_y, 1)

        self.parser.parse_bytes(b'\x1b[ 0 ; 99 H') # clamp left and bottom
        self.assertEqual(self.screen.cursor_x, 1)
        self.assertEqual(self.screen.cursor_y, 24)

        self.parser.parse_bytes(b'\x1b[ 99 ; 0 H') # clamp right and top
        self.assertEqual(self.screen.cursor_x, 80)
        self.assertEqual(self.screen.cursor_y, 1)

        self.parser.parse_bytes(b'\x1b[ ; 14 H')
        self.assertEqual(self.screen.cursor_x, 1)
        self.assertEqual(self.screen.cursor_y, 14)

        self.parser.parse_bytes(b'\x1b[ 56 ; H')
        self.assertEqual(self.screen.cursor_x, 56)
        self.assertEqual(self.screen.cursor_y, 1)

        self.parser.parse_bytes(b'\x1b[ 13 ; 9 f')
        self.assertEqual(self.screen.cursor_x, 13)
        self.assertEqual(self.screen.cursor_y, 9)

        self.parser.parse_bytes(b'\b')
        self.assertEqual(self.screen.cursor_x, 12)
        self.assertEqual(self.screen.cursor_y, 9)

        self.parser.parse_bytes(b'\b'*50) # clamp on right
        self.assertEqual(self.screen.cursor_x, 1)
        self.assertEqual(self.screen.cursor_y, 9)

        self.parser.parse_bytes(b'1234')
        self.assertEqual(self.screen.cursor_x, 5)
        self.assertEqual(self.screen.cursor_y, 9)

        self.parser.parse_bytes(b'\n'*30) # clamp on bottom
        self.assertEqual(self.screen.cursor_x, 5)
        self.assertEqual(self.screen.cursor_y, 24)

        self.parser.parse_bytes(b'\x1b[ 28 ; 19 H')
        self.assertEqual(self.screen.cursor_x, 28)
        self.assertEqual(self.screen.cursor_y, 19)

        self.parser.parse_bytes(b'\r')
        self.assertEqual(self.screen.cursor_x, 1)
        self.assertEqual(self.screen.cursor_y, 19)

        self.parser.parse_bytes(b'123')
        self.assertEqual(self.screen.cursor_x, 4)
        self.assertEqual(self.screen.cursor_y, 19)

        self.parser.parse_bytes(b'\a\t\v\f\x00\x1d')
        self.assertEqual(self.screen.cursor_x, 4)
        self.assertEqual(self.screen.cursor_y, 19)

    def _assert_attributes(self, attr_list):
        """Utility, assert that the current screen attributes are the passed in list."""
        self.assertEqual(attr_list, list(self.screen.current_attributes.enumerate()))

    def test_sgr_exclusion(self):
        """The test the mutually exclusive attributes."""
        self._assert_attributes([])

        self.parser.parse_bytes(b'\x1b[ 1 m')
        self._assert_attributes([screen.ATTR_BOLD])

        self.parser.parse_bytes(b'\x1b[ 2 m')
        self._assert_attributes([screen.ATTR_FAINT])

        self.parser.parse_bytes(b'\x1b[ 5 m')
        self._assert_attributes([screen.ATTR_FAINT, screen.ATTR_SLOW_BLINK])

        self.parser.parse_bytes(b'\x1b[ 6 m')
        self._assert_attributes([screen.ATTR_FAINT, screen.ATTR_RAPID_BLINK])

        # Too many font and color codes not to use a loop
        for (range_, negate) in ((range(screen.ATTR_ALTERNATE_FONT1,
                                        screen.ATTR_ALTERNATE_FONT9+1),
                                  screen.ATTR_DEFAULT_FONT),
                                 (range(screen.ATTR_BLACK_FG,
                                        screen.ATTR_SET_COLOR_FG+1),
                                  screen.ATTR_DEFAULT_FG),
                                 (range(screen.ATTR_BLACK_BG,
                                        screen.ATTR_SET_COLOR_BG+1),
                                  screen.ATTR_DEFAULT_BG)):
            # Need to iterate multiple times
            range_list = list(range_)
            # Each code in the range is mutually exclusive
            for char in range_list:
                # set color requires 2 or 4 arguments, which are currently ignored
                if char == screen.ATTR_SET_COLOR_FG:
                    self.parser.parse_bytes(b'\x1b[ %d ; 5 ; 3 m' % char)
                elif char == screen.ATTR_SET_COLOR_BG:
                    self.parser.parse_bytes(b'\x1b[ %d ; 2 ; 255 ; 255 ; 255 m' % char)
                else:
                    self.parser.parse_bytes(b'\x1b[ %d m' % char)
                self._assert_attributes([screen.ATTR_FAINT, screen.ATTR_RAPID_BLINK, char])
            # The negate code cancels all codes in the range
            for char in range_list:
                # set color requires 2 or 4 arguments, which are currently ignored
                if char == screen.ATTR_SET_COLOR_FG:
                    self.parser.parse_bytes(b'\x1b[ %d ; 2 ; 128 ; 0 ; 64 m' % char)
                elif char == screen.ATTR_SET_COLOR_BG:
                    self.parser.parse_bytes(b'\x1b[ %d ; 5 ; 1 m' % char)
                else:
                    self.parser.parse_bytes(b'\x1b[ %d m' % char)
                self._assert_attributes([screen.ATTR_FAINT, screen.ATTR_RAPID_BLINK, char])
                self.parser.parse_bytes(b'\x1b[ %d m' % negate)
                self._assert_attributes([screen.ATTR_FAINT, screen.ATTR_RAPID_BLINK])

    def test_sgr_negate(self):
        """Test sgr codes that negate other codes, except the font/color ones
           that are already covered in the mutual exclusion test."""
        # Just for "fun" set a color to start
        self.parser.parse_bytes(b'\x1b[ 31 m')
        self._assert_attributes([screen.ATTR_RED_FG])

        self.parser.parse_bytes(b'\x1b[ 1 m')
        self._assert_attributes([screen.ATTR_BOLD, screen.ATTR_RED_FG])

        self.parser.parse_bytes(b'\x1b[ 22 m')
        self._assert_attributes([screen.ATTR_RED_FG])

        self.parser.parse_bytes(b'\x1b[ 2 m')
        self._assert_attributes([screen.ATTR_FAINT, screen.ATTR_RED_FG])

        self.parser.parse_bytes(b'\x1b[ 22 m')
        self._assert_attributes([screen.ATTR_RED_FG])

        self.parser.parse_bytes(b'\x1b[ 3 m')
        self._assert_attributes([screen.ATTR_ITALIC, screen.ATTR_RED_FG])

        self.parser.parse_bytes(b'\x1b[ 23 m')
        self._assert_attributes([screen.ATTR_RED_FG])

        self.parser.parse_bytes(b'\x1b[ 4 m')
        self._assert_attributes([screen.ATTR_UNDERLINE, screen.ATTR_RED_FG])

        self.parser.parse_bytes(b'\x1b[ 24 m')
        self._assert_attributes([screen.ATTR_RED_FG])

        self.parser.parse_bytes(b'\x1b[ 1 m')
        self._assert_attributes([screen.ATTR_BOLD, screen.ATTR_RED_FG])

        # double underline also turns bold off
        self.parser.parse_bytes(b'\x1b[ 21 m')
        self._assert_attributes([screen.ATTR_2X_UNDERLINE, screen.ATTR_RED_FG])

        self.parser.parse_bytes(b'\x1b[ 24 m')
        self._assert_attributes([screen.ATTR_RED_FG])

        self.parser.parse_bytes(b'\x1b[ 5 m')
        self._assert_attributes([screen.ATTR_SLOW_BLINK, screen.ATTR_RED_FG])

        self.parser.parse_bytes(b'\x1b[ 25 m')
        self._assert_attributes([screen.ATTR_RED_FG])

        self.parser.parse_bytes(b'\x1b[ 6 m')
        self._assert_attributes([screen.ATTR_RAPID_BLINK, screen.ATTR_RED_FG])

        self.parser.parse_bytes(b'\x1b[ 25 m')
        self._assert_attributes([screen.ATTR_RED_FG])

        self.parser.parse_bytes(b'\x1b[ 7 m')
        self._assert_attributes([screen.ATTR_INVERSE, screen.ATTR_RED_FG])

        self.parser.parse_bytes(b'\x1b[ 27 m')
        self._assert_attributes([screen.ATTR_RED_FG])

        self.parser.parse_bytes(b'\x1b[ 8 m')
        self._assert_attributes([screen.ATTR_CONCEAL, screen.ATTR_RED_FG])

        self.parser.parse_bytes(b'\x1b[ 28 m')
        self._assert_attributes([screen.ATTR_RED_FG])

        self.parser.parse_bytes(b'\x1b[ 9 m')
        self._assert_attributes([screen.ATTR_STRIKE, screen.ATTR_RED_FG])

        self.parser.parse_bytes(b'\x1b[ 29 m')
        self._assert_attributes([screen.ATTR_RED_FG])

    def test_sgr_clear(self):
        """Test the SGR 0 clears all attributes."""
        self.parser.parse_bytes(b'\x1b[ 1 m\x1b[ 3 m\x1b[ 6 m\x1b[ 7 m')
        self._assert_attributes([screen.ATTR_BOLD, screen.ATTR_ITALIC,
                                 screen.ATTR_RAPID_BLINK, screen.ATTR_INVERSE])

        self.parser.parse_bytes(b'\x1b[ 0 m')
        self._assert_attributes([])

        self.parser.parse_bytes(b'\x1b[ 2 m\x1b[ 4 m\x1b[ 5 m\x1b[ 8 m')
        self._assert_attributes([screen.ATTR_FAINT, screen.ATTR_UNDERLINE,
                                 screen.ATTR_SLOW_BLINK, screen.ATTR_CONCEAL])

        # no argument is same as 0
        self.parser.parse_bytes(b'\x1b[m')
        self._assert_attributes([])

    def test_sgr_args(self):
        """Test that only the custom color sgrs are allowed arguments."""
        # This test is currently really slow. Either catching exceptions
        # or re-constructing the parser is taking longer than expected.
        worked = 0
        for code in range(0, 50):
            for num_args in range(1, 6):
                try:
                    self.parser.parse_bytes((b'\x1b[ %d '+(b' ; 9 '*num_args)+b' m') % code)
                    # only a few cases should actually work
                    self.assertTrue(num_args in (2, 4))
                    self.assertTrue(code in (screen.ATTR_SET_COLOR_FG, screen.ATTR_SET_COLOR_BG))
                    worked += 1
                except parser.ParseException:
                    # This is generally what we expect. Parser is invalid after exception reset.
                    self.parser = parser.Parser()
        # make sure the right number entered the "worked" case (otherwise would pass if all raised)
        self.assertEqual(4, worked)

    def test_nethack_eod(self):
        """Test the nethack end-of-data escape"""
        self.assertTrue(self.parser.end_of_data)

        self.parser.parse_bytes(b'abc')
        self.assertFalse(self.parser.end_of_data)

        self.parser.parse_bytes(b'\x1b[ 1 ; 3 z')
        self.assertTrue(self.parser.end_of_data)

        # Even an in-progress escape sequence should count as data
        self.parser.parse_bytes(b'\x1b')
        self.assertFalse(self.parser.end_of_data)

        self.parser.parse_bytes(b'[ 1 ; 3 z')
        self.assertTrue(self.parser.end_of_data)

    def test_nethack_windows(self):
        """Test the nethack escape to switch 'window' for output"""
        self.assertEqual(self.screen.current_window, screen.BASE_WINDOW)

        self.parser.parse_bytes(b'\x1b[ 1 ; 2 ; 1 z')
        self.assertEqual(self.screen.current_window, screen.MSG_WINDOW)

        self.parser.parse_bytes(b'a')
        self.assertEqual(self.screen.windows[screen.MSG_WINDOW].char_data[1][1].char, ord(b'a'))

        self.parser.parse_bytes(b'\x1b[ 1 ; 2 ; 2 z')
        self.assertEqual(self.screen.current_window, screen.STATUS_WINDOW)

        self.parser.parse_bytes(b'b')
        self.assertEqual(self.screen.windows[screen.STATUS_WINDOW].char_data[2][1].char, ord(b'b'))

        self.parser.parse_bytes(b'\x1b[ 1 ; 2 ; 3 z')
        self.assertEqual(self.screen.current_window, screen.MAP_WINDOW)

        self.parser.parse_bytes(b'c')
        self.assertEqual(self.screen.windows[screen.MAP_WINDOW].char_data[3][1].char, ord(b'c'))

        self.parser.parse_bytes(b'\x1b[ 1 ; 2 ; 4 z')
        self.assertEqual(self.screen.current_window, screen.INV_WINDOW)

        self.parser.parse_bytes(b'd')
        self.assertEqual(self.screen.windows[screen.INV_WINDOW].char_data[4][1].char, ord(b'd'))

        self.parser.parse_bytes(b'\x1b[ 1 ; 2 ; 0 z')
        self.assertEqual(self.screen.current_window, screen.BASE_WINDOW)

        self.parser.parse_bytes(b'e')
        self.assertEqual(self.screen.windows[screen.BASE_WINDOW].char_data[5][1].char, ord(b'e'))

    def test_tiledata(self):
        """Test writing tiledata into the map window"""
        # switch to the map window
        self.parser.parse_bytes(b'\x1b[ 1 ; 2 ; 3 z')

        # move into part of the "normal" map area
        self.parser.parse_bytes(b'\x1b[ 5 ; 5 H')

        # write out a tile
        self.parser.parse_bytes(b'\x1b[ 1 ; 0 ; 7 ; 9 z\x1b[ 1 m\x1b[ 31 m@\x1b[ 1 ; 1 z')
        data = self.screen.windows[screen.MAP_WINDOW].char_data[5][5]
        self.assertEqual(ord(b'@'), data.char)
        self.assertTrue(data.attributes.check(screen.ATTR_BOLD))
        self.assertTrue(data.attributes.check(screen.ATTR_RED_FG))
        self.assertEqual(7, data.tile_num)
        self.assertEqual(9, data.tile_flag)

        # overwrite the area outside a tile escape
        self.parser.parse_bytes(b'\b\x1b[ 21 mh')
        self.assertEqual(ord(b'h'), data.char)
        self.assertTrue(data.attributes.check(screen.ATTR_RED_FG))
        self.assertEqual(None, data.tile_num)
        self.assertEqual(None, data.tile_flag)



if __name__ == '__main__':
    unittest.main()
