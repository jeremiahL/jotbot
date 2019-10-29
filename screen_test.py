"""Tests the classes and methods in the screen module."""

import itertools
import unittest

import screen

class TestCharAttributes(unittest.TestCase):
    """Test for the CharAttribtues operations (bitmap)"""

    def setUp(self):
        """Fixture is a CharAttributes object"""
        self.attributes = screen.CharAttributes()

    def test_set_check(self):
        """Test that setting and checking by bit number works."""
        for i in range(256):
            self.assertFalse(self.attributes.check(i))

        self.assertFalse(self.attributes.check(5))
        self.attributes.set(5)
        self.assertTrue(self.attributes.check(5))
        self.assertEqual(0x20, self.attributes.bitmap)

        self.assertFalse(self.attributes.check(0))
        self.attributes.set(0)
        self.assertTrue(self.attributes.check(0))
        self.assertTrue(self.attributes.check(5))
        self.assertEqual(0x21, self.attributes.bitmap)

        self.assertFalse(self.attributes.check(204))
        self.attributes.set(204)
        self.assertTrue(self.attributes.check(204))
        self.assertTrue(self.attributes.check(0))
        self.assertTrue(self.attributes.check(5))
        self.assertEqual(0x1000000000000000000000000000000000000000000000000021,
                         self.attributes.bitmap)

        for i in itertools.chain(range(1, 5), range(6, 204), range(205, 256)):
            self.assertFalse(self.attributes.check(i))

    def _check_any_set(self):
        """Utility method to check if "any" bits are set. For the
           purposes of this test in only checks up to 256."""
        result = False
        for i in range(256):
            result |= self.attributes.check(i)
        return result

    def test_clear_all(self):
        """Check that clearing all bits works"""
        self.assertFalse(self._check_any_set())

        self.attributes.set(4)
        self.assertTrue(self._check_any_set())

        self.attributes.set(8)
        self.assertTrue(self._check_any_set())

        self.attributes.set(22)
        self.assertTrue(self._check_any_set())

        self.attributes.clear_all()
        self.assertFalse(self._check_any_set())

    def test_enumerate(self):
        """Check that enumerating the set bits works"""
        self.assertEqual(list(), list(self.attributes.enumerate()))

        self.attributes.set(8)
        self.assertEqual([8,], list(self.attributes.enumerate()))

        self.attributes.set(23)
        self.assertEqual([8, 23], list(self.attributes.enumerate()))

        self.attributes.set(0)
        self.assertEqual([0, 8, 23], list(self.attributes.enumerate()))

        self.attributes.set(211)
        self.assertEqual([0, 8, 23, 211], list(self.attributes.enumerate()))

        self.attributes.set(1035)
        self.assertEqual([0, 8, 23, 211, 1035], list(self.attributes.enumerate()))

        self.attributes.clear_all()
        self.assertEqual([], list(self.attributes.enumerate()))

        self.attributes.set(304)
        self.assertEqual([304,], list(self.attributes.enumerate()))

    def test_copy(self):
        """Test the copying works and that after copying the
           two objects remain independant."""
        other = screen.CharAttributes()
        other.set(4)

        self.assertFalse(self.attributes.check(4))
        self.assertTrue(other.check(4))

        other.copy_to(self.attributes)

        self.assertTrue(self.attributes.check(4))
        self.assertTrue(other.check(4))

        self.attributes.set(5)
        self.assertTrue(self.attributes.check(4))
        self.assertTrue(other.check(4))
        self.assertTrue(self.attributes.check(5))
        self.assertFalse(other.check(5))

        other.clear_all()
        self.assertTrue(self.attributes.check(4))
        self.assertFalse(other.check(4))
        self.assertTrue(self.attributes.check(5))
        self.assertFalse(other.check(5))

    def test_clear(self):
        """Test that clearing by bitnumber works."""
        self.assertFalse(self.attributes.check(34))
        self.attributes.set(34)
        self.assertTrue(self.attributes.check(34))
        self.attributes.clear(34)
        self.assertFalse(self.attributes.check(34))

    def test_mask(self):
        """Test setting and clearing using a bitmask."""
        self.assertEqual([], list(self.attributes.enumerate()))
        self.attributes.set_mask(0x58cf)
        self.assertEqual([0, 1, 2, 3, 6, 7, 11, 12, 14], list(self.attributes.enumerate()))
        self.attributes.clear_mask(0x17f2)
        self.assertEqual([0, 2, 3, 11, 14], list(self.attributes.enumerate()))

