"""Classes to represent the various ways of running nethack, mostly either
   a local subprocess or (TODO) a remote ssh connection."""

import os.path
import pty
import select
import subprocess

def default_subprocess():
    """Run a local copy of nethack from the default install location"""
    return SubprocessNethack(SubprocessNethack.DEFAULT_NH)

class SubprocessNethack:
    """Represents interacting with nethack running in a local subprocess"""

    DEFAULT_NH = os.path.expanduser('~/nh/install/games/nethack')

    def __init__(self, *args):
        """Run a nethack subprocess using the given command"""
        (parent_pty, child_pty) = pty.openpty()
        self.io_pty = open(parent_pty, 'br+', buffering=0)
        self.subproc = subprocess.Popen(args,
                                        stdin=child_pty,
                                        stdout=child_pty,
                                        bufsize=0, # unbuffered
                                        close_fds=True)

    def read(self, timeout=1.0):
        """Read data from nethack stdout if available, or if no data is
           available by the given timeout, return None"""
        (readable, _, _) = select.select((self.io_pty,), (), (),
                                         timeout)
        if readable:
            return self.io_pty.read(1024)
        return None

    def write(self, bytes_):
        """Write data to nethack stdin"""
        self.io_pty.write(bytes_)

    def terminate(self):
        """Immediately terminate the nethack subprocess with SIGTERM. This
           is intended to be used from tests."""
        self.io_pty.close()
        self.subproc.terminate()
        self.subproc.communicate()
