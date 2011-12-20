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
