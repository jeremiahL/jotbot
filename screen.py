"""Model of the screen contents of a nethack game.
   It uses vt_tiledata to distinguish between multiple
   windows"""

class CharAttributes:
    """Represent character attributes such as bold, reverse, color, etc."""

    def __init__(self):
        """Initializes an empty attributes object."""
        self.bitmap = 0

    def set(self, attr_num):
        """Set the numbered attribute in the bitmask."""
        self.bitmap |= (1 << attr_num)

    def check(self, attr_num):
        """Return true if the numbered attribute is set."""
        return self.bitmap & (1 << attr_num)

    def clear_all(self):
        """Clear all attributes that are currently set."""
        self.bitmap = 0

    def enumerate(self):
        """Return an iterator that returns the number of all set
           attributes in the bitmask."""
        bits = self.bitmap
        pos = 0
        while bits:
            if bits & 1:
                yield pos
            pos += 1
            bits >>= 1

    def copy_to(self, target):
        """Copy all attributes in the current bitmask in to the
           given bitmask."""
        target.bitmap = self.bitmap

class CharData:
    """Represents a single character with its attributes."""

    def __init__(self):
        """The character data is initialize empty."""
        self.attributes = CharAttributes()
        self.char = None
        self.dirty = False

    def clear(self):
        """Reset the character data back to empty with no attributes."""
        self.char = None
        self.attributes.clear_all()

class TileData(CharData):
    """Extends CharData to also include tiledata"""

    def __init__(self):
        """The tiledata implements empty."""
        super().__init__()
        self.tile_num = None
        self.tile_flag = None

    def clear(self):
        """Reset the character data and tiledata back to empty."""
        super().clear()
        self.tile_num = None
        self.tile_flag = None

# vt_tiledata window numbers
BASE_WINDOW = 0
MSG_WINDOW = 1
STATUS_WINDOW = 2
MAP_WINDOW = 3
INV_WINDOW = 4
NUM_WINDOWS = 5

COLUMNS = 80
ROWS = 24

class WindowData:
    """Represent an entire 80x25 "window" of data. Nethack emits an escape code
       before emitting characters which indicates which window the data is
       intended for. The window data object can also track what portion of
       a window has changed with the "dirty" flags."""

    def __init__(self, use_tile_data):
        """Initialize the window into an array of empty characters, all of which
           are marked cleaned by default.
           use_tile_data - if True fill the array with TileData, else CharData"""
        self.dirty_x_max = None
        self.dirty_x_min = None
        self.dirty_y_max = None
        self.dirty_y_min = None
        self.char_data = list()
        for _ in range(COLUMNS):
            window_col = list()
            for _ in range(ROWS):
                if use_tile_data:
                    window_col.append(TileData())
                else:
                    window_col.append(CharData())
            self.char_data.append(window_col)

    def has_dirty_data(self):
        """Return True if any characters in the window are dirty."""
        if self.dirty_x_min is None:
            assert self.dirty_x_max is None
            assert self.dirty_y_min is None
            assert self.dirty_y_max is None
            return False
        return True

    def set_dirty(self, x, y):
        """Set the dirty flag on the character as the given coordinates.
           Both the flag on the character and the dirty min/max
           coordinates will be updated (if necessary)"""
        self.char_data[x][y].dirty = True
        if not self.has_dirty_data():
            self.dirty_x_min = x
            self.dirty_x_max = x
            self.dirty_y_min = y
            self.dirty_y_max = y
        else:
            if x < self.dirty_x_min:
                self.dirty_x_min = x
            elif x > self.dirty_x_max:
                self.dirty_x_max = x
            if y < self.dirty_y_min:
                self.dirty_y_min = y
            else:
                self.dirty_y_max = y

    def set_all_clean(self):
        """Set all character data objects in the window as clean and
           reset the dirty min/max coordinates (to None)"""
        for x in range(self.dirty_x_min, self.dirty_x_max+1):
            for y in range(self.dirty_y_min, self.dirty_y_max+1):
                self.char_data[x][y].dirty = False
        self.dirty_x_min = None
        self.dirty_x_max = None
        self.dirty_y_min = None
        self.dirty_y_max = None

