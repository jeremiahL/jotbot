import binascii
import re
import sys
import threading
import Queue

IDLE_TIMEOUT=1
COLS = 80
ROWS = 25

# Escape sequence regexes
escH_re = re.compile(r'\[(?:([0-9][0-9]?)?\;([0-9][0-9]?)?)?H')
escK_re = re.compile(r'\[([0-2])?K')
escJ_re = re.compile(r'\[([0-2])?J')
escz_re = re.compile(r'\[([0-3])(?:\;([0-9]*))?z')

# Status line regexes
status1_re = re.compile(r'^(.*) the ([^ ]*) *'+
	r'St:([1-9][0-9]?)(?:/([0-9][0-9]))? Dx:([1-9][0-9]?) '+
	r'Co:([1-9][0-9]?) In:([1-9][0-9]?) Wi:([1-9][0-9]?) '+
	r'Ch:([1-9][0-9]?) *([^ ]*) S:([0-9]*)')
status2_re = re.compile(r'^Dlvl:(-?[1-9][0-9]?) *\$:([0-9]*) *'+
	r'HP:([0-9]*)\(([0-9]*)\) *Pw:([0-9]*)\(([0-9]*)\) *'+
	r'AC:(-?[0-9]*) *Xp:([0-9]*)/([0-9]*) *T:([0-9]*) *'+
	r'([^ ]*(?: [^ ]+)*)?')

# vt_tiledata window numbers
BASE_WINDOW = 0
MSG_WINDOW = 1
STATUS_WINDOW = 2
MAP_WINDOW = 3
INV_WINDOW = 4
OTHER_WINDOW_BASE = 5

def noop(*args):
	pass

STATUS_START = 22

class Status:
	def __init__(self):
		self.dirty = False
		self.lines = [
			bytearray(80),
			bytearray(80),
		]
		for y in (0, 1):
			for x in range(0, 80):
				self.lines[y][x] = ord(' ')

	def update_char(self, x, y, c):
		self.lines[y][x] = ord(c)
		self.dirty = True

	def parse(self):
		self.dirty = False
		m = status1_re.match(self.lines[0])
		self.player = m.group(1)
		self.rank = m.group(2)
		self.str = int(m.group(3))
		self.str_percent = m.group(4)
		if (self.str_percent is None):
			self.str_percent = None
		else:
			self.str_percent = int(self.str_percent)
		self.dex = int(m.group(5))
		self.con = int(m.group(6))
		self.int = int(m.group(7))
		self.wis = int(m.group(8))
		self.cha = int(m.group(9))
		self.align = m.group(10)
		self.score = int(m.group(11))

		m = status2_re.match(self.lines[1])
		self.dungeon_level = int(m.group(1))
		self.gold = int(m.group(2))
		self.hp = int(m.group(3))
		self.hpmax = int(m.group(4))
		self.pw = int(m.group(5))
		self.pwmax = int(m.group(6))
		self.ac = int(m.group(7))
		self.xp_level = int(m.group(8))
		self.xp = int(m.group(9))
		self.turns = int(m.group(10))
		self.effects = str(m.group(11)).split(' ')

MAP_START = 1
MAP_ROWS = 21

class Map:

	def __init__(self):
		# Map is 80x21 max in nethack, accessing tiles outside that
		# range will give a range error
		self.tiles = [ [None]*MAP_ROWS for i in range(COLS) ]
		self.update_func = noop

	def get_tile(self, x, y):
		return self.tiles[x][y]

	def clear_rows(self, start_y, end_y):
		for x in range(0, COLS):
			for y in range(start_y, end_y):
				self.set_tile(x, y, None)

	def clear_cols(self, start_x, end_x, y):
		for x in range(start_x, end_x):
			self.set_tile(x, y, None)

	def set_tile(self, x, y, tile):
		self.tiles[x][y] = tile
		self.update_func(x, y, tile)