class TestScreenData(unittest.TestCase):
    """Test operations on ScreenData object."""

    def setUp(self):
        """Fixture is ScreenData object"""
        self.screen = screen.ScreenData()

    def test_row_enumerate(self):
        """Test enumerating data in a single row."""
        self.screen.current_window = screen.STATUS_WINDOW
        self.screen.cursor_x = 9
        self.screen.cursor_y = 5
        for char in b'abcdefghijklmnopqrstuvwxyz':
            self.screen.set_char(char)
        self.assertEqual(b'abcdefghijklmnopqrstuvwxyz',
                         bytes([data.char for data in
                                self.screen.enumerate_row(screen.STATUS_WINDOW, 9, 34, 5)]))
        self.assertEqual(b'jklmnop',
                         bytes([data.char for data in
                                self.screen.enumerate_row(screen.STATUS_WINDOW, 18, 24, 5)]))

    def test_range_enumerate(self):
        """Test enumerating multiline ranges of the screen data."""
        self.screen.current_window = screen.STATUS_WINDOW
        self.screen.cursor_x = 18
        self.screen.cursor_y = 7
        for row in (b'The quick brown fox ',
                    b'jumps over the lazy ',
                    b'dog. 1234567890'):
            for char in row:
                self.screen.set_char(char)
            self.screen.cursor_y += 1
            self.screen.cursor_x = 18

        # May as well test the dirty min/max while we are at it.
        self.assertEqual(18, self.screen.windows[screen.STATUS_WINDOW].dirty_x_min)
        self.assertEqual(37, self.screen.windows[screen.STATUS_WINDOW].dirty_x_max)
        self.assertEqual(7, self.screen.windows[screen.STATUS_WINDOW].dirty_y_min)
        self.assertEqual(9, self.screen.windows[screen.STATUS_WINDOW].dirty_y_max)

        # Enumerate a sub-piece of the window
        for b_row, s_row in zip((b'quic', b's ov', b' 123'),
                                self.screen.enumerate_range(screen.STATUS_WINDOW, 22, 25, 7, 9)):
            for byte, data in zip(b_row, s_row):
                self.assertEqual(byte, data.char)

    def test_clean_dirty(self): # pylint: disable=too-many-statements
        """Test the various ways that screen data can be marked dirty
           and that marking clean works as expected."""
        for win in range(screen.MAX_WINDOWS):
            self.assertFalse(self.screen.windows[win].has_dirty_data())

        self.screen.current_window = screen.MAP_WINDOW
        self.screen.cursor_x = 12
        self.screen.cursor_y = 4
        self.screen.set_char(ord(b'x'))
        self.assertFalse(self.screen.windows[screen.MSG_WINDOW].has_dirty_data())
        self.assertFalse(self.screen.windows[4].has_dirty_data())
        self.assertFalse(self.screen.windows[screen.STATUS_WINDOW].has_dirty_data())
        self.assertTrue(self.screen.windows[screen.MAP_WINDOW].has_dirty_data())
        self.assertEqual(12, self.screen.windows[screen.MAP_WINDOW].dirty_x_min)
        self.assertEqual(12, self.screen.windows[screen.MAP_WINDOW].dirty_x_max)
        self.assertEqual(4, self.screen.windows[screen.MAP_WINDOW].dirty_y_min)
        self.assertEqual(4, self.screen.windows[screen.MAP_WINDOW].dirty_y_max)

        self.screen.cursor_x = 1
        self.screen.cursor_y = 6
        self.screen.set_tile(20, 1)
        self.assertFalse(self.screen.windows[screen.MSG_WINDOW].has_dirty_data())
        self.assertFalse(self.screen.windows[4].has_dirty_data())
        self.assertFalse(self.screen.windows[screen.STATUS_WINDOW].has_dirty_data())
        self.assertTrue(self.screen.windows[screen.MAP_WINDOW].has_dirty_data())
        self.assertEqual(1, self.screen.windows[screen.MAP_WINDOW].dirty_x_min)
        self.assertEqual(12, self.screen.windows[screen.MAP_WINDOW].dirty_x_max)
        self.assertEqual(4, self.screen.windows[screen.MAP_WINDOW].dirty_y_min)
        self.assertEqual(6, self.screen.windows[screen.MAP_WINDOW].dirty_y_max)

        self.screen.current_window = 4
        # clearing data that is not set has no effect
        self.screen.clear_rows(9, 10)
        self.assertFalse(self.screen.windows[screen.MSG_WINDOW].has_dirty_data())
        self.assertFalse(self.screen.windows[4].has_dirty_data())
        self.assertFalse(self.screen.windows[screen.STATUS_WINDOW].has_dirty_data())
        self.assertTrue(self.screen.windows[screen.MAP_WINDOW].has_dirty_data())
        self.assertEqual(1, self.screen.windows[screen.MAP_WINDOW].dirty_x_min)
        self.assertEqual(12, self.screen.windows[screen.MAP_WINDOW].dirty_x_max)
        self.assertEqual(4, self.screen.windows[screen.MAP_WINDOW].dirty_y_min)
        self.assertEqual(6, self.screen.windows[screen.MAP_WINDOW].dirty_y_max)

        self.screen.current_window = screen.MSG_WINDOW
        # clear data that is not set has no effect
        self.screen.clear_cols(5, 21, 24)
        self.assertFalse(self.screen.windows[screen.MSG_WINDOW].has_dirty_data())
        self.assertFalse(self.screen.windows[4].has_dirty_data())
        self.assertFalse(self.screen.windows[screen.STATUS_WINDOW].has_dirty_data())
        self.assertTrue(self.screen.windows[screen.MAP_WINDOW].has_dirty_data())
        self.assertEqual(1, self.screen.windows[screen.MAP_WINDOW].dirty_x_min)
        self.assertEqual(12, self.screen.windows[screen.MAP_WINDOW].dirty_x_max)
        self.assertEqual(4, self.screen.windows[screen.MAP_WINDOW].dirty_y_min)
        self.assertEqual(6, self.screen.windows[screen.MAP_WINDOW].dirty_y_max)

        self.screen.clear_rows(8, 20, all_windows=True)
        self.assertFalse(self.screen.windows[screen.MSG_WINDOW].has_dirty_data())
        self.assertFalse(self.screen.windows[4].has_dirty_data())
        self.assertFalse(self.screen.windows[screen.STATUS_WINDOW].has_dirty_data())
        self.assertTrue(self.screen.windows[screen.MAP_WINDOW].has_dirty_data())
        self.assertEqual(1, self.screen.windows[screen.MAP_WINDOW].dirty_x_min)
        self.assertEqual(12, self.screen.windows[screen.MAP_WINDOW].dirty_x_max)
        self.assertEqual(4, self.screen.windows[screen.MAP_WINDOW].dirty_y_min)
        self.assertEqual(6, self.screen.windows[screen.MAP_WINDOW].dirty_y_max)

        self.screen.set_all_clean()
        for win in range(screen.MAX_WINDOWS):
            self.assertFalse(self.screen.windows[win].has_dirty_data())

        # only data that was previously filled in become dirty
        self.screen.clear_cols(3, 67, 4, all_windows=True)
        self.assertFalse(self.screen.windows[screen.MSG_WINDOW].has_dirty_data())
        self.assertFalse(self.screen.windows[4].has_dirty_data())
        self.assertFalse(self.screen.windows[screen.STATUS_WINDOW].has_dirty_data())
        self.assertTrue(self.screen.windows[screen.MAP_WINDOW].has_dirty_data())
        self.assertEqual(12, self.screen.windows[screen.MAP_WINDOW].dirty_x_min)
        self.assertEqual(12, self.screen.windows[screen.MAP_WINDOW].dirty_x_max)
        self.assertEqual(4, self.screen.windows[screen.MAP_WINDOW].dirty_y_min)
        self.assertEqual(4, self.screen.windows[screen.MAP_WINDOW].dirty_y_max)

        # setup data in multiple windows
        self.screen.current_window = 4
        self.screen.cursor_x = 1
        self.screen.cursor_y = 1
        self.screen.set_char(ord(b'b'))
        self.screen.current_window = screen.MSG_WINDOW
        self.screen.cursor_x = 75
        self.screen.cursor_y = 21
        self.screen.set_char(ord(b'v'))
        self.assertTrue(self.screen.windows[screen.MSG_WINDOW].has_dirty_data())
        self.assertTrue(self.screen.windows[4].has_dirty_data())
        self.assertFalse(self.screen.windows[screen.STATUS_WINDOW].has_dirty_data())
        self.assertTrue(self.screen.windows[screen.MAP_WINDOW].has_dirty_data())
        self.assertEqual(12, self.screen.windows[screen.MAP_WINDOW].dirty_x_min)
        self.assertEqual(12, self.screen.windows[screen.MAP_WINDOW].dirty_x_max)
        self.assertEqual(4, self.screen.windows[screen.MAP_WINDOW].dirty_y_min)
        self.assertEqual(4, self.screen.windows[screen.MAP_WINDOW].dirty_y_max)
        self.assertEqual(1, self.screen.windows[4].dirty_x_min)
        self.assertEqual(1, self.screen.windows[4].dirty_x_max)
        self.assertEqual(1, self.screen.windows[4].dirty_y_min)
        self.assertEqual(1, self.screen.windows[4].dirty_y_max)
        self.assertEqual(75, self.screen.windows[screen.MSG_WINDOW].dirty_x_min)
        self.assertEqual(75, self.screen.windows[screen.MSG_WINDOW].dirty_x_max)
        self.assertEqual(21, self.screen.windows[screen.MSG_WINDOW].dirty_y_min)
        self.assertEqual(21, self.screen.windows[screen.MSG_WINDOW].dirty_y_max)

        # Set all windows to be clean
        self.screen.set_all_clean()
        for win in range(screen.MAX_WINDOWS):
            self.assertFalse(self.screen.windows[win].has_dirty_data())

        # Any data that gets cleared will be dirty
        self.screen.clear_rows(2, 24, all_windows=True)
        self.assertTrue(self.screen.windows[screen.MSG_WINDOW].has_dirty_data())
        self.assertFalse(self.screen.windows[4].has_dirty_data())
        self.assertFalse(self.screen.windows[screen.STATUS_WINDOW].has_dirty_data())
        self.assertTrue(self.screen.windows[screen.MAP_WINDOW].has_dirty_data())
        self.assertEqual(1, self.screen.windows[screen.MAP_WINDOW].dirty_x_min)
        self.assertEqual(1, self.screen.windows[screen.MAP_WINDOW].dirty_x_max)
        self.assertEqual(6, self.screen.windows[screen.MAP_WINDOW].dirty_y_min)
        self.assertEqual(6, self.screen.windows[screen.MAP_WINDOW].dirty_y_max)
        self.assertEqual(75, self.screen.windows[screen.MSG_WINDOW].dirty_x_min)
        self.assertEqual(75, self.screen.windows[screen.MSG_WINDOW].dirty_x_max)
        self.assertEqual(21, self.screen.windows[screen.MSG_WINDOW].dirty_y_min)
        self.assertEqual(21, self.screen.windows[screen.MSG_WINDOW].dirty_y_max)

    def test_screen_attrs(self):
        """Test the attributes set into the screen current_attributes are transfer
           into any written characters. And the subsequent changes to current_attributes
           do not affect previously written characters."""
        self.screen.set_char(ord(b'a'))
        self.screen.current_attributes.set(4)
        self.screen.set_char(ord(b'b'))
        self.screen.set_char(ord(b'c'))
        self.screen.current_attributes.set(9)
        self.screen.set_char(ord(b'd'))
        self.screen.set_char(ord(b'e'))
        self.screen.current_attributes.clear_all()
        self.screen.set_char(ord(b'f'))
        self.screen.set_char(ord(b'g'))

        (a, b, c, d, e, f, g) = self.screen.enumerate_row(screen.BASE_WINDOW, 1, 7, 1) # pylint: disable=invalid-name
        self.assertEqual(a.char, ord(b'a'))
        self.assertEqual(list(a.attributes.enumerate()), [])
        self.assertEqual(b.char, ord(b'b'))
        self.assertEqual(list(b.attributes.enumerate()), [4,])
        self.assertEqual(c.char, ord(b'c'))
        self.assertEqual(list(c.attributes.enumerate()), [4,])
        self.assertEqual(d.char, ord(b'd'))
        self.assertEqual(list(d.attributes.enumerate()), [4, 9])
        self.assertEqual(e.char, ord(b'e'))
        self.assertEqual(list(e.attributes.enumerate()), [4, 9])
        self.assertEqual(f.char, ord(b'f'))
        self.assertEqual(list(f.attributes.enumerate()), [])
        self.assertEqual(g.char, ord(b'g'))
        self.assertEqual(list(g.attributes.enumerate()), [])

    def test_clear(self):
        """Test the ScreenData functions that clear data"""
        self.screen.cursor_x = 5
        self.screen.cursor_y = 3
        for _ in range(10):
            for char in range(ord('a'), ord('g')+1):
                self.screen.set_char(char)
            self.screen.cursor_x = 5
            self.screen.cursor_y += 1
        self.screen.clear_rows(4, 5)
        self.screen.clear_cols(8, 10, 9)

        for (rng, row_list) in zip(self.screen.enumerate_range(screen.BASE_WINDOW, 4, 13, 2, 14),
                                   [[None]*10,
                                    [None, b'a', b'b', b'c', b'd', b'e', b'f', b'g', None],
                                    [None]*10,
                                    [None]*10,
                                    [None, b'a', b'b', b'c', b'd', b'e', b'f', b'g', None],
                                    [None, b'a', b'b', b'c', b'd', b'e', b'f', b'g', None],
                                    [None, b'a', b'b', b'c', b'd', b'e', b'f', b'g', None],
                                    [None, b'a', b'b', b'c', None, None, None, b'g', None],
                                    [None, b'a', b'b', b'c', b'd', b'e', b'f', b'g', None],
                                    [None, b'a', b'b', b'c', b'd', b'e', b'f', b'g', None],
                                    [None, b'a', b'b', b'c', b'd', b'e', b'f', b'g', None],
                                    [None]*10]):
            for data, byte in zip(rng, row_list):
                self.assertEqual(data.char, None if byte is None else ord(byte))

if __name__ == '__main__':
    unittest.main()
