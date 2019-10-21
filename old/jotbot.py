import sys
import tty
import threading
import termios

# Local modules
from server import *
from parser import *

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

class JotBot:

	def __init__(self):
		self.stopped = True
		self.input_lock = threading.Lock()
		self.bot_commands = {
			"passthru": self.start_passthru,
			"tiles": self.show_tiles,
			"cursor": self.show_cursor,
			"status": self.show_status,
			"message": self.show_message,
			"base": self.show_base,
			"inv": self.show_inv,
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
		for y in range(0, MAP_ROWS):
			for x in range(0, COLS):
				t = self.parser.map.get_tile(x, y)
				if t:
					print "%4d" % t,
				else:
					print "----", 
			print

	def show_cursor(self):
		print "(%d, %d)" % (
			self.parser.cursor_x, self.parser.cursor_y)

	def show_status(self):
		print self.parser.status.lines[0].decode('ascii')
		print self.parser.status.lines[1].decode('ascii')
		self.parser.status.parse()
		for x in dir(self.parser.status):
			print x, getattr(self.parser.status, x)

	def show_message(self):
		print self.parser.msgstr

	def show_base(self):
		print self.parser.basestr

	def show_inv(self):
		print self.parser.invstr

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
		# TODO: make wizmode optional
		self.nh = SubprocessNethack(
			"/opt/nethack/nethack.alt.org/nh343/nethack.343-nao",
			"/opt/nethack/nethack.alt.org/nh343/", "-D")

		# Start the parser thread
		self.parser = NethackParser(self.nh)
		self.parser.start()

		# Run the loop that processes the bot menu
		self.bot_loop()

# main
JotBot().main(sys.argv[1:])