class ScreenData:
    """Track all data that makes up the nethack screen. This includes
       character data layered into multiple windows, the current position
       of the cursor, the current active window, and the current attributes
       set for new characters."""

    def __init__(self):
        """All windows are initialized empty, with the cursor set to 0,0 in the base window."""
        self.windows = list()
        for win in range(NUM_WINDOWS):
            self.windows.append(WindowData(use_tile_data=(win == MAP_WINDOW)))
        self.current_attributes = CharAttributes()
        self.current_window = BASE_WINDOW
        self.cursor_x = 0
        self.cursor_y = 0

    def get_current_data(self):
        """Return the CharData object at the cursor location in the current window."""
        return self.get_data(self.current_window, self.cursor_x, self.cursor_y)

    def get_data(self, window, x, y):
        """Return the CharData from the given window and the given coordinates."""
        return self.windows[window].char_data[x][y]

    def set_current_dirty(self):
        """Set the character at the cusor location in the current window to be dirty."""
        self.windows[self.current_window].set_dirty(self.cursor_x, self.cursor_y)

    def set_char(self, char):
        """Set the character data at the cursor location in the current window to be the
           given char with the current attributes and advance the cursor. If this
           changes the data at the location, mark the character data as dirty."""
        current_data = self.get_current_data()
        if (current_data.char != char or
                self.current_attributes.bitmap != current_data.attributes.bitmap):
            current_data.char = char
            self.current_attributes.copy_to(current_data.attributes)
            self.set_current_dirty()
        self.cursor_x += 1

    def set_tile(self, num, flag):
        """Set the tiledata at the cursor location to the given tile number and flag.
           This is only valid when the map window is the current window, and should
           not be called when other windows are active. If this call changes the tile
           data at the location, mark the tile/character data as dirty."""
        assert self.current_window == MAP_WINDOW
        current_data = self.get_current_data()
        if (current_data.tile_num != num or current_data.tile_flag != flag):
            current_data.tile_num = num
            current_data.tile_flag = flag
            self.set_current_dirty()

    def set_all_clean(self):
        """Sets the window data for all windows to be clean."""
        for window in range(0, NUM_WINDOWS):
            self.windows[window].set_clean()

    def _window_range(self, all_windows):
        """Internal function: all_windows==False, return a range of only the current window number
                              all_windows==True, return a range of all possible windows numbers."""
        if all_windows:
            return range(0, NUM_WINDOWS)
        return range(self.current_window, self.current_window + 1)

    def clear_rows(self, start_y, end_y, all_windows=False):
        """Clear character data and mark it dirty for all rows from
           start_y to end_y. all_windows==False(default), current window only.
           all_windows==True, all windows"""
        for win in self._window_range(all_windows):
            for x in range(0, COLUMNS):
                for y in range(start_y, end_y):
                    self.get_data(win, x, y).clear()
                    self.windows[win].set_dirty(x, y)

    def clear_cols(self, start_x, end_x, y, all_windows=False):
        """Clear character data and mark it dirty from
           start_x to end_x in row y. all_windows==False(default), current window only.
           all_windows==True, all windows"""
        for win in self._window_range(all_windows):
            for x in range(start_x, end_x):
                self.get_data(win, x, y).clear()
                self.windows[win].set_dirty(x, y)

    def enumerate_row(self, win, start_x, end_x, y):
        """Return an iterator that returns a portion of a row"""
        for x in range(start_x, end_x):
            yield self.windows[win].char_data[x][y]

    def enumerate_range(self, win, start_x, end_x, start_y, end_y):
        """Return an iterator of iterators the covers the range from
           (start_x, start_y) to (end_x, end_y)"""
        for y in range(start_y, end_y):
            yield self.enumerate_row(win, start_x, end_x, y)
