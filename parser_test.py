"""Test the nethack parser module"""

import unittest

import parser

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

if __name__ == '__main__':
    unittest.main()
