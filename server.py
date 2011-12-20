import os
import pty

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


