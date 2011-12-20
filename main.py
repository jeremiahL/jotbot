import sys
import os
import curses
import pty
import tty
import threading
import termios
import Queue
import re

IDLE_TIMEOUT=1
COLS = 80
ROWS = 25

class SubprocessNethack:
	def __init__(self, exe, playground):
		(pid, self.fd) = pty.fork()
		if (pid == 0):
			# child, exec nethack
			os.execl(exe, exe, "-d", playground)
			print "Error: should not reach here"
			os._exit(1)

	def read(self):
		return os.read(self.fd, 1)

	def write(self, str):
		os.write(self.fd, str)

# ugly stuff from web for getch
def getch():
	fd = sys.stdin.fileno()
	old_settings = termios.tcgetattr(fd)
        try:
		tty.setcbreak(fd)
        	ch = sys.stdin.read(1)
	finally:
		termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
	return ch

# Escape sequence regexes
escH_re = re.compile(r'\[(?:([0-9][0-9]?)?\;([0-9][0-9]?)?)?H')
escK_re = re.compile(r'\[([0-2])?K')
escJ_re = re.compile(r'\[([0-2])?J')
escz_re = re.compile(r'\[([0-3])(?:\;([0-9]*))?z')

# vt_tiledata window numbers
BASE_WINDOW = 0
MSG_WINDOW = 1
STATUS_WINDOW = 2
MAP_WINDOW = 3
INV_WINDOW = 4
OTHER_WINDOW_BASE = 5

def noop():
	pass

class NethackParser:

	def __init__(self, nh):
		self.nh = nh
		self.escapeseq = None
		self.window = BASE_WINDOW
		self.cursor_x = 0
		self.cursor_y = 0
		self.tilech = None
		self.end_of_data = False

		# TODO: these will need to change
		self.pending_tiles = list()
		self.current_tiles = list()

		self.basestr = ""
		self.msgstr = ""

		self.idle_func = noop

	def output_thread(self, q):
		ch = self.nh.read()
		while (ch):
			q.put(ch)
			ch = self.nh.read()
		print "Nethack exited (EOF)"

	def cursor_rel_x(self, adj):
		self.cursor_x += adj
		if (self.cursor_x < 0):
			self.cursor_x = 0
		if (self.cursor_x > COLS):
			self.cursor_x = COLS

	def cursor_rel_y(self, adj):
		self.cursor_y += adj
		if (self.cursor_y < 0):
			self.cursor_y = 0
		if (self.cursor_y > ROWS):
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
				self.escapeseq = None
			elif (ch == 'M'):
				# down one line
				if len(self.escapeseq) != 1:
					print "Error: illegal escape:",\
						self.escapeseq
					sys.exit(1)
				self.cursor_rel_y(1)
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
					for c in range(self.cursor_x, COLS-1):
						self.pending_tiles.append(
							(c, self.cursor_y, -1))
				elif str == "1":
					for c in range(0, self.cursor_x-1):
						self.pending_tiles.append(
							(c, self.cursor_y, -1))
				elif str == "2":
					for c in range(0, COLS-1):
						self.pending_tiles.append(
							(c, self.cursor_y, -1))
				self.escapeseq = None
			elif (ch == 'J'):
				m = escJ_re.match(self.escapeseq)
				if not m:
					print "Error: illegal escape:",\
					      self.escapeseq
				str = m.group(1)
				if not str or str == "0":
					for r in range(self.cursor_y+1, ROWS-1):
						for c in range(0, COLS-1):
							self.pending_tiles.append(
								(c, r, -1))
				elif str == "1":
					for r in range(0, self.cursor_y-1):
						for c in range(0, COLS-1):
							self.pending_tiles.append(
								(c, r, -1))
				elif str == "2":
					for r in range(0, ROWS-1):
						for c in range(0, COLS-1):
							self.pending_tiles.append(
								(c, r, -1))
				else:
					print "Error: illegal escape:",\
						self.escapeseq
					sys.exit(1)
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
					self.pending_tiles.append(
						(self.cursor_x, self.cursor_y, 
						 int(m.group(2))))
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
					# TODO apply updates
					self.current_tiles = self.pending_tiles
					self.pending_tiles = list()
				else:
					print "Error: illegal sequence:",\
						self.escapeseq
					sys.exit(1)
				self.escapeseq = None
			elif (ch == 'h'):
				if (self.escapeseq != "[?1049h"):
					print "Error: illegal escape:",\
					      self.escapeseq
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

			# A regular character advances the cursor
			self.cursor_x += 1

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
				pass
			elif self.window == MAP_WINDOW:
				print "Error: non-tile data in map window:", ch
				sys.exit(1)
			elif self.window == INV_WINDOW:
				# TODO
				pass
			else:
				# TODO
				pass
		
	def parser_loop(self):
		output = Queue.Queue()
		t = threading.Thread(target=self.output_thread, args=(output,))
		t.daemon = True
		t.start()

		# TODO: use ttyrec instead (or in addition)
		outlog = file("nethack.out", mode='w', buffering=0)

		while True:
			try:
				while True:
					ch = output.get(timeout=IDLE_TIMEOUT)
					# TODO: switch to self.log_func()
					outlog.write(ch)
					self.process_char(ch)
			except Queue.Empty:
				pass

			# TODO: Check if the last run command is complete.  If 
			# it is and we are idle and we've gotten the 
			# "output done" vt_tiledata then we can fire all the 
			# pending events.

			self.idle_func()

	# Start the parser in its own thread
	def start(self):
		t = threading.Thread(target=self.parser_loop)
		t.daemon = True
		t.start()

class JotBot:

	def __init__(self):
		self.stopped = True
		self.input_lock = threading.Lock()
		self.bot_commands = {
			"passthru": self.start_passthru,
			"tiles": self.show_tiles,
			"cursor": self.show_cursor,
			"quit": self.quit,
		}


	def start_passthru(self):
		self.input_lock.acquire()
		self.stopped = True
		print "Entering passthru mode (~ to exit)"
		self.input_lock.release()
		while True:
			ch = getch()
			if ch == '~':
				return
			self.input_lock.acquire()
			self.nh.write(ch)
			self.input_lock.release()

	def show_tiles(self):
		for t in self.parser.current_tiles:
			print "(%d, %d) = %d" % t

	def show_cursor(self):
		print "(%d, %d)" % (
			self.parser.cursor_x, self.parser.cursor_y)

	def quit(self):
		sys.exit(0)

	def bot_loop(self):
		while True:
			sys.stdout.write("jotbot# ")
			cmd = sys.stdin.readline().strip()
			# process command
			if not cmd:
				continue
			try:
				func = self.bot_commands[cmd]
				func()
			except KeyError:
				print "Unknown command:", cmd


	def main(self, argv):
		# Launch nethack as a sub-process
		# TODO: also support telnet to nao
		self.nh = SubprocessNethack(
			"/opt/nethack/nethack.alt.org/nh343/nethack.343-nao",
			"/opt/nethack/nethack.alt.org/nh343/")

		# Start the parser thread
		self.parser = NethackParser(self.nh)
		self.parser.start()

		# Run the loop that processes the bot menu
		self.bot_loop()

# main
JotBot().main(sys.argv[1:])
