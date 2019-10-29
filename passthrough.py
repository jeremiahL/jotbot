"""A sort of interactive test. It runs a local nethack subprocess and
   passes its output to the parser as well as showing it on the screen."""

import os
import pty
import subprocess
import sys

import parser
import server

def child_main():
    """Read from my stdin and send to the parser as
       well as to stdout"""
    parser_ = parser.Parser()

    data = sys.stdin.buffer.read(1)
    while data:
        sys.stdout.buffer.write(data)
        sys.stdout.buffer.flush()
        parser_.parse_bytes(data)
        data = sys.stdin.buffer.read(1)

def parent_main():
    """Launch nethack using its own pseudo-terminal. This keeps it
       from inheriting the actual terminal size and instead will use
       the default 24x80"""
    pty.spawn([server.SubprocessNethack.DEFAULT_NH])

def launch_main():
    """Launch two separate subprocess. One will handle running nethack
       and the other will be the parser."""
    (rpipe, wpipe) = os.pipe()
    subprocess.Popen([sys.executable, sys.argv[0], 'child'], stdin=rpipe)
    parent_proc = subprocess.Popen([sys.executable, sys.argv[0], 'parent'], stdout=wpipe)

    parent_proc.wait()

if __name__ == '__main__':
    # This arg-parsing is lame...
    if len(sys.argv) == 1:
        launch_main()
    elif len(sys.argv) != 2:
        print("Don't call this with arguments")
        sys.exit(1)
    elif sys.argv[1] == 'child':
        child_main()
    elif sys.argv[1] == 'parent':
        parent_main()
    else:
        print("Bad argument")
        sys.exit(1)
