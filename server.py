import os.path
import pty
import select
import subprocess

def default_subprocess():
    return SubprocessNethack(SubprocessNethack.DEFAULT_NH)

class SubprocessNethack:

    DEFAULT_NH = os.path.expanduser('~/nh/install/games/nethack')

    def __init__(self, *args):
        (parent_pty, child_pty) = pty.openpty()
        self.input_pty = open(parent_pty, 'wb', buffering=0)
        self.subproc = subprocess.Popen(args,
            stdin=child_pty,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0, # unbuffered
            close_fds=True)

    def read(self, timeout=1.0):
        return self._handleOut(self.subproc.stdout, timeout)

    def error(self, timeout=1.0):
        return self._handleOut(self.subproc.stderr, timeout)

    def _handleOut(self, stream, timeout):
        (readable, _, _) = select.select((stream,), (), (), timeout)
        if readable:
            return stream.read(1024)

    def write(self, bytes_):
        self.input_pty.write(bytes_)

    # this is mostly for the tests
    def terminate(self):
        self.input_pty.close()
        self.subproc.terminate()
        self.subproc.communicate()

