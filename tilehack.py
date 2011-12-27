from Tkinter import *
from tkFont import Font
from PIL import Image
from PIL import ImageTk

from collections import deque
import threading
import time

# local imports
from parser import *
from server import *

NUM_TILES=1057
TILES_PER_ROW=40
TILE_WIDTH=16
TILE_HEIGHT=16

BLANK_TILE=829
REFRESH_RATE=50

def _mkstatlabel(parent, font, text):
	ret = Label(parent,
		bg="black",
		fg="white",
		bd=0,
		font=font,
		text=text)
	ret.pack(side=LEFT)
	return ret


class Application(Frame):
	def __init__(self, master=None):
		Frame.__init__(self, master, bg="black")
		self.loadTiles()
		self.pack()
		self.createWidgets()
		self.bind_all("<Any-KeyPress>", self.keypress)
		# TODO: all locks should use try/finally block
		self.lock = threading.Lock()
		self.status_dirty = False
		self.messages = deque()
		self.more = False
		self.clear_message = True

	def keypress(self, event):
		self.lock.acquire()
		if self.more:
			if (event.char == ' '):
				self.more = False
				self.clear_message = True
			elif (event.char == '\x1b'):
				self.more = False
				self.messages.clear()
				self.clear_message = True
			self.lock.release()
			return
		if (event.char):
			self.clear_message = True
			self.nh.write(event.char)
		self.lock.release()

	def tile_update(self, x, y, tile):
		self.pending_tile[x][y] = tile

	def nh_idle(self):
		self.lock.acquire()
		if self.parser.status.dirty:
			self.status_dirty = True
			self.parser.status.parse()
		if self.parser.msgstr:
			self.messages.extend(filter(str.strip,
				self.parser.msgstr.split('\n')))
			self.parser.msgstr = ''
		basestr = self.parser.basestr.strip()
		self.parser.basestr = ''
		if basestr.endswith("--More--"):
			# So it shows in ttyrec, watchers, etc.
			time.sleep(0.5)
			self.nh.write(' ')
			basestr = basestr[0:-8]
		self.messages.extend(filter(str.strip, basestr.split('\n')))
		self.lock.release()

	def show_more(self, b):
		# The text is always there, just use black-on-black to hide
		if b:
			self.more_label.configure(bg="white")
		else:
			self.more_label.configure(bg="black")
		self.more = b

	def color_stat(self, attr, reverse=False):
		cur = getattr(self.parser.status, attr)
		try:
			last = getattr(self, attr+"_last")
			if (cur > last):
				color = "green"
			elif (cur < last):
				color = "red"
			else:
				color = "white"
		except:
			last = None
			color = "white"
		if (reverse):
			if (color == "green"):
				color = "red"
			elif (color == "red"):
				color = "green"
		label = getattr(self, attr+"_label")
		if (last != cur):
			label.configure(
				text=str(cur),
				fg=color)
			setattr(self, attr+"_last", cur)
			setattr(self, attr+"_turn", self.parser.status.turns)
		else:
			# clear the color once 3 turns have passed
			if (getattr(self, attr+"_turn")+3 <=
			    self.parser.status.turns):
				label.configure(fg=color)

	def refresh(self):
		# for now, no lock between update_tile and refresh
		for y in range(0, MAP_ROWS):
			for x  in range(0, COLS):
				pending = self.pending_tile[x][y]
				if (pending != self.current_tile[x][y]):
					self.current_tile[x][y] = pending
					if (pending is None):
						self.map.itemconfigure(
						    self.image_ids[x][y],
						    state=HIDDEN)
					else:
						self.map.itemconfigure(
						    self.image_ids[x][y],
						    image=self.images[pending],
						    state=NORMAL)
		self.lock.acquire()
		msg = ""
		while (self.messages and self.clear_message):
			if self.more:
				break
			if (len(msg) + len(self.messages[0]) > 80):
				break
			msg += self.messages.popleft()+"  "
		if (msg):
			self.message_label.configure(text=msg)
			self.clear_message = False
		elif self.clear_message:
			self.message_label.configure(text="")
		self.show_more(len(self.messages))
		if self.status_dirty:
			self.status_dirty = False
			# Some fields are always white
			self.name_label.configure(
				text=self.parser.status.player)
			self.rank_label.configure(
				text=self.parser.status.rank)
			self.align_label.configure(
				text=self.parser.status.align)
			self.dungeon_level_label.configure(
				text=self.parser.status.dungeon_level)
			self.turns_label.configure(
				text=self.parser.status.turns)
			# curses-style colored status
			# TODO: hpmon-style coloring of HP?
			self.color_stat("str")
			self.color_stat("dex")
			self.color_stat("con")
			self.color_stat("int")
			self.color_stat("wis")
			self.color_stat("cha")
			self.color_stat("score")
			self.color_stat("gold")
			self.color_stat("hp")
			self.color_stat("hpmax")
			self.color_stat("pw")
			self.color_stat("pwmax")
			self.color_stat("ac", reverse=True)
			self.color_stat("xp_level")
			self.color_stat("xp")
			# strength percent must be handled specially
			percent = self.parser.status.str_percent
			if percent is None:
				self.str_slash_label.configure(text="")
				self.str_percent_label.configure(text="")
				self.str_percent_last = -1
			else:
				self.str_slash_label.configure(text="/")
				self.color_stat("str_percent")
				if (percent < 10):
					self.str_percent_label.configure(
						text="0"+str(percent))
		self.lock.release()
		self.after(REFRESH_RATE, self.refresh)

	def createWidgets(self):
		f = Font(family="Courier", size=16)
		width = COLS*TILE_WIDTH

		# TODO: center text?  Multi-line messages?
		self.message_label = Label(self,
			fg="white",
			bg="black",
			bd=0,
			font=f,
			text="Test message")
		self.message_label.pack(anchor=W)

		self.more_label = Label(self,
			bg="black",
			fg="black",
			bd=0,
			font=f,
			text="--More--")
		self.more_label.pack(anchor=W)

		self.map = Canvas(self, 
			height=TILE_HEIGHT*MAP_ROWS,
			width=width,
			bd=0,
			bg="black",
			highlightthickness=0)
		
		self.map.pack()

		# Pre-populate the entire map with the "blank" tile
		self.image_ids = [ [None]*MAP_ROWS for i in range(COLS) ]
		self.pending_tile = [ [None]*MAP_ROWS for i in range(COLS) ]
		self.current_tile = [ [None]*MAP_ROWS for i in range(COLS) ]
		for y in range(0, MAP_ROWS):
			for x in range(0, COLS):
				self.image_ids[x][y] = self.map.create_image(
					x*TILE_WIDTH,
					y*TILE_HEIGHT,
					image=self.images[BLANK_TILE],
					state=HIDDEN,
					anchor=NW)

		# Split the status line into many labels for colors
		self.status1 = Frame(self, bg="black")
		self.status1.pack(anchor=W)
		self.status2 = Frame(self, bg="black")
		self.status2.pack(anchor=W)

		self.name_label = _mkstatlabel(self.status1, f, "Player")
		_mkstatlabel(self.status1, f, " the ")
		self.rank_label = _mkstatlabel(self.status1, f, "Rank")
		_mkstatlabel(self.status1, f, "    Str:")
		self.str_label = _mkstatlabel(self.status1, f, "18")
		self.str_slash_label = _mkstatlabel(self.status1, f, "/")
		self.str_percent_label = _mkstatlabel(self.status1, f, "99")
		_mkstatlabel(self.status1, f, " Dex:")
		self.dex_label = _mkstatlabel(self.status1, f, "18")
		_mkstatlabel(self.status1, f, " Con:")
		self.con_label = _mkstatlabel(self.status1, f, "18")
		_mkstatlabel(self.status1, f, " Int:")
		self.int_label = _mkstatlabel(self.status1, f, "18")
		_mkstatlabel(self.status1, f, " Wis:")
		self.wis_label = _mkstatlabel(self.status1, f, "18")
		_mkstatlabel(self.status1, f, " Cha:")
		self.cha_label = _mkstatlabel(self.status1, f, "18")
		_mkstatlabel(self.status1, f, "  ")
		self.align_label = _mkstatlabel(self.status1, f, "Alignment")
		_mkstatlabel(self.status1, f, " S:")
		self.score_label = _mkstatlabel(self.status1, f, "31549")

		_mkstatlabel(self.status2, f, "Dlvl:")
		self.dungeon_level_label = _mkstatlabel(self.status2, f, "0")
		_mkstatlabel(self.status2, f, "  $:")
		self.gold_label = _mkstatlabel(self.status2, f, "54321")
		_mkstatlabel(self.status2, f, "  HP:")
		self.hp_label = _mkstatlabel(self.status2, f, "99")
		_mkstatlabel(self.status2, f, "(")
		self.hpmax_label = _mkstatlabel(self.status2, f, "99")
		_mkstatlabel(self.status2, f, ") Pw:")
		self.pw_label = _mkstatlabel(self.status2, f, "1")
		_mkstatlabel(self.status2, f, "(")
		self.pwmax_label = _mkstatlabel(self.status2, f, "1")
		_mkstatlabel(self.status2, f, ") AC:")
		self.ac_label = _mkstatlabel(self.status2, f, "10")
		_mkstatlabel(self.status2, f, "  Xp:")
		self.xp_level_label = _mkstatlabel(self.status2, f, "1")
		_mkstatlabel(self.status2, f, "/")
		self.xp_label = _mkstatlabel(self.status2, f, "0")
		_mkstatlabel(self.status2, f, " T:")
		self.turns_label = _mkstatlabel(self.status2, f, "1")
		_mkstatlabel(self.status2, f, " ")
		self.conf_status_label = _mkstatlabel(
			self.status2, f, "Conf")

	def loadTiles(self):
		self.bigimage = Image.open("tiles.png")
		self.images = [None]*NUM_TILES
		for i in range(0, NUM_TILES):
			x = i % TILES_PER_ROW
			y = i / TILES_PER_ROW
			self.images[i] = ImageTk.PhotoImage(
				self.bigimage.crop(
					(x*TILE_WIDTH, y*TILE_HEIGHT,
					 x*TILE_WIDTH+TILE_WIDTH,
					 y*TILE_HEIGHT+TILE_HEIGHT)))

	def main(self, argv):
                # Launch nethack as a sub-process
                # TODO: also support telnet to nao
                # TODO: make wizmode optional
		# TODO: startup dialog
                self.nh = SubprocessNethack(
                        "/opt/nethack/nethack.alt.org/nh343/nethack.343-nao",
                        "/opt/nethack/nethack.alt.org/nh343/", "-D")

                # Start the parser thread
                self.parser = NethackParser(self.nh)
		self.parser.map.update_func = self.tile_update
		self.parser.idle_func = self.nh_idle
                self.parser.start()

		self.master.title("Tile Hack")
		self.after_idle(self.refresh)
		self.mainloop()

Application().main(sys.argv)
