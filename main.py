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

stopped = True
input_lock = threading.Lock()

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

def output_thread(q):
	global nh
	ch = nh.read()
	while (ch):
		q.put(ch)
		ch = nh.read()
	print "Nethack exited (EOF)"

# ugly stuff from web for getch
# TODO: this doesn't work for stdin, probably use a pipe or something to control it instead
def getch():
	fd = sys.stdin.fileno()
	old_settings = termios.tcgetattr(fd)
        try:
		tty.setcbreak(fd)
        	ch = sys.stdin.read(1)
	finally:
		termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
	return ch


# Buffer up escape sequences
escapeseq = None

# Escape sequence regexes
escH_re = re.compile(r'\[(?:([0-9][0-9]?)?\;([0-9][0-9]?)?)?H')
escK_re = re.compile(r'\[([0-2])?K')
escJ_re = re.compile(r'\[([0-2])?J')
escz_re = re.compile(r'\[([0-3])(?:\;([0-9]*))?z')

BASE_WINDOW = 0
MSG_WINDOW = 1
STATUS_WINDOW = 2
MAP_WINDOW = 3
INV_WINDOW = 4
OTHER_WINDOW_BASE = 5

window = BASE_WINDOW

# The current position of the cursor in our "terminal"
cursor = lambda:None
cursor.x = 0
cursor.y = 0

tilech = None
end_of_data = False

# Buffer up all the map data and apply only after we know the dungeon level
# (dungeon level update in status line is printed after map)
pending_tiles = list()
current_tiles = list()

basestr = ""
msgstr = ""

def cursor_rel_x(adj):
	cursor.x += adj
	if (cursor.x < 0):
		cursor.x = 0
	if (cursor.x > COLS):
		cursor.x = COLS

def cursor_rel_y(adj):
	cursor.y += adj
	if (cursor.y < 0):
		cursor.y = 0
	if (cursor.y > ROWS):
		cursor.y = ROWS

def process_char(ch):
	# XXX: This whole function is a little hacky, probably
	#      could be improved.
	global cursor
	global window
	global escapeseq
	global tilech
	global end_of_data
	global pending_tiles
	global current_tiles
	global basestr
	global msgstr
	end_of_data = False
	if ch == '\x1b': # Escape
		if escapeseq is None:
			# Start an escape sequence
			escapeseq = ""
		elif escapeseq == "":
			# Escape escape is nothing, ignore
			escapeseq = None
			return
		else:
			if escapeseq is not None:
				print "Error: Incomplete escape seq:", escapeseq
				sys.exit(1)
			escapeseq = ""
			# Not expecting an escape here...
		return

	if escapeseq is not None:
		print "in escape:", ch
		# I'm in an escape sequence, keep appending
		if len(escapeseq) > 7:
			print "Error: escape sequence too long:", escapeseq
			sys.exit(1)
		escapeseq += ch
		# XXX: The other bots handle more escape sequences, but for
		# now I'll only handle ones that I've seen.
		if (ch == 'H'):
			# set cursor
			m = escH_re.match(escapeseq)
			if not m:
				print "Error: illegal escape:", escapeseq
			str = m.group(1)
			if str:
				cursor.y = int(str)-1
			else:
				cursor.y = 0
			str = m.group(2)
			if str:
				cursor.x = int(str)-1
			else:
				cursor.x = 0
			escapeseq = None
			print "cursor:",cursor.x, cursor.y
		elif (ch == 'M'):
			# down one line
			if len(escapeseq) != 1:
				print "Error: illegal escape:", escapeseq
				sys.exit(1)
			cursor_rel_y(1)
			escapeseq = None
		elif (ch == 'C'):
			# right one col
			if (escapeseq) != "[C":
				print "Error: illegal escape:", escapeseq
				sys.exit(1)
			cursor_rel_x(1)
			escapeseq = None
		elif (ch == 'D'):
			# left one col
			if (escapeseq) != "[D":
				print "Error: illegal escape:", escapeseq
				sys.exit(1)
			cursor_rel_x(-1)
			escapeseq = None
		elif (ch == 'K'):
			m = escK_re.match(escapeseq)
			if not m:
				print "Error: illegal escape:", escapeseq
				sys.exit(1)
			str = m.group(1)
			if not str or str == "0":
				for c in range(cursor.x, COLS-1):
					pending_tiles.append((c, cursor.y, -1))
			elif str == "1":
				for c in range(0, cursor.x-1):
					pending_tiles.append((c, cursor.y, -1))
			elif str == "2":
				for c in range(0, COLS-1):
					pending_tiles.append((c, cursor.y, -1))
			escapeseq = None
		elif (ch == 'J'):
			m = escJ_re.match(escapeseq)
			if not m:
				print "Error: illegal escape:", escapeseq
			str = m.group(1)
			if not str or str == "0":
				for r in range(cursor.y+1, ROWS-1):
					for c in range(0, COLS-1):
						pending_tiles.append(
							(c, r, -1))
			elif str == "1":
				for r in range(0, cursor.y-1):
					for c in range(0, COLS-1):
						pending_tiles.append(
							(c, r, -1))
			elif str == "2":
				for r in range(0, ROWS-1):
					for c in range(0, COLS-1):
						pending_tiles.append(
							(c, r, -1))
			else:
				print "Error: illegal escape:", escapeseq
			escapeseq = None
		elif (ch == 'z'):
			m = escz_re.match(escapeseq)
			if not m:
				print "Error: illegal escape:", escapeseq
			str = m.group(1)
			if (str == "0"):
				if (window != MAP_WINDOW):
					print "Error: not in map window"
					sys.exit(1)
				pending_tiles.append(
					(cursor.x, cursor.y, int(m.group(2))))
				print "tile", cursor.x, cursor.y, m.group(2)
				tilech = ""
			elif (str == "1"):
				if (window != MAP_WINDOW):
					print "Error: not in map window"
					sys.exit(1)
				if (tilech == ""):
					print "No tile char!"
				tilech = None
			elif (str == "2"):
				window = int(m.group(2))
			elif (str == "3"):
				print "end of data"
				end_of_data = True
				# TODO apply updates
				current_tiles = pending_tiles
				pending_tiles = list()
			else:
				print "Error: illegal sequence:", escapeseq
				sys.exit(1)
			escapeseq = None
		elif (ch == 'h'):
			if (escapeseq != "[?1049h"):
				print "Error: illegal escape:", escapeseq
			escapeseq = None
		elif (ch == 'm'):
			# ignore character attributes, color
			escapeseq = None
		elif (ch in 'A', 'B', '0', '1', '2'):
			if (escapeseq == "[A"):
				# up one line
				cursor_rel_y(-1)
				escape_seq = None
			if (escapeseq == "[B"):
				# down one line
				cursor_rel_y(1)
				escape_seq = None

			# TODO: there are some other escape that end in A/B
			#  If nethack uses them we will have to change this
			if (len(escapeseq) == 2 and escapeseq[0] in ('(',')')):
				# Ignore charset escape
				escapeseq = None
	else: # escape seq
		# Check for backspace
		if (ch == '\x08'):
			cursor_rel_x(-1)
			return

		# A regular character advances the cursor
		cursor.x += 1

		# A tile should contain only one non-escape char
		if tilech == '':
			tilech = ch
		elif tilech is not None:
			print "Error: multiple chars for tile:", tilech, ch
			sys.exit(1)
		elif window == BASE_WINDOW:
			# For now, not worrying about cursor position in
			# base window.  We'll see what else it is used for
			basestr += ch
		elif window == MSG_WINDOW:
			# Don't need to track cursor in message window, the 
			# chars come out in order
			msgstr += ch
		elif window == STATUS_WINDOW:
			# TODO: need to update the status line in-place
			pass
		elif window == MAP_WINDOW:
			print "Error: non-tile data in map window:", ch
			sys.exit(1)
		elif window == INV_WINDOW:
			# TODO
			pass
		else:
			# TODO
			pass
		
