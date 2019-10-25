
import itertools
import os
import time
import unittest

import screen
import server

class TestDefaultSubprocess(unittest.TestCase):

    def setUp(self):
        # constantly killing nethack messes up the locks
        os.system(b'rm ~/nh/install/games/lib/nethackdir/*lock* 2> /dev/null')
        # tests shouldn't use a savefile
        os.system(b'rm ~/nh/install/games/lib/nethackdir/save/* 2> /dev/null')
        self.nh = server.default_subprocess()

    def tearDown(self):
        self.nh.terminate()

    def test_startup(self):
        data = self.nh.read()
        self.assertTrue(data, msg="Some output from nethack")

    def test_input(self):
        data = self.nh.read()
        while data:
            data = self.nh.read()
        self.nh.write(b' ')
        data = self.nh.read()
        print(data)
        self.assertTrue(data, msg="Input didn't create more output")

class TestCharAttributes(unittest.TestCase):

    def setUp(self):
        self.attributes = screen.CharAttributes()

    def test_set_check(self):
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
        result = False
        for i in range(256):
            result |= self.attributes.check(i)
        return result

    def test_clear_all(self):
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

class TestScreenData(unittest.TestCase):

    def setUp(self):
        self.screen = screen.ScreenData()

    def test_row_enumerate(self):
        self.screen.current_window = screen.STATUS_WINDOW
        self.screen.cursor_x = 9
        self.screen.cursor_y = 5
        for c in b'abcdefghijklmnopqrstuvwxyz':
            self.screen.set_char(c)
        self.assertEqual(b'abcdefghijklmnopqrstuvwxyz',
                         bytes([data.char for data in self.screen.enumerate_row(screen.STATUS_WINDOW, 9, 34, 5)]))
        self.assertEqual(b'jklmnop',
                         bytes([data.char for data in self.screen.enumerate_row(screen.STATUS_WINDOW, 18, 24, 5)]))

    def test_range_enumerate(self):
        self.screen.current_window = screen.INV_WINDOW
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
        self.assertEqual(18, self.screen.windows[screen.INV_WINDOW].dirty_x_min)
        self.assertEqual(37, self.screen.windows[screen.INV_WINDOW].dirty_x_max)
        self.assertEqual( 7, self.screen.windows[screen.INV_WINDOW].dirty_y_min)
        self.assertEqual( 9, self.screen.windows[screen.INV_WINDOW].dirty_y_max)

        # Enumerate a sub-piece of the window
        for b_row, s_row in zip((b'quic', b's ov', b' 123'),
                                self.screen.enumerate_range(screen.INV_WINDOW, 22, 25, 7, 9)):
            for byte, data in zip(b_row, s_row):
                self.assertEqual(byte, data.char)

    def test_clean_dirty(self):
        for win in range(screen.NUM_WINDOWS):
            self.assertFalse(self.screen.windows[win].has_dirty_data())

        self.screen.current_window = screen.MAP_WINDOW
        self.screen.cursor_x = 12
        self.screen.cursor_y = 4
        self.screen.set_char(ord(b'x'))
        self.assertFalse(self.screen.windows[screen.MSG_WINDOW].has_dirty_data())
        self.assertFalse(self.screen.windows[screen.INV_WINDOW].has_dirty_data())
        self.assertFalse(self.screen.windows[screen.STATUS_WINDOW].has_dirty_data())
        self.assertTrue(self.screen.windows[screen.MAP_WINDOW].has_dirty_data())
        self.assertEqual(12, self.screen.windows[screen.MAP_WINDOW].dirty_x_min)
        self.assertEqual(12, self.screen.windows[screen.MAP_WINDOW].dirty_x_max)
        self.assertEqual( 4, self.screen.windows[screen.MAP_WINDOW].dirty_y_min)
        self.assertEqual( 4, self.screen.windows[screen.MAP_WINDOW].dirty_y_max)

        self.screen.cursor_x = 1
        self.screen.cursor_y = 6
        self.screen.set_tile(20, 1)
        self.assertFalse(self.screen.windows[screen.MSG_WINDOW].has_dirty_data())
        self.assertFalse(self.screen.windows[screen.INV_WINDOW].has_dirty_data())
        self.assertFalse(self.screen.windows[screen.STATUS_WINDOW].has_dirty_data())
        self.assertTrue(self.screen.windows[screen.MAP_WINDOW].has_dirty_data())
        self.assertEqual( 1, self.screen.windows[screen.MAP_WINDOW].dirty_x_min)
        self.assertEqual(12, self.screen.windows[screen.MAP_WINDOW].dirty_x_max)
        self.assertEqual( 4, self.screen.windows[screen.MAP_WINDOW].dirty_y_min)
        self.assertEqual( 6, self.screen.windows[screen.MAP_WINDOW].dirty_y_max)

        self.screen.current_window = screen.INV_WINDOW
        # clearing data that is not set has no effect
        self.screen.clear_rows(9, 10)
        self.assertFalse(self.screen.windows[screen.MSG_WINDOW].has_dirty_data())
        self.assertFalse(self.screen.windows[screen.INV_WINDOW].has_dirty_data())
        self.assertFalse(self.screen.windows[screen.STATUS_WINDOW].has_dirty_data())
        self.assertTrue(self.screen.windows[screen.MAP_WINDOW].has_dirty_data())
        self.assertEqual( 1, self.screen.windows[screen.MAP_WINDOW].dirty_x_min)
        self.assertEqual(12, self.screen.windows[screen.MAP_WINDOW].dirty_x_max)
        self.assertEqual( 4, self.screen.windows[screen.MAP_WINDOW].dirty_y_min)
        self.assertEqual( 6, self.screen.windows[screen.MAP_WINDOW].dirty_y_max)

        self.screen.current_window = screen.MSG_WINDOW
        # clear data that is not set has no effect
        self.screen.clear_cols(5, 21, 24)
        self.assertFalse(self.screen.windows[screen.MSG_WINDOW].has_dirty_data())
        self.assertFalse(self.screen.windows[screen.INV_WINDOW].has_dirty_data())
        self.assertFalse(self.screen.windows[screen.STATUS_WINDOW].has_dirty_data())
        self.assertTrue(self.screen.windows[screen.MAP_WINDOW].has_dirty_data())
        self.assertEqual( 1, self.screen.windows[screen.MAP_WINDOW].dirty_x_min)
        self.assertEqual(12, self.screen.windows[screen.MAP_WINDOW].dirty_x_max)
        self.assertEqual( 4, self.screen.windows[screen.MAP_WINDOW].dirty_y_min)
        self.assertEqual( 6, self.screen.windows[screen.MAP_WINDOW].dirty_y_max)

        self.screen.clear_rows(8, 20, all_windows=True)
        self.assertFalse(self.screen.windows[screen.MSG_WINDOW].has_dirty_data())
        self.assertFalse(self.screen.windows[screen.INV_WINDOW].has_dirty_data())
        self.assertFalse(self.screen.windows[screen.STATUS_WINDOW].has_dirty_data())
        self.assertTrue(self.screen.windows[screen.MAP_WINDOW].has_dirty_data())
        self.assertEqual( 1, self.screen.windows[screen.MAP_WINDOW].dirty_x_min)
        self.assertEqual(12, self.screen.windows[screen.MAP_WINDOW].dirty_x_max)
        self.assertEqual( 4, self.screen.windows[screen.MAP_WINDOW].dirty_y_min)
        self.assertEqual( 6, self.screen.windows[screen.MAP_WINDOW].dirty_y_max)

        self.screen.set_all_clean()
        for win in range(screen.NUM_WINDOWS):
            self.assertFalse(self.screen.windows[win].has_dirty_data())

        # only data that was previously filled in become dirty
        self.screen.clear_cols(3, 67, 4, all_windows=True)
        self.assertFalse(self.screen.windows[screen.MSG_WINDOW].has_dirty_data())
        self.assertFalse(self.screen.windows[screen.INV_WINDOW].has_dirty_data())
        self.assertFalse(self.screen.windows[screen.STATUS_WINDOW].has_dirty_data())
        self.assertTrue(self.screen.windows[screen.MAP_WINDOW].has_dirty_data())
        self.assertEqual(12, self.screen.windows[screen.MAP_WINDOW].dirty_x_min)
        self.assertEqual(12, self.screen.windows[screen.MAP_WINDOW].dirty_x_max)
        self.assertEqual( 4, self.screen.windows[screen.MAP_WINDOW].dirty_y_min)
        self.assertEqual( 4, self.screen.windows[screen.MAP_WINDOW].dirty_y_max)

        # setup data in multiple windows
        self.screen.current_window = screen.INV_WINDOW
        self.screen.cursor_x = 1
        self.screen.cursor_y = 1
        self.screen.set_char(ord(b'b'))
        self.screen.current_window = screen.MSG_WINDOW
        self.screen.cursor_x = 75
        self.screen.cursor_y = 21
        self.screen.set_char(ord(b'v'))
        self.assertTrue(self.screen.windows[screen.MSG_WINDOW].has_dirty_data())
        self.assertTrue(self.screen.windows[screen.INV_WINDOW].has_dirty_data())
        self.assertFalse(self.screen.windows[screen.STATUS_WINDOW].has_dirty_data())
        self.assertTrue(self.screen.windows[screen.MAP_WINDOW].has_dirty_data())
        self.assertEqual(12, self.screen.windows[screen.MAP_WINDOW].dirty_x_min)
        self.assertEqual(12, self.screen.windows[screen.MAP_WINDOW].dirty_x_max)
        self.assertEqual( 4, self.screen.windows[screen.MAP_WINDOW].dirty_y_min)
        self.assertEqual( 4, self.screen.windows[screen.MAP_WINDOW].dirty_y_max)
        self.assertEqual( 1, self.screen.windows[screen.INV_WINDOW].dirty_x_min)
        self.assertEqual( 1, self.screen.windows[screen.INV_WINDOW].dirty_x_max)
        self.assertEqual( 1, self.screen.windows[screen.INV_WINDOW].dirty_y_min)
        self.assertEqual( 1, self.screen.windows[screen.INV_WINDOW].dirty_y_max)
        self.assertEqual(75, self.screen.windows[screen.MSG_WINDOW].dirty_x_min)
        self.assertEqual(75, self.screen.windows[screen.MSG_WINDOW].dirty_x_max)
        self.assertEqual(21, self.screen.windows[screen.MSG_WINDOW].dirty_y_min)
        self.assertEqual(21, self.screen.windows[screen.MSG_WINDOW].dirty_y_max)

        # Set all windows to be clean
        self.screen.set_all_clean()
        for win in range(screen.NUM_WINDOWS):
            self.assertFalse(self.screen.windows[win].has_dirty_data())

        # Any data that gets cleared will be dirty
        self.screen.clear_rows(2, 24, all_windows=True)
        self.assertTrue(self.screen.windows[screen.MSG_WINDOW].has_dirty_data())
        self.assertFalse(self.screen.windows[screen.INV_WINDOW].has_dirty_data())
        self.assertFalse(self.screen.windows[screen.STATUS_WINDOW].has_dirty_data())
        self.assertTrue(self.screen.windows[screen.MAP_WINDOW].has_dirty_data())
        self.assertEqual( 1, self.screen.windows[screen.MAP_WINDOW].dirty_x_min)
        self.assertEqual( 1, self.screen.windows[screen.MAP_WINDOW].dirty_x_max)
        self.assertEqual( 6, self.screen.windows[screen.MAP_WINDOW].dirty_y_min)
        self.assertEqual( 6, self.screen.windows[screen.MAP_WINDOW].dirty_y_max)
        self.assertEqual(75, self.screen.windows[screen.MSG_WINDOW].dirty_x_min)
        self.assertEqual(75, self.screen.windows[screen.MSG_WINDOW].dirty_x_max)
        self.assertEqual(21, self.screen.windows[screen.MSG_WINDOW].dirty_y_min)
        self.assertEqual(21, self.screen.windows[screen.MSG_WINDOW].dirty_y_max)

    def test_screen_attrs(self):
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

        (a, b, c, d, e, f, g) = self.screen.enumerate_row(screen.BASE_WINDOW, 1, 7, 1)
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
        self.screen.cursor_x = 5
        self.screen.cursor_y = 3
        for _ in range(10):
            for ch in range(ord('a'), ord('g')+1):
                self.screen.set_char(ch)
            self.screen.cursor_x = 5
            self.screen.cursor_y += 1
        self.screen.clear_rows(4, 5)
        self.screen.clear_cols(8, 10, 9)

        y = 2
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
