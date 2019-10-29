"""This parser can read data from a nethack proces (server) and
   convert it into the screendata model."""

import itertools

import screen

class ParseException(Exception):
    """If the parser raises this exception then a fatal error has
       occurred. The parser object will be in an undefined state
       after raising the exception."""

# mini state machine for parsing tile escapes
TILE_STATE_END = 1
TILE_STATE_START = 2
TILE_STATE_MID = 3

class Parser:
    """Class representing the parser."""

    def __init__(self):
        """Initialize the parser. Starts with empty screendata.
           escape_sequence = None mean no escape syntax in progress
           Otherwise the escape_sequence is a bytearray that contains
           the sequence so far.
        """
        self.screen = screen.ScreenData()
        self.escape_sequence = None
        self.end_of_data = True
        self.tile_state = TILE_STATE_END

    @staticmethod
    def is_parameter_byte(byte):
        """Is this a valid escape sequence parameter byte. Technically
           there separate ranges for parameter vs 'intermediate' bytes,
           but this code treats them all as one."""
        return 0x20 <= byte <= 0x3f

    @staticmethod
    def is_final_byte(byte):
        """Is this a 'final byte' that ends an escape syntax."""
        return 0x40 <= byte <= 0x7e

    def parse_bytes(self, bytes_):
        """Convenience. Loop over the bytes and call parseByte on each one"""
        for byte in bytes_:
            self.parse_byte(byte)

    def parse_byte(self, byte): # pylint: disable=too-many-branches
        """Parse the input stream byte-by-byte."""
        self.end_of_data = False
        if byte == 27:
            if self.escape_sequence is None:
                self.escape_sequence = bytearray()
            elif self.escape_sequence == b'':
                # Two escapes in a row is "nothing"
                self.escape_sequence = None
            else:
                # Illegal escape syntax, got another escape before final byte
                raise ParseException("Illegal escape syntax")
        elif self.escape_sequence is not None:
            if not self.escape_sequence:
                if byte != ord(b'['):
                    # We can only handle CSI sequences
                    raise ParseException("Illegal escape prefix")
                self.escape_sequence.append(byte)
            elif self.is_final_byte(byte):
                self.handle_escape_sequence(byte, self.escape_sequence)
                self.escape_sequence = None
            elif not self.is_parameter_byte(byte):
                # Illegal escape syntax, not valid byte for an escape syntax
                raise ParseException("Illegal escape syntax")
            else:
                self.escape_sequence.append(byte)
        else:
            # Non-escape sequence character, check for screen movement chars
            if byte == 8:
                # Backspace
                self.screen.cursor_x -= 1
                self.screen.clamp_cursor()
            elif byte == 10:
                # Line feed
                self.screen.cursor_y += 1
                self.screen.clamp_cursor()
            elif byte == 13:
                # Carrige return
                self.screen.cursor_x = 1
            elif byte < 32:
                # Ignore other control characters
                pass
            else:
                # handle clearing tiledata state-machine
                if self.screen.current_window == screen.MAP_WINDOW:
                    if self.tile_state == TILE_STATE_END:
                        # Writing data outside a tile escape clears the tiledata
                        self.screen.get_current_data().clear_tile()
                    elif self.tile_state == TILE_STATE_START:
                        # a single char is allowed per tile
                        self.tile_state = TILE_STATE_MID
                    elif self.tile_state == TILE_STATE_MID:
                        # got a second char in the tile
                        raise ParseException('Multiple characters in tile')
                self.screen.set_char(byte)

    @staticmethod
    def parse_escape_args(seq, defaults):
        """Parse the argument bits of the escape sequence,
           integers separated by semicolons. Any missing
           arguments will be filled in from defaults."""
        if len(seq) == 1:
            splt = ()
        else:
            splt = seq[1:].split(b';')
        if len(splt) > len(defaults):
            raise ParseException("Too many escape sequence arguments")
        for tok, dflt in itertools.zip_longest(splt, defaults):
            tok = b"" if tok is None else tok.strip()
            if not tok:
                yield dflt
            else:
                try:
                    num = int(tok, 10)
                    if num < 0:
                        raise ParseException("Escape sequence argument must be positive")
                    yield num
                except ValueError:
                    raise ParseException("Non-numeric escape sequence argument: "+str(tok))

    def handle_sgr_attribute(self, num):
        """The SGR escape controls the look of the characters, and the processing
           of the options is surprisingly complicated. It's unlikely that this is
           really 100% correct for full vt100 terminal emulation, but it is at
           least good enough to parse nethack."""
        # NORMAL == no attributes
        if num == screen.ATTR_NORMAL:
            self.screen.current_attributes.clear_all()
            return

        # Some attributes are mutually exclusive
        exclusive_bitmasks = (screen.ATTR_INTENSITY_BITMASK, screen.ATTR_BLINK_BITMASK,
                              screen.ATTR_FONT_BITMASK, screen.ATTR_FG_BITMASK,
                              screen.ATTR_BG_BITMASK)
        for mask in exclusive_bitmasks:
            if mask & (1 << num):
                self.screen.current_attributes.clear_mask(mask)
                if num not in (screen.ATTR_DEFAULT_FONT, screen.ATTR_DEFAULT_FG,
                               screen.ATTR_DEFAULT_BG):
                    self.screen.current_attributes.set(num)
                return

        # Some attributes actually negate other attributes
        negative_attrs = ((screen.ATTR_NORMAL_INTENSITY, screen.ATTR_INTENSITY_BITMASK),
                          (screen.ATTR_NOT_ITALIC, 1<<screen.ATTR_ITALIC),
                          (screen.ATTR_NOT_UNDERLINE, screen.ATTR_UNDERLINE_BITMASK),
                          (screen.ATTR_BLINK_OFF, screen.ATTR_BLINK_BITMASK),
                          (screen.ATTR_INVERSE_OFF, 1<<screen.ATTR_INVERSE),
                          (screen.ATTR_CONCEAL_OFF, 1<<screen.ATTR_CONCEAL),
                          (screen.ATTR_STRIKE_OFF, 1<<screen.ATTR_STRIKE))
        for attr, mask in negative_attrs:
            if num == attr:
                self.screen.current_attributes.clear_mask(mask)
                return

        # This attribute also clears bold in addition to setting the attr, for whatever reason
        if num == screen.ATTR_2X_UNDERLINE:
            self.screen.current_attributes.clear(screen.ATTR_BOLD)

        # simple bitmask set is the default
        self.screen.current_attributes.set(num)

    def handle_escape_sequence(self, final_byte, seq): # pylint: disable=too-many-branches,too-many-statements,too-many-locals
        """Handle the given escape syntax. Don't include actual escape (27) character
           and pass the final byte only in the separate argument."""
        if seq[0] == ord(b'['):
            if final_byte == ord(b'A'):
                # Cursor Up
                (num,) = self.parse_escape_args(seq, (1,))
                self.screen.cursor_y -= num
                self.screen.clamp_cursor()
            elif final_byte == ord(b'B'):
                # Cursor Down
                (num,) = self.parse_escape_args(seq, (1,))
                self.screen.cursor_y += num
                self.screen.clamp_cursor()
            elif final_byte == ord(b'C'):
                # Cursor Forward
                (num,) = self.parse_escape_args(seq, (1,))
                self.screen.cursor_x += num
                self.screen.clamp_cursor()
            elif final_byte == ord(b'D'):
                # Cursor Back
                (num,) = self.parse_escape_args(seq, (1,))
                self.screen.cursor_x -= num
                self.screen.clamp_cursor()
            elif final_byte == ord(b'E'):
                # Cursor Next Line
                (num,) = self.parse_escape_args(seq, (1,))
                self.screen.cursor_y += num
                self.screen.cursor_x = 1
                self.screen.clamp_cursor()
            elif final_byte == ord(b'F'):
                # Cursor Previous Line
                (num,) = self.parse_escape_args(seq, (1,))
                self.screen.cursor_y -= num
                self.screen.cursor_x = 1
                self.screen.clamp_cursor()
            elif final_byte == ord(b'G'):
                # Cursor Horizontal Absolute
                (num,) = self.parse_escape_args(seq, (1,))
                self.screen.cursor_x = num
                self.screen.clamp_cursor()
            elif final_byte == ord(b'H') or final_byte == ord(b'f'):
                # Cursor Position
                # y is first!
                (y, x) = self.parse_escape_args(seq, (1, 1))
                self.screen.cursor_x = x
                self.screen.cursor_y = y
                self.screen.clamp_cursor()
            elif final_byte == ord(b'J'):
                # Erase in Display
                (num,) = self.parse_escape_args(seq, (0,))
                if num == 0:
                    start_y = self.screen.cursor_y
                    end_y = screen.ROWS
                elif num == 1:
                    start_y = 1
                    end_y = self.screen.cursor_y
                elif num in (2, 3):
                    start_y = 1
                    end_y = screen.ROWS
                else:
                    raise ParseException("Illegal escape erase display code")
                self.screen.clear_rows(start_y, end_y, all_windows=True)
            elif final_byte == ord(b'K'):
                # Erase in Line
                (num,) = self.parse_escape_args(seq, (0,))
                if num == 0:
                    start_x = self.screen.cursor_x
                    end_x = screen.COLUMNS
                elif num == 1:
                    start_x = 1
                    end_x = self.screen.cursor_x
                elif num == 2:
                    start_x = 1
                    end_x = screen.COLUMNS
                else:
                    raise ParseException('Illegal escape erase line code')
                self.screen.clear_cols(start_x, end_x, self.screen.cursor_y, all_windows=True)
            elif final_byte in (ord(b'h'), ord(b'l'), ord(b't')):
                # ignore some 'private' sequences
                pass
            elif final_byte == ord(b'm'):
                # Select Graphic Rendition
                extra_args = [None, None, None, None]
                (num, extra_args[0], extra_args[1], extra_args[2], extra_args[3]) = \
                    self.parse_escape_args(seq, (0, None, None, None, None))
                # Annoyingly the "custom color" SGR can take arguments. The arguments are ignored
                # for now and just the custom color flag is set without the rgb value, etc.
                # Nethack doesn't seem to use these anyway. Just verify that no other SGR codes
                # got unexpected arguments.
                num_extra_args = 0
                for i in range(4):
                    if extra_args[i] is not None:
                        num_extra_args += 1
                if num in (screen.ATTR_SET_COLOR_FG, screen.ATTR_SET_COLOR_BG):
                    if num_extra_args not in (2, 4):
                        raise ParseException("Incorrect number of arguments to set color")
                else:
                    if num_extra_args != 0:
                        raise ParseException("Unexpected argument to SGR escape")
                self.handle_sgr_attribute(num)
            elif final_byte == ord(b'z'):
                # nethack vt_tiledata escape
                (version, td_code, num1, num2) = self.parse_escape_args(seq,
                                                                        (None, None, None, None))
                if version != 1:
                    raise ParseException('Wrong version of vt_tiledata escape')
                if td_code == 0:
                    # Start Glyph
                    if self.tile_state != TILE_STATE_END:
                        raise ParseException('Nested tiledata escapes')
                    if self.screen.current_window != screen.MAP_WINDOW:
                        raise ParseException('Tiledata outside of map window')
                    self.tile_state = TILE_STATE_START
                    self.screen.set_tile(num1, num2)
                elif td_code == 1:
                    # End Glyph
                    if not (num1 is None and num2 is None):
                        raise ParseException('Unexpected argument to end glyph')
                    if self.tile_state != TILE_STATE_MID:
                        raise ParseException('Unexpected end glyph context')
                    self.tile_state = TILE_STATE_END
                elif td_code == 2:
                    # Switch Window
                    if num2 is not None:
                        raise ParseException('Too many arguments to switch window')
                    if self.tile_state != TILE_STATE_END:
                        raise ParseException('Switch window during tiledata')
                    self.screen.current_window = num1
                elif td_code == 3:
                    # End of Data
                    if not (num1 is None and num2 is None):
                        raise ParseException('Unexpected argument to end-of-data')
                    if self.tile_state != TILE_STATE_END:
                        raise ParseException('End-of-date during tiledata')
                    self.end_of_data = True
                else:
                    raise ParseException('Unrecognized vt_tiledata escape code')
            else:
                raise ParseException('Illegal escape code suffix')
        else:
            raise ParseException("Unrecognized escape syntax prefix")