class NethackParser:

	def __init__(self, nh):
		self.nh = nh
		self.escapeseq = None
		self.window = BASE_WINDOW
		self.cursor_x = 0
		self.cursor_y = 0
		self.tilech = None
		self.end_of_data = False

		self.map = Map()
		self.status = Status()

		self.basestr = ""
		self.msgstr = ""
		self.invstr = ""

		self.idle_func = noop

	def newline_buffers(self):
		self.newline_buffer("basestr")
		self.newline_buffer("msgstr")
		self.newline_buffer("invstr")

	def newline_buffer(self, attr):
		str = getattr(self, attr)
		if (str == ""):
			return
		elif (str[-1] != '\n'):
			setattr(self, attr, str+"\n")

	def cursor_rel_x(self, adj):
		self.newline_buffers()
		self.cursor_x += adj
		if (self.cursor_x < 0):
			self.cursor_x = 0
		if (self.cursor_x > COLS):
			print "Cursor beyond screen: x:", self.cursor_x
			self.cursor_x = COLS

	def cursor_rel_y(self, adj):
		self.newline_buffers()
		self.cursor_y += adj
		if (self.cursor_y < 0):
			self.cursor_y = 0
		if (self.cursor_y > ROWS):
			print "Cursor beyond screen: y:", self.cursor_y
			self.cursor_y = ROWS

	def process_char(self, ch):
		# XXX: This whole function is a little hacky, probably
		#      could be improved.
		self.end_of_data = False
		if ch == '\x1b': # Escape
			if self.escapeseq is None:
				# Start an escape sequence
				self.escapeseq = ""
			elif self.escapeseq == "":
				# Escape escape is nothing, ignore
				self.escapeseq = None
				return
			else:
				if self.escapeseq is not None:
					print "Error: Incomplete escape seq:",\
					      self.escapeseq
					sys.exit(1)
				self.escapeseq = ""
			return

		if self.escapeseq is not None:
			# I'm in an escape sequence, keep appending
			if len(self.escapeseq) > 7:
				print "Error: escape sequence too long:",\
				      self.escapeseq
				sys.exit(1)
			self.escapeseq += ch
			# XXX: The other bots handle more escape sequences,
			# but for now I'll only handle ones that I've seen.
			if (ch == 'H'):
				# set cursor
				m = escH_re.match(self.escapeseq)
				if not m:
					print "Error: illegal escape:",\
					      self.escapeseq
					sys.exit(1)
				str = m.group(1)
				if str:
					self.cursor_y = int(str)-1
				else:
					self.cursor_y = 0
				str = m.group(2)
				if str:
					self.cursor_x = int(str)-1
				else:
					self.cursor_x = 0
				self.newline_buffers()
				self.escapeseq = None
			elif (ch == 'M'):
				# down one line
				if len(self.escapeseq) != 1:
					print "Error: illegal escape:",\
						self.escapeseq
					sys.exit(1)
				self.cursor_rel_y(-1)
				self.escapeseq = None
			elif (ch == 'C'):
				# right one col
				if (self.escapeseq) != "[C":
					print "Error: illegal escape:",\
						self.escapeseq
					sys.exit(1)
				self.cursor_rel_x(1)
				self.escapeseq = None
			elif (ch == 'D'):
				# left one col
				if (self.escapeseq) != "[D":
					print "Error: illegal escape:",\
						self.escapeseq
					sys.exit(1)
				self.cursor_rel_x(-1)
				self.escapeseq = None
			elif (ch == 'K'):
				m = escK_re.match(self.escapeseq)
				if not m:
					print "Error: illegal escape:",\
						self.escapeseq
					sys.exit(1)
				str = m.group(1)
				if not str or str == "0":
					start_x = self.cursor_x
					end_x = COLS
				elif str == "1":
					start_x = 0
					end_x = self.cursor_x
				elif str == "2":
					start_x = 0
					end_x = COLS
				if (self.window == MAP_WINDOW and
				    self.cursor_y >= MAP_START and
				    self.cursor_y < MAP_ROWS+MAP_START):
					self.map.clear_cols(start_x, end_x,
						self.cursor_y-MAP_START)
				# TODO: handle clears outside the map
				self.escapeseq = None
			elif (ch == 'J'):
				m = escJ_re.match(self.escapeseq)
				if not m:
					print "Error: illegal escape:",\
					      self.escapeseq
				str = m.group(1)
				if not str or str == "0":
					start_y = self.cursor_y-MAP_START+1
					end_y = MAP_ROWS
				elif str == "1":
					start_y = 0
					end_y = self.cursor_y-MAP_START
				elif str == "2":
					start_y = 0
					end_y = MAP_ROWS
				else:
					print "Error: illegal escape:",\
						self.escapeseq
					sys.exit(1)
				if self.window == MAP_WINDOW:
					self.map.clear_rows(start_y, end_y)
				self.escapeseq = None
			elif (ch == 'z'):
				m = escz_re.match(self.escapeseq)
				if not m:
					print "Error: illegal escape:",\
						self.escapeseq
					sys.exit(1)
				str = m.group(1)
				if (str == "0"):
					if (self.window != MAP_WINDOW):
						print "Error: not in map window"
						sys.exit(1)
					self.map.set_tile(
						self.cursor_x,
						self.cursor_y-MAP_START,
						 int(m.group(2)))
					self.tilech = ""
				elif (str == "1"):
					if (self.window != MAP_WINDOW):
						print "Error: not in map window"
						sys.exit(1)
					if (self.tilech == ""):
						print "No tile char!"
					self.tilech = None
				elif (str == "2"):
					self.window = int(m.group(2))
				elif (str == "3"):
					self.end_of_data = True
					# XXX: hack
					self.window = MSG_WINDOW
				else:
					print "Error: illegal sequence:",\
						self.escapeseq
					sys.exit(1)
				self.escapeseq = None
			elif (ch == 'h'):
				if (self.escapeseq != "[?1049h"):
					print "Error: illegal escape:",\
					      self.escapeseq
					sys.exit(1)
				self.escapeseq = None
			elif (ch == 'l'):
				if (self.escapeseq != "[?1049l"):
					print "Error: illegal escape:",\
						self.escapeseq
					sys.exit(1)
				self.escapeseq = None
			elif (ch == 'm'):
				# ignore character attributes, color
				self.escapeseq = None
			elif (ch in 'A', 'B', '0', '1', '2'):
				if (self.escapeseq == "[A"):
					# up one line
					self.cursor_rel_y(-1)
					self.escape_seq = None
				if (self.escapeseq == "[B"):
					# down one line
					self.cursor_rel_y(1)
					self.escape_seq = None

				if (len(self.escapeseq) == 2 and
				    self.escapeseq[0] in ('(',')')):
					# Ignore charset escape
					self.escapeseq = None
		else: # escape seq
			# Check for backspace
			if (ch == '\x08'):
				self.cursor_rel_x(-1)
				return
			# carriage return
			if (ch == '\x0D'):
				self.cursor_x = 0
				return
			# line feed
			if (ch == '\x0A'):
				self.cursor_rel_y(1)
				return
			# TODO: other movement chars??

			# A tile should contain only one non-escape char
			if self.tilech == '':
				self.tilech = ch
			elif self.tilech is not None:
				print "Error: multiple chars for tile:",\
				      self.tilech, ch
				sys.exit(1)
			elif self.window == BASE_WINDOW:
				# For now, not worrying about cursor position
				# in base window.  We'll see what else it is 
				# used for.
				self.basestr += ch
			elif self.window == MSG_WINDOW:
				# Don't need to track cursor in message
				# window, the chars come out in order
				self.msgstr += ch
			elif self.window == STATUS_WINDOW:
				# TODO: need to update the status line in-place
				if (self.cursor_y >= STATUS_START):
					self.status.update_char(
						self.cursor_x,
						self.cursor_y-STATUS_START,
						ch)
				else:
					print "Error: data outside status line"
					sys.exit(1)
			elif self.window == MAP_WINDOW:
				print "Error: non-tile data in map window:", ch
				sys.exit(1)
			elif self.window == INV_WINDOW:
				self.invstr += ch
			else:
				# TODO
				pass

			# regular char advances cursor, don't use the method
			# to avoid the newline message effect
			self.cursor_x += 1
			if (self.cursor_x > COLS):
				self.cursor_x = COLS
				print "Write beyond screen"
		
	def parser_loop(self):
		# TODO: use ttyrec instead (or in addition)
		outlog = file("nethack.out", mode='w', buffering=0)

		while True:
			try:
				while True:
					ch = self.nh.read()
					# TODO: switch to self.log_func() ?
					outlog.write(ch)
					self.process_char(ch)
					if (self.end_of_data):
						self.idle_func()
			except Queue.Empty:
				pass

			# TODO: Check if the last run command is complete.  If 
			# it is and we are idle and we've gotten the 
			# "output done" vt_tiledata then we can fire all the 
			# pending events.


	# Start the parser in its own thread
	def start(self):
		t = threading.Thread(target=self.parser_loop)
		t.daemon = True
		t.start()