def nh_loop():
	global nh
	global stopped
	global input_lock
	output = Queue.Queue()
	t = threading.Thread(target=output_thread, args=(output,))
	t.daemon = True
	t.start()

	# TODO: use ttyrec instead (or in addition)
	outlog = file("nethack.out", mode='w', buffering=0)

	while True:
		try:
			while True:
				# TODO: this won't play well with lag on NAO
				# not sure how to tell the difference between
				# "waiting for input" and lag
				ch = output.get(timeout=IDLE_TIMEOUT)
				outlog.write(ch)
				process_char(ch)
		except Queue.Empty:
			pass

		# TODO: Check if the last run command is complete.  If it
		# and we are idle and we've gotten the "output done"
		# vt_tiledata then we can fire all the pending events.

		input_lock.acquire()
		if not stopped:
			# TODO: When not stopped, grab the top command
			# (or task?) off the priority queue and execute it.
			# Do this only when idel and we've gotten the "output
			# done" vt_tiledata and the previous command considers
			# itself "done"
			pass
		input_lock.release()

def start_passthru():
	global stopped
	global nh
	input_lock.acquire()
	stopped = True
	print "Entering passthru mode (~ to exit)"
	input_lock.release()
	while True:
		ch = getch()
		if ch == '~':
			return
		input_lock.acquire()
		nh.write(ch)
		input_lock.release()

def show_tiles():
	global current_tiles
	for t in current_tiles:
		print "(%d, %d) = %d" % t

def show_cursor():
	global cursor
	print "(%d, %d)" % (cursor.x, cursor.y)

def quit():
	sys.exit(0)

bot_commands = {
	"passthru": start_passthru,
	"tiles": show_tiles,
	"cursor": show_cursor,
	"quit": quit,
}

def bot_loop():
	while True:
		sys.stdout.write("jotbot# ")
		cmd = sys.stdin.readline().strip()
		# process command
		if not cmd:
			continue
		try:
			func = bot_commands[cmd]
			func()
		except KeyError:
			print "Unknown command:", cmd
def main(argv):
	global nh
	# Launch nethack as a sub-process
	# TODO: also support telnet to nao
	nh = SubprocessNethack(
		"/opt/nethack/nethack.alt.org/nh343/nethack.343-nao",
		"/opt/nethack/nethack.alt.org/nh343/")

	# Start the loop that parses output from nethack
	t = threading.Thread(target=nh_loop)
	t.daemon = True
	t.start()

	# Run the loop that process the bot menu
	bot_loop()

main(sys.argv[1:])
